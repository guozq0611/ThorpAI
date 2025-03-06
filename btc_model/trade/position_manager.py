from abc import ABC, abstractmethod

import ccxt.pro as ccxtpro

class PositionManager(ABC):
    """
    仓位管理器
    """
    def __init__(self, exchange: ccxtpro.Exchange):
        self.exchange = exchange

    @abstractmethod
    def create_position(self, pair_key, data):
        pass


