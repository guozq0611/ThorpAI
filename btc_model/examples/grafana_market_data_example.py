#!/usr/bin/env python
"""
示例脚本：将市场数据导出到 InfluxDB 以便在 Grafana 中可视化

使用方法：
1. 安装 InfluxDB（可以使用 Docker）
   docker run -d -p 8086:8086 --name influxdb influxdb:2.0

2. 安装 Grafana（可以使用 Docker）
   docker run -d -p 3000:3000 --name grafana grafana/grafana

3. 安装必要的 Python 包
   pip install influxdb-client

4. 运行此脚本
   python grafana_market_data_example.py

5. 在 Grafana 中配置 InfluxDB 数据源并创建仪表板
   - 访问 http://localhost:3000 (默认用户名/密码: admin/admin)
   - 添加 InfluxDB 数据源
   - 创建仪表板，使用 InfluxDB 数据源查询市场数据
"""

import asyncio
import time
import signal
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from btc_model.core.market.market_data_service import MarketDataService
from btc_model.core.visualization.market_data_exporter import MarketDataExporter
from btc_model.core.util.log_util import Logger
import ccxt.async_support as ccxt_async

# InfluxDB 配置
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "your_influxdb_token"  # 替换为您的 InfluxDB token
INFLUXDB_ORG = "my-org"
INFLUXDB_BUCKET = "market_data"

# 交易所配置
EXCHANGES = {
    "binance": {
        "apiKey": "",  # 可选，如果需要访问私有 API
        "secret": "",  # 可选，如果需要访问私有 API
        "enableRateLimit": True,
    },
    "okx": {
        "apiKey": "",  # 可选，如果需要访问私有 API
        "secret": "",  # 可选，如果需要访问私有 API
        "enableRateLimit": True,
    }
}

# 要监控的交易对
SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "LSK/USDT"
]

# 全局变量
market_data_service = None
market_data_exporter = None

async def setup_exchanges():
    """设置交易所"""
    global market_data_service
    
    # 创建市场数据服务
    market_data_service = MarketDataService()
    
    # 添加交易所
    for exchange_id, config in EXCHANGES.items():
        try:
            # 创建交易所实例
            exchange_class = getattr(ccxt_async, exchange_id)
            exchange = exchange_class(config)
            
            # 添加到市场数据服务
            market_data_service.add_exchange(exchange_id, exchange)
            Logger.info(f"添加交易所: {exchange_id}")
        except Exception as e:
            Logger.error(f"添加交易所失败: {exchange_id}, 错误: {str(e)}")
    
    # 启动市场数据服务
    market_data_service.start()
    Logger.info("市场数据服务已启动")
    
    # 订阅交易对
    for symbol in SYMBOLS:
        for exchange_id in EXCHANGES.keys():
            try:
                # 订阅订单簿
                market_data_service.subscribe_orderbook(exchange_id, symbol)
                
                # 如果是合约交易对，订阅资金费率
                if symbol.endswith("USDT:USDT") or symbol.endswith("USD:USD"):
                    market_data_service.subscribe_funding_rate(exchange_id, symbol)
            except Exception as e:
                Logger.warning(f"订阅交易对失败: {exchange_id}:{symbol}, 错误: {str(e)}")

def setup_exporter():
    """设置数据导出器"""
    global market_data_service, market_data_exporter
    
    # 创建数据导出器
    market_data_exporter = MarketDataExporter(
        influxdb_url=INFLUXDB_URL,
        influxdb_token=INFLUXDB_TOKEN,
        influxdb_org=INFLUXDB_ORG,
        influxdb_bucket=INFLUXDB_BUCKET,
        export_interval=5  # 每5秒导出一次数据
    )
    
    # 设置市场数据服务
    market_data_exporter.set_market_data_service(market_data_service)
    
    # 添加要导出的交易对
    for symbol in SYMBOLS:
        for exchange_id in EXCHANGES.keys():
            # 导出订单簿数据
            market_data_exporter.add_export_symbol("orderbook", exchange_id, symbol)
            
            # 如果是合约交易对，导出资金费率数据
            if symbol.endswith("USDT:USDT") or symbol.endswith("USD:USD"):
                market_data_exporter.add_export_symbol("funding_rate", exchange_id, symbol)
    
    # 启动数据导出
    market_data_exporter.start()
    Logger.info("数据导出已启动")

def cleanup():
    """清理资源"""
    global market_data_service, market_data_exporter
    
    # 停止数据导出
    if market_data_exporter:
        market_data_exporter.stop()
        Logger.info("数据导出已停止")
    
    # 停止市场数据服务
    if market_data_service:
        market_data_service.stop()
        Logger.info("市场数据服务已停止")

def signal_handler(sig, frame):
    """信号处理函数"""
    Logger.info(f"接收到信号 {sig}，正在退出...")
    cleanup()
    sys.exit(0)

async def main():
    """主函数"""
    try:
        # 设置交易所
        await setup_exchanges()
        
        # 设置数据导出器
        setup_exporter()
        
        # 注册信号处理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 运行一段时间
        Logger.info("程序已启动，按 Ctrl+C 退出")
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        Logger.error(f"程序异常: {str(e)}")
    finally:
        cleanup()

if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main()) 