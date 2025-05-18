import pandas as pd
import threading
import queue
import asyncio
from typing import NamedTuple, Dict, Tuple, Optional, Any
import ccxt
import time
import ccxt.pro as ccxtpro
import numpy as np
import json
import os
from collections import defaultdict
from datetime import datetime

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

from btc_model.core.wrapper.db_wrapper import DBWrapper
from btc_model.strategy.exchange_arbitrage.object import ArbitrageSignal
from btc_model.core.backend.websocket_service import WebSocketService
from btc_model.manager.instance_manager import set_instance, register_instance

from btc_model.strategy.funding_rate_arbitrage.data_processor import DataProcessor
from btc_model.strategy.funding_rate_arbitrage.exchange_connector import ExchangeConnector
from btc_model.strategy.funding_rate_arbitrage.risk_manager import RiskManager
from btc_model.strategy.funding_rate_arbitrage.strategy_params import StrategyParams

from btc_model.strategy.funding_rate_arbitrage.trade.funding_rate_arbitrage_execute_manager import FundingRateArbitrageExecuteManager
from btc_model.strategy.funding_rate_arbitrage.trade.funding_rate_arbitrage_position_manager import FundingRateArbitragePositionManager


class FundingRateArbitrageStrategy:
    """
    跨交易所套利策略
    """
    def __init__(self,
                 exchange_id: str,
                 symbol_id: str,
                 spot_inst_id: str,
                 swap_inst_id: str,
                 exchange_connector: ExchangeConnector,
                 data_processor: DataProcessor,
                 position_manager: FundingRateArbitragePositionManager,
                 execution_manager: FundingRateArbitrageExecuteManager,
                 risk_manager: RiskManager,
                 market_data_service: MarketDataService,
                 strategy_params: StrategyParams,
                 ):
        """
        初始化策略
        
        Args:
            data_processor: DataProcessor instance.
            position_manager: PositionManager instance.
            execution_manager: ExecutionManager instance.
            risk_manager: RiskManager instance.
            config: Dictionary containing strategy parameters.
            context: 上下文       
        """
        self.exchange_id = exchange_id
        self.symbol_id = symbol_id
        self.spot_inst_id = spot_inst_id
        self.swap_inst_id = swap_inst_id

        self.exchange_connector = exchange_connector
        self.data_processor = data_processor
        self.position_manager = position_manager
        self.execution_manager: FundingRateArbitrageExecuteManager = execution_manager
        self.risk_manager = risk_manager
        self.market_data_service = market_data_service

        self.db_wrapper = DBWrapper().get_instance()

        # 从配置文件中获取策略参数
        self.strategy_params = strategy_params

        self.is_live = get_settings('trade')['live_mode']




      
        self._blacklist_symbols = set()
        # self._load_blacklist_symbols()

        # self.websocket_service: WebSocketService = self.service_manager.get_websocket_service()
        # 启动监控线程
        self.is_running = True
        # self.monitor_thread = threading.Thread(target=self._monitor_arbitrage_opportunities_loop, daemon=True)
        # self.monitor_thread.start()
        
        Logger.info("Strategy module initialized with configuration.")

    def _monitor_arbitrage_opportunities_loop(self):
        while True:
            self.evaluate_opportunities()
            time.sleep(10) # Evaluate every 10 seconds

    def evaluate_opportunities(self):
        """
        Evaluates market data and checks for open and close signals.
        This method should be called periodically in a separate loop or thread.
        """
        Logger.debug("Evaluating trading opportunities...")

        # 1. Check for open signals
        self.check_open_signal()

        # 2. Check for close signals (Close signals can also be triggered directly by RiskManager)
        self.check_close_signal()

        Logger.debug("Opportunity evaluation completed.")

    def check_open_signal(self):
        """
        检查是否有开仓信号，满足条件后、执行交易前才记录信号
        """
        # 获取现货和永续合约的价格数据
        spot_bbo = self.market_data_service.get_bbo(self.exchange_id, self.spot_inst_id)
        if spot_bbo is None or spot_bbo['timestamp'] == 0:
            return False
        
        swap_bbo = self.market_data_service.get_bbo(self.exchange_id, self.swap_inst_id)
        if swap_bbo is None or swap_bbo['timestamp'] == 0:
            return False
        
        
        # 获取当前资金费率
        current_funding_rate = self.market_data_service.get_funding_rate(self.exchange_id, self.swap_inst_id)
        if current_funding_rate is None or current_funding_rate['timestamp'] == 0:
            Logger.warning(f"无法获取资金费率，跳过开仓检查")
            return False
        
        current_funding_rate = current_funding_rate['fundingRate']
        
        # 计算年化资金费率（假设每8小时一次，一年365天）
        funding_periods_per_year = 365 * 3  # 每天3次，一年365天
        annualized_funding_rate = current_funding_rate * funding_periods_per_year * 100  # 转换为百分比
        
        # 计算基差
        spot_ask = spot_bbo['ask_price']
        swap_bid = swap_bbo['bid_price']
        basis = swap_bid - spot_ask
        basis_ratio = (basis / spot_ask) * 100  # 转换为百分比
        
        # 根据策略条件判断是否开仓
        if annualized_funding_rate > self.strategy_params.common_params.min_annualized_funding_rate and \
            basis_ratio < self.strategy_params.common_params.max_acceptable_basis:
            # 进行额外检查
            
            # 检查交易对是否在黑名单中
            if self.spot_inst_id in self._blacklist_symbols or self.swap_inst_id in self._blacklist_symbols:
                Logger.info(f"交易对 {self.spot_inst_id}/{self.swap_inst_id} 在黑名单中，不开仓")
                return False
            
            # 检查是否已有该交易对的头寸
            existing_position = self.position_manager.get_position_by_symbols(self.spot_inst_id, self.swap_inst_id)
            if existing_position:
                Logger.info(f"已存在交易对 {self.spot_inst_id}/{self.swap_inst_id} 的头寸，不重复开仓")
                return False
            
            # 计算头寸大小
            available_capital = self.get_available_capital()
            position_size = self.calculate_position_size(available_capital, spot_ask)
            
            if position_size <= 0:
                Logger.info("计算的头寸大小为零或负数，不开仓")
                return False
            
            active_position_count = self.position_manager.get_active_position_by_symbol_id(symbol_id=self.symbol_id)
            if active_position_count >= self.strategy_params.common_params.max_open_positions:
                Logger.info(f"当前交易对 {self.symbol_id} 已有 {active_position_count} 个活跃持仓，不开仓")
                return False
                
            # 满足开仓条件，准备信号数据
            exchange_id = self.exchange_id
            pair_parts = self.spot_inst_id.split('/')
            base_currency = pair_parts[0]
            quote_currency = pair_parts[1]
            
            now = datetime.now()
           
            sql = """
            INSERT INTO funding_rate_arbitrage_signal (
                signal_date, 
                signal_time, 
                exchange_id, 
                base_currency, 
                quote_currency, 
                spot_inst_id, 
                swap_inst_id, 
                current_funding_rate, 
                annualized_funding_rate, 
                spot_bid, 
                spot_bid_volume, 
                spot_ask, 
                spot_ask_volume, 
                swap_bid, 
                swap_bid_volume, 
                swap_ask, 
                swap_ask_volume, 
                basis, 
                basis_ratio, 
                status, 
                remark
                )VALUES (
                :signal_date, 
                :signal_time, 
                :exchange_id, 
                :base_currency, 
                :quote_currency, 
                :spot_inst_id, 
                :swap_inst_id, 
                :current_funding_rate, 
                :annualized_funding_rate, 
                :spot_bid, 
                :spot_bid_volume, 
                :spot_ask, 
                :spot_ask_volume, 
                :swap_bid, 
                :swap_bid_volume, 
                :swap_ask, 
                :swap_ask_volume, 
                :basis, 
                :basis_ratio, 
                :status, 
                :remark
                )
            """
            
            params = {
                'signal_date': now.date(),
                'signal_time': now.time(),
                'exchange_id': exchange_id,
                'base_currency': base_currency,
                'quote_currency': quote_currency,
                'spot_inst_id': self.spot_inst_id,
                'swap_inst_id': self.swap_inst_id,
                'current_funding_rate': current_funding_rate,
                'annualized_funding_rate': annualized_funding_rate,
                'spot_bid': spot_bbo['bid_price'],
                'spot_bid_volume': spot_bbo['bid_volume'],
                'spot_ask': spot_bbo['ask_price'],
                'spot_ask_volume': spot_bbo['ask_volume'],
                'swap_bid': swap_bbo['bid_price'],
                'swap_bid_volume': swap_bbo['bid_volume'],
                'swap_ask': swap_bbo['ask_price'],
                'swap_ask_volume': swap_bbo['ask_volume'],
                'basis': basis,
                'basis_ratio': basis_ratio,
                'status': 'triggered',
                'remark': '开仓信号已触发交易'
            }

            # 写入信号到数据库
            signal_id = self.db_wrapper.execute_sql(sql, params)
            if signal_id is None:
                Logger.warning(f"记录开仓信号失败，跳过开仓")
                return False
            
            symbol_id = f"{self.spot_inst_id}/{self.swap_inst_id}"
            # self.trigger_open_position(signal_id, params)
            self.execution_manager.create_arbitrage_position(
                symbol_id, 
                position_size
                )
            
            Logger.info(f"记录开仓信号 ID: {signal_id}, 交易对: {self.spot_inst_id}/{self.swap_inst_id}")
            
            # 执行交易逻辑
            #self.execute_open_position(self.spot_inst_id, self.swap_inst_id, spot_ask, swap_bid, position_size)
            return True
        
        return False
    
    def trigger_open_position(self, signal_id: int, signal_data: dict):
        """
        触发开仓交易
        """
        self.execution_manager.trigger_open_position(signal_id, signal_data)

    def check_close_signal(self):
        """检查是否有平仓信号，满足条件后、执行交易前才记录信号"""
        # 获取现货和永续合约的价格数据
        spot_bbo = self.market_data_service.get_bbo(self.exchange_id, self.spot_inst_id)
        if spot_bbo is None or spot_bbo['timestamp'] == 0:  
            return False
        
        swap_bbo = self.market_data_service.get_bbo(self.exchange_id, self.swap_inst_id)
        if swap_bbo is None or swap_bbo['timestamp'] == 0:
            return False
        
        # 获取当前资金费率
        current_funding_rate = self.market_data_service.get_funding_rate(self.exchange_id, self.swap_inst_id)
        if current_funding_rate is None or current_funding_rate['timestamp'] == 0:
            Logger.warning(f"无法获取资金费率，跳过平仓检查")
            return False
        
        current_funding_rate = current_funding_rate['fundingRate']
        
        # 计算年化资金费率
        funding_periods_per_year = 365 * 3
        annualized_funding_rate = current_funding_rate * funding_periods_per_year * 100
        
        # 计算基差
        spot_bid = spot_bbo['bid_price']
        swap_ask = swap_bbo['ask_price']
        basis = swap_ask - spot_bid
        basis_ratio = (basis / spot_bid) * 100
        
        position = self.position_manager.get_position_by_symbols(self.spot_inst_id, self.swap_inst_id)

        if position is None:
            Logger.warning(f"无法获取头寸信息，跳过平仓检查")
            return False
        
        # # 计算持仓时间
        # position_duration = (datetime.now() - position.entry_time).total_seconds() / 3600  # 持仓时间(小时)
        
        # 根据策略条件判断是否平仓
        if annualized_funding_rate < self.strategy_params.common_params.min_annualized_funding_rate or \
            basis_ratio > self.strategy_params.common_params.max_acceptable_basis:
            
            # 检查是否可以平仓
            if not self.position_manager.can_close_position(position.position_id):
                Logger.info(f"头寸 {position.position_id} 当前不可平仓")
                return False
                
            # 检查是否有足够的流动性进行平仓
            if spot_bid <= 0 or swap_ask <= 0:
                Logger.warning(f"价格异常，不能平仓：spot_bid={spot_bid}, swap_ask={swap_ask}")
                return False
            
            # 满足平仓条件，准备信号数据
            exchange_id = self.exchange_id
            pair_parts = self.spot_inst_id.split('/')
            base_currency = pair_parts[0]
            quote_currency = pair_parts[1]
            
            close_reason = []
            # if position_duration >= self.strategy_params.common_params.min_hold_hours:
            #     close_reason.append(f"持仓时间已达到最小持仓时间")
            if annualized_funding_rate < self.strategy_params.common_params.min_annualized_funding_rate:
                close_reason.append(f"资金费率低于平仓阈值")
            if basis_ratio > self.strategy_params.common_params.max_acceptable_basis:
                close_reason.append(f"基差比例高于平仓阈值")
            
            close_reason_str = ", ".join(close_reason)
            
            now = datetime.now()
            signal_data = {
                'signal_date': now.date(),
                'signal_time': now.time(),
                'exchange_id': exchange_id,
                'base_currency': base_currency,
                'quote_currency': quote_currency,
                'spot_inst_id': self.spot_inst_id,
                'swap_inst_id': self.swap_inst_id,
                'current_funding_rate': current_funding_rate,
                'annualized_funding_rate': annualized_funding_rate,
                'spot_bid': spot_bid,
                'spot_bid_volume': spot_bbo['bid_volume'],
                'spot_ask': spot_bbo['ask_price'],
                'spot_ask_volume': spot_bbo['ask_volume'],
                'swap_bid': swap_bbo['bid_price'],
                'swap_bid_volume': swap_bbo['bid_volume'],
                'swap_ask': swap_bbo['ask_price'],
                'swap_ask_volume': swap_bbo['ask_volume'],
                'basis': basis,
                'basis_ratio': basis_ratio,
                'status': 'triggered',
                'remark': f'平仓信号已触发, 持仓时间: {position_duration:.2f}小时, 原因: {close_reason_str}'
            }
            
            # 写入信号到数据库
            #signal_id = self.db_connector.insert_record('funding_rate_arbitrage_signal', signal_data)
            
            #Logger.info(f"记录平仓信号 ID: {signal_id}, 交易对: {self.spot_inst_id}/{self.swap_inst_id}, 原因: {close_reason_str}")
            
            # 执行平仓逻辑
            #self.execute_close_position(self.spot_inst_id, self.swap_inst_id, spot_bid, swap_ask)
            return True
        
        return False

    # This method can be called directly by RiskManager to force a close
    def trigger_close_by_risk_manager(self, position_id: str, reason: str):
        """
        Called by RiskManager to force the closure of a specific position.

        Args:
            position_id: The ID of the position to close.
            reason: The reason for triggering the close (e.g., 'liquidation_risk', 'basis_stop_loss').
        """
        Logger.warning(f"Close instruction received from RiskManager for position {position_id}. Reason: {reason}")
        self._trigger_close(position_id, reason=f"risk_triggered:{reason}")


    def _trigger_close(self, position_id: str, reason: str):
        """
        Internal method: Generates a close instruction and sends it to ExecutionManager.
        Ensures that close instructions are not sent repeatedly for a position already closing.
        """
        position = self.position_manager.get_position(position_id)
        if position is None:
             Logger.warning(f"Attempted to trigger close for non-existent position: {position_id}")
             return

        # Check if the position is already in a state of being closed or closed
        if position.get('status') in ['CLOSING', 'CLOSED', 'ERROR']:
             Logger.info(f"Position {position_id} is already in status {position.get('status')}. Skipping close trigger.")
             return

        Logger.info(f"Sending close instruction for position {position_id}. Reason: {reason}")

        # Update internal state to CLOSING to prevent duplicate triggers
        position['status'] = 'CLOSING' # Assuming position object is mutable or update method is called
        # TODO: PositionManager needs a method to update status and save state
        # self.pos_manager.update_position_status(position_id, 'CLOSING')
        # self.pos_manager.save_positions() # Save state after status change

        # Generate the close instruction
        close_instruction = {
            'position_id': position_id,
            'inst_id': position.get('inst_id'), # Trading pair ID from the position object
            # TODO: Add more instruction details, like order type (market/limit)
        }
        self.execution_manager.handle_close_instruction(close_instruction) # Notify ExecutionManager to execute

    def get_available_capital(self) -> float:
        """
        获取当前可用的资金量
        
        Returns:
            float: 可用资金（以USDT计价）
        """
        try:
            # 从交易所获取账户信息
            account_info = self.exchange_connector.get_account_info()
            if not account_info:
                Logger.warning("无法获取账户信息，使用默认可用资金")
                return self.config.get('common_params', {}).get('default_available_capital', 1000.0)
            
            # 获取可用权益（USDT）
            available_equity = account_info.get('available_equity', 0)
            
            # 考虑风险管理，通常只使用账户资金的一部分
            risk_ratio = self.strategy_params.risk_control_params.margin_ratio_warning
            available_capital = available_equity * risk_ratio
            
            # 记录可用资金
            Logger.info(f"当前可用资金: {available_capital} USDT (总可用权益: {available_equity} USDT, 使用比例: {risk_ratio*100}%)")
            
            return available_capital
            
        except Exception as e:
            Logger.error(f"获取可用资金时出错: {e}")
            # 返回默认值
            return self.strategy_params.common_params.min_position_size_usd

    def calculate_position_size(self, available_capital: float, current_price: float) -> float:
        """
        计算合适的头寸大小
        
        Args:
            available_capital: 可用资金（USDT）
            current_price: 当前现货价格
            
        Returns:
            float: 头寸大小（以交易对基础货币计价，如BTC）
        """
        try:
            # 获取配置参数
            min_position_size_usd = self.strategy_params.common_params.min_position_size_usd
            max_position_size_usd = self.strategy_params.common_params.max_position_size_usd
            max_concurrent_positions = self.strategy_params.common_params.max_concurrent_positions
            
            # 当前活跃头寸数量
            active_positions_count = self.position_manager.get_active_positions_count()
            
            # 如果已达到最大头寸数量，则不开新仓
            if active_positions_count >= max_concurrent_positions:
                Logger.warning(f"已达到最大头寸数量 ({active_positions_count}/{max_concurrent_positions})，不开新仓")
                return 0.0
            
            # 考虑当前活跃头寸数，计算此次可用资金
            remaining_positions = max_concurrent_positions - active_positions_count
            per_position_capital = available_capital / max(1, remaining_positions)
            
            # 确保不超过最大单笔头寸限制
            position_size_usd = min(per_position_capital, max_position_size_usd)
            
            # 不低于最小头寸限制
            if position_size_usd < min_position_size_usd:
                Logger.warning(f"计算的头寸大小 ({position_size_usd} USDT) 低于最小要求 ({min_position_size_usd} USDT)，不开仓")
                return 0.0
            
            # 转换为币种数量
            position_size_coin = position_size_usd / current_price if current_price > 0 else 0.0
            
            # 记录计算结果
            Logger.info(f"计算头寸大小: {position_size_coin} (约 {position_size_usd} USDT)")
            
            return position_size_coin
            
        except Exception as e:
            Logger.error(f"计算头寸大小时出错: {e}")
            return 0.0

    def check_and_execute_new_position(self, trading_pair_info: Dict):
        """
        检查是否应该为指定交易对开仓并执行
        
        Args:
            trading_pair_info: 交易对信息字典，包含交易对ID、价格等
        """
        try:
            spot_symbol = trading_pair_info.get('spot_inst_id')
            swap_symbol = trading_pair_info.get('swap_inst_id')
            exchange_id = trading_pair_info.get('exchange_id')
            
            # 获取当前市场数据
            spot_ticker = self.exchange_connector.fetch_ticker(spot_symbol)
            swap_ticker = self.exchange_connector.fetch_ticker(swap_symbol)
            funding_rate = self.exchange_connector.fetch_funding_rate(swap_symbol)
            
            if not spot_ticker or not swap_ticker or not funding_rate:
                Logger.warning(f"无法获取完整市场数据，取消开仓: {spot_symbol}/{swap_symbol}")
                return
                
            # 获取关键数据
            spot_price = spot_ticker.get('last', 0)
            swap_price = swap_ticker.get('last', 0)
            current_funding_rate = float(funding_rate.get('fundingRate', 0)) 
            next_funding_rate = float(funding_rate.get('nextFundingRate', 0) or 0)
            
            # 计算年化资金费率
            funding_periods_per_year = 1095  # 通常是每8小时一次，一年约1095次
            annualized_funding_rate = next_funding_rate * funding_periods_per_year * 100  # 转换为百分比
            
            # 计算基差
            basis = (swap_price - spot_price) / spot_price
            
            # 检查开仓条件
            min_rate = self.config.get('common_params', {}).get('min_annualized_funding_rate', 15.0)
            min_basis = self.config.get('common_params', {}).get('min_basis_for_open', 0.0)
            max_basis = self.config.get('common_params', {}).get('max_acceptable_basis', 0.002)
            
            # 判断是否满足开仓条件
            if annualized_funding_rate < min_rate:
                Logger.info(f"年化资金费率 ({annualized_funding_rate:.2f}%) 低于最小要求 ({min_rate:.2f}%)，不开仓")
                return
                
            if basis < min_basis:
                Logger.info(f"基差 ({basis:.4f}) 低于最小要求 ({min_basis:.4f})，不开仓")
                return
                
            if basis > max_basis:
                Logger.info(f"基差 ({basis:.4f}) 超过最大可接受值 ({max_basis:.4f})，不开仓")
                return
            
            # 获取可用资金
            available_capital = self.get_available_capital()
            
            # 计算头寸大小
            position_size_coin = self.calculate_position_size(available_capital, spot_price)
            
            if position_size_coin <= 0:
                return
                
            # 检查是否已有该交易对的头寸
            existing_position = self.position_manager.get_position_by_symbols(spot_symbol, swap_symbol)
            if existing_position:
                Logger.info(f"已存在交易对 {spot_symbol}/{swap_symbol} 的头寸，不重复开仓")
                return
                
            # 创建新头寸
            new_position = self.position_manager.create_funding_rate_position(
                exchange_id=exchange_id,
                spot_symbol=spot_symbol,
                swap_symbol=swap_symbol,
                spot_size=position_size_coin,
                swap_size=-position_size_coin,  # 合约方向相反
                spot_price=spot_price,
                swap_price=swap_price,
                basis=basis
            )
            
            if new_position:
                # 生成开仓指令
                open_instruction = {
                    'position_id': new_position.position_id,
                    'exchange_id': exchange_id,
                    'spot_symbol': spot_symbol,
                    'swap_symbol': swap_symbol,
                    'spot_size': position_size_coin,
                    'swap_size': -position_size_coin,  # 合约方向相反
                    'action': 'open'
                }
                
                # 发送给执行管理器
                Logger.info(f"发送开仓指令: {new_position.position_id}")
                self.execution_manager.handle_open_instruction(open_instruction)
                
                # 广播信号
                self.whitelist_manager.broadcast_funding_rate_signal(
                    trading_pair_info,
                    {
                        'funding_rate': current_funding_rate,
                        'next_funding_rate': next_funding_rate,
                        'annualized_funding_rate': annualized_funding_rate,
                        'basis': basis,
                        'basis_pct': basis * 100,
                        'spot_price': spot_price,
                        'swap_price': swap_price,
                        'next_funding_time': funding_rate.get('nextFundingTime', ''),
                    }
                )
            
        except Exception as e:
            Logger.error(f"检查和执行新头寸时出错: {e}")

def run():
    from exchange_connector import ExchangeConnector
    from btc_model.strategy.funding_rate_arbitrage.trade.funding_rate_arbitrage_position_manager import PositionManager
    from btc_model.strategy.funding_rate_arbitrage.execution_manager______ import ExecutionManager
    from risk_manager import RiskManager
    from data_processor import DataProcessor
    import threading
    import time


    # Assume other modules are initialized
    # api_connector = OkxAPIConnector(...)
    # pos_manager = PositionManager(...)
    # exec_manager = ExecutionManager(...)
    # risk_manager = RiskManager(...)
    # data_processor = DataProcessor(...)

    # Strategy configuration
    # strategy_config = {
    #     'min_annualized_funding_rate': 20.0,
    #     'max_acceptable_basis': 0.003,
    #     'min_basis_for_open': 0.0001,
    #     'min_position_size_usd': 5000.0,
    #     'max_concurrent_positions': 2,
    #     'funding_rate_close_threshold': 8.0,
    #     'data_staleness_threshold_sec': 90
    # }

    # Initialize the strategy
    # strategy = Strategy(data_processor, pos_manager, exec_manager, risk_manager, strategy_config)

    # # Example of running the strategy evaluation in a loop (in a separate thread)
    # def strategy_evaluation_loop(strategy_instance):
    #      while True:
    #           strategy_instance.evaluate_opportunities()
    #           time.sleep(10) # Evaluate every 10 seconds

    # # Start the strategy evaluation thread
    # strategy_thread = threading.Thread(target=strategy_evaluation_loop, args=(strategy,))
    # strategy_thread.daemon = True # Allow main program to exit even if this thread is running
    # strategy_thread.start()

    # # In your main program loop, you would also run data fetching, risk monitoring, and order monitoring
    # # while True:
    # #      # Data fetching loop (e.g., data_processor.update_market_data())
    # #      # Risk monitoring loop (e.g., risk_manager.monitor_risks())
    # #      # Order monitoring loop (e.g., exec_manager.monitor_orders())
    # #      time.sleep(1) # Main loop sleep