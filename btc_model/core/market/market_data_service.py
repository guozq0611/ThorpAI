import asyncio
import threading
import time
from typing import Dict, List, Set, Optional, Any
import ccxt
import ccxt.pro as ccxtpro
from btc_model.core.util.log_util import Logger
from btc_model.core.util.crypto_util import CryptoUtil

#TODO: 需要重构，使用异步API获取行情数据(watch_ticker, watch_orderbook, watch_funding_rate)

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
            
        # 存储交易所实例
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self.pro_exchanges: Dict[str, ccxtpro.Exchange] = {}
        
        # 存储订阅的行情数据
        self.orderbooks: Dict[str, Dict[str, Any]] = {}
        self.tickers: Dict[str, Dict[str, Any]] = {}
        self.funding_rates: Dict[str, Dict[str, Any]] = {}
        
        # 订阅状态管理
        self.subscribed_symbols: Dict[str, Set[str]] = {
            'orderbook': set(),
            'ticker': set(),
            'funding_rate': set()
        }
        
        # 线程和锁
        self.lock = threading.Lock()
        self.subscription_thread = None
        self.is_running = False
        
        # 统计数据
        self.rest_stats = {}  # 键为 "exchange_id:symbol:data_type"
        
        self._initialized = True
        Logger.info("MarketDataService initialized")
    
    def add_exchange(self, exchange_id: str, exchange: ccxt.Exchange) -> None:
        """添加交易所实例"""
        self.exchanges[exchange_id] = exchange
        Logger.info(f"添加交易所: {exchange_id}")
        
        # 创建对应的 ccxtpro 实例
        pro_exchange = self._create_pro_exchange(exchange)
        if pro_exchange:
            self.pro_exchanges[exchange_id] = pro_exchange
            Logger.info(f"创建 ccxtpro 实例: {exchange_id}")
        else:
            Logger.warning(f"无法创建 {exchange_id} 的 ccxtpro 实例，将仅使用 REST API")
    
    def _create_pro_exchange(self, exchange: ccxt.Exchange) -> Optional[ccxtpro.Exchange]:
        """根据普通交易所实例创建对应的 ccxtpro 实例"""
        try:
            exchange_id = exchange.id
            
            if hasattr(exchange, 'proxies'):
                proxies = exchange.proxies
            else:
                proxies = {'http': None, 'https': None}
            
            # 基础配置
            config = {
                'enableRateLimit': True,
                'apiKey': exchange.apiKey,
                'secret': exchange.secret,
                'proxies': {
                    'http': proxies['http'],                 
                    'https': proxies['https'],
                },
                'aiohttp_proxy': proxies['http'],
                'ws_proxy': proxies['http']
            }
    
            # 添加特定交易所的配置
            if hasattr(exchange, 'password'):
                config['password'] = exchange.password
            
            config['options'] = {}
            # 复制交易类型设置
            if hasattr(exchange, 'options') and 'defaultType' in exchange.options:
                config['options']['defaultType'] = exchange.options['defaultType']
            
            # 创建异步交易所实例
            pro_exchange = getattr(ccxtpro, exchange_id)(config)

            if exchange.isSandboxModeEnabled:
                pro_exchange.set_sandbox_mode(True)
                Logger.info(f"{exchange_id} 使用沙盒模式")
        

            
            # 测试连接
            Logger.info(f"创建 {exchange_id} 的异步交易所实例成功")
            
            return pro_exchange
        except Exception as e:
            Logger.error(f"创建异步交易所实例失败: {exchange_id}, 错误: {str(e)}")
            return None

    def subscribe_orderbook(self, exchange_id: str, symbol: str) -> None:
        """订阅特定交易所和交易对的订单簿"""
        key = f"{exchange_id}:{symbol}"
        with self.lock:
            self.subscribed_symbols['orderbook'].add(key)
            # 初始化空数据结构
            self.orderbooks[key] = {'bids': [], 'asks': [], 'timestamp': 0}
        Logger.info(f"subscribe orderbook: {key}")
    
    
    def subscribe_funding_rate(self, exchange_id: str, symbol: str) -> None:
        """订阅特定交易所和交易对的资金费率"""
        key = f"{exchange_id}:{symbol}"
        with self.lock:
            self.subscribed_symbols['funding_rate'].add(key)
            # 初始化空数据结构
            self.funding_rates[key] = {'fundingRate': 0, 'timestamp': 0}
        Logger.info(f"subscribe funding rate: {key}")
    
    def get_orderbook(self, exchange_id: str, symbol: str) -> Dict[str, Any]:
        """获取特定交易所和交易对的订单簿"""
        key = f"{exchange_id}:{symbol}"
        with self.lock:
            return self.orderbooks.get(key, {'bids': [], 'asks': [], 'timestamp': 0})
    

    def get_funding_rate(self, exchange_id: str, symbol: str) -> Dict[str, Any]:
        """获取特定交易所和交易对的资金费率"""
        key = f"{exchange_id}:{symbol}"
        with self.lock:
            return self.funding_rates.get(key, {'fundingRate': 0, 'timestamp': 0})
    
    def start(self) -> None:
        """启动市场数据订阅"""
        if self.is_running:
            Logger.warning("market data service is running")
            return
            
        self.is_running = True
        self.subscription_thread = threading.Thread(target=self._run_subscription_loop, daemon=True)
        self.subscription_thread.start()
        Logger.info("market data service started")
    
    def stop(self) -> None:
        """停止市场数据订阅"""
        self.is_running = False
        if self.subscription_thread and self.subscription_thread.is_alive():
            self.subscription_thread.join(timeout=5)
        
        # 关闭所有异步交易所连接
        self.close_connections()
        
        Logger.info("market data service stopped")
    
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
        markets_loaded = False
        max_retries = 3
        retry_count = 0
        
        # 记录成功加载市场数据的交易所
        loaded_exchanges = set()
        
        while not markets_loaded and retry_count < max_retries:
            try:
                retry_count += 1
                Logger.info(f"try to load market data (try {retry_count}/{max_retries})...")
                
                # 加载所有交易所的市场数据
                for exchange_id, pro_exchange in list(self.pro_exchanges.items()):
                    # 如果已经成功加载，则跳过
                    if exchange_id in loaded_exchanges:
                        continue
                        
                    try:
                        Logger.info(f"loading market data for {exchange_id}...")
                        
                        # 设置超时
                        timeout = 20
                        try:
                            # 使用 asyncio.wait_for 设置超时
                            await asyncio.wait_for(pro_exchange.load_markets(), timeout)
                            Logger.info(f"{exchange_id} market data loaded")
                            # 标记为已加载成功
                            loaded_exchanges.add(exchange_id)
                        except (asyncio.TimeoutError, asyncio.CancelledError) as e:
                            Logger.error(f"{exchange_id} load market data failed: {str(e)}")
                            # 如果是最后一次尝试，则移除该交易所的异步实例
                            if retry_count == max_retries:
                                Logger.warning(f"remove {exchange_id} pro instance, will only use sync API")
                                self.pro_exchanges.pop(exchange_id, None)
                            continue
                        
                    except Exception as e:
                        error_msg = str(e)
                        Logger.error(f"load market data for {exchange_id} failed: {error_msg}")
                        
                        # 如果是最后一次尝试，则移除该交易所的异步实例
                        if retry_count == max_retries:
                            Logger.warning(f"remove {exchange_id} pro instance, will only use sync API")
                            self.pro_exchanges.pop(exchange_id, None)
                
                # 如果所有交易所都已加载或者已经没有异步实例，则标记为加载完成
                if len(loaded_exchanges) == len(self.pro_exchanges) or not self.pro_exchanges:
                    markets_loaded = True
                    Logger.info("market data loaded")
                
            except Exception as e:
                error_msg = str(e)
                Logger.error(f"load market data exception (try {retry_count}/{max_retries}): {error_msg}")
                
                if retry_count < max_retries:
                    wait_time = min(5, 2 ** retry_count)  # 指数退避，但最大等待5秒
                    Logger.info(f"will retry in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    Logger.error("reach max retry times, cannot load all market data")
                    # 尝试继续运行，即使市场数据没有完全加载
                    markets_loaded = True
                    Logger.warning("will try to continue running, but some functions may be affected")
        
        # 如果没有成功加载任何交易所的市场数据，则记录警告
        if not loaded_exchanges and self.pro_exchanges:
            Logger.warning("no market data loaded, will only use sync API")
            self.pro_exchanges.clear()
        
        # 开始订阅循环
        subscription_tasks = {}  # 用于跟踪活跃的订阅任务
        
        while self.is_running:
            try:
                # 创建所有订阅任务
                new_tasks = []
                
                # 订单簿订阅任务
                for key in self.subscribed_symbols['orderbook']:
                    exchange_id, symbol = key.split(':', 1)
                    task_key = f"orderbook:{key}"
                    
                    # 如果任务已经在运行，则跳过
                    if task_key in subscription_tasks and not subscription_tasks[task_key].done():
                        continue
                        
                    # 使用异步API获取订单簿
                    task = asyncio.create_task(self._fetch_orderbook(exchange_id, symbol))
                    
                    subscription_tasks[task_key] = task
                    new_tasks.append(task)
                

                
                # 资金费率订阅任务
                for key in self.subscribed_symbols['funding_rate']:
                    exchange_id, symbol = key.split(':', 1)
                    task_key = f"funding_rate:{key}"
                    
                    # 如果任务已经在运行，则跳过
                    if task_key in subscription_tasks and not subscription_tasks[task_key].done():
                        continue
                    
                    # 使用REST API获取资金费率
                    task = asyncio.create_task(self._fetch_funding_rate(exchange_id, symbol))
                    
                    subscription_tasks[task_key] = task
                    new_tasks.append(task)
                
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
                else:
                    # 如果没有新任务，等待一段时间再检查
                    await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                Logger.warning("subscription worker cancelled, will retry in 3 seconds")
                await asyncio.sleep(3)  # 被取消后等待3秒再重试
            except Exception as e:
                Logger.error(f"subscription worker exception: {str(e)}")
                await asyncio.sleep(3)  # 出错后等待3秒再重试
    
    async def _fetch_orderbook_for_symbols(self, exchange_id: str, symbols: List[str]) -> None:
        """优先使用WEBSOCKET获取订单簿"""

        try:
            # 优先使用异步交易所的fetch_order_book方法
            if exchange_id in self.pro_exchanges and not self.pro_exchanges[exchange_id].isSandboxModeEnabled:
                pro_exchange = self.pro_exchanges[exchange_id]
                orderbook = await asyncio.wait_for(pro_exchange.watch_order_book_for_symbols(symbols, limit=5), 30)
            else:
                # REST API 获取订单簿, 需要等待1秒
                time.sleep(1)
                # 如果没有异步交易所实例，使用同步交易所
                exchange = self.exchanges[exchange_id]
                orderbook = exchange.fetch_order_book_for_symbols(symbols)
                
            
            with self.lock:
                self.orderbooks[key] = {
                    'bids': orderbook['bids'],
                    'asks': orderbook['asks'],
                    'timestamp': orderbook['timestamp'] or int(time.time() * 1000)
                }
            #Logger.info(f"orderbook updated: {key[:30]:<30}, bid1:{orderbook['bids'][0] if orderbook['bids'] else None} ask1:{orderbook['asks'][0] if orderbook['asks'] else None}")
            
            
        except Exception as e:
            Logger.error(f"使用fetch_order_book获取订单簿失败: {key}, 错误: {str(e)}")
            # 确保有一个空的数据结构
            with self.lock:
                if key not in self.orderbooks:
                    self.orderbooks[key] = {'bids': [], 'asks': [], 'timestamp': int(time.time() * 1000)}
            
            # 出错后等待一段时间再重试
            await asyncio.sleep(5)
    
    
    async def _fetch_orderbook(self, exchange_id: str, symbol: str) -> None:
        """使用REST API获取订单簿"""
        key = f"{exchange_id}:{symbol}"
        try:
            # 优先使用异步交易所的fetch_order_book方法
            if exchange_id in self.pro_exchanges and not self.pro_exchanges[exchange_id].isSandboxModeEnabled:
                pro_exchange = self.pro_exchanges[exchange_id]
                orderbook = await asyncio.wait_for(pro_exchange.watch_order_book(symbol, limit=5), 30)
            else:
                # REST API 获取订单簿, 需要等待1秒
                time.sleep(1)
                # 如果没有异步交易所实例，使用同步交易所
                exchange = self.exchanges[exchange_id]
                orderbook = exchange.fetch_order_book(symbol)
                
            
            with self.lock:
                self.orderbooks[key] = {
                    'bids': orderbook['bids'],
                    'asks': orderbook['asks'],
                    'timestamp': orderbook['timestamp'] or int(time.time() * 1000)
                }
            #Logger.info(f"orderbook updated: {key[:30]:<30}, bid1:{orderbook['bids'][0] if orderbook['bids'] else None} ask1:{orderbook['asks'][0] if orderbook['asks'] else None}")
            
            
        except Exception as e:
            Logger.error(f"使用fetch_order_book获取订单簿失败: {key}, 错误: {str(e)}")
            # 确保有一个空的数据结构
            with self.lock:
                if key not in self.orderbooks:
                    self.orderbooks[key] = {'bids': [], 'asks': [], 'timestamp': int(time.time() * 1000)}
            
            # 出错后等待一段时间再重试
            await asyncio.sleep(5)
    
    async def _fetch_funding_rate(self, exchange_id: str, symbol: str) -> None:
        """使用REST API获取资金费率"""
        key = f"{exchange_id}:{symbol}"
        try:
            # 优先使用异步交易所的fetch_funding_rate方法
            if exchange_id in self.pro_exchanges:
                pro_exchange = self.pro_exchanges[exchange_id]
                funding_rate = await asyncio.wait_for(pro_exchange.fetch_funding_rate(symbol), 30)
            else:
                # 如果没有异步交易所实例，使用同步交易所
                exchange = self.exchanges[exchange_id]
                
                # 检查交易所是否支持fetch_funding_rate方法
                if hasattr(exchange, 'fetch_funding_rate'):
                    funding_rate = exchange.fetch_funding_rate(symbol)
                else:
                    # 如果不支持，尝试使用fetch_funding_rates并找到对应的交易对
                    all_rates = exchange.fetch_funding_rates()
                    funding_rate = all_rates.get(symbol, {'fundingRate': 0, 'timestamp': int(time.time() * 1000)})
            
            with self.lock:
                self.funding_rates[key] = {
                    'fundingRate': funding_rate.get('fundingRate', 0),
                    'timestamp': funding_rate.get('timestamp', int(time.time() * 1000))
                }
            # Logger.info(f"funding_rate updated:  {key[:30]:<30}, rate:{funding_rate.get('fundingRate', 0)}")
            
            # 等待一段时间再次获取（模拟订阅）
            await asyncio.sleep(60)  # 资金费率通常每小时或每8小时更新一次，所以60秒的间隔是合理的
        except Exception as e:
            Logger.error(f"使用fetch_funding_rate获取资金费率失败: {key}, 错误: {str(e)}")
            # 确保有一个空的数据结构
            with self.lock:
                if key not in self.funding_rates:
                    self.funding_rates[key] = {'fundingRate': 0, 'timestamp': int(time.time() * 1000)}
            
            # 出错后等待一段时间再重试
            await asyncio.sleep(30)
    
    def is_data_fresh(self, data_type: str, exchange_id: str, symbol: str, max_age_ms: int = 10000) -> bool:
        """检查数据是否新鲜（默认10秒内的数据视为新鲜）"""

        return True
    
        key = f"{exchange_id}:{symbol}"
        current_time = int(time.time() * 1000)
        
        with self.lock:
            if data_type == 'orderbook':
                data = self.orderbooks.get(key, {})
            elif data_type == 'funding_rate':
                data = self.funding_rates.get(key, {})
            else:
                return False
            
            timestamp = data.get('timestamp', 0)
            return (current_time - timestamp) <= max_age_ms 

    