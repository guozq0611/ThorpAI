"""
服务管理模块

用于注册和初始化应用程序中常用的服务。
该模块应在应用启动时被导入一次。
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import uvicorn
from typing import Dict, Any, Optional
from btc_model.manager.instance_manager import register_instance
from btc_model.core.util.log_util import Logger


from btc_model.core.util.db_util import DBUtil
from btc_model.core.util.cache_util import CacheUtil
from btc_model.core.common.context import Context
from btc_model.setting.setting import get_settings


# 用于运行异步 WebSocket 服务器的线程函数
def run_websocket_server_thread(websocket_server):
    """在独立线程中运行 WebSocket 服务器"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(websocket_server.run())
    except Exception as e:
        Logger.error(f"WebSocket 服务器运行出错: {e}")
    finally:
        loop.close()


# 用于运行异步 REST API 服务器的线程函数
def run_restapi_server_thread(restapi_server):
    """在独立线程中运行 REST API 服务器"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(restapi_server.run())
    except Exception as e:
        Logger.error(f"REST API 服务器运行出错: {e}")
    finally:
        loop.close()


class ServiceManager:
    """服务管理类，负责初始化和管理系统中的关键实例"""

    def __init__(self):
        """初始化全局实例管理器"""
        self.websocket_service = None
        self.restapi_service = None
        self.ws_thread = None
        self.api_thread = None
        self.is_initialized = False

    def initialize(self):
        """初始化所有服务"""
        if self.is_initialized:
            Logger.warning("服务已经初始化，跳过重复初始化")
            return
        
        try:
            # 初始化 WebSocket 服务器
            self.initialize_websocket_server()
            
            # 初始化 REST API 服务器
            self.initialize_restapi_server()
            
            self.is_initialized = True
            Logger.info("服务初始化完成")
        except Exception as e:
            Logger.error(f"初始化服务时出错: {e}")
            raise

    def initialize_websocket_server(self):
        """初始化 WebSocket 服务器"""
        # 创建 WebSocket 服务器实例
        from btc_model.core.backend.websocket_service import WebSocketService

        self.websocket_service = WebSocketService(ip="0.0.0.0", port=8001)
        
        # 注册 WebSocket 服务器实例
        register_instance("websocket_service", self.websocket_service)
        
        # 在单独的线程中启动 WebSocket 服务器
        ws_thread = threading.Thread(
            target=run_websocket_server_thread, 
            args=(self.websocket_service,),
            daemon=True  # 设为守护线程，主程序退出时自动终止
        )
        ws_thread.start()
        self.ws_thread = ws_thread
        
        Logger.info("WebSocket 服务器已初始化并启动")

    def initialize_restapi_server(self):
        """初始化 REST API 服务器"""
        # 创建 REST API 服务器实例
        from btc_model.core.backend.restapi_service import RestApiService
        self.restapi_service = RestApiService(ip="0.0.0.0", port=8002)
        
        # 注册 REST API 服务器实例
        register_instance("restapi_service", self.restapi_service)
        
        # 在单独的线程中启动 REST API 服务器
        api_thread = threading.Thread(
            target=run_restapi_server_thread, 
            args=(self.restapi_service,),
            daemon=True  # 设为守护线程，主程序退出时自动终止
        )
        api_thread.start()
        self.api_thread = api_thread
        
        Logger.info("REST API 服务器已初始化并启动")

    def shutdown(self):
        """关闭并清理所有服务"""
        Logger.info("正在关闭服务...")
        
        # 在此添加关闭资源的代码
        # (WebSocket 和 REST API 服务器会随着主线程结束而终止，因为它们是守护线程)
        
        self.is_initialized = False
        Logger.info("服务已关闭")

    def get_websocket_service(self):
        """获取 WebSocket 服务器实例"""
        return self.websocket_service

    def get_restapi_service(self):
        """获取 REST API 服务器实例"""
        return self.restapi_service
    
# 创建服务管理器的单例
_service_manager = ServiceManager()

def initialize_service_manager():
    """初始化所有服务"""
    _service_manager.initialize()

def get_service_manager():
    """获取服务管理器"""
    return _service_manager

def shutdown_service_manager():
    """关闭所有服务"""
    _service_manager.shutdown()


# def init_instances():
#     """初始化所有服务"""
#     # 注册常规实例
#     register_instance("db_util", lambda: DBUtil())
#     register_instance("cache_util", lambda: CacheUtil())
#     register_instance("context", lambda: Context())
    
#     # 特殊处理 WebSocketServer
#     try:
#         from btc_model.core.backend.websocket_service import WebSocketService
        
#         # 创建 WebSocketServer 实例
#         websocket_server = WebSocketService(
#             ip=get_settings("websocket.server").get("host", "0.0.0.0"), 
#             port=get_settings("websocket.server").get("port", 8001)
#         )
        
#         # 注册实例
#         register_instance("websocket_service", websocket_server)
        
#         # 在单独的线程中启动 WebSocket 服务器
#         ws_thread = threading.Thread(
#             target=run_websocket_server_thread, 
#             args=(websocket_server,),
#             daemon=True  # 设为守护线程，主程序退出时自动终止
#         )
#         ws_thread.start()
        
#         # 等待服务器启动 (可选，视情况调整或移除)
#         time.sleep(0.5)
        
#         print("WebSocket 服务器已在后台启动")
#     except ImportError as e:
#         print(f"警告: WebSocketServer 模块无法导入: {e}")
#     except Exception as e:
#         print(f"启动 WebSocket 服务器出错: {e}")


# def run_api_server_thread(api_app):
#     """在独立线程中运行 API 服务器"""
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     try:
#         # 使用 uvicorn 在事件循环中运行 FastAPI 应用
#         config = uvicorn.Config(
#             api_app, 
#             host="0.0.0.0", 
#             port=8002, 
#             loop="asyncio"
#         )
#         server = uvicorn.Server(config)
#         loop.run_until_complete(server.serve())
#     except Exception as e:
#         print(f"API 服务器运行出错: {e}")
#     finally:
#         loop.close()


# def initialize_api_service():
#     """初始化并启动 API 服务"""
#     # 导入 API 应用
#     from btc_model.backend.restapi_server import app as api_app
    
#     # 注册 API 应用实例
#     register_instance("api_app", api_app)
    
#     # 在单独的线程中启动 API 服务器
#     api_thread = threading.Thread(
#         target=run_api_server_thread, 
#         args=(api_app,),
#         daemon=True
#     )
#     api_thread.start()
    
#     return api_thread


# # 自动初始化全局实例
# init_instances()

#  初始化服务管理器
initialize_service_manager()
# 导出为简洁的 API
service_manager = get_service_manager()
