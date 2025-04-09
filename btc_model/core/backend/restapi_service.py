import asyncio
from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import traceback
import time
import uvicorn
from singleton_decorator import singleton

from btc_model.core.util.log_util import Logger
#from btc_model.manager.service_manager import service_manager
from btc_model.manager.instance_manager import get_instance
from btc_model.strategy.exchange_arbitrage.exchange_arbitrage_strategy import ExchangeArbitrageStrategy
from btc_model.strategy.exchange_arbitrage.object import ArbitrageSignal

# 套利执行请求模型
class ArbitrageExecuteRequest(BaseModel):
    symbol: str
    exchange1: str
    exchange2: str
    price_diff: Any  # 可以是数字或字符串
    volume: Any  # 可以是数字或字符串
    signal_id: Optional[str] = None

# 套利执行响应模型
class ArbitrageExecuteResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

@singleton
class RestApiService:
    def __init__(self, ip: str, port: int):
        """初始化 REST API 服务器
        
        Args:
            ip: 服务器绑定的 IP 地址
            port: 服务器监听的端口
        """
        self.app = FastAPI(title="ThorpAI API", version="1.0.0")
        self.ip = ip
        self.port = port
        
        # 主路由器
        self.main_router = APIRouter(prefix="/api")
        
        # 策略路由器
        self.strategy_router = APIRouter(prefix="/strategy")
        
        # 套利路由器
        self.arbitrage_router = APIRouter(prefix="/exchange-arbitrage")
        
        # 设置 CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 在生产环境中应该设置具体的域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 注册路由
        self._setup_routes()
        
        Logger.info(f"REST API 服务器初始化完成，监听地址: {ip}:{port}")
    
    def _setup_routes(self):
        """设置 API 路由"""
        # 套利执行端点
        @self.arbitrage_router.post("/execute", response_model=ArbitrageExecuteResponse)
        async def execute_arbitrage(request: ArbitrageExecuteRequest = Body(...)):
            """执行跨交易所套利"""
            try:
                Logger.info(f"收到套利执行请求: {request}")
                
                
                # 获取套利策略实例
                strategy: ExchangeArbitrageStrategy = get_instance("exchange_arbitrage_strategy")
                
                if not strategy or strategy.__class__.__name__ != 'ExchangeArbitrageStrategy':
                    Logger.error("无法获取套利策略实例")
                    raise HTTPException(status_code=500, detail="套利策略实例未初始化")
                
                # 确保symbol是合适的格式
                symbol = request.symbol

                arbitrage_signal = ArbitrageSignal(
                    symbol=symbol,
                    exchange1=request.exchange1,
                    exchange2=request.exchange2,
                    price_diff=float(request.price_diff.replace('%', '')) / 100,
                    volume=float(request.volume),
                    status="pending",
                    timestamp=datetime.now()
                )

            #   const params = {
			# 	symbol: signal.symbol || signal.pair,
			# 	exchange1: signal.exchange1,
			# 	exchange2: signal.exchange2,
			# 	price_diff: signal.price_diff,
			# 	volume: signal.volume,
			# 	signal_id: signal.id || getSignalId(signal)
			# };
                
                # 触发套利
                await strategy.execute_arbitrage(arbitrage_signal)
                
                return ArbitrageExecuteResponse(
                    success=True,
                    message="套利指令已发送",
                    data={
                        "symbol": symbol,
                        "exchange1": request.exchange1,
                        "exchange2": request.exchange2,
                        "timestamp": str(time.time())
                    }
                )
            except Exception as e:
                Logger.error(f"执行套利异常: {str(e)}")
                Logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"执行套利失败: {str(e)}")
        
        # 健康检查端点
        @self.app.get("/health")
        async def health_check():
            """API 服务健康检查"""
            return {
                "status": "healthy",
                "service": "REST API Server",
                "time": time.time()
            }
        
        # 注册路由
        self.strategy_router.include_router(self.arbitrage_router)
        self.main_router.include_router(self.strategy_router)
        self.app.include_router(self.main_router)
    
    async def run(self):
        """运行 API 服务器"""
        config = uvicorn.Config(
            self.app,
            host=self.ip,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def start(self):
        """启动 API 服务器（同步方法，用于非异步环境）"""
        Logger.info(f"启动 REST API 服务器: {self.ip}:{self.port}")
        uvicorn.run(self.app, host=self.ip, port=self.port, log_level="info")
    
    def get_app(self):
        """获取 FastAPI 应用实例，用于在其他地方直接使用"""
        return self.app

# 直接运行此文件时启动服务器
if __name__ == "__main__":
    server = RestApiService(ip="0.0.0.0", port=8002)
    server.start() 