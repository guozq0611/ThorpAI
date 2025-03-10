from dataclasses import dataclass, field
from typing import Dict

from btc_model.core.common.object import PositionData, AccountData

@dataclass
class PositionHolder:
    """
    Position holder is used for tracking all positions and accounts.
    """
    positions: Dict[str, PositionData] = field(default_factory=dict)
    _current_prices: Dict[str, float] = field(default_factory=dict)  # 存储当前价格

    def add_position(self, symbol: str, quantity: float, entry_price: float) -> None:
        """添加新的仓位"""
        if symbol in self.positions:
            # 如果仓位已存在，更新数量和开仓价格
            existing_position = self.positions[symbol]
            existing_position.quantity += quantity
            existing_position.entry_price = (existing_position.entry_price * existing_position.quantity + entry_price * quantity) / (existing_position.quantity + quantity)
        else:
            # 创建新的仓位
            self.positions[symbol] = PositionData(symbol, quantity, entry_price)

    def remove_position(self, symbol: str, quantity: float) -> None:
        """移除仓位"""
        if symbol in self.positions:
            existing_position = self.positions[symbol]
            if existing_position.quantity >= quantity:
                existing_position.quantity -= quantity
                if existing_position.quantity == 0:
                    del self.positions[symbol]  # 如果数量为0，删除仓位
            else:
                raise ValueError("移除的数量超过现有仓位")
        else:
            raise ValueError("该仓位不存在")

    def get_position_value(self, symbol: str, current_price: float) -> float:
        """获取特定仓位的当前价值"""
        if symbol in self.positions:
            return self.positions[symbol].current_value(current_price)
        else:
            raise ValueError("该仓位不存在")

    def total_value(self, current_prices: Dict[str, float]) -> float:
        """计算所有仓位的总价值"""
        total = 0.0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                total += position.current_value(current_prices[symbol])
            else:
                raise ValueError(f"当前价格中缺少仓位 {symbol} 的价格")
        return total

    @property
    def total_position_value(self) -> float:
        """所有仓位的总价值（属性）"""
        # 注意：这需要当前价格，但作为属性无法传递参数
        # 这里假设有一个存储当前价格的属性或方法
        current_prices = self._get_current_prices()  # 这个方法需要在类中实现
        return self.total_value(current_prices)

    def update_current_price(self, symbol: str, price: float) -> None:
        """更新特定符号的当前价格"""
        self._current_prices[symbol] = price
        
    def update_current_prices(self, prices: Dict[str, float]) -> None:
        """批量更新当前价格"""
        self._current_prices.update(prices)
        
    def _get_current_prices(self) -> Dict[str, float]:
        """获取当前价格"""
        return self._current_prices

    def get_positions(self) -> Dict[str, PositionData]:
        """获取所有仓位的字典视图"""
        return dict(self.positions)