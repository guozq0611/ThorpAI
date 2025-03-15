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
                 hedge_exchange: ccxt.Exchange,
                 context: Context
                 ):
        self.strategy = strategy
        self.exchange_1 = exchange_1
        self.exchange_2 = exchange_2
        self.hedge_exchange = hedge_exchange

        self.market_data_service = context.market_data_service
 
        
        self.active_orders: Dict[str, ArbitrageOrder | ArbitrageHedgeOrder] = {}
        self.lock = threading.Lock()
        self._start_monitor()
    
    def create_position(self, pair_key, data):
        pass

    def create_arbitrage_position(self, pair_key: tuple, data: dict) -> Optional[str]:
        """创建套利仓位"""
        
        # 使用锁来防止竞态条件
        with self.lock:
            # 如果仓位已经存在，则不创建
            if pair_key in self.active_orders:
                Logger.warning(f"仓位已存在，不创建仓位: {pair_key}")
                return None
                
            # 在锁内添加到活跃订单列表，防止其他线程重复创建
            position_id = self._generate_position_id()
            self.active_orders[pair_key] = {
                'position_id': position_id,
                'status': 'creating',
                'data': data,
                'created_at': time.time()
            }
        
        # 锁外执行耗时操作，避免长时间持有锁
        try:
            # 这里执行创建仓位的具体逻辑
            # ...
            
            # 更新仓位状态
            with self.lock:
                self.active_orders[pair_key]['status'] = 'active'
            
            Logger.info(f"创建套利仓位成功: {pair_key}, position_id: {position_id}")
            return position_id
        except Exception as e:
            # 如果创建失败，从活跃订单中移除
            with self.lock:
                self.active_orders.pop(pair_key, None)
            
            Logger.error(f"创建套利仓位失败: {pair_key}, 错误: {str(e)}")
            return None

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
        hedge_exchange=hedge_exchange,
        context=context
    )

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
        md.stop()
        Logger.info("程序已终止")
        print("程序已终止")

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
