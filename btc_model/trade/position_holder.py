from dataclasses import dataclass, field
from typing import Dict

from btc_model.core.common.const import PositionDirection, Exchange
from btc_model.core.common.object import PositionData, AccountData


class PositionHolder:
    """
    Position holder is used for tracking all positions and accounts.
    """
    def __init__(self):
        # tuple[Exchange, str, PositionDirection] exchange_id, symbol, direction
        self.positions: Dict[tuple[Exchange, str, PositionDirection], PositionData] = field(default_factory=dict)

    def add_position(
            self, 
            exchange: Exchange, 
            symbol: str, direction: 
            PositionDirection, 
            quantity: float,
            entry_price: float
            ) -> None:
        """添加新的仓位"""
        if (exchange, symbol, direction) in self.positions:
            # 如果仓位已存在，更新数量和开仓价格
            existing_position = self.positions[(exchange, symbol, direction)]
            existing_position.entry_price = (existing_position.entry_price * existing_position.quantity \
                                             + entry_price * quantity) / (existing_position.quantity + quantity)
            existing_position.quantity += quantity
        else:
            # 创建新的仓位
            self.positions[(exchange, symbol, direction)] = PositionData(symbol, quantity, entry_price)

    def remove_position(
            self, 
            exchange: Exchange, 
            symbol: str, 
            direction: PositionDirection, 
            quantity: float
            ) -> None:
        """移除仓位"""
        if (exchange, symbol, direction) in self.positions:
            existing_position = self.positions[(exchange, symbol, direction)]
            if existing_position.quantity >= quantity:
                existing_position.quantity -= quantity
                if existing_position.quantity == 0:
                    del self.positions[(exchange, symbol, direction)]  # 如果数量为0，删除仓位
            else:
                raise ValueError("移除的数量超过现有仓位")
        else:
            raise ValueError("该仓位不存在")

    def get_position_value(
            self, 
            exchange: Exchange, 
            symbol: str, 
            direction: PositionDirection, 
            current_price: float
            ) -> float:
        """获取特定仓位的当前价值"""
        if (exchange, symbol, direction) in self.positions:
            return self.positions[(exchange, symbol, direction)].volume * current_price * (-1 if direction == PositionDirection.SHORT else 1)
        else:
            raise ValueError("该仓位不存在")

    def get_total_position_value(self, current_prices: Dict[str, float]) -> float:
        """
        计算所有仓位的总价值, 需要当前价格
        
        @Param: current_prices: 当前价格字典, key为symbol, value为当前价格
        @Return: 所有仓位的总价值

        @Note: 合约空头仓位为正、空头仓位为负, 现货多头仓位为正
        """
        total = 0.0
        for (exchange, symbol, direction), position in self.positions.items():
            if symbol in current_prices:
                total += position.volume * current_prices[symbol] * (-1 if direction == PositionDirection.SHORT else 1)
            else:
                raise ValueError(f"当前价格中缺少仓位 {symbol} 的价格")
        return total

    def get_positions(self) -> Dict[tuple[Exchange, str, PositionDirection], PositionData]:
        """获取所有仓位的字典视图"""
        return self.positions