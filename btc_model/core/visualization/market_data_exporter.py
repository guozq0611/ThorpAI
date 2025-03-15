"""
Author: AI Assistant

Create Date: 2025-03-14

Description:
    将市场数据导出到 InfluxDB，以便在 Grafana 中进行可视化。
    支持导出订单簿、行情和资金费率数据。

History:
    2025-03-14: 初始版本
"""

import asyncio
import threading
import time
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

# 尝试导入 InfluxDB 客户端，如果不存在则提供安装指南
try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
    INFLUXDB_AVAILABLE = True
except ImportError:
    INFLUXDB_AVAILABLE = False
    logging.warning("InfluxDB 客户端未安装，请使用 pip install influxdb-client 安装")

from btc_model.core.util.log_util import Logger


class MarketDataExporter:
    """
    市场数据导出器，将行情数据导出到 InfluxDB，以便在 Grafana 中进行可视化
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MarketDataExporter, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, 
                 influxdb_url: str = "http://localhost:8086", 
                 influxdb_token: str = "", 
                 influxdb_org: str = "my-org", 
                 influxdb_bucket: str = "market_data",
                 export_interval: int = 5):
        """初始化市场数据导出器"""
        if self._initialized:
            return
            
        self.influxdb_url = influxdb_url
        self.influxdb_token = influxdb_token
        self.influxdb_org = influxdb_org
        self.influxdb_bucket = influxdb_bucket
        self.export_interval = export_interval  # 导出间隔（秒）
        
        # InfluxDB 客户端
        self.influxdb_client = None
        self.write_api = None
        
        # 导出线程
        self.export_thread = None
        self.is_running = False
        
        # 市场数据服务引用
        self.market_data_service = None
        
        # 需要导出的交易对
        self.export_symbols = {
            'orderbook': set(),
            'ticker': set(),
            'funding_rate': set()
        }
        
        self._initialized = True
        Logger.info("MarketDataExporter initialized")
        
        # 检查 InfluxDB 客户端是否可用
        if not INFLUXDB_AVAILABLE:
            Logger.warning("InfluxDB 客户端未安装，无法导出数据到 Grafana")
    
    def set_market_data_service(self, market_data_service):
        """设置市场数据服务"""
        self.market_data_service = market_data_service
        Logger.info("设置市场数据服务")
    
    def add_export_symbol(self, data_type: str, exchange_id: str, symbol: str) -> None:
        """添加需要导出的交易对"""
        if data_type not in self.export_symbols:
            Logger.warning(f"不支持的数据类型: {data_type}")
            return
            
        key = f"{exchange_id}:{symbol}"
        self.export_symbols[data_type].add(key)
        Logger.info(f"添加导出交易对: {data_type} {key}")
    
    def remove_export_symbol(self, data_type: str, exchange_id: str, symbol: str) -> None:
        """移除需要导出的交易对"""
        if data_type not in self.export_symbols:
            return
            
        key = f"{exchange_id}:{symbol}"
        if key in self.export_symbols[data_type]:
            self.export_symbols[data_type].remove(key)
            Logger.info(f"移除导出交易对: {data_type} {key}")
    
    def start(self) -> None:
        """启动数据导出"""
        if self.is_running:
            Logger.warning("数据导出已在运行")
            return
            
        if not INFLUXDB_AVAILABLE:
            Logger.error("InfluxDB 客户端未安装，无法启动数据导出")
            return
            
        if not self.market_data_service:
            Logger.error("未设置市场数据服务，无法启动数据导出")
            return
            
        # 初始化 InfluxDB 客户端
        try:
            self.influxdb_client = InfluxDBClient(
                url=self.influxdb_url,
                token=self.influxdb_token,
                org=self.influxdb_org
            )
            self.write_api = self.influxdb_client.write_api(write_options=SYNCHRONOUS)
            Logger.info("InfluxDB 客户端初始化成功")
        except Exception as e:
            Logger.error(f"InfluxDB 客户端初始化失败: {str(e)}")
            return
            
        self.is_running = True
        self.export_thread = threading.Thread(target=self._run_export_loop, daemon=True)
        self.export_thread.start()
        Logger.info("数据导出已启动")
    
    def stop(self) -> None:
        """停止数据导出"""
        self.is_running = False
        if self.export_thread and self.export_thread.is_alive():
            self.export_thread.join(timeout=5)
            
        # 关闭 InfluxDB 客户端
        if self.influxdb_client:
            self.influxdb_client.close()
            self.influxdb_client = None
            self.write_api = None
            
        Logger.info("数据导出已停止")
    
    def _run_export_loop(self) -> None:
        """运行导出循环"""
        while self.is_running:
            try:
                # 导出订单簿数据
                self._export_orderbooks()
                
                # 导出行情数据
                self._export_tickers()
                
                # 导出资金费率数据
                self._export_funding_rates()
                
                # 等待下一次导出
                time.sleep(self.export_interval)
            except Exception as e:
                Logger.error(f"数据导出异常: {str(e)}")
                time.sleep(5)  # 出错后等待5秒再重试
    
    def _export_orderbooks(self) -> None:
        """导出订单簿数据"""
        if not self.market_data_service:
            return
            
        points = []
        
        for key in self.export_symbols['orderbook']:
            try:
                exchange_id, symbol = key.split(':', 1)
                orderbook = self.market_data_service.get_orderbook(exchange_id, symbol)
                
                if not orderbook or not orderbook.get('bids') or not orderbook.get('asks'):
                    continue
                    
                # 获取最优买卖价格和数量
                best_bid_price = orderbook['bids'][0][0] if orderbook['bids'] else 0
                best_bid_amount = orderbook['bids'][0][1] if orderbook['bids'] else 0
                best_ask_price = orderbook['asks'][0][0] if orderbook['asks'] else 0
                best_ask_amount = orderbook['asks'][0][1] if orderbook['asks'] else 0
                
                # 计算买卖盘深度（前5档）
                bid_depth = sum(item[1] for item in orderbook['bids'][:5]) if orderbook['bids'] else 0
                ask_depth = sum(item[1] for item in orderbook['asks'][:5]) if orderbook['asks'] else 0
                
                # 计算买卖价差
                spread = best_ask_price - best_bid_price if best_bid_price > 0 and best_ask_price > 0 else 0
                spread_percent = (spread / best_bid_price * 100) if best_bid_price > 0 else 0
                
                # 创建数据点
                point = Point("orderbook") \
                    .tag("exchange", exchange_id) \
                    .tag("symbol", symbol) \
                    .field("best_bid_price", float(best_bid_price)) \
                    .field("best_bid_amount", float(best_bid_amount)) \
                    .field("best_ask_price", float(best_ask_price)) \
                    .field("best_ask_amount", float(best_ask_amount)) \
                    .field("bid_depth", float(bid_depth)) \
                    .field("ask_depth", float(ask_depth)) \
                    .field("spread", float(spread)) \
                    .field("spread_percent", float(spread_percent)) \
                    .time(datetime.utcfromtimestamp(orderbook['timestamp'] / 1000))
                
                points.append(point)
            except Exception as e:
                Logger.error(f"导出订单簿数据异常: {key}, 错误: {str(e)}")
        
        # 批量写入数据
        if points:
            try:
                self.write_api.write(bucket=self.influxdb_bucket, record=points)
                Logger.debug(f"导出订单簿数据成功: {len(points)} 条")
            except Exception as e:
                Logger.error(f"写入订单簿数据到 InfluxDB 失败: {str(e)}")
    
    def _export_tickers(self) -> None:
        """导出行情数据"""
        if not self.market_data_service:
            return
            
        points = []
        
        for key in self.export_symbols['ticker']:
            try:
                exchange_id, symbol = key.split(':', 1)
                ticker = self.market_data_service.get_ticker(exchange_id, symbol)
                
                if not ticker:
                    continue
                    
                # 创建数据点
                point = Point("ticker") \
                    .tag("exchange", exchange_id) \
                    .tag("symbol", symbol) \
                    .field("bid", float(ticker.get('bid', 0))) \
                    .field("ask", float(ticker.get('ask', 0))) \
                    .field("last", float(ticker.get('last', 0))) \
                    .time(datetime.utcfromtimestamp(ticker.get('timestamp', int(time.time() * 1000)) / 1000))
                
                points.append(point)
            except Exception as e:
                Logger.error(f"导出行情数据异常: {key}, 错误: {str(e)}")
        
        # 批量写入数据
        if points:
            try:
                self.write_api.write(bucket=self.influxdb_bucket, record=points)
                Logger.debug(f"导出行情数据成功: {len(points)} 条")
            except Exception as e:
                Logger.error(f"写入行情数据到 InfluxDB 失败: {str(e)}")
    
    def _export_funding_rates(self) -> None:
        """导出资金费率数据"""
        if not self.market_data_service:
            return
            
        points = []
        
        for key in self.export_symbols['funding_rate']:
            try:
                exchange_id, symbol = key.split(':', 1)
                funding_rate = self.market_data_service.get_funding_rate(exchange_id, symbol)
                
                if not funding_rate:
                    continue
                    
                # 创建数据点
                point = Point("funding_rate") \
                    .tag("exchange", exchange_id) \
                    .tag("symbol", symbol) \
                    .field("rate", float(funding_rate.get('fundingRate', 0))) \
                    .time(datetime.utcfromtimestamp(funding_rate.get('timestamp', int(time.time() * 1000)) / 1000))
                
                points.append(point)
            except Exception as e:
                Logger.error(f"导出资金费率数据异常: {key}, 错误: {str(e)}")
        
        # 批量写入数据
        if points:
            try:
                self.write_api.write(bucket=self.influxdb_bucket, record=points)
                Logger.debug(f"导出资金费率数据成功: {len(points)} 条")
            except Exception as e:
                Logger.error(f"写入资金费率数据到 InfluxDB 失败: {str(e)}") 