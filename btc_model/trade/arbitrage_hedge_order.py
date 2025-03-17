from dataclasses import dataclass
from enum import Enum
from typing import Dict, List
import threading
from datetime import datetime


from btc_model.core.common.object import OrderData
from btc_model.core.common.const import OrderStatus


class ArbitrageHedgeOrder():
    """
    套利对冲建仓订单
    
    @Note: 
    1. 包含2腿现货多头和1腿合约空头
    2. (现货腿1 + 现货腿2, 多头) 和合约腿（空头）的订单数量必须一致, 且方向相反
    3. 考虑报撤单, 需要记录每个订单的报撤单状态, 并用list管理每腿的订单列表及状态
    """
    def __init__(self, order_id: str, symbol_id: str):
        self.order_id = order_id    
        self.symbol_id = symbol_id

        # 现货腿
        self.leg_spot_1: List[OrderData] = list()  # 存储现货腿1的OrderData对象列表
        self.leg_spot_2: List[OrderData] = list()  # 存储现货腿2的OrderData对象列表
        # 合约腿
        self.leg_swap: List[OrderData] = list()    # 存储合约腿的OrderData对象列表

        self.create_time = datetime.now()
        self.update_time = datetime.now()

        self.lock = threading.Lock()

    def put_leg(self, leg_type: str, order: OrderData) -> None:
        """
        添加订单到指定腿

        @params:
            leg_type: str, 腿类型, 可选值: spot_1, spot_2, swap
            order: OrderData, 订单数据
        """
        with self.lock:
            if leg_type == 'spot_1':
                self.leg_spot_1.append(order)
            elif leg_type == 'spot_2':
                self.leg_spot_2.append(order)
            elif leg_type == 'swap':
                self.leg_swap.append(order)

    def get_last_leg(self) -> tuple[OrderData, OrderData, OrderData]:
        """
        获取指定腿的最后一条订单
        """
        with self.lock:
            return self.leg_spot_1[-1], self.leg_spot_2[-1], self.leg_swap[-1]
        
    def get_leg_origin_volume(self, leg_type: str) -> float:
        """
        获取指定腿的原始挂单量
        """
        with self.lock:
            if leg_type == 'spot_1':
                return self.leg_spot_1[0].volume
            elif leg_type == 'spot_2':
                return self.leg_spot_2[0].volume
            elif leg_type == 'swap':
                return self.leg_swap[0].volume

    def get_leg_volume_traded(self, leg_type: str) -> float:
        """
        获取指定腿的成交量
        """
        with self.lock:
            if leg_type == 'spot_1':
                volume_traded = sum(order.volume_traded for order in self.leg_spot_1)                
            elif leg_type == 'spot_2':
                volume_traded = sum(order.volume_traded for order in self.leg_spot_2)
            elif leg_type == 'swap':
                volume_traded = sum(order.volume_traded for order in self.leg_swap)
            
            return volume_traded
           

    def is_pending(self) -> bool:
        """挂单状态"""
        return self.leg_spot_1[-1].status.is_pending or self.leg_spot_2[-1].status.is_pending or self.leg_swap[-1].status.is_pending
    
    @property
    def is_finished(self) -> bool:
        """成交状态"""
        return self.leg_spot_1[-1].status.is_finished and self.leg_spot_2[-1].status.is_finished and self.leg_swap[-1].status.is_finished
    
    @property
    def is_failed(self) -> bool:
        """失败状态"""
        return self.leg_spot_1[-1].status.is_failed or self.leg_spot_2[-1].status.is_failed or self.leg_swap[-1].status.is_failed
    
    @property
    def is_canceled(self) -> bool:
        """取消状态"""
        return self.leg_spot_1[-1].status.is_canceled or self.leg_spot_2[-1].status.is_canceled or self.leg_swap[-1].status.is_canceled
