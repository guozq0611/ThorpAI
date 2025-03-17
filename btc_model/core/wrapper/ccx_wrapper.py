import datetime
from btc_model.core.common.const import OrderType, Direction, OrderStatus, Exchange
from btc_model.core.common.object import OrderData
import ccxt
from typing import Union
from btc_model.core.util.crypto_util import ORDERTYPE_FROM_CCXT, DIRECTION_FROM_CCXT, STATUS_FROM_CCXT, EXCHANGE_FROM_CCXT
class CCXWrapper:

    def __init__(self, exchange: Exchange):
        self.exchange = exchange

