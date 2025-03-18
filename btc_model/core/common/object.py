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
    client_id: str  # 本地订单ID
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
        return self.status in [OrderStatus.SUBMITTING, OrderStatus.OPEN, OrderStatus.CANCELING]

    @property
    def is_finished(self) -> bool:
        """
        检查订单是否已完成
        """
        return self.status in [OrderStatus.CLOSED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]

    def create_cancel_request(self) -> "CancelRequest":
        """
        创建取消请求对象
        """
        req = CancelRequest(
            orderid=self.order_id, symbol=self.symbol, exchange=self.exchange
        )
        return req
        
    @classmethod
    def create_empty(cls, symbol: str, exchange: Exchange, client_id: str, order_id: str = None) -> "OrderData":
        """
        创建一个空的订单对象，用于初始化订单
        
        Args:
            symbol: 交易对
            exchange: 交易所
            client_id: 本地订单ID
            order_id: 交易所订单ID，默认为None
            
        Returns:
            OrderData: 初始化的订单对象
        """
        return cls(
            order_id=order_id,
            client_id=client_id,
            symbol=symbol,
            exchange=exchange,
            order_type=OrderType.LIMIT,
            direction=Direction.NONE,
            offset=Offset.NONE,
            price=0,
            volume=0,
            volume_traded=0,
            status=OrderStatus.NONE,
            datetime=datetime.datetime.now(),
            reference="",
            create_time=time.time()
        )


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
