import threading
import time

from btc_model.market.market_data_service import MarketDataService
from btc_model.manager.service_manager import service_manager 
from btc_model.core.wrapper.db_wrapper import DBWrapper

from exchange_connector import ExchangeConnector
from position_manager import PositionManager
from execution_manager import ExecutionManager
from risk_manager import RiskManager
from data_processor import DataProcessor
from whitelist_manager import FundingRateWhitelistManager
from strategy_params import StrategyParams
from strategy import FundingRateArbitrageStrategy

class StrategyRunner:
    def __init__(self):
        # 从配置文件中获取策略参数
        self.strategy_params = StrategyParams.from_settings()

        # market_data = MarketDataService()
    
        # # 创建交易所实例
        # market_data.create_exchanges(['okx'])
        # market_data.set_perpetual_exchanges(['okx'])

        self.exchange_connector = ExchangeConnector('okx')

        self.data_processor = DataProcessor(
            exchange_connector=self.exchange_connector,
            spot_inst_id='BTC-USDT',
            swap_inst_id='BTC-USDT-SWAP'
            )
        
        self.position_manager = PositionManager(
            exchange_connector=self.exchange_connector,
            db_wrapper=DBWrapper.get_instance()
            )
        
        
        self.execution_manager = ExecutionManager(
            exchange_connector=self.exchange_connector, 
            position_manager=self.position_manager, 
            strategy_params=self.strategy_params
            )
        
        self.risk_manager = RiskManager(
            exchange_connector=self.exchange_connector,
            data_processor=self.data_processor,
            position_manager=self.position_manager,
            execution_manager=self.execution_manager,
            risk_control_params=self.strategy_params.risk_control_params
            )
        
        self.whitelist_manager = FundingRateWhitelistManager(
            db_wrapper=DBWrapper.get_instance(),
            websocket_service=service_manager.get_websocket_service()
            )
        
        self.strategy = FundingRateArbitrageStrategy(
            data_processor=self.data_processor,
            position_manager=self.position_manager,
            execution_manager=self.execution_manager,
            risk_manager=self.risk_manager,
            strategy_params=self.strategy_params
            )

    def run_syncronized(self):
        """
        同步运行策略, 用于测试各组件是否正常工作
        """   
        while True:
            self.data_processor.update_market_data()
            self.risk_manager.monitor_risks()
            self.strategy.evaluate_opportunities()
            #self.execution_manager.execute_trades()
            print('sleep 1 sec')
            time.sleep(1)

if __name__ == "__main__":
    strategy_runner = StrategyRunner()
    strategy_runner.run_syncronized()