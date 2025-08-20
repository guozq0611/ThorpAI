import os
import pickle
import pandas as pd
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading

from btc_model.core.common.const import Exchange
from btc_model.core.util.log_util import logger
from btc_model.core.wrapper.db_wrapper import DBWrapper
from btc_model.strategy.funding_rate_arbitrage.exchange_connector import ExchangeConnector

from trade.funding_rate_arbitrage_position import FundingRateArbitragePosition

# class FundingRateArbitragePosition:
#     """持仓对象，表示一个套利持仓"""
    
#     def __init__(self, 
#                  position_id: str,
#                  exchange_id: str,
#                  spot_symbol: str, 
#                  swap_symbol: str,
#                  spot_position: float = 0,
#                  swap_position: float = 0,
#                  entry_spot_price: float = 0,
#                  entry_swap_price: float = 0,
#                  entry_basis: float = 0,
#                  entry_time: float = 0,
#                  last_update_time: float = 0,
#                  status: str = "open",
#                  pnl: float = 0,
#                  metadata: Dict = None):
#         """
#         初始化持仓对象
        
#         Args:
#             position_id: 持仓ID
#             exchange_id: 交易所ID
#             spot_symbol: 现货交易对符号
#             swap_symbol: 永续合约交易对符号
#             spot_position: 现货持仓数量 (正为多, 负为空)
#             swap_position: 永续合约持仓数量 (正为多, 负为空)
#             entry_spot_price: 现货进场价格
#             entry_swap_price: 永续合约进场价格
#             entry_basis: 进场时的基差
#             entry_time: 进场时间戳
#             last_update_time: 最后更新时间戳
#             status: 持仓状态 ("open", "closing", "closed")
#             pnl: 当前盈亏
#             metadata: 其他元数据
#         """
#         self.position_id = position_id
#         self.exchange_id = exchange_id
#         self.spot_symbol = spot_symbol
#         self.swap_symbol = swap_symbol
#         self.spot_position = spot_position
#         self.swap_position = swap_position
#         self.entry_spot_price = entry_spot_price
#         self.entry_swap_price = entry_swap_price
#         self.entry_basis = entry_basis
#         self.entry_time = entry_time
#         self.last_update_time = last_update_time or time.time()
#         self.status = status
#         self.pnl = pnl
#         self.metadata = metadata or {}
        
#     def to_dict(self) -> Dict:
#         """将持仓对象转换为字典"""
#         return {
#             'position_id': self.position_id,
#             'exchange_id': self.exchange_id,
#             'spot_symbol': self.spot_symbol,
#             'swap_symbol': self.swap_symbol,
#             'spot_position': self.spot_position,
#             'swap_position': self.swap_position,
#             'entry_spot_price': self.entry_spot_price,
#             'entry_swap_price': self.entry_swap_price,
#             'entry_basis': self.entry_basis,
#             'entry_time': self.entry_time,
#             'last_update_time': self.last_update_time,
#             'status': self.status,
#             'pnl': self.pnl,
#             'metadata': self.metadata,
#             'duration': time.time() - self.entry_time if self.entry_time > 0 else 0,
#             'entry_time_str': datetime.fromtimestamp(self.entry_time).strftime('%Y-%m-%d %H:%M:%S') if self.entry_time > 0 else ''
#         }
        
#     @classmethod
#     def from_dict(cls, data: Dict) -> 'FundingRateArbitragePosition':
#         """从字典创建持仓对象"""
#         return cls(
#             position_id=data.get('position_id', ''),
#             exchange_id=data.get('exchange_id', ''),
#             spot_symbol=data.get('spot_symbol', ''),
#             swap_symbol=data.get('swap_symbol', ''),
#             spot_position=float(data.get('spot_position', 0)),
#             swap_position=float(data.get('swap_position', 0)),
#             entry_spot_price=float(data.get('entry_spot_price', 0)),
#             entry_swap_price=float(data.get('entry_swap_price', 0)),
#             entry_basis=float(data.get('entry_basis', 0)),
#             entry_time=float(data.get('entry_time', 0)),
#             last_update_time=float(data.get('last_update_time', 0)),
#             status=data.get('status', 'open'),
#             pnl=float(data.get('pnl', 0)),
#             metadata=data.get('metadata', {})
#         )

class FundingRateArbitragePositionManager:
    """
    持仓管理器，负责管理资金费率套利策略的持仓
    """
    
    def __init__(self, 
                 exchange_connector: ExchangeConnector, 
                 db_wrapper: DBWrapper=None
                 ):
        """
        初始化持仓管理器
        
        Args:
            exchange_connector: 交易所连接器
            db_wrapper: 数据库连接包装器（可选）
        """
        self.exchange_connector = exchange_connector
        self.db_wrapper: DBWrapper = db_wrapper

        self._lock = threading.Lock()

        self.positions: Dict[int, FundingRateArbitragePosition] = {}  # 持仓字典，键为持仓ID
        self.positions_by_exchange_symbol: Dict[tuple[str, str], FundingRateArbitragePosition] = {}  # 通过交易所ID和交易对ID快速查找
        self.load_positions_from_db()
        
    def load_positions_from_db(self):
        """从数据库加载持仓"""
        if not self.db_wrapper:
            logger.warning("数据库连接未提供，无法从数据库加载持仓")
            return
            
        with self._lock:
            try:
                query = """
                SELECT * FROM funding_rate_arbitrage_position
                WHERE status IN ('OPENING', 'HOLDING', 'CLOSING')
                """
                
                rows = self.db_wrapper.fetch_result(query)
                if not rows:
                    logger.info("没有找到活跃的资金费率套利持仓")
                    return
                
                df = pd.DataFrame(rows, columns=['id', 
                                                 'exchange_id', 
                                                 'symbol_id', 
                                                 'spot_inst_id', 
                                                 'swap_inst_id', 
                                                 'swap_contract_size', 
                                                 'arbitrage_position', 
                                                 'spot_position', 
                                                 'swap_position', 
                                                 'status',
                                                 'created_at',
                                                 'updated_at'
                                                 ])
                    
                for _, row in df.iterrows():
                    position = FundingRateArbitragePosition(position_id=row.get('id'),
                                                            exchange_id=row.get('exchange_id'),
                                                            symbol_id=row.get('symbol_id'),
                                                            spot_inst_id=row.get('spot_inst_id'),
                                                            swap_inst_id=row.get('swap_inst_id'),
                                                            swap_contract_size=row.get('swap_contract_size'),
                                                            arbitrage_position=row.get('arbitrage_position'),
                                                            spot_position=row.get('spot_position'),
                                                            swap_position=row.get('swap_position'),
                                                            status=row.get('status')
                                                            )
                    self.positions[position.position_id] = position
                    # 添加到快速查找字典
                    self.positions_by_exchange_symbol[(position.exchange_id, position.symbol_id)] = position
                    
                logger.info(f"从数据库加载了 {len(self.positions)} 个活跃持仓")
            
            except Exception as e:
                logger.error(f"从数据库加载持仓失败: {e}")
            
    def get_all_positions(self) -> List[FundingRateArbitragePosition]:
        """获取所有持仓"""
        with self._lock:
            return list(self.positions.values())
        
    def get_position(self, position_id: Optional[int] = None, exchange_id: Optional[str] = None, symbol_id: Optional[str] = None) -> Optional[FundingRateArbitragePosition]:
        """
        获取指定条件的持仓
        
        Args:
            position_id: 持仓ID
            exchange_id: 交易所ID
            symbol_id: 交易对ID
            
        Returns:
            Optional[FundingRateArbitragePosition]: 符合条件的持仓，如果不存在则返回None
            
        Note:
            - 如果提供了position_id，则直接通过ID查询
            - 如果提供了exchange_id和symbol_id，则通过这两个参数查询
            - 如果只提供了其中一个参数，则返回None
        """
        with self._lock:
            # 通过position_id查询
            if position_id is not None:
                return self.positions.get(position_id)
            
            # 通过exchange_id和symbol_id查询
            if exchange_id is not None and symbol_id is not None:
                return self.positions_by_exchange_symbol.get((exchange_id, symbol_id))
                        
            return None
        
    def get_concurrent_positions_count(self) -> int:
        """获取当前活跃持仓数量(HOLDING, OPENING)"""
        with self._lock:
            return len([p for p in self.positions.values() if p.status in ['HOLDING', 'OPENING', 'CLOSING']])
        
    def add_position(self, position_dict: dict) -> Optional[int]:
        """添加新持仓"""
        with self._lock:
            if self.positions_by_exchange_symbol.get((position_dict['exchange_id'], position_dict['symbol_id'])):
                logger.warning(f"持仓已存在: exchange_id={position_dict['exchange_id']}, symbol_id={position_dict['symbol_id']}")
                return None

            
            # 保存到数据库
            if self.db_wrapper:
                try:                 
                    sql = f"""
                    INSERT INTO funding_rate_arbitrage_position (
                        exchange_id,
                        symbol_id,
                        spot_inst_id,
                        swap_inst_id,
                        swap_contract_size,
                        arbitrage_position,
                        spot_position,
                        swap_position,          
                        status
                    )
                    VALUES (
                        :exchange_id,
                        :symbol_id,
                        :spot_inst_id,
                        :swap_inst_id,
                        :swap_contract_size,
                        :arbitrage_position,
                        :spot_position,
                        :swap_position,
                        :status
                    )
                    """

                    params = {
                        "exchange_id": position_dict['exchange_id'],
                        "symbol_id": position_dict['symbol_id'],
                        "spot_inst_id": position_dict['spot_inst_id'],
                        "swap_inst_id": position_dict['swap_inst_id'],  
                        "swap_contract_size": position_dict['swap_contract_size'],
                        "arbitrage_position": position_dict['arbitrage_position'],
                        "spot_position": position_dict['spot_position'],
                        "swap_position": position_dict['swap_position'],
                        "status": 'OPENING',                 
                    }
                    
                    position_id = self.db_wrapper.execute_sql(sql, params=params)
                    if position_id is None:
                        logger.error(f"保存持仓到数据库失败: {sql} {params}")
                        return None
                    
                    position = FundingRateArbitragePosition(position_id=position_id,
                                                            exchange_id=position_dict['exchange_id'],
                                                            symbol_id=position_dict['symbol_id'],
                                                            spot_inst_id=position_dict['spot_inst_id'],
                                                            swap_inst_id=position_dict['swap_inst_id'],
                                                            swap_contract_size=position_dict['swap_contract_size'],
                                                            arbitrage_position=position_dict['arbitrage_position'],
                                                            spot_position=position_dict['spot_position'],
                                                            swap_position=position_dict['swap_position'],
                                                            status=position_dict['status'])
                    
                    self.positions[position_id] = position
                    self.positions_by_exchange_symbol[(position.exchange_id, position.symbol_id)] = position

                    logger.info(f"成功添加持仓: {position_id}")

                    return position_id
                    
                except Exception as e:
                    logger.error(f"保存持仓到数据库失败: {e}")
                    return None
                    
            return None
        
    def update_position(self, position_data: dict) -> bool:
        """更新持仓"""
        with self._lock:
            position_id = position_data.get('position_id', None)
            if position_id:
                position: FundingRateArbitragePosition = self.positions.get(position_id)
            else:
                position: FundingRateArbitragePosition = self.positions_by_exchange_symbol.get((position_data['exchange_id'], position_data['symbol_id']))
                
            if position is None:
                logger.warning(f"持仓ID不存在: {position_data['position_id']}")
                return False
                
            position.update_position(position_data)
    
            # 更新数据库
            if self.db_wrapper:
                try:
                    sql = f"""
                    UPDATE funding_rate_arbitrage_position
                    SET spot_position = :spot_position,
                        swap_position = :swap_position,
                        status = :status
                    WHERE id = :position_id
                    """

                    params = {
                        "spot_position": position.spot_position,
                        "swap_position": position.swap_position,
                        "status": position.status,
                        "position_id": position.position_id
                    }

                    self.db_wrapper.execute_sql(sql, params=params)
                    logger.info(f"成功更新持仓: {position.position_id}")
                    
                except Exception as e:
                    logger.error(f"更新持仓信息失败: {e}")
                    return False
                    
            return True
        
    def close_position(self, position_id: str, final_pnl: float = None) -> bool:
        """关闭持仓"""
        with self._lock:
            if position_id not in self.positions:
                logger.warning(f"持仓ID不存在: {position_id}")
                return False
                
            position = self.positions[position_id]
            position.status = 'CLOSED'
            position.last_update_time = time.time()
            
            if final_pnl is not None:
                position.pnl = final_pnl
                
            # 从快速查找字典中移除
            self.positions_by_exchange_symbol.pop((position.exchange_id, position.symbol_id), None)
                
            # 更新数据库
            if self.db_wrapper:
                try:
                    query = """
                    UPDATE funding_rate_arbitrage_position
                    SET status = 'CLOSED', 
                        last_update_time = %s, 
                        pnl = %s
                    WHERE position_id = %s
                    """
                    
                    values = (position.last_update_time, position.pnl, position_id)
                    self.db_wrapper.execute_sql(query, values)
                    logger.info(f"成功关闭持仓: {position_id}, 最终盈亏: {position.pnl}")
                    
                except Exception as e:
                    logger.error(f"关闭持仓失败: {e}")
                    return False
                    
            return True
        
    def update_all_positions_status(self):
        """更新所有持仓的状态和盈亏"""
        with self._lock:
            # 获取最新市场数据
            for position_id, position in list(self.positions.items()):
                if position.status != 'OPENED':
                    continue
                    
                try:
                    # 获取最新现货和永续合约价格
                    spot_ticker = self.exchange_connector.fetch_ticker(position.spot_symbol)
                    swap_ticker = self.exchange_connector.fetch_ticker(position.swap_symbol)
                    
                    if not spot_ticker or not swap_ticker:
                        logger.warning(f"无法获取持仓 {position_id} 的最新价格数据")
                        continue
                        
                    # 计算当前盈亏
                    spot_price = spot_ticker['last']
                    swap_price = swap_ticker['last']
                    
                    # 对于多现货空合约的持仓，盈亏计算公式为:
                    # PNL = spot_position * (current_spot_price - entry_spot_price) + 
                    #       swap_position * (entry_swap_price - current_swap_price)
                    spot_pnl = position.spot_position * (spot_price - position.entry_spot_price)
                    swap_pnl = position.swap_position * (position.entry_swap_price - swap_price)
                    total_pnl = spot_pnl + swap_pnl
                    
                    # 更新持仓盈亏
                    position.pnl = total_pnl
                    position.last_update_time = time.time()
                    
                    # 更新数据库
                    if self.db_wrapper:
                        query = """
                        UPDATE funding_rate_arbitrage_position
                        SET pnl = %s, 
                            last_update_time = %s
                        WHERE position_id = %s
                        """
                        
                        values = (position.pnl, position.last_update_time, position_id)
                        self.db_wrapper.execute_sql(query, values)
                        
                except Exception as e:
                    logger.error(f"更新持仓 {position_id} 状态失败: {e}")
                    
            logger.info(f"更新了 {len(self.positions)} 个持仓的状态")
        
    def get_active_position(self, exchange_id: str, symbol_id: str) -> Optional[FundingRateArbitragePosition]:
        """根据交易对符号获取活跃持仓"""
        with self._lock:
            for position in self.positions.values():
                if (position.exchange_id == exchange_id and 
                    position.symbol_id == symbol_id and 
                    position.status in ['OPENING', 'OPENED', 'CLOSING']):
                    return position
            return None
        
    
        
    def get_positions_by_exchange(self, exchange_id: str) -> List[FundingRateArbitragePosition]:
        """获取指定交易所的所有持仓"""
        with self._lock:
            return [p for p in self.positions.values() if p.exchange_id == exchange_id]
        
    def get_total_pnl(self) -> float:
        """获取所有持仓的总盈亏"""
        with self._lock:
            return sum(p.pnl for p in self.positions.values())
        
    def sync_positions_with_exchange(self):
        """
        与交易所同步持仓状态，确保本地持仓数据与实际交易所持仓一致
        """
        try:
            # 获取交易所的实际持仓
            exchange_positions = self.exchange_connector.fetch_positions()
            if not exchange_positions:
                logger.warning("无法获取交易所持仓信息")
                return
                
            # 将交易所持仓转换为字典，便于查找
            exchange_pos_dict = {}
            for pos in exchange_positions:
                if 'instId' in pos:
                    exchange_pos_dict[pos['instId']] = pos
                    
            # 检查本地持仓是否与交易所一致
            for position_id, position in list(self.positions.items()):
                if position.status != 'OPENED':
                    continue
                    
                # 检查永续合约持仓
                if position.swap_symbol in exchange_pos_dict:
                    exchange_swap_pos = exchange_pos_dict[position.swap_symbol]
                    exchange_size = float(exchange_swap_pos.get('pos', 0))
                    
                    # 如果交易所持仓为0但本地记录不为0，说明持仓可能已被平仓
                    if exchange_size == 0 and position.swap_position != 0:
                        logger.warning(f"持仓 {position_id} 在交易所上可能已被平仓")
                        position.status = 'CLOSING'
                        self.update_position(position)
                else:
                    # 交易所没有该持仓
                    if position.swap_position != 0:
                        logger.warning(f"持仓 {position_id} 在交易所上未找到")
                        position.status = 'CLOSING'
                        self.update_position(position)
                        
        except Exception as e:
            logger.error(f"同步持仓状态失败: {e}")
            
    def create_funding_rate_position(self, 
                                    exchange_id: str,
                                    spot_symbol: str, 
                                    swap_symbol: str,
                                    spot_size: float,
                                    swap_size: float,
                                    spot_price: float,
                                    swap_price: float,
                                    basis: float) -> Optional[FundingRateArbitragePosition]:
        """
        创建新的资金费率套利持仓
        
        Args:
            exchange_id: 交易所ID
            spot_symbol: 现货交易对符号
            swap_symbol: 永续合约交易对符号
            spot_size: 现货持仓数量
            swap_size: 永续合约持仓数量
            spot_price: 现货价格
            swap_price: 永续合约价格
            basis: 当前基差
            
        Returns:
            新创建的持仓对象，如果创建失败则返回None
        """
        try:
            # 生成唯一持仓ID
            position_id = f"FR_{exchange_id}_{spot_symbol}_{int(time.time())}"
            
            # 创建新持仓
            position = FundingRateArbitragePosition(
                position_id=position_id,
                exchange_id=exchange_id,
                spot_symbol=spot_symbol,
                swap_symbol=swap_symbol,
                spot_position=spot_size,
                swap_position=swap_size,
                entry_spot_price=spot_price,
                entry_swap_price=swap_price,
                entry_basis=basis,
                entry_time=time.time(),
                last_update_time=time.time(),
                status="OPENED",
                pnl=0.0,
                metadata={
                    "strategy_type": "funding_rate",
                    "creation_reason": "高资金费率套利"
                }
            )
            
            # 添加到管理器并保存到数据库
            if self.add_position(position):
                logger.info(f"成功创建资金费率套利持仓: {position_id}")
                return position
            else:
                logger.error(f"创建资金费率套利持仓失败: {position_id}")
                return None
                
        except Exception as e:
            logger.error(f"创建资金费率套利持仓时发生错误: {e}")
            return None

    def reconcile_positions_with_exchange(self, api_connector, data_processor):
        """
        与交易所的实际持仓状态进行同步和核对。
        Args:
            api_connector: OkxAPIConnector 实例
            data_processor: DataProcessor 实例 (可能需要获取最新价格等)
        """
        logger.info("Starting position reconciliation with exchange.")

        try:
            # 1. 获取交易所最新持仓和账户信息
            exchange_positions = api_connector.get_positions() # 获取所有交易所持仓
            account_info = api_connector.get_account_balance() # 获取账户信息

            if exchange_positions is None:
                 logger.warning("Could not retrieve exchange positions for reconciliation. Skipping sync.")
                 # TODO: 触发告警，同步失败是很严重的
                 return

            if account_info:
                 # 更新账户信息（供 RiskManager 使用）
                 # self.total_balance = ... # PositionManager 可以存储总余额
                 # self.margin_ratio = ... # PositionManager 可以存储总保证金率
                 logger.info("Account info synced from exchange.")

            # 创建一个字典，以 instId 和 posSide 为 key，方便查找交易所持仓
            exchange_pos_map = {}
            for pos in exchange_positions:
                 # 交易所持仓通常有 instId 和 posSide (对于合约)，现货可能只有 instId
                 key = (pos.get('instId'), pos.get('posSide', '')) # 组合 key
                 exchange_pos_map[key] = pos
                 # TODO: 对于现货，需要特殊处理，因为它没有 posSide，可能需要根据数量判断是哪条腿

            synced_position_ids = set() # 记录成功同步的内部头寸ID

            # 2. 核对内部持仓与交易所持仓
            internal_pos_ids_to_remove = []
            for pos_id, internal_pos in list(self.positions.items()): # 遍历副本，以便在循环中修改原字典
                 logger.debug(f"Reconciling internal position: {pos_id}")

                 # 尝试在交易所持仓中找到对应的永续合约腿
                 swap_key = (internal_pos.inst_id + '-SWAP', 'short') # 假设永续合约ID是 instId + '-SWAP'
                 exchange_swap_leg = exchange_pos_map.pop(swap_key, None) # 找到并从 map 中移除，剩下的就是交易所"多余"的持仓

                 # 尝试在交易所持仓中找到对应的现货腿
                 # 现货匹配更复杂，可能需要根据 instId 和数量范围来判断是否匹配内部的 spot_leg
                 # 简化处理：假设永续合约腿找到了，就认为对应的现货腿也应该存在且数量匹配
                 # 实际需要更严谨的匹配逻辑，或者单独查找现货持仓
                 # exchange_spot_leg = api_connector.get_spot_position(internal_pos.inst_id) # 可能需要单独API方法

                 if exchange_swap_leg: # 永续合约腿找到了
                      logger.debug(f"Found matching swap leg for {pos_id} on exchange.")
                      # 使用交易所数据更新内部 Swap 腿状态
                      # 需要解析 exchange_swap_leg 的字段，更新 internal_pos.swap_leg
                      # 例如:
                      # internal_pos.update_swap_leg(
                      #    executed_qty_coin=float(exchange_swap_leg.get('pos', 0)), # 当前持仓数量
                      #    executed_price=float(exchange_swap_leg.get('avgPx', 0)), # 平均开仓价格
                      #    current_qty_coin=float(exchange_swap_leg.get('pos', 0)),
                      #    current_price=float(exchange_swap_leg.get('last', 0)), # 最新价格
                      #    floating_pnl=float(exchange_swap_leg.get('upl', 0)), # 浮动盈亏
                      #    margin=float(exchange_swap_leg.get('margin', 0)), # 持仓保证金
                      #    liquidation_price=float(exchange_swap_leg.get('liqPx', 0)) # 强平价格
                      # )
                      # internal_pos.status = 'OPENED' # 假设找到交易所持仓就认为是打开状态
                      synced_position_ids.add(pos_id)

                      # TODO: 同样逻辑处理现货腿的匹配和更新
                      # exchange_spot_leg = ... # 找到现货持仓
                      # if exchange_spot_leg:
                      #    internal_pos.update_spot_leg(...)
                      # else:
                      #    logger.warning(f"Internal position {pos_id} swap leg found, but spot leg not found on exchange!")
                      #    # 触发告警，这个头寸可能不健康

                 else: # 内部头寸在交易所没找到对应的永续合约腿
                      logger.warning(f"Internal position {pos_id} (Swap Leg) not found on exchange. Marking as closed/error.")
                      internal_pos.status = 'CLOSED' # 或 'LIQUIDATED', 'ERROR'
                      # TODO: 根据需要设置 close_time, total_pnl (可能需要从账户历史推断或标记未知)
                      internal_pos_ids_to_remove.append(pos_id) # 标记待移除

            # 3. 处理交易所存在但内部没有的持仓 (剩余在 exchange_pos_map 中的)
            for (inst_id, pos_side), exchange_pos in exchange_pos_map.items():
                 logger.warning(f"Exchange has unexpected position: {inst_id} - {pos_side} Qty: {exchange_pos.get('pos')}. Not managed by this bot.")
                 self.trigger_alert("Unexpected Exchange Position", f"Exchange has position {inst_id}-{pos_side} not found in bot's state. Please check manually.", level='warning')
                 # 默认不处理，只告警。如果需要处理，这里是实现逻辑的地方。

            # 4. 移除内部已标记为关闭的头寸
            for pos_id in internal_pos_ids_to_remove:
                 self.remove_position(pos_id) # remove_position 方法中应该包含保存持久化的逻辑

            logger.info("Position reconciliation completed.")
            self.save_positions() # 同步完成后，保存一次最新的状态

        except Exception as e:
            logger.error(f"Error during position reconciliation: {e}")
            self.trigger_alert("Position Reconciliation Error", f"An error occurred during sync: {e}", level='critical')
            # TODO: 触发告警，同步失败是很严重的风险，可能需要暂停交易

    # TODO: PositionManager 需要有一个 trigger_alert 方法，或者调用 RiskManager 的 trigger_alert 方法
    def trigger_alert(self, subject: str, message: str, level: str = 'warning'):
         """ Placeholder for triggering alerts """
         if level == 'critical':
              logger.critical(f"ALERT: {subject} - {message}")
         elif level == 'warning':
              logger.warning(f"ALERT: {subject} - {message}")
         else:
              logger.info(f"ALERT: {subject} - {message}")
         # Actual alerting mechanism (email, sms etc.) should be implemented here or called from here
         pass
