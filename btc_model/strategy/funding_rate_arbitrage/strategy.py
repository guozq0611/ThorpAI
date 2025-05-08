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
from btc_model.strategy.funding_rate_arbitrage.position_manager import PositionManager
from btc_model.strategy.funding_rate_arbitrage.execution_manager import ExecutionManager
from btc_model.strategy.funding_rate_arbitrage.risk_manager import RiskManager
from btc_model.strategy.funding_rate_arbitrage.strategy_params import StrategyParams

class FundingRateArbitrageStrategy:
    """
    跨交易所套利策略
    """
    def __init__(self,
                 data_processor: DataProcessor,
                 position_manager: PositionManager,
                 execution_manager: ExecutionManager,
                 risk_manager: RiskManager,
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
        self.data_processor = data_processor
        self.position_manager = position_manager
        self.execution_manager = execution_manager
        self.risk_manager = risk_manager

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
        Checks if conditions are met to open a new arbitrage position.
        """
        # Get the latest market metrics
        latest_metrics = self.data_processor.get_latest_metrics()
        current_basis = latest_metrics.get('basis')
        next_annualized_funding_rate = latest_metrics.get('next_annualized_funding_rate')
        last_data_update_time = latest_metrics.get('last_update_time', 0)

        # Get current position information
        active_positions = self.position_manager.get_all_positions()

        # Check basic data availability and freshness
        if current_basis is None:
            Logger.debug("Open signal check skipped: current_basis not available.")
            return

        # if time.time() - last_data_update_time > self.data_staleness_threshold_sec:
        #      Logger.warning(f"Open signal check skipped: Market data is stale (last updated {time.time() - last_data_update_time:.2f}s ago).")
        #      self.risk_manager.trigger_alert("Data Stale Warning", f"Market data for strategy is stale ({time.time() - last_data_update_time:.2f}s old).", level='warning')
        #      return

        # 1. Check if funding rate meets requirement
        # if next_annualized_funding_rate < self.min_annualized_funding_rate:
        #     Logger.debug(f"Open signal check skipped: Next funding rate ({next_annualized_funding_rate:.2f}%) below minimum requirement ({self.min_annualized_funding_rate:.2f}%).")
        #     return

        # 2. Check if basis is within acceptable range
        if current_basis < self.strategy_params.common_params.min_basis_for_open or \
           current_basis > self.strategy_params.common_params.max_acceptable_basis:
             Logger.debug(f"Open signal check skipped: Basis ({current_basis:.8f}) outside acceptable range ({self.strategy_params.common_params.min_basis_for_open} to {self.strategy_params.common_params.max_acceptable_basis}).")
             return

        # 3. Check if maximum concurrent positions reached
        if len(active_positions) >= self.strategy_params.common_params.max_concurrent_positions:
            Logger.debug(f"Open signal check skipped: Max concurrent positions ({self.strategy_params.common_params.max_concurrent_positions}) reached (currently {len(active_positions)}).")
            return

        # 4. Check if an active position already exists for this trading pair
        # Requires PositionManager to have a method to check this
        # if self.pos_manager.has_active_position_for_pair(self.data_proc.spot_inst_id):
        #      Logger.debug(f"Open signal check skipped: Active position already exists for {self.data_proc.spot_inst_id}.")
        #      return

        # 5. Check if there is enough available capital
        # Requires RiskManager or another module to provide available capital information
        # available_capital = self.risk_manager.get_available_capital() # Example
        # if available_capital is None or available_capital < self.min_position_size_usd:
        #      Logger.warning(f"Open signal check skipped: Insufficient capital ({available_capital}) for minimum size ({self.min_position_size_usd} USD).")
        #      self.risk_manager.trigger_alert("Insufficient Capital", f"Available capital ({available_capital}) below min position size ({self.min_position_size_usd} USD).", level='warning')
        #      return

        # 6. Check overall risk status (e.g., if overall margin is healthy)
        # if not self.risk_manager.is_overall_margin_healthy():
        #      Logger.warning("Open signal check skipped: Overall risk status is not healthy.")
        #      return

        # If all conditions are met, trigger the open signal
        # Logger.info(f"Open signal triggered for {self.data_proc.spot_inst_id}! Next Funding: {next_annualized_funding_rate:.2f}%, Basis: {current_basis:.8f}.")
        Logger.info(f"Open signal triggered for {self.data_proc.spot_inst_id}, Basis: {current_basis:.8f}.")

        # Calculate position size (based on available capital, min size, etc.)
        # This calculation needs to be precise, considering leverage, contract multiplier, etc.
        # It might require more info from DataProcessor or a separate calculation utility
        # Example calculation placeholder:
        # position_size_coin = self.calculate_position_size(available_capital, self.data_proc.get_latest_spot_price()) # TODO: Implement size calculation

        # if position_size_coin > 0:
        #     # Create a new position object (status 'OPENING') and generate a unique position_id
        #     new_position = self.pos_manager.create_new_position(self.data_proc.spot_inst_id)
        #
        #     # Generate the open instruction
        #     open_instruction = {
        #         'position_id': new_position['position_id'], # Use the ID from the created position
        #         'inst_id': self.data_proc.spot_inst_id, # Trading pair ID
        #         'size_coin': position_size_coin, # Size in base currency (e.g., BTC)
        #         # TODO: Add more instruction details, like order type (market/limit), price for limit orders etc.
        #     }
        #     Logger.info(f"Sending open instruction for position {new_position['position_id']}")
        #     self.exec_manager.handle_open_instruction(open_instruction) # Notify ExecutionManager to execute
        # else:
        #      Logger.warning("Calculated position size is zero. Open instruction not sent.")

        # For simulation purposes, let's just log the signal
        Logger.info("Simulating sending open instruction (actual execution commented out).")


    def check_close_signal(self):
        """
        Checks if conditions are met to close existing arbitrage positions.
        """
        active_positions = self.pos_manager.get_all_positions()

        if not active_positions:
            Logger.debug("Close signal check skipped: No active positions.")
            return

        latest_metrics = self.data_proc.get_latest_metrics()
        current_annualized_funding_rate = latest_metrics.get('annualized_funding_rate')
        last_data_update_time = latest_metrics.get('last_update_time', 0)

        # Ensure funding rate data is fresh
        if time.time() - last_data_update_time > self.data_staleness_threshold_sec:
             Logger.warning(f"Close signal check skipped: Funding rate data is stale ({time.time() - last_data_update_time:.2f}s old).")
             # RiskManager should already be alerting on stale data, but can add here too
             return

        # Iterate through all active positions to check for closing conditions
        for position in active_positions:
             # Only check positions that are fully opened
             if position.get('status') != 'OPENED':
                  Logger.debug(f"Skipping close check for position {position.get('position_id')}: Status is {position.get('status')}.")
                  continue

             position_id = position.get('position_id')

             # 1. Check if current funding rate is below the close threshold (Core close condition)
             # We use the 'current' funding rate here, not 'next predicted', as we care about current earnings
             if current_annualized_funding_rate is not None and current_annualized_funding_rate < self.funding_rate_close_threshold:
                  Logger.info(f"Close signal triggered for position {position_id}: Current funding rate ({current_annualized_funding_rate:.2f}%) below threshold ({self.funding_rate_close_threshold:.2f}%).")
                  self._trigger_close(position_id, reason="funding_rate_low") # Trigger close

             # 2. Check if profit target is reached (Optional condition)
             # Requires PositionManager to calculate current total PnL
             # current_total_pnl = self.pos_manager.calculate_total_pnl(position_id) # Example
             # profit_target_reached = False # TODO: Implement logic based on config
             # if profit_target_reached:
             #      Logger.info(f"Close signal triggered for position {position_id}: Profit target reached.")
             #      self._trigger_close(position_id, reason="profit_target")

             # 3. Check if maximum holding time is reached (Optional condition)
             # Requires PositionManager to store open time
             # max_hold_time_reached = False # TODO: Implement logic based on config and position['open_time']
             # if max_hold_time_reached:
             #      Logger.info(f"Close signal triggered for position {position_id}: Max hold time reached.")
             #      self._trigger_close(position_id, reason="max_hold_time")

             # TODO: Add other potential close conditions, e.g.:
             # - Approaching a major funding settlement time window (if you want to avoid potentially paying negative rates)
             # - Extreme market volatility or upcoming significant events

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
        position = self.pos_manager.get_position(position_id)
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
        self.exec_manager.handle_close_instruction(close_instruction) # Notify ExecutionManager to execute

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
            risk_ratio = self.config.get('risk_control_params', {}).get('capital_usage_ratio', 0.5)
            available_capital = available_equity * risk_ratio
            
            # 记录可用资金
            Logger.info(f"当前可用资金: {available_capital} USDT (总可用权益: {available_equity} USDT, 使用比例: {risk_ratio*100}%)")
            
            return available_capital
            
        except Exception as e:
            Logger.error(f"获取可用资金时出错: {e}")
            # 返回默认值
            return self.config.get('common_params', {}).get('default_available_capital', 1000.0)

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
            min_position_size_usd = self.config.get('common_params', {}).get('min_position_size_usd', 100.0)
            max_position_size_usd = self.config.get('risk_control_params', {}).get('max_single_position_size_usd', 1000.0)
            max_concurrent_positions = self.config.get('common_params', {}).get('max_concurrent_positions', 5)
            
            # 当前活跃头寸数量
            active_positions_count = self.pos_manager.get_active_positions_count()
            
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
            existing_position = self.pos_manager.get_position_by_symbols(spot_symbol, swap_symbol)
            if existing_position:
                Logger.info(f"已存在交易对 {spot_symbol}/{swap_symbol} 的头寸，不重复开仓")
                return
                
            # 创建新头寸
            new_position = self.pos_manager.create_funding_rate_position(
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
                self.exec_manager.handle_open_instruction(open_instruction)
                
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
    from position_manager import PositionManager
    from execution_manager import ExecutionManager
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