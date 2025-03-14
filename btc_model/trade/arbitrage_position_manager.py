from typing import Dict, List, Optional
import threading
import time
import ccxt
import ccxt.pro as ccxtpro
import asyncio
import traceback
from ccxt.base.errors import RequestTimeout, NetworkError

from btc_model.core.common.const import OrderStatus
from btc_model.core.common.object import PositionData
from btc_model.core.util.log_util import Logger
from btc_model.core.util.serialno_util import SerialnoUtil
from btc_model.core.util.crypto_util import CryptoUtil
from btc_model.core.util.crypto_hedge_util import CryptoHedgeUtil
from btc_model.core.market.market_data_service import MarketDataService
from btc_model.trade.position_manager import PositionManager
from btc_model.trade.arbitrage_order import ArbitrageOrder
from btc_model.trade.arbitrage_hedge_order import ArbitrageHedgeOrder
from btc_model.strategy.exchange_arbitrage.exchange_arbitrage_strategy import ExchangeArbitrageStrategy
from btc_model.core.common.context import Context


class ArbitragePositionManager(PositionManager):
    """
    套利仓位管理器
    """
    def __init__(self,
                 strategy: ExchangeArbitrageStrategy,
                 exchange_1: ccxt.Exchange, 
                 exchange_2: ccxt.Exchange, 
                 hedge_exchange: ccxt.Exchange
                 ):
        self.strategy = strategy
        self.exchange_1 = exchange_1
        self.exchange_2 = exchange_2
        self.hedge_exchange = hedge_exchange
        
        # 获取市场数据管理器实例
        self.md = MarketDataService()
        
        # 添加交易所到市场数据管理器
        self.md.add_exchange('exchange_1', exchange_1)
        self.md.add_exchange('exchange_2', exchange_2)
        self.md.add_exchange('hedge_exchange', hedge_exchange)
        
        # 订阅交易对的行情数据
        self._subscribe_market_data()
        
        # 启动市场数据订阅
        self.md.start()
        
        self.active_orders: Dict[str, ArbitrageOrder | ArbitrageHedgeOrder] = {}
        self.lock = threading.Lock()
        self._start_monitor()
    
    def _subscribe_market_data(self):
        """
        订阅交易对的行情数据
        """
        # 获取策略中的交易对
        pairs = self.strategy.pairs
        symbols_to_watch = set()
        
        # 收集所有需要订阅的交易对
        for pair in pairs:
            symbol_a = pair['symbol_a']
            symbol_b = pair['symbol_b']
            symbols_to_watch.add(symbol_a)
            symbols_to_watch.add(symbol_b)
            
            # 添加合约交易对
            contract_symbol = CryptoUtil.convert_symbol_to_contract(self.hedge_exchange, symbol_b)
            symbols_to_watch.add(contract_symbol)
        
        # 订阅所有交易对的订单簿
        for symbol in symbols_to_watch:
            if symbol.endswith(':USDT'):  # 合约交易对
                self.md.subscribe_orderbook('hedge_exchange', symbol)
                self.md.subscribe_funding_rate('hedge_exchange', symbol)
            else:  # 现货交易对
                if symbol in [pair['symbol_a'] for pair in self.strategy.pairs]:
                    self.md.subscribe_orderbook('exchange_1', symbol)
                if symbol in [pair['symbol_b'] for pair in self.strategy.pairs]:
                    self.md.subscribe_orderbook('exchange_2', symbol)
        
        Logger.info(f"已订阅 {len(symbols_to_watch)} 个交易对的市场数据")

    def create_position(self, pair_key, data):
        pass

    def create_arbitrage_position(self, pair_key: tuple, data: dict) -> Optional[str]:
        """创建套利仓位"""
        max_retries = 3
        retry_delay = min(30, 2 ** 0)  # 指数退避，最大30秒
        
        for attempt in range(max_retries):
            try:
                # 获取订单簿数据（使用市场数据管理器）
                spot_orderbook_1 = self.market_data.get_orderbook('exchange_1', pair_key[0])
                spot_orderbook_2 = self.market_data.get_orderbook('exchange_2', pair_key[1])

                contract_symbol = CryptoUtil.convert_symbol_to_contract(self.hedge_exchange, pair_key[1])
                swap_orderbook = self.market_data.get_orderbook('hedge_exchange', contract_symbol)
                
                # 检查行情数据是否有效和新鲜
                if (not spot_orderbook_1['asks'] or 
                    not spot_orderbook_2['asks'] or 
                    not swap_orderbook['bids'] or
                    not self.market_data.is_data_fresh('orderbook', 'exchange_1', pair_key[0]) or
                    not self.market_data.is_data_fresh('orderbook', 'exchange_2', pair_key[1]) or
                    not self.market_data.is_data_fresh('orderbook', 'hedge_exchange', contract_symbol)):
                    
                    Logger.warning(f"行情数据不完整或不新鲜，尝试直接获取行情 (尝试 {attempt + 1}/{max_retries})")
                    # 如果订阅的行情不可用，回退到直接获取
                    spot_orderbook_1 = self.md.get_orderbook(pair_key[0])
                    spot_orderbook_2 = self.md.get_orderbook(pair_key[1])
                    swap_orderbook = self.md.get_orderbook(contract_symbol)

                # 现货多头买入，按卖1价下单
                spot_price_1 = spot_orderbook_1['asks'][0][0] 
                spot_price_2 = spot_orderbook_2['asks'][0][0] 

                # 合约空头卖出，按买1价下单
                swap_price = swap_orderbook['bids'][0][0] + 0.0005

                # 记录行情数据用于日志
                Logger.info(
                    f"获取行情成功 | "
                    f"{pair_key[0]} 卖1价: {spot_price_1} | "
                    f"{pair_key[1]} 卖1价: {spot_price_2} | "
                    f"{contract_symbol} 买1价: {swap_orderbook['bids'][0][0]}"
                )
                
                # 创建限价单
                # spot_order_1 = self.exchange_1.create_limit_buy_order(
                #     pair_key[0], 
                #     data['amount'],
                #     spot_price_1
                # )
                spot_order_2 = self.exchange_2.create_limit_buy_order(
                    pair_key[1],
                    data['amount'],
                    spot_price_2
                )
                
                # 添加持仓方向参数
                try:
                    # 尝试使用双向持仓模式
                    swap_order = self.hedge_exchange.create_limit_sell_order(
                        contract_symbol,
                        data['amount'],
                        swap_price,
                        params={"positionSide": "SHORT"}  # 指定为空头持仓
                    )
                except Exception as e:
                    # 如果失败，尝试使用单向持仓模式
                    if "position side does not match" in str(e):
                        Logger.warning(f"尝试使用单向持仓模式下单: {contract_symbol}")
                        swap_order = self.hedge_exchange.create_limit_sell_order(
                            contract_symbol,
                            data['amount'],
                            swap_price
                        )
                    else:
                        # 其他错误，直接抛出
                        raise
                
                # 记录订单
                order_id = SerialnoUtil.create_serial_no(prefix='arb_', length=20)
                arb_order = ArbitrageHedgeOrder(
                    id=order_id,
                    leg_spot_1=None,  # 这里需要修改，因为没有 spot_order_1
                    leg_spot_2=spot_order_2,
                    leg_swap=swap_order
                )

                with self.lock:
                    self.active_orders[order_id] = arb_order
                    
                return order_id
                
            except RequestTimeout as e:
                error_msg = (
                    f"创建套利仓位超时 (尝试 {attempt + 1}/{max_retries}) | "
                    f"交易所: {self.exchange_2.id} | "
                    f"交易对: {pair_key[1]} | "
                    f"URL: {e.url if hasattr(e, 'url') else 'unknown'}"
                )
                if attempt < max_retries - 1:
                    Logger.warning(f"{error_msg} | 将在 {retry_delay} 秒后重试")
                    time.sleep(retry_delay)
                    retry_delay = min(30, 2 ** (attempt + 1))  # 指数退避，最大30秒
                else:
                    Logger.error(f"{error_msg} | 已达到最大重试次数")
                    raise
                    
            except NetworkError as e:
                Logger.error(
                    f"网络错误 | "
                    f"交易所: {self.exchange_2.id} | "
                    f"交易对: {pair_key[1]} | "
                    f"错误: {str(e)}"
                )
                raise
                
            except Exception as e:
                Logger.error(
                    f"创建套利仓位失败 | "
                    f"交易对: {pair_key} | "
                    f"数量: {data.get('amount')} | "
                    f"价格: {data.get('price_a')}/{data.get('price_b')} | "
                    f"错误类型: {e.__class__.__name__} | "
                    f"错误信息: {str(e)} | "
                    f"堆栈跟踪:\n{traceback.format_exc()}"
                )
                raise

    def _start_monitor(self):
        """启动订单监控线程"""
        def monitor_orders():
            while True:
                try:
                    with self.lock:
                        for order_id, arb_order in list(self.active_orders.items()):
                            self._check_order_status(order_id, arb_order)
                    time.sleep(0.5)  # 每500ms检查一次
                except Exception as e:
                    self.strategy.logger.error(f"订单监控异常: {e}")
                    
        threading.Thread(target=monitor_orders, daemon=True).start()

    def _check_order_status(self, order_id: str, arb_order: ArbitrageOrder):
        """检查订单状态并处理"""
        try:
            # 获取订单最新状态
            if arb_order.leg_spot_1 and hasattr(arb_order.leg_spot_1, 'order_id'):
                spot_order_1 = self.exchange_1.fetch_order(arb_order.leg_spot_1.order_id)
                arb_order.leg_spot_1.filled = spot_order_1['filled']
            
            spot_order_2 = self.exchange_2.fetch_order(arb_order.leg_spot_2.order_id)
            swap_order = self.hedge_exchange.fetch_order(arb_order.leg_swap.order_id)
            
            # 更新成交量
            arb_order.leg_spot_2.filled = spot_order_2['filled']
            arb_order.leg_swap.filled = swap_order['filled']
            
            # 检查是否需要撤单
            if time.time() - arb_order.create_time > arb_order.timeout:
                self._cancel_and_adjust(order_id, arb_order)
                return
                
            # 处理残腿
            if abs(arb_order.spot_filled - arb_order.futures_filled) > 0.0001:
                self._handle_imbalance(order_id, arb_order)
                
            # 检查是否完全成交
            if arb_order.spot_filled >= arb_order.amount and arb_order.futures_filled >= arb_order.amount:
                arb_order.status = OrderStatus.FILLED
                self.active_orders.pop(order_id)
                Logger.info(f"套利订单 {order_id} 完全成交")
                
        except Exception as e:
            Logger.error(f"检查订单状态失败: {e}")
            Logger.error(traceback.format_exc())

    def _cancel_and_adjust(self, order_id: str, arb_order: ArbitrageOrder):
        """撤单并追单"""
        try:
            # 撤销未完成的订单
            if arb_order.leg_spot_1 and arb_order.leg_spot_1.filled < arb_order.amount:
                self.exchange_1.cancel_order(arb_order.leg_spot_1.order_id)
                
            if arb_order.leg_spot_2.filled < arb_order.amount:
                self.exchange_2.cancel_order(arb_order.leg_spot_2.order_id)
                
            if arb_order.leg_swap.filled < arb_order.amount:
                self.hedge_exchange.cancel_order(arb_order.leg_swap.order_id)
                
            # 重新下单（剩余未成交部分）
            remaining_amount = arb_order.amount - max(arb_order.spot_filled, arb_order.futures_filled)
            if remaining_amount > 0:
                # 以更激进的价格重新下单
                self.create_arbitrage_position(
                    arb_order.pair_key,
                    {'amount': remaining_amount}
                )
                
        except Exception as e:
            Logger.error(f"撤单调整失败: {e}")
            Logger.error(traceback.format_exc())

    def _handle_imbalance(self, order_id: str, arb_order: ArbitrageOrder):
        """处理残腿"""
        try:
            # 计算现货和合约的成交差额
            spot_filled = arb_order.leg_spot_2.filled
            if arb_order.leg_spot_1:
                spot_filled += arb_order.leg_spot_1.filled
                
            futures_filled = arb_order.leg_swap.filled
            imbalance = spot_filled - futures_filled
            
            if abs(imbalance) < 0.0001:
                return  # 差额很小，不需要处理
                
            if imbalance > 0:  # 现货多成交
                # 补充合约空单
                contract_symbol = CryptoUtil.convert_symbol_to_contract(self.hedge_exchange, arb_order.pair_key[1])
                self.hedge_exchange.create_market_sell_order(
                    contract_symbol,
                    abs(imbalance),
                    params={"positionSide": "SHORT"}  # 尝试使用双向持仓模式
                )
                Logger.info(f"补充合约空单: {contract_symbol}, 数量: {abs(imbalance)}")
            else:  # 合约多成交
                # 补充现货多单
                self.exchange_2.create_market_buy_order(
                    arb_order.pair_key[1],
                    abs(imbalance)
                )
                Logger.info(f"补充现货多单: {arb_order.pair_key[1]}, 数量: {abs(imbalance)}")
        except Exception as e:
            Logger.error(f"处理残腿失败: {e}")
            Logger.error(traceback.format_exc())



def test_arbitrage_position_manager():
    from btc_model.strategy.exchange_arbitrage.exchange_arbitrage_strategy import setup_exchanges, load_pairs
    
    exchanges = setup_exchanges()
    exchange_1 = exchanges['exchange_1']
    exchange_2 = exchanges['exchange_2']
    hedge_exchange = exchanges['exchange_hedge']

    pairs = load_pairs()

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

    # 等待数据开始流入
    Logger.info("等待行情数据开始流入...")
    time.sleep(10)
    
    context = Context.get_instance()
    context.market_data_service = md
    
    strategy = ExchangeArbitrageStrategy(exchange_1=exchange_1, 
                                         exchange_2=exchange_2, 
                                         hedge_exchange=hedge_exchange, 
                                         pairs=pairs,
                                         context=context
                                        )

    position_manager = ArbitragePositionManager(
        strategy=strategy,
        exchange_1=exchange_1,
        exchange_2=exchange_2,
        hedge_exchange=hedge_exchange
    )


    try:
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        Logger.info("程序被用户中断")
    finally:
        # 停止市场数据订阅
        md.stop()
        Logger.info("程序已退出")


if __name__ == '__main__':
    test_arbitrage_position_manager()
    
    
    print('-------------------------------------------------------------------------')
