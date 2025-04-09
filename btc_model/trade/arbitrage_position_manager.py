from typing import Dict, List, Optional
import threading
import datetime, time
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
from btc_model.core.util.crypto_util import CryptoUtil, ORDERTYPE_2CCXT, DIRECTION_2CCXT, EXCHANGE_FROM_CCXT, POSITION_SIDE_2CCXT
from btc_model.core.util.crypto_hedge_util import CryptoHedgeUtil
from btc_model.core.market.market_data_service import MarketDataService
from btc_model.trade.position_manager import PositionManager
from btc_model.trade.arbitrage_order import ArbitrageOrder
from btc_model.trade.arbitrage_hedge_order import ArbitrageHedgeOrder
from btc_model.trade.arbitrage_position import ArbitragePosition
from btc_model.core.common.context import Context
from btc_model.trade.position_holder import PositionHolder
from btc_model.core.common.const import PositionSide, Exchange, Direction, Offset, OrderType
from btc_model.core.common.object import OrderData, OrderRequest
from collections import defaultdict
from btc_model.core.engine.event_engine import EventEngine, Event
from btc_model.manager.instance_manager import get_instance

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

        self.context = context
        self.market_data_service: MarketDataService = context.market_data_service
        self.service_manager = context.service_manager

        self.websocket_service = self.service_manager.get_websocket_service()
        if self.websocket_service is None:
            Logger.warning(f"获取WebSocket服务实例失败: {e}，将无法推送订单数据到前端")

        self.perpetual_markets = context.perpetual_markets
        
       
     
        self.active_orders: Dict[str, ArbitrageOrder | ArbitrageHedgeOrder] = {}
        # 当前正在交易中的货币对, 为了防止重复创建仓位, 如果int > 0 表示有正在进行中的货币对
        self.active_symbol_ids: Dict[str, int] = defaultdict(int)

        # 当前正在交易中的套利仓位，key为symbol_id；当仓位建好后，才能进行后续的现货一买一卖
        self.position_holder: Dict[str, ArbitragePosition] = {}

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

    def create_arbitrage_position(self, symbol_id: str, volume: float) -> Optional[str]:
        """创建套利仓位"""

        # 如果仓位已经存在，则不创建
        with self.lock:
            if self.active_symbol_ids[symbol_id] > 0:
                Logger.warning(f"已存在正在进行的套利仓位, 不创建新仓位: {symbol_id}")
                return None
            
            if symbol_id not in self.position_holder:
                self.position_holder[symbol_id] = ArbitragePosition(symbol_id, self.exchange_1, self.exchange_2, self.exchange_hedge)
            # 生成一个本地订单ID（用于套利整体）
            arb_order_id = SerialnoUtil.create_serial_no(prefix='', length=20)

            # 为每个交易腿生成唯一的client_id
            spot_client_id_1 = SerialnoUtil.create_serial_no(prefix='', length=20)  
            spot_client_id_2 = SerialnoUtil.create_serial_no(prefix='', length=20)
            swap_client_id = SerialnoUtil.create_serial_no(prefix='', length=20)

            # 使用新的类方法创建空订单
            spot_order_1 = OrderData.create_empty(
                symbol=symbol_id,
                exchange=EXCHANGE_FROM_CCXT[self.exchange_1.id],
                client_id=spot_client_id_1
            )
            spot_order_1.order_type = OrderType.LIMIT
            spot_order_1.direction = Direction.BUY
            spot_order_1.offset = Offset.OPEN
            spot_order_1.price = 0
            spot_order_1.volume = volume
            spot_order_1.volume_traded = 0
            spot_order_1.status = OrderStatus.NONE
            spot_order_1.datetime = datetime.datetime.now()
            spot_order_1.reference = ""
            spot_order_1.create_time = time.time()

            # 创建现货腿2的初始订单
            spot_order_2 = OrderData.create_empty(
                symbol=symbol_id,
                exchange=EXCHANGE_FROM_CCXT[self.exchange_2.id],
                client_id=spot_client_id_2
            )
            spot_order_2.order_type = OrderType.LIMIT
            spot_order_2.direction = Direction.BUY
            spot_order_2.offset = Offset.OPEN
            spot_order_2.price = 0
            spot_order_2.volume = volume
            spot_order_2.volume_traded = 0
            spot_order_2.status = OrderStatus.NONE
            spot_order_2.datetime = datetime.datetime.now()
            spot_order_2.reference = ""
            spot_order_2.create_time = time.time()

            # 创建合约腿的初始订单
            contract_symbol = CryptoUtil.convert_symbol_to_contract(self.exchange_hedge, symbol_id)
            contract_size = self.exchange_hedge.markets[contract_symbol].get('contractSize', 1)

            swap_order: OrderData = OrderData.create_empty(
                symbol=contract_symbol,
                exchange=EXCHANGE_FROM_CCXT[self.exchange_hedge.id], 
                client_id=swap_client_id
            )
            
            swap_order.order_type = OrderType.LIMIT
            swap_order.direction = Direction.SELL
            swap_order.offset = Offset.OPEN
            swap_order.price = 0
            swap_order.volume = volume * 2 / contract_size
            swap_order.volume_traded = 0
            swap_order.status = OrderStatus.NONE
            swap_order.datetime = datetime.datetime.now()
            swap_order.reference = ""
            swap_order.create_time = time.time()

            arbitrage_hedge_order = ArbitrageHedgeOrder(
                order_id=arb_order_id,
                symbol_id=symbol_id
            )

            arbitrage_hedge_order.put_leg('spot_1', spot_order_1)
            arbitrage_hedge_order.put_leg('spot_2', spot_order_2)
            arbitrage_hedge_order.put_leg('swap', swap_order)
       
            self.active_orders[arb_order_id] = arbitrage_hedge_order
            self.active_symbol_ids[symbol_id] += 1
                

            try:
                contract_symbol = CryptoUtil.convert_symbol_to_contract(self.exchange_hedge, symbol_id)

                spot_price_1 = self.get_price_safely(self.exchange_1, symbol_id, side='ask')
                spot_price_2 = self.get_price_safely(self.exchange_2, symbol_id, side='ask')
                swap_price = self.get_price_safely(self.exchange_hedge, contract_symbol, side='bid')

                if spot_price_1 == 0 or spot_price_2 == 0 or swap_price == 0:
                    Logger.warning(f"检测到行情异常, 不创建套利仓位: {symbol_id}")
                    return None
                
                # 记录行情数据用于日志
                Logger.info(
                    f"获取行情成功 | "
                    f"exchange_1: {symbol_id} 卖1价: {spot_price_1} | "
                    f"exchange_2: {symbol_id} 卖1价: {spot_price_2} | "
                    f"exchange_hedge: {contract_symbol} 买1价: {swap_price}"
                )
                
                # 创建限价单
                updated_spot_order_1 = self.send_spot_order(
                    client_id=spot_client_id_1,
                    exchange=self.exchange_1,
                    symbol_id=symbol_id,
                    volume=volume,
                    price=spot_price_1,
                    order_type=OrderType.LIMIT,
                    direction=Direction.BUY
                )
                if updated_spot_order_1 is not None:
                    spot_order_1.copy_from(updated_spot_order_1)

                updated_spot_order_2 = self.send_spot_order(
                    client_id=spot_client_id_2,
                    exchange=self.exchange_2,
                    symbol_id=symbol_id,
                    volume=volume,
                    price=spot_price_2,
                    order_type=OrderType.LIMIT,
                    direction=Direction.BUY
                )
                if updated_spot_order_2 is not None:
                    spot_order_2.copy_from(updated_spot_order_2)

                updated_swap_order = self.send_swap_order(
                    client_id=swap_client_id,
                    exchange=self.exchange_hedge,
                    symbol_id=contract_symbol,
                    volume=swap_order.volume_remaining,
                    price=swap_price,
                    order_type=OrderType.LIMIT,
                    direction=Direction.SELL,
                    offset=Offset.OPEN
                )
                if updated_swap_order is not None:
                    swap_order.copy_from(updated_swap_order)    
                    
                return arbitrage_hedge_order
                
            except RequestTimeout as e:
                Logger.error(
                    f"创建套利仓位超时 | "
                    f"交易对: {symbol_id} | "
                    f"URL: {e.url if hasattr(e, 'url') else 'unknown'}"
                )
                #raise
            except NetworkError as e:
                Logger.error(
                    f"创建套利仓位失败 | "
                    f"网络错误 | "
                    f"交易对: {symbol_id} | "
                    f"错误: {str(e)}"
                )
                # raise
                
            except Exception as e:
                Logger.error(
                    f"创建套利仓位失败 | "
                    f"交易对: {symbol_id} | "
                    f"数量: {volume} | "
                    f"错误类型: {e.__class__.__name__} | "
                    f"错误信息: {str(e)} | "
                    f"堆栈跟踪:\n{traceback.format_exc()}"
                )
                #TODO: 这里需要监控提醒
                # raise

    def execute_arbitrage(self, symbol_id: str, volume: float, exchange_pair: tuple[Exchange, Exchange]):
        """
        执行一个套利对
        
        Args:
            symbol_id: 币种
            volume: 数量
            exchange_pair: 买入交易所和卖出交易所的元组

        Note:
            1. 两腿的exchange不同, symbol相同, 数量相同、方向相反
            2. 对冲仓位需要预先创建好，这里只是现货的低买高卖
        """
        with self.lock:
            if self.active_symbol_ids[symbol_id] > 0:
                Logger.warning(f"已存在正在进行的套利交易, 不执行新交易: {symbol_id}")
                return None
            
            if symbol_id not in self.position_holder:
                Logger.warning(f"未找到对冲仓位, 不执行套利交易: {symbol_id}")
                return None

            arbitrage_position = self.position_holder[symbol_id]
            # 检查对冲仓位是否已经建仓
            if (arbitrage_position.spot_1_position + arbitrage_position.spot_2_position == 0) or (arbitrage_position.swap_position == 0):
                Logger.warning(f"对冲仓位未建仓, 不执行套利交易: {symbol_id}")
                return None
            
            if arbitrage_position.net_position != 0:
                Logger.warning(f"对冲仓位准备就绪(多头与空头不平衡), 不执行套利交易: {symbol_id}")
                return None
            
            # 设置买入交易所和卖出交易所--》self.exchange_1、self.exchange_2 的买卖方向
            if self.exchange_1.id == exchange_pair[0].id:
               leg_1_direction = Direction.BUY
               leg_2_direction = Direction.SELL
            else:
                leg_1_direction = Direction.SELL
                leg_2_direction = Direction.BUY

            # 检查现货腿1持仓是否足够
            if leg_1_direction == Direction.SELL and arbitrage_position.spot_1_position < volume:
                Logger.warning(f"现货腿1持仓不足, 不执行套利交易: {symbol_id}")
                return None
            
            # 检查现货腿2持仓是否足够
            if leg_2_direction == Direction.SELL and arbitrage_position.spot_2_position < volume:
                Logger.warning(f"现货腿2持仓不足, 不执行套利交易: {symbol_id}")
                return None
           

            # 生成一个本地订单ID（用于套利整体）
            arb_order_id = SerialnoUtil.create_serial_no(prefix='', length=20)

            # 为每个交易腿生成唯一的client_id
            spot_1_client_id = SerialnoUtil.create_serial_no(prefix='', length=20)  
            spot_2_client_id = SerialnoUtil.create_serial_no(prefix='', length=20)

            # 使用新的类方法创建空订单
            spot_1_order = OrderData.create_empty(
                symbol=symbol_id,
                exchange=EXCHANGE_FROM_CCXT[self.exchange_1.id],
                client_id=spot_1_client_id
            )
            spot_1_order.order_type = OrderType.LIMIT
            spot_1_order.direction = leg_1_direction
            spot_1_order.offset = Offset.OPEN
            spot_1_order.price = 0
            spot_1_order.volume = volume
            spot_1_order.volume_traded = 0

            # 创建现货腿2的初始订单
            spot_2_order = OrderData.create_empty(
                symbol=symbol_id,
                exchange=EXCHANGE_FROM_CCXT[self.exchange_2.id],
                client_id=spot_2_client_id
            )
            spot_2_order.order_type = OrderType.LIMIT
            spot_2_order.direction = leg_2_direction
            spot_2_order.offset = Offset.OPEN
            spot_2_order.price = 0
            spot_2_order.volume = volume
            spot_2_order.volume_traded = 0

            arbitrage_order = ArbitrageOrder(
                order_id=arb_order_id,
                symbol_id=symbol_id
            )

            arbitrage_order.put_leg('spot_1', spot_1_order)
            arbitrage_order.put_leg('spot_2', spot_2_order)
       
            self.active_orders[arb_order_id] = arbitrage_order
            self.active_symbol_ids[symbol_id] += 1
                

            try:
                price_1 = self.get_price_safely(self.exchange_1, symbol_id, side='asks' if leg_1_direction == Direction.BUY else 'bids', position=0)
                price_2 = self.get_price_safely(self.exchange_2, symbol_id, side='bids' if leg_2_direction == Direction.BUY else 'asks', position=0)
                  
                # 记录行情数据用于日志
                Logger.info(
                    f"获取行情成功 | "
                    f"exchange_1: {symbol_id} 卖1价: {price_1} | "
                    f"exchange_2: {symbol_id} 买1价: {price_2}"
                )
                
                # 创建限价单
                updated_spot_1_order = self.send_order(
                    client_id=spot_1_client_id,    
                    exchange=self.exchange_1,
                    symbol_id=symbol_id,
                    volume=volume,
                    price=price_1,
                    order_type=OrderType.LIMIT,
                    direction=leg_1_direction
                )

                if updated_spot_1_order is not None:
                    spot_1_order.copy_from(updated_spot_1_order)

                updated_spot_2_order = self.send_order(
                    client_id=spot_2_client_id,
                    exchange=self.exchange_2,
                    symbol_id=symbol_id,
                    volume=volume,
                    price=price_2,
                    order_type=OrderType.LIMIT,
                    direction=leg_2_direction
                )
                if updated_spot_2_order is not None:
                    spot_2_order.copy_from(updated_spot_2_order)

                return arbitrage_order
                
            except RequestTimeout as e:
                Logger.error(
                    f"执行套利交易超时 | "
                    f"交易对: {symbol_id} | "
                    f"URL: {e.url if hasattr(e, 'url') else 'unknown'}"
                )
                #raise
            except NetworkError as e:
                Logger.error(
                    f"执行套利交易失败 | "
                    f"网络错误 | "
                    f"交易对: {symbol_id} | "
                    f"错误: {str(e)}"
                )
                # raise
                
            except Exception as e:
                Logger.error(
                    f"执行套利交易失败 | "
                    f"交易对: {symbol_id} | "
                    f"数量: {volume} | "
                    f"错误类型: {e.__class__.__name__} | "
                    f"错误信息: {str(e)} | "
                    f"堆栈跟踪:\n{traceback.format_exc()}"
                )
                #TODO: 这里需要监控提醒
                # raise

    def _start_monitor(self):
        """启动订单监控线程"""
        def monitor_orders():
            while True:
                try:
                    with self.lock:
                        for order_id, arb_order in list(self.active_orders.items()):
                            self._check_order_status(arb_order)
                    time.sleep(0.5)  # 每500ms检查一次
                except Exception as e:
                    self.strategy.logger.error(f"订单监控异常: {e}")
                    
        threading.Thread(target=monitor_orders, daemon=True).start()

    def _check_order_status(self, arb_order: Union[ArbitrageOrder, ArbitrageHedgeOrder]):
        """检查订单状态并处理"""
        try:
            if isinstance(arb_order, ArbitrageHedgeOrder):
                spot_order_1, spot_order_2, swap_order = arb_order.get_last_leg()
            else:
                spot_order_1, spot_order_2 = arb_order.get_last_leg()

            # 检查订单状态为空或提交中，则查询订单，
            if spot_order_1.status in {OrderStatus.NONE, OrderStatus.SUBMITTING}:
                order_updated = self.query_order_by_client_id(self.exchange_1, spot_order_1.client_id, spot_order_1.symbol)
                # spot_order_1.copy_from(order_updated)
                
                if order_updated is None:
                    if spot_order_1.direction == Direction.BUY:
                        price = self.get_price_safely(self.exchange_1, spot_order_1.symbol, side='ask')
                    else:
                        price = self.get_price_safely(self.exchange_1, spot_order_1.symbol, side='bid')
                    
                    order_updated = self.send_spot_order(
                        client_id=spot_order_1.client_id,
                        exchange=self.exchange_1,
                        symbol_id=spot_order_1.symbol,
                        volume=spot_order_1.volume,
                        price=price,
                        order_type=OrderType.LIMIT,
                        direction=spot_order_1.direction
                    )   
                    if order_updated is not None:
                        spot_order_1.copy_from(order_updated)
            
            if spot_order_2.status in {OrderStatus.NONE, OrderStatus.SUBMITTING}:
                order_updated = self.query_order_by_client_id(self.exchange_2, spot_order_2.client_id, spot_order_2.symbol)
                # spot_order_2.copy_from(order_updated)
                
                if order_updated is None:
                    if spot_order_2.direction == Direction.BUY:
                        price = self.get_price_safely(self.exchange_2, spot_order_2.symbol, side='bid')
                    else:
                        price = self.get_price_safely(self.exchange_2, spot_order_2.symbol, side='ask')

                    order_updated = self.send_spot_order(
                        client_id=spot_order_2.client_id,
                        exchange=self.exchange_2,
                        symbol_id=spot_order_2.symbol,
                        volume=spot_order_2.volume,
                        price=price,
                        order_type=OrderType.LIMIT,
                        direction=spot_order_2.direction
                    )
                    if order_updated is not None:
                        spot_order_2.copy_from(order_updated)

            if isinstance(arb_order, ArbitrageHedgeOrder) and swap_order.status in {OrderStatus.NONE, OrderStatus.SUBMITTING}:
                order_updated = self.query_order_by_client_id(self.exchange_hedge, swap_order.client_id, CryptoUtil.convert_symbol_to_contract(self.exchange_hedge, arb_order.symbol_id))
                # swap_order.copy_from(order_updated)

                if order_updated is None:
                    if swap_order.direction == Direction.BUY:
                        price = self.get_price_safely(self.exchange_hedge, swap_order.symbol, side='bid')
                    else:
                        price = self.get_price_safely(self.exchange_hedge, swap_order.symbol, side='ask')

                    order_updated = self.send_swap_order(
                        client_id=swap_order.client_id,
                        exchange=self.exchange_hedge,
                        symbol_id=swap_order.symbol,
                        volume=swap_order.volume,
                        price=price,
                        order_type=OrderType.LIMIT,
                        direction=swap_order.direction,
                        offset=swap_order.offset
                    )
                    if order_updated is not None:
                        swap_order.copy_from(order_updated)

            # 获取订单最新状态
            if spot_order_1.is_active:
                exhange_order = self.exchange_1.fetch_order(id=spot_order_1.order_id, symbol=spot_order_1.symbol)
                updated_order = CryptoUtil.convert_order_data_from_ccxt(self.exchange_1, exhange_order)
                
                spot_order_1.volume_traded = updated_order.volume_traded
                spot_order_1.status = updated_order.status

            
            if spot_order_2.is_active:
                exhange_order = self.exchange_2.fetch_order(id=spot_order_2.order_id, symbol=spot_order_2.symbol)
                updated_order = CryptoUtil.convert_order_data_from_ccxt(self.exchange_2, exhange_order)
                
                spot_order_2.volume_traded = updated_order.volume_traded
                spot_order_2.status = updated_order.status

            if isinstance(arb_order, ArbitrageHedgeOrder) and swap_order.is_active:
                exhange_order = self.exchange_hedge.fetch_order(
                    id=swap_order.order_id, 
                    symbol=swap_order.symbol
                    )
                updated_order = CryptoUtil.convert_order_data_from_ccxt(self.exchange_hedge, exhange_order)
                
                swap_order.volume_traded = updated_order.volume_traded
                swap_order.status = updated_order.status
                
            # 检查是否需要撤单
            if arb_order.is_active and arb_order.is_timeout(self.context.strategy_params.common_params.order_timeout):
                self._cancel_and_adjust(arb_order)
                return
                
            # 处理残腿
            if arb_order.is_finished:
                self._handle_imbalance(arb_order)

            if arb_order.is_finished and self.active_orders.get(arb_order.order_id) is not None:
                self.active_orders.pop(arb_order.order_id)
                self.active_symbol_ids[arb_order.symbol_id] -= 1

                # 更新对冲仓位的持仓数据
                if isinstance(arb_order, ArbitrageHedgeOrder):
                    arbitrage_position = self.position_holder[arb_order.symbol_id]

                    spot_1_volume_traded = arb_order.get_leg_volume_traded('spot_1')
                    spot_2_volume_traded = arb_order.get_leg_volume_traded('spot_2')
                    swap_volume_traded = arb_order.get_leg_volume_traded('swap')

                    arbitrage_position.spot_1_position += spot_1_volume_traded
                    arbitrage_position.spot_2_position += spot_2_volume_traded
                    arbitrage_position.swap_position += swap_volume_traded
                else:
                    arbitrage_position = self.position_holder[arb_order.symbol_id]

                    spot_1_volume_traded = arb_order.get_leg_volume_traded('spot_1')
                    spot_2_volume_traded = arb_order.get_leg_volume_traded('spot_2')
                    
                    if arb_order.leg_spot_1[-1].direction == Direction.BUY:
                        arbitrage_position.spot_1_position += spot_1_volume_traded
                        arbitrage_position.spot_2_position -= spot_2_volume_traded
                    else:
                        arbitrage_position.spot_1_position -= spot_1_volume_traded
                        arbitrage_position.spot_2_position += spot_2_volume_traded
                    

                Logger.info(f"套利订单 {arb_order.order_id} 完全成交")
            else:
                Logger.info(f"套利订单 {arb_order.order_id} 未完全成交")


        except Exception as e:
            Logger.error(f"检查订单状态失败: {e}")
            Logger.error(traceback.format_exc())

    def _cancel_and_adjust(self, order: Union[ArbitrageOrder, ArbitrageHedgeOrder]):
        """撤单并追单"""
        try:
            if order.is_active:
                if isinstance(order, ArbitrageHedgeOrder):
                    leg_spot_1, leg_spot_2, leg_swap = order.get_last_leg()
                else:
                    leg_spot_1, leg_spot_2 = order.get_last_leg()

                # 撤销未完成的订单
                if leg_spot_1.status == OrderStatus.OPEN and leg_spot_1.volume_traded < leg_spot_1.volume:
                    self.cancel_order(exchange=self.exchange_1, order=leg_spot_1)

                    if leg_spot_1.status != OrderStatus.CANCELLED:
                        Logger.warning(f"现货腿1撤单失败. 订单状态应当为{OrderStatus.CANCELLED}, 当前状态为{leg_spot_1.status}")
                        return

                    volume_remaining = leg_spot_1.volume_remaining
                    if volume_remaining > 0:
                        if len(order.leg_spot_1) > self.context.strategy_params.common_params.order_chase_times:
                            # TODO: 这里需要监控起来，比如发送邮件、拨打电话等，未来不影响效率，应该要使用异步任务来处理
                            Logger.warning(f"现货腿1追单次数超过限制, 不再追单")
                            return
                        
                        if leg_spot_1.direction == Direction.BUY:
                            # 为每个交易腿生成唯一的client_id
                            chase_spot_1_client_id = SerialnoUtil.create_serial_no(prefix='', length=20) 

                            price = self.get_price_safely(self.exchange_1, order.symbol_id, side='ask')
                            chase_order = self.send_spot_order(
                                client_id=chase_spot_1_client_id,
                                exchange=self.exchange_1,
                                symbol_id=order.symbol_id,
                                volume=volume_remaining,
                                price=price,
                                order_type=OrderType.LIMIT,
                                direction=leg_spot_1.direction
                            )
                            if chase_order is not None:
                                order.put_leg('spot_1', chase_order)
                        else:
                            # 为每个交易腿生成唯一的client_id
                            chase_spot_1_client_id = SerialnoUtil.create_serial_no(prefix='', length=20) 

                            price = self.get_price_safely(self.exchange_1, order.symbol_id, side='bid')
                            chase_order = self.send_spot_order(
                                client_id=chase_spot_1_client_id,
                                exchange=self.exchange_1,
                                symbol_id=order.symbol_id,
                                volume=volume_remaining,
                                price=price,
                                order_type=OrderType.LIMIT,
                                direction=leg_spot_1.direction
                            )
                            if chase_order is not None:
                                order.put_leg('spot_1', chase_order)
                    
                if leg_spot_2.status == OrderStatus.OPEN and leg_spot_2.volume_traded < leg_spot_2.volume:
                    self.cancel_order(exchange=self.exchange_2, order=leg_spot_2)

                    if leg_spot_2.status != OrderStatus.CANCELLED:
                        Logger.warning(f"现货腿2撤单失败. 订单状态应当为{OrderStatus.CANCELLED}, 当前状态为{leg_spot_2.status}")
                        return

                    volume_remaining = leg_spot_2.volume_remaining
                    if volume_remaining > 0:
                        if len(order.leg_spot_2) > self.context.strategy_params.common_params.order_chase_times:
                            # TODO: 这里需要监控起来，比如发送邮件、拨打电话等，未来不影响效率，应该要使用异步任务来处理
                            Logger.warning(f"现货腿2追单次数超过限制, 不再追单")
                            return
                        
                        if leg_spot_2.direction == Direction.BUY:
                            chase_spot_2_client_id = SerialnoUtil.create_serial_no(prefix='', length=20) 

                            price = self.get_price_safely(self.exchange_2, order.symbol_id, side='ask')
                            chase_order = self.send_spot_order(
                                client_id=chase_spot_2_client_id,
                                exchange=self.exchange_2,
                                symbol_id=order.symbol_id,
                                volume=volume_remaining,
                                price=price,
                                order_type=OrderType.LIMIT,
                                direction=leg_spot_2.direction
                            )
                            if chase_order is not None:
                                order.put_leg('spot_2', chase_order)
                        else:
                            chase_spot_2_client_id = SerialnoUtil.create_serial_no(prefix='', length=20) 

                            price = self.get_price_safely(self.exchange_2, order.symbol_id, side='bid')
                            chase_order = self.send_spot_order(
                                client_id=chase_spot_2_client_id,
                                exchange=self.exchange_2,
                                symbol_id=order.symbol_id,
                                volume=volume_remaining,
                                price=price,
                                order_type=OrderType.LIMIT,
                                direction=leg_spot_2.direction
                            )
                            if chase_order is not None:
                                order.put_leg('spot_2', chase_order)

                if isinstance(order, ArbitrageHedgeOrder) and leg_swap.status == OrderStatus.OPEN and leg_swap.volume_traded < leg_swap.volume:
                    self.cancel_order(exchange=self.exchange_hedge, order=leg_swap) 

                    if leg_swap.status != OrderStatus.CANCELLED:
                        Logger.warning(f"合约腿撤单失败. 订单状态应当为{OrderStatus.CANCELLED}, 当前状态为{leg_swap.status}")
                        return

                    contract_symbol = CryptoUtil.convert_symbol_to_contract(self.exchange_hedge, order.symbol_id)   
                    volume_remaining = leg_swap.volume_remaining
                    if volume_remaining > 0:    
                        if len(order.leg_swap) > self.context.strategy_params.common_params.order_chase_times:
                            # TODO: 这里需要监控起来，比如发送邮件、拨打电话等，未来不影响效率，应该要使用异步任务来处理
                            Logger.warning(f"合约腿追单次数超过限制, 不再追单")
                            return
                          
                        if leg_swap.direction == Direction.BUY:
                            # 为每个交易腿生成唯一的client_id
                            chase_swap_client_id = SerialnoUtil.create_serial_no(prefix='', length=20) 

                            price = self.get_price_safely(self.exchange_hedge, contract_symbol, side='ask')
                            chase_order = self.send_swap_order(
                                client_id=chase_swap_client_id,
                                exchange=self.exchange_hedge,
                                symbol_id=contract_symbol,
                                volume=volume_remaining,
                                price=price,
                                order_type=OrderType.LIMIT,
                                direction=leg_swap.direction,
                                offset=leg_swap.offset
                            )
                            if chase_order is not None:
                                order.put_leg('swap', chase_order)
                        else:
                            # 为每个交易腿生成唯一的client_id
                            chase_swap_client_id = SerialnoUtil.create_serial_no(prefix='', length=20) 

                            price = self.get_price_safely(self.exchange_hedge, contract_symbol, side='bid')
                            chase_order = self.send_swap_order(
                                client_id=chase_swap_client_id,
                                exchange=self.exchange_hedge,
                                symbol_id=contract_symbol,
                                volume=volume_remaining,
                                price=price,
                                order_type=OrderType.LIMIT,
                                direction=leg_swap.direction,  
                                offset=leg_swap.offset
                            )
                            if chase_order is not None:
                                order.put_leg('swap', chase_order)  

                    
        except Exception as e:
            Logger.error(f"撤单调整失败: {e}")
            Logger.error(traceback.format_exc())

    def _handle_imbalance(self, order: Union[ArbitrageOrder, ArbitrageHedgeOrder]):
        """
        处理残腿
        
        Args:
            order_id: 订单ID
            order: 订单对象

        Note:
            1. order.status必须是finished 才进行残腿处理
            2. 如果是创建对冲仓位, leg1和leg2是现货腿(多头), leg3是合约腿(空头), 一共3腿
            3. 如果是一般套利交易, 只有leg1和leg2两腿, 一买一卖
        """
        try:
            # 计算现货和合约的成交差额
            spot_order_1_filled = order.get_leg_volume_traded('spot_1') * (1 if order.leg_spot_1[-1].direction == Direction.BUY else -1)
            spot_order_2_filled = order.get_leg_volume_traded('spot_2') * (1 if order.leg_spot_2[-1].direction == Direction.BUY else -1)

            if isinstance(order, ArbitrageHedgeOrder):
                swap_order_filled = order.get_leg_volume_traded('swap') * (-1)
                contract_symbol = CryptoUtil.convert_symbol_to_contract(self.exchange_hedge, order.symbol_id)
                contract_size = self.perpetual_markets[contract_symbol]['contract_size']
                swap_order_filled_notional = swap_order_filled * contract_size
            else:
                swap_order_filled = 0
                swap_order_filled_notional = 0

            imbalance = spot_order_1_filled + spot_order_2_filled + swap_order_filled_notional
            
            if abs(imbalance) <= self.context.strategy_params.common_params.order_imbalance_threshold:
                return  # 差额很小，不需要处理
                
            if not isinstance(order, ArbitrageHedgeOrder):
                # 跨交易所现货的两条腿，一买一卖
                if imbalance > 0:
                    # 买单多了，需要补充另一腿的卖出数量
                    if order.is_imbalance_adjust_times_limit(self.context.strategy_params.common_params.imbalance_adjust_times):
                        Logger.warning(f"残腿调整次数超过限制, 不再调整")
                        return

                    new_spot_1_client_id = SerialnoUtil.create_serial_no(prefix='', length=20) 
                    
                    if order.leg_spot_1[-1].direction == Direction.SELL:             
                        price = self.get_price_safely(self.exchange_1, order.symbol_id, 'bid')
                        new_order = self.send_spot_order(
                            client_id=new_spot_1_client_id,
                            exchange=self.exchange_1,
                            symbol_id=order.symbol_id,
                            volume=abs(imbalance),
                            price=price,
                            order_type=OrderType.LIMIT,
                            direction=Direction.SELL
                        )
                        if new_order is not None:
                            order.put_leg('spot_1', new_order)
                    else:
                        price = self.get_price_safely(self.exchange_2, order.symbol_id, 'bid')
                        new_order = self.send_spot_order(
                            client_id=new_spot_1_client_id,
                            exchange=self.exchange_2,
                            symbol_id=order.symbol_id,
                            volume=abs(imbalance),
                            price=price,
                            order_type=OrderType.LIMIT,
                            direction=Direction.SELL
                        )
                        if new_order is not None:
                            order.put_leg('spot_2', new_order)

                    order.imbalance_adjust_times += 1
                    
                    Logger.info(f"补充现货多单: {order.symbol_id}, 数量: {abs(imbalance)}")
                    
                else:
                    # 卖单多了，需要补充另一腿的买入数量
                    if order.is_imbalance_adjust_times_limit(self.context.strategy_params.common_params.imbalance_adjust_times):
                        Logger.warning(f"残腿调整次数超过限制, 不再调整")
                        return

                    new_spot_client_id = SerialnoUtil.create_serial_no(prefix='', length=20) 

                    if order.leg_spot_1[-1].direction == Direction.BUY:
                        price = self.get_price_safely(self.exchange_1, order.symbol_id, 'ask')
                        new_order = self.send_spot_order(
                            client_id=new_spot_client_id,
                            exchange=self.exchange_1,
                            symbol_id=order.symbol_id,
                            volume=abs(imbalance),
                            price=price,
                            order_type=OrderType.LIMIT,
                            direction=Direction.BUY
                        )
                        if new_order is not None:
                            order.put_leg('spot_1', new_order)
                    else:
                        price = self.get_price_safely(self.exchange_2, order.symbol_id, 'ask')
                        new_order = self.send_spot_order(
                            client_id=new_spot_client_id,
                            exchange=self.exchange_2,
                            symbol_id=order.symbol_id,
                            volume=abs(imbalance),
                            price=price,
                            order_type=OrderType.LIMIT,
                            direction=Direction.BUY
                        )   
                        if new_order is not None:
                            order.put_leg('spot_2', new_order)

                    order.imbalance_adjust_times += 1

                    Logger.info(f"补充现货空单: {order.symbol_id}, 数量: {abs(imbalance)}")
            elif isinstance(order, ArbitrageHedgeOrder) and imbalance > 0:  
                # 现货多成交, 需要补充合约空单

                if order.is_imbalance_adjust_times_limit(self.context.strategy_params.common_params.imbalance_adjust_times):
                    Logger.warning(f"残腿调整次数超过限制, 不再调整")
                    return
                
                new_swap_client_id = SerialnoUtil.create_serial_no(prefix='', length=20) 

                contract_symbol = CryptoUtil.convert_symbol_to_contract(self.exchange_hedge, order.symbol_id)
                contract_size = self.perpetual_markets[contract_symbol]['contract_size']
                price = self.get_price_safely(self.exchange_hedge, contract_symbol, 'bid')
                new_order = self.send_swap_order(
                    client_id=new_swap_client_id,
                    exchange=self.exchange_hedge,
                    symbol_id=contract_symbol,
                    volume=abs(imbalance) / contract_size,
                    price=price,
                    order_type=OrderType.LIMIT,
                    direction=Direction.SELL,
                    offset=Offset.OPEN
                )
                if new_order is not None:
                    order.put_leg('swap', new_order)

                order.imbalance_adjust_times += 1

                Logger.info(f"补充合约空单: {contract_symbol}, 数量: {abs(imbalance)}")
            elif isinstance(order, ArbitrageHedgeOrder) and imbalance < 0:  
                # 合约多成交, 需要补充现货多单

                if order.is_imbalance_adjust_times_limit(self.context.strategy_params.common_params.imbalance_adjust_times):
                    Logger.warning(f"残腿调整次数超过限制, 不再调整")
                    return

                price1 = self.get_price_safely(self.exchange_1, order.symbol_id, 'ask')
                price2 = self.get_price_safely(self.exchange_2, order.symbol_id, 'ask')

                if price1 <= price2:
                    new_spot_client_id = SerialnoUtil.create_serial_no(prefix='', length=20) 

                    new_order = self.send_spot_order(
                        client_id=new_spot_client_id,
                        exchange=self.exchange_1,
                        symbol_id=order.symbol_id,
                        volume=abs(imbalance),
                        price=price1,
                        order_type=OrderType.LIMIT,
                        direction=Direction.BUY
                    )
                    if new_order is not None:
                        order.put_leg('spot_1', new_order)

                    order.imbalance_adjust_times += 1
                else:   
                    new_spot_client_id = SerialnoUtil.create_serial_no(prefix='', length=20) 

                    new_order = self.send_spot_order(
                        client_id=new_spot_client_id,
                        exchange=self.exchange_2,
                        symbol_id=order.symbol_id,
                        volume=abs(imbalance),
                        price=price2,
                        order_type=OrderType.LIMIT,
                        direction=Direction.BUY
                    )
                    if new_order is not None:
                        order.put_leg('spot_2', new_order)

                    order.imbalance_adjust_times += 1

                Logger.info(f"补充现货多单: {order.symbol_id}, 数量: {abs(imbalance)}")
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

        # 先在活跃订单中查找并更新
        for arb_id, arb_order in self.active_orders.items():
            for leg_name, leg_order in arb_order.legs.items():
                if leg_order.client_id == order_data.client_id or leg_order.order_id == order_data.order_id:
                    leg_order.copy_from(order_data)
                    # 推送更新后的订单数据到WebSocket
                    self.push_order_to_websocket(leg_order)
                    break
        
        # 如果是仓位的一部分，更新仓位并推送
        for symbol_id, position in self.position_holder.items():
            # 检查是否需要更新仓位数据
            updated = False
            
            # 这里根据实际情况添加仓位更新逻辑
            # 如果仓位有更新，则标记updated = True
            
            if updated:
                # 推送更新后的仓位数据到WebSocket
                self.push_position_to_websocket(position)

    def send_spot_order(
            self,
            client_id: str,
            exchange: Union[ccxt.Exchange, ccxtpro.Exchange], 
            symbol_id: str, 
            volume: float, 
            price: float, 
            order_type: OrderType,
            direction: Direction
            ):
        """
        发送现货订单
        
        Args:
            exchange: 交易所
            symbol_id: 交易对   
            volume: 数量
            price: 价格
            order_type: 订单类型
            direction: 方向
        """
        try:
            # 调用交易所API发送订单
            order = exchange.create_order(
                symbol=symbol_id, 
                type=ORDERTYPE_2CCXT[order_type], 
                side=DIRECTION_2CCXT[direction], 
                amount=volume, 
                price=price,
                params={'clientOrderId': client_id}
            )
            order = exchange.fetch_order(order['id'], symbol_id)     
            order = CryptoUtil.convert_order_data_from_ccxt(exchange, order)
            # 触发取消事件
            self.event_engine.put_event(EventType.ON_ORDER, order)

            # 将订单推送到WebSocket服务
            self.push_order_to_websocket(order)
            
            return order
        except Exception as e:
            Logger.error(f"发送订单失败: {e}")
            return None
        
    def send_swap_order(
            self,
            client_id: str,
            exchange: Union[ccxt.Exchange, ccxtpro.Exchange], 
            symbol_id: str, 
            volume: float, 
            price: float, 
            order_type: OrderType, 
            direction: Direction,
            offset: Offset
            ):
        """
        发送永续合约订单
        
        Args:
            exchange: 交易所
            symbol_id: 交易对
            volume: 数量
            price: 价格
            order_type: 订单类型
            direction: 方向
        """
        try:
            if direction == Direction.BUY and offset == Offset.OPEN:
                pos_side = PositionSide.LONG
            elif direction == Direction.SELL and offset == Offset.OPEN:
                pos_side = PositionSide.SHORT
            elif direction == Direction.BUY and offset == Offset.CLOSE:
                pos_side = PositionSide.SHORT
            elif direction == Direction.SELL and offset == Offset.CLOSE:
                pos_side = PositionSide.LONG
            else:
                raise ValueError(f"无效的偏移量: {offset}")
            
            exchange.set_leverage(1, symbol_id)
                
            # 调用交易所API发送订单
            order = exchange.create_order(
                symbol=symbol_id, 
                type=ORDERTYPE_2CCXT[order_type], 
                side=DIRECTION_2CCXT[direction], 
                amount=volume, 
                price=price,
                params={'clientOrderId': client_id, 
                        'tdMode': 'cross',  # cross - 全仓模式, isolated - 逐仓模式
                        'posSide': POSITION_SIDE_2CCXT[pos_side]   # 持仓方向，'long' 或 'short'
                        }
            )
            order = exchange.fetch_order(order['id'], symbol_id)     
            order = CryptoUtil.convert_order_data_from_ccxt(exchange, order)
            # 设置偏移量, 交易所返回的order里面不含position_direction，这里重新设置
            order.offset = offset
            # 触发取消事件
            self.event_engine.put_event(EventType.ON_ORDER, order)

            # 将订单推送到WebSocket服务
            self.push_order_to_websocket(order)

            return order
        except Exception as e:
            Logger.error(f"发送订单失败: {e}")
            return None

    def query_order_by_client_id(self, exchange: Union[ccxt.Exchange, ccxtpro.Exchange], client_id: str, symbol_id: str):
        """
        查询订单
        """
        try:
            order = exchange.fetch_order(id=None, symbol=symbol_id, params={'clientOrderId': client_id})
            order = CryptoUtil.convert_order_data_from_ccxt(exchange, order)
            return order
        except Exception as e:
            Logger.error(f"查询订单失败: {e}")
            return None
    
    
    def cancel_order(self, exchange: Union[ccxt.Exchange, ccxtpro.Exchange], order: OrderData):
        """
        取消订单
        
        Args:
            order: 要取消的订单
        """
        try:
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

    def get_price_safely(self, exchange: Union[ccxt.Exchange, ccxtpro.Exchange], symbol, side='bid', default=None):
        """
        安全地获取指定交易所和交易对的价格
        
        Args:
            exchange_id: 交易所ID
            symbol: 交易对
            side: 'bids' 或 'asks'
            position: 价格深度位置，0为最佳价格
            default: 当无法获取价格时返回的默认值
            
        Returns:
            float 或 default: 获取到的价格，或默认值
        """
        try:
            bbo = self.market_data_service.get_bbo(exchange.id, symbol)

            if side == 'bid':
                return bbo['bid_price']
            elif side == 'ask':
                return bbo['ask_price']
            else:
                return default
            
        except Exception as e:
            Logger.error(f"获取{side}报价失败: {exchange.id}, {symbol}, 错误: {e}")
            return default

    def get_arbitrage_position(self, symbol_id: str) -> ArbitragePosition:
        """
        获取指定symbol_id的套利仓位
        """
        with self.lock:
            return self.position_holder.get(symbol_id, None)

    def check_margin_requirements(
            self, 
            exchange: ccxt.Exchange, 
            symbol: str, 
            position_size: float, 
            leverage: float = 10, 
            position_type: str = 'long', 
            margin_mode: str = 'isolated'
            ) -> Dict:
        """
        检查合约保证金要求，计算风险指标
        
        Args:
            exchange_id: 交易所ID
            symbol: 交易对名称，例如 'BTC/USDT:USDT'
            position_size: 仓位大小，以基础货币单位计算(如BTC数量)
            leverage: 杠杆倍数，默认为10倍
            position_type: 仓位类型，'long'或'short'
            margin_mode: 保证金模式，'isolated'(逐仓)或'cross'(全仓)
            
        Returns:
            Dict: {
                'required_initial_margin': 初始保证金要求,
                'required_maintenance_margin': 维持保证金要求,
                'available_balance': 可用余额,
                'margin_ratio': 保证金率,
                'liquidation_price': 预估强平价格,
                'margin_safety': 保证金安全度(可用余额/所需保证金),
                'max_position_size': 当前最大可开仓位,
                'error': 错误信息(如有)
            }
        """
        
        try:
            # 获取市场信息
            markets = CryptoUtil.get_perpetual_markets(exchange)
            if symbol not in markets:
                return {
                    'error': f"交易对 {symbol} 不是永续合约或不存在",
                    'margin_safety': 0,
                    'required_initial_margin': 0,
                    'required_maintenance_margin': 0,
                    'available_balance': 0,
                    'margin_ratio': 0,
                    'liquidation_price': 0,
                    'max_position_size': 0
                }
            
            market_info = markets[symbol]
            
            # 获取当前价格
            current_price = 0
            key = f"{exchange.id}:{symbol}"
            
            # 先尝试从我们的缓存中获取价格
            with self.lock:
                current_price = (self.get_price_safely(exchange, symbol, 'bid', 0) + self.get_price_safely(exchange, symbol, 'ask', 0)) / 2

            # 如果缓存中没有，则通过API获取
            if current_price <= 0:
                ticker = exchange.fetch_ticker(symbol)
                current_price = ticker['last'] or ((ticker['bid'] + ticker['ask']) / 2)
            
            # 获取合约乘数
            contract_size = market_info.get('contract_size', 1)
            # 计算仓位价值
            position_value = position_size * current_price * contract_size
            
            # 获取保证金率
            initial_margin_rate = market_info.get('initial_margin', 1/leverage)
            maintenance_margin_rate = market_info.get('maintenance_margin', 0.005)  # 默认0.5%
            
            # 计算所需保证金
            required_initial_margin = position_value * initial_margin_rate
            required_maintenance_margin = position_value * maintenance_margin_rate
            
            # 获取账户余额
            balance = exchange.fetch_balance()
            quote_currency = market_info['quote']
            available_balance = float(balance.get('free', {}).get(quote_currency, 0))
            
            # 计算最大可开仓位
            max_position_size = (available_balance * leverage) / (current_price * contract_size)
            
            # 计算保证金安全度
            margin_safety = available_balance / required_initial_margin if required_initial_margin > 0 else 0
            
            # 计算预估强平价格
            liquidation_price = 0
            if position_type.lower() == 'long':
                # 多仓强平价 = 开仓价 * (1 - 初始保证金率 + 维持保证金率)
                liquidation_price = current_price * (1 - initial_margin_rate + maintenance_margin_rate)
            else:
                # 空仓强平价 = 开仓价 * (1 + 初始保证金率 - 维持保证金率)
                liquidation_price = current_price * (1 + initial_margin_rate - maintenance_margin_rate)
            
            # 构建结果
            result = {
                'required_initial_margin': required_initial_margin,
                'required_maintenance_margin': required_maintenance_margin,
                'available_balance': available_balance,
                'margin_ratio': initial_margin_rate,
                'liquidation_price': liquidation_price,
                'margin_safety': margin_safety,
                'max_position_size': max_position_size,
                'current_price': current_price,
                'contract_size': contract_size,
                'position_value': position_value,
                'error': None
            }
            
            # 检查是否有足够的保证金
            if margin_safety < 1:
                result['warning'] = f"保证金不足，安全度为 {margin_safety:.2f}，需要 {required_initial_margin:.6f} {quote_currency}，可用 {available_balance:.6f} {quote_currency}"
            
            return result
            
        except Exception as e:
            Logger.error(f"检查保证金要求时出错: {str(e)}")
            return {
                'error': f"检查保证金要求时出错: {str(e)}",
                'margin_safety': 0,
                'required_initial_margin': 0,
                'required_maintenance_margin': 0,
                'available_balance': 0,
                'margin_ratio': 0,
                'liquidation_price': 0,
                'max_position_size': 0
            }

    # 向WebSocket服务发送订单数据
    def push_order_to_websocket(self, order_data: OrderData):
        """
        将订单数据推送到WebSocket服务
        """
        if not self.websocket_service:
            return
            
        try:
            # 转换OrderData为前端需要的字典格式
            order_dict = {
                "id": order_data.order_id or order_data.client_id,
                "symbol": order_data.symbol,
                "side": "buy" if order_data.direction == Direction.BUY else "sell",
                "price": order_data.price,
                "volume": order_data.volume,
                "status": self._convert_order_status(order_data.status),
                "exchange": str(order_data.exchange).split(".")[-1],
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "volume_traded": order_data.volume_traded
            }
            
            # 使用asyncio创建一个临时事件循环来执行异步函数
            def add_order_task():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.websocket_service.add_order(order_dict))
                finally:
                    loop.close()
            
            # 在新线程中运行异步任务
            threading.Thread(target=add_order_task).start()
            
        except Exception as e:
            Logger.error(f"推送订单数据到WebSocket服务失败: {e}")
            
    # 向WebSocket服务发送持仓数据
    def push_position_to_websocket(self, position: ArbitragePosition):
        """
        将持仓数据推送到WebSocket服务
        """
        if not self.websocket_service:
            return
            
        try:
            # 为每个腿创建持仓记录
            positions = []
            
            # 现货腿1
            if position.leg_spot_1.volume != 0:
                positions.append({
                    "id": f"{position.symbol_id}_spot1_{int(time.time())}",
                    "symbol": position.symbol_id,
                    "exchange": str(position.exchange_spot_1.id),
                    "volume": position.leg_spot_1.volume,
                    "entryPrice": position.leg_spot_1.price,
                    "currentPrice": position.leg_spot_1.price,  # 可以后续更新
                    "pnl": 0,  # 可以后续计算
                    "status": "open" if position.leg_spot_1.volume > 0 else "closed",
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
            # 现货腿2
            if position.leg_spot_2.volume != 0:
                positions.append({
                    "id": f"{position.symbol_id}_spot2_{int(time.time())}",
                    "symbol": position.symbol_id,
                    "exchange": str(position.exchange_spot_2.id),
                    "volume": position.leg_spot_2.volume,
                    "entryPrice": position.leg_spot_2.price,
                    "currentPrice": position.leg_spot_2.price,  # 可以后续更新
                    "pnl": 0,  # 可以后续计算
                    "status": "open" if position.leg_spot_2.volume > 0 else "closed",
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
            # 合约腿
            if position.leg_swap.volume != 0:
                positions.append({
                    "id": f"{position.symbol_id}_swap_{int(time.time())}",
                    "symbol": position.symbol_hedge,
                    "exchange": str(position.exchange_swap.id),
                    "volume": position.leg_swap.volume,
                    "entryPrice": position.leg_swap.price,
                    "currentPrice": position.leg_swap.price,  # 可以后续更新
                    "pnl": 0,  # 可以后续计算
                    "status": "open" if position.leg_swap.volume != 0 else "closed",
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # 推送每个持仓数据
            for pos in positions:
                def add_position_task(pos_data):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self.websocket_service.add_position(pos_data))
                    finally:
                        loop.close()
                
                threading.Thread(target=add_position_task, args=(pos,)).start()
                
        except Exception as e:
            Logger.error(f"推送持仓数据到WebSocket服务失败: {e}")
    
    def _convert_order_status(self, status: OrderStatus) -> str:
        """
        将内部OrderStatus转换为前端可识别的状态字符串
        """
        status_map = {
            OrderStatus.NONE: "pending",
            OrderStatus.SUBMITTING: "pending",
            OrderStatus.OPEN: "open",
            OrderStatus.EXPIRED: "expired",
            OrderStatus.REJECTED: "rejected",
            OrderStatus.CANCELLED: "canceled",
            OrderStatus.CLOSED: "closed"
        }
        return status_map.get(status, "unknown")

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
            
            Logger.warning(f"行情数据不完整或不新鲜, 尝试 {attempt + 1}/{max_retries}")

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

    position_manager.create_arbitrage_position(symbol_id='LSK/USDT', volume=10)


    try:
        while True:
            arbitrage_position = position_manager.get_arbitrage_position('LSK/USDT')
            if arbitrage_position is not None and \
                arbitrage_position.spot_1_position > 0 and \
                    arbitrage_position.spot_2_position > 0 and \
                        arbitrage_position.swap_position > 0 and \
                            abs(arbitrage_position.net_position) < 1:
                position_manager.execute_arbitrage(symbol_id='LSK/USDT',
                                                   volume=10,
                                                   exchange_pair=(exchange_1, exchange_2)
                                                   )
                
                
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
