import threading
import time

from btc_model.market.market_data_service import MarketDataService
from btc_model.manager.service_manager import service_manager 
from btc_model.core.wrapper.db_wrapper import DBWrapper
from btc_model.core.util.log_util import Logger
from btc_model.core.backend.websocket_service import WebSocketService

from exchange_connector import ExchangeConnector
from risk_manager import RiskManager
from data_processor import DataProcessor
from whitelist_manager import FundingRateWhitelistManager
from strategy_params import StrategyParams
from strategy import FundingRateArbitrageStrategy

from trade.funding_rate_arbitrage_execute_manager import FundingRateArbitrageExecuteManager
from trade.funding_rate_arbitrage_position_manager import FundingRateArbitragePositionManager


class StrategyRunner:
    def __init__(self,
                 market_data_service: MarketDataService
                 ):
        self.market_data_service = market_data_service

        # 从配置文件中获取策略参数
        self.strategy_params = StrategyParams.from_settings()

        # market_data = MarketDataService()
    
        # # 创建交易所实例
        # market_data.create_exchanges(['okx'])
        # market_data.set_perpetual_exchanges(['okx'])

        self.exchange_connector = ExchangeConnector('okx')


        self.position_manager = FundingRateArbitragePositionManager(
            exchange_connector=self.exchange_connector,
            db_wrapper=DBWrapper.get_instance()
            )
        
             
        self.whitelist_manager = FundingRateWhitelistManager(
            db_wrapper=DBWrapper.get_instance(),
            websocket_service=service_manager.get_websocket_service()
            )
        self.whitelist_manager.load_whitelist()
        self.white_list = self.whitelist_manager.get_whitelist()
        
        self.subscribe_market_data()

        # 启动市场数据订阅
        self.market_data_service.start()
        self.service_manager = service_manager

        self.execution_manager = FundingRateArbitrageExecuteManager(
            strategy_params=self.strategy_params,
            exchange=self.exchange_connector.exchange,
            market_data_service=self.market_data_service,
            position_manager=self.position_manager,
            service_manager=service_manager
            )
        
        self.websocket_service: WebSocketService = self.service_manager.get_websocket_service()

        spot_symbols = self.market_data_service.get_spot_symbols('okx')
        swap_symbols = self.market_data_service.get_swap_symbols('okx')
  
        self.strategy_list = []
        for white_list in self.white_list:
            spot_inst_id = white_list['spot_inst_id']
            swap_inst_id = white_list['swap_inst_id']
            swap_contract_size = self.exchange_connector.exchange.markets[swap_inst_id].get('contractSize', 1)

            if spot_inst_id not in spot_symbols or swap_inst_id not in swap_symbols:
                Logger.warning(f"币种 {spot_inst_id} 或 {swap_inst_id} 不在当前交易所，跳过策略初始化")
                continue

            self.data_processor = DataProcessor(
                exchange_connector=self.exchange_connector,
                spot_inst_id=spot_inst_id,
                swap_inst_id=swap_inst_id
            )
        
            self.risk_manager = RiskManager(
                exchange_connector=self.exchange_connector,
                data_processor=self.data_processor,
                position_manager=self.position_manager,
                risk_control_params=self.strategy_params.risk_control_params
            )

            strategy = FundingRateArbitrageStrategy(
                exchange_id='okx',
                symbol_id=spot_inst_id,
                spot_inst_id=spot_inst_id,
                swap_inst_id=swap_inst_id,
                swap_contract_size=swap_contract_size,
                exchange_connector=self.exchange_connector,
                data_processor=self.data_processor,
                position_manager=self.position_manager,
                execution_manager=self.execution_manager,
                risk_manager=self.risk_manager,
                market_data_service=self.market_data_service,
                strategy_params=self.strategy_params
            )
            self.strategy_list.append(strategy)
        
    def subscribe_market_data(self):
        """
        订阅交易对的行情数据
        """
        spot_symbols_to_watch = set()
        swap_symbols_to_watch = set()
        # 收集所有需要订阅的交易对
        for pair in self.white_list:
            spot_symbol = pair['spot_inst_id']
            spot_symbols_to_watch.add(spot_symbol)
            
            # 添加合约交易对
            swap_symbol = pair['swap_inst_id']
            swap_symbols_to_watch.add(swap_symbol)

 
        for symbol in spot_symbols_to_watch:
            #market_data_service.subscribe_orderbook(exchange_id, symbol)
            self.market_data_service.subscribe_bbo('okx', symbol)
            
        for symbol in swap_symbols_to_watch:
            #market_data_service.subscribe_orderbook(exchange_id, symbol)
            self.market_data_service.subscribe_bbo('okx', symbol)
            self.market_data_service.subscribe_funding_rate('okx', symbol)
        
        Logger.info(f"已订阅 {len(spot_symbols_to_watch)} 个现货交易对的市场数据")
        Logger.info(f"已订阅 {len(swap_symbols_to_watch)} 个合约交易对的市场数据")

            
    def run_syncronized(self):
        """
        同步运行策略, 用于测试各组件是否正常工作
        """   
        while True:
            self.data_processor.update_market_data()
            self.risk_manager.monitor_risks()
            for strategy in self.strategy_list: 
                strategy.evaluate_opportunities()
            #self.execution_manager.execute_trades()
            print('sleep 1 sec')
            time.sleep(1)

if __name__ == "__main__":
    from btc_model.manager.service_manager import service_manager 
    # 创建MarketDataService实例
    market_data_service = MarketDataService()
    
    # 创建交易所实例
    market_data_service.create_exchanges(['okx'])
    market_data_service.set_perpetual_exchanges(['okx'])


    strategy_runner = StrategyRunner(market_data_service)
    strategy_runner.run_syncronized()