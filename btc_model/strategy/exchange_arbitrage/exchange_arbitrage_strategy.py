import pandas as pd
import threading
import queue
import asyncio
from typing import NamedTuple, Dict, Tuple, Optional
import ccxt
import time
import ccxt.pro as ccxtpro

from btc_model.core.util.log_util import Logger
from btc_model.strategy.exchange_arbitrage.pairs_monitor import PairsMonitor
from btc_model.core.common.object import PositionData
from btc_model.trade.position_holder import PositionHolder
from btc_model.setting.setting import get_settings



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
                 pairs: list,
                 settings=None
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

        self.position_holder1 = PositionHolder()
        self.position_holder2 = PositionHolder()

        self.pair_monitor = PairsMonitor(self.exchange_1, self.exchange_2, self.pairs)
        self.pair_monitor.add_arbitrage_opportunity_event(self.on_arbitrage_opportunity)

        self.lock = threading.Lock()
        # 通过队列保存接收到的套利机会，并通过其他线程处理队列中的数据
        self.queue = queue.Queue()
        # 套利机会事件列表
        self.on_arbitrage_event_list = []
        self.websocket_manager = None

        # # 套利参数设置
        # self.settings = settings or {}
        # self.TRADE_FEE = self.settings.get('TRADE_FEE', 0.001)  # 交易手续费，默认0.1%
        # self.TRANSFER_FEE = self.settings.get('TRANSFER_FEE', 0.001)  # 转账手续费，默认0.1%
        # self.MIN_PROFIT = self.settings.get('MIN_PROFIT', 0.005)  # 最小利润率，默认0.5%
        # self.MAX_SLIPPAGE = self.settings.get('MAX_SLIPPAGE', 0.002)  # 最大滑点，默认0.2%
        # self.TRADE_AMOUNT = self.settings.get('TRADE_AMOUNT', 0.01)  # 交易数量，默认0.01BTC
        # self.MAX_RETRIES = self.settings.get('MAX_RETRIES', 3)  # 最大重试次数
   

    # def start(self):
    #     try:
    #         t = threading.Thread(target=self.run, daemon=True)
    #         t.start()
    #         return True
    #     except Exception as e:
    #         logger.error(f"启动ExchangeArbitrageStrategy失败,错误信息:{e}", exc_info=True)
    #         return False


    async def run_monitor(self):
        
        
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
            spot_balance1 = self.exchange_1.fetch_balance()
            if spot_balance1:
                for currency, balance in spot_balance1['total'].items():
                    if balance > 0:
                        self.position_holder1.add_position(
                            f"{currency}/USDT", 
                            balance,
                            0  # 现货没有entry_price概念
                        )

            # 获取永续合约持仓
            futures_positions1 = self.exchange_1.fetch_positions()
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
            spot_balance2 = self.exchange_2.fetch_balance()
            if spot_balance2:
                for currency, balance in spot_balance2['total'].items():
                    if balance > 0:
                        self.position_holder2.add_position(
                            f"{currency}/USDT", 
                            balance,
                            0  # 现货没有entry_price概念
                        )

            # 获取永续合约持仓
            futures_positions2 = self.exchange_2.fetch_positions()
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

    async def create_arbitrage_position(self, pair_key: tuple, data: dict) -> str:
        """创建套利仓位"""
        try:
            # 获取订单簿数据
            orderbook1 = await self.exchange_1.fetch_order_book(pair_key[0])
            orderbook2 = await self.exchange_2.fetch_order_book(pair_key[1])
            
            # 创建限价单
            order1 = await self.exchange_1.create_limit_buy_order(
                pair_key[0],
                data['amount'],
                orderbook1['asks'][0][0]
            )
            
            order2 = await self.exchange_2.create_limit_sell_order(
                pair_key[1],
                data['amount'],
                orderbook2['bids'][0][0]
            )
            
            # 更新持仓数据
            await self.load_positions()
            
            return order1['id']  # 或返回其他标识
            
        except Exception as e:
            self.logger.error(f"创建套利仓位失败: {e}")
            return None

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
        
        # TODO: 价差出现次数阈值
        # # 计算价差出现次数阈值
        # spread_occurrence = self.strategy_params.spread_occurrence_params
        # if data['spread'] < spread_occurrence.min_spread or data['spread'] > spread_occurrence.max_spread:
        #     return
        
        # # 计算风险控制阈值
        # risk_control = self.strategy_params.risk_control_params
        # if data['spread'] < risk_control.min_percent or data['spread'] > risk_control.max_percent:
        #     return  
        
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

    async def fetch_orderbook(self, exchange: ccxt.Exchange, symbol: str) -> Tuple[Optional[float], Optional[float]]:
        """获取订单簿数据"""
        for _ in range(self.MAX_RETRIES):
            try:
                orderbook = await exchange.fetch_order_book(symbol) if hasattr(exchange, 'fetch_order_book') else exchange.fetch_order_book(symbol)
                if not orderbook['bids'] or not orderbook['asks']:
                    self.logger.warning(f"Empty orderbook for {symbol} on {exchange.id}")
                    return None, None
                    
                bid = orderbook['bids'][0][0]  # 最高买入价
                ask = orderbook['asks'][0][0]  # 最低卖出价
                return bid, ask
            except Exception as e:
                self.logger.error(f"Error fetching orderbook from {exchange.id}: {e}")
                await asyncio.sleep(1)
        return None, None

    async def check_balance(self, exchange: ccxt.Exchange, asset: str, min_amount: float) -> bool:
        """检查账户余额是否足够"""
        try:
            balance = await exchange.fetch_balance() if hasattr(exchange, 'fetch_balance') else exchange.fetch_balance()
            available = balance['free'].get(asset, 0)
            if available < min_amount:
                self.logger.warning(f"Insufficient {asset} balance on {exchange.id}: {available} < {min_amount}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking balance on {exchange.id}: {e}")
            return False

    async def place_order(self, exchange: ccxt.Exchange, symbol: str, side: str, amount: float, price: float) -> bool:
        """下单并验证执行结果"""
        try:
            order = await exchange.create_order(symbol, 'limit', side, amount, price) if hasattr(exchange, 'create_order') else exchange.create_order(symbol, 'limit', side, amount, price)
            self.logger.info(f"Order placed on {exchange.id}: {side} {amount} {symbol} @ {price}")
            
            # 等待订单成交（简单实现，实际需异步处理）
            await asyncio.sleep(2)
            order_status = await exchange.fetch_order(order['id'], symbol) if hasattr(exchange, 'fetch_order') else exchange.fetch_order(order['id'], symbol)
            if order_status['status'] == 'closed':
                self.logger.info(f"Order executed successfully on {exchange.id}: {order_status['filled']} filled")
                return True
            else:
                self.logger.warning(f"Order not fully executed on {exchange.id}: {order_status['status']}")
                return False
        except Exception as e:
            self.logger.error(f"Error placing order on {exchange.id}: {e}")
            return False

    async def calculate_arbitrage(self, pair_key):
        """计算套利机会并返回方向"""
        data = self.pair_data[pair_key]
        
        try:
            if not data['price_a'] or not data['price_b']:
                return 0, 0, "no_opportunity"
                
            # 计算 a买b卖 的套利机会
            profit_a_to_b = (data['price_b']['bid'] * (1 - self.TRADE_FEE)) - (data['price_a']['ask'] * (1 + self.TRADE_FEE)) - (self.TRANSFER_FEE * data['price_a']['ask'])
            
            # 计算 b买a卖 的套利机会
            profit_b_to_a = (data['price_a']['bid'] * (1 - self.TRADE_FEE)) - (data['price_b']['ask'] * (1 + self.TRADE_FEE)) - (self.TRANSFER_FEE * data['price_b']['ask'])
            
            # 计算套利方向和利润
            if profit_a_to_b > profit_b_to_a and profit_a_to_b > self.MIN_PROFIT:
                data['spread'] = profit_a_to_b / data['price_a']['ask']
                data['comment'] = (
                    f'【{self.exchange_a_name}】 买入 {data["price_a"]["ask"]}, '
                    f'【{self.exchange_b_name}】 卖出 {data["price_b"]["bid"]}'
                )
                return profit_a_to_b, data['price_a']['ask'], f"{self.exchange_a_name}_to_{self.exchange_b_name}"
            elif profit_b_to_a > self.MIN_PROFIT:
                data['spread'] = profit_b_to_a / data['price_b']['ask']
                data['comment'] = (
                    f'【{self.exchange_b_name}】 买入 {data["price_b"]["ask"]}, '
                    f'【{self.exchange_a_name}】 卖出 {data["price_a"]["bid"]}'
                )
                return profit_b_to_a, data['price_b']['ask'], f"{self.exchange_b_name}_to_{self.exchange_a_name}"
            
            # 没有套利机会
            data['spread'] = max(profit_a_to_b, profit_b_to_a) / min(data['price_a']['ask'], data['price_b']['ask'])
            data['comment'] = "无套利机会"
            return 0, 0, "no_opportunity"
        except (TypeError, ZeroDivisionError, KeyError) as e:
            pair_key_str = '-'.join(pair_key) if isinstance(pair_key, tuple) else pair_key
            self.logger.error(f"套利计算错误 {pair_key_str}: {str(e)}")
            return 0, 0, "error"

    async def execute_arbitrage(self, pair_key, direction):
        """执行套利交易"""
        data = self.pair_data[pair_key]
        pair_str = '-'.join(pair_key) if isinstance(pair_key, tuple) else pair_key
        
        # 根据方向确定买卖交易所
        if direction == f"{self.exchange_a_name}_to_{self.exchange_b_name}":
            buy_exchange = self.exchange_1
            sell_exchange = self.exchange_2
            buy_price = data['price_a']['ask']
            sell_price = data['price_b']['bid']
        elif direction == f"{self.exchange_b_name}_to_{self.exchange_a_name}":
            buy_exchange = self.exchange_2
            sell_exchange = self.exchange_1
            buy_price = data['price_b']['ask']
            sell_price = data['price_a']['bid']
        else:
            self.logger.warning(f"Invalid arbitrage direction: {direction}")
            return False
            
        # 检查滑点
        current_buy_bid, current_buy_ask = await self.fetch_orderbook(buy_exchange, pair_str)
        current_sell_bid, current_sell_ask = await self.fetch_orderbook(sell_exchange, pair_str)
        
        if current_buy_ask is None or current_sell_bid is None:
            self.logger.warning("Failed to fetch current orderbook, aborting trade.")
            return False
            
        if (abs(current_buy_ask - buy_price) / buy_price > self.MAX_SLIPPAGE or
            abs(current_sell_bid - sell_price) / sell_price > self.MAX_SLIPPAGE):
            self.logger.warning("Excessive slippage detected, aborting trade.")
            return False

        # 获取交易对的基础货币和计价货币
        base_currency, quote_currency = pair_key
        
        # 检查余额
        if not await self.check_balance(buy_exchange, quote_currency, self.TRADE_AMOUNT * buy_price):
            return False
        if not await self.check_balance(sell_exchange, base_currency, self.TRADE_AMOUNT):
            return False

        # 下单：买入
        buy_success = await self.place_order(buy_exchange, pair_str, 'buy', self.TRADE_AMOUNT, buy_price)
        if not buy_success:
            return False

        # 下单：卖出
        sell_success = await self.place_order(sell_exchange, pair_str, 'sell', self.TRADE_AMOUNT, sell_price)
        if not sell_success:
            self.logger.warning("Sell order failed, manual intervention required.")
            return False

        self.logger.info(
            f"套利交易成功: {pair_str} {direction} 价差: {data['spread']:.2%}, {data['comment']}"
        )
        return True

    async def trigger_arbitrage(self, pair_key):
        """触发套利信号"""
        profit, buy_price, direction = await self.calculate_arbitrage(pair_key)
        
        if direction != "no_opportunity" and direction != "error":
            self.logger.info(
                f"套利信号触发: {pair_key} 价差: {self.pair_data[pair_key]['spread']:.2%}, {self.pair_data[pair_key]['comment']}"
            )
            
            # 如果启用了自动交易，执行套利
            if self.settings.get('AUTO_TRADE', False):
                await self.execute_arbitrage(pair_key, direction)

    def check_spread_occurrence(self, pair_key: tuple, data: dict) -> bool:
        """检查价差是否满足出现次数和持续时间要求"""
        params = self.strategy_params.spread_occurrence_params
        
        # 检查价差是否在有效范围内
        if not (params.min_spread <= data['spread'] <= params.max_spread):
            return False
        
        # 获取历史价差数据
        now = time.time()
        window_start = now - params.duration
        
        # 从缓存中获取该交易对的历史价差记录
        spread_history = self.spread_history.get(pair_key, [])
        
        # 清理过期数据
        spread_history = [(t, s) for t, s in spread_history if t >= window_start]
        
        # 添加当前价差
        spread_history.append((now, data['spread']))
        self.spread_history[pair_key] = spread_history
        
        # 统计有效价差出现次数
        valid_occurrences = sum(
            1 for _, spread in spread_history 
            if params.min_spread <= spread <= params.max_spread
        )
        
        # 如果要求连续
        if params.consecutive_required:
            consecutive_count = 0
            max_consecutive = 0
            for _, spread in spread_history:
                if params.min_spread <= spread <= params.max_spread:
                    consecutive_count += 1
                    max_consecutive = max(max_consecutive, consecutive_count)
                else:
                    consecutive_count = 0
            return max_consecutive >= params.min_occurrences
        
        # 不要求连续，只检查总次数
        return valid_occurrences >= params.min_occurrences


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
    # 对冲交易所
    hedge_exchange = ccxtpro.binance(params)

    strategy = ExchangeArbitrageStrategy(exchange_1=exchange_1, 
                                         exchange_2=exchange_2, 
                                         hedge_exchange=hedge_exchange, 
                                         pairs=pairs
                                         )
    Logger.info("跨交易所套利监控程序已启动")
    strategy.execute()
    print("程序已终止")
