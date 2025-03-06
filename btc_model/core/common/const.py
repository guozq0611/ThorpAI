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
    LIMIT_ORDER = "LIMIT_ORDER"
    MARKET_ORDER = "MARKET_ORDER"


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
    SUBMITTED = "SUBMITTED"
    CANCELING = "CANCELING"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FILLED = "FILLED"
    PARTIAL_FILLED = "PARTIAL_FILLED"

    @property
    def is_pending(self) -> bool:
        """挂单状态"""
        return self in {OrderStatus.SUBMITTING, 
                        OrderStatus.SUBMITTED, 
                        OrderStatus.CANCELING}
    
    @property
    def is_finished(self) -> bool:
        """成交状态"""
        return self in {OrderStatus.FILLED, 
                        OrderStatus.PARTIAL_FILLED,
                        OrderStatus.CANCELLED,
                        OrderStatus.REJECTED}
    
    @property
    def is_failed(self) -> bool:
        """失败状态"""
        return self in {OrderStatus.REJECTED}
    
    @property
    def is_canceled(self) -> bool:
        """取消状态"""
        return self in {OrderStatus.CANCELLED}
        

ACTIVE_ORDER_STATUSES = set([OrderStatus.SUBMITTING, 
                             OrderStatus.NOTTRADED, 
                             OrderStatus.PARTTRADED])

class Offset(Enum):
    """
    Offset of order/trade.
    """
    NONE = "NONE"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    CLOSETODAY = "CLOSETODAY"
    CLOSEYESTERDAY = "CLOSEYESTERDAY"


