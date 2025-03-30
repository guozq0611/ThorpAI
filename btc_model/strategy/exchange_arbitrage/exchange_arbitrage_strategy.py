import pandas as pd
import threading
import queue
import asyncio
from typing import NamedTuple, Dict, Tuple, Optional
import ccxt
import time
import ccxt.pro as ccxtpro
import numpy as np
import json
import os
from collections import defaultdict

from btc_model.core.util.log_util import Logger
from btc_model.strategy.exchange_arbitrage.pairs_monitor import PairsMonitor
from btc_model.core.common.object import PositionData, BlacklistSymbol
from btc_model.trade.position_holder import PositionHolder
from btc_model.setting.setting import get_settings
from btc_model.core.util.crypto_util import CryptoUtil
from btc_model.core.market.market_data_service import MarketDataService
from btc_model.core.common.context import Context
from btc_model.trade.arbitrage_position_manager import ArbitragePositionManager
from btc_model.core.util.crypto_util import CryptoUtil
from btc_model.core.util.db_util import DBUtil

class CommonParams(NamedTuple):
    """
    通用参数
    """
    order_timeout: int  # 订单超时时间（秒）
    retry_times: int  # 重试次数
    order_imbalance_threshold: float  # 订单不平衡阈值
    order_chase_times: int  # 追单次数  
    imbalance_adjust_times: int  # 残腿调整次数


class CapitalLimitParams(NamedTuple):
    """
    资金限制参数
    """
    max_amount: float   # 策略最大资金量, 美金
    max_trading_pairs: int      # 策略最大在途货币对数量
    max_amount_per_pair: float  # 策略单个货币对最大资金量, 美金
    min_amount_per_pair: float  # 策略单个货币对最小资金量, 美金
    swap_leverage: int  # 永续合约杠杆倍数

class SpreadThresholdParams(NamedTuple):
    """
    价差阈值参数
    """
    min_percent: float  # 最小价差百分比
    max_percent: float  # 最大价差百分比（防异常）
    min_absolute: float  # 最小绝对价差（USDT）
    max_absolute: float  # 最大绝对价差（USDT）
    min_profit: float  # 最小利润率

class SpreadOccurrenceParams(NamedTuple):
    """
    价差出现次数参数
    """
    duration: int  # 窗口时长（秒）
    min_occurrences: int  # 最小出现次数
    consecutive_required: bool  # 是否要求连续


class RiskControlParams(NamedTuple):
    """
    风险控制参数
    """
    max_loss_limit_absolute_daily: float  # 单日最大亏损限制（绝对值）
    max_consecutive_loss_times: int  # 连续亏损次数


class StrategyParams(NamedTuple):
    """
    策略参数
    """
    common_params: CommonParams
    capital_limit_params: CapitalLimitParams
    spread_threshold_params: SpreadThresholdParams
    spread_occurrence_params: SpreadOccurrenceParams
    risk_control_params: RiskControlParams

    @classmethod
    def from_settings(cls) -> 'StrategyParams':
        config = get_settings('strategy.exchange_arbitrage')
        return cls(
            common_params=CommonParams(**config['common_params']),
            capital_limit_params=CapitalLimitParams(**config['capital_limit_params']),
            spread_threshold_params=SpreadThresholdParams(**config['spread_threshold_params']),
            spread_occurrence_params=SpreadOccurrenceParams(**config['spread_occurrence_params']),
            risk_control_params=RiskControlParams(**config['risk_control_params'])
        )
    
class ExchangeArbitrageStrategy:
    """
    跨交易所套利策略
    """
    def __init__(self,
                 exchange_1: ccxt.Exchange, 
                 exchange_2: ccxt.Exchange, 
                 hedge_exchange: ccxt.Exchange,
                 pair_data: dict,
                 context: Context = None
                 ):
        """
        初始化策略
        
        params:
            exchange_1: 交易所1, 用于现货多头仓位的创建
            exchange_2: 交易所2, 用于永续合约空头对冲仓位的创建
            hedge_exchange: 对冲交易所, 用于永续合约空头对冲仓位的创建
            pairs: 货币对列表
            context: 上下文
                1) market_data_service: MarketDataService 通过上下文传递市场行情数据服务类的实例
                
        """
        # 从配置文件中获取策略参数
        self.strategy_params = StrategyParams.from_settings()


        is_live = get_settings('trade')['live_mode']
        if not is_live and not exchange_1.isSandboxModeEnabled:
            raise ValueError(f"模拟环境不能使用真实交易所: {exchange_1.id}")
        
        if not is_live and not exchange_2.isSandboxModeEnabled:
            raise ValueError(f"模拟环境不能使用真实交易所: {exchange_2.id}")
        
        if not is_live and not hedge_exchange.isSandboxModeEnabled:
            raise ValueError(f"模拟环境不能使用真实交易所(perpetual): {hedge_exchange.id}")
        
        self.exchange_1 = exchange_1
        self.exchange_2 = exchange_2
        self.hedge_exchange = hedge_exchange

        self.pair_data = pair_data

        # 获取或创建上下文实例
        self.context = context if context else Context()
        self.market_data_service: MarketDataService = self.context.market_data_service
        self.context.strategy_params = self.strategy_params
        self.perpetual_markets = self.context.perpetual_markets

        self._blacklist_symbols = set()
        self._load_blacklist_symbols()

        # 过滤掉黑名单货币对
        self.pair_data = {pair_key: data for pair_key, data in self.pair_data.items() if pair_key not in self._blacklist_symbols}

        # 订阅市场数据
        self._subscribe_market_data()

        # 初始化套利仓位管理器
        self.position_manager = ArbitragePositionManager(
            exchange_1=self.exchange_1,
            exchange_2=self.exchange_2,
            exchange_hedge=self.hedge_exchange,
            context=self.context
        )
  
        # # 初始化数据结构
        # self.pair_data = {}
        # for pair in pairs:
        #     symbol_a = pair['symbol_a']
        #     symbol_b = pair['symbol_b']
        #     symbol_hedge = CryptoUtil.convert_symbol_to_contract(self.hedge_exchange, symbol_a)

        #     pair_key = (symbol_a, symbol_b)
        #     self.pair_data[pair_key] = {
        #         'trading_limits_a': CryptoUtil.get_trading_limits(self.exchange_1, symbol_a),
        #         'trading_limits_b': CryptoUtil.get_trading_limits(self.exchange_2, symbol_b),
        #         'trading_limits_hedge': CryptoUtil.get_trading_limits(self.hedge_exchange, symbol_hedge),
        #         'price_a': None,
        #         'price_b': None,
        #         'spread': 0,
        #         'comment': '',
        #         'timestamp': 0
        #     }
        
        # 启动监控线程
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_arbitrage_opportunities, daemon=True)
        self.monitor_thread.start()
        
        Logger.info(f"跨交易所套利策略初始化完成，监控 {len(self.pair_data)} 个交易对")
    
    def _load_blacklist_symbols(self):
        """加载黑名单货币对"""
        fecth_ressult = DBUtil().get_blacklist_symbols()
        self._blacklist_symbols = set(CryptoUtil.convert_perpetual_symbol_to_spot(result[1]) for result in fecth_ressult)

    def _subscribe_market_data(self):
        """
        订阅交易对的行情数据
        """
        spot_symbols_to_watch = set()
        swap_symbols_to_watch = set()
        # 收集所有需要订阅的交易对
        for symbol in self.pair_data:
            spot_symbols_to_watch.add(symbol)
            
            # 添加合约交易对
            contract_symbol = CryptoUtil.convert_symbol_to_contract(self.hedge_exchange, symbol)
            swap_symbols_to_watch.add(contract_symbol)

        for exchange_id in self.market_data_service.exchanges:
            for symbol in spot_symbols_to_watch:
                #market_data_service.subscribe_orderbook(exchange_id, symbol)
                self.market_data_service.subscribe_bbo(exchange_id, symbol)
            for symbol in swap_symbols_to_watch:
                #market_data_service.subscribe_orderbook(exchange_id, symbol)
                self.market_data_service.subscribe_bbo(exchange_id, symbol)
                #market_data_service.subscribe_funding_rate(exchange_id, symbol)
        
        
        # 订阅所有交易对的订单簿
        # for symbol in spot_symbols_to_watch:
        #     if symbol in [pair['symbol_a'] for pair in self.pairs]:
        #         self.market_data_service.subscribe_orderbook('exchange_1', symbol)
        #     if symbol in [pair['symbol_b'] for pair in self.pairs]:
        #         self.market_data_service.subscribe_orderbook('exchange_2', symbol)

        # for symbol in swap_symbols_to_watch:
        #     self.market_data_service.subscribe_orderbook('hedge_exchange', symbol)
        #     self.market_data_service.subscribe_funding_rate('hedge_exchange', symbol)
        
        # Logger.info(f"已订阅 {len(spot_symbols_to_watch)} 个现货交易对的市场数据")
        Logger.info(f"已订阅 {len(swap_symbols_to_watch)} 个合约交易对的市场数据")

    
    
    def _monitor_arbitrage_opportunities(self):
        """监控套利机会"""
        while self.is_running:
            try:
                for pair_key in self.pair_data:
                    self.update_pair_data(pair_key)
                    self.calculate_spread(pair_key)
                
                time.sleep(1)  # 每秒检查一次
            except Exception as e:
                Logger.error(f"监控套利机会异常: {str(e)}")
                time.sleep(5)  # 出错后等待5秒再重试
    
    def update_pair_data(self, symbol_id):
        """
        更新交易对数据
        symbol_id: 货币对（现货）, 例如: 'BTC/USDT'
        """
        try:
            # 获取交易所1的订单簿数据
            bbo_a = self.market_data_service.get_bbo(self.exchange_1.id, symbol_id)
            if bbo_a['bid_price'] and bbo_a['ask_price'] and self.market_data_service.is_data_fresh('bbo', self.exchange_1.id, symbol_id):
                self.pair_data[symbol_id]['price_a'] = {
                    'bid': bbo_a['bid_price'],
                    'ask': bbo_a['ask_price']
                }
            
            # 获取交易所2的订单簿数据
            bbo_b = self.market_data_service.get_bbo(self.exchange_2.id, symbol_id)
            if bbo_b['bid_price'] and bbo_b['ask_price'] and self.market_data_service.is_data_fresh('bbo', self.exchange_2.id, symbol_id):
                self.pair_data[symbol_id]['price_b'] = {
                    'bid': bbo_b['bid_price'],
                    'ask': bbo_b['ask_price']
                }

            swap_symbol = CryptoUtil.convert_symbol_to_contract(self.hedge_exchange, symbol_id)
            bbo_hedge = self.market_data_service.get_bbo(self.hedge_exchange.id, swap_symbol)
            if bbo_hedge['bid_price'] and bbo_hedge['ask_price'] and self.market_data_service.is_data_fresh('bbo', self.hedge_exchange.id, swap_symbol):
                self.pair_data[symbol_id]['price_hedge'] = {
                    'bid': bbo_hedge['bid_price'],
                    'ask': bbo_hedge['ask_price']
                }
            
            # 更新时间戳
            self.pair_data[symbol_id]['timestamp'] = int(time.time() * 1000)
        except Exception as e:
            Logger.error(f"更新交易对数据异常: {symbol_id}, 错误: {str(e)}")
    
    def calculate_spread(self, symbol_id):
        """带校验的价差计算"""
        data = self.pair_data[symbol_id]
        try:
            if data['price_a'] and data['price_b']:
                # 作为a的买方，监控 price_b['ask'] / price_a['bid'] - 1 的价差
                spread_buy_a = (data['price_b']['ask'] / data['price_a']['bid']) - 1
                # 作为b的买方，监控 price_a['ask'] / price_b['bid'] - 1 的价差
                spread_buy_b = (data['price_a']['ask'] / data['price_b']['bid']) - 1
                
                # 取两个价差中的较大值作为最终价差
                spread = max(spread_buy_a, spread_buy_b)
                data['spread'] = spread
                
                # 更新套利方向和注释
                if spread_buy_a > spread_buy_b:
                    data['comment'] = (
                        f'【{self.exchange_1.id}】 买入 {data["price_a"]["bid"]}, '
                        f'【{self.exchange_2.id}】 卖出 {data["price_b"]["ask"]}'
                    )
                else:
                    data['comment'] = (
                        f'【{self.exchange_2.id}】 买入 {data["price_b"]["bid"]}, '
                        f'【{self.exchange_1.id}】 卖出 {data["price_a"]["ask"]}'
                    )

                # 触发报警的价差阈值
                if spread > 0.003:  
                    self.trigger_arbitrage(symbol_id)
        except (TypeError, ZeroDivisionError, KeyError) as e:
            Logger.error(f"价差计算错误 {symbol_id}: {str(e)}")
    
    def trigger_arbitrage(self, symbol_id):
        """触发套利信号"""
        symbol_hedge = CryptoUtil.convert_symbol_to_contract(self.hedge_exchange, symbol_id)

        data = self.pair_data[symbol_id]
        
        Logger.info(
            f"套利信号触发: {symbol_id:<15} 价差: {data['spread']:>6.2%}, {data['comment']}"
        )
        
        volume = self.strategy_params.capital_limit_params.max_amount_per_pair / ((data['price_a']['bid'] + data['price_b']['ask']) / 2)
        
        # 从symbol_a的角度计算
        if volume < data['trading_limits_a']['amount']['min']:
            volume = data['trading_limits_a']['amount']['min']

        if data['trading_limits_b']['cost']['min'] is not None:
            volume = min(volume, data['trading_limits_a']['cost']['min'] / max(data['price_a']['bid'], data['price_a']['ask']))

        # 从symbol_b的角度计算
        if volume < data['trading_limits_b']['amount']['min']:
            volume = data['trading_limits_b']['amount']['min']

        if data['trading_limits_b']['cost']['min'] is not None:
            volume = min(volume, data['trading_limits_b']['cost']['min'] / max(data['price_b']['bid'], data['price_b']['ask']))


        position = self.position_manager.get_arbitrage_position(symbol_id)
        if not position or position.swap_position == 0:
            # 从symbol_hedge的角度计算
            # 按10倍杠杆计算
            position_risk = CryptoUtil.get_position_risk(self.hedge_exchange, symbol_hedge, 10)
            max_position = position_risk['max_position']
            contract_size = position_risk['contract_size']
            if volume / contract_size > max_position:
                Logger.warning(f"无非执行该套利信号, 杠杆过高: {symbol_hedge}, 杠杆: {volume / contract_size}, 最大仓位: {max_position}")
                return
    
            self.position_manager.create_arbitrage_position(symbol_id=symbol_id, volume=volume)
        else:
            # 如果仓位存在，则更新仓位
            self.position_manager.execute_arbitrage(symbol_id=symbol_id, volume=volume, exchange_pair=(self.exchange_1, self.exchange_2))
        
        # 这里可以添加自动交易逻辑
        # 例如调用 position_manager.create_arbitrage_position(pair_key, data)
    
    def stop(self):
        """停止策略"""
        self.is_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        Logger.info("跨交易所套利策略已停止")
    
    async def execute(self):
        """执行策略的主要逻辑"""
        Logger.info("开始执行跨交易所套利策略")
        
        
        self.market_data_service.start()
        
        # 主循环
        try:
            while self.is_running:
                # 这里可以添加定期检查或其他异步操作
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            Logger.info("策略执行被取消")
        except Exception as e:
            Logger.error(f"策略执行异常: {str(e)}")
        finally:
            Logger.info("策略执行结束")


# def setup_exchanges(sandbox: bool = True):

#     """设置交易所实例"""
#     # 初始化币安交易所
#     setting = get_settings('cex.sandbox.binance.spot') if sandbox else get_settings('cex.binance')
#     apikey = setting['apikey']
#     secretkey = setting['secretkey']


#     params_1 = {
#         'enableRateLimit': True,
#         'proxies': {
#             'http': get_settings('common')['proxies'].get('http', None),                  
#             'https': get_settings('common')['proxies'].get('https', None),
#         },
#         'apiKey': apikey,          
#         'secret': secretkey,       
#         'options': {
#             'defaultType': 'spot',  # 可选：'spot', 'margin', 'future'
#         },
#         'aiohttp_proxy': get_settings('common')['proxies'].get('http', None),
#         'ws_proxy': get_settings('common')['proxies'].get('http', None)
#     }

#     exchange_1 = ccxt.binance(params_1)


#      # 初始化 OKX 交易所
#     setting = get_settings('cex.sandbox.okx') if sandbox else get_settings('cex.okx')
#     apikey = setting['apikey']
#     secretkey = setting['secretkey']
#     passphrase = setting['passphrase']

#     params_2 = {
#         'enableRateLimit': True,
#         'proxies': {
#             'http': get_settings('common')['proxies'].get('http', None),                   
#             'https': get_settings('common')['proxies'].get('https', None),  
#         },
#         'apiKey': apikey,          
#         'secret': secretkey,  
#         'password': passphrase,     
#         'options': {
#             'defaultType': 'spot',
#         },
#         'aiohttp_proxy': get_settings('common')['proxies'].get('http', None),
#         'ws_proxy': get_settings('common')['proxies'].get('http', None)
#     }
#     exchange_2 = ccxt.okx(params_2)
 


#     # 初始化币安合约交易所
#     setting = get_settings('cex.sandbox.binance.swap') if sandbox else get_settings('cex.binance')
#     apikey = setting['apikey']
#     secretkey = setting['secretkey']

#     params_hedge = {
#         'enableRateLimit': True,
#         'proxies': {
#             'http': get_settings('common')['proxies'].get('http', None),                  
#             'https': get_settings('common')['proxies'].get('https', None),
#         },
#         'apiKey': apikey,          
#         'secret': secretkey,       
#         'options': {
#             'defaultType': 'swap',  # 可选：'spot', 'margin', 'future'
#         },
#         'aiohttp_proxy': get_settings('common')['proxies'].get('http', None),
#         'ws_proxy': get_settings('common')['proxies'].get('http', None)
#     }
#     exchange_hedge = ccxt.binance(params_hedge)

#     if sandbox:
#         exchange_1.set_sandbox_mode(True)
#         exchange_2.set_sandbox_mode(True)
#         exchange_hedge.set_sandbox_mode(True)

   
#     return {
#         'exchange_1': exchange_1,
#         'exchange_2': exchange_2,
#         'exchange_hedge': exchange_hedge,
#     }

def load_pairs():
    try:
        pairs_df = pd.read_csv("normal_pairs.csv")
        pairs_dif = pairs_df[pairs_df['quote'] == "USDT"]
        required_cols = ['base', 'quote', 'symbol_a', 'symbol_b']
        if not all(col in pairs_df.columns for col in required_cols):
            raise ValueError("CSV文件缺少必要列")
        pairs = pairs_df[required_cols].to_dict('records')
    except Exception as e:
        Logger.error(f"配置加载失败: {str(e)}")
        exit(1)

    return pairs

def run():
    # 创建MarketDataService实例
    market_data_service = MarketDataService()
    
    # 创建交易所实例
    market_data_service.create_exchanges(['binance', 'okx'])
    market_data_service.set_perpetual_exchanges(['okx'])

    pairs = load_pairs()

    # 过滤掉不在交易所的币种对
    currencies_binance = list(market_data_service.exchanges['binance'].currencies.keys())
    pairs = [pair for pair in pairs if pair['quote'] == 'USDT' and pair['base'] in currencies_binance]
    currencies_okx = list(market_data_service.exchanges['okx'].currencies.keys())
    pairs = [pair for pair in pairs if pair['quote'] == 'USDT' and pair['base'] in currencies_okx]

    hedge_exchange = market_data_service.exchanges['okx']
    perpetual_markets = CryptoUtil.get_perpetual_markets(exchange=hedge_exchange)
    perpetual_bases = {market_data['base'] for market_data in perpetual_markets.values()}
    pairs = [pair for pair in pairs if pair['quote'] == 'USDT' and pair['base'] in perpetual_bases]
   
 
    context = Context.get_instance()
    context.market_data_service = market_data_service
    

    is_live = get_settings('trade')['live_mode']
    if is_live:
        exchanges = CryptoUtil.create_exchanges(['binance', 'okx'])
        exchange_1 =  exchanges['binance']
        exchange_1.load_markets()   
        exchange_2 = exchanges['okx']
        exchange_2.load_markets()
        hedge_exchange = exchanges['binance']
        hedge_exchange.load_markets()
    else:
        exchanges = CryptoUtil.create_sandbox_exchanges(['binance', 'okx'], 'spot')
        exchange_1 = exchanges['binance']
        exchange_1.load_markets()
        exchange_2 = exchanges['okx']
        exchange_2.load_markets()
        hedge_exchange = CryptoUtil.create_sandbox_exchanges(['okx'], 'swap')['okx']
        hedge_exchange.load_markets()

        # 对模拟环境再过滤一次
        currencies_binance = list(exchange_1.markets.keys())
        pairs = [pair for pair in pairs if pair['symbol_a'] in currencies_binance]
        currencies_okx = list(exchange_2.markets.keys())
        pairs = [pair for pair in pairs if pair['symbol_b'] in currencies_okx]

        hedge_exchange = hedge_exchange
        perpetual_markets = CryptoUtil.get_perpetual_markets(exchange=hedge_exchange)
        pairs = [pair for pair in pairs if CryptoUtil.convert_symbol_to_contract(hedge_exchange, pair['symbol_a']) in perpetual_markets]
   
      # 初始化数据结构
    pair_data = {}
    for pair in pairs:
        symbol_a = pair['symbol_a']
        symbol_b = pair['symbol_b']
        if symbol_a != symbol_b:
            # 过滤掉交易所货币代码不一致的货币对
            continue

        symbol = symbol_a
        symbol_hedge = CryptoUtil.convert_symbol_to_contract(hedge_exchange, symbol)

        pair_key = symbol_a
        pair_data[pair_key] = {
            'trading_limits_a': CryptoUtil.get_trading_limits(exchange_1, symbol),
            'trading_limits_b': CryptoUtil.get_trading_limits(exchange_2, symbol),
            'trading_limits_hedge': CryptoUtil.get_trading_limits(hedge_exchange, symbol_hedge),
            'price_a': None,
            'price_b': None,
            'price_hedge': None,
            'spread': 0,
            'comment': '',
            'timestamp': 0
        }

    context.pair_data = pair_data
    context.perpetual_markets = perpetual_markets

    # 创建策略实例，传入Context
    strategy = ExchangeArbitrageStrategy(
        exchange_1=exchange_1, 
        exchange_2=exchange_2, 
        hedge_exchange=hedge_exchange, 
        pair_data=pair_data,
        context=context
    )
    
    Logger.info("跨交易所套利监控程序已启动")

    try:
        # 运行策略
        asyncio.run(strategy.execute())
    except KeyboardInterrupt:
        Logger.info("用户中断程序")
    except Exception as e:
        Logger.error(f"程序异常: {str(e)}")
    finally:
        # 停止策略和MarketDataService
        strategy.stop()
        market_data_service.stop()
        Logger.info("程序已终止")
        print("程序已终止")



if __name__ == "__main__":
    run()



    
   