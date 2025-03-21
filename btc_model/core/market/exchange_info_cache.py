import os
import json
import time
import pymysql
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import ccxt
import threading

from btc_model.core.util.log_util import Logger
from btc_model.core.util.file_util import FileUtil
from btc_model.setting.setting import get_settings


class ExchangeInfoCache:
    """
    交易所基础信息缓存类 - MySQL版本
    
    缓存内容：
    1. 币种精度
    2. 交易手续费
    3. 提现手续费
    4. 交易对信息（例如最小交易额、价格精度、数量精度等）
    5. 网络信息（支持的网络ID、费用等）
    
    数据更新：
    - 首次访问时自动加载缓存
    - 提供手动更新接口
    - 设置缓存有效期，超过有效期自动更新
    """
    # 单例模式
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ExchangeInfoCache, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, cache_expire_days=7):
        if self._initialized:
            return
            
        with self._lock:
            if self._initialized:  # 双重检查锁定
                return
            

            settings = get_settings('database.mysql')

            db_user = settings['user']
            db_password = settings['password']
            db_host = settings['host']
            db_port = settings['port']
            db_database = settings['database']


            self.db_config = {
                'host': db_host,
                'user': db_user,
                'password': db_password,
                'database': db_database,
                'port': db_port,
                'cursorclass': pymysql.cursors.DictCursor
            }
            
            self.cache_expire_days = cache_expire_days
            self.conn_pool = {}
            
            # 初始化数据库
            self._init_db()
            self._initialized = True
    
    def _get_connection(self):
        """获取数据库连接，使用线程本地存储确保线程安全"""
        thread_id = threading.get_ident()
        
        if thread_id not in self.conn_pool or self.conn_pool[thread_id] is None:
            try:
                conn = pymysql.connect(**self.db_config)
                self.conn_pool[thread_id] = conn
            except Exception as e:
                Logger.error(f"MySQL连接失败: {e}")
                raise
                
        return self.conn_pool[thread_id]
    
    def _init_db(self):
        """初始化数据库表结构"""
        try:
            connection = self._get_connection()
            with connection.cursor() as cursor:
                # 创建币种信息表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS currency_info (
                    exchange_id VARCHAR(50),
                    currency VARCHAR(20),
                    precision_value INT,
                    min_withdraw DOUBLE,
                    max_withdraw DOUBLE,
                    withdraw_fee DOUBLE,
                    active BOOLEAN,
                    updated_at TIMESTAMP,
                    data LONGTEXT,
                    PRIMARY KEY (exchange_id, currency)
                )
                ''')
                
                # 创建交易对信息表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS symbol_info (
                    exchange_id VARCHAR(50),
                    symbol VARCHAR(50),
                    base_currency VARCHAR(20),
                    quote_currency VARCHAR(20), 
                    price_precision INT,
                    amount_precision INT,
                    min_amount DOUBLE,
                    min_cost DOUBLE,
                    maker_fee DOUBLE,
                    taker_fee DOUBLE,
                    active BOOLEAN,
                    updated_at TIMESTAMP,
                    data LONGTEXT,
                    PRIMARY KEY (exchange_id, symbol)
                )
                ''')
                
                # 创建网络信息表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS network_info (
                    exchange_id VARCHAR(50),
                    currency VARCHAR(20),
                    network VARCHAR(50),
                    withdraw_fee DOUBLE,
                    withdraw_min DOUBLE,
                    withdraw_max DOUBLE,
                    active BOOLEAN,
                    updated_at TIMESTAMP,
                    data LONGTEXT,
                    PRIMARY KEY (exchange_id, currency, network)
                )
                ''')
                
                # 创建交易所费率表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS exchange_fees (
                    exchange_id VARCHAR(50),
                    market_type VARCHAR(20),  -- spot, swap, futures, margin, etc.
                    maker_fee DOUBLE,
                    taker_fee DOUBLE,
                    updated_at TIMESTAMP,
                    PRIMARY KEY (exchange_id, market_type)
                )
                ''')
                
                # 创建最后更新时间记录表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS last_update (
                    exchange_id VARCHAR(50) PRIMARY KEY,
                    last_update_time TIMESTAMP
                )
                ''')
                
                connection.commit()
                Logger.info("MySQL数据库表结构初始化成功")
                
        except Exception as e:
            Logger.error(f"初始化数据库失败: {e}")
            raise
    
    def _need_update(self, exchange_id: str) -> bool:
        """检查是否需要更新缓存数据"""
        connection = self._get_connection()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT last_update_time FROM last_update WHERE exchange_id = %s", 
                    (exchange_id,)
                )
                result = cursor.fetchone()
                
                if result is None:
                    return True
                    
                last_update_time = result['last_update_time']
                now = datetime.now()
                
                # 如果上次更新时间距今超过缓存有效期，需要更新
                return (now - last_update_time) > timedelta(days=self.cache_expire_days)
                
        except Exception as e:
            Logger.error(f"检查更新时间失败: {exchange_id}, 错误: {e}")
            return True
    
    def update_exchange_info(self, exchange: ccxt.Exchange, force: bool = False) -> bool:
        """
        更新指定交易所的所有基础信息
        
        Args:
            exchange: ccxt交易所实例
            force: 是否强制更新，即使缓存未过期
            
        Returns:
            bool: 是否成功更新
        """
        exchange_id = exchange.id
        
        # 如果不强制更新且缓存未过期，则不更新
        if not force and not self._need_update(exchange_id):
            Logger.info(f"交易所 {exchange_id} 的缓存数据有效，无需更新")
            return True
            
        try:
            # 更新币种信息
            self._update_currencies(exchange)
            
            # 更新交易对信息
            self._update_symbols(exchange)
            
            # 更新交易所费率
            self._update_fees(exchange)
            
            # 更新网络信息
            self._update_networks(exchange)
            
            # 更新最后更新时间
            self._update_last_update_time(exchange_id)
            
            Logger.info(f"已成功更新交易所 {exchange_id} 的所有基础信息")
            return True
            
        except Exception as e:
            Logger.error(f"更新交易所 {exchange_id} 信息失败: {e}")
            return False
    
    def _update_currencies(self, exchange: ccxt.Exchange):
        """更新币种信息"""
        exchange_id = exchange.id
        connection = self._get_connection()
        
        try:
            # 获取所有币种信息
            currencies = exchange.fetch_currencies()
            
            # 批量更新
            with connection.cursor() as cursor:
                for code, currency in currencies.items():
                    try:
                        precision = currency.get('precision', 8)
                        min_withdraw = float(currency.get('limits', {}).get('withdraw', {}).get('min', 0))
                        max_withdraw = float(currency.get('limits', {}).get('withdraw', {}).get('max', 0))
                        withdraw_fee = float(currency.get('fee', 0))
                        active = bool(currency.get('active', True))
                        data = json.dumps(currency)
                        
                        cursor.execute('''
                        INSERT INTO currency_info
                        (exchange_id, currency, precision_value, min_withdraw, max_withdraw, withdraw_fee, active, updated_at, data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        precision_value = VALUES(precision_value),
                        min_withdraw = VALUES(min_withdraw),
                        max_withdraw = VALUES(max_withdraw),
                        withdraw_fee = VALUES(withdraw_fee),
                        active = VALUES(active),
                        updated_at = VALUES(updated_at),
                        data = VALUES(data)
                        ''', (
                            exchange_id, code, precision, min_withdraw, max_withdraw, withdraw_fee, 
                            active, datetime.now(), data
                        ))
                    except Exception as e:
                        Logger.error(f"更新币种 {code} 信息失败: {e}")
                        continue
                        
                connection.commit()
                Logger.info(f"已更新交易所 {exchange_id} 的 {len(currencies)} 个币种信息")
                
        except Exception as e:
            connection.rollback()
            Logger.error(f"更新币种信息失败: {e}")
            raise
    
    def _update_symbols(self, exchange: ccxt.Exchange):
        """更新交易对信息"""
        exchange_id = exchange.id
        connection = self._get_connection()
        
        try:
            # 获取所有交易对信息
            markets = exchange.fetch_markets()
            
            # 批量更新
            with connection.cursor() as cursor:
                for market in markets:
                    try:
                        symbol = market['symbol']
                        base = market['base']
                        quote = market['quote']
                        price_precision = market.get('precision', {}).get('price', 8)
                        amount_precision = market.get('precision', {}).get('amount', 8)
                        min_amount = float(market.get('limits', {}).get('amount', {}).get('min', 0))
                        min_cost = float(market.get('limits', {}).get('cost', {}).get('min', 0))
                        maker_fee = float(market.get('maker', 0))
                        taker_fee = float(market.get('taker', 0))
                        active = bool(market.get('active', True))
                        data = json.dumps(market)
                        
                        cursor.execute('''
                        INSERT INTO symbol_info
                        (exchange_id, symbol, base_currency, quote_currency, price_precision, amount_precision, 
                        min_amount, min_cost, maker_fee, taker_fee, active, updated_at, data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        base_currency = VALUES(base_currency),
                        quote_currency = VALUES(quote_currency),
                        price_precision = VALUES(price_precision),
                        amount_precision = VALUES(amount_precision),
                        min_amount = VALUES(min_amount),
                        min_cost = VALUES(min_cost),
                        maker_fee = VALUES(maker_fee),
                        taker_fee = VALUES(taker_fee),
                        active = VALUES(active),
                        updated_at = VALUES(updated_at),
                        data = VALUES(data)
                        ''', (
                            exchange_id, symbol, base, quote, price_precision, amount_precision,
                            min_amount, min_cost, maker_fee, taker_fee, active, 
                            datetime.now(), data
                        ))
                    except Exception as e:
                        Logger.error(f"更新交易对 {market.get('symbol', '未知')} 信息失败: {e}")
                        continue
                        
                connection.commit()
                Logger.info(f"已更新交易所 {exchange_id} 的 {len(markets)} 个交易对信息")
                
        except Exception as e:
            connection.rollback()
            Logger.error(f"更新交易对信息失败: {e}")
            raise
    
    def _update_fees(self, exchange: ccxt.Exchange):
        """更新交易所费率信息"""
        exchange_id = exchange.id
        connection = self._get_connection()
        
        try:
            # 从交易所获取费率信息
            fees = {}
            
            # 尝试使用交易所API获取费率
            try:
                if hasattr(exchange, 'fetch_trading_fees'):
                    fees = exchange.fetch_trading_fees()
            except Exception as e:
                Logger.warning(f"无法通过API获取交易所 {exchange_id} 的费率，使用默认值: {e}")
            
            # 使用交易所对象中的费率信息
            if not fees and hasattr(exchange, 'fees') and 'trading' in exchange.fees:
                fees = {'trading': exchange.fees['trading']}
            
            # 如果没有获取到费率信息，使用默认值
            if not fees or 'trading' not in fees:
                # 尝试从配置文件获取费率
                from btc_model.core.util.crypto_util import CryptoUtil
                try:
                    fees = CryptoUtil.get_trading_fees(exchange)
                except Exception:
                    # 使用通用默认值
                    fees = {
                        'spot': {'maker': 0.001, 'taker': 0.001},
                        'swap': {'maker': 0.0002, 'taker': 0.0005},
                        'futures': {'maker': 0.0002, 'taker': 0.0005},
                        'margin': {'maker': 0.001, 'taker': 0.001}
                    }
            
            # 更新数据库
            with connection.cursor() as cursor:
                for market_type, fee_info in fees.items():
                    if isinstance(fee_info, dict) and ('maker' in fee_info or 'taker' in fee_info):
                        maker_fee = fee_info.get('maker', 0.001)
                        taker_fee = fee_info.get('taker', 0.001)
                        
                        if market_type == 'trading':
                            market_type = 'spot'
                            
                        cursor.execute('''
                        INSERT INTO exchange_fees
                        (exchange_id, market_type, maker_fee, taker_fee, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        maker_fee = VALUES(maker_fee),
                        taker_fee = VALUES(taker_fee),
                        updated_at = VALUES(updated_at)
                        ''', (
                            exchange_id, market_type, maker_fee, taker_fee, datetime.now()
                        ))
                
                connection.commit()
                Logger.info(f"已更新交易所 {exchange_id} 的费率信息")
                
        except Exception as e:
            connection.rollback()
            Logger.error(f"更新交易所费率信息失败: {e}")
            raise
    
    def _update_networks(self, exchange: ccxt.Exchange):
        """更新网络信息"""
        exchange_id = exchange.id
        connection = self._get_connection()
        
        try:
            # 获取所有币种信息
            currencies = exchange.fetch_currencies()
            
            # 批量更新网络信息
            with connection.cursor() as cursor:
                for code, currency in currencies.items():
                    try:
                        networks = {}
                        
                        # 处理不同交易所的网络信息格式
                        if 'networks' in currency:
                            networks = currency['networks']
                        elif 'info' in currency and isinstance(currency['info'], dict):
                            # 处理OKX等交易所的特殊格式
                            if 'chains' in currency['info']:
                                for chain in currency['info']['chains']:
                                    chain_name = chain.get('chain', '')
                                    if chain_name:
                                        fee = float(chain.get('minFee', 0))
                                        min_withdraw = float(chain.get('minWd', 0))
                                        max_withdraw = float(chain.get('maxWd', 0) or 0)
                                        active = True
                                        networks[chain_name] = {
                                            'id': chain_name,
                                            'network': chain_name,
                                            'fee': fee,
                                            'min': min_withdraw,
                                            'max': max_withdraw,
                                            'active': active
                                        }
                        
                        # 如果没有找到网络信息，使用默认值
                        if not networks:
                            default_fee = float(currency.get('fee', 0))
                            if default_fee > 0:
                                networks['default'] = {
                                    'id': 'default',
                                    'network': 'default',
                                    'fee': default_fee,
                                    'min': float(currency.get('limits', {}).get('withdraw', {}).get('min', 0)),
                                    'max': float(currency.get('limits', {}).get('withdraw', {}).get('max', 0) or 0),
                                    'active': True
                                }
                        
                        # 将网络信息写入数据库
                        for network_id, network_info in networks.items():
                            if isinstance(network_info, dict):
                                network_name = network_info.get('network', network_id)
                                fee = float(network_info.get('fee', 0))
                                min_withdraw = float(network_info.get('min', 0))
                                max_withdraw = float(network_info.get('max', 0) or 0)
                                active = bool(network_info.get('active', True))
                                data = json.dumps(network_info)
                                
                                cursor.execute('''
                                INSERT INTO network_info
                                (exchange_id, currency, network, withdraw_fee, withdraw_min, withdraw_max, active, updated_at, data)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                withdraw_fee = VALUES(withdraw_fee),
                                withdraw_min = VALUES(withdraw_min),
                                withdraw_max = VALUES(withdraw_max),
                                active = VALUES(active),
                                updated_at = VALUES(updated_at),
                                data = VALUES(data)
                                ''', (
                                    exchange_id, code, network_name, fee, min_withdraw, max_withdraw, 
                                    active, datetime.now(), data
                                ))
                                
                    except Exception as e:
                        Logger.error(f"更新币种 {code} 的网络信息失败: {e}")
                        continue
                        
                connection.commit()
                Logger.info(f"已更新交易所 {exchange_id} 的网络信息")
                
        except Exception as e:
            connection.rollback()
            Logger.error(f"更新网络信息失败: {e}")
            raise
    
    def _update_last_update_time(self, exchange_id: str):
        """更新最后更新时间"""
        connection = self._get_connection()
        
        try:
            with connection.cursor() as cursor:
                now = datetime.now()
                cursor.execute('''
                INSERT INTO last_update
                (exchange_id, last_update_time)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE
                last_update_time = VALUES(last_update_time)
                ''', (exchange_id, now))
                
                connection.commit()
                
        except Exception as e:
            connection.rollback()
            Logger.error(f"更新最后更新时间失败: {exchange_id}, 错误: {e}")
            raise
    
    def get_currency_info(self, exchange_id: str, currency: str) -> Optional[Dict]:
        """获取币种信息"""
        connection = self._get_connection()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute('''
                SELECT * FROM currency_info
                WHERE exchange_id = %s AND currency = %s
                ''', (exchange_id, currency))
                
                result = cursor.fetchone()
                return result
                
        except Exception as e:
            Logger.error(f"获取币种信息失败: {exchange_id}, {currency}, 错误: {e}")
            return None
    
    def get_symbol_info(self, exchange_id: str, symbol: str) -> Optional[Dict]:
        """获取交易对信息"""
        connection = self._get_connection()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute('''
                SELECT * FROM symbol_info
                WHERE exchange_id = %s AND symbol = %s
                ''', (exchange_id, symbol))
                
                result = cursor.fetchone()
                return result
                
        except Exception as e:
            Logger.error(f"获取交易对信息失败: {exchange_id}, {symbol}, 错误: {e}")
            return None
    
    def get_trading_fees(self, exchange_id: str, market_type: str = 'spot') -> Dict:
        """获取交易所费率"""
        connection = self._get_connection()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute('''
                SELECT maker_fee, taker_fee FROM exchange_fees
                WHERE exchange_id = %s AND market_type = %s
                ''', (exchange_id, market_type))
                
                result = cursor.fetchone()
                if result is None:
                    # 如果没有找到，返回默认值
                    return {
                        'maker': 0.001 if market_type == 'spot' else 0.0002,
                        'taker': 0.001 if market_type == 'spot' else 0.0005
                    }
                    
                return {
                    'maker': result['maker_fee'],
                    'taker': result['taker_fee']
                }
                
        except Exception as e:
            Logger.error(f"获取交易费率失败: {exchange_id}, {market_type}, 错误: {e}")
            # 返回默认值
            return {
                'maker': 0.001 if market_type == 'spot' else 0.0002,
                'taker': 0.001 if market_type == 'spot' else 0.0005
            }
    
    def get_withdrawal_fee(self, exchange_id: str, currency: str, network: str = None) -> float:
        """获取提现手续费"""
        connection = self._get_connection()
        
        try:
            with connection.cursor() as cursor:
                if network:
                    # 查找指定网络的提现费
                    cursor.execute('''
                    SELECT withdraw_fee FROM network_info
                    WHERE exchange_id = %s AND currency = %s AND network = %s
                    ''', (exchange_id, currency, network))
                    
                    result = cursor.fetchone()
                    if result is not None:
                        return result['withdraw_fee']
                
                # 如果没有指定网络或没有找到特定网络的费用，获取所有可用网络中最小的费用
                cursor.execute('''
                SELECT MIN(withdraw_fee) as min_fee FROM network_info
                WHERE exchange_id = %s AND currency = %s AND active = 1
                ''', (exchange_id, currency))
                
                result = cursor.fetchone()
                if result is not None and result['min_fee'] is not None:
                    return result['min_fee']
                
                # 如果网络表中没有数据，尝试从币种表获取
                cursor.execute('''
                SELECT withdraw_fee FROM currency_info
                WHERE exchange_id = %s AND currency = %s
                ''', (exchange_id, currency))
                
                result = cursor.fetchone()
                if result is not None:
                    return result['withdraw_fee']
                    
                # 如果都没有找到，返回0
                return 0
                
        except Exception as e:
            Logger.error(f"获取提现费用失败: {exchange_id}, {currency}, {network}, 错误: {e}")
            return 0
    
    def get_all_currencies(self, exchange_id: str) -> List[str]:
        """获取交易所支持的所有币种"""
        connection = self._get_connection()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute('''
                SELECT currency FROM currency_info
                WHERE exchange_id = %s AND active = 1
                ''', (exchange_id,))
                
                return [row['currency'] for row in cursor.fetchall()]
                
        except Exception as e:
            Logger.error(f"获取所有币种失败: {exchange_id}, 错误: {e}")
            return []
    
    def get_all_symbols(self, exchange_id: str, quote_currency: str = None) -> List[str]:
        """获取交易所支持的所有交易对
        
        Args:
            exchange_id: 交易所ID
            quote_currency: 指定计价币种，如 'USDT'
            
        Returns:
            List[str]: 交易对列表
        """
        connection = self._get_connection()
        
        try:
            with connection.cursor() as cursor:
                if quote_currency:
                    cursor.execute('''
                    SELECT symbol FROM symbol_info
                    WHERE exchange_id = %s AND quote_currency = %s AND active = 1
                    ''', (exchange_id, quote_currency))
                else:
                    cursor.execute('''
                    SELECT symbol FROM symbol_info
                    WHERE exchange_id = %s AND active = 1
                    ''', (exchange_id,))
                
                return [row['symbol'] for row in cursor.fetchall()]
                
        except Exception as e:
            Logger.error(f"获取所有交易对失败: {exchange_id}, 错误: {e}")
            return []
    
    def get_symbol_precision(self, exchange_id: str, symbol: str) -> Dict[str, int]:
        """获取交易对的价格和数量精度"""
        symbol_info = self.get_symbol_info(exchange_id, symbol)
        if symbol_info:
            return {
                'price': symbol_info['price_precision'],
                'amount': symbol_info['amount_precision']
            }
        return {'price': 8, 'amount': 8}  # 默认精度
    
    def close(self):
        """关闭所有数据库连接"""
        for thread_id, conn in list(self.conn_pool.items()):
            if conn:
                try:
                    conn.close()
                except:
                    pass
                self.conn_pool[thread_id] = None
            
    def __del__(self):
        """析构函数，确保数据库连接关闭"""
        self.close()

# 系统初始化函数，预加载交易所信息到缓存
def preload_exchange_info(exchanges: Dict[str, ccxt.Exchange], async_load: bool = True,
                         db_config: Dict = None):
    """
    预加载交易所基础信息到缓存中
    
    Args:
        exchanges: 交易所字典，格式为 {exchange_id: exchange_instance}
        async_load: 是否异步加载，默认为 True
        db_config: MySQL数据库配置，默认为None，使用默认配置
        
    Returns:
        ExchangeInfoCache: 缓存实例
    """
    # 使用传入的数据库配置或默认配置初始化缓存
    if db_config:
        cache = ExchangeInfoCache(**db_config)
    else:
        cache = ExchangeInfoCache()
    
    def load_exchange_info(exchange_id, exchange):
        try:
            Logger.info(f"正在预加载交易所 {exchange_id} 的基础信息...")
            cache.update_exchange_info(exchange)
            Logger.info(f"交易所 {exchange_id} 的基础信息预加载完成")
        except Exception as e:
            Logger.error(f"预加载交易所 {exchange_id} 信息失败: {e}")
    
    if async_load:
        threads = []
        
        for exchange_id, exchange in exchanges.items():
            thread = threading.Thread(
                target=load_exchange_info,
                args=(exchange_id, exchange),
                daemon=True
            )
            threads.append(thread)
            thread.start()
            
        # 不等待线程完成，让它们在后台运行
        Logger.info(f"已启动 {len(threads)} 个后台线程预加载交易所信息")
    else:
        for exchange_id, exchange in exchanges.items():
            load_exchange_info(exchange_id, exchange)
    
    return cache

if __name__ == "__main__":
    # 测试代码
    from btc_model.strategy.exchange_arbitrage.exchange_arbitrage_strategy import setup_exchanges


    exchanges = setup_exchanges(sandbox=False)
    exchange_binance = exchanges['exchange_1']
    exchange_okx = exchanges['exchange_2']

    cache = preload_exchange_info({
        'exchange_binance': exchange_binance,
        'exchange_okx': exchange_okx
    }, async_load=False)

    print(cache.get_currency_info('exchange_binance', 'BTC'))
    print(cache.get_symbol_info('exchange_binance', 'BTC/USDT'))
    print(cache.get_trading_fees('exchange_binance', 'spot'))
    print(cache.get_withdrawal_fee('exchange_binance', 'BTC'))
    print(cache.get_all_currencies('exchange_binance'))
    print(cache.get_all_symbols('exchange_binance'))
