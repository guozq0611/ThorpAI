from enum import Enum

PROJECT_NAME = 'ThorpAI'


class Interval(Enum):
    """
    interval of bar data.
    """
    NONE = "NONE"
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR = "1h"
    DAILY = "1d"
    WEEKLY = "1w"
    TICK = "tick"
    DAILY_UTC = "1d_utc"


class InstrumentType(Enum):
    STOCK = 'STOCK'
    FUTURE = 'FUTURE'
    OPTION = 'OPTION'
    BOND = 'BOND'
    OPENFUND = 'OF'
    ETF = 'ETF'
    INDEX = 'INDEX'
    CRYPTO = 'CRYPTO'


class Product(Enum):
    # 股指期货
    IH = 'IH'   # 上证50
    IF = 'IF'   # 沪深300
    IC = 'IC'   # 中证500

    # 加密货币
    SPOT = 'SPOT'      # 现货
    MARGIN = 'MARGIN'  # 杠杆
    SWAP = 'SWAP'      # 永续合约
    FUTURE = 'FUTURE'  # 期货
    OPTION = 'OPTION'  # 期权

    @property
    def is_index_future(self) -> bool:
        """股指期货"""
        return self in {Product.IH, Product.IF, Product.IC}
    
    @property
    def is_crypto(self) -> bool:
        """加密货币"""
        return self in {Product.SPOT, Product.MARGIN, Product.SWAP, Product.FUTURE, Product.OPTION}
    

class Exchange(Enum):
    """
    Exchange.
    """
    NONE = ""
    # Chinese
    SSE = "SSE"  # Shanghai Stock Exchange
    SZSE = "SZSE"  # Shenzhen Stock Exchange

    CFFEX = "CFFEX"  # China Financial Futures Exchange
    SHFE = "SHFE"  # Shanghai Futures Exchange
    CZCE = "CZCE"  # Zhengzhou Commodity Exchange
    DCE = "DCE"  # Dalian Commodity Exchange
    INE = "INE"  # Shanghai International Energy Exchange

    BSE = "BSE"  # Beijing Stock Exchange
    CFETS = "CFETS"  # CFETS Bond Market Maker Trading System
    XBOND = "XBOND"  # CFETS X-Bond Anonymous Trading System

    # Global
    NYSE = "NYSE"  # New York Stock Exchnage
    NASDAQ = "NASDAQ"  # Nasdaq Exchange
    HKEX = "HKEX"  # Stock Exchange of Hong Kong

    # Crypto Currency
    BINANCE = "BINANCE"  # BINANCE Exchange
    OKX = "OKX"  # OKX Exchange


class ProviderType(Enum):
    """
    数据提供方
    """
    NONE = 'NONE'
    ALTERNATIVE = 'ALTERNATIVE'
    BLOCKCHAIN = 'BLOCKCHAIN'  # https://api.blockchain.com/
    BITCOIN_DATA = 'BITCOIN_DATA'  # https://bitcoin-data.com
    GLASSNODE = 'GLASSNODE'
    BINANCE = 'BINANCE'
    OKX = 'OKX'


class EntityType(Enum):
    INSTRUMENT = 'INSTRUMENT'
    KLINE = 'KLINE'
    KLINE_INDEX = 'KLINE_INDEX'
    INDICATOR = 'INDICATOR'
    FACTOR = 'FACTOR'
    FEATURE = 'FEATURE'
    ORDER = 'ORDER'
    TRADE = 'TRADE'
    ACCOUNT = 'ACCOUNT'


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"


class Direction(Enum):
    """
    Direction of order/trade.
    """
    BUY = "BUY"
    SELL = "SELL"

    LONG = "LONG"
    SHORT = "SHORT"

    @property
    def is_spot(self) -> bool:
        """现货方向"""
        return self in {Direction.BUY, Direction.SELL}
    
    @property
    def is_futures(self) -> bool:
        """衍生品方向"""
        return self in {Direction.LONG, Direction.SHORT}
    

class PositionDirection(Enum):
    """
    Direction specifically for positions.
    """
    LONG = "LONG"   # 多
    SHORT = "SHORT" # 空
    NET = "NET"     # 净持仓


class OrderStatus(Enum):
    """
    Order status.
    """
    NONE = "NONE"
    SUBMITTING = "SUBMITTING"
    CANCELING = "CANCELING"

    OPEN = "OPEN"
    EXPIRED = 'EXPIRED'
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"

    @property
    def is_active(self) -> bool:
        """挂单状态"""
        return self in {OrderStatus.SUBMITTING, 
                        OrderStatus.OPEN, 
                        OrderStatus.CANCELING}
    
    @property
    def is_finished(self) -> bool:
        """成交状态"""
        return self in {OrderStatus.CLOSED, 
                        OrderStatus.CANCELLED,
                        OrderStatus.EXPIRED,
                        OrderStatus.REJECTED}
  
    


class Offset(Enum):
    """
    Offset of order/trade.
    """
    NONE = "NONE"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    CLOSETODAY = "CLOSETODAY"
    CLOSEYESTERDAY = "CLOSEYESTERDAY"


# 事件类型
class EventType:
    """
    事件类型常量
    """
    ON_ORDER = "ON_ORDER"  # 订单更新事件
    ON_TRADE = "ON_TRADE"  # 成交事件
    ON_CANCEL = "ON_CANCEL"  # 订单取消事件
    ON_POSITION = "ON_POSITION"  # 持仓更新事件
    ON_ACCOUNT = "ON_ACCOUNT"  # 账户更新事件
    ON_CONTRACT = "ON_CONTRACT"  # 合约信息事件
    ON_ERROR = "ON_ERROR"  # 错误事件
    ON_LOG = "ON_LOG"  # 日志事件


