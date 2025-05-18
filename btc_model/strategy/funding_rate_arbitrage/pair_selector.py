# pair_selector.py
import logging
import time

from btc_model.core.util.log_util import logger
from btc_model.strategy.funding_rate_arbitrage.exchange_connector import ExchangeConnector # 引入交易所连接器


class PairSelector:
    def __init__(self, exchange_connector: ExchangeConnector):
        """
        初始化交易对筛选器
        :param exchange_connector: ExchangeConnector 实例
        """
        logger.info("初始化交易对筛选器...")
        self.exchange_connector = exchange_connector
        # 从配置加载筛选参数 (如果定义了的话)
        # self.min_spot_volume_usd = getattr(config, 'MIN_SPOT_VOLUME_USD', 1000000) # 默认值示例
        # self.min_perpetual_volume_usd = getattr(config, 'MIN_PERPETUAL_VOLUME_USD', 5000000) # 默认值示例
        # self.max_spot_spread_percent = getattr(config, 'MAX_SPOT_SPREAD_PERCENT', 0.05) # 默认值示例 0.05%
        # self.max_perpetual_spread_percent = getattr(config, 'MAX_PERPETUAL_SPREAD_PERCENT', 0.1) # 默认值示例 0.1%

    def get_filtered_pairs(self)->list[dict]:
        """
        筛选出适用于资金费率套利的交易对
        基于是否存在现货/永续对和流动性指标
        :return: 列表，每个元素是一个字典，格式与 config.TARGET_PAIRS 中的元素一致
        """
        logger.info("开始筛选适用的交易对...")
        if not self.exchange_connector or not self.exchange_connector.exchange:
            logger.error("交易所连接未建立或市场信息未加载，无法筛选交易对。")
            return []

        # 确保市场信息已加载
        if not self.exchange_connector.exchange.markets:
             try:
                  logger.info("交易所市场信息未加载，尝试重新加载...")
                  self.exchange_connector.exchange.load_markets()
             except Exception as e:
                  logger.error(f"加载交易所市场信息失败: {e}")
                  return []
             if not self.exchange_connector.exchange.markets:
                  logger.error("加载市场信息后 markets 仍然为空，无法筛选。")
                  return []


        all_markets = self.exchange_connector.exchange.markets # 获取所有市场信息

        spot_markets = {m['symbol']: m for m in all_markets.values() if m['spot'] and m['active']}
        perpetual_markets = {m['symbol']: m for m in all_markets.values() if m['swap'] and m['active'] and m['linear'] and m['quote'] == 'USDT'} # 筛选 USDT 结算的永续合约 (通常线性合约)

        logger.info(f"获取到 {len(spot_markets)} 个活跃现货市场，{len(perpetual_markets)} 个活跃 USDT 永续合约市场。")

        potential_pairs = []
        # 寻找匹配的现货和永续合约对
        for spot_symbol, spot_m in spot_markets.items():
            base = spot_m['base']
            quote = spot_m['quote']

            # 构建可能的永续合约 Symbol (OKX V5 通常是 BASE-QUOTE-SWAP)
            possible_perpetual_symbol = f"{base}/{quote}:{quote}"

            if possible_perpetual_symbol in perpetual_markets:
                perpetual_m = perpetual_markets[possible_perpetual_symbol]

                # 检查基础货币和计价货币是否一致 (双重确认)
                if perpetual_m['base'] == base and perpetual_m['quote'] == quote:
                     potential_pairs.append({
                         'pair_name': f"{base}-{quote}-HEDGE", # 构建一个策略内部名称
                         'spot_symbol': spot_symbol,
                         'perpetual_symbol': possible_perpetual_symbol,
                         'base_currency': base,
                         'quote_currency': quote,
                     })
                     # logger.debug(f"找到潜在配对：现货 {spot_symbol} <-> 永续 {possible_perpetual_symbol}")


        logger.info(f"找到 {len(potential_pairs)} 个潜在的现货-永续合约配对。")

        filtered_pairs = []

        # 对潜在配对进行流动性筛选
        # 需要获取最新的行情数据来判断交易量和价差
        logger.info("正在对潜在配对进行流动性筛选...")

        # 可以批量获取 tickers，但 CCXT 的 fetch_tickers 可能对所有市场请求，或者需要指定列表
        # 简单起见，这里逐个获取，注意频率限制
        # 或者在 DataProcessor 中先获取所有需要的 tickers，这里直接使用？
        # 让 PairSelector 自己获取最新的 Ticker 数据进行筛选更独立
        
        # 注意：这里需要频繁调用 fetch_ticker，确保 connector 内部的频率限制处理是有效的
        # 如果潜在对很多，批量获取更高效（如果 CCXT 支持且交易所 API 支持）
        # CCXT 的 fetch_tickers() 通常可以传入 symbol 列表
        #all_symbols_to_fetch = [p['spot_symbol'] for p in potential_pairs] + [p['perpetual_symbol'] for p in potential_pairs]
        
        # 现货和永续合约的ticker需要分开获取，因为交易所的API限制
        spot_symbols_to_fetch = list(set([p['spot_symbol'] for p in potential_pairs]))
        perpetual_symbols_to_fetch = list(set([p['perpetual_symbol'] for p in potential_pairs]))
        
        logger.debug(f"准备获取 {len(spot_symbols_to_fetch) + len(perpetual_symbols_to_fetch)} 个 symbols 的最新行情数据...")
        try:
             # 批量获取 ticker 数据
             # 注意：OKX API 对 fetch_tickers 传入的 Symbol 列表长度有限制，CCXT 内部应该会处理拆分请求
             spot_tickers = self.exchange_connector.exchange.fetch_tickers(spot_symbols_to_fetch)
             perpetual_tickers = self.exchange_connector.exchange.fetch_tickers(perpetual_symbols_to_fetch)
             tickers = {**spot_tickers, **perpetual_tickers}
             logger.debug("成功获取所有Symbols的批量行情数据。")
        except Exception as e:
             logger.error(f"批量获取行情数据失败，无法进行流动性筛选: {e}")
             # 如果批量失败，可以尝试单个获取，或者直接跳过流动性筛选
             # 为了不阻塞流程，这里选择返回找到的潜在对（不经过流动性筛选）
             logger.warning("跳过流动性筛选，返回所有潜在配对。")
             return potential_pairs # TODO: 根据实际需求决定失败时的行为

        # 将批量获取的 ticker 数据转换为字典方便查找
        tickers_dict = {t['symbol']: t for t in tickers.values()}


        # 开始筛选
        for pair in potential_pairs:
            spot_symbol = pair['spot_symbol']
            perpetual_symbol = pair['perpetual_symbol']

            spot_ticker = tickers_dict.get(spot_symbol)
            perpetual_ticker = tickers_dict.get(perpetual_symbol)

            if not spot_ticker or not perpetual_ticker:
                logger.warning(f"缺少 {pair['pair_name']} 的行情数据，跳过流动性检查。")
                continue

            # --- 流动性检查 ---
            # 检查是否有足够的交易量和较小的价差

            # 交易量检查 (使用 quoteVolume 或 baseVolume，取决于哪个更方便衡量)
            # OKX 的 volume 是交易量（数量），quoteVolume 是交易额（计价货币价值）
            spot_volume_usd = spot_ticker.get('quoteVolume') # 现货交易额
            perpetual_volume_usd = perpetual_ticker.get('quoteVolume') # 永续合约交易额

            # TODO: 从 config 加载阈值并应用
            # if spot_volume_usd is None or spot_volume_usd < self.min_spot_volume_usd:
            #      logger.debug(f"{pair['pair_name']}: 现货交易量不足 ({spot_volume_usd})，跳过。")
            #      continue
            # if perpetual_volume_usd is None or perpetual_volume_usd < self.min_perpetual_volume_usd:
            #      logger.debug(f"{pair['pair_name']}: 永续交易量不足 ({perpetual_volume_usd})，跳过。")
            #      continue

            # 价差检查 (使用 bid 和 ask)
            spot_bid = spot_ticker.get('bid')
            spot_ask = spot_ticker.get('ask')
            perpetual_bid = perpetual_ticker.get('bid')
            perpetual_ask = perpetual_ticker.get('ask')

            spot_spread_percent = None
            if spot_bid is not None and spot_ask is not None and spot_ask > 0:
                spot_spread_percent = (spot_ask - spot_bid) / spot_ask * 100

            perpetual_spread_percent = None
            if perpetual_bid is not None and perpetual_ask is not None and perpetual_ask > 0:
                perpetual_spread_percent = (perpetual_ask - perpetual_bid) / perpetual_ask * 100

            # TODO: 从 config 加载阈值并应用
            # if spot_spread_percent is None or spot_spread_percent > self.max_spot_spread_percent:
            #      logger.debug(f"{pair['pair_name']}: 现货价差过大 ({spot_spread_percent:.4f}%)，跳过。")
            #      continue
            # if perpetual_spread_percent is None or perpetual_spread_percent > self.max_perpetual_spread_percent:
            #      logger.debug(f"{pair['pair_name']}: 永续价差过大 ({perpetual_spread_percent:.4f}%)，跳过。")
            #      continue

            # --- 简化筛选示例 (仅检查非零的 bid/ask 作为初步流动性判断) ---
            # TODO: 替换为实际的交易量和价差阈值判断
            if spot_bid is not None and spot_ask is not None and spot_bid > 0 and \
               perpetual_bid is not None and perpetual_ask is not None and perpetual_bid > 0:
                # 假设通过了流动性检查 (这里只是占位符)
                 passed_liquidity_check = True # 替换为实际的基于阈值的判断逻辑
                 logger.debug(f"{pair['pair_name']}: 通过初步流动性检查。")
            else:
                 passed_liquidity_check = False
                 logger.debug(f"{pair['pair_name']}: 未通过初步流动性检查 (缺少 bid/ask)。")


            if passed_liquidity_check:
                filtered_pairs.append(pair)
                logger.info(f"识别到适用交易对: {pair['pair_name']} (现货: {spot_symbol}, 永续: {perpetual_symbol})")
            else:
                 logger.debug(f"{pair['pair_name']} 未通过流动性筛选。")

        logger.info(f"筛选完成，找到 {len(filtered_pairs)} 个适用的交易对。")
        return filtered_pairs


if __name__ == "__main__":
    # 需要先初始化 logger 和 ExchangeConnector
    print("初始化日志...")


    print("初始化交易所连接器...")
    connector = ExchangeConnector('okx') # 确保 OKX API 密钥在 .env 中配置

    if connector.exchange:
        print("初始化交易对筛选器...")
        pair_selector = PairSelector(connector)

        # 运行筛选
        filtered_pairs = pair_selector.get_filtered_pairs()

        print("\n--- 筛选结果 ---")
        if filtered_pairs:
            print("找到以下适用的交易对 (格式与 config.TARGET_PAIRS 一致):")
            import json
            print(json.dumps(filtered_pairs, indent=4))
        else:
            print("未找到适用的交易对。请检查配置、API密钥、网络连接以及交易所的交易对情况。")

        connector.close()
        print("程序退出。")
    else:
        print("交易所连接失败，无法运行交易对筛选器示例。请检查 API 密钥和网络。")