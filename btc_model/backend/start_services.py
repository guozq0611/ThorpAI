import asyncio
import os
import sys
import threading
import uvicorn
from multiprocessing import Process

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from btc_model.core.backend.restapi_service import RestApiService
from btc_model.core.backend.websocket_server import WebSocketServer
from btc_model.manager.instance_manager import register_instance, global_instance
from btc_model.core.util.log_util import Logger
from btc_model.strategy.exchange_arbitrage.exchange_arbitrage_strategy import ExchangeArbitrageStrategy, setup_exchanges, load_pairs

def start_api_server():
    """启动FastAPI服务器"""
    Logger.info("正在启动REST API服务器...")
    api_server = RestApiService(ip="0.0.0.0", port=8000)
    
    # 注册API服务器实例
    register_instance("restapi_server", api_server)
    
    # 启动API服务器
    api_server.start()

def start_websocket_server():
    """启动WebSocket服务器"""
    Logger.info("正在启动WebSocket服务器...")
    ws_server = WebSocketServer(ip="0.0.0.0", port=8001)
    
    # 注册WebSocket服务器实例
    register_instance("websocket_server", ws_server)
    
    # 启动WebSocket服务器
    uvicorn.run(ws_server.app, host=ws_server.ip, port=ws_server.port, log_level="info")

def initialize_strategy():
    """初始化策略"""
    Logger.info("正在初始化交易所套利策略...")
    
    try:
        # 设置交易所
        Logger.info("设置交易所...")
        exchange_1, exchange_2, hedge_exchange = setup_exchanges(sandbox=True)
        
        # 加载交易对
        Logger.info("加载交易对...")
        pair_data = load_pairs()
        
        # 初始化策略
        Logger.info("初始化策略...")
        strategy = ExchangeArbitrageStrategy(
            exchange_1=exchange_1,
            exchange_2=exchange_2,
            hedge_exchange=hedge_exchange,
            pair_data=pair_data
        )
        
        # 注册策略实例
        register_instance("exchange_arbitrage_strategy", strategy)
        Logger.info("交易所套利策略初始化完成")
        
        return strategy
    except Exception as e:
        Logger.error(f"初始化策略失败: {e}")
        return None

def main():
    """主函数，启动所有服务"""
    Logger.info("正在启动ThorpAI服务...")
    
    try:
        # 初始化策略
        strategy = initialize_strategy()
        if not strategy:
            Logger.error("策略初始化失败，无法启动服务")
            return
            
        # 创建并启动API服务进程
        api_process = Process(target=start_api_server)
        api_process.start()
        Logger.info(f"API服务已在进程 {api_process.pid} 中启动")
        
        # 创建并启动WebSocket服务进程
        ws_process = Process(target=start_websocket_server)
        ws_process.start()
        Logger.info(f"WebSocket服务已在进程 {ws_process.pid} 中启动")
        
        # 等待子进程完成
        api_process.join()
        ws_process.join()
        
    except KeyboardInterrupt:
        Logger.info("收到中断信号，正在关闭服务...")
    except Exception as e:
        Logger.error(f"启动服务时出错: {e}")
    finally:
        Logger.info("ThorpAI服务已关闭")

if __name__ == "__main__":
    main() 