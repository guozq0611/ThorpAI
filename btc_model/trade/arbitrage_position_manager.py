from typing import Dict, List, Optional
import threading
import time
import ccxt
import ccxt.pro as ccxtpro
import asyncio
import traceback
from typing import Union
from ccxt.base.errors import RequestTimeout, NetworkError

from btc_model.core.common.const import OrderStatus, EventType
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
from btc_model.trade.position_holder import PositionHolder
from btc_model.core.common.const import PositionDirection, Exchange, Direction  
from collections import defaultdict
from btc_model.core.engine.event_engine import EventEngine, Event

class ArbitragePositionManager(PositionManager):
    """
    套利仓位管理器
    """
    def __init__(self,
                 exchange_1: ccxt.Exchange, 
                 exchange_2: ccxt.Exchange, 
                 exchange_hedge: ccxt.Exchange,
                 context: Context
                 ):
        self.exchange_1 = exchange_1
        self.exchange_2 = exchange_2
        self.exchange_hedge = exchange_hedge

        self.market_data_service: MarketDataService = context.market_data_service
 
        self.position_holder = PositionHolder()
        self.active_orders: Dict[str, ArbitrageOrder | ArbitrageHedgeOrder] = {}
        # 当前正在交易中的货币对, 为了防止重复创建仓位, 如果int > 0 表示有正在进行中的货币对
        self.active_symbol_ids: Dict[str, int] = defaultdict(int)
       
        self.lock = threading.Lock()
        self._start_monitor()
        
        # 初始化事件引擎
        self.event_engine = EventEngine()
        self.event_engine.start()
        
        # 注册事件处理函数
        self.event_engine.register(EventType.ON_CANCEL, self.on_order_cancel)
        self.event_engine.register(EventType.ON_ORDER, self.on_order_update)
    
    def create_position(self, pair_key, data):
        pass

    def create_arbitrage_position(self, symbol_id: str, data: dict) -> Optional[str]:
        """创建套利仓位"""

        # 如果仓位已经存在，则不创建
        with self.lock:
            if self.active_symbol_ids[symbol_id] > 0:
                Logger.warning(f"已存在正在进行的套利仓位, 不创建新仓位: {symbol_id}")
                return None

        max_retries = 3
        retry_delay = min(30, 2 ** 0)  # 指数退避，最大30秒
        
        for attempt in range(max_retries):
            try:
                # 获取订单簿数据（使用市场数据管理器）
                spot_orderbook_1 = self.market_data_service.get_orderbook('exchange_1', symbol_id)
                spot_orderbook_2 = self.market_data_service.get_orderbook('exchange_2', symbol_id)

                contract_symbol = CryptoUtil.convert_symbol_to_contract(self.exchange_hedge, symbol_id)
                swap_orderbook = self.market_data_service.get_orderbook('exchange_hedge', contract_symbol)
                
                # 检查行情数据是否有效和新鲜
                if (not spot_orderbook_1['asks'] or 
                    not spot_orderbook_2['asks'] or 
                    not swap_orderbook['bids'] or
                    not self.market_data_service.is_data_fresh('orderbook', 'exchange_1', symbol_id) or
                    not self.market_data_service.is_data_fresh('orderbook', 'exchange_2', symbol_id) or
                    not self.market_data_service.is_data_fresh('orderbook', 'exchange_hedge', contract_symbol)):
                    
                    Logger.warning(f"行情数据不完整或不新鲜，尝试直接获取行情 (尝试 {attempt + 1}/{max_retries})")
                    # 如果订阅的行情不可用，回退到直接获取
                    spot_orderbook_1 = self.market_data_service.get_orderbook('exchange_1', symbol_id)
                    spot_orderbook_2 = self.market_data_service.get_orderbook('exchange_2', symbol_id)
                    swap_orderbook = self.market_data_service.get_orderbook('exchange_hedge', contract_symbol)

                # 现货多头买入，按卖1价下单
                spot_price_1 = spot_orderbook_1['asks'][0][0] 
                spot_price_2 = spot_orderbook_2['asks'][0][0] 

                # 合约空头卖出，按买1价下单
                swap_price = swap_orderbook['bids'][0][0]

                # 记录行情数据用于日志
                Logger.info(
                    f"获取行情成功 | "
                    f"exchange_1: {symbol_id} 卖1价: {spot_price_1} | "
                    f"exchange_2: {symbol_id} 卖1价: {spot_price_2} | "
                    f"exchange_hedge: {contract_symbol} 买1价: {swap_price}"
                )
                
                # 创建限价单
                spot_order_1 = self.exchange_1.create_limit_buy_order(
                    symbol_id, 
                    data['amount'],
                    spot_price_1
                )
                spot_order_1 = self.exchange_1.fetch_order(spot_order_1['id'], symbol_id)

                spot_order_2 = self.exchange_2.create_limit_buy_order(
                    symbol_id,
                    data['amount'],
                    spot_price_2
                )
                spot_order_2 = self.exchange_2.fetch_order(spot_order_2['id'], symbol_id)

                swap_order = self.exchange_hedge.create_limit_sell_order(
                    contract_symbol,
                    data['amount'],
                    swap_price
                )
                swap_order = self.exchange_hedge.fetch_order(swap_order['id'], contract_symbol)
                
                spot_order_1 = CryptoUtil.convert_order_data_from_ccxt(self.exchange_1, spot_order_1)
                spot_order_2 = CryptoUtil.convert_order_data_from_ccxt(self.exchange_2, spot_order_2)
                swap_order = CryptoUtil.convert_order_data_from_ccxt(self.exchange_hedge, swap_order)
                
                # 记录订单
                order_id = SerialnoUtil.create_serial_no(prefix='arb_', length=20)
                arbitrage_hedge_order = ArbitrageHedgeOrder(
                    order_id=order_id,
                    symbol_id=symbol_id
                )

                arbitrage_hedge_order.put_leg('spot_1', spot_order_1)
                arbitrage_hedge_order.put_leg('spot_2', spot_order_2)
                arbitrage_hedge_order.put_leg('swap', swap_order)

                with self.lock:
                    self.active_orders[order_id] = arbitrage_hedge_order
                    self.active_symbol_ids[symbol_id] += 1
                    
                return order_id
                
            except RequestTimeout as e:
                error_msg = (
                    f"创建套利仓位超时 (尝试 {attempt + 1}/{max_retries}) | "
                    f"交易所: {self.exchange_2.id} | "
                    f"交易对: {symbol_id} | "
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
                    f"交易对: {symbol_id} | "
                    f"错误: {str(e)}"
                )
                raise
                
            except Exception as e:
                Logger.error(
                    f"创建套利仓位失败 | "
                    f"交易对: {symbol_id} | "
                    f"数量: {data.get('amount')} | "
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

    def _check_order_status(self, order_id: str, order: Union[ArbitrageOrder, ArbitrageHedgeOrder]):
        """检查订单状态并处理"""
        try:
 
            spot_order_1, spot_order_2, swap_order = order.get_last_leg()
            # 获取订单最新状态
            if spot_order_1.is_active:
                exhange_order = self.exchange_1.fetch_order(id=spot_order_1.order_id, symbol=order.symbol_id)
                updated_order = CryptoUtil.convert_order_data_from_ccxt(self.exchange_1, exhange_order)
                
                spot_order_1.volume_traded = updated_order.volume_traded
                spot_order_1.status = updated_order.status

            
            if spot_order_2.is_active:
                exhange_order = self.exchange_2.fetch_order(id=spot_order_2.order_id, symbol=order.symbol_id)
                updated_order = CryptoUtil.convert_order_data_from_ccxt(self.exchange_2, exhange_order)
                
                spot_order_2.volume_traded = updated_order.volume_traded
                spot_order_2.status = updated_order.status

            if isinstance(order, ArbitrageHedgeOrder) and swap_order.is_active:
                exhange_order = self.exchange_hedge.fetch_order(
                    id=swap_order.order_id, 
                    symbol=CryptoUtil.convert_symbol_to_contract(self.exchange_hedge, order.symbol_id)
                    )
                updated_order = CryptoUtil.convert_order_data_from_ccxt(self.exchange_hedge, exhange_order)
                
                swap_order.volume_traded = updated_order.volume_traded
                swap_order.status = updated_order.status
                
            # # 检查是否需要撤单
            # if time.time() - order.create_time > self.strategy_params.common_params.order_timeout:
            #     self._cancel_and_adjust(order_id, order)
            #     return
                
            # # 处理残腿
            # if abs(order.leg_spot_1.volume_traded + order.leg_spot_2.volume_traded - order.leg_swap.volume_traded) > 0.0001:
            #     self._handle_imbalance(order_id, order)

            # if order.status == OrderStatus.is_finished:
            #     self.active_orders.pop(order_id)
            #     Logger.info(f"套利订单 {order_id} 完全成交")
            # else:
            #     Logger.info(f"套利订单 {order_id} 未完全成交")


        except Exception as e:
            Logger.error(f"检查订单状态失败: {e}")
            Logger.error(traceback.format_exc())

    def _cancel_and_adjust(self, order_id: str, order: Union[ArbitrageOrder, ArbitrageHedgeOrder]):
        """撤单并追单"""
        try:
            # 撤销未完成的订单
            if order.leg_spot_1 and order.leg_spot_1.volume_traded < order.amount:
                self.exchange_1.cancel_order(order.leg_spot_1.order_id)
                
            if order.leg_spot_2 and order.leg_spot_2.volume_traded < order.amount:
                self.exchange_2.cancel_order(order.leg_spot_2.order_id)
                
            if order.leg_swap and order.leg_swap.volume_traded < order.amount:
                self.exchange_hedge.cancel_order(order.leg_swap.order_id)
                
            # 重新下单（剩余未成交部分）
            remaining_amount = order.amount - max(order.leg_spot_1.volume_traded, order.leg_spot_2.volume_traded, order.leg_swap.volume_traded)
            if remaining_amount > 0:
                # 以更激进的价格重新下单
                self.create_arbitrage_position(
                    order.symbol_id,
                    {'amount': remaining_amount}
                )
                
        except Exception as e:
            Logger.error(f"撤单调整失败: {e}")
            Logger.error(traceback.format_exc())

    def _handle_imbalance(self, order_id: str, order: Union[ArbitrageOrder, ArbitrageHedgeOrder]):
        """处理残腿"""
        try:
            # 计算现货和合约的成交差额
            spot_order_1_filled = order.leg_spot_1.volume_traded * (1 if order.leg_spot_1.direction == Direction.BUY else -1)
            spot_order_2_filled = order.leg_spot_2.volume_traded * (1 if order.leg_spot_2.direction == Direction.BUY else -1)

            if isinstance(order, ArbitrageHedgeOrder):
                swap_order_filled = order.leg_swap.volume_traded * (-1)
            else:
                swap_order_filled = 0
                
            imbalance = spot_order_1_filled + spot_order_2_filled + swap_order_filled
            
            if abs(imbalance) < 0.0001:
                return  # 差额很小，不需要处理
                
            if not isinstance(order, ArbitrageOrder):
                # 跨交易所现货的两条腿，一买一卖
                if imbalance > 0:
                    # 买单多了
                    if order.leg_spot_1.direction == Direction.SELL:
                        new_order = self.exchange_1.create_market_sell_order(
                            order.symbol_id,
                            abs(imbalance)
                        )
                        order.leg_spot_1.order_id = id
                    Logger.info(f"补充现货多单: {order.symbol_id}, 数量: {abs(imbalance)}")
                else:
                    self.exchange_2.create_market_sell_order(
                        order.symbol_id,
                        abs(imbalance)
                    )
                    Logger.info(f"补充现货空单: {order.symbol_id}, 数量: {abs(imbalance)}")
            elif isinstance(order, ArbitrageHedgeOrder) and imbalance > 0:  # 现货多成交
                # 补充合约空单
                contract_symbol = CryptoUtil.convert_symbol_to_contract(self.exchange_hedge, arbitrage_order.symbol_id)
                self.exchange_hedge.create_market_sell_order(
                    contract_symbol,
                    abs(imbalance),
                    params={"positionSide": "SHORT"}  # 尝试使用双向持仓模式
                )
                Logger.info(f"补充合约空单: {contract_symbol}, 数量: {abs(imbalance)}")
            else:  # 合约多成交
                # 补充现货多单
                self.exchange_2.create_market_buy_order(
                    arbitrage_order.symbol_id,
                    abs(imbalance)
                )
                Logger.info(f"补充现货多单: {arbitrage_order.symbol_id}, 数量: {abs(imbalance)}")
        except Exception as e:
            Logger.error(f"处理残腿失败: {e}")
            Logger.error(traceback.format_exc())

    def on_order_cancel(self, event: Event):
        """
        处理订单取消事件
        
        Args:
            event: 事件对象，data 是 OrderData 对象
        """
        order_data = event.data
        print(f"订单已取消: {order_data.order_id}, 交易对: {order_data.symbol}")
        
        # 在这里处理订单取消后的逻辑
        # 例如，重新下单、调整策略等
    
    def on_order_update(self, event: Event):
        """
        处理订单更新事件
        
        Args:
            event: 事件对象，data 是 OrderData 对象
        """
        order_data = event.data
        
        # 检查订单是否被取消
        if order_data.status == OrderStatus.CANCELLED:
            # 触发取消事件
            self.event_engine.put_event(EventType.ON_CANCEL, order_data)
    
    def cancel_order(self, order: PositionData):
        """
        取消订单
        
        Args:
            order: 要取消的订单
        """
        try:
            # 获取对应的交易所
            if order.exchange == Exchange.XXX:
                exchange = self.exchange_1
            else:
                exchange = self.exchange_2
            
            # 调用交易所API取消订单
            exchange.cancel_order(order.order_id, order.symbol)
            
            # 更新订单状态
            order.status = OrderStatus.CANCELLED
            
            # 触发取消事件
            self.event_engine.put_event(EventType.ON_CANCEL, order)
            
            return True
        except Exception as e:
            print(f"取消订单失败: {e}")
            return False
    
    def __del__(self):
        """
        析构函数，确保事件引擎停止
        """
        if hasattr(self, 'event_engine'):
            self.event_engine.stop()

def test_arbitrage_position_manager():
    from btc_model.strategy.exchange_arbitrage.exchange_arbitrage_strategy import setup_exchanges, load_pairs
    
    exchanges = setup_exchanges()
    exchange_1 = exchanges['exchange_1']
    exchange_2 = exchanges['exchange_2']
    exchange_hedge = exchanges['exchange_hedge']

    pairs = load_pairs()
    # pairs = [pair for pair in pairs if pair['base'] == 'LSK']


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


    max_retries = 10
    attempt = 0
    retry_delay = min(30, 2 ** 0)  # 指数退避，最大30秒

    # 等待数据开始流入
    Logger.info("等待行情数据开始流入...")
    while True:
        spot_orderbook_1 = md.get_orderbook('exchange_1', 'LSK/USDT')
        spot_orderbook_2 = md.get_orderbook('exchange_2', 'LSK/USDT')
        swap_orderbook = md.get_orderbook('exchange_hedge', 'LSK/USDT:USDT')
        
        # 检查行情数据是否有效和新鲜
        if (not spot_orderbook_1['asks'] or 
            not spot_orderbook_2['asks'] or 
            not swap_orderbook['bids'] or
            not md.is_data_fresh('orderbook', 'exchange_1', 'LSK/USDT') or
            not md.is_data_fresh('orderbook', 'exchange_2', 'LSK/USDT') or
            not md.is_data_fresh('orderbook', 'exchange_hedge', 'LSK/USDT:USDT')):
            
            Logger.warning(f"行情数据不完整或不新鲜，尝试直接获取行情 (尝试 {attempt + 1}/{max_retries})")

            retry_delay = min(30, 2 ** (attempt + 1))  # 指数退避，最大30秒
            time.sleep(retry_delay) 
            attempt += 1
            if attempt >= max_retries:
                Logger.error("行情数据获取失败，已达到最大重试次数")
                exit(0)

        
        else:
            break
    
    context = Context.get_instance()
    context.market_data_service = md
    
    from btc_model.strategy.exchange_arbitrage.exchange_arbitrage_strategy import StrategyParams
    strategy_params = StrategyParams.from_settings()
    context.strategy_params = strategy_params

    position_manager = ArbitragePositionManager(
        exchange_1=exchange_1,
        exchange_2=exchange_2,
        exchange_hedge=exchange_hedge,
        context=context
    )

    position_manager.create_arbitrage_position('LSK/USDT', {'amount': 10})


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
