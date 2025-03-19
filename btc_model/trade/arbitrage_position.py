from dataclasses import dataclass
from enum import Enum
from typing import Dict, List
import threading
from datetime import datetime, timedelta
import time


from btc_model.core.common.object import OrderData, PositionData
from btc_model.core.common.const import OrderStatus, Exchange, PositionDirection

class ArbitragePosition():
    """
    套利对冲仓位

    """
    def __init__(self, 
                 symbol_id: str, 
                 exchange_spot_1: Exchange, 
                 exchange_spot_2: Exchange, 
                 exchange_swap: Exchange
                 ):
        self.symbol_id = symbol_id

        # 现货腿
        self.leg_spot_1: PositionData = PositionData(symbol_id, exchange_spot_1, PositionDirection.NET)
        self.leg_spot_2: PositionData = PositionData(symbol_id, exchange_spot_2, PositionDirection.NET)
        # 合约腿
        self.leg_swap: PositionData = PositionData(symbol_id, exchange_swap, PositionDirection.SHORT)

        self.update_time = datetime.now()  # 更新时间

        self.lock = threading.Lock()

    def update_position(self, leg_type: str, position_data: PositionData) -> None:
        """更新仓位"""
        with self.lock:
            if leg_type == "spot_1":
                self.leg_spot_1.copy_from(position_data)
            elif leg_type == "spot_2":
                self.leg_spot_2.copy_from(position_data)
            elif leg_type == "swap":
                self.leg_swap.copy_from(position_data)

    def get_position(self) -> tuple[PositionData, PositionData, PositionData]:
        """获取仓位"""
        with self.lock:
            return self.leg_spot_1, self.leg_spot_2, self.leg_swap

    @property
    def net_position(self) -> float:
        """净仓位"""
        with self.lock:
            return self.leg_spot_1.volume + self.leg_spot_2.volume - self.leg_swap.volume

    @property
    def spot_1_position(self) -> float:
        """现货1仓位"""
        with self.lock:
            return self.leg_spot_1.volume
        
    @spot_1_position.setter
    def spot_1_position(self, value: float):
        with self.lock:
            self.leg_spot_1.volume = value

    @property
    def spot_2_position(self) -> float:
        """现货2仓位"""
        with self.lock:
            return self.leg_spot_2.volume

    @spot_2_position.setter
    def spot_2_position(self, value: float):
        with self.lock:
            self.leg_spot_2.volume = value

    @property
    def swap_position(self) -> float:
        """合约仓位"""
        with self.lock:
            return self.leg_swap.volume

    @swap_position.setter
    def swap_position(self, value: float):
        with self.lock:
            self.leg_swap.volume = value
