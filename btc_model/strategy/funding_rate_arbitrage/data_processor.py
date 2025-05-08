import time
from typing import Dict, Optional
from btc_model.strategy.funding_rate_arbitrage.exchange_connector import ExchangeConnector
from btc_model.core.util.log_util import Logger

class DataProcessor:
    def __init__(self, 
                 exchange_connector: ExchangeConnector, 
                 spot_inst_id: str, 
                 swap_inst_id: str):
        """
        初始化数据处理器。

        Args:
            exchange_connector: ExchangeConnector 实例。
            spot_inst_id: 现货交易对 ID (例如 'BTC-USDT')。
            swap_inst_id: 永续合约交易对 ID (例如 'BTC-USDT-SWAP')。
        """
        self.exchange_connector = exchange_connector
        self.spot_inst_id = spot_inst_id
        self.swap_inst_id = swap_inst_id

        # 存储最新的原始数据
        self._latest_spot_ticker: Optional[Dict] = None
        self._latest_swap_ticker: Optional[Dict] = None
        self._latest_funding_info: Optional[Dict] = None

        # 存储最新的计算指标
        self._latest_basis: Optional[float] = None
        self._latest_annualized_funding_rate: Optional[float] = None
        self._latest_next_annualized_funding_rate: Optional[float] = None
        self._last_update_time: float = 0.0 # 记录上次更新时间戳

        # OKX 资金费率结算周期 (小时)
        self.FUNDING_INTERVAL_HOURS = 8
        self.FUNDING_PERIODS_PER_YEAR = 24 / self.FUNDING_INTERVAL_HOURS * 365 # 3 * 365 = 1095

        Logger.info(f"Data Processor initialized for {spot_inst_id} and {swap_inst_id}.")

    def get_latest_funding_rate(self):
        """
        获取最新的资金费率。
        """
        return self._latest_funding_info.get('fundingRate', None)

    def update_market_data(self):
        """
        从 API 连接器获取最新的市场数据并处理。
        应在一个独立的循环或线程中定期调用此方法。
        """
        Logger.debug(f"Updating market data for {self.spot_inst_id}/{self.swap_inst_id}...")
        try:
            # 获取最新的 ticker 数据
            spot_ticker = self.exchange_connector.fetch_ticker(self.spot_inst_id)
            swap_ticker = self.exchange_connector.fetch_ticker(self.swap_inst_id)

            if spot_ticker and swap_ticker:
                self._latest_spot_ticker = spot_ticker
                self._latest_swap_ticker = swap_ticker
                self._calculate_basis() # 成功获取行情后计算基差
            else:
                Logger.warning(f"Failed to get latest ticker data for {self.spot_inst_id} or {self.swap_inst_id}.")
                # TODO: 触发告警，数据源中断

            # 获取最新的资金费率信息
            funding_info = self.exchange_connector.fetch_funding_rate(self.swap_inst_id)

            if funding_info:
                self._latest_funding_info = funding_info
                self._calculate_annualized_funding_rates() # 成功获取资金费率后计算年化费率
            else:
                 Logger.warning(f"Failed to get latest funding rate for {self.swap_inst_id}.")
                 # TODO: 触发告警，数据源中断


            self._last_update_time = time.time()
            Logger.debug(f"Market data update completed for {self.spot_inst_id}/{self.swap_inst_id}.")

        except Exception as e:
            Logger.error(f"Error updating market data: {e}")
            # TODO: 触发告警，数据处理过程中出现错误

    def _calculate_basis(self):
        """
        内部方法：计算实时基差。
        使用永续合约卖一价减去现货买一价（针对空永续+多现货策略）。
        """
        if self._latest_spot_ticker and self._latest_swap_ticker:
            try:
                # 确保获取到有效的买卖价格
                spot_bid = float(self._latest_spot_ticker.get('bid', 0))
                swap_ask = float(self._latest_swap_ticker.get('ask', 0))

                if spot_bid > 0: # 确保买价有效，避免除以零或基差异常
                     self._latest_basis = swap_ask - spot_bid
                     Logger.debug(f"Calculated Basis: {self._latest_basis:.8f} (Swap Ask: {swap_ask}, Spot Bid: {spot_bid})")
                else:
                     self._latest_basis = None
                     Logger.warning(f"Spot bid price is invalid ({spot_bid}), cannot calculate basis.")

            except (ValueError, TypeError) as e:
                 Logger.error(f"Error calculating basis from ticker data: {e}")
                 self._latest_basis = None # 计算失败则置空
                 # TODO: 触发告警

        else:
            self._latest_basis = None # 数据不全，无法计算
            Logger.debug("Not enough ticker data to calculate basis.")


    def _calculate_annualized_funding_rates(self):
        """
        内部方法：计算年化资金费率。
        """
        if self._latest_funding_info:
            try:
                current_rate = self._latest_funding_info.get('fundingRate', None)
                if current_rate:
                    # 计算当前年化资金费率
                    self._latest_annualized_funding_rate = current_rate * self.FUNDING_PERIODS_PER_YEAR * 100 if current_rate is not None else 0 # 乘以100转换为百分比
                    Logger.debug(f"Calculated Annualized Funding: Current={self._latest_annualized_funding_rate:.4f}%")
                else:
                    self._latest_annualized_funding_rate = None
                    Logger.debug(f"Calculated Annualized Funding: Current={'N/A'}")

                next_rate = self._latest_funding_info.get('nextFundingRate', None)
                if next_rate:
                    # 计算下一周期年化资金费率
                    self._latest_next_annualized_funding_rate = next_rate * self.FUNDING_PERIODS_PER_YEAR * 100 if next_rate is not None else 0 # 乘以100转换为百分比
                    Logger.debug(f"Calculated Annualized Funding: Next={self._latest_next_annualized_funding_rate:.4f}%")
                else:
                    self._latest_next_annualized_funding_rate = None
                    Logger.debug(f"Calculated Annualized Funding: Next={'N/A'}")

            except (ValueError, TypeError) as e:
                 Logger.error(f"Error calculating annualized funding rates from funding info: {e}")
                 self._latest_annualized_funding_rate = None
                 self._latest_next_annualized_funding_rate = None
                 # TODO: 触发告警
        else:
             self._latest_annualized_funding_rate = None
             self._latest_next_annualized_funding_rate = None
             Logger.debug("Not enough funding info to calculate annualized rates.")


    # --- 提供给其他模块查询的方法 ---
    def get_latest_metrics(self) -> Dict[str, Optional[float]]:
        """
        获取最新的所有计算指标。
        Returns:
            字典包含最新指标 {'basis', 'annualized_funding_rate', 'next_annualized_funding_rate'}。
            如果指标无法计算或数据不全，对应的值可能为 None。
        """
        return {
            'basis': self._latest_basis,
            'annualized_funding_rate': self._latest_annualized_funding_rate,
            'next_annualized_funding_rate': self._latest_next_annualized_funding_rate,
            'last_update_time': self._last_update_time
        }

    def get_latest_basis(self) -> Optional[float]:
         """获取最新的基差。"""
         return self._latest_basis

    def get_latest_annualized_funding_rate(self) -> Optional[float]:
         """获取最新的当前年化资金费率。"""
         return self._latest_annualized_funding_rate

    def get_latest_next_annualized_funding_rate(self) -> Optional[float]:
         """获取最新的下一周期年化资金费率。"""
         return self._latest_next_annualized_funding_rate

    # TODO: 添加获取原始 ticker 或 funding info 的方法，如果其他模块需要访问原始数据


# --- 如何使用 ---
# import Logger_config # 假设你有一个配置日志的模块
# from okx_api_connector import OkxAPIConnector # 假设你已经实现了并初始化了连接器

# Logger_config.setup_Logger()

# # 假设 api_connector 已经被正确初始化并连接到 OKX
# # api_connector = OkxAPIConnector(...)

# # data_processor = DataProcessor(api_connector, 'BTC-USDT', 'BTC-USDT-SWAP')

# # # 在一个独立的线程或循环中定期调用 update_market_data
# # while True:
# #     # data_processor.update_market_data()
# #     # time.sleep(5) # 例如每隔5秒更新一次

# # # 其他模块可以查询最新指标
# # # latest_metrics = data_processor.get_latest_metrics()
# # # if latest_metrics['next_annualized_funding_rate'] is not None and latest_metrics['next_annualized_funding_rate'] > 20.0:
# # #     Logger.info("Found potential high funding rate opportunity!")
# #     # TODO: 触发策略模块进行判断和开仓