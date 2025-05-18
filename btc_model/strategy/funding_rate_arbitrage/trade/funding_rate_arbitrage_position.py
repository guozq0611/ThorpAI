from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Union
import threading
from datetime import datetime, timedelta
import time


from btc_model.core.common.object import OrderData, PositionData
from btc_model.core.common.const import Exchange, PositionSide
from btc_model.core.util.crypto_util import CryptoUtil


# class HedgedPosition:
#     """
#     表示一个独立的套利头寸单元 (现货多头 + 永续空头)
#     """
#     def __init__(self, position_id: str, symbol_id: str, open_time: float):
#         self.position_id = position_id
#         self.symbol_id = symbol_id # 例如 'BTC-USDT'
#         self.open_time = open_time # 开仓时间戳
#         self.status = 'OPENING' # 'OPENING', 'OPENED', 'CLOSING', 'CLOSED', 'ERROR'

#         # 现货腿信息
#         self.spot_leg = {
#             'open_order_id': None,
#             'executed_qty': 0.0,
#             'executed_price': 0.0, # 平均成交价
#             'current_qty': 0.0,
#             'current_price': 0.0, # 最新市场价
#             'floating_pnl': 0.0
#         }

#         # 永续合约腿信息
#         self.swap_leg = {
#             'open_order_id': None,
#             'executed_qty_coin': 0.0, # 以币为单位的数量
#             'executed_price': 0.0, # 平均成交价
#             'current_qty_coin': 0.0,
#             'current_price': 0.0, # 最新市场价
#             'floating_pnl': 0.0,
#             'margin': 0.0, # 持仓保证金
#             'liquidation_price': 0.0 # 强平价格
#         }

#         self.open_basis = 0.0 # 开仓时的基差 (Swap Open Price - Spot Open Price)
#         self.total_funding_collected = 0.0 # 累计收到的资金费用

#         self.close_time = None
#         self.close_basis = None
#         self.total_pnl = 0.0 # 最终总盈亏

#     def update_spot_leg(self, executed_qty: float, executed_price: float, current_qty: float, current_price: float, floating_pnl: float):
#         """更新现货腿信息"""
#         self.spot_leg['executed_qty'] = executed_qty
#         self.spot_leg['executed_price'] = executed_price
#         self.spot_leg['current_qty'] = current_qty
#         self.spot_leg['current_price'] = current_price
#         self.spot_leg['floating_pnl'] = floating_pnl
#         # TODO: 根据需要更新其他字段

#     def update_swap_leg(self, executed_qty_coin: float, executed_price: float, current_qty_coin: float, current_price: float, floating_pnl: float, margin: float, liquidation_price: float):
#         """更新永续合约腿信息"""
#         self.swap_leg['executed_qty_coin'] = executed_qty_coin
#         self.swap_leg['executed_price'] = executed_price
#         self.swap_leg['current_qty_coin'] = current_qty_coin
#         self.swap_leg['current_price'] = current_price
#         self.swap_leg['floating_pnl'] = floating_pnl
#         self.swap_leg['margin'] = margin
#         self.swap_leg['liquidation_price'] = liquidation_price
#         # TODO: 根据需要更新其他字段

#     def calculate_total_floating_pnl(self) -> float:
#         """计算该套利头寸的总浮动盈亏 (现货浮盈亏 + 永续合约浮盈亏)"""
#         # 注意：这里只是简单的加法，实际计算可能需要考虑手续费、资金费等，取决于你如何定义浮盈亏
#         return self.spot_leg['floating_pnl'] + self.swap_leg['floating_pnl']

#     def update_market_data(self, spot_price: float, swap_price: float):
#         """根据最新的市场价格更新浮动盈亏"""
#         # 简化计算：这里只更新当前价格
#         self.spot_leg['current_price'] = spot_price
#         self.swap_leg['current_price'] = swap_price
#         # 实际应用中，浮动盈亏通常由交易所API提供，或者需要更精确计算
#         # 你可能需要定期从 OkxAPIConnector 获取最新的持仓信息来更新这些值
#         pass # TODO: Implement logic to fetch and update floating PnL based on latest market data or API calls

#     def to_dict(self) -> Dict:
#         """
#         将 HedgedPosition 对象转换为字典，用于 JSON 序列化。
#         """
#         return {
#             'position_id': self.position_id,
#             'symbol_id': self.symbol_id,
#             'open_time': self.open_time,
#             'status': self.status,
#             'spot_leg': self.spot_leg,
#             'swap_leg': self.swap_leg,
#             'open_basis': self.open_basis,
#             'total_funding_collected': self.total_funding_collected,
#             'close_time': self.close_time,
#             'close_basis': self.close_basis,
#             'total_pnl': self.total_pnl,
#             # 确保所有属性都是 JSON 支持的类型 (基本类型、列表、字典)
#         }

#     @staticmethod # 使用静态方法，因为它不依赖于 HedgedPosition 的实例
#     def from_dict(data: Dict) -> 'HedgedPosition':
#         """
#         从字典重建 HedgedPosition 对象。
#         Args:
#             data: 从 JSON 加载的字典数据。
#         Returns:
#             重建的 HedgedPosition 对象实例。
#         """
#         # 创建一个基础实例
#         position = HedgedPosition(
#             position_id=data['position_id'],
#             symbol_id=data['symbol_id'],
#             open_time=data['open_time']
#         )

#         # 复制其他属性的值
#         position.status = data.get('status', 'OPENING') # 提供默认值以防旧数据没有该字段
#         position.spot_leg = data.get('spot_leg', {})
#         position.swap_leg = data.get('swap_leg', {})
#         position.open_basis = data.get('open_basis', 0.0)
#         position.total_funding_collected = data.get('total_funding_collected', 0.0)
#         position.close_time = data.get('close_time')
#         position.close_basis = data.get('close_basis')
#         position.total_pnl = data.get('total_pnl', 0.0)

#         # TODO: 确保在加载时，如果字典中缺少某些key，能够安全地处理 (使用 .get() 并提供默认值)

#         return position

@dataclass
class FundingRateArbitragePosition():
    """
    资金费率套利仓位
    表示一个独立的套利头寸单元 (目前仅支持现货多头 + 永续空头)
    """
    def __init__(self, 
                 position_id: int,
                 symbol_id: str,
                 spot_inst_id: str, 
                 swap_inst_id: str, 
                 swap_contract_size: float,
                 exchange: Exchange,
                 open_time: datetime
                 ):
        self.position_id = position_id
        self.symbol_id = symbol_id
        self.spot_inst_id = spot_inst_id
        self.swap_inst_id = swap_inst_id
        self.swap_contract_size = swap_contract_size
        self.exchange: Exchange = exchange


        self.open_time = open_time # 开仓时间戳
        self.status = 'OPENING' # 'OPENING', 'OPENED', 'CLOSING', 'CLOSED', 'ERROR'

        # 现货腿
        self.leg_spot: PositionData = PositionData(spot_inst_id, exchange, PositionSide.NET)
        # 合约腿
        self.leg_swap: PositionData = PositionData(swap_inst_id, exchange, PositionSide.SHORT, volume_multiple=swap_contract_size)

        self.open_basis = 0.0 # 开仓时的基差 (Swap Open Price - Spot Open Price)
        self.total_funding_collected = 0.0 # 累计收到的资金费用

        self.close_time = None
        self.close_basis = None
        self.total_pnl = 0.0 # 最终总盈亏

        self.update_time = datetime.now()  # 更新时间

        self.lock = threading.Lock()

    def update_position(self, leg_type: str, position_data: PositionData) -> None:
        """更新仓位"""
        with self.lock:
            if leg_type == "spot":
                self.leg_spot.copy_from(position_data)
            elif leg_type == "swap":
                self.leg_swap.copy_from(position_data)

    def get_position(self) -> tuple[PositionData, PositionData, PositionData]:
        """获取仓位"""
        with self.lock:
            return self.leg_spot, self.leg_swap

    @property
    def net_position(self) -> float:
        """净仓位"""
        with self.lock:
            return self.leg_spot.volume - self.leg_swap.volume

    @property
    def spot_position(self) -> float:
        """现货1仓位"""
        with self.lock:
            return self.leg_spot.volume
        
    @spot_position.setter
    def spot_position(self, value: float):
        with self.lock:
            self.leg_spot.volume = value

    @property
    def swap_position(self) -> float:
        """合约仓位"""
        with self.lock:
            return self.leg_swap.volume

    @swap_position.setter
    def swap_position(self, value: float):
        with self.lock:
            self.leg_swap.volume = value

    @property
    def swap_position_notional(self) -> float:
        """合约仓位价值"""
        with self.lock:
            return self.leg_swap.volume * self.leg_swap.volume_multiple
        
    @staticmethod   
    def from_dict(data: Dict) -> 'FundingRateArbitragePosition':
        """从字典重建 FundingRateArbitragePosition 对象"""

        position = FundingRateArbitragePosition(
            position_id=data.get('position_id', 0),
            spot_inst_id=data.get('spot_inst_id', ''),
            swap_inst_id=data.get('swap_inst_id', ''),
            exchange=data.get('exchange', Exchange.NONE),
            open_time=data.get('open_time', datetime.now())
        )
        
        return position
   