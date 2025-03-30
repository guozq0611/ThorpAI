import asyncio
import threading
import datetime
import time
from typing import Dict, List, Set, Optional, Any
import ccxt
import ccxt.pro as ccxtpro
from btc_model.core.util.log_util import Logger
from btc_model.core.util.crypto_util import CryptoUtil
from btc_model.core.common.const import Exchange
from btc_model.setting.setting import get_settings
from btc_model.core.util.db_util import get_db_engine
from sqlalchemy import text
import traceback
import json
import copy
import pymysql
from typing import Union

class MarketDataService:
    """
    市场数据管理类，负责订阅和管理各交易所的行情数据
    考虑性能问题, 仅使用websocket获取订单簿
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MarketDataService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """初始化市场数据管理器"""
        if self._initialized:
            return
        
        self.db_engine = get_db_engine('thorpai')
            
        # 存储交易所实例
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self.pro_exchanges: Dict[str, ccxtpro.Exchange] = {}

        # 存储永续合约交易所实例, 仅通过指定的交易所实例获取永续合约市场数据
        self.perpetual_exchanges: Dict[str, ccxtpro.Exchange] = {}

        # 存储订阅的行情数据
        self.orderbooks: Dict[str, Dict[str, Any]] = {}
        self.funding_rates: Dict[str, Dict[str, Any]] = {}
        self.tickers: Dict[str, Dict[str, Any]] = {}
        self.bbo_prices: Dict[str, Dict[str, Any]] = {}    # best bid offer prices
        
        # 订阅状态管理
        self.subscribed_symbols: Dict[str, Set[str]] = {
            'orderbook': set(),
            'funding_rate': set(),
            'ticker': set(),
            'bbo': set()
        }
        
        # 按交易所存储订阅的交易对 - 便于查询特定交易所的所有订阅
        self.subscribed_by_exchange: Dict[str, Dict[str, Set[str]]] = {
            'orderbook': {},       # 格式: {'binance': {'BTC/USDT', 'ETH/USDT'}, 'okx': {...}}
            'funding_rate': {},     # 格式同上
            'ticker': {},           # 格式同上
            'bbo': {}               # 格式同上
        }
        
        # 线程和锁
        self.lock = threading.Lock()
        self.subscription_thread = None
        self.is_running = False
        
        # 持久化线程和状态
        self.persistence_thread = None
        self.persistence_thread_running = False
        
        # 统计数据
        self.rest_stats = {}  # 键为 "exchange_id:symbol:data_type"
        
        self._initialized = True
        Logger.info("MarketDataService initialized")

    def create_exchanges(self, exchange_ids: List[str]) -> None:
        """
        创建交易所实例
        Args:
            exchange_ids: 交易所ID列表, 如 ['binance', 'okx']
        """

        for exchange_id in exchange_ids:
            setting = get_settings(f'cex.{exchange_id}')
            apikey = setting['apikey']
            secretkey = setting['secretkey']
            params = {
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

            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class(params)
            exchange.load_markets()
            Logger.info(f"load markets: {exchange.id}")
            self.add_exchange(exchange)
            
    def add_exchange(self, exchange: ccxt.Exchange) -> None:
        """添加交易所实例"""
        

        if exchange.id in self.exchanges:
            Logger.warning(f"交易所 {exchange.id} 已存在")
            return
        
        
        self.exchanges[exchange.id] = exchange
        Logger.info(f"添加交易所: {exchange.id}")

        pro_exchange, msg = CryptoUtil.create_pro_exchange(exchange)
        if pro_exchange:
            self.pro_exchanges[exchange.id] = pro_exchange
            Logger.info(f"添加异步交易所: {exchange.id}")
        else:
            Logger.error(f"添加异步交易所失败: {msg}")
        
    def set_perpetual_exchanges(self, exchange_ids: List[str]) -> None:
        """设置永续合约交易所实例"""
        for exchange_id in exchange_ids:
            if exchange_id not in self.pro_exchanges:
                Logger.error(f"交易所 {exchange_id} 不存在")
                continue
            
            self.perpetual_exchanges[exchange_id] = self.pro_exchanges[exchange_id]
            Logger.info(f"设置永续合约交易所: {exchange_id}")   

    def subscribe_bbo(self, exchange_id: str, symbol: str) -> None:
        """订阅特定交易所和交易对的bbo"""
        key = f"{exchange_id}:{symbol}"
        with self.lock:
            self.subscribed_symbols['bbo'].add(key)
            
            # 同时更新按交易所分组的订阅信息
            if exchange_id not in self.subscribed_by_exchange['bbo']:
                self.subscribed_by_exchange['bbo'][exchange_id] = set()
            self.subscribed_by_exchange['bbo'][exchange_id].add(symbol)
            
            # 初始化空数据结构
            self.bbo_prices[key] = {'bid_price': 0, 'bid_volume': 0, 'ask_price': 0, 'ask_volume': 0, 'timestamp': 0}
        Logger.info(f"subscribe bbo: {key}")

    def subscribe_ticker(self, exchange_id: str, symbol: str) -> None:
        """订阅特定交易所和交易对的ticker"""
        key = f"{exchange_id}:{symbol}"
        with self.lock:
            self.subscribed_symbols['ticker'].add(key)
            
            # 同时更新按交易所分组的订阅信息
            if exchange_id not in self.subscribed_by_exchange['ticker']:
                self.subscribed_by_exchange['ticker'][exchange_id] = set()
            self.subscribed_by_exchange['ticker'][exchange_id].add(symbol)
            
            # 初始化空数据结构
            self.tickers[key] = {'ticker': [], 'timestamp': 0}
        Logger.info(f"subscribe ticker: {key}")

    def subscribe_orderbook(self, exchange_id: str, symbol: str) -> None:
        """订阅特定交易所和交易对的订单簿"""
        key = f"{exchange_id}:{symbol}"
        with self.lock:
            self.subscribed_symbols['orderbook'].add(key)
            
            # 同时更新按交易所分组的订阅信息
            if exchange_id not in self.subscribed_by_exchange['orderbook']:
                self.subscribed_by_exchange['orderbook'][exchange_id] = set()
            self.subscribed_by_exchange['orderbook'][exchange_id].add(symbol)
            
            # 初始化空数据结构
            self.orderbooks[key] = {'bids': [], 'asks': [], 'timestamp': 0}
        Logger.info(f"subscribe orderbook: {key}")
    
    
    def subscribe_funding_rate(self, exchange_id: str, symbol: str) -> None:
        """订阅特定交易所和交易对的资金费率"""
        key = f"{exchange_id}:{symbol}"
        with self.lock:
            self.subscribed_symbols['funding_rate'].add(key)
            
            # 同时更新按交易所分组的订阅信息
            if exchange_id not in self.subscribed_by_exchange['funding_rate']:
                self.subscribed_by_exchange['funding_rate'][exchange_id] = set()
            self.subscribed_by_exchange['funding_rate'][exchange_id].add(symbol)
            
            # 初始化空数据结构
            self.funding_rates[key] = {'fundingRate': 0, 'timestamp': 0}
        Logger.info(f"subscribe funding rate: {key}")

    def get_bbo(self, exchange_id: str, symbol: str) -> Dict[str, Any]:
        """获取特定交易所和交易对的BBO"""
        key = f"{exchange_id}:{symbol}"
        with self.lock:
            bbo = self.bbo_prices.get(key, {'bid_price': 0, 'bid_volume': 0, 'ask_price': 0, 'ask_volume': 0, 'timestamp': 0})
            if bbo['bid_price'] == 0 or bbo['ask_price'] == 0:
                # 如果BBO价格为0, 则通过同步方式获取BBO
                if self.exchanges[exchange_id].has['fetchBidsAsks']:
                    bbo = self.exchanges[exchange_id].fetch_bids_asks([symbol])
                    bbo = {
                        'bid_price': bbo[symbol]['bid'],
                        'bid_volume': bbo[symbol]['bidVolume'],
                        'ask_price': bbo[symbol]['ask'],
                        'ask_volume': bbo[symbol]['askVolume'],
                        'timestamp': bbo[symbol]['timestamp'] or int(time.time() * 1000)
                    }
                    self.bbo_prices[key] = bbo
                elif self.exchanges[exchange_id].has['fetchTicker']:
                    ticker = self.exchanges[exchange_id].fetch_ticker(symbol)
                    bbo = {
                        'bid_price': ticker['bid'],
                        'bid_volume': ticker['bidVolume'],
                        'ask_price': ticker['ask'],
                        'ask_volume': ticker['askVolume'],
                        'timestamp': ticker['timestamp'] or int(time.time() * 1000)
                    }
                    self.bbo_prices[key] = bbo

            return bbo
    
    def get_orderbook(self, exchange_id: str, symbol: str) -> Dict[str, Any]:
        """获取特定交易所和交易对的订单簿"""
        key = f"{exchange_id}:{symbol}"
        with self.lock:
            return self.orderbooks.get(key, {'bids': [], 'asks': [], 'timestamp': 0})
        
    def get_ticker(self, exchange_id: str, symbol: str) -> Dict[str, Any]:
        """获取特定交易所和交易对的ticker"""
        key = f"{exchange_id}:{symbol}"
        with self.lock:
            return self.tickers.get(key, {'ticker': [], 'timestamp': 0})
    

    def get_funding_rate(self, exchange_id: str, symbol: str) -> Dict[str, Any]:
        """获取特定交易所和交易对的资金费率"""
        key = f"{exchange_id}:{symbol}"
        with self.lock:
            return self.funding_rates.get(key, {'fundingRate': 0, 'timestamp': 0})
    
    def start(self) -> None:
        """启动市场数据订阅"""
        if self.is_running:
            Logger.warning("market data service is already running")
            return
            
        self.is_running = True
        self.subscription_thread = threading.Thread(target=self._run_subscription_loop, daemon=True)
        self.subscription_thread.start()
        Logger.info("market data service started")
    
    def start_persistence(self, db_config=None) -> None:
        """启动市场数据持久化线程
        
        Args:
            db_config: 数据库配置，如果为None则使用默认配置
        """
        if self.persistence_thread_running:
            Logger.warning("数据持久化线程已经在运行")
            return
        
        # 初始化数据库表
        self.ensure_market_data_db(db_config)
        
        # 启动持久化线程
        self.persistence_thread_running = True
        self.persistence_thread = threading.Thread(target=self._run_market_data_persistence, daemon=True)
        self.persistence_thread.start()
        Logger.info("市场数据持久化线程已启动")
    
    def stop(self) -> None:
        """停止市场数据订阅"""
        self.is_running = False
        if self.subscription_thread and self.subscription_thread.is_alive():
            self.subscription_thread.join(timeout=5)
        
        # 停止持久化线程
        self.stop_persistence()
        
        # 关闭所有异步交易所连接
        self.close_connections()
        
        Logger.info("market data service stopped")
    
    def stop_persistence(self) -> None:
        """停止市场数据持久化线程"""
        if not self.persistence_thread_running:
            return
            
        self.persistence_thread_running = False
        if self.persistence_thread and self.persistence_thread.is_alive():
            self.persistence_thread.join(timeout=5)
            Logger.info("市场数据持久化线程已停止")
    
    def close_connections(self) -> None:
        """关闭所有异步交易所连接"""
        # 创建一个新的事件循环来关闭连接
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 关闭所有异步交易所实例
            for exchange_id, pro_exchange in list(self.pro_exchanges.items()):
                try:
                    Logger.info(f"正在关闭 {exchange_id} 的异步连接...")
                    # 使用同步方式关闭
                    if hasattr(pro_exchange, 'close'):
                        loop.run_until_complete(pro_exchange.close())
                    Logger.info(f"{exchange_id} 的异步连接已关闭")
                except Exception as e:
                    Logger.warning(f"关闭 {exchange_id} 的异步连接时出错: {str(e)}")
        except Exception as e:
            Logger.error(f"关闭异步连接时出错: {str(e)}")
        finally:
            loop.close()
            
        # 清空异步交易所实例
        self.pro_exchanges.clear()
        Logger.info("所有异步连接已关闭")
    
    def _run_subscription_loop(self) -> None:
        """运行订阅循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._subscription_worker())
        except Exception as e:
            Logger.error(f"subscription loop exception: {str(e)}")
        finally:
            loop.close()
    
    async def _subscription_worker(self) -> None:
        """订阅工作线程"""
        # 首先加载所有交易所的市场数据
        # markets_loaded = False
        # max_retries = 3
        # retry_count = 0
        
        # # 记录成功加载市场数据的交易所
        # loaded_exchanges = set()
        
        # while not markets_loaded and retry_count < max_retries:
        #     try:
        #         retry_count += 1
        #         Logger.info(f"try to load market data (try {retry_count}/{max_retries})...")
                
        #         # 加载所有交易所的市场数据
        #         for exchange_id, pro_exchange in list(self.pro_exchanges.items()):
        #             # 如果已经成功加载，则跳过
        #             if exchange_id in loaded_exchanges:
        #                 continue
                        
        #             try:
        #                 Logger.info(f"loading market data for {exchange_id}...")
                        
        #                 # 设置超时
        #                 timeout = 20
        #                 try:
        #                     # 使用 asyncio.wait_for 设置超时
        #                     await asyncio.wait_for(pro_exchange.load_markets(), timeout)
                            
        #                     exchange = self.exchanges[exchange_id]
        #                     # exchange.markets = pro_exchange.markets
        #                     # exchange.symbols = pro_exchange.symbols
        #                     # exchange.currencies = pro_exchange.currencies
        #                     #exchange.load_markets()


        #                     Logger.info(f"{exchange_id} market data loaded")
        #                     # 标记为已加载成功
        #                     loaded_exchanges.add(exchange_id)
        #                 except (asyncio.TimeoutError, asyncio.CancelledError) as e:
        #                     Logger.error(f"{exchange_id} load market data failed: {str(e)}")
        #                     # 如果是最后一次尝试，则移除该交易所的异步实例
        #                     if retry_count == max_retries:
        #                         Logger.warning(f"remove {exchange_id} pro instance")
        #                         self.pro_exchanges.pop(exchange_id, None)
        #                     continue
                        
        #             except Exception as e:
        #                 error_msg = str(e)
        #                 Logger.error(f"load market data for {exchange_id} failed: {error_msg}")
                        
        #                 # 如果是最后一次尝试，则移除该交易所的异步实例
        #                 if retry_count == max_retries:
        #                     Logger.warning(f"remove {exchange_id} pro instance")
        #                     self.pro_exchanges.pop(exchange_id, None)
                
        #         # 如果所有交易所都已加载或者已经没有异步实例，则标记为加载完成
        #         if len(loaded_exchanges) == len(self.pro_exchanges) or not self.pro_exchanges:
        #             markets_loaded = True
        #             Logger.info("market data loaded")
                
        #     except Exception as e:
        #         error_msg = str(e)
        #         Logger.error(f"load market data exception (try {retry_count}/{max_retries}): {error_msg}")
                
        #         if retry_count < max_retries:
        #             wait_time = min(5, 2 ** retry_count)  # 指数退避，但最大等待5秒
        #             Logger.info(f"will retry in {wait_time} seconds...")
        #             await asyncio.sleep(wait_time)
        #         else:
        #             Logger.error("reach max retry times, cannot load all market data")
        #             # 尝试继续运行，即使市场数据没有完全加载
        #             markets_loaded = True
        #             Logger.warning("will try to continue running, but some functions may be affected")
        
        # # 如果没有成功加载任何交易所的市场数据，则记录警告
        # if not loaded_exchanges and self.pro_exchanges:
        #     Logger.warning("no market data loaded, please check!")
        #     self.pro_exchanges.clear()
        
        # 开始订阅循环
        subscription_tasks = {}  # 用于跟踪活跃的订阅任务
        
        while self.is_running:
            try:
                # 创建所有订阅任务
                new_tasks = []

                # # 处理订单簿数据订阅
                # for exchange_id, exchange in list(self.pro_exchanges.items()):
                #     # 检查此交易所是否已有活跃的订单簿订阅任务
                #     task_key = f"orderbook_spot:{exchange_id}"
                #     if task_key in subscription_tasks and not subscription_tasks[task_key].done():
                #         # 如果任务仍在运行，跳过创建新任务
                #         continue   
          
                #     symbols = list(self.get_subscribed_symbols_by_exchange('orderbook', 'spot', exchange_id))
                #     if symbols:
                #         # 创建批量获取订单簿的任务
                #         task = asyncio.create_task(self._watch_orderbook_for_symbols(exchange, symbols))
                #         subscription_tasks[f"{task_key}:spot"] = task
                #         new_tasks.append(task)


                # for exchange_id, exchange in list(self.perpetual_exchanges.items()):
                #     # 检查此交易所是否已有活跃的订单簿订阅任务
                #     task_key = f"orderbook_swap:{exchange_id}"
                #     if task_key in subscription_tasks and not subscription_tasks[task_key].done():
                #         # 如果任务仍在运行，跳过创建新任务
                #         continue   
          
                #     symbols = list(self.get_subscribed_symbols_by_exchange('orderbook', 'swap', exchange_id))
                #     if symbols:
                #         # 创建批量获取订单簿的任务
                #         task = asyncio.create_task(self._watch_orderbook_for_symbols(exchange, symbols))
                #         subscription_tasks[f"{task_key}:swap"] = task
                #         new_tasks.append(task)


                # 处理数据订阅
                for exchange_id, exchange in list(self.pro_exchanges.items()):
                    # 检查此交易所是否已有活跃的订单簿订阅任务
                    task_key = f"bbo_spot:{exchange_id}"
                    if task_key in subscription_tasks and not subscription_tasks[task_key].done():
                        # 如果任务仍在运行，跳过创建新任务
                        continue   
          
                    symbols = list(self.get_subscribed_symbols_by_exchange('bbo', 'spot', exchange_id))
                    if symbols:
                        # 创建批量获取订单簿的任务
                        task = asyncio.create_task(self._watch_bbo_prices(exchange, symbols))
                        subscription_tasks[f"{task_key}:spot"] = task
                        new_tasks.append(task)


                for exchange_id, exchange in list(self.perpetual_exchanges.items()):
                    # 检查此交易所是否已有活跃的订单簿订阅任务
                    task_key = f"bbo_swap:{exchange_id}"
                    if task_key in subscription_tasks and not subscription_tasks[task_key].done():
                        # 如果任务仍在运行，跳过创建新任务
                        continue   
          
                    symbols = list(self.get_subscribed_symbols_by_exchange('bbo', 'swap', exchange_id))
                    if symbols:
                        # 创建批量获取订单簿的任务
                        task = asyncio.create_task(self._watch_bbo_prices(exchange, symbols))
                        subscription_tasks[f"{task_key}:swap"] = task
                        new_tasks.append(task)
                
                
                # # 处理资金费率数据订阅
                # for exchange_id, pro_exchange in list(self.pro_exchanges.items()):
                #     # 只处理合约产品的资金费率
                #     product_type = 'swap'
                #     # 检查此交易所是否已有活跃的资金费率订阅任务
                #     task_key = f"funding_rate:{exchange_id}"
                #     if task_key in subscription_tasks and not subscription_tasks[task_key].done():
                #         # 如果任务仍在运行，跳过创建新任务
                #         continue
                    
                #     # 获取该交易所订阅的所有交易对
                #     symbols = list(self.get_subscribed_symbols_by_exchange('funding_rate', product_type, exchange_id))
                #     if symbols:
                #         # 创建批量获取资金费率的任务
                #         task = asyncio.create_task(self._watch_funding_rate_for_symbols(exchange_id, symbols))
                #         subscription_tasks[task_key] = task
                #         new_tasks.append(task)
                        
                # 清理已完成的任务
                for key in list(subscription_tasks.keys()):
                    if subscription_tasks[key].done():
                        try:
                            # 获取任务结果，如果有异常会抛出
                            subscription_tasks[key].result()
                        except Exception as e:
                            if isinstance(e, (asyncio.TimeoutError, asyncio.CancelledError)):
                                # 超时或取消错误，只记录警告
                                Logger.warning(f"subscription task {key} timeout or cancelled: {str(e)}")
                            else:
                                # 其他异常记录为错误
                                Logger.error(f"subscription task {key} exception: {str(e)}")
                        
                        # 从字典中移除已完成的任务
                        subscription_tasks.pop(key)
                
                # 如果有新任务，等待一小段时间让它们开始执行
                if new_tasks:
                    await asyncio.sleep(0.1)
                    # 确保new_tasks在使用后被清空，防止内存泄漏
                    new_tasks.clear()
                else:
                    # 如果没有新任务，等待一段时间再检查
                    await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                Logger.warning("subscription worker cancelled, will retry in 3 seconds")
                await asyncio.sleep(3)  # 被取消后等待3秒再重试
            except Exception as e:
                Logger.error(f"subscription worker exception: {str(e)}")
                await asyncio.sleep(3)  # 出错后等待3秒再重试


     
    async def _watch_bbo_prices(self, exchange: ccxtpro.Exchange, symbols: List[str]) -> None:
        """优先使用WEBSOCKET获取订单簿"""
        try:

            bbo_prices = await asyncio.wait_for(exchange.watch_bids_asks(symbols),timeout=30)
            for symbol, bbo in bbo_prices.items():
                key = f"{exchange.id}:{symbol}"
                current_timestamp = int(time.time() * 1000)
                with self.lock:
                    self.bbo_prices[key] = {
                        'bid_price': bbo['bid'],
                        'bid_volume': bbo['bidVolume'],
                        'ask_price': bbo['ask'],
                        'ask_volume': bbo['askVolume'],
                        'timestamp': bbo['timestamp'] or current_timestamp
                    }

                    # Logger.info(f"bbo updated, {key}, bid:{self.bbo_prices[key]['bid_price'] if self.bbo_prices[key]['bid_price'] else 'N/A'}, ask:{self.bbo_prices[key]['ask_price'] if self.bbo_prices[key]['ask_price'] else 'N/A'}")

        except Exception as e:
            Logger.error(f"使用watch_bbo_prices获取bbo失败, 交易所: {exchange.id}, 错误: {str(e)}")
            # 确保有一个空的数据结构
            # with self.lock:
            #     for symbol in symbols:
            #         key = f"{exchange.id}:{symbol}"
            #         if key not in self.bbo_prices:
            #             self.bbo_prices[key] = {       
            #                 'bidPrice': 0,
            #                 'bidVolume': 0,
            #                 'askPrice': 0,
            #                 'askVolume': 0,
            #                 'timestamp': int(time.time() * 1000)
            #             }
    
    
    async def _watch_orderbook_for_symbols(self, exchange: ccxtpro.Exchange, symbols: List[str]) -> None:
        """优先使用WEBSOCKET获取订单簿"""
        try:

      
            orderbook = await asyncio.wait_for(
                                exchange.watch_order_book_for_symbols(symbols, limit=10),
                                timeout=30
                            )
            key = f"{exchange.id}:{dict(orderbook)['symbol']}"
            with self.lock:
                self.orderbooks[key] = {
                    'bids': list(dict(orderbook)['bids'])[0:5],
                    'asks': list(dict(orderbook)['asks'])[0:5],
                    'timestamp': dict(orderbook)['timestamp'] or int(time.time() * 1000)
                }

                Logger.info(f"orderbook updated, {key}, bid1:{self.orderbooks[key]['bids'][0] if self.orderbooks[key]['bids'] else 'N/A'}, ask1:{self.orderbooks[key]['asks'][0] if self.orderbooks[key]['asks'] else 'N/A'}")

        except Exception as e:
            Logger.error(f"使用watch_order_book获取订单簿失败, 交易所: {exchange.id}, 错误: {str(e)}")
            # 确保有一个空的数据结构
            with self.lock:
                for symbol in symbols:
                    key = f"{exchange.id}:{symbol}"
                    if key not in self.orderbooks:
                        self.orderbooks[key] = {
                            'bids': [],
                            'asks': [],
                            'timestamp': int(time.time() * 1000)
                        }
    
    
    async def _watch_funding_rate_for_symbols(self, exchange: ccxt.Exchange, symbols: List[str]) -> None:
        """使用WEBSOCKET或REST API获取资金费率"""
 
    
        current_time = int(time.time() * 1000)
            
        # 单独处理每个交易对
        for symbol in symbols:
            try:
                # 尝试使用WebSocket获取资金费率（如果支持）
                funding_rate_data = None
                
                # 目前币安、OKX等都不支持
                # if hasattr(pro_exchange, 'watch_funding_rate'):
                #     try:
                #         funding_rate_data = await asyncio.wait_for(
                #             pro_exchange.watch_funding_rate(symbol),
                #             timeout=10
                #         )
                #     except Exception as ws_error:
                #         Logger.warning(f"无法通过WebSocket获取 {exchange_id}:{symbol} 资金费率: {str(ws_error)}，将回退到REST API")
                    
                # # 如果WebSocket不支持或失败，回退到REST API
                if not funding_rate_data:
                    funding_rate = await asyncio.wait_for(exchange.fetch_funding_rate(symbol), timeout=5)
                    
                    funding_rate_data = {
                        'symbol': symbol,
                        'fundingRate': funding_rate['fundingRate'],
                        'fundingTime': funding_rate.get('nextFundingTime', funding_rate.get('fundingTime')),
                        'timestamp': funding_rate.get('timestamp', current_time)
                    }
                
                # 使用正确的键存储数据
                key = f"{exchange.id}:{symbol}"
                with self.lock:
                    self.funding_rates[key] = {
                        'fundingRate': funding_rate_data['fundingRate'],
                        'fundingTime': funding_rate_data.get('nextFundingTime', funding_rate_data.get('fundingTime')),
                        'timestamp': funding_rate_data.get('timestamp', current_time)
                    }
                    
                    Logger.info(f"资金费率已更新: {key}, rate:{self.funding_rates[key]['fundingRate']}")
                        
            except Exception as e:
                Logger.warning(f"获取 {exchange.id}:{symbol} 资金费率失败: {str(e)}")
                # 确保有一个空的数据结构
                key = f"{exchange.id}:{symbol}"
                with self.lock:
                    if key not in self.funding_rates:
                        self.funding_rates[key] = {
                            'fundingRate': 0,
                            'fundingTime': None,
                            'timestamp': current_time
                        }



    def is_data_fresh(self, data_type: str, exchange_id: str, symbol: str, max_age_ms: int = 10000) -> bool:
        """检查数据是否新鲜（默认10秒内的数据视为新鲜）"""
        key = f"{exchange_id}:{symbol}"
        current_time = int(time.time() * 1000)
        
        with self.lock:
            if data_type == 'bbo':
                data = self.bbo_prices.get(key, {})
            elif data_type == 'orderbook':
                data = self.orderbooks.get(key, {})
            elif data_type == 'funding_rate':
                data = self.funding_rates.get(key, {})
            else:
                return False
            
            timestamp = data.get('timestamp', 0)
            return (current_time - timestamp) <= max_age_ms 

   
    def ensure_market_data_db(self, db_config):
        """初始化行情数据库和表结构"""
        try:
            try:
                with self.db_engine.connect() as conn:
                    sql = '''
                    CREATE TABLE IF NOT EXISTS bbo_snapshot (
                        exchange_id VARCHAR(50) NOT NULL,
                        symbol VARCHAR(50) NOT NULL,
                        datetime DATETIME NOT NULL,
                        bid_price DOUBLE NOT NULL,
                        bid_volume DOUBLE NOT NULL,
                        ask_price DOUBLE NOT NULL,
                        ask_volume DOUBLE NOT NULL,
                        timestamp BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (exchange_id, symbol)
                    )
                    '''
                   
                    conn.execute(text(sql))
                    # 创建最新订单簿表 - 使用复合主键来支持UPSERT
                    sql = '''
                    CREATE TABLE IF NOT EXISTS orderbook_snapshot (
                        exchange_id VARCHAR(50) NOT NULL,
                        symbol VARCHAR(50) NOT NULL,
                        datetime DATETIME NOT NULL,
                        bid1_price DOUBLE NOT NULL,
                        bid1_volume DOUBLE NOT NULL,
                        bid2_price DOUBLE NOT NULL,
                        bid2_volume DOUBLE NOT NULL,
                        bid3_price DOUBLE NOT NULL,
                        bid3_volume DOUBLE NOT NULL,
                        bid4_price DOUBLE NOT NULL,
                        bid4_volume DOUBLE NOT NULL,
                        bid5_price DOUBLE NOT NULL,
                        bid5_volume DOUBLE NOT NULL,
                        ask1_price DOUBLE NOT NULL,
                        ask1_volume DOUBLE NOT NULL,
                        ask2_price DOUBLE NOT NULL,
                        ask2_volume DOUBLE NOT NULL,
                        ask3_price DOUBLE NOT NULL,
                        ask3_volume DOUBLE NOT NULL,
                        ask4_price DOUBLE NOT NULL,
                        ask4_volume DOUBLE NOT NULL,
                        ask5_price DOUBLE NOT NULL,
                        ask5_volume DOUBLE NOT NULL,
                        timestamp BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (exchange_id, symbol)
                    )
                    '''
                   
                    conn.execute(text(sql))

                    # 创建最新资金费率表
                    sql = '''
                    CREATE TABLE IF NOT EXISTS funding_rate_snapshot (
                        exchange_id VARCHAR(50) NOT NULL,
                        symbol VARCHAR(50) NOT NULL,
                        datetime DATETIME NOT NULL,
                        funding_rate DOUBLE NOT NULL,
                        funding_time BIGINT,
                        timestamp BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (exchange_id, symbol)
                    )
                    '''
                    
                    conn.execute(text(sql))

                    conn.commit()
                    Logger.info("行情数据库表结构初始化成功")
                    
            finally:
                conn.close()
                
        except Exception as e:
            Logger.error(f"初始化行情数据库失败: {e}")
            traceback.print_exc()

    def _run_market_data_persistence(self):
        """运行行情数据持久化线程，使用UPSERT模式和命名参数
        """

        
        while self.persistence_thread_running:
            try:
                # 批量存储需要的数据
                bbo_data_to_save = []
                orderbook_data_to_save = []
                funding_rate_data_to_save = []
                
                # 使用锁保护，但只获取必要的数据，不做深拷贝
                with self.lock:
                    for key, bbo in self.bbo_prices.items():
                        entry = {
                            'key': key,
                            'timestamp': bbo.get('timestamp', 0),
                            'bid_price': bbo.get('bid_price', 0),
                            'bid_volume': bbo.get('bid_volume', 0),
                            'ask_price': bbo.get('ask_price', 0),
                            'ask_volume': bbo.get('ask_volume', 0)
                        }
                        bbo_data_to_save.append(entry)

                    for key, orderbook in self.orderbooks.items():
                        # 只获取有足够深度的订单簿
                        bids = orderbook.get('bids', [])
                        asks = orderbook.get('asks', [])
                        if len(bids) >= 5 and len(asks) >= 5:
                            # 只复制需要的信息
                            entry = {
                                'key': key,
                                'timestamp': orderbook.get('timestamp', 0),
                                'bids': bids[:5],  # 只取前5档
                                'asks': asks[:5]   # 只取前5档
                            }
                            orderbook_data_to_save.append(entry)
                    
                    # 同样处理资金费率
                    for key, funding_rate in self.funding_rates.items():
                        entry = {
                            'key': key,
                            'timestamp': funding_rate.get('timestamp', 0),
                            'fundingRate': funding_rate.get('fundingRate', 0),
                            'fundingTime': funding_rate.get('fundingTime')
                        }
                        funding_rate_data_to_save.append(entry)
                
                # 获取当前时间戳
                current_timestamp = int(time.time() * 1000)
                
                with self.db_engine.connect() as conn:
                    for entry in bbo_data_to_save:
                        key = entry['key']
                        exchange_id, symbol = key.split(':', 1)
                        timestamp = entry['timestamp'] or current_timestamp
                        
                        # 将毫秒时间戳转换为datetime对象
                        dt = datetime.datetime.fromtimestamp(timestamp / 1000.0)    

                        # 使用命名参数的SQL
                        sql_query = """
                        INSERT INTO bbo_snapshot
                        (exchange_id, symbol, datetime, bid_price, bid_volume, ask_price, ask_volume, timestamp, created_at, updated_at)
                        VALUES (
                        :exchange_id, :symbol, :datetime, :bid_price, :bid_volume, :ask_price, :ask_volume, :timestamp, NOW(), NOW())   
                        ON DUPLICATE KEY UPDATE 
                        datetime = :datetime,
                        timestamp = :timestamp,
                        bid_price = :bid_price,
                        bid_volume = :bid_volume,
                        ask_price = :ask_price,
                        ask_volume = :ask_volume,
                        updated_at = NOW()  
                        """
                        
                        # 准备参数字典
                        params = {
                            'exchange_id': exchange_id,
                            'symbol': symbol,   
                            'datetime': dt,
                            'timestamp': timestamp,
                            'bid_price': entry['bid_price'],
                            'bid_volume': entry['bid_volume'],
                            'ask_price': entry['ask_price'],
                            'ask_volume': entry['ask_volume'],
                        }

                        try:
                            # 执行SQL
                            conn.execute(text(sql_query), params)
                        except Exception as sql_error:
                            Logger.error(f"保存BBO数据失败 {key}: {str(sql_error)}")

                    # 保存订单簿数据 - 使用命名参数
                    for entry in orderbook_data_to_save:
                        key = entry['key']
                        exchange_id, symbol = key.split(':', 1)
                        timestamp = entry['timestamp'] or current_timestamp
                        
                        # 将毫秒时间戳转换为datetime对象
                        dt = datetime.datetime.fromtimestamp(timestamp / 1000.0)
                        
                        # 获取买卖盘数据
                        bids = entry['bids']
                        asks = entry['asks']
                        
                        # 使用命名参数的SQL
                        sql_query = """
                        INSERT INTO orderbook_snapshot
                        (exchange_id, symbol, datetime, 
                        bid1_price, bid1_volume, bid2_price, bid2_volume, 
                        bid3_price, bid3_volume, bid4_price, bid4_volume, 
                        bid5_price, bid5_volume, 
                        ask1_price, ask1_volume, ask2_price, ask2_volume, 
                        ask3_price, ask3_volume, ask4_price, ask4_volume, 
                        ask5_price, ask5_volume, timestamp, created_at, updated_at)
                        VALUES (
                        :exchange_id, :symbol, :datetime, 
                        :bid1_price, :bid1_volume, :bid2_price, :bid2_volume,
                        :bid3_price, :bid3_volume, :bid4_price, :bid4_volume,
                        :bid5_price, :bid5_volume,
                        :ask1_price, :ask1_volume, :ask2_price, :ask2_volume,
                        :ask3_price, :ask3_volume, :ask4_price, :ask4_volume,
                        :ask5_price, :ask5_volume, :timestamp, NOW(), NOW())
                        ON DUPLICATE KEY UPDATE 
                        datetime = :datetime,
                        timestamp = :timestamp,
                        bid1_price = :bid1_price,
                        bid1_volume = :bid1_volume,
                        bid2_price = :bid2_price,
                        bid2_volume = :bid2_volume,
                        bid3_price = :bid3_price,
                        bid3_volume = :bid3_volume,
                        bid4_price = :bid4_price,
                        bid4_volume = :bid4_volume,
                        bid5_price = :bid5_price,
                        bid5_volume = :bid5_volume,
                        ask1_price = :ask1_price,
                        ask1_volume = :ask1_volume,
                        ask2_price = :ask2_price,
                        ask2_volume = :ask2_volume,
                        ask3_price = :ask3_price,
                        ask3_volume = :ask3_volume,
                        ask4_price = :ask4_price,
                        ask4_volume = :ask4_volume,
                        ask5_price = :ask5_price,
                        ask5_volume = :ask5_volume,
                        updated_at = NOW()
                        """
                        
                        # 准备参数字典
                        params = {
                            'exchange_id': exchange_id,
                            'symbol': symbol,
                            'datetime': dt,
                            'timestamp': timestamp,
                            'bid1_price': bids[0][0],
                            'bid1_volume': bids[0][1],
                            'bid2_price': bids[1][0],
                            'bid2_volume': bids[1][1],
                            'bid3_price': bids[2][0],
                            'bid3_volume': bids[2][1],
                            'bid4_price': bids[3][0],
                            'bid4_volume': bids[3][1],
                            'bid5_price': bids[4][0],
                            'bid5_volume': bids[4][1],
                            'ask1_price': asks[0][0],
                            'ask1_volume': asks[0][1],
                            'ask2_price': asks[1][0],
                            'ask2_volume': asks[1][1], 
                            'ask3_price': asks[2][0],
                            'ask3_volume': asks[2][1],
                            'ask4_price': asks[3][0],
                            'ask4_volume': asks[3][1],
                            'ask5_price': asks[4][0],
                            'ask5_volume': asks[4][1]
                        }
                        
                        try:
                            # 执行SQL
                            conn.execute(text(sql_query), params)
                        except Exception as sql_error:
                            Logger.error(f"保存订单簿数据失败 {key}: {str(sql_error)}")
                    
                    # 保存资金费率数据 - 使用命名参数
                    for entry in funding_rate_data_to_save:
                        key = entry['key']
                        exchange_id, symbol = key.split(':', 1)
                        timestamp = entry['timestamp'] or current_timestamp
                        
                        # 将毫秒时间戳转换为datetime对象
                        dt = datetime.datetime.fromtimestamp(timestamp / 1000.0)
                        
                        sql_query = """
                        INSERT INTO funding_rate_snapshot(
                        exchange_id, symbol, datetime, 
                        funding_rate, funding_time, timestamp, created_at, updated_at)
                        VALUES (
                        :exchange_id, :symbol, :datetime, 
                        :funding_rate, :funding_time, :timestamp, NOW(), NOW())
                        ON DUPLICATE KEY UPDATE
                        datetime = :datetime,
                        timestamp = :timestamp,
                        funding_rate = :funding_rate,
                        funding_time = :funding_time,
                        updated_at = NOW()
                        """
                        
                        # 处理funding_time，可能为None
                        funding_time = entry['fundingTime']
                        
                        try:
                            # 准备参数字典
                            params = {
                                'exchange_id': exchange_id,
                                'symbol': symbol,
                                'datetime': dt,
                                'timestamp': timestamp,
                                'funding_rate': entry['fundingRate'],
                                'funding_time': funding_time
                            }
                            
                            # 执行SQL
                            conn.execute(text(sql_query), params)
                        except Exception as sql_error:
                            Logger.error(f"保存资金费率数据失败 {key}: {str(sql_error)}")
                
                    # 提交事务
                    conn.commit()
                    Logger.info(f"已将行情数据更新到数据库: {len(orderbook_data_to_save)} 个订单簿, {len(funding_rate_data_to_save)} 个资金费率")
                    
            except Exception as e:
                Logger.error(f"行情数据持久化线程异常: {e}")
                traceback.print_exc()
                
            # 等待10秒再次执行
            for _ in range(10):
                if not self.persistence_thread_running:
                    break
                time.sleep(1)

    def get_subscribed_symbols_by_exchange(self, data_type: str, product_type: str, exchange_id: str) -> Set[str]:
        """获取特定交易所订阅的所有交易对
        
        Args:
            data_type: 数据类型，'orderbook' 或 'funding_rate'
            product_type: 产品类型，'spot' 或 'swap'
            exchange_id: 交易所ID，如 'binance'、'okx'
            
        Returns:
            交易对集合，如 {'BTC/USDT', 'ETH/USDT'}
        """
        with self.lock:
            # 优先使用按交易所分组的字典
            if exchange_id in self.subscribed_by_exchange.get(data_type, {}):
                symbols = self.subscribed_by_exchange[data_type][exchange_id].copy()            
            else:
                 # 如果上面的字典为空，则从原始集合中过滤
                prefix = f"{exchange_id}:"
                symbols = set()
                for key in self.subscribed_symbols.get(data_type, set()):
                    if key.startswith(prefix):
                        symbol = key[len(prefix):]
                        symbols.add(symbol)
         
            if product_type == 'spot':
                symbols = [symbol for symbol in symbols if not symbol.endswith(':USDT')]
            elif product_type == 'swap':
                symbols = [symbol for symbol in symbols if symbol.endswith(':USDT')]

            return symbols

   
def subscribe_market_data(pairs, market_data_service: MarketDataService):
        """
        订阅交易对的行情数据
        """
        spot_symbols_to_watch = set()
        swap_symbols_to_watch = set()
        # 收集所有需要订阅的交易对
        for pair in pairs:
            symbol = pair['symbol_a']
            spot_symbols_to_watch.add(symbol)
            
            # 添加合约交易对
            contract_symbol = CryptoUtil.convert_symbol_to_contract(None, symbol)
            swap_symbols_to_watch.add(contract_symbol)

        for exchange_id in market_data_service.exchanges:
            for symbol in spot_symbols_to_watch:
                #market_data_service.subscribe_orderbook(exchange_id, symbol)
                market_data_service.subscribe_bbo(exchange_id, symbol)
            for symbol in swap_symbols_to_watch:
                #market_data_service.subscribe_orderbook(exchange_id, symbol)
                market_data_service.subscribe_bbo(exchange_id, symbol)
                #market_data_service.subscribe_funding_rate(exchange_id, symbol)
        
        Logger.info(f"已订阅 {len(spot_symbols_to_watch)} 个现货交易对的市场数据")
        Logger.info(f"已订阅 {len(swap_symbols_to_watch)} 个合约交易对的市场数据")

if __name__ == "__main__":
    from btc_model.core.util.crypto_util import CryptoUtil
    from btc_model.core.common.const import Exchange
    from btc_model.strategy.exchange_arbitrage.exchange_arbitrage_strategy import load_pairs
    
    pairs = load_pairs()


    # 创建MarketDataService实例
    market_data = MarketDataService()
    
    # 创建交易所实例
    market_data.create_exchanges(['binance', 'okx'])
    market_data.set_perpetual_exchanges(['binance'])

    # 过滤掉不在交易所的币种对
    currencies_binance = list(market_data.exchanges['binance'].currencies.keys())
    pairs = [pair for pair in pairs if pair['quote'] == 'USDT' and pair['base'] in currencies_binance]
    currencies_okx = list(market_data.exchanges['okx'].currencies.keys())
    pairs = [pair for pair in pairs if pair['quote'] == 'USDT' and pair['base'] in currencies_okx]

    hedge_exchange = market_data.exchanges['binance']
    swap_symbols = CryptoUtil.get_perpetual_markets(exchange=hedge_exchange)
    swap_bases = {market_data['base'] for market_data in swap_symbols.values()}
    pairs = [pair for pair in pairs if pair['quote'] == 'USDT' and pair['base'] in swap_bases]

    #pairs = pairs[0:200]
    
    subscribe_market_data(pairs, market_data)
    
    # 订阅订单簿数据
    # market_data.subscribe_orderbook('binance', 'BTC/USDT')
    # market_data.subscribe_orderbook('binance', 'LSK/USDT')
    # market_data.subscribe_orderbook('binance', 'LSK/USDT:USDT')
    # market_data.subscribe_bbo('binance', 'LSK/USDT:USDT')
    # market_data.subscribe_orderbook('okx', 'BTC/USDT')
    # market_data.subscribe_orderbook('okx', 'ETH/USDT')

    

    # 订阅资金费率数据
    # market_data.subscribe_funding_rate('binance', 'BTC/USDT:USDT')
    # market_data.subscribe_funding_rate('binance', 'LSK/USDT:USDT')
    # market_data.subscribe_funding_rate('binance', 'ETH/USDT:USDT')

    
    # 启动市场数据订阅
    market_data.start()
    
    # 启动市场数据持久化
    market_data.start_persistence()
    
    try:
        print("市场数据服务已启动...")
        while True:
            # 每10秒打印一次订单簿和资金费率数据
            orderbook_binance = market_data.get_orderbook('binance', 'BTC/USDT')
            orderbook_okx = market_data.get_orderbook('okx', 'BTC/USDT')
            
            funding_rate_binance = market_data.get_funding_rate('binance', 'BTC/USDT')
            funding_rate_okx = market_data.get_funding_rate('okx', 'BTC/USDT')
            
            # print("\n===== 订单簿数据 =====")
            # print(f"Binance BTC/USDT bid1: {orderbook_binance['bids'][0] if orderbook_binance['bids'] else 'N/A'}")
            # print(f"Binance BTC/USDT ask1: {orderbook_binance['asks'][0] if orderbook_binance['asks'] else 'N/A'}")
            # print(f"OKX BTC/USDT bid1: {orderbook_okx['bids'][0] if orderbook_okx['bids'] else 'N/A'}")
            # print(f"OKX BTC/USDT ask1: {orderbook_okx['asks'][0] if orderbook_okx['asks'] else 'N/A'}")
            
            # print("\n===== 资金费率数据 =====")
            # print(f"Binance BTC/USDT funding rate: {funding_rate_binance['fundingRate']}")
            # print(f"OKX BTC/USDT funding rate: {funding_rate_okx['fundingRate']}")
            
            # 睡眠10秒
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n正在停止市场数据服务...")
    finally:
        # 停止市场数据服务
        market_data.stop()
        print("市场数据服务已停止")
