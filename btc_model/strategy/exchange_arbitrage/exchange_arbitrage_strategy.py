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

from btc_model.core.util.log_util import Logger
from btc_model.strategy.exchange_arbitrage.pairs_monitor import PairsMonitor
from btc_model.core.common.object import PositionData
from btc_model.trade.position_holder import PositionHolder
from btc_model.setting.setting import get_settings
from btc_model.core.util.crypto_util import CryptoUtil
from btc_model.core.market.market_data_service import MarketDataService
from btc_model.core.common.context import Context


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
    max_amount: float   # 策略最大资金量
    max_trading_pairs: int      # 策略最大在途货币对数量
    max_amount_per_pair: float  # 策略单个货币对最大资金量
    min_amount_per_pair: float  # 策略单个货币对最小资金量

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
                 exchange_1: ccxtpro.Exchange, 
                 exchange_2: ccxtpro.Exchange, 
                 hedge_exchange: ccxtpro.Exchange,
                 pairs: list,
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

        self.exchange_1 = exchange_1
        self.exchange_2 = exchange_2
        self.hedge_exchange = hedge_exchange
        self.pairs = pairs

        # 获取或创建上下文实例
        self.context = context if context else Context()
        self.market_data_service: MarketDataService = self.context.market_data_service

  
        # 初始化数据结构
        self.pair_data = {}
        for pair in pairs:
            pair_key = (pair['symbol_a'], pair['symbol_b'])
            self.pair_data[pair_key] = {
                'price_a': None,
                'price_b': None,
                'spread': 0,
                'comment': '',
                'timestamp': 0
            }
        
        # 启动监控线程
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_arbitrage_opportunities, daemon=True)
        self.monitor_thread.start()
        
        Logger.info(f"跨交易所套利策略初始化完成，监控 {len(pairs)} 个交易对")
    
    def _subscribe_market_data(self):
        """
        订阅交易对的行情数据
        """
        spot_symbols_to_watch = set()
        swap_symbols_to_watch = set()
        # 收集所有需要订阅的交易对
        for pair in self.pairs:
            symbol_a = pair['symbol_a']
            symbol_b = pair['symbol_b']
            spot_symbols_to_watch.add(symbol_a)
            spot_symbols_to_watch.add(symbol_b)
            
            # 添加合约交易对
            contract_symbol = CryptoUtil.convert_symbol_to_contract(self.hedge_exchange, symbol_a)
            swap_symbols_to_watch.add(contract_symbol)
        
        # 订阅所有交易对的订单簿
        for symbol in spot_symbols_to_watch:
            if symbol in [pair['symbol_a'] for pair in self.pairs]:
                self.market_data_service.subscribe_orderbook('exchange_1', symbol)
            if symbol in [pair['symbol_b'] for pair in self.pairs]:
                self.market_data_service.subscribe_orderbook('exchange_2', symbol)

        for symbol in swap_symbols_to_watch:
            self.market_data_service.subscribe_orderbook('hedge_exchange', symbol)
            self.market_data_service.subscribe_funding_rate('hedge_exchange', symbol)
        
        Logger.info(f"已订阅 {len(spot_symbols_to_watch)} 个现货交易对的市场数据")
        Logger.info(f"已订阅 {len(swap_symbols_to_watch)} 个合约交易对的市场数据")
    
    def _monitor_arbitrage_opportunities(self):
        """监控套利机会"""
        while self.is_running:
            try:
                for pair in self.pairs:
                    pair_key = (pair['symbol_a'], pair['symbol_b'])
                    self.update_pair_data(pair_key)
                    self.calculate_spread(pair_key)
                
                time.sleep(1)  # 每秒检查一次
            except Exception as e:
                Logger.error(f"监控套利机会异常: {str(e)}")
                time.sleep(5)  # 出错后等待5秒再重试
    
    def update_pair_data(self, pair_key):
        """更新交易对数据"""
        try:
            # 获取交易所1的订单簿数据
            orderbook_a = self.market_data_service.get_orderbook('exchange_1', pair_key[0])
            if orderbook_a['bids'] and orderbook_a['asks'] and self.market_data_service.is_data_fresh('orderbook', 'exchange_1', pair_key[0]):
                self.pair_data[pair_key]['price_a'] = {
                    'bid': orderbook_a['bids'][0][0],
                    'ask': orderbook_a['asks'][0][0]
                }
            
            # 获取交易所2的订单簿数据
            orderbook_b = self.market_data_service.get_orderbook('exchange_2', pair_key[1])
            if orderbook_b['bids'] and orderbook_b['asks'] and self.market_data_service.is_data_fresh('orderbook', 'exchange_2', pair_key[1]):
                self.pair_data[pair_key]['price_b'] = {
                    'bid': orderbook_b['bids'][0][0],
                    'ask': orderbook_b['asks'][0][0]
                }
            
            # 更新时间戳
            self.pair_data[pair_key]['timestamp'] = int(time.time() * 1000)
        except Exception as e:
            Logger.error(f"更新交易对数据异常: {pair_key}, 错误: {str(e)}")
    
    def calculate_spread(self, pair_key):
        """带校验的价差计算"""
        data = self.pair_data[pair_key]
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
                if spread > 0.001:  
                    self.trigger_arbitrage(pair_key)
        except (TypeError, ZeroDivisionError, KeyError) as e:
            pair_key_str = '-'.join(pair_key) if isinstance(pair_key, tuple) else pair_key
            Logger.error(f"价差计算错误 {pair_key_str}: {str(e)}")
    
    def trigger_arbitrage(self, pair_key):
        """触发套利信号"""
        data = self.pair_data[pair_key]
        pair_key_str = '-'.join(pair_key) if isinstance(pair_key, tuple) else pair_key
        
        Logger.info(
            f"套利信号触发: {pair_key_str:<15} 价差: {data['spread']:>6.2%}, {data['comment']}"
        )
        
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
        
        # 订阅市场数据
        self._subscribe_market_data()
        
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


def setup_exchanges():

    """设置交易所实例"""
    # 初始化币安交易所
    setting = get_settings('cex.sandbox.binance.spot')
    apikey = setting['apikey']
    secretkey = setting['secretkey']


    params_1 = {
        'enableRateLimit': True,
        'proxies': {
            'http': get_settings('common')['proxies'].get('http', None),                  
            'https': get_settings('common')['proxies'].get('https', None),
        },
        'apiKey': apikey,          
        'secret': secretkey,       
        'options': {
            'defaultType': 'spot',  # 可选：'spot', 'margin', 'future'
        },
        'aiohttp_proxy': get_settings('common')['proxies'].get('http', None),
        'ws_proxy': get_settings('common')['proxies'].get('http', None)
    }

    exchange_1 = ccxt.binance(params_1)
    exchange_1.set_sandbox_mode(True)

     # 初始化 OKX 交易所
    setting = get_settings('cex.sandbox.okx')
    apikey = setting['apikey']
    secretkey = setting['secretkey']
    passphrase = setting['passphrase']

    params_2 = {
        'enableRateLimit': True,
        'proxies': {
            'http': get_settings('common')['proxies'].get('http', None),                   
            'https': get_settings('common')['proxies'].get('https', None),  
        },
        'apiKey': apikey,          
        'secret': secretkey,  
        'password': passphrase,     
        'options': {
            'defaultType': 'spot',
        },
        'aiohttp_proxy': get_settings('common')['proxies'].get('http', None),
        'ws_proxy': get_settings('common')['proxies'].get('http', None)
    }
    exchange_2 = ccxt.okx(params_2)
    exchange_2.set_sandbox_mode(True)


    # 初始化币安合约交易所
    setting = get_settings('cex.sandbox.binance.swap')
    apikey = setting['apikey']
    secretkey = setting['secretkey']

    params_hedge = {
        'enableRateLimit': True,
        'proxies': {
            'http': get_settings('common')['proxies'].get('http', None),                  
            'https': get_settings('common')['proxies'].get('https', None),
        },
        'apiKey': apikey,          
        'secret': secretkey,       
        'options': {
            'defaultType': 'swap',  # 可选：'spot', 'margin', 'future'
        },
        'aiohttp_proxy': get_settings('common')['proxies'].get('http', None),
        'ws_proxy': get_settings('common')['proxies'].get('http', None)
    }
    exchange_hedge = ccxt.binance(params_hedge)
    exchange_hedge.set_sandbox_mode(True)

   
    return {
        'exchange_1': exchange_1,
        'exchange_2': exchange_2,
        'exchange_hedge': exchange_hedge,
    }

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

def test_exchange_arbitrage_strategy():
    exchanges = setup_exchanges()
    exchange_1 = exchanges['exchange_1']
    exchange_2 = exchanges['exchange_2']
    exchange_hedge = exchanges['exchange_hedge']

    pairs = load_pairs()
    
    swap_symbols = CryptoUtil.get_perpetual_markets(exchange=hedge_exchange)
    swap_bases = {market_data['base'] for market_data in swap_symbols.values()}
    pairs = [pair for pair in pairs if pair['quote'] == 'USDT' and pair['base'] in swap_bases]
    

    # 初始化市场数据管理器
    md = MarketDataService()
    # 添加交易所
    for exchange_id, exchange in exchanges.items():
        md.add_exchange(exchange_id, exchange)

    # 订阅行情数据
    spot_symbols_to_watch = ['LSK/USDT']
    swap_symbols_to_watch = ['LSK/USDT:USDT']
    
    # 订阅现货订单簿
    for symbol in spot_symbols_to_watch:
        md.subscribe_orderbook('exchange_1', symbol)
        md.subscribe_orderbook('exchange_2', symbol)
        

    # 订阅合约订单簿和资金费率
    for symbol in swap_symbols_to_watch:
        md.subscribe_orderbook('exchange_hedge', symbol)
        md.subscribe_funding_rate('exchange_hedge', symbol)
    
    # 启动市场数据订阅
    md.start()

    Logger.info("等待行情数据开始流入...")

    time.sleep(30)

    
    context = Context.get_instance()
    context.market_data_service = md
    




    try:
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        Logger.info("程序被用户中断")
    finally:
        # 停止市场数据订阅
        md.stop()
        Logger.info("程序已退出")

if __name__ == "__main__":
    pairs = load_pairs()





    exchanges = setup_exchanges()
    exchange_1 = exchanges['exchange_1']
    exchange_2 = exchanges['exchange_2']
    hedge_exchange = exchanges['exchange_hedge']

    # 获取永续合约市场信息
    swap_symbols = CryptoUtil.get_perpetual_markets(exchange=hedge_exchange)
    swap_bases = {market_data['base'] for market_data in swap_symbols.values()}
    pairs = [pair for pair in pairs if pair['quote'] == 'USDT' and pair['base'] in swap_bases]

   
    # 初始化Context单例
    context = Context.get_instance()
    
    # 初始化MarketDataService并设置到Context中
    market_data_service = MarketDataService()
    
    # 添加交易所到MarketDataService
    market_data_service.add_exchange('exchange_1', exchange_1)
    market_data_service.add_exchange('exchange_2', exchange_2)
    market_data_service.add_exchange('hedge_exchange', hedge_exchange)
    
    # 启动MarketDataService
    market_data_service.start()
    
    # 设置到Context中
    context.market_data_service = market_data_service

    # 创建策略实例，传入Context
    strategy = ExchangeArbitrageStrategy(
        exchange_1=exchange_1, 
        exchange_2=exchange_2, 
        hedge_exchange=hedge_exchange, 
        pairs=pairs,
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
