from dataclasses import dataclass
from enum import Enum
from typing import Dict, List
import threading
from datetime import datetime, timedelta
import time


from btc_model.core.common.object import OrderData
from btc_model.core.common.const import OrderStatus


class FundingRateArbitrageHedgeOrder():
    """
    资金费率套利对冲建仓订单
    
    @Note: 
    1. 现货多头和合约空头
    2. 考虑报撤单, 需要记录每个订单的报撤单状态, 并用list管理每腿的订单列表及状态
    """
    def __init__(self, order_id: str, symbol_id: str):
        self.order_id = order_id    
        self.symbol_id = symbol_id

        # 现货腿
        self.leg_spot: List[OrderData] = list()  
        # 合约腿
        self.leg_swap: List[OrderData] = list()    # 存储合约腿的OrderData对象列表

        # 使用datetime对象记录时间，更清晰直观
        self.create_time = datetime.now()  # 创建时间
        self.update_time = datetime.now()  # 更新时间

        self._imbalance_adjust_times = 0    # 残腿调整次数

        self.lock = threading.Lock()

    def put_leg(self, leg_type: str, order: OrderData) -> None:
        """
        添加订单到指定腿

        @params:
            leg_type: str, 腿类型, 可选值: spot, swap
            order: OrderData, 订单数据
        """
        with self.lock:
            if leg_type == 'spot':
                self.leg_spot.append(order)
            elif leg_type == 'swap':
                self.leg_swap.append(order)

    def get_last_leg(self) -> tuple[OrderData, OrderData]:
        """
        获取指定腿的最后一条订单
        """
        with self.lock:
            return self.leg_spot[-1], self.leg_swap[-1]
        
    def get_leg_origin_volume(self, leg_type: str) -> float:
        """
        获取指定腿的原始挂单量
        """
        with self.lock:
            if leg_type == 'spot':
                return self.leg_spot[0].volume
            elif leg_type == 'swap':
                return self.leg_swap[0].volume

    def get_leg_volume_traded(self, leg_type: str) -> float:
        """
        获取指定腿的成交量
        """
        with self.lock:
            if leg_type == 'spot':
                volume_traded = sum(order.volume_traded for order in self.leg_spot)                
            elif leg_type == 'swap':
                volume_traded = sum(order.volume_traded for order in self.leg_swap)
            
            return volume_traded
        
    @property
    def imbalance_adjust_times(self) -> int:
        """
        获取残腿调整次数
        """
        with self.lock:
            return self._imbalance_adjust_times
    
    @imbalance_adjust_times.setter
    def imbalance_adjust_times(self, value: int):
        with self.lock:
            self._imbalance_adjust_times = value
           
    @property
    def is_active(self) -> bool:
        """挂单状态"""
        return self.leg_spot[-1].status.is_active or self.leg_swap[-1].status.is_active
    
    @property
    def is_finished(self) -> bool:
        """成交状态"""
        return self.leg_spot[-1].status.is_finished and self.leg_swap[-1].status.is_finished
    
    @property
    def is_canceled(self) -> bool:
        """取消状态"""
        return self.leg_spot[-1].status == OrderStatus.CANCELLED or self.leg_swap[-1].status == OrderStatus.CANCELLED

    def is_timeout(self, timeout_seconds: float) -> bool:
        """
        检查订单是否超时
        
        Args:
            timeout_seconds: 超时时间（秒）
            
        Returns:
            bool: 是否超时
        """
        # 计算当前时间与创建时间的差值（秒）
        elapsed = (datetime.now() - self.create_time).total_seconds()
        return elapsed > timeout_seconds
    
    def is_imbalance_adjust_times_limit(self, limit: int) -> bool:
        """
        检查残腿调整次数是否超过限制

        @params:
            limit: 限制次数

        @return:
            bool: 是否超过限制
        """
        with self.lock:
            return self._imbalance_adjust_times >= limit
