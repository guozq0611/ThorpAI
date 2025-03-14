"""
MarketData 类使用示例
"""
import time
import ccxt
from btc_model.core.market.market_data_service import MarketDataService
from btc_model.core.util.log_util import Logger
from btc_model.setting.setting import get_settings


def setup_exchanges():
    """设置交易所实例"""
    # 初始化币安交易所
    setting = get_settings('cex.binance')
    apikey = setting['apikey']
    secretkey = setting['secretkey']


    params_1 = {
        'enableRateLimit': True,
        'proxies': {
            'http': get_settings('common')['proxies']['http'],                  
            'https': get_settings('common')['proxies']['http'],
        },
        'apiKey': apikey,          
        'secret': secretkey,       
        'options': {
            'defaultType': 'spot',  # 可选：'spot', 'margin', 'future'
        },
        'aiohttp_proxy': get_settings('common')['proxies']['http'],
        'ws_proxy': get_settings('common')['proxies']['http']
    }

    exchange_1 = ccxt.binance(params_1)

     # 初始化 OKX 交易所
    setting = get_settings('cex.okx')
    apikey = setting['apikey']
    secretkey = setting['secretkey']
    passphrase = setting['passphrase']

    params_2 = {
        'enableRateLimit': True,
        'proxies': {
            'http': get_settings('common')['proxies']['http'],                   
            'https': get_settings('common')['proxies']['http'],  
        },
        'apiKey': apikey,          
        'secret': secretkey,  
        'password': passphrase,     
        'options': {
            'defaultType': 'spot',
        },
        'aiohttp_proxy': get_settings('common')['proxies']['http'],
        'ws_proxy': get_settings('common')['proxies']['http']
    }
    exchange_2 = ccxt.okx(params_2)


    # 初始化币安合约交易所
    setting = get_settings('cex.binance')
    apikey = setting['apikey']
    secretkey = setting['secretkey']

    params_hedge = {
        'enableRateLimit': True,
        'proxies': {
            'http': get_settings('common')['proxies']['http'],                  
            'https': get_settings('common')['proxies']['http'],
        },
        'apiKey': apikey,          
        'secret': secretkey,       
        'options': {
            'defaultType': 'swap',  # 可选：'spot', 'margin', 'future'
        },
        'aiohttp_proxy': get_settings('common')['proxies']['http'],
        'ws_proxy': get_settings('common')['proxies']['http']
    }
    exchange_hedge = ccxt.binance(params_hedge)

   
    return {
        'exchange_1': exchange_1,
        'exchange_2': exchange_2,
        'exchange_hedge': exchange_hedge,
    }


def main():
    """主函数"""
    # 获取交易所实例
    exchanges = setup_exchanges()
    
    # 初始化市场数据管理器
    md = MarketDataService()
    
    # 添加交易所
    for exchange_id, exchange in exchanges.items():
        md.add_exchange(exchange_id, exchange)
    
    # 订阅行情数据
    symbols_to_watch = ['LSK/USDT']
    swap_symbols = ['LSK/USDT:USDT']
    
    # 订阅现货订单簿
    for symbol in symbols_to_watch:
        md.subscribe_orderbook('exchange_1', symbol)
        md.subscribe_orderbook('exchange_2', symbol)
        

    # 订阅合约订单簿和资金费率
    for symbol in swap_symbols:
        md.subscribe_orderbook('exchange_hedge', symbol)
        md.subscribe_funding_rate('exchange_hedge', symbol)
    
    # 启动市场数据订阅
    md.start()
    
    # 等待数据开始流入
    Logger.info("等待数据开始流入...")
    time.sleep(5)
    
    # 使用市场数据
    try:
        while True:
            # 获取 BTC/USDT 的订单簿数据
            # binance_btc_orderbook = market_data.get_orderbook('binance', 'BTC/USDT')
            # okx_btc_orderbook = market_data.get_orderbook('okx', 'BTC/USDT')
            
            binance_btc_bid = 0
            binance_btc_ask = 0
            okx_btc_bid = 0
            okx_btc_ask = 0

            # # 检查数据是否新鲜
            # if market_data.is_data_fresh('orderbook', 'binance', 'BTC/USDT'):
            #     binance_btc_bid = binance_btc_orderbook['bids'][0][0] if binance_btc_orderbook['bids'] else 0
            #     binance_btc_ask = binance_btc_orderbook['asks'][0][0] if binance_btc_orderbook['asks'] else 0
            #     Logger.info(f"Binance BTC/USDT 买一价: {binance_btc_bid}, 卖一价: {binance_btc_ask}")
            
                
            # if market_data.is_data_fresh('orderbook', 'okx', 'BTC/USDT'):
            #     okx_btc_bid = okx_btc_orderbook['bids'][0][0] if okx_btc_orderbook['bids'] else 0
            #     okx_btc_ask = okx_btc_orderbook['asks'][0][0] if okx_btc_orderbook['asks'] else 0
            #     Logger.info(f"OKX BTC/USDT 买一价: {okx_btc_bid}, 卖一价: {okx_btc_ask}")

            
            # # 计算套利机会
            # if binance_btc_bid > 0 and okx_btc_ask > 0:
            #     spread_1 = (binance_btc_bid / okx_btc_ask - 1) * 100
            #     Logger.info(f"OKX买入Binance卖出套利机会: {spread_1:.4f}%")
            
            # if okx_btc_bid > 0 and binance_btc_ask > 0:
            #     spread_2 = (okx_btc_bid / binance_btc_ask - 1) * 100
            #     Logger.info(f"Binance买入OKX卖出套利机会: {spread_2:.4f}%")
            
            # # 获取合约资金费率
            # btc_funding_rate = market_data.get_funding_rate('binance_futures', 'BTC/USDT:USDT')
            # if market_data.is_data_fresh('funding_rate', 'binance_futures', 'BTC/USDT:USDT'):
            #     Logger.info(f"BTC/USDT 资金费率: {btc_funding_rate['fundingRate'] * 100:.6f}%")
            
            # 等待一秒
            time.sleep(1)
            
    except KeyboardInterrupt:
        Logger.info("程序被用户中断")
    finally:
        # 停止市场数据订阅
        md.stop()
        Logger.info("程序已退出")


if __name__ == "__main__":
    main() 