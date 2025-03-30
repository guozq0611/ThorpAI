import os
from logging import CRITICAL
from typing import Dict, Any

from btc_model.core.common.const import PROJECT_NAME
from btc_model.core.util.file_util import FileUtil

SETTINGS: Dict[str, Any] = {
    # 配置request url需要的proxies，如果网络环境无需代理，注释即可
    "common.proxies": {
     
        'http': 'http://127.0.0.1:7897',
        'https': 'http://127.0.0.1:7897'

    },


    "font.family": "微软雅黑",
    "font.size": 12,

    "log.active": True,
    "log.level": CRITICAL,
    "log.console": True,
    "log.file": True,

    "email.server": "smtp.qq.com",
    "email.port": 465,
    "email.username": "",
    "email.password": "",
    "email.sender": "",
    "email.receiver": "",

    # 配置需要订阅的市场数据
    "market_data_service.exchanges": ['binance', 'okx'],

    "trade.live_mode": False,

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # 为避免真实账户信息泄露，这里填写的是模拟账户的apikey和secretkey
    # 如果需要使用实盘账户，请在.ThorpAI/setting/setting.local.json中填写实盘账户的apikey和secretkey
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    "cex.okx.apikey": "dede12e9-ec61-4212-944e-9ac5138f743b",
    "cex.okx.secretkey": "E70C2C82FDC68D98DC7252B83745B38F",
    "cex.okx.passphrase": "Qwe123!@#",
   # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    # 配置okx用的代理，若网络网络无需代理，设置为False
    "cex.okx.proxy": False,
    "cex.okx.fees": {
                'spot': {
                    'maker': 0.0008,
                    'taker': 0.001
                },
                'swap': {
                    'maker': 0.0002,
                    'taker': 0.0005
                }
            },

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # 为避免真实账户信息泄露，这里填写的是模拟账户的apikey和secretkey
    # 如果需要使用实盘账户，请在.ThorpAI/setting/setting.local.json中填写实盘账户的apikey和secretkey
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    "cex.binance.apikey": "Yef2imrldezU8R6hdgvBFPgMMFnsxG06TvPoQUpwP5UI4jw9XhM4MudQbCFgXVis",
    "cex.binance.secretkey": "66Rc9gtt1OnudixpPKvIuqNL56YSymtfz8WQ6Q9rfw58R2TxAUY3RH4ohjaJkeYu",
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
    # 配置binance用的代理，若网络网络无需代理，设置为False
    "cex.binance.proxy": False,
    "cex.binance.fees": {
                'spot': {
                    'maker': 0.001,
                    'taker': 0.001
                },
                'swap': {
                    'maker': 0.0002,
                    'taker': 0.0004
                }
            },

    # ------------------------------------------------------
    # 设置逃顶模型各指标的参数
    # ------------------------------------------------------
    "escape_model.indicator.pi_cycle.short_window": 111,
    "escape_model.indicator.pi_cycle.long_window": 350,
    "escape_model.indicator.pi_cycle.threshold": 2,

    "escape_model.indicator.mvrv_zscore.threshold": 8,

    "escape_model.indicator.mayer_multiple.window": 200,
    "escape_model.indicator.mayer_multiple.threshold": 2.4,

    "escape_model.indicator.feargreed.threshold": 80,

    "escape_model.indicator.rsi.window": 14,
    "escape_model.indicator.rsi.upper": 70,
    "escape_model.indicator.rsi.lower": 30,

    "escape_model.indicator.macd.fast_period": 12,
    "escape_model.indicator.macd.slow_period": 26,
    "escape_model.indicator.macd.signal_period": 9,

    "escape_model.indicator.sth_mvrv.threshold": 2,

    "escape_model.indicator.bollinger.window": 100,
    "escape_model.indicator.bollinger.nbdev": 2.5,
    # ------------------------------------------------------

    # ------------------------------------------------------
    # update_manager的参数
    # ------------------------------------------------------
    "update_manager.indicator.use_exchange": 'OKX',
    "update_manager.indicator.symbols": ['BTC-USDT', 'ETH-USDT', 'SOL-USDT', 'SOL-USDT'],

    # setting mysql in ~/.thorpai/setting/setting.local.json
    "database.mysql.host": "",
    "database.mysql.port": 3306,
    "database.mysql.user": "",
    "database.mysql.password": "",
    "database.mysql.database": "",

    "database.uri": "",
    "database.name": "",
    "database.database": "",
    "database.host": "",
    "database.port": 0,
    "database.user": "",
    "database.password": "",
    "database.auth_source": '',

    # ------------------------------------------------------
    # 套利策略参数
    # ------------------------------------------------------  
    "strategy.exchange_arbitrage.common_params": {
        "order_timeout": 10,    # 订单超时时间, 超时后撤单重新下单
        "retry_times": 3,       # 重试次数
        "order_imbalance_threshold": 10,    # 残腿阈值，单位为USDT
        "order_chase_times": 3, # 追单次数
        "imbalance_adjust_times": 5, # 残腿调整次数
    },
    
    "strategy.exchange_arbitrage.capital_limit_params": {
        "max_amount": 100,
        "max_trading_pairs": 10,
        "max_amount_per_pair": 100,
        "min_amount_per_pair": 10,
        "swap_leverage": 1, # 永续合约杠杆倍数
        
    },

    "strategy.exchange_arbitrage.spread_threshold_params": {
        "min_percent": 0.001,
        "max_percent": 0.005,
        "min_absolute": 10,
        "max_absolute": 100,
        "min_profit": 0.001,
    },

    "strategy.exchange_arbitrage.spread_occurrence_params": {
        "duration": 10,
        "min_occurrences": 10,
        "consecutive_required": True,
    },

    "strategy.exchange_arbitrage.risk_control_params": {
        "max_loss_limit_absolute_daily": 10,
        "max_consecutive_loss_times": 10,
    },
    

    

}


def update_settings(d1: Dict, d2: Dict) -> Dict:
    """递归合并两个字典"""
    result = d1.copy()
    for k, v in d2.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = update_settings(result[k], v)
        else:
            result[k] = v
    return result


# Load global setting from json file.
setting_filename: str = "setting.local.json"
local_settings_file_path = os.path.join(FileUtil.get_project_dir(project_name=PROJECT_NAME, sub_dir='setting'), setting_filename)
SETTINGS = update_settings(SETTINGS, FileUtil.load_json(local_settings_file_path))


def get_settings(prefix: str = "") -> Dict[str, Any]:
    prefix_length = len(prefix)
    if prefix_length > 0 and not prefix.endswith('.'):
        prefix = prefix + '.'
        prefix_length += 1

    return {k[prefix_length:]: v for k, v in SETTINGS.items() if k.startswith(prefix)}



proxy_http = get_settings('common')['proxies'].get('http', None)
proxy_https = get_settings('common')['proxies'].get('https', None)


if __name__ == "__main__":
    setting = get_settings('cex.okx')
    print(setting)

    