from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import threading
from datetime import datetime


from btc_model.core.common.object import OrderData
from btc_model.core.common.const import OrderStatus

@dataclass
class ArbitrageHedgeOrder():
    """
    套利对冲建仓订单
    包含2腿现货多头和1腿合约空头
    """
    id: str
    leg_spot_1: OrderData  
    leg_spot_2: OrderData 
    leg_swap: OrderData
    create_time: datetime = datetime.now()
    update_time: datetime = datetime.now()
    
    @property
    def is_pending(self) -> bool:
        """挂单状态"""
        return self.leg_spot_1.status.is_pending or self.leg_spot_2.status.is_pending or self.leg_swap.status.is_pending
    
    @property
    def is_finished(self) -> bool:
        """成交状态"""
        return self.leg_spot_1.status.is_finished and self.leg_spot_2.status.is_finished and self.leg_swap.status.is_finished
    
    @property
    def is_failed(self) -> bool:
        """失败状态"""
        return self.leg_spot_1.status.is_failed or self.leg_spot_2.status.is_failed or self.leg_swap.status.is_failed
    
    @property
    def is_canceled(self) -> bool:
        """取消状态"""
        return self.leg_spot_1.status.is_canceled or self.leg_spot_2.status.is_canceled or self.leg_swap.status.is_canceled
