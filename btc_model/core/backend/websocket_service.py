import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from datetime import datetime
import random
import uvicorn
from singleton_decorator import singleton

from btc_model.core.util.log_util import Logger as logger

# 存储活跃的 WebSocket 连接
class ConnectionManager():
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_times: Dict[WebSocket, datetime] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_times[websocket] = datetime.now()
        logger.info(f"New WebSocket connection established. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            del self.connection_times[websocket]
            logger.info(f"WebSocket connection closed. Remaining connections: {len(self.active_connections)}")

    def check_connection(self, websocket: WebSocket):
        if websocket in self.active_connections:
            return True
        else:
            return False

    async def send_message(self, message: str, websocket: WebSocket):
        """
        发送消息给指定的客户端
        """
        if not self.check_connection(websocket):
            return

        try:
            await websocket.send_text(message)
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """
        广播消息给所有连接的客户端
        """
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(connection)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                self.disconnect(connection)

@singleton
class WebSocketService:
    def __init__(self, ip: str, port: int):
        self.app: FastAPI = FastAPI()
        self.manager: ConnectionManager = ConnectionManager()
        self.ip = ip
        self.port = port
        self.router = APIRouter()

        self.queue = asyncio.Queue()
        # 存储所有活跃信号的字典，键为信号ID（通常是交易对名称）
        self.active_signals: Dict[str, Dict] = {}
        # 信号的最大存储数量，防止内存无限增长
        self.max_signals_count = 100
        
        # 存储订单和持仓数据
        self.orders: Dict[str, Dict] = {}  # 委托订单
        self.trades: Dict[str, Dict] = {}  # 成交订单
        self.positions: Dict[str, Dict] = {}  # 持仓数据
        self.max_orders_count = 100  # 订单的最大存储数量

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
        
    def _setup_routes(self):
        # 注册 WebSocket 路由 - 使用装饰器方式
        @self.app.websocket("/ws/arbitrage-signals")
        async def websocket_endpoint(websocket: WebSocket):
            await self.websocket_handler(websocket)
            
        # 注册健康检查路由
        @self.app.get("/health")
        async def health_check():
            return self.health_check()
    
    async def websocket_handler(self, websocket: WebSocket):
        await self.manager.connect(websocket)
        last_heartbeat = datetime.now()

        try:
            # 连接建立后，立即发送当前所有活跃信号和订单数据
            await self.send_all_signals(websocket)
            await self.send_all_orders(websocket)
            await self.send_all_positions(websocket)
            
            while True:
                if not self.manager.check_connection(websocket):
                    break

                # 检查心跳
                current_time = datetime.now()
                if (current_time - last_heartbeat).seconds > 30:
                    try:
                        await websocket.send_json({"type": "heartbeat"})
                        last_heartbeat = current_time
                    except Exception as e:
                        logger.error(f"Heartbeat failed: {e}")
                        break

                # 处理新信号
                new_signals = await self.process_new_signals()
                if new_signals:
                    # 只发送新信号，不重复发送所有信号
                    await self.manager.send_message(
                        message=json.dumps({
                            "type": "new_signals",
                            "data": new_signals,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }),
                        websocket=websocket
                    )
                
                # 控制发送频率
                await asyncio.sleep(1)
                
        except WebSocketDisconnect:
            self.manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.manager.disconnect(websocket)
        finally:
            self.manager.disconnect(websocket)

    async def send_all_signals(self, websocket: WebSocket):
        """发送所有活跃信号到客户端"""
        if not self.active_signals:
            return
            
        await self.manager.send_message(
            message=json.dumps({
                "type": "all_signals",
                "data": list(self.active_signals.values()),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }),
            websocket=websocket
        )
        logger.info(f"已发送 {len(self.active_signals)} 个活跃信号到新连接")

    def health_check(self):
        return {
            "status": "healthy",
            "active_connections": len(self.manager.active_connections),
            "uptime": str(datetime.now() - min(self.manager.connection_times.values())) if self.manager.connection_times else "0"
        }
    
    async def process_new_signals(self) -> List[Dict]:
        """处理队列中的新信号，更新到活跃信号字典中"""
        new_signals = []
        
        try:
            # 非阻塞获取所有可用信号
            while not self.queue.empty():
                signal = await self.queue.get()
                self.queue.task_done()
                
                # 使用交易对作为信号的唯一标识
                signal_id = signal.get('signal_id', signal.get('symbol', f"{signal.get('pair', '')}-{random.randint(1, 10000)}"))
                
                # 更新时间戳为当前时间
                signal['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 将信号添加或更新到活跃信号字典
                self.active_signals[signal_id] = signal
                new_signals.append(signal)
                
                # 如果信号数量超过最大值，删除最早的信号
                if len(self.active_signals) > self.max_signals_count:
                    oldest_key = min(self.active_signals.keys(), key=lambda k: self.active_signals[k].get('timestamp', ''))
                    del self.active_signals[oldest_key]
                    
            return new_signals
                    
        except Exception as e:
            logger.error(f"处理信号出错: {e}")
            return []
    
    async def add_signal(self, signal: Dict):
        """添加信号到队列中
        
        Args:
            signal: 要添加的信号字典
        """
        await self.queue.put(signal)
        logger.info(f"信号已添加到队列，当前队列大小: {self.queue.qsize()}")
    
    async def get_signal(self) -> Optional[Dict]:
        """从队列中获取信号
        
        Returns:
            Optional[Dict]: 获取到的信号，如果队列为空则会阻塞等待
        """
        signal = await self.queue.get()
        self.queue.task_done()
        return signal
    
    async def get_signal_nonblocking(self) -> Optional[Dict]:
        """从队列中非阻塞地获取信号
        
        Returns:
            Optional[Dict]: 获取到的信号，如果队列为空则返回None
        """
        try:
            if self.queue.empty():
                return None
            signal = self.queue.get_nowait()
            self.queue.task_done()
            return signal
        except asyncio.QueueEmpty:
            return None
    
    def get_queue_size(self) -> int:
        """获取当前队列大小
        
        Returns:
            int: 队列中的信号数量
        """
        return self.queue.qsize()
    
    def get_active_signals_count(self) -> int:
        """获取当前活跃信号数量
        
        Returns:
            int: 活跃信号数量
        """
        return len(self.active_signals)
    
    def clear_signals(self):
        """清空所有活跃信号"""
        self.active_signals.clear()
        logger.info("已清空所有活跃信号")
    
    async def run(self):
        config = uvicorn.Config(self.app, host=self.ip, port=self.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    async def send_all_orders(self, websocket: WebSocket):
        """发送所有订单数据到客户端"""
        # 发送委托订单
        if self.orders:
            await self.manager.send_message(
                message=json.dumps({
                    "type": "pending_orders",
                    "data": list(self.orders.values()),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }),
                websocket=websocket
            )
            logger.info(f"已发送 {len(self.orders)} 个委托订单到新连接")
        
        # 发送成交订单
        if self.trades:
            await self.manager.send_message(
                message=json.dumps({
                    "type": "completed_orders",
                    "data": list(self.trades.values()),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }),
                websocket=websocket
            )
            logger.info(f"已发送 {len(self.trades)} 个成交订单到新连接")

    async def send_all_positions(self, websocket: WebSocket):
        """发送所有持仓数据到客户端"""
        if self.positions:
            await self.manager.send_message(
                message=json.dumps({
                    "type": "positions",
                    "data": list(self.positions.values()),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }),
                websocket=websocket
            )
            logger.info(f"已发送 {len(self.positions)} 个持仓数据到新连接")

    async def add_order(self, order_data: Dict):
        """添加或更新订单"""
        try:
            order_id = order_data.get('id')
            if not order_id:
                logger.warning(f"订单数据缺少ID: {order_data}")
                return
                
            # 根据订单状态分类存储
            order_status = order_data.get('status', '').lower()
            if order_status in ['filled', 'complete', 'canceled', 'cancelled']:
                # 已完成或已取消的订单
                self.trades[order_id] = order_data
                # 如果之前在委托订单中，则移除
                if order_id in self.orders:
                    del self.orders[order_id]
            else:
                # 委托中的订单
                self.orders[order_id] = order_data
                
            # 限制订单数量
            if len(self.orders) > self.max_orders_count:
                oldest_key = min(self.orders.keys(), key=lambda k: self.orders[k].get('timestamp', ''))
                del self.orders[oldest_key]
                
            if len(self.trades) > self.max_orders_count:
                oldest_key = min(self.trades.keys(), key=lambda k: self.trades[k].get('timestamp', ''))
                del self.trades[oldest_key]
                
            # 广播订单更新
            await self.broadcast_orders()
            
        except Exception as e:
            logger.error(f"添加订单出错: {e}")

    async def add_position(self, position_data: Dict):
        """添加或更新持仓"""
        try:
            position_id = position_data.get('id')
            if not position_id:
                logger.warning(f"持仓数据缺少ID: {position_data}")
                return
                
            # 更新持仓数据
            self.positions[position_id] = position_data
                
            # 限制持仓数量
            if len(self.positions) > self.max_orders_count:
                oldest_key = min(self.positions.keys(), key=lambda k: self.positions[k].get('timestamp', ''))
                del self.positions[oldest_key]
                
            # 广播持仓更新
            await self.broadcast_positions()
            
        except Exception as e:
            logger.error(f"添加持仓出错: {e}")

    async def broadcast_orders(self):
        """广播订单更新"""
        # 广播委托订单
        if self.orders:
            await self.manager.broadcast(
                json.dumps({
                    "type": "pending_orders",
                    "data": list(self.orders.values()),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            )
        
        # 广播成交订单
        if self.trades:
            await self.manager.broadcast(
                json.dumps({
                    "type": "completed_orders",
                    "data": list(self.trades.values()),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            )

    async def broadcast_positions(self):
        """广播持仓更新"""
        if self.positions:
            await self.manager.broadcast(
                json.dumps({
                    "type": "positions",
                    "data": list(self.positions.values()),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            )

if __name__ == "__main__":
    server = WebSocketService(ip="0.0.0.0", port=8001)
    asyncio.run(server.run())
    print("WebSocketService started")
