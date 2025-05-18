# exchange_connector.py
import ccxt
import time

from btc_model.setting.setting import get_settings
from btc_model.core.util.log_util import logger

class ExchangeConnector:
    def __init__(self, exchange_id:str):
        """
        初始化交易所连接器
        :param exchange_id: 交易所名称 (ccxt 支持的名称)
        """
        self.exchange_id = exchange_id
        self.exchange: ccxt.Exchange = None
        self._connect()

    def _connect(self):
        """
        建立与交易所的连接并加载市场信息
        """
        logger.info(f"正在连接到交易所: {self.exchange_id}")
        try:
            is_live = get_settings("trade.live_mode")
            if is_live:
                setting = get_settings(f'cex.{self.exchange_id}')
            else:
                setting = get_settings(f'cex.sandbox.{self.exchange_id}')

            apikey = setting.get('apikey', None)
            secretkey = setting.get('secretkey', None)
            passphrase = setting.get('passphrase', None)

            exchange_params = {
                'enableRateLimit': True,
                'proxies': {
                    'http': get_settings('common.proxies').get('http', None),                  
                    'https': get_settings('common.proxies').get('https', None),
                },
                'apiKey': apikey,          
                'secret': secretkey,       
                'password': passphrase,   
                'options': {
                    'defaultType': 'swap', # 默认操作永续合约
                    'adjustForTimeDifference': True, # 调整时间戳，避免签名错误
                },
                'aiohttp_proxy': get_settings('common.proxies').get('http', None),
                'ws_proxy': get_settings('common.proxies').get('http', None)
            }

            # 获取 CCXT 支持的交易所类实例
            self.exchange = getattr(ccxt, self.exchange_id)(exchange_params)

            # 如果是 OKX 模拟盘，设置 sandbox 模式
            if self.exchange_id == 'okx' and  not is_live:
                exchange_params['options']['sandbox'] = True
                self.exchange.set_sandbox_mode(True)
                logger.info("OKX 连接器设置为模拟盘模式")

            # 加载市场信息，这会获取所有交易对、精度、限制等信息
            self.exchange.load_markets()
            logger.info(f"成功连接并加载市场信息: {self.exchange_id}")

        except ccxt.BaseError as e:
            logger.error(f"连接交易所失败: {e}")
            self.exchange = None # 连接失败时将 exchange 设为 None
            # 根据需要可以退出程序或者实现重连逻辑
            # raise e # 重新抛出异常，让调用者知道连接失败
        except Exception as e:
            logger.error(f"初始化交易所连接器时发生未知错误: {e}")
            self.exchange = None
            # raise e

    def _handle_rate_limit(self):
        """
        处理交易所 API 调用频率限制
        """
        if self.exchange and self.exchange.rateLimit:
            time.sleep(self.exchange.rateLimit / 1000.0)

    def fetch_ticker(self, symbol):
        """
        获取指定交易对的最新行情信息
        :param symbol: 交易对符号 (例如 'BTC/USDT:USDT' 对于 OKX 永续)
        :return: Ticker dict 或 None
        """
        if not self.exchange:
            logger.error("交易所连接未建立，无法获取行情。")
            return None
        try:
            self._handle_rate_limit()
            # CCXT 对于永续合约通常使用 '基础货币/计价货币:结算货币' 的格式
            # 例如 BTC/USDT 永续，结算货币是 USDT，symbol 是 'BTC/USDT:USDT'
            # 如果结算货币是 BTC，symbol 是 'BTC/USDT:BTC'
            # 需要根据具体的交易对确定 symbol
            # fetch_ticker 通常包含买一价 (bid), 卖一价 (ask), 最新价 (last) 等
            ticker = self.exchange.fetch_ticker(symbol)
            logger.debug(f"获取 {symbol} 行情: {ticker}")
            return ticker
        except ccxt.ExchangeError as e:
            logger.error(f"获取 {symbol} 行情时发生交易所错误: {e}")
            return None
        except Exception as e:
            logger.error(f"获取 {symbol} 行情时发生未知错误: {e}")
            return None

    def fetch_funding_rate(self, symbol):
        """
        获取指定交易对的资金费率信息
        :param symbol: 交易对符号 (例如 'BTC/USDT:USDT')
        :return: Funding rate dict 或 None
        """
        if not self.exchange:
            logger.error("交易所连接未建立，无法获取资金费率。")
            return None
        try:
            self._handle_rate_limit()
            # fetch_funding_rate 方法通常返回当前的资金费率和下一期的预测资金费率等
            # 不同交易所返回的数据结构可能略有差异，需要查阅 CCXT 文档
            # OKX 返回的数据可能包含 'currentFundingRate', 'nextFundingRate', 'nextFundingTime' 等
            funding_rate_data = self.exchange.fetch_funding_rate(symbol)
            logger.debug(f"获取 {symbol} 资金费率: {funding_rate_data}")
            return funding_rate_data
        except ccxt.ExchangeError as e:
            logger.error(f"获取 {symbol} 资金费率时发生交易所错误: {e}")
            return None
        except Exception as e:
            logger.error(f"获取 {symbol} 资金费率时发生未知错误: {e}")
            return None

    def fetch_balance(self):
        """
        获取账户余额信息
        :return: Balance dict 或 None
        """
        if not self.exchange:
            logger.error("交易所连接未建立，无法获取账户余额。")
            return None
        try:
            self._handle_rate_limit()
            # fetch_balance 返回一个包含所有资产余额信息的字典
            # 例如 {'USDT': {'free': 1000.0, 'used': 500.0, 'total': 1500.0}, ...}
            balance = self.exchange.fetch_balance()
            logger.debug(f"获取账户余额: {balance}")
            return balance
        except ccxt.ExchangeError as e:
            logger.error(f"获取账户余额时发生交易所错误: {e}")
            return None
        except Exception as e:
            logger.error(f"获取账户余额时发生未知错误: {e}")
            return None

    def get_account_info(self, params=None):
        """
        获取账户详细信息，包括账户类型、保证金、杠杆、风险率等
        
        Args:
            params: 额外的请求参数，根据交易所API的不同可能需要传递不同的参数
            
        Returns:
            Dict: 账户信息字典，如果获取失败则返回None
            格式例如：
            {
                'account_type': 'spot/margin/futures',
                'balances': {'BTC': {'free': 1.0, 'used': 0.5, 'total': 1.5}, ...},
                'margin_ratio': 0.25,  # 保证金率
                'risk_level': 'normal',  # 风险级别
                'unrealized_pnl': 100.0,  # 未实现盈亏
                'positions': [...]  # 当前持仓列表
            }
        """
        if not self.exchange:
            logger.error("交易所连接未建立，无法获取账户信息。")
            return None
        
        try:
            self._handle_rate_limit()
            
            # 根据交易所不同，选择合适的API方法获取账户信息
            account_info = {}
            
            # 获取基础账户余额信息
            balance = self.fetch_balance()
            if balance:
                account_info['balances'] = balance
            
            # 针对不同交易所的特定实现
            if self.exchange_id == 'okx':
                # OKX特有的账户信息获取方法
                try:
                    # 安全地使用OKX V5 API
                    account_info['account_type'] = 'unified'  # OKX使用统一账户模式
                    
                    # 获取账户资金信息 - 这是获取账户信息的正确API
                    try:
                        # 使用CCXT OKX账户余额API（正确的方法）
                        account_funds = self.exchange.privateGetAccountBalance(params)
                        if 'data' in account_funds and len(account_funds['data']) > 0:
                            funds_data = account_funds['data'][0]
                            account_info['total_equity'] = float(funds_data.get('totalEq') or 0)
                            account_info['available_equity'] = float(funds_data.get('availEq') or 0)
                            
                            # 统计所有币种的未实现盈亏总和
                            
                            total_available_equity = 0  # 可用保证金
                            total_available_balance = 0  # 可用余额
                            total_unrealized_pl = 0  # 未实现盈亏
                            for detail in funds_data.get('details', []):
                                total_available_equity += float(detail.get('availEq') or 0)
                                total_available_balance += float(detail.get('availBal') or 0)
                                total_unrealized_pl += float(detail.get('upl') or 0)
                                
                            account_info['unrealized_pnl'] = total_unrealized_pl
                            account_info['available_equity'] = total_available_equity
                            account_info['available_balance'] = total_available_balance
                    except Exception as e:
                        logger.warning(f"获取OKX账户资金信息失败: {e}")
                    
                    # 尝试获取账户配置信息
                    try:
                        # 这个API可能不存在或路径不正确，使用try-except捕获
                        account_config = self.exchange.privateGetAccountConfig(params)
                        if 'data' in account_config:
                            account_info['account_config'] = account_config['data']
                    except Exception as e:
                        logger.warning(f"获取OKX账户配置信息失败: {e}")
                    
                    # 获取当前持仓信息
                    try:
                        positions = self.fetch_positions(params)
                        if positions:
                            account_info['positions'] = positions
                            
                            # 计算一个综合的保证金率
                            min_margin_ratio = 999.0
                            for pos in positions:
                                if pos and 'notional' in pos and float(pos.get('notional', 0)) > 0:
                                    # 尝试从持仓信息中获取保证金率
                                    margin_ratio = float(pos.get('marginRatio', 999))
                                    min_margin_ratio = min(min_margin_ratio, margin_ratio)
                            
                            if min_margin_ratio < 999.0:
                                account_info['margin_ratio'] = min_margin_ratio
                                account_info['risk_level'] = self._calculate_risk_level(min_margin_ratio)
                            else:
                                account_info['margin_ratio'] = 999.0
                                account_info['risk_level'] = 'safe'
                        else:
                            account_info['margin_ratio'] = 999.0
                            account_info['risk_level'] = 'safe'

                    except Exception as e:
                        logger.warning(f"获取OKX持仓信息失败: {e}")
                        
                except Exception as e:
                    logger.warning(f"获取OKX特定账户信息时出错: {e}")
                
            elif self.exchange_id == 'binance':
                # Binance特有的账户信息获取方法
                try:
                    # 获取账户信息
                    if 'swap' in self.exchange.options.get('defaultType', ''):
                        # 合约账户
                        futures_account = self.exchange.fapiPrivateGetAccount(params)
                        account_info['account_type'] = 'futures'
                        account_info['positions'] = futures_account.get('positions', [])
                        account_info['margin_ratio'] = float(futures_account.get('totalMarginBalance', 0)) / float(futures_account.get('totalMaintMargin', 1)) if float(futures_account.get('totalMaintMargin', 0)) > 0 else 999
                        account_info['unrealized_pnl'] = float(futures_account.get('totalUnrealizedProfit', 0))
                        account_info['risk_level'] = self._calculate_risk_level(account_info['margin_ratio'])
                    else:
                        # 现货账户
                        account_info['account_type'] = 'spot'
                        
                except Exception as e:
                    logger.warning(f"获取Binance特定账户信息时出错: {e}")
            
            # 其他交易所可以在这里添加
            
            return account_info
            
        except ccxt.ExchangeError as e:
            logger.error(f"获取账户信息时发生交易所错误: {e}")
            return None
        except Exception as e:
            logger.error(f"获取账户信息时发生未知错误: {e}")
            return None

    def _calculate_risk_level(self, margin_ratio):
        """
        根据保证金率计算风险级别
        
        Args:
            margin_ratio: 保证金率
            
        Returns:
            str: 风险级别 ('safe', 'warning', 'danger', 'critical')
        """
        if margin_ratio >= 0.5:
            return 'safe'
        elif margin_ratio >= 0.3:
            return 'normal'
        elif margin_ratio >= 0.2:
            return 'warning'
        elif margin_ratio >= 0.1:
            return 'danger'
        else:
            return 'critical'
            
    def fetch_positions(self, params={}):
        """
        获取当前所有持仓信息
        
        Args:
            params: 额外参数
            
        Returns:
            List: 持仓列表，如果获取失败则返回None
        """
        if not self.exchange:
            logger.error("交易所连接未建立，无法获取持仓信息。")
            return None
            
        try:
            self._handle_rate_limit()

            if not params:
                params = {}
            
            # 对于支持fetch_positions方法的交易所直接调用
            if hasattr(self.exchange, 'fetch_positions'):
                positions = self.exchange.fetch_positions(params=params)
                logger.debug(f"获取持仓信息: {positions}")
                return positions
                
            # 对于不支持直接方法的交易所，根据交易所进行特殊处理
            elif self.exchange_id == 'okx':
                # OKX API特有的获取持仓方法
                try:
                    positions_data = self.exchange.privateGetAccountPositions(params)
                    if 'data' in positions_data:
                        return positions_data['data']
                    return []
                except Exception as e:
                    logger.error(f"获取OKX持仓信息失败: {e}")
                    return None
                    
            else:
                logger.warning(f"交易所 {self.exchange_id} 不支持获取持仓信息")
                return None
                
        except ccxt.ExchangeError as e:
            logger.error(f"获取持仓信息时发生交易所错误: {e}")
            return None
        except Exception as e:
            logger.error(f"获取持仓信息时发生未知错误: {e}")
            return None

    # TODO: 后续需要添加更多方法，如：
    # place_order(symbol, type, side, amount, price=None, params={})
    # cancel_order(id, symbol=None, params={})
    # fetch_order(id, symbol=None, params={})
    # fetch_open_orders(symbol=None, params={})
    # fetch_my_trades(symbol=None, since=None, limit=None, params={})

    def close(self):
        """
        关闭交易所连接 (如果需要)
        """
        logger.info(f"关闭交易所连接: {self.exchange_id}")
        if self.exchange:
            # CCXT 通常不需要显式关闭连接，但这是一个良好的实践
            # 如果使用了 WebSocket，这里需要处理 WebSocket 连接的关闭
            pass



if __name__ == "__main__":
    connector = ExchangeConnector('okx')
    # 测试获取 BTC/USDT 永续合约的行情和资金费率 (注意 symbol 格式)
    # 对于 OKX，BTC/USDT 永续合约结算币种是 USDT，symbol 通常是 'BTC/USDT' 或 'BTC-USDT-SWAP'
    # 建议通过 fetch_markets() 查找正确的 symbol
    # 或者直接查阅 OKX API 文档或 CCXT 文档
    # 经过查阅，OKX V5 API 永续合约 symbol 格式通常是 'BTC-USDT-SWAP'
    okx_perpetual_symbol = 'BTC-USDT-SWAP' # 需要根据实际交易对修改
    ticker = connector.fetch_ticker(okx_perpetual_symbol)
    if ticker:
        print(f"Latest Ticker for {okx_perpetual_symbol}: {ticker}")

    funding_rate = connector.fetch_funding_rate(okx_perpetual_symbol)
    if funding_rate:
         print(f"Funding Rate for {okx_perpetual_symbol}: {funding_rate}")

    balance = connector.fetch_balance()
    if balance:
        # 打印 USDT 的可用余额
        if 'USDT' in balance and 'free' in balance['USDT']:
             print(f"USDT Available Balance: {balance['USDT']['free']}")
        else:
             print("无法获取 USDT 余额信息")

    connector.close()

    