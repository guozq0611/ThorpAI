from typing import NamedTuple
from btc_model.setting.setting import get_settings

class CommonParams(NamedTuple):
    """
    通用参数
    """
    min_annualized_funding_rate: float = 0.15  # 最小开仓预测年化资金费率 
    min_basis_for_open: float = 0.0  # 最小开仓实时基差 
    max_acceptable_basis: float = 0.002  # 最大可接受实时基差 
    max_concurrent_positions: int = 5  # 最大同时活跃套利头寸数量
    min_position_size_usd: float = 100  # 最小开仓名义价值 (USD)
    funding_rate_close_threshold: float = 0.05  # 平仓触发的年化资金费率 


class MonitorParams(NamedTuple):
    """
    监控参数
    """
    data_fetch_interval_sec: int = 10  # 数据获取间隔 (秒)
    strategy_eval_interval_sec: int = 10  # 策略评估间隔 (秒)
    risk_check_interval_sec: int = 5  # 风险检查间隔 (秒)

class RiskControlParams(NamedTuple):
    """
    风险控制参数
    """
    max_loss_limit_absolute_daily: float = 10  # 单日最大亏损限制（绝对值）
    max_consecutive_loss_times: int = 10  # 连续亏损次数
    margin_ratio_warning: float = 0.3  # 保证金率预警线
    margin_ratio_critical: float = 0.2  # 保证金率危险线，需采取行动
    basis_threshold_stop_loss: float = -0.005  # 基差不利变动止损阈值 (例如 -0.5%)
    funding_rate_unfavorable_threshold: float = 0.0  # 资金费率转为负的阈值
    position_imbalance_tolerance: float = 0.05  # 头寸价值偏差容忍度 (例如 5%)
    total_floating_pnl_limit: float = -0.1  # 总浮动亏损占总投入资金的比例限制 (例如 -10%)

class ExecutionParams(NamedTuple):
    """
    执行参数
    """
    spot_td_mode: str = "cash"  # 现货交易模式 (通常是cash)
    swap_td_mode: str = "isolated"  # 永续合约交易模式 (cross 或 isolated)
    spot_order_type_open: str = "market"  # 现货开仓订单类型 (market, limit)
    swap_order_type_open: str = "market"  # 永续合约开仓订单类型 (market, limit)
    spot_order_type_close: str = "market"  # 现货平仓订单类型
    swap_order_type_close: str = "market"  # 永续合约平仓订单类型



class StrategyParams(NamedTuple):
    """
    策略参数
    """
    common_params: CommonParams
    monitor_params: MonitorParams
    risk_control_params: RiskControlParams
    execution_params: ExecutionParams

    @classmethod
    def from_settings(cls) -> 'StrategyParams':
        config = get_settings('strategy.funding_rate_arbitrage')
        return cls(
            common_params=CommonParams(**config['common_params']),
            monitor_params=MonitorParams(**config['monitor_params']),
            risk_control_params=RiskControlParams(**config['risk_control_params']),
            execution_params=ExecutionParams(**config['execution_params'])  
        )