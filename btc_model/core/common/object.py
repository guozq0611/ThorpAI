"""
This file contains code modified from VNPY (https://github.com/vnpy/vnpy)
Original author: VeighNa Technology
License: MIT
Copyright (c) 2015-present VeighNa Technology

Modified Comments:
- OrderData Class
- OrderRequest Class
- CancelRequest Class
"""

import datetime
from dataclasses import dataclass
from btc_model.core.common.const import (InstrumentType,
                                         Product,
                                         Exchange,
                                         OrderStatus,
                                         Offset,
                                         Direction,
                                         OrderType
                                         )
import time

@dataclass
class Instrument:

    instrument_id: str
    instrument_name: str
    exchange: Exchange
    instrument_type: InstrumentType
    product: Product
    list_date: str
    expire_date: str
    price_tick: float
    min_limit_order_volume: float
    max_limit_order_volume: float
    min_market_order_volume: float
    max_market_order_volume: float
    status: str


@dataclass
class OrderData:
    order_id: str
    symbol: str
    exchange: Exchange
    order_type: OrderType = OrderType.LIMIT
    direction: Direction = None
    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    volume_traded: float = 0
    status: OrderStatus = OrderStatus.SUBMITTING
    datetime: 'datetime.datetime' = None  # 使用字符串形式的类型注解
    reference: str = ""
    create_time: float = None  # 创建时间的时间戳（秒）

    @property
    def volume_remaining(self) -> float:
        """剩余挂单量"""
        return self.volume - self.volume_traded

    @property
    def is_active(self) -> bool:
        """
        检查订单是否活跃
        """
        return self.status not in [OrderStatus.CLOSED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]

    def create_cancel_request(self) -> "CancelRequest":
        """
        创建取消请求对象
        """
        req = CancelRequest(
            orderid=self.order_id, symbol=self.symbol, exchange=self.exchange
        )
        return req

    @staticmethod
    def from_exchange_order(exchange_order: dict, exchange: Exchange) -> "OrderData":
        """
        将交易所返回的订单数据转换为OrderData对象
        
        Args:
            exchange_order: 交易所返回的订单数据
            exchange: 交易所枚举值
            
        Returns:
            OrderData: 转换后的OrderData对象
        """
        # 确定订单方向
        direction = Direction.LONG
        if "side" in exchange_order:
            if exchange_order["side"].lower() == "sell":
                direction = Direction.SHORT
                
        # 确定订单类型
        order_type = OrderType.LIMIT_ORDER
        if "type" in exchange_order:
            if exchange_order["type"].lower() == "market":
                order_type = OrderType.MARKET_ORDER
                
        # 确定订单状态
        status = OrderStatus.SUBMITTING
        if "status" in exchange_order:
            status_str = exchange_order["status"].lower()
            if status_str in ["filled", "closed"]:
                status = OrderStatus.ALLTRADED
            elif status_str == "canceled":
                status = OrderStatus.CANCELLED
            elif status_str == "open":
                status = OrderStatus.NOTTRADED
            elif status_str == "partially_filled":
                status = OrderStatus.PARTTRADED
                
        # 获取订单ID
        order_id = exchange_order.get("id", "")
        
        # 获取交易对
        symbol = exchange_order.get("symbol", "")
        
        # 获取价格和数量
        price = float(exchange_order.get("price", 0))
        volume = float(exchange_order.get("amount", 0))
        volume_traded = float(exchange_order.get("filled", 0))
        
        # 获取时间
        dt = None
        if "datetime" in exchange_order and exchange_order["datetime"]:
            # 将ISO格式的UTC时间转换为datetime对象
            utc_dt = datetime.datetime.fromisoformat(exchange_order["datetime"].replace("Z", "+00:00"))
            # 转换为本地时间
            dt = utc_dt.astimezone(datetime.datetime.now().astimezone().tzinfo)
        
        # 创建OrderData对象
        order_data = OrderData(
            order_id=order_id,
            symbol=symbol,
            exchange=exchange,
            order_type=order_type,
            direction=direction,
            price=price,
            volume=volume,
            volume_traded=volume_traded,
            status=status,
            datetime=dt,
            create_time=time.time()  # 使用当前时间作为创建时间
        )
        
        return order_data

@dataclass
class OrderRequest:

    symbol: str
    exchange: Exchange
    direction: Direction
    type: OrderType
    volume: float
    price: float = 0
    offset: Offset = Offset.NONE
    reference: str = ""


    def create_order_data(self, orderid: str) -> OrderData:
        """
        Create order data from request.
        """
        order: OrderData = OrderData(
            symbol=self.symbol,
            exchange=self.exchange,
            order_id=orderid,
            order_type=self.type,
            direction=self.direction,
            offset=self.offset,
            price=self.price,
            volume=self.volume,
            reference=self.reference
        )
        return order


@dataclass
class CancelRequest:
    """
    Request sending to specific gateway for canceling an existing order.
    """

    orderid: str
    symbol: str
    exchange: Exchange



@dataclass
class PositionData:
    """
    Positon data is used for tracking each individual position holding.
    """

    symbol: str
    exchange: Exchange
    direction: Direction

    volume: float = 0
    frozen: float = 0
    entry_price: float = 0



@dataclass
class AccountData:
    """
    Account data contains information about balance, frozen and
    available.
    """

    account_id: str

    balance: float = 0
    frozen: float = 0
    available: float = 0
