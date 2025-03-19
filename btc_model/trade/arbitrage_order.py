from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import threading
from datetime import datetime


from btc_model.core.common.object import OrderData
from btc_model.core.common.const import OrderStatus

@dataclass
class ArbitrageOrder():
    """
    套利订单(一买一卖), 约定第一腿为买入腿, 第二腿为卖出腿
    
    @Note: 
    1. 包含2腿现货多头
    2. 现货腿1 和 现货腿2 的订单数量必须一致, 且方向相反
    3. 考虑报撤单, 需要记录每个订单的报撤单状态, 并用list管理每腿的订单列表及状态
    """
    def __init__(self, order_id: str, symbol_id: str):
        self.order_id = order_id    
        self.symbol_id = symbol_id

        # 现货腿
        self.leg_spot_1: List[OrderData] = list()  # 存储现货腿1的OrderData对象列表
        self.leg_spot_2: List[OrderData] = list()  # 存储现货腿2的OrderData对象列表
      

        # 使用datetime对象记录时间，更清晰直观
        self.create_time = datetime.now()  # 创建时间
        self.update_time = datetime.now()  # 更新时间

        self._imbalance_adjust_times = 0    # 残腿调整次数

        self.lock = threading.Lock()

    def put_leg(self, leg_type: str, order: OrderData) -> None:
        """
        添加订单到指定腿

        @params:
            leg_type: str, 腿类型, 可选值: spot_1, spot_2
            order: OrderData, 订单数据
        """
        with self.lock:
            if leg_type == 'spot_1':
                self.leg_spot_1.append(order)
            elif leg_type == 'spot_2':
                self.leg_spot_2.append(order)
          
    def get_last_leg(self) -> tuple[OrderData, OrderData]:
        """
        获取指定腿的最后一条订单
        """
        with self.lock:
            return self.leg_spot_1[-1], self.leg_spot_2[-1]
        
    def get_leg_origin_volume(self, leg_type: str) -> float:
        """
        获取指定腿的原始挂单量
        """
        with self.lock:
            if leg_type == 'spot_1':
                return self.leg_spot_1[0].volume
            elif leg_type == 'spot_2':
                return self.leg_spot_2[0].volume

    def get_leg_volume_traded(self, leg_type: str) -> float:
        """
        获取指定腿的成交量
        """
        with self.lock:
            if leg_type == 'spot_1':
                volume_traded = sum(order.volume_traded for order in self.leg_spot_1)                
            elif leg_type == 'spot_2':
                volume_traded = sum(order.volume_traded for order in self.leg_spot_2)
            
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
        return self.leg_spot_1[-1].status.is_active or self.leg_spot_2[-1].status.is_active
    
    @property
    def is_finished(self) -> bool:
        """成交状态"""
        return self.leg_spot_1[-1].status.is_finished and self.leg_spot_2[-1].status.is_finished
    
    @property
    def is_canceled(self) -> bool:
        """取消状态"""
        return self.leg_spot_1[-1].status == OrderStatus.CANCELLED or self.leg_spot_2[-1].status == OrderStatus.CANCELLED

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
