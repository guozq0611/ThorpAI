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
                                         OrderType,
                                         ACTIVE_ORDER_STATUSES
                                         )

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
    orderid: str
    symbol: str
    exchange: Exchange
    order_type: OrderType = OrderType.LIMIT
    direction: Direction = None
    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    volume_traded: float = 0
    status: OrderStatus = OrderStatus.SUBMITTING
    datetime: datetime.datetime = None # type: ignore
    reference: str = ""

    @property
    def volume_remaining(self) -> float:
        """剩余挂单量"""
        return self.volume - self.volume_traded

    @property
    def is_active(self) -> bool:
        """
        检查订单是否活跃
        """
        return self.status in ACTIVE_ORDER_STATUSES

    def create_cancel_request(self) -> "CancelRequest":
        """
        创建取消请求对象
        """
        req = CancelRequest(
            orderid=self.orderid, symbol=self.symbol, exchange=self.exchange
        )
        return req

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
            orderid=orderid,
            type=self.type,
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
