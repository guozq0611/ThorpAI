from fastapi import FastAPI, APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import traceback
import time
from btc_model.core.util.log_util import Logger
from btc_model.manager.service_manager import global_instance
from btc_model.strategy.exchange_arbitrage.exchange_arbitrage_strategy import ExchangeArbitrageStrategy

# 定义API路由器
router = APIRouter(prefix="/api")
strategy_router = APIRouter(prefix="/strategy")
arbitrage_router = APIRouter(prefix="/exchange-arbitrage")

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

@arbitrage_router.post("/execute", response_model=ArbitrageExecuteResponse)
async def execute_arbitrage(request: ArbitrageExecuteRequest = Body(...)):
    """
    执行跨交易所套利
    """
    try:
        Logger.info(f"收到套利执行请求: {request}")
        
        # 获取套利策略实例
        strategy = global_instance("exchange_arbitrage_strategy")
        
        if not strategy or not isinstance(strategy, ExchangeArbitrageStrategy):
            Logger.error("无法获取套利策略实例")
            raise HTTPException(status_code=500, detail="套利策略实例未初始化")
        
        # 确保symbol是合适的格式
        symbol = request.symbol
        
        # 触发套利
        strategy.trigger_arbitrage(symbol)
        
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

# 注册路由
strategy_router.include_router(arbitrage_router)
router.include_router(strategy_router)

# 创建FastAPI应用
def create_app():
    app = FastAPI(title="ThorpAI API", version="1.0.0")
    app.include_router(router)
    
    # 健康检查
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    return app

app = create_app()

class RestApiServer:
    def __init__(self, ip: str, port: int):
        self.app = create_app()
        self.ip = ip
        self.port = port

        self._setup_routes()

    def _setup_routes(self):
        # 注册 WebSocket 路由 - 使用装饰器方式
        @arbitrage_router.post("/execute", response_model=ArbitrageExecuteResponse)
        async def execute_arbitrage(request: ArbitrageExecuteRequest = Body(...)):
            """
            执行跨交易所套利
            """
            try:
                Logger.info(f"收到套利执行请求: {request}")
                
                # 获取套利策略实例
                strategy = global_instance("exchange_arbitrage_strategy")
                
                if not strategy or not isinstance(strategy, ExchangeArbitrageStrategy):
                    Logger.error("无法获取套利策略实例")
                    raise HTTPException(status_code=500, detail="套利策略实例未初始化")
                
                # 确保symbol是合适的格式
                symbol = request.symbol
                
                # 触发套利
                strategy.trigger_arbitrage(symbol)
                
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
            
        
        # 注册路由
        strategy_router.include_router(arbitrage_router)
        router.include_router(strategy_router)

    def run(self):
        uvicorn.run(self.app, host=self.ip, port=self.port)

if __name__ == "__main__":
    import uvicorn
    
    # 运行API服务器
    uvicorn.run(app, host="0.0.0.0", port=8000) 