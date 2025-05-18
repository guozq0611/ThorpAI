import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import threading
import pandas as pd
import numpy as np
import time
from btc_model.core.wrapper.db_wrapper import DBWrapper
from btc_model.core.util.log_util import Logger
from btc_model.core.backend.websocket_service import WebSocketService

class FundingRateWhitelistManager:
    """
    管理资金费率套利的交易对白名单
    
    功能:
    1. 从数据库加载白名单交易对
    2. 提供交易对的过滤和查询功能
    3. 更新交易对的基差和资金费率统计数据
    4. 根据交易对的质量自动评分
    5. 支持白名单的动态调整和维护
    """
    
    def __init__(self, 
                 db_wrapper: DBWrapper,
                 websocket_service: WebSocketService
                 ):
        """
        初始化白名单管理器
        
        Args:
            db_wrapper: 数据库连接包装器
        """
        self.db_wrapper: DBWrapper = db_wrapper
        self.websocket_service: WebSocketService = websocket_service
        self.whitelist: List[Dict] = []  # 存储白名单交易对信息
        self.whitelist_dict: Dict[str, Dict] = {}  # 用于快速查找的字典，键为交易对ID
        
        # 锁用于线程安全操作
        self._lock = threading.RLock()
        
        # 加载初始白名单
        self.load_whitelist()
        
        Logger.info(f"FundingRateWhitelistManager initialized with {len(self.whitelist)} trading pairs")
    
    def load_whitelist(self) -> None:
        """
        从数据库加载白名单交易对
        """
        try:
            query = """
            SELECT 
                exchange_id, base_currency, quote_currency, 
                spot_inst_id, swap_inst_id,
                is_active, comment, created_at, updated_at
            FROM funding_rate_arbitrage_whitelist
            WHERE is_active = TRUE
            """
            
            with self._lock:
                rows = self.db_wrapper.fetch_result(query)
                
                # 清空现有白名单
                self.whitelist.clear()
                self.whitelist_dict.clear()
                
                # 加载新的白名单数据
                for row in rows:
                    pair_data = {
                        'exchange_id': row[0],
                        'base_currency': row[1],
                        'quote_currency': row[2],
                        'spot_inst_id': row[3],
                        'swap_inst_id': row[4],
                        'is_active': row[5],
                        'comment': row[6],
                        'created_at': row[7],
                        'updated_at': row[8]
                    }
                    
                    # 生成唯一键，用于快速查找
                    key = f"{row[0]}:{row[3]}:{row[4]}"  # exchange_id:spot_inst_id:swap_inst_id
                    
                    self.whitelist.append(pair_data)
                    self.whitelist_dict[key] = pair_data
            
            Logger.info(f"Loaded {len(self.whitelist)} trading pairs from whitelist")
            
        except Exception as e:
            Logger.error(f"Error loading whitelist: {str(e)}")
            # 加载失败时，使用空白名单
            with self._lock:
                self.whitelist.clear()
                self.whitelist_dict.clear()
    
    def get_whitelist(self) -> List[Dict]:
        """
        获取当前白名单的副本
        
        Returns:
            白名单交易对列表的副本
        """
        with self._lock:
            return self.whitelist.copy()
    
    def is_in_whitelist(self, exchange_id: str, spot_inst_id: str, swap_inst_id: str) -> bool:
        """
        检查交易对是否在白名单中
        
        Args:
            exchange_id: 交易所ID
            spot_inst_id: 现货交易对ID
            swap_inst_id: 永续合约交易对ID
            
        Returns:
            是否在白名单中
        """
        key = f"{exchange_id}:{spot_inst_id}:{swap_inst_id}"
        with self._lock:
            return key in self.whitelist_dict
    
    def get_pair_info(self, exchange_id: str, spot_inst_id: str, swap_inst_id: str) -> Optional[Dict]:
        """
        获取指定交易对的详细信息
        
        Args:
            exchange_id: 交易所ID
            spot_inst_id: 现货交易对ID
            swap_inst_id: 永续合约交易对ID
            
        Returns:
            交易对信息字典，若不存在则返回None
        """
        key = f"{exchange_id}:{spot_inst_id}:{swap_inst_id}"
        with self._lock:
            return self.whitelist_dict.get(key)
    
    def add_to_whitelist(self,
                         exchange_id: str, 
                         base_currency: str, 
                         quote_currency: str, 
                         spot_inst_id: str, 
                         swap_inst_id: str, 
                         comment: str = None
                         ) -> bool:
        """
        添加新的交易对到白名单
        
        Args:
            exchange_id: 交易所ID
            base_currency: 基础货币
            quote_currency: 计价货币
            spot_inst_id: 现货交易对ID
            swap_inst_id: 永续合约交易对ID
            comment: 备注信息
            
        Returns:
            是否添加成功
        """
        try:
            query = """
            INSERT INTO funding_rate_arbitrage_whitelist (
                exchange_id, 
                base_currency, 
                quote_currency, 
                spot_inst_id, 
                swap_inst_id, 
                comment, 
                is_active
            ) VALUES (
                :exchange_id, 
                :base_currency, 
                :quote_currency, 
                :spot_inst_id, 
                :swap_inst_id, 
                :comment, 
                :is_active
            )on duplicate key update 
                exchange_id = :exchange_id,
                base_currency = :base_currency,
                quote_currency = :quote_currency,
                spot_inst_id = :spot_inst_id,
                swap_inst_id = :swap_inst_id,
                comment = :comment,
                is_active = :is_active
            """
            params = {
                'exchange_id': exchange_id,
                'base_currency': base_currency,
                'quote_currency': quote_currency,
                'spot_inst_id': spot_inst_id,
                'swap_inst_id': swap_inst_id,
                'comment': comment,
                'is_active': True
            }
            
            self.db_wrapper.execute_sql(query, params)
            
            # 重新加载白名单
            self.load_whitelist()
            
            # 找到新添加的交易对
            key = f"{exchange_id}:{spot_inst_id}:{swap_inst_id}"
            with self._lock:
                if key in self.whitelist_dict:
                    # 广播添加更新到UI
                    self.broadcast_whitelist_update("add", self.whitelist_dict[key])
            
            return True
            
        except Exception as e:
            Logger.error(f"Error adding to whitelist: {str(e)}")
            return False
    
    def remove_from_whitelist(self, exchange_id: str, spot_inst_id: str, swap_inst_id: str) -> bool:
        """
        从白名单中移除交易对（将is_active设为FALSE）
        
        Args:
            exchange_id: 交易所ID
            spot_inst_id: 现货交易对ID
            swap_inst_id: 永续合约交易对ID
            
        Returns:
            是否移除成功
        """
        try:
            # 先获取要移除的交易对信息（用于后续广播）
            key = f"{exchange_id}:{spot_inst_id}:{swap_inst_id}"
            pair_to_remove = None
            with self._lock:
                if key in self.whitelist_dict:
                    pair_to_remove = self.whitelist_dict[key].copy()
            
            query = """
            UPDATE funding_rate_arbitrage_whitelist
            SET is_active = FALSE
            WHERE exchange_id = %s AND spot_inst_id = %s AND swap_inst_id = %s
            """
            params = (exchange_id, spot_inst_id, swap_inst_id)
            
            rows_affected = self.db_wrapper.execute_sql(query, params)
            
            if rows_affected > 0:
                # 重新加载白名单
                self.load_whitelist()
                
                # 如果有找到被移除的交易对信息，广播移除事件
                if pair_to_remove:
                    self.broadcast_whitelist_update("remove", pair_to_remove)
                
                return True
            else:
                Logger.warning(f"No records found to remove from whitelist: {exchange_id}:{spot_inst_id}:{swap_inst_id}")
                return False
            
        except Exception as e:
            Logger.error(f"Error removing from whitelist: {str(e)}")
            return False
    
    def update_statistics(self, exchange_id: str, spot_inst_id: str, swap_inst_id: str, 
                         stats_data: Dict) -> bool:
        """
        更新交易对的统计数据
        
        Args:
            exchange_id: 交易所ID
            spot_inst_id: 现货交易对ID
            swap_inst_id: 永续合约交易对ID
            stats_data: 包含各统计字段的字典
            
        Returns:
            是否更新成功
        """
        try:
            # 构建更新语句
            update_fields = []
            params = []
            
            # 添加可能要更新的字段
            possible_fields = [
                'avg_ann_funding_rate_90d', 'median_ann_funding_rate_90d', 
                'std_dev_ann_funding_rate_90d', 'positive_rate_pct_90d',
                'avg_basis_90d', 'median_basis_90d', 'std_dev_basis_90d', 
                'max_basis_90d', 'min_basis_90d', 'basis_quartile_1_90d',
                'basis_quartile_3_90d', 'basis_volatility_90d', 'positive_basis_pct_90d',
                'basis_funding_correlation_90d', 'avg_basis_to_funding_ratio_90d',
                'potential_apr_90d', 'sharpe_ratio_90d', 'max_drawdown_90d'
            ]
            
            # 只更新提供的字段
            for field in possible_fields:
                if field in stats_data:
                    update_fields.append(f"{field} = %s")
                    params.append(stats_data[field])
            
            # 如果没有字段需要更新，直接返回
            if not update_fields:
                Logger.warning(f"No fields to update for {exchange_id}:{spot_inst_id}:{swap_inst_id}")
                return False
            
            # 完成参数列表
            params.extend([exchange_id, spot_inst_id, swap_inst_id])
            
            # 构建并执行更新查询
            query = f"""
            UPDATE funding_rate_arbitrage_whitelist
            SET {', '.join(update_fields)}
            WHERE exchange_id = %s AND spot_inst_id = %s AND swap_inst_id = %s
            """
            
            rows_affected = self.db_wrapper.execute_sql(query, params)
            
            if rows_affected > 0:
                # 更新内存中的数据
                key = f"{exchange_id}:{spot_inst_id}:{swap_inst_id}"
                with self._lock:
                    if key in self.whitelist_dict:
                        for field, value in stats_data.items():
                            if field in possible_fields:
                                self.whitelist_dict[key][field] = value
                
                # 广播更新事件到UI
                self.broadcast_whitelist_update("update", self.whitelist_dict[key])
                
                return True
            else:
                Logger.warning(f"No records found to update statistics: {exchange_id}:{spot_inst_id}:{swap_inst_id}")
                return False
            
        except Exception as e:
            Logger.error(f"Error updating statistics: {str(e)}")
            return False
    
    def refresh_whitelist(self) -> bool:
        """
        重新从数据库加载白名单
        
        Returns:
            是否成功刷新
        """
        try:
            self.load_whitelist()
            
            # 广播刷新事件到UI
            self.broadcast_whitelist_update("refresh")
            
            return True
        except Exception as e:
            Logger.error(f"Error refreshing whitelist: {str(e)}")
            return False
    
    def get_filtered_pairs(self, min_funding_rate: float = None, min_sharpe: float = None, 
                          max_drawdown: float = None) -> List[Dict]:
        """
        根据条件筛选白名单交易对
        
        Args:
            min_funding_rate: 最小平均年化资金费率(%)
            min_sharpe: 最小夏普比率
            max_drawdown: 最大回撤限制(%)
            
        Returns:
            符合条件的交易对列表
        """
        with self._lock:
            filtered_pairs = self.whitelist.copy()
        
        # 应用过滤条件
        if min_funding_rate is not None:
            filtered_pairs = [p for p in filtered_pairs 
                             if p.get('avg_ann_funding_rate_90d') is not None 
                             and p['avg_ann_funding_rate_90d'] >= min_funding_rate]
        
        if min_sharpe is not None:
            filtered_pairs = [p for p in filtered_pairs 
                             if p.get('sharpe_ratio_90d') is not None 
                             and p['sharpe_ratio_90d'] >= min_sharpe]
        
        if max_drawdown is not None:
            filtered_pairs = [p for p in filtered_pairs 
                             if p.get('max_drawdown_90d') is not None 
                             and p['max_drawdown_90d'] <= max_drawdown]
        
        return filtered_pairs
    
    def calculate_pair_score(self, pair_data: Dict) -> float:
        """
        计算交易对的综合评分
        
        Args:
            pair_data: 交易对数据字典
            
        Returns:
            0-100的综合评分，越高越好
        """
        # 定义各指标的权重
        weights = {
            'avg_ann_funding_rate_90d': 0.35,  # 平均年化资金费率
            'std_dev_ann_funding_rate_90d': 0.10,  # 资金费率标准差（越低越好）
            'avg_basis_90d': 0.15,  # 平均基差
            'sharpe_ratio_90d': 0.20,  # 夏普比率
            'max_drawdown_90d': 0.10,  # 最大回撤（越低越好）
            'basis_funding_correlation_90d': 0.10  # 基差与资金费率相关性（越高越好）
        }
        
        # 为每个指标计算标准化分数
        scores = {}
        
        # 平均年化资金费率 (假设10%为满分)
        funding_rate = pair_data.get('avg_ann_funding_rate_90d')
        if funding_rate is not None:
            scores['avg_ann_funding_rate_90d'] = min(100, funding_rate * 10)
        else:
            scores['avg_ann_funding_rate_90d'] = 0
        
        # 资金费率标准差 (假设低于2%为满分，高于10%为0分)
        std_dev = pair_data.get('std_dev_ann_funding_rate_90d')
        if std_dev is not None:
            scores['std_dev_ann_funding_rate_90d'] = max(0, 100 - (std_dev - 2) * (100 / 8))
        else:
            scores['std_dev_ann_funding_rate_90d'] = 0
        
        # 平均基差 (假设1%为满分)
        basis = pair_data.get('avg_basis_90d')
        if basis is not None:
            scores['avg_basis_90d'] = min(100, basis * 100)
        else:
            scores['avg_basis_90d'] = 0
        
        # 夏普比率 (假设3以上为满分)
        sharpe = pair_data.get('sharpe_ratio_90d')
        if sharpe is not None:
            scores['sharpe_ratio_90d'] = min(100, sharpe * (100/3))
        else:
            scores['sharpe_ratio_90d'] = 0
        
        # 最大回撤 (假设低于5%为满分，高于20%为0分)
        drawdown = pair_data.get('max_drawdown_90d')
        if drawdown is not None:
            scores['max_drawdown_90d'] = max(0, 100 - (drawdown - 5) * (100 / 15))
        else:
            scores['max_drawdown_90d'] = 0
        
        # 基差与资金费率相关性 (假设0.8以上为满分)
        correlation = pair_data.get('basis_funding_correlation_90d')
        if correlation is not None:
            scores['basis_funding_correlation_90d'] = min(100, correlation * (100/0.8))
        else:
            scores['basis_funding_correlation_90d'] = 0
        
        # 计算加权平均分
        total_weight = 0
        weighted_sum = 0
        
        for key, weight in weights.items():
            if key in scores:
                weighted_sum += scores[key] * weight
                total_weight += weight
        
        if total_weight > 0:
            return weighted_sum / total_weight
        else:
            return 0
    
    def get_top_pairs(self, limit: int = 10) -> List[Dict]:
        """
        获取评分最高的交易对
        
        Args:
            limit: 返回的交易对数量
            
        Returns:
            评分最高的交易对列表，每个交易对包含评分
        """
        with self._lock:
            # 为每个交易对计算评分
            scored_pairs = []
            for pair in self.whitelist:
                score = self.calculate_pair_score(pair)
                pair_with_score = pair.copy()
                pair_with_score['score'] = score
                scored_pairs.append(pair_with_score)
            
            # 按评分排序
            scored_pairs.sort(key=lambda x: x['score'], reverse=True)
            
            # 返回前limit个
            return scored_pairs[:limit]

    def broadcast_whitelist_update(self, update_type: str = "refresh", pair_data: Dict = None):
        """
        向UI广播白名单更新事件
        
        Args:
            update_type: 更新类型：'refresh'(刷新整个列表), 'add'(添加), 'remove'(移除), 'update'(更新)
            pair_data: 针对add/update/remove操作的交易对数据
        """
        try:
            message = {
                "type": "funding_rate_whitelist_update",
                "update_type": update_type,
                "timestamp": time.time()
            }
            
            # 针对不同类型的更新添加相应的数据
            if update_type == "refresh":
                # 刷新整个列表时，发送完整的白名单
                with self._lock:
                    pairs_with_score = []
                    for pair in self.whitelist:
                        pair_with_score = pair.copy()
                        pair_with_score['score'] = self.calculate_pair_score(pair)
                        pairs_with_score.append(pair_with_score)
                    
                    message["data"] = pairs_with_score
            
            elif update_type in ["add", "update", "remove"] and pair_data:
                # 单条记录的操作，只发送相关的交易对数据
                if update_type in ["add", "update"]:
                    pair_data_with_score = pair_data.copy()
                    pair_data_with_score['score'] = self.calculate_pair_score(pair_data)
                    message["data"] = pair_data_with_score
                else:  # remove
                    message["data"] = pair_data
            
            # 异步发送更新消息到WebSocket
            self._send_websocket_message(message)
            
            Logger.info(f"已广播白名单{update_type}更新到UI")
        except Exception as e:
            Logger.error(f"广播白名单更新失败: {e}")

    def broadcast_funding_rate_signal(self, pair_info: Dict, current_data: Dict):
        """
        广播资金费率套利信号
        
        Args:
            pair_info: 交易对信息字典
            current_data: 当前市场数据，包含资金费率、基差等
        """
        try:
            # 构建需要展示的信号数据
            exchange_id = pair_info['exchange_id']
            spot_inst_id = pair_info['spot_inst_id']
            swap_inst_id = pair_info['swap_inst_id']
            
            # 生成信号数据
            signal_data = {
                "type": "funding_rate_signal",
                "exchange_id": exchange_id,
                "spot_inst_id": spot_inst_id, 
                "swap_inst_id": swap_inst_id,
                "base_currency": pair_info['base_currency'],
                "quote_currency": pair_info['quote_currency'],
                "current_funding_rate": current_data.get('funding_rate', 0),
                "annualized_funding_rate": current_data.get('annualized_funding_rate', 0),
                "next_funding_rate": current_data.get('next_funding_rate', 0),
                "next_annualized_funding_rate": current_data.get('next_annualized_funding_rate', 0),
                "basis": current_data.get('basis', 0),
                "basis_pct": current_data.get('basis_pct', 0),
                "spot_price": current_data.get('spot_price', 0),
                "swap_price": current_data.get('swap_price', 0),
                "score": self.calculate_pair_score(pair_info),
                "next_funding_time": current_data.get('next_funding_time', ''),
                "status": "active",
                "timestamp": time.time()
            }
            
            # 异步发送信号到WebSocket
            self._send_websocket_message(signal_data)
            
            Logger.info(f"已发送资金费率套利信号: {exchange_id} {spot_inst_id}/{swap_inst_id}, 年化资金费率: {signal_data['annualized_funding_rate']:.2f}%")
        except Exception as e:
            Logger.error(f"发送资金费率套利信号失败: {e}")

    def _send_websocket_message(self, message: Dict):
        """
        通过WebSocket发送消息的辅助方法
        
        Args:
            message: 要发送的消息字典
        """
        try:
            # 创建一个线程安全的事件循环发送WebSocket消息
            from concurrent.futures import ThreadPoolExecutor
            
            # 将异步调用放入一个独立的任务中执行
            def send_message_task():
                # 在新线程中创建新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # 在事件循环中执行异步调用
                    loop.run_until_complete(self.websocket_service.broadcast_message("funding_rate", message))
                finally:
                    loop.close()
            
            # 使用线程池执行任务
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(send_message_task)
                
        except Exception as e:
            Logger.error(f"WebSocket消息发送失败: {e}")

# 使用示例
if __name__ == "__main__":
    # 假设db_wrapper已正确初始化
    # db_wrapper = DBWrapper(...)
    
    # 初始化白名单管理器
    # whitelist_manager = FundingRateWhitelistManager(db_wrapper)
    
    # 获取白名单
    # pairs = whitelist_manager.get_whitelist()
    # print(f"Found {len(pairs)} trading pairs in whitelist")
    
    # 获取评分最高的交易对
    # top_pairs = whitelist_manager.get_top_pairs(5)
    # for pair in top_pairs:
    #     print(f"{pair['exchange_id']} {pair['spot_inst_id']}/{pair['swap_inst_id']}: Score={pair['score']:.2f}")
    
    # 筛选高资金费率的交易对
    # high_funding_pairs = whitelist_manager.get_filtered_pairs(min_funding_rate=8.0)
    # print(f"Found {len(high_funding_pairs)} pairs with funding rate >= 8%")
    
    pass 