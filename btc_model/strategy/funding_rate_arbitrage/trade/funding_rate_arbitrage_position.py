from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Union, Optional
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
                 exchange_id: str,
                 symbol_id: str,
                 spot_inst_id: str, 
                 swap_inst_id: str, 
                 swap_contract_size: float,
                 arbitrage_position: float,
                 spot_position: float,
                 swap_position: float,
                 status: str
                 ):
        self.position_id = position_id
        self.symbol_id = symbol_id
        self.exchange_id = exchange_id
        self.spot_inst_id = spot_inst_id
        self.swap_inst_id = swap_inst_id
        self.swap_contract_size = swap_contract_size

        self.arbitrage_position = arbitrage_position
        self.spot_position = spot_position
        self.swap_position = swap_position

        self.status = status # 'OPENING', 'HOLDING', 'CLOSING', 'CLOSED', 'FAILED'

        self.open_time = datetime.now() # 开仓时间戳
      
        # # 现货腿
        # self.leg_spot: PositionData = PositionData(spot_inst_id, self.exchange, PositionSide.NET)
        # # 合约腿
        # self.leg_swap: PositionData = PositionData(swap_inst_id, self.exchange, PositionSide.SHORT, volume_multiple=swap_contract_size)

        self.open_basis = 0.0 # 开仓时的基差 (Swap Open Price - Spot Open Price)
        self.total_funding_collected = 0.0 # 累计收到的资金费用

        self.close_time = None
        self.close_basis = None
        self.total_pnl = 0.0 # 最终总盈亏

        self.update_time = datetime.now()  # 更新时间

        self.lock = threading.Lock()

    def update_position(self, update_data: Dict) -> None:
        """
        更新仓位信息
        
        Args:
            update_data: 包含要更新的字段和值的字典
        """
        with self.lock:
            self.spot_position = update_data.get('spot_position', self.spot_position)
            self.swap_position = update_data.get('swap_position', self.swap_position)
            self.status = update_data.get('status', self.status)
            self.open_time = update_data.get('open_time', self.open_time)
            self.open_basis = update_data.get('open_basis', self.open_basis)
            self.total_funding_collected = update_data.get('total_funding_collected', self.total_funding_collected)
            self.close_time = update_data.get('close_time', self.close_time)
            self.close_basis = update_data.get('close_basis', self.close_basis)
            self.total_pnl = update_data.get('total_pnl', self.total_pnl)
            self.update_time = datetime.now()


    @property
    def net_position(self) -> float:
        """净仓位"""
        with self.lock:
            return self.spot_position - self.swap_position

  
    @property
    def swap_position_notional(self) -> float:
        """合约仓位价值"""
        with self.lock:
            return self.swap_position * self.swap_contract_size
        

    def from_dict(self, data: Dict):
        """从字典重建 FundingRateArbitragePosition 对象"""

        with self.lock:
            self.position_id=data.get('position_id', 0),
            self.exchange_id=data.get('exchange_id', ''),
            self.symbol_id=data.get('symbol_id', ''),
            self.spot_inst_id=data.get('spot_inst_id', ''),
            self.swap_inst_id=data.get('swap_inst_id', ''),
            self.swap_contract_size=data.get('swap_contract_size', 0.0),
            self.arbitrage_position=data.get('arbitrage_position', 0.0),
            self.spot_position=data.get('spot_position', 0.0),
            self.swap_position=data.get('swap_position', 0.0),
            self.status=data.get('status', '')
        
   
   
    def to_dict(self) -> Dict:
        """将 FundingRateArbitragePosition 对象转换为字典"""
        with self.lock:
            return {
                'position_id': self.position_id,
                'exchange_id': self.exchange_id,
                'symbol_id': self.symbol_id,
                'spot_inst_id': self.spot_inst_id,
                'swap_inst_id': self.swap_inst_id,
                'swap_contract_size': self.swap_contract_size,
                'arbitrage_position': self.arbitrage_position,
                'spot_position': self.spot_position,
                'swap_position': self.swap_position,
                'status': self.status,
                'open_time': self.open_time,
                'open_basis': self.open_basis,
                'total_funding_collected': self.total_funding_collected,
                'close_time': self.close_time,
                'close_basis': self.close_basis,
                'total_pnl': self.total_pnl,
                'update_time': self.update_time
            }
