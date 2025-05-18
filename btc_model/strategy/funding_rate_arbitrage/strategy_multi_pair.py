import pandas as pd
import threading
import queue
import asyncio
from typing import NamedTuple, Dict, List, Tuple, Optional, Any
import ccxt
import time
import ccxt.pro as ccxtpro
import numpy as np
import json
import os
from collections import defaultdict

from btc_model.core.util.log_util import Logger
from btc_model.strategy.exchange_arbitrage.pairs_monitor import PairsMonitor
from btc_model.core.common.object import PositionData, BlacklistSymbol
from btc_model.trade.position_holder import PositionHolder
from btc_model.setting.setting import get_settings
from btc_model.core.util.crypto_util import CryptoUtil
from btc_model.market.market_data_service import MarketDataService
from btc_model.core.common.context import Context
from btc_model.trade.arbitrage_position_manager import ArbitragePositionManager
from btc_model.core.util.crypto_util import CryptoUtil
from btc_model.core.util.db_util import DBUtil

from btc_model.strategy.exchange_arbitrage.object import ArbitrageSignal
from btc_model.core.backend.websocket_service import WebSocketService
from btc_model.manager.instance_manager import set_instance, register_instance

from btc_model.strategy.funding_rate_arbitrage.data_processor import DataProcessor
from btc_model.strategy.funding_rate_arbitrage.trade.funding_rate_arbitrage_position_manager import PositionManager
from btc_model.strategy.funding_rate_arbitrage.execution_manager______ import ExecutionManager
from btc_model.strategy.funding_rate_arbitrage.risk_manager import RiskManager
from btc_model.strategy.funding_rate_arbitrage.strategy_params import StrategyParams
from btc_model.strategy.funding_rate_arbitrage.exchange_connector import ExchangeConnector

class TradingPairInfo:
    """交易对信息类，存储单个交易对的所有组件和状态"""
    
    def __init__(self, 
                 pair_id: str,
                 exchange_id: str,
                 spot_symbol: str, 
                 swap_symbol: str,
                 data_processor: DataProcessor,
                 position_manager: PositionManager,
                 execution_manager: ExecutionManager):
        """
        初始化交易对信息
        
        Args:
            pair_id: 交易对唯一标识
            exchange_id: 交易所ID
            spot_symbol: 现货交易对符号
            swap_symbol: 永续合约交易对符号
            data_processor: 数据处理器实例
            position_manager: 仓位管理器实例
            execution_manager: 执行管理器实例
        """
        self.pair_id = pair_id
        self.exchange_id = exchange_id
        self.spot_symbol = spot_symbol
        self.swap_symbol = swap_symbol
        self.data_processor = data_processor
        self.position_manager = position_manager
        self.execution_manager = execution_manager
        
        # 状态信息
        self.active = True  # 是否激活
        self.last_eval_time = 0  # 上次评估时间
        self.last_data_update_time = 0  # 上次数据更新时间
        self.has_open_position = False  # 是否有开放仓位
        self.last_metrics = {}  # 上次的指标数据
        self.opportunity_score = 0  # 机会评分
        
    def update_market_data(self):
        """更新市场数据"""
        self.data_processor.update_market_data()
        self.last_data_update_time = time.time()
        
    def evaluate_opportunity(self, strategy_params):
        """评估交易机会"""
        self.last_eval_time = time.time()
        
        # 获取最新指标
        metrics = self.data_processor.get_latest_metrics()
        self.last_metrics = metrics
        
        # 获取当前仓位
        positions = self.position_manager.get_all_positions()
        self.has_open_position = len(positions) > 0
        
        # 基本数据检查
        if not metrics.get('basis'):
            self.opportunity_score = 0
            return False, "基差数据不可用"
            
        # 检查基差是否在可接受范围内
        basis = metrics.get('basis', 0)
        if basis < strategy_params.common_params.min_basis_for_open:
            self.opportunity_score = 0
            return False, f"基差 ({basis:.8f}) 低于最小开仓要求"
            
        if basis > strategy_params.common_params.max_acceptable_basis:
            self.opportunity_score = 0
            return False, f"基差 ({basis:.8f}) 高于最大可接受值"
        
        # 检查是否已有仓位
        if self.has_open_position:
            self.opportunity_score = 0
            return False, "已存在活跃仓位"
            
        # 计算机会评分
        funding_rate = metrics.get('next_annualized_funding_rate', 0)
        
        # 评分算法: 将资金费率作为主要因素，基差作为次要因素
        score = 0
        if funding_rate:
            score += funding_rate * 10  # 资金费率权重
        
        if basis > 0:
            # 基差越小越好(但不为负)
            score += (1 / (1 + basis * 1000)) * 5
        
        self.opportunity_score = score
        return True, f"有效机会，评分: {score:.2f}"
        
    def get_info(self):
        """获取交易对信息摘要"""
        return {
            'pair_id': self.pair_id,
            'exchange': self.exchange_id,
            'spot_symbol': self.spot_symbol,
            'swap_symbol': self.swap_symbol,
            'active': self.active,
            'has_position': self.has_open_position,
            'last_eval_time': self.last_eval_time,
            'last_metrics': self.last_metrics,
            'opportunity_score': self.opportunity_score
        }


class FundingRateArbitrageStrategyMultiPair:
    """
    支持多交易对的资金费率套利策略
    """
    def __init__(self, 
                 exchange_connector: ExchangeConnector,
                 trading_pairs: List[Dict[str, str]],
                 risk_manager: RiskManager,
                 strategy_params: StrategyParams):
        """
        初始化多交易对套利策略
        
        Args:
            exchange_connector: 交易所连接器
            trading_pairs: 交易对列表，每项包含 spot_symbol 和 swap_symbol
            risk_manager: 风险管理器
            strategy_params: 策略参数
        """
        self.exchange_connector = exchange_connector
        self.risk_manager = risk_manager
        self.strategy_params = strategy_params
        self.is_live = get_settings('trade')['live_mode']
        
        # 创建交易对信息字典
        self.pairs = {}
        self._init_trading_pairs(trading_pairs)
        
        # 跟踪资源分配
        self.total_allocated_capital = 0.0
        self.available_capital = 0.0
        self._update_capital_info()
        
        # 黑名单交易对
        self.blacklist_pairs = set()
        
        # 状态跟踪
        self.is_running = True
        self.last_global_risk_check_time = 0
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_arbitrage_opportunities_loop, daemon=True)
        self.monitor_thread.start()
        
        Logger.info(f"多交易对资金费率套利策略初始化完成, 监控 {len(self.pairs)} 个交易对")

    def _init_trading_pairs(self, trading_pairs: List[Dict[str, str]]):
        """初始化所有交易对"""
        for pair_info in trading_pairs:
            spot_symbol = pair_info['spot_symbol']
            swap_symbol = pair_info['swap_symbol']
            
            # 生成唯一ID
            pair_id = f"{spot_symbol}_{swap_symbol}"
            
            # 为每个交易对创建组件
            data_processor = DataProcessor(
                self.exchange_connector, 
                spot_symbol, 
                swap_symbol
            )
            
            position_manager = PositionManager()
            execution_manager = ExecutionManager(self.exchange_connector)
            
            # 创建交易对信息对象
            pair = TradingPairInfo(
                pair_id=pair_id,
                exchange_id=self.exchange_connector.exchange_id,
                spot_symbol=spot_symbol,
                swap_symbol=swap_symbol,
                data_processor=data_processor,
                position_manager=position_manager,
                execution_manager=execution_manager
            )
            
            # 添加到交易对字典
            self.pairs[pair_id] = pair
            
            Logger.info(f"初始化交易对: {pair_id}")

    def _monitor_arbitrage_opportunities_loop(self):
        """主监控循环"""
        while self.is_running:
            try:
                # 1. 更新所有交易对的市场数据
                self._update_all_market_data()
                
                # 2. 更新资金信息
                self._update_capital_info()
                
                # 3. 检查全局风险状态
                if time.time() - self.last_global_risk_check_time > self.strategy_params.monitor_params.risk_check_interval_sec:
                    self._check_global_risk()
                    self.last_global_risk_check_time = time.time()
                
                # 4. 评估所有交易对的机会
                self._evaluate_all_opportunities()
                
                # 5. 执行最佳机会
                self._execute_best_opportunities()
                
                # 6. 检查是否需要平仓
                self._check_all_close_signals()
                
                # 暂停一段时间
                time.sleep(self.strategy_params.monitor_params.strategy_eval_interval_sec)
                
            except Exception as e:
                Logger.error(f"监控循环异常: {str(e)}")
                time.sleep(5)  # 出错后短暂暂停
    
    def _update_all_market_data(self):
        """更新所有交易对的市场数据"""
        for pair_id, pair in self.pairs.items():
            if pair.active and pair_id not in self.blacklist_pairs:
                try:
                    pair.update_market_data()
                except Exception as e:
                    Logger.error(f"更新 {pair_id} 市场数据出错: {str(e)}")
    
    def _update_capital_info(self):
        """更新资金信息"""
        try:
            # 获取账户资金信息
            account_info = self.exchange_connector.get_account_info()
            if account_info:
                # 计算已分配资金
                self.total_allocated_capital = 0.0
                for pair_id, pair in self.pairs.items():
                    positions = pair.position_manager.get_all_positions()
                    for pos in positions:
                        self.total_allocated_capital += pos.get('investment_amount', 0)
                
                # 计算可用资金
                total_equity = account_info.get('total_equity', 0)
                # 预留10%作为缓冲
                buffer = total_equity * 0.1
                max_allocatable = total_equity - buffer
                
                # 可用资金 = 最大可分配资金 - 已分配资金
                self.available_capital = max(0, max_allocatable - self.total_allocated_capital)
                
                Logger.debug(f"资金更新: 总权益={total_equity}, 已分配={self.total_allocated_capital}, 可用={self.available_capital}")
            else:
                Logger.warning("获取账户信息失败, 无法更新资金状态")
        except Exception as e:
            Logger.error(f"更新资金信息出错: {str(e)}")
    
    def _check_global_risk(self):
        """检查全局风险状态"""
        try:
            # 计算总体浮动盈亏
            total_pnl = 0.0
            for pair_id, pair in self.pairs.items():
                positions = pair.position_manager.get_all_positions()
                for pos in positions:
                    total_pnl += pos.get('unrealized_pnl', 0)
            
            # 如果有分配资金，计算盈亏比例
            if self.total_allocated_capital > 0:
                pnl_ratio = total_pnl / self.total_allocated_capital
                
                # 如果亏损超过阈值，触发风险控制
                if pnl_ratio < self.strategy_params.risk_control_params.total_floating_pnl_limit:
                    Logger.warning(f"全局风险触发: 总浮动盈亏比例 {pnl_ratio:.2%}")
                    self._handle_global_risk()
            
            # 其他风险检查...
            
        except Exception as e:
            Logger.error(f"全局风险检查出错: {str(e)}")
    
    def _handle_global_risk(self):
        """处理全局风险事件"""
        # 根据风险等级采取不同行动
        try:
            # 1. 关闭表现最差的仓位
            self._close_worst_performing_positions()
            
            # 2. 通知风险管理器
            self.risk_manager.trigger_alert("全局风险触发", "总体浮动盈亏超过阈值，已关闭表现最差仓位")
            
        except Exception as e:
            Logger.error(f"处理全局风险事件出错: {str(e)}")
    
    def _close_worst_performing_positions(self):
        """关闭表现最差的仓位"""
        # 收集所有仓位信息
        all_positions = []
        for pair_id, pair in self.pairs.items():
            positions = pair.position_manager.get_all_positions()
            for pos in positions:
                pos_info = {
                    'pair_id': pair_id,
                    'position_id': pos.get('position_id'),
                    'unrealized_pnl': pos.get('unrealized_pnl', 0),
                    'pnl_ratio': pos.get('unrealized_pnl', 0) / pos.get('investment_amount', 1),
                    'pair': pair
                }
                all_positions.append(pos_info)
        
        # 按盈亏比例排序
        all_positions.sort(key=lambda x: x['pnl_ratio'])
        
        # 关闭最差的前1/3仓位
        num_to_close = max(1, len(all_positions) // 3)
        for i in range(num_to_close):
            if i < len(all_positions):
                worst_pos = all_positions[i]
                Logger.info(f"关闭表现最差仓位: {worst_pos['pair_id']}, PnL比例: {worst_pos['pnl_ratio']:.2%}")
                self._trigger_close(worst_pos['pair'], worst_pos['position_id'], "全局风险控制")
    
    def _evaluate_all_opportunities(self):
        """评估所有交易对的机会"""
        for pair_id, pair in self.pairs.items():
            if pair.active and pair_id not in self.blacklist_pairs:
                try:
                    valid, reason = pair.evaluate_opportunity(self.strategy_params)
                    if valid:
                        Logger.debug(f"{pair_id} 评估结果: {reason}")
                    else:
                        Logger.debug(f"{pair_id} 无交易机会: {reason}")
                except Exception as e:
                    Logger.error(f"评估 {pair_id} 机会出错: {str(e)}")
    
    def _execute_best_opportunities(self):
        """执行最佳交易机会"""
        # 计算可用仓位数
        max_concurrent = self.strategy_params.common_params.max_concurrent_positions
        active_positions = sum(1 for pair in self.pairs.values() if pair.has_open_position)
        available_slots = max(0, max_concurrent - active_positions)
        
        # 如果没有可用仓位数或资金不足，直接返回
        if available_slots == 0 or self.available_capital <= 0:
            return
            
        # 收集所有有效机会
        valid_opportunities = []
        for pair_id, pair in self.pairs.items():
            if pair.active and not pair.has_open_position and pair_id not in self.blacklist_pairs:
                if pair.opportunity_score > 0:
                    valid_opportunities.append((pair_id, pair, pair.opportunity_score))
        
        # 按照评分排序
        valid_opportunities.sort(key=lambda x: x[2], reverse=True)
        
        # 计算每个仓位的资金分配
        capital_per_position = self.available_capital / min(available_slots, len(valid_opportunities))
        min_capital = self.strategy_params.common_params.min_position_size_usd
        
        # 确保每个仓位有足够资金
        if capital_per_position < min_capital:
            Logger.warning(f"每个仓位分配资金 ({capital_per_position:.2f}) 低于最小值 ({min_capital:.2f})")
            return
        
        # 执行最佳机会
        executed_count = 0
        for pair_id, pair, score in valid_opportunities:
            if executed_count >= available_slots:
                break
                
            Logger.info(f"执行交易机会: {pair_id}, 评分: {score:.2f}, 分配资金: {capital_per_position:.2f}")
            
            # 在这里执行开仓逻辑
            self._open_position(pair, capital_per_position)
            
            executed_count += 1
    
    def _open_position(self, pair: TradingPairInfo, capital: float):
        """开仓"""
        try:
            # 这里需要根据您的具体实现替换为实际的开仓逻辑
            # 以下是示例代码框架
            
            # 1. 计算仓位大小
            metrics = pair.data_processor.get_latest_metrics()
            spot_price = metrics.get('spot_price', 0)
            if spot_price <= 0:
                Logger.error(f"无法开仓 {pair.pair_id}: 现货价格无效")
                return
            
            # 计算购买数量
            quantity = capital / spot_price
            
            # 2. 创建新仓位
            position_id = f"{pair.pair_id}_{int(time.time())}"
            
            # 3. 发送开仓指令
            open_instruction = {
                'position_id': position_id,
                'spot_symbol': pair.spot_symbol,
                'swap_symbol': pair.swap_symbol,
                'quantity': quantity,
                'capital': capital
            }
            
            # 4. 执行开仓
            # pair.execution_manager.handle_open_instruction(open_instruction)
            
            # 模拟成功开仓
            Logger.info(f"模拟开仓成功: {pair.pair_id}, 数量: {quantity}, 资金: {capital}")
            pair.has_open_position = True
            
        except Exception as e:
            Logger.error(f"开仓 {pair.pair_id} 出错: {str(e)}")
    
    def _check_all_close_signals(self):
        """检查所有交易对的平仓信号"""
        for pair_id, pair in self.pairs.items():
            if pair.has_open_position:
                try:
                    self._check_close_signal(pair)
                except Exception as e:
                    Logger.error(f"检查 {pair_id} 平仓信号出错: {str(e)}")
    
    def _check_close_signal(self, pair: TradingPairInfo):
        """检查单个交易对的平仓信号"""
        positions = pair.position_manager.get_all_positions()
        
        # 获取最新指标
        metrics = pair.data_processor.get_latest_metrics()
        current_funding_rate = metrics.get('annualized_funding_rate', 0)
        current_basis = metrics.get('basis')
        
        for position in positions:
            position_id = position.get('position_id')
            
            # 检查资金费率是否达到平仓阈值
            if current_funding_rate is not None and current_funding_rate < self.strategy_params.common_params.funding_rate_close_threshold:
                self._trigger_close(pair, position_id, f"资金费率 ({current_funding_rate:.2f}%) 低于平仓阈值")
                continue
                
            # 检查基差是否转为负值
            if current_basis is not None and current_basis < 0:
                self._trigger_close(pair, position_id, f"基差转为负值 ({current_basis:.8f})")
                continue
                
            # 其他平仓条件...
    
    def _trigger_close(self, pair: TradingPairInfo, position_id: str, reason: str):
        """触发平仓"""
        Logger.info(f"触发平仓: {pair.pair_id}, 原因: {reason}")
        
        try:
            # 在这里添加您的平仓执行逻辑
            # pair.execution_manager.handle_close_instruction({'position_id': position_id})
            
            # 模拟平仓成功
            Logger.info(f"模拟平仓成功: {pair.pair_id}, 仓位ID: {position_id}")
            pair.has_open_position = False
            
        except Exception as e:
            Logger.error(f"平仓 {pair.pair_id} 仓位 {position_id} 出错: {str(e)}")
    
    def add_trading_pair(self, spot_symbol: str, swap_symbol: str):
        """添加新的交易对"""
        pair_id = f"{spot_symbol}_{swap_symbol}"
        
        if pair_id in self.pairs:
            Logger.warning(f"交易对 {pair_id} 已存在")
            return
            
        # 创建交易对组件
        data_processor = DataProcessor(
            self.exchange_connector, 
            spot_symbol, 
            swap_symbol
        )
        
        position_manager = PositionManager()
        execution_manager = ExecutionManager(self.exchange_connector)
        
        # 创建交易对信息对象
        pair = TradingPairInfo(
            pair_id=pair_id,
            exchange_id=self.exchange_connector.exchange_id,
            spot_symbol=spot_symbol,
            swap_symbol=swap_symbol,
            data_processor=data_processor,
            position_manager=position_manager,
            execution_manager=execution_manager
        )
        
        # 添加到交易对字典
        self.pairs[pair_id] = pair
        
        Logger.info(f"添加新交易对: {pair_id}")
    
    def remove_trading_pair(self, pair_id: str, close_positions: bool = True):
        """移除交易对"""
        if pair_id not in self.pairs:
            Logger.warning(f"交易对 {pair_id} 不存在")
            return
            
        pair = self.pairs[pair_id]
        
        # 如果有开放仓位且要求关闭
        if pair.has_open_position and close_positions:
            positions = pair.position_manager.get_all_positions()
            for pos in positions:
                position_id = pos.get('position_id')
                self._trigger_close(pair, position_id, "删除交易对")
        
        # 从字典中移除
        del self.pairs[pair_id]
        
        Logger.info(f"移除交易对: {pair_id}")
    
    def get_trading_pairs_status(self):
        """获取所有交易对状态"""
        status = []
        for pair_id, pair in self.pairs.items():
            pair_status = pair.get_info()
            status.append(pair_status)
        return status
    
    def stop(self):
        """停止策略运行"""
        self.is_running = False
        Logger.info("策略停止运行")

# 示例用法
def run_multi_pair_strategy():
    # 创建交易所连接器
    exchange_connector = ExchangeConnector('okx')
    
    # 定义要监控的交易对
    trading_pairs = [
        {'spot_symbol': 'BTC-USDT', 'swap_symbol': 'BTC-USDT-SWAP'},
        {'spot_symbol': 'ETH-USDT', 'swap_symbol': 'ETH-USDT-SWAP'},
        {'spot_symbol': 'SOL-USDT', 'swap_symbol': 'SOL-USDT-SWAP'}
    ]
    
    # 创建风险管理器
    risk_manager = RiskManager(StrategyParams.from_settings().risk_control_params)
    
    # 创建并启动策略
    strategy = FundingRateArbitrageStrategyMultiPair(
        exchange_connector=exchange_connector,
        trading_pairs=trading_pairs,
        risk_manager=risk_manager,
        strategy_params=StrategyParams.from_settings()
    )
    
    # 主线程可以继续做其他事情，策略在后台线程运行
    
    # 如果需要停止策略
    # strategy.stop()
    
    return strategy 