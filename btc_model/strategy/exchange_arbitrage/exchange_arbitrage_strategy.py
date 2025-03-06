import pandas as pd
import threading
import queue
import asyncio
from typing import NamedTuple, Dict

import ccxt.pro as ccxtpro
from btc_model.core.util.log_util import Logger
from btc_model.strategy.exchange_arbitrage.pairs_monitor import PairsMonitor
from btc_model.core.common.object import PositionData
from btc_model.core.util.crypto_util import get_position_data

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
    capital_limit_params: CapitalLimitParams
    spread_threshold_params: SpreadThresholdParams
    spread_occurrence_params: SpreadOccurrenceParams
    risk_control_params: RiskControlParams

    @classmethod
    def from_settings(cls) -> 'StrategyParams':
        config = get_settings('strategy.exchange_arbitrage')
        return cls(
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
                 pairs: list
                 ):
        """
        初始化策略
        
        params:
            exchange_1: 交易所1, 用于现货多头仓位的创建
            exchange_2: 交易所2, 用于永续合约空头对冲仓位的创建
            hedge_exchange: 对冲交易所, 用于永续合约空头对冲仓位的创建
            pairs: 货币对列表
        """
        # 从配置文件中获取策略参数
        self.strategy_params = StrategyParams.from_settings()

        self.exchange_1 = exchange_1
        self.exchange_2 = exchange_2
        self.hedge_exchange = hedge_exchange
        self.pairs = pairs

        self.pair_monitor = PairsMonitor(self.exchange_1, self.exchange_2, self.pairs)
        self.pair_monitor.add_arbitrage_opportunity_event(self.on_arbitrage_opportunity)

        self.lock = threading.Lock()
        # 通过队列保存接收到的套利机会，并通过其他线程处理队列中的数据
        self.queue = queue.Queue()
        # 套利机会事件列表
        self.on_arbitrage_event_list = []
        self.websocket_manager = None

    # def start(self):
    #     try:
    #         t = threading.Thread(target=self.run, daemon=True)
    #         t.start()
    #         return True
    #     except Exception as e:
    #         logger.error(f"启动ExchangeArbitrageStrategy失败,错误信息:{e}", exc_info=True)
    #         return False


    async def run_monitor(self):
        await self.exchange_1.load_markets()
        await self.exchange_2.load_markets()

        self.pair_monitor.start()
        
        try:
            while True:
                await asyncio.sleep(1)
        except:
            self.pair_monitor.stop()
            print("监控已停止")
        
    def execute(self):
        try:
            asyncio.run(self.run_monitor())
        except KeyboardInterrupt:
            print("程序已终止")


    def load_positions(self):
        """刷新两个交易所的持仓数据（现货和永续合约）"""
        try:
            # 刷新第一个交易所的持仓数据
            # 获取现货持仓
            spot_balance1 = self.exchange1.fetch_balance()
            if spot_balance1:
                for currency, balance in spot_balance1['total'].items():
                    if balance > 0:
                        self.position_holder1.add_position(
                            f"{currency}/USDT", 
                            balance,
                            0  # 现货没有entry_price概念
                        )

            # 获取永续合约持仓
            futures_positions1 = self.exchange1.fetch_positions()
            if futures_positions1:
                for position in futures_positions1:
                    if float(position['contracts']) != 0:
                        self.position_holder1.add_position(
                            position['symbol'],
                            float(position['contracts']),
                            float(position['entryPrice'])
                        )

            # 刷新第二个交易所的持仓数据
            # 获取现货持仓
            spot_balance2 = self.exchange2.fetch_balance()
            if spot_balance2:
                for currency, balance in spot_balance2['total'].items():
                    if balance > 0:
                        self.position_holder2.add_position(
                            f"{currency}/USDT", 
                            balance,
                            0  # 现货没有entry_price概念
                        )

            # 获取永续合约持仓
            futures_positions2 = self.exchange2.fetch_positions()
            if futures_positions2:
                for position in futures_positions2:
                    if float(position['contracts']) != 0:
                        self.position_holder2.add_position(
                            position['symbol'],
                            float(position['contracts']),
                            float(position['entryPrice'])
                        )

            self.logger.info("持仓数据刷新成功")

        except Exception as e:
            self.logger.error(f"刷新持仓数据失败: {str(e)}")
            raise

    def send_order(self, order):
        pass

    def cancel_order(self, order):
        pass

    def create_arbitrage_position(self, pair_key, data):
        """创建套利底仓（现货多头 + 合约空头）"""
        # 创建现货多头持仓
        self.exchange_1.create_market_buy_order(pair_key[0], data['amount'])
        # 创建永续合约空头对冲仓位
        self.exchange_2.create_market_sell_order(pair_key[1], data['amount'])   
        # 更新持仓数据
        self.load_positions()

    def close_arbitrage_position(self, pair_key, data):
        """
        关闭套利底仓（现货多头 + 合约空头）
        """
        # 关闭现货多头持仓
        self.exchange_1.create_market_sell_order(pair_key[0], data['amount'])
        # 关闭永续合约空头对冲仓位
        self.exchange_2.create_market_buy_order(pair_key[1], data['amount'])
        # 更新持仓数据
        self.load_positions()

    def update_arbitrage_position(self, pair_key, data):
        """
        更新套利底仓（现货多头 + 合约空头）
        """
        # 更新现货多头持仓
        self.exchange_1.create_market_buy_order(pair_key[0], data['amount'])
        # 更新永续合约空头对冲仓位
        self.exchange_2.create_market_sell_order(pair_key[1], data['amount'])
        # 更新持仓数据
        self.load_positions()



    def on_arbitrage_opportunity(self, pair_key, data):
        """处理套利机会""" 
        Logger.info(f"套利信号触发: {'-'.join(pair_key) :<10} 价差: {data['spread']:>6.2%}, {data['comment']}")
        # 计算各种阈值 
        # 计算资金限制阈值
        capital_limit = self.strategy_params.capital_limit_params
        if self.position_holder1.total_position_value > capital_limit.max_amount:
            return
        if self.position_holder2.total_position_value > capital_limit.max_amount:
            return
        
        # 计算价差阈值
        spread_threshold = self.strategy_params.spread_threshold_params
        if data['spread'] < spread_threshold.min_percent or data['spread'] > spread_threshold.max_percent:
            return
        
        # 计算价差出现次数阈值
        spread_occurrence = self.strategy_params.spread_occurrence_params
        if data['spread'] < spread_occurrence.min_percent or data['spread'] > spread_occurrence.max_percent:
            return
        
        # 计算风险控制阈值
        risk_control = self.strategy_params.risk_control_params
        if data['spread'] < risk_control.min_percent or data['spread'] > risk_control.max_percent:
            return  
        
        # 将套利机会添加到队列中
        self.queue.put(data)

    # async def start(self):
    #     # 启动 WebSocket 服务器
    #     import uvicorn
    #     uvicorn.run(app, host="0.0.0.0", port=8000)

    def get_exchange_a_price(self):
        # 实现获取交易所A价格的方法
        pass

    def get_exchange_b_price(self):
        # 实现获取交易所B价格的方法
        pass

    def get_price_diff(self):
        # 实现获取价差的方法
        pass

    def get_diff_percentage(self):
        # 实现获取价差百分比的方法
        pass


if __name__ == "__main__":
    from btc_model.setting.setting import get_settings

    params = {
        'enableRateLimit': True,
        'proxies': {
            'http': get_settings('common')['proxies']['http'],
            'https': get_settings('common')['proxies']['https'],
        },
        'aiohttp_proxy': get_settings('common')['proxies']['http'],
        'ws_proxy': get_settings('common')['proxies']['http']
    }


    try:
        pairs_df = pd.read_csv("normal_pairs.csv")
        pairs_dif = pairs_df[pairs_df['quote'] == "USDT"]
        required_cols = ['base', 'quote', 'symbol_a', 'symbol_b']
        if not all(col in pairs_df.columns for col in required_cols):
            raise ValueError("CSV文件缺少必要列")
        pairs = pairs_df[required_cols].to_dict('records')
    except Exception as e:
        print(f"配置加载失败: {str(e)}")
        exit(1)

    # 交易所初始化
    exchange_1 = ccxtpro.binance(params)
    exchange_2 = ccxtpro.okx(params)
    
    strategy = ExchangeArbitrageStrategy(exchange_1, exchange_2, pairs)
    Logger.info("跨交易所套利监控程序已启动")
    strategy.execute()
    print("程序已终止")
