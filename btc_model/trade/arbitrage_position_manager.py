from typing import Dict, List, Optional
import threading
import time
import ccxt.pro as ccxtpro

from btc_model.core.common.const import OrderStatus
from btc_model.core.common.object import PositionData
from btc_model.core.util.serialno_util import SerialnoUtil
from btc_model.core.util.crypto_util import CryptoUtil
from btc_model.core.util.crypto_hedge_util import CryptoHedgeUtil
from btc_model.trade.position_manager import PositionManager
from btc_model.trade.arbitrage_order import ArbitrageOrder
from btc_model.trade.arbitrage_hedge_order import ArbitrageHedgeOrder
from btc_model.strategy.exchange_arbitrage.exchange_arbitrage_strategy import ExchangeArbitrageStrategy



class ArbitragePositionManager(PositionManager):
    """
    套利仓位管理器
    """
    def __init__(self,
                 strategy: ExchangeArbitrageStrategy,
                 exchange_1: ccxtpro.Exchange, 
                 exchange_2: ccxtpro.Exchange, 
                 hedge_exchange: ccxtpro.Exchange
                 ):
        self.strategy = strategy
        self.exchange_1 = exchange_1
        self.exchange_2 = exchange_2
        self.hedge_exchange = hedge_exchange

        self.active_orders: Dict[str, ArbitrageOrder | ArbitrageHedgeOrder] = {}
        self.lock = threading.Lock()
        self._start_monitor()
        

    def create_arbitrage_position(self, pair_key: tuple, data: dict) -> str:
        """创建套利底仓"""
        try:
            # 获取当前盘口价格
            # TODO: 暂时通过调用接口获取盘口价格,需要优化
            spot_orderbook_1 = self.exchange_1.fetch_order_book(pair_key[0])
            spot_orderbook_2 = self.exchange_2.fetch_order_book(pair_key[1])

            contract_symbol = CryptoUtil.convert_symbol_to_contract(self.hedge_exchange, pair_key[1])
            swap_orderbook = self.hedge_exchange.fetch_order_book(contract_symbol)

            # 现货多头买入，按卖1价下单
            spot_price_1 = spot_orderbook_1['asks'][0][0] 
            spot_price_2 = spot_orderbook_2['asks'][0][0] 

            # 合约空头卖出，按买1价下单
            swap_price = swap_orderbook['bids'][0][0] 

            
            # 创建限价单
            spot_order_1 = self.exchange_1.create_limit_buy_order(
                pair_key[0], 
                data['amount'],
                spot_price_1
            )
            spot_order_2 = self.exchange_2.create_limit_sell_order(
                pair_key[1],
                data['amount'],
                spot_price_2
            )
            swap_order = self.hedge_exchange.create_limit_sell_order(
                contract_symbol,
                data['amount'],
                swap_price
            )
            
            # 记录订单
            order_id = SerialnoUtil.create_serial_no(prefix='arb_', length=20)
            arb_order = ArbitrageHedgeOrder(
                id=order_id,
                leg_spot_1=spot_order_1,
                leg_spot_2=spot_order_2,
                leg_swap=swap_order,
                pair_key=pair_key,
                amount=data['amount']
            )
            
            with self.lock:
                self.active_orders[order_id] = arb_order
                
            return order_id
            
        except Exception as e:
            self.strategy.logger.error(f"创建套利仓位失败: {e}")
            self._handle_error(pair_key, data)
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
            spot_order_1 = self.exchange_1.fetch_order(arb_order.leg_spot_1.order_id)
            spot_order_2 = self.exchange_2.fetch_order(arb_order.leg_spot_2.order_id)
            swap_order = self.hedge_exchange.fetch_order(arb_order.leg_swap.order_id)
            
            # 更新成交量
            arb_order.leg_spot_1.filled = spot_order_1['filled']
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
                self.strategy.logger.info(f"套利订单 {order_id} 完全成交")
                
        except Exception as e:
            self.strategy.logger.error(f"检查订单状态失败: {e}")

    def _cancel_and_adjust(self, order_id: str, arb_order: ArbitrageOrder):
        """撤单并追单"""
        try:
            # 撤销未完成的订单
            if arb_order.spot_filled < arb_order.amount:
                self.strategy.exchange_1.cancel_order(arb_order.spot_order_id)
            if arb_order.futures_filled < arb_order.amount:
                self.strategy.exchange_2.cancel_order(arb_order.futures_order_id)
                
            # 重新下单（剩余未成交部分）
            remaining_amount = arb_order.amount - max(arb_order.spot_filled, arb_order.futures_filled)
            if remaining_amount > 0:
                # 以更激进的价格重新下单
                self.create_arbitrage_position(
                    arb_order.pair_key,
                    {'amount': remaining_amount}
                )
                
        except Exception as e:
            self.strategy.logger.error(f"撤单调整失败: {e}")

    def _handle_imbalance(self, order_id: str, arb_order: ArbitrageOrder):
        """处理残腿"""
        try:
            imbalance = arb_order.spot_filled - arb_order.futures_filled
            if imbalance > 0:  # 现货多成交
                # 补充合约空单
                self.strategy.exchange_2.create_market_sell_order(
                    arb_order.pair_key[1],
                    abs(imbalance)
                )
            else:  # 合约多成交
                # 补充现货多单
                self.strategy.exchange_1.create_market_buy_order(
                    arb_order.pair_key[0],
                    abs(imbalance)
                )
        except Exception as e:
            self.strategy.logger.error(f"处理残腿失败: {e}")


if __name__ == '__main__':

    from btc_model.setting.setting import get_settings
    import pandas as pd

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
    hedge_exchange = ccxtpro.binance(params)

    strategy = ExchangeArbitrageStrategy(exchange_1, exchange_2, pairs)

    position_manager = ArbitragePositionManager(
        strategy=ExchangeArbitrageStrategy(),
        exchange_1=exchange_1,
        exchange_2=exchange_2,
        hedge_exchange=hedge_exchange
    )

    # position_manager.create_arbitrage_position(
    #     ('BTC/USDT', 'BTC/USDT'),
    #     {'amount': 0.001}
    # )   
    
    print('-------------------------------------------------------------------------')
