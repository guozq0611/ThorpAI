from typing import Dict, List, Optional
import threading
import time
import ccxt
import traceback
from ccxt.base.errors import RequestTimeout, NetworkError

from btc_model.core.common.const import OrderStatus
from btc_model.core.common.object import PositionData
from btc_model.core.util.log_util import Logger
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
                 exchange_1: ccxt.Exchange, 
                 exchange_2: ccxt.Exchange, 
                 hedge_exchange: ccxt.Exchange
                 ):
        self.strategy = strategy
        self.exchange_1 = exchange_1
        self.exchange_2 = exchange_2
        self.hedge_exchange = hedge_exchange

        self.active_orders: Dict[str, ArbitrageOrder | ArbitrageHedgeOrder] = {}
        self.lock = threading.Lock()
        self._start_monitor()
        
    def create_position(self, pair_key, data):
        pass

    def create_arbitrage_position(self, pair_key: tuple, data: dict) -> Optional[str]:
        """创建套利仓位"""
        max_retries = 3
        retry_delay = 1  # 秒
        
        for attempt in range(max_retries):
            try:
                # 获取订单簿数据
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
                spot_order_2 = self.exchange_2.create_limit_buy_order(
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
                    retry_delay *= 2  # 指数退避
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
    # 获取设置
  
    # 初始化币安交易所
    setting = get_settings('cex.binance')
    apikey = setting['apikey']
    secretkey = setting['secretkey']

    params_1 = {
        'enableRateLimit': True,
        'proxies': {
            'http': get_settings('common')['proxies']['http'],                
            'https': get_settings('common')['proxies']['http'],
        },
        'apiKey': apikey,          
        'secret': secretkey,       
        'options': {
            'defaultType': 'spot',  # 可选：'spot', 'margin', 'future'
        }
    }
    exchange_1 = ccxt.binance(params_1)


    setting = get_settings('cex.okx')
    apikey = setting['apikey']
    secretkey = setting['secretkey']
    passphrase = setting['passphrase']

    # 初始化币安交易所
    params_2 = {
        'enableRateLimit': True,
        'proxies': {
            'http': get_settings('common')['proxies']['http'],                   
            'https': get_settings('common')['proxies']['http'],  
        },
        'apiKey': apikey,          
        'secret': secretkey,  
        'password': passphrase,     
        'options': {
            'defaultType': 'spot',  # 可选：'spot', 'margin', 'future'
        },
        'headers': {
            'x-simulated-trading': '1'
        }
    }

    exchange_2 = ccxt.okx(params_2)
    hedge_exchange = ccxt.binance(params_1)

    exchange_1.set_sandbox_mode(True)
    exchange_2.set_sandbox_mode(True)
    hedge_exchange.set_sandbox_mode(True)
    
    strategy = ExchangeArbitrageStrategy(exchange_1=exchange_1, 
                                         exchange_2=exchange_2, 
                                         hedge_exchange=hedge_exchange, 
                                         pairs=pairs
                                        )

    position_manager = ArbitragePositionManager(
        strategy=strategy,
        exchange_1=exchange_1,
        exchange_2=exchange_2,
        hedge_exchange=hedge_exchange
    )

    # position_manager.create_arbitrage_position(
    #     ('BTC/USDT', 'BTC/USDT'),
    #     {'amount': 0.001}
    # )   

    pair_key = ('LSK/USDT', 'LSK/USDT')
    data = {
        'amount': 10
    }
    order_id = position_manager.create_arbitrage_position(pair_key, data)
    print(order_id)
    
    
    print('-------------------------------------------------------------------------')
