import os
import asyncio
import ccxt.pro as ccxtpro
import pandas as pd
import traceback
from typing import Dict, Tuple
from collections import defaultdict

from btc_model.setting.setting import get_settings

params = {
    'enableRateLimit': True,
    'proxies': {
        'http': get_settings('common')['proxies'].get('http', None),
        'https': get_settings('common')['proxies'].get('https', None),
    },
    'aiohttp_proxy': get_settings('common')['proxies'].get('http', None),
    'ws_proxy': get_settings('common')['proxies'].get('http', None)
}

class PairsMonitor:
    def __init__(self, exchange_a, exchange_b, pairs):
        self.exchange_a = exchange_a
        self.exchange_b = exchange_b
        
        # 构建symbol映射关系
        self.symbol_map = self._build_symbol_map(pairs)
        self.pair_data: Dict[Tuple[str, str], dict] = {}
        self.monitor_tasks = []
        self.running = False

        self.on_arbitrage_opportunity_event_list = []

    def _build_symbol_map(self, pairs):
        """构建symbol到配对关系的快速映射"""
        symbol_map = defaultdict(dict)
        for pair in pairs:
            key = (pair['base'], pair['quote'])
            symbol_map['a'][pair['symbol_a']] = {'index': 'a', 'pair_key': key}
            symbol_map['b'][pair['symbol_b']] = {'index': 'b', 'pair_key': key}
        return symbol_map

    async def monitor(self, exchange, index: str):
        """
        统一监控方法
        :param exchange: 交易所实例
        :param index: 来源索引 ('a'或'b')
        """
        symbols = [s for s in self.symbol_map[index]]

        while self.running:
            try:
                tickers = await exchange.watch_tickers(symbols)
                await self.process_tickers(tickers, index)
            except Exception as e:
                traceback.print_exc()
                print(f"监控异常({index}): {str(e)}")
                await asyncio.sleep(5)

    async def process_tickers(self, tickers, index):
        """处理批量ticker数据"""
        for symbol, ticker in tickers.items():
            if symbol not in self.symbol_map[index]:
                continue

            pair_map = self.symbol_map[index][symbol]
            pair_key = pair_map['pair_key']
            
            # 初始化数据结构
            if pair_key not in self.pair_data:
                self.pair_data[pair_key] = {
                    'price_a': None,
                    'price_b': None,
                    'spread': None
                } 

            price_field = f'price_{index}'
            self.pair_data[pair_key][price_field] = {
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'last': ticker['last']
            }
 
            # 立即计算价差
            await self.calculate_spread(pair_key)

    async def calculate_spread(self, pair_key):
        """带校验的价差计算"""
        data = self.pair_data[pair_key]
        try:
            if data['price_a'] and data['price_b']:
                # 作为a的买方，监控 price_a['ask'] / price_b['bid'] - 1 的价差
                spread_buy_a = (data['price_b']['bid'] / data['price_a']['ask']) - 1
                # 作为b的买方，监控 price_b['ask'] / price_a['bid'] - 1 的价差
                spread_buy_b = (data['price_a']['bid'] / data['price_b']['ask']) - 1

                # 取两个价差中的较大值作为最终价差
                spread = max(spread_buy_a, spread_buy_b)
                data['spread'] = spread
                data['comment'] = ''
               
                # 触发报警的价差阈值
                if spread > 0.003:  # 假设阈值为1%
                    if spread_buy_a > spread_buy_b:
                        data['comment'] = f'【{self.exchange_a.id}】 买入 {data["price_a"]["ask"]},【{self.exchange_b.id}】 卖出 {data["price_b"]["bid"]}'
    
                    else:
                        data['comment'] = f'【{self.exchange_b.id}】 买入 {data["price_b"]["ask"]},【{self.exchange_a.id}】 卖出 {data["price_a"]["bid"]}'

                    await self.trigger_arbitrage(pair_key)
        except (TypeError, ZeroDivisionError, KeyError) as e:
            print(f"价差计算错误 {'-'.join(pair_key)  }: {str(e)}")

    async def trigger_arbitrage(self, pair_key):
        """触发套利逻辑"""
        data = self.pair_data[pair_key]
        # print(f"套利机会! {pair_key} 价差: {data['spread']:.2%}")

        for event in self.on_arbitrage_opportunity_event_list:
            event(pair_key, data)


    def start(self):
        """启动监控任务"""
        self.running = True
        self.monitor_tasks = [
            asyncio.create_task(self.monitor(self.exchange_a, 'a')),
            asyncio.create_task(self.monitor(self.exchange_b, 'b'))
        ]

    async def stop(self):
        """优雅关闭"""
        self.running = False
        await asyncio.gather(*self.monitor_tasks, return_exceptions=True)
        await self.exchange_a.close()
        await self.exchange_b.close()

    def on_arbitrage_opportunity(self, opportunity):
        """处理套利机会"""
        print(f"套利机会触发: {opportunity}")
        # 在这里执行套利策略
        self.execute_arbitrage(opportunity)

    def add_arbitrage_opportunity_event(self, on_arbitrage_opportunity_event):
        if callable(on_arbitrage_opportunity_event):
            self.on_arbitrage_opportunity_event_list.append(on_arbitrage_opportunity_event)
        else:
            raise ValueError("传递的对象不是可调用的函数或方法")


async def run_monitor(exchange_a, exchange_b, pairs):
    await exchange_a.load_markets()
    await exchange_b.load_markets()

    pairs_monitor = PairsMonitor(exchange_a, exchange_b, pairs)
    pairs_monitor.start()
    
    try:
        while True:
            await asyncio.sleep(1)
    except:
        await pairs_monitor.stop()
        print("监控已停止")

if __name__ == "__main__":
    try:
        pairs_df = pd.read_csv("normal_pairs.csv")
        pairs_dif = pairs_df[pairs_df['quote'] == "USDT"]
        required_cols = ['base', 'quote', 'symbol_a', 'symbol_b']
        if not all(col in pairs_df.columns for col in required_cols):
            raise ValueError("CSV文件缺少必要列")
        pairs = pairs_df[required_cols].to_dict('records')
    except Exception as e:
        print(f"配置加载失败: {str(e)}")
        exit(1)

    # 交易所初始化
    exchange_a = ccxtpro.binance(params)
    exchange_b = ccxtpro.okx(params)
    
    try:
        asyncio.run(run_monitor(exchange_a, exchange_b, pairs))
    except KeyboardInterrupt:
        print("程序已终止")