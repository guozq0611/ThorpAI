import ccxt
from typing import Dict, Optional, List
from decimal import Decimal
import numpy as np

from btc_model.setting.setting import get_settings
from btc_model.core.common.singleton import Singleton


class CryptoUtil:
    """
    加密货币工具类
    """
    @staticmethod
    def get_crypto_currency_list(exchange: ccxt.Exchange):
        """获取加密货币列表"""
        return exchange.load_markets()

    @staticmethod
    def get_ticker(exchange: ccxt.Exchange, symbol: str):
        """获取加密货币ticker"""
        return exchange.fetch_ticker(symbol)

    @staticmethod
    def get_last_price(exchange: ccxt.Exchange, symbol: str):
        """获取加密货币最新价格"""
        return exchange.fetch_ticker(symbol)['last']

    @staticmethod
    def get_ohlcv(exchange: ccxt.Exchange, symbol: str, timeframe: str = '1d', 
                  since: int = None, limit: int = None) -> List:
        """
        获取K线数据
        
        Args:
            exchange: 交易所实例
            symbol: 交易对
            timeframe: 时间周期
            since: 开始时间戳
            limit: 限制数量
            
        Returns:
            List: K线数据
        """
        try:
            # 处理OKX的永续合约格式
            if exchange.id.lower() == 'okx' and ':USDT' in symbol:
                # 将 'BTC/USDT:USDT' 转换为 'BTC-USDT-SWAP'
                base = symbol.split('/')[0]
                symbol = f'{base}-USDT-SWAP'
            
            # 获取K线数据
            ohlcv = exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                since=since,
                limit=limit
            )
            
            return ohlcv
            
        except Exception as e:
            print(f"获取K线数据失败: {str(e)}")
            return []

    @staticmethod
    def withdraw(
        exchange: ccxt.Exchange,
        currency: str,
        amount: float,
        address: str,
        tag: Optional[str] = None,
        network: Optional[str] = None,
        params: Dict = {}
    ) -> str:
        """
        从交易所提现到外部钱包地址
        
        Args:
            currency: 货币代码 (例如 'BTC', 'ETH', 'USDT')
            amount: 提现金额
            address: 目标钱包地址
            tag: 部分币种需要的标签/备注 (例如 XRP 的 tag)
            network: 网络类型 (例如 'TRX', 'ETH', 'BSC')
            params: 额外参数
            
        Returns:
            str: 提现交易ID
        """
        try:
            # 检查余额
            balance = exchange.fetch_balance()
            available = Decimal(str(balance[currency]['free']))
            amount = Decimal(str(amount))
            
            if available < amount:
                raise ValueError(f"余额不足: 可用 {available} {currency}, 需要 {amount} {currency}")
            
            # 构建提现参数
            withdraw_params = {
                'network': network,
                **params
            }
            
            if tag:
                withdraw_params['tag'] = tag
            
            # 发起提现
            response = exchange.withdraw(
                currency,
                float(amount),
                address,
                params=withdraw_params
            )
            
            return response['id']
            
        except ccxt.ExchangeError as e:
            raise Exception(f"提现失败: {str(e)}")
            
    @staticmethod
    def get_withdraw_status(exchange: ccxt.Exchange, currency: str, withdraw_id: str) -> Dict:
        """
        查询提现状态
        
        Args:
            currency: 货币代码
            withdraw_id: 提现交易ID
            
        Returns:
            Dict: 提现状态信息
        """
        try:
            withdrawals = exchange.fetch_withdrawals(currency)
            for withdrawal in withdrawals:
                if withdrawal['id'] == withdraw_id:
                    return withdrawal
            raise ValueError(f"未找到提现记录: {withdraw_id}")
            
        except ccxt.ExchangeError as e:
            raise Exception(f"查询提现状态失败: {str(e)}")

    @staticmethod
    def get_trading_fees(exchange: ccxt.Exchange) -> Dict:
        """
        获取交易对的交易费率
        考虑交易费率相对固定，用户可以自行设置费率，所以这里直接从设置中获取费率
        Args:
            exchange: 交易所实例
            
        Returns:
            Dict: 费率信息
        """
        try:
            exchange_id = f"cex.{exchange.id.lower()}"
            settings = get_settings(exchange_id)
            
            if 'fees' in settings:
                return {
                    'maker': settings['fees']['spot']['maker'],
                    'taker': settings['fees']['spot']['taker'],
                    'info': settings['fees']
                }
            
            # 如果设置中没有费率信息，使用默认值
            return {
                'maker': 0.001,
                'taker': 0.001,
                'info': {
                    'spot': {'maker': 0.001, 'taker': 0.001},
                    'swap': {'maker': 0.0002, 'taker': 0.0005}
                }
            }
            
        except Exception as e:
            raise Exception(f"获取费率失败: {str(e)}")
            
    @staticmethod
    def get_withdrawal_fees(exchange: ccxt.Exchange, currencies: List[str] = None) -> Dict:
        """
        获取提现手续费费率
        
        Args:
            exchange: ccxt交易所实例
            currencies: 币种列表，如 ['BTC', 'ETH', 'USDT']。如果为None则获取所有支持的币种
            
        Returns:
            Dict: {
                'BTC': {'fee': 0.0005, 'networks': {'BTC': 0.0005, 'BSC': 0.0001}},
                'USDT': {'fee': 1, 'networks': {'TRX': 1, 'ETH': 5, 'BSC': 0.1}}
            }
        """
        try:
            # 对于OKX，使用专门的API
            if exchange.id.lower() == 'okx':
                result = {}
                
                # 获取币种信息
                response = exchange.privateGetAssetCurrencies({
                    'ccy': ','.join(currencies) if currencies else None
                })
                
                if response['code'] == '0' and response['data']:
                    for currency_info in response['data']:
                        ccy = currency_info['ccy']
                        networks = {}
                        
                        # 处理每个链的提现信息
                        for chain in currency_info.get('chains', []):
                            network = chain.get('chain', '')
                            fee = float(chain.get('minFee', '0'))
                            if network and fee is not None:
                                networks[network] = fee
                        
                        # 如果没有具体的链信息，使用默认费率
                        if not networks and 'minFee' in currency_info:
                            networks['default'] = float(currency_info['minFee'])
                        
                        result[ccy] = {
                            'fee': min(networks.values()) if networks else 0,
                            'networks': networks
                        }
                
                return result
            
            # 对于其他交易所
            if not hasattr(exchange, 'fetch_currencies'):
                raise Exception(f"{exchange.id} 不支持获取币种信息")
                
            all_currencies = exchange.fetch_currencies()
            
            if not all_currencies:
                raise Exception("获取币种信息失败")
                
            result = {}
            target_currencies = currencies if currencies else all_currencies.keys()
            
            for currency in target_currencies:
                if currency in all_currencies:
                    currency_info = all_currencies[currency]
                    networks = {}
                    
                    # 处理不同网络的提现费用
                    if 'networks' in currency_info:
                        for network_id, network_info in currency_info['networks'].items():
                            if 'fee' in network_info:
                                networks[network_id] = network_info['fee']
                    
                    # 如果没有网络信息，使用默认费率
                    if not networks and 'fee' in currency_info:
                        networks['default'] = currency_info['fee']
                    
                    result[currency] = {
                        'fee': min(networks.values()) if networks else 0,
                        'networks': networks
                    }
            
            return result
            
        except Exception as e:
            raise Exception(f"获取提现费率失败: {str(e)}")

    @staticmethod
    def get_trading_limits(exchange: ccxt.Exchange, symbol: str) -> Dict:
        """
        获取交易对的最小交易数量和金额限制
        
        Args:
            exchange: ccxt交易所实例
            symbol: 交易对，如 'BTC/USDT'
            
        Returns:
            Dict: {
                'amount': {
                    'min': 最小交易数量,
                    'max': 最大交易数量(如果有),
                    'precision': 数量精度
                },
                'price': {
                    'min': 最小价格,
                    'max': 最大价格(如果有),
                    'precision': 价格精度
                },
                'cost': {
                    'min': 最小交易金额,
                    'max': 最大交易金额(如果有)
                }
            }
        """
        try:
            # 加载市场信息
            market = exchange.load_markets()[symbol]
            
            limits = {
                'amount': {
                    'min': market['limits']['amount']['min'] if 'amount' in market['limits'] else None,
                    'max': market['limits']['amount']['max'] if 'amount' in market['limits'] else None,
                    'precision': market['precision']['amount']
                },
                'price': {
                    'min': market['limits']['price']['min'] if 'price' in market['limits'] else None,
                    'max': market['limits']['price']['max'] if 'price' in market['limits'] else None,
                    'precision': market['precision']['price']
                },
                'cost': {
                    'min': market['limits']['cost']['min'] if 'cost' in market['limits'] else None,
                    'max': market['limits']['cost']['max'] if 'cost' in market['limits'] else None
                }
            }
            
            return limits
            
        except ccxt.ExchangeError as e:
            raise Exception(f"获取交易限制失败: {str(e)}")
        except KeyError as e:
            raise Exception(f"交易对 {symbol} 不存在或数据结构异常: {str(e)}")
            
    @staticmethod
    def validate_order(exchange: ccxt.Exchange, symbol: str, amount: float, price: float = None) -> bool:
        """
        验证订单是否满足最小交易限制
        
        Args:
            exchange: ccxt交易所实例
            symbol: 交易对
            amount: 交易数量
            price: 交易价格（市价单可不传）
            
        Returns:
            bool: 是否满足限制
        """
        try:
            limits = CryptoUtil.get_trading_limits(exchange, symbol)
            
            # 检查数量限制
            if limits['amount']['min'] and amount < limits['amount']['min']:
                raise ValueError(f"交易数量 {amount} 小于最小限制 {limits['amount']['min']}")
                
            if limits['amount']['max'] and amount > limits['amount']['max']:
                raise ValueError(f"交易数量 {amount} 大于最大限制 {limits['amount']['max']}")
            
            # 如果是限价单，检查价格和金额限制
            if price is not None:
                cost = amount * price
                
                if limits['cost']['min'] and cost < limits['cost']['min']:
                    raise ValueError(f"交易金额 {cost} 小于最小限制 {limits['cost']['min']}")
                    
                if limits['cost']['max'] and cost > limits['cost']['max']:
                    raise ValueError(f"交易金额 {cost} 大于最大限制 {limits['cost']['max']}")
                    
                if limits['price']['min'] and price < limits['price']['min']:
                    raise ValueError(f"交易价格 {price} 小于最小限制 {limits['price']['min']}")
                    
                if limits['price']['max'] and price > limits['price']['max']:
                    raise ValueError(f"交易价格 {price} 大于最大限制 {limits['price']['max']}")
            
            return True
            
        except Exception as e:
            raise Exception(f"验证订单失败: {str(e)}")

    @staticmethod
    def get_price_tick(exchange: ccxt.Exchange, symbol: str) -> Dict:
        """
        获取交易对的价格跳点信息
        
        Args:
            exchange: ccxt交易所实例
            symbol: 交易对，如 'BTC/USDT'
            
        Returns:
            Dict: {
                'tick_size': 价格最小变动单位,
                'precision': 价格精度,
                'example': {
                    'valid_price': 有效价格示例,
                    'invalid_price': 无效价格示例
                }
            }
        """
        try:
            market = exchange.load_markets()[symbol]
            
            # 获取价格精度
            precision = market['precision']['price']
            
            # 计算最小价格变动单位
            tick_size = 1 / (10 ** precision) if isinstance(precision, int) else precision
            
            # 生成示例价格
            current_price = exchange.fetch_ticker(symbol)['last']
            valid_price = round(current_price / tick_size) * tick_size
            invalid_price = valid_price + (tick_size * 0.5)  # 故意生成无效价格
            
            return {
                'tick_size': tick_size,
                'precision': precision,
                'example': {
                    'valid_price': valid_price,
                    'invalid_price': invalid_price
                }
            }
            
        except ccxt.ExchangeError as e:
            raise Exception(f"获取价格跳点失败: {str(e)}")
            
    @staticmethod
    def format_price(exchange: ccxt.Exchange, symbol: str, price: float) -> float:
        """
        将价格格式化为符合跳点要求的有效价格
        
        Args:
            exchange: ccxt交易所实例
            symbol: 交易对
            price: 原始价格
            
        Returns:
            float: 格式化后的价格
        """
        try:
            tick_info = CryptoUtil.get_price_tick(exchange, symbol)
            tick_size = tick_info['tick_size']
            
            # 将价格调整到最近的有效价格
            valid_price = round(price / tick_size) * tick_size
            
            # 根据精度格式化
            if isinstance(tick_info['precision'], int):
                valid_price = round(valid_price, tick_info['precision'])
                
            return valid_price
            
        except Exception as e:
            raise Exception(f"价格格式化失败: {str(e)}")

    @staticmethod
    def get_perpetual_markets(exchange: ccxt.Exchange) -> Dict:
        """
        获取交易所的永续合约列表
        
        Args:
            exchange: ccxt交易所实例
            
        Returns:
            Dict: {
                'BTC/USDT:USDT': {
                    'symbol': 合约符号,
                    'base': 基础货币,
                    'quote': 计价货币,
                    'settle': 结算货币,
                    'leverage': {
                        'max': 最大杠杆,
                        'min': 最小杠杆
                    },
                    'margin_mode': ['isolated', 'cross'],  # 支持的保证金模式
                    'fees': {
                        'maker': maker费率,
                        'taker': taker费率,
                        'funding': {
                            'rate': 当前资金费率,
                            'next_time': 下次收取时间
                        }
                    },
                    'maintenance_margin': 维持保证金率,
                    'initial_margin': 初始保证金率,
                    'contract_size': 合约面值,
                    'precision': {
                        'price': 价格精度,
                        'amount': 数量精度
                    }
                }
            }
        """
        try:
            markets = exchange.load_markets()
            perpetual_markets = {}
            
            for symbol, market in markets.items():
                # 筛选永续合约
                if market.get('swap') and market.get('linear'):
                    market_info = {
                        'symbol': symbol,
                        'base': market['base'],
                        'quote': market['quote'],
                        'settle': market.get('settle'),
                        'leverage': {
                            'max': market.get('limits', {}).get('leverage', {}).get('max'),
                            'min': market.get('limits', {}).get('leverage', {}).get('min', 1)
                        },
                        'margin_mode': market.get('margin_modes', ['isolated', 'cross']),
                        'fees': {
                            'maker': market.get('maker'),
                            'taker': market.get('taker'),
                        },
                        'maintenance_margin': market.get('maintenance_margin_rate'),
                        'initial_margin': market.get('initial_margin_rate'),
                        'contract_size': market.get('contractSize', 1),
                        'precision': {
                            'price': market['precision']['price'],
                            'amount': market['precision']['amount']
                        }
                    }
                    perpetual_markets[symbol] = market_info
                    
            return perpetual_markets
            
        except ccxt.ExchangeError as e:
            raise Exception(f"获取永续合约列表失败: {str(e)}")
            
    @staticmethod
    def get_funding_rate(exchange: ccxt.Exchange, symbol: str) -> Dict:
        """
        获取合约的资金费率信息
        """
        try:
            if hasattr(exchange, 'fetch_funding_rate'):
                funding_info = exchange.fetch_funding_rate(symbol)
                return {
                    'rate': funding_info.get('fundingRate'),
                    'next_time': funding_info.get('nextFundingTime')
                }
            return {}
        except:
            return {}
            
    @staticmethod
    def get_position_risk(exchange: ccxt.Exchange, symbol: str, 
                         leverage: float, margin_mode: str = 'isolated') -> Dict:
        """
        计算合约仓位风险
        
        Args:
            exchange: ccxt交易所实例
            symbol: 合约符号
            leverage: 杠杆倍数
            margin_mode: 保证金模式 ('isolated' 或 'cross')
            
        Returns:
            Dict: {
                'max_position': 最大可开仓位,
                'liquidation_price': 预估强平价格,
                'margin_ratio': 保证金率,
                'maintenance_amount': 维持保证金,
                'initial_amount': 初始保证金
            }
        """
        try:
            market = exchange.load_markets()[symbol]
            ticker = exchange.fetch_ticker(symbol)
            
            if not market.get('future'):
                raise ValueError(f"{symbol} 不是合约交易对")
                
            # 获取保证金率
            maintenance_margin = market.get('maintenance_margin_rate', 0.005)  # 默认0.5%
            initial_margin = market.get('initial_margin_rate', 1/leverage)
            
            # 获取合约面值
            contract_size = market.get('contractSize', 1)
            
            # 获取账户余额
            balance = exchange.fetch_balance()
            free_margin = float(balance.get('free', {}).get(market['quote'], 0))
            
            # 计算最大可开仓位
            max_position = (free_margin * leverage) / (ticker['last'] * contract_size)
            
            # 计算其他风险指标
            risk_info = {
                'max_position': max_position,
                'liquidation_price': None,  # 需要根据具体仓位计算
                'margin_ratio': 1/leverage,
                'maintenance_amount': maintenance_margin * free_margin,
                'initial_amount': initial_margin * free_margin
            }
            
            return risk_info
            
        except Exception as e:
            raise Exception(f"计算仓位风险失败: {str(e)}")

    @staticmethod
    def compare_currency_info(exchange_a: ccxt.Exchange, exchange_b: ccxt.Exchange) -> Dict:
        """
        比较两个交易所的币种信息，找出同名但可能不同的币种
        
        Args:
            exchange_a: 第一个交易所实例
            exchange_b: 第二个交易所实例
            
        Returns:
            Dict: {
                'suspicious_pairs': [  # 可疑的同名不同币
                    {
                        'symbol': 币种符号,
                        'exchange_a': {
                            'name': 交易所A中的名称,
                            'network': 支持的网络,
                            'contract': 合约地址
                        },
                        'exchange_b': {
                            'name': 交易所B中的名称,
                            'network': 支持的网络,
                            'contract': 合约地址
                        }
                    }
                ],
                'network_mismatch': [  # 网络支持不同的币种
                    {
                        'symbol': 币种符号,
                        'exchange_a_networks': [网络列表],
                        'exchange_b_networks': [网络列表]
                    }
                ]
            }
        """
        try:
            # 获取两个交易所的币种信息
            currencies_a = exchange_a.fetch_currencies()
            currencies_b = exchange_b.fetch_currencies()
            
            # 找出两个交易所都支持的币种
            common_symbols = set(currencies_a.keys()) & set(currencies_b.keys())
            
            suspicious_pairs = []
            network_mismatch = []
            
            for symbol in common_symbols:
                currency_a = currencies_a[symbol]
                currency_b = currencies_b[symbol]
                
                # 获取币种在两个交易所的网络信息
                networks_a = CryptoUtil._get_currency_networks(currency_a)
                networks_b = CryptoUtil._get_currency_networks(currency_b)
                
                # 检查网络支持是否不同
                if networks_a != networks_b:
                    network_mismatch.append({
                        'symbol': symbol,
                        'exchange_a_networks': networks_a,
                        'exchange_b_networks': networks_b
                    })
                
                # 检查可疑的同名不同币
                if CryptoUtil._is_suspicious_currency(currency_a, currency_b, networks_a, networks_b):
                    suspicious_pairs.append({
                        'symbol': symbol,
                        'exchange_a': {
                            'name': currency_a.get('name'),
                            'network': networks_a,
                            'contract': CryptoUtil._get_contract_addresses(currency_a)
                        },
                        'exchange_b': {
                            'name': currency_b.get('name'),
                            'network': networks_b,
                            'contract': CryptoUtil._get_contract_addresses(currency_b)
                        }
                    })
            
            return {
                'suspicious_pairs': suspicious_pairs,
                'network_mismatch': network_mismatch
            }
            
        except ccxt.ExchangeError as e:
            raise Exception(f"比较币种信息失败: {str(e)}")
            
    def _get_currency_networks(self, currency_info: Dict) -> List[str]:
        """获取币种支持的网络列表"""
        networks = []
        
        # 从networks字段获取
        if 'networks' in currency_info:
            networks.extend(currency_info['networks'].keys())
            
        # 从info字段获取（某些交易所使用不同的结构）
        if 'info' in currency_info:
            info = currency_info['info']
            if 'chains' in info:
                networks.extend(info['chains'])
            elif 'network' in info:
                networks.append(info['network'])
                
        return sorted(list(set(networks)))  # 去重并排序
        
    def _get_contract_addresses(self, currency_info: Dict) -> Dict[str, str]:
        """获取币种在各个网络上的合约地址"""
        contracts = {}
        
        # 从networks字段获取
        if 'networks' in currency_info:
            for network, info in currency_info['networks'].items():
                if 'contract' in info:
                    contracts[network] = info['contract']
                    
        # 从info字段获取
        if 'info' in currency_info:
            info = currency_info['info']
            if 'contracts' in info:
                for contract in info['contracts']:
                    network = contract.get('network')
                    address = contract.get('address')
                    if network and address:
                        contracts[network] = address
                        
        return contracts
        
    def _is_suspicious_currency(self, currency_a: Dict, currency_b: Dict, 
                              networks_a: List[str], networks_b: List[str]) -> bool:
        """判断是否为可疑的同名不同币"""
        # 检查合约地址
        contracts_a = self._get_contract_addresses(currency_a)
        contracts_b = self._get_contract_addresses(currency_b)
        
        # 如果两个交易所都提供了合约地址，但地址不同
        common_networks = set(contracts_a.keys()) & set(contracts_b.keys())
        if common_networks:
            for network in common_networks:
                if contracts_a[network] != contracts_b[network]:
                    return True
                    
        # 检查币种名称（如果有）
        name_a = currency_a.get('name', '').lower()
        name_b = currency_b.get('name', '').lower()
        if name_a and name_b and name_a != name_b:
            return True
            
        # 检查网络支持差异是否过大
        if len(set(networks_a) ^ set(networks_b)) > len(set(networks_a) & set(networks_b)):
            return True
            
        return False
        
    @staticmethod
    def analyze_currency_risk(exchange_a: ccxt.Exchange, exchange_b: ccxt.Exchange, 
                            symbol: str, timeframe: str = '1d', limit: int = 30) -> Dict:
        """
        分析两个交易所同名币种的风险等级
        
        Args:
            exchange_a: 第一个交易所实例
            exchange_b: 第二个交易所实例
            symbol: 交易对，如 'BTC/USDT'
            timeframe: K线周期，如 '1d', '4h', '1h'
            limit: 获取多少根K线
            
        Returns:
            Dict: {
                'risk_level': 风险等级 (1-5, 5最高),
                'risk_factors': {
                    'price_deviation': 价格偏离度,
                    'volume_deviation': 成交量偏离度,
                    'correlation': 价格相关性,
                    'network_risk': 网络风险分数,
                    'contract_risk': 合约地址风险分数
                },
                'price_analysis': {
                    'max_spread': 最大价差,
                    'avg_spread': 平均价差,
                    'volatility_diff': 波动率差异
                },
                'recommendations': [风险提示和建议]
            }
        """
        try:
            risk_factors = {}
            recommendations = []
            
            # 1. 获取历史K线数据
            ohlcv_a = exchange_a.fetch_ohlcv(symbol, timeframe, limit=limit)
            ohlcv_b = exchange_b.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # 2. 分析价格差异
            price_analysis = CryptoUtil._analyze_price_difference(ohlcv_a, ohlcv_b)
            risk_factors['price_deviation'] = price_analysis['risk_score']
            
            if price_analysis['risk_score'] > 0.7:
                recommendations.append(f"警告: 交易所间价格差异显著 (偏离度: {price_analysis['max_spread']:.2%})")
            
            # 3. 分析成交量差异
            volume_analysis = CryptoUtil._analyze_volume_difference(ohlcv_a, ohlcv_b)
            risk_factors['volume_deviation'] = volume_analysis['risk_score']
            
            if volume_analysis['risk_score'] > 0.7:
                recommendations.append("警告: 交易所间成交量差异过大，可能存在流动性风险")
            
            # 4. 分析网络支持情况
            currency_info = CryptoUtil.compare_currency_info(exchange_a, exchange_b)
            network_risk = CryptoUtil._analyze_network_risk(currency_info, symbol)
            risk_factors['network_risk'] = network_risk['risk_score']
            
            if network_risk['risk_score'] > 0.5:
                recommendations.append(f"注意: {network_risk['warning']}")
            
            # 5. 计算综合风险等级
            risk_level = CryptoUtil._calculate_risk_level(risk_factors)
            
            return {
                'risk_level': risk_level,
                'risk_factors': risk_factors,
                'price_analysis': price_analysis,
                'recommendations': recommendations
            }
            
        except Exception as e:
            raise Exception(f"风险分析失败: {str(e)}")
            
    @staticmethod
    def _analyze_price_difference(ohlcv_a: List, ohlcv_b: List) -> Dict:
        """分析价格差异"""
        # 提取收盘价
        prices_a = np.array([x[4] for x in ohlcv_a])
        prices_b = np.array([x[4] for x in ohlcv_b])
        
        # 计算价差
        spreads = np.abs(prices_a - prices_b) / prices_a
        
        # 计算相关性
        correlation = np.corrcoef(prices_a, prices_b)[0, 1]
        
        # 计算波动率差异
        volatility_a = np.std(np.diff(prices_a) / prices_a[:-1])
        volatility_b = np.std(np.diff(prices_b) / prices_b[:-1])
        
        return {
            'max_spread': float(np.max(spreads)),
            'avg_spread': float(np.mean(spreads)),
            'correlation': float(correlation),
            'volatility_diff': abs(volatility_a - volatility_b),
            'risk_score': float(
                0.4 * np.max(spreads) +
                0.3 * (1 - correlation) +
                0.3 * abs(volatility_a - volatility_b)
            )
        }
        
    @staticmethod
    def _analyze_volume_difference(ohlcv_a: List, ohlcv_b: List) -> Dict:
        """分析成交量差异"""
        # 提取成交量
        volume_a = np.array([x[5] for x in ohlcv_a])
        volume_b = np.array([x[5] for x in ohlcv_b])
        
        # 计算成交量比例差异
        volume_ratio = np.abs(volume_a - volume_b) / np.maximum(volume_a, volume_b)
        
        return {
            'max_diff_ratio': float(np.max(volume_ratio)),
            'avg_diff_ratio': float(np.mean(volume_ratio)),
            'risk_score': float(np.mean(volume_ratio))
        }
        
    def _analyze_network_risk(self, currency_info: Dict, symbol: str) -> Dict:
        """分析网络支持风险"""
        base_currency = symbol.split('/')[0]
        
        # 检查是否在可疑列表中
        is_suspicious = any(
            pair['symbol'] == base_currency 
            for pair in currency_info['suspicious_pairs']
        )
        
        # 检查网络支持差异
        network_mismatch = next(
            (item for item in currency_info['network_mismatch'] 
             if item['symbol'] == base_currency),
            None
        )
        
        risk_score = 0
        warning = []
        
        if is_suspicious:
            risk_score += 0.6
            warning.append("币种在不同交易所可能为不同代币")
            
        if network_mismatch:
            common_networks = set(network_mismatch['exchange_a_networks']) & \
                            set(network_mismatch['exchange_b_networks'])
            if not common_networks:
                risk_score += 0.4
                warning.append("交易所间无共同支持的网络")
            elif len(common_networks) == 1:
                risk_score += 0.2
                warning.append("仅有一个共同支持的网络")
                
        return {
            'risk_score': risk_score,
            'warning': '; '.join(warning) if warning else "网络风险较低"
        }
        
    def _calculate_risk_level(self, risk_factors: Dict) -> int:
        """计算综合风险等级 (1-5)"""
        # 权重设置
        weights = {
            'price_deviation': 0.4,
            'volume_deviation': 0.3,
            'network_risk': 0.3
        }
        
        # 计算加权风险分数
        risk_score = sum(
            risk_factors[factor] * weight
            for factor, weight in weights.items()
            if factor in risk_factors
        )
        
        # 映射到1-5的风险等级
        if risk_score < 0.2:
            return 1
        elif risk_score < 0.4:
            return 2
        elif risk_score < 0.6:
            return 3
        elif risk_score < 0.8:
            return 4
        else:
            return 5
        
    @staticmethod
    def analyze_funding_history(exchange: ccxt.Exchange, symbol: str, 
                              limit: int = 30) -> Dict:
        """
        分析合约历史资金费率
        
        Args:
            exchange: 交易所实例
            symbol: 合约交易对
            limit: 获取的历史数据数量
            
        Returns:
            Dict: {
                'current_rate': 当前资金费率,
                'avg_rate': 平均资金费率,
                'max_rate': 最高资金费率,
                'min_rate': 最低资金费率,
                'volatility': 费率波动性,
                'trend': 费率趋势 ('up', 'down', 'stable'),
                'risk_score': 风险评分 (0-1)
            }
        """
        try:
            if not hasattr(exchange, 'fetch_funding_rate_history'):
                raise ccxt.NotSupported(f"{exchange.id} 不支持获取历史资金费率")
                
            # 获取历史资金费率
            history = exchange.fetch_funding_rate_history(symbol, limit=limit)
            
            if not history:
                return {
                    'current_rate': None,
                    'avg_rate': None,
                    'max_rate': None,
                    'min_rate': None,
                    'volatility': None,
                    'trend': 'unknown',
                    'risk_score': 1.0  # 无数据视为高风险
                }
                
            # 提取费率数据
            rates = [x['fundingRate'] for x in history if x['fundingRate'] is not None]
            rates = np.array(rates)
            
            # 计算统计指标
            current_rate = rates[-1] if len(rates) > 0 else None
            avg_rate = np.mean(rates)
            max_rate = np.max(rates)
            min_rate = np.min(rates)
            volatility = np.std(rates)
            
            # 判断趋势
            if len(rates) >= 3:
                recent_trend = np.polyfit(range(len(rates[-3:])), rates[-3:], 1)[0]
                trend = 'up' if recent_trend > 0.0001 else 'down' if recent_trend < -0.0001 else 'stable'
            else:
                trend = 'unknown'
                
            # 计算风险分数
            risk_score = min(1.0, (
                0.4 * abs(current_rate) / 0.01 +  # 当前费率（基准0.01）
                0.3 * volatility / 0.005 +        # 波动性（基准0.005）
                0.3 * (1 if trend == 'up' else 0.5 if trend == 'stable' else 0)  # 趋势
            ))
            
            return {
                'current_rate': float(current_rate),
                'avg_rate': float(avg_rate),
                'max_rate': float(max_rate),
                'min_rate': float(min_rate),
                'volatility': float(volatility),
                'trend': trend,
                'risk_score': float(risk_score)
            }
            
        except Exception as e:
            raise Exception(f"分析资金费率失败: {str(e)}")
            
    @staticmethod
    def analyze_market_depth(exchange: ccxt.Exchange, symbol: str, 
                           depth: int = 20) -> Dict:
        """
        分析市场深度和流动性
        
        Args:
            exchange: 交易所实例
            symbol: 交易对
            depth: 订单簿深度
            
        Returns:
            Dict: {
                'spread': 买卖价差,
                'bid_volume': 买单总量,
                'ask_volume': 卖单总量,
                'bid_depth': 买单深度分布,
                'ask_depth': 卖单深度分布,
                'liquidity_score': 流动性评分 (0-1),
                'slippage': {
                    'buy': 买入滑点估计,
                    'sell': 卖出滑点估计
                }
            }
        """
        try:
            orderbook = exchange.fetch_order_book(symbol, depth)
            
            bids = np.array(orderbook['bids'])
            asks = np.array(orderbook['asks'])
            
            # 计算基本指标
            spread = (asks[0][0] - bids[0][0]) / bids[0][0]
            bid_volume = np.sum(bids[:, 1])
            ask_volume = np.sum(asks[:, 1])
            
            # 计算深度分布
            bid_depths = np.cumsum(bids[:, 1])
            ask_depths = np.cumsum(asks[:, 1])
            
            # 估算滑点
            target_volume = min(bid_volume, ask_volume) * 0.1  # 以10%的深度为基准
            buy_slippage = CryptoUtil._estimate_slippage(asks, target_volume, 'buy')
            sell_slippage = CryptoUtil._estimate_slippage(bids, target_volume, 'sell')
            
            # 计算流动性评分
            liquidity_score = 1 - min(1.0, (
                0.4 * spread / 0.001 +           # 价差（基准0.1%）
                0.3 * (1 - min(1, bid_volume / ask_volume if bid_volume < ask_volume else ask_volume / bid_volume)) +
                0.3 * (buy_slippage + sell_slippage) / 2 / 0.001  # 滑点（基准0.1%）
            ))
            
            return {
                'spread': float(spread),
                'bid_volume': float(bid_volume),
                'ask_volume': float(ask_volume),
                'bid_depth': bid_depths.tolist(),
                'ask_depth': ask_depths.tolist(),
                'liquidity_score': float(liquidity_score),
                'slippage': {
                    'buy': float(buy_slippage),
                    'sell': float(sell_slippage)
                }
            }
            
        except Exception as e:
            raise Exception(f"分析市场深度失败: {str(e)}")
            
    @staticmethod
    def _estimate_slippage(orders: np.ndarray, target_volume: float, 
                          side: str) -> float:
        """估算滑点"""
        cumulative_volume = 0
        weighted_price = 0
        base_price = orders[0][0]
        
        for price, volume in orders:
            if cumulative_volume >= target_volume:
                break
            fill_volume = min(volume, target_volume - cumulative_volume)
            weighted_price += price * fill_volume
            cumulative_volume += fill_volume
            
        avg_price = weighted_price / cumulative_volume if cumulative_volume > 0 else base_price
        return abs(avg_price - base_price) / base_price
        
    @staticmethod
    def get_exchange_reputation(exchange_id: str) -> Dict:
        """
        获取交易所信誉度评分
        
        Args:
            exchange_id: 交易所ID
            
        Returns:
            Dict: {
                'score': 综合评分 (0-1),
                'factors': {
                    'age': 运营时间评分,
                    'volume': 交易量评分,
                    'regulation': 监管评分,
                    'security': 安全评分
                },
                'risk_level': 风险等级 (1-5)
            }
        """
        # 交易所基础信息（可以扩展为从API或数据库获取）
        exchange_info = {
            'binance': {
                'age': 2017,  # 成立年份
                'volume_rank': 1,  # 交易量排名
                'regulation': ['US', 'UK', 'JP'],  # 持牌地区
                'security_incidents': 0  # 安全事故数
            },
            'okx': {
                'age': 2017,
                'volume_rank': 3,
                'regulation': ['HK', 'UAE'],
                'security_incidents': 1
            }
            # 可以添加更多交易所
        }
        
        if exchange_id not in exchange_info:
            return {
                'score': 0.5,  # 默认中等信誉度
                'factors': {
                    'age': 0.5,
                    'volume': 0.5,
                    'regulation': 0.5,
                    'security': 0.5
                },
                'risk_level': 3
            }
            
        info = exchange_info[exchange_id]
        current_year = 2024
        
        # 计算各因素得分
        age_score = min(1.0, (current_year - info['age']) / 5)  # 5年满分
        volume_score = 1.0 - (info['volume_rank'] - 1) * 0.1  # 排名越高分越高
        regulation_score = min(1.0, len(info['regulation']) * 0.2)  # 每个牌照0.2分
        security_score = 1.0 - min(1.0, info['security_incidents'] * 0.3)  # 每次事故扣0.3分
        
        # 计算综合得分
        total_score = (
            0.3 * age_score +
            0.3 * volume_score +
            0.2 * regulation_score +
            0.2 * security_score
        )
        
        # 计算风险等级
        risk_level = 6 - int(total_score * 5 + 0.5)  # 转换为1-5的风险等级
        
        return {
            'score': float(total_score),
            'factors': {
                'age': float(age_score),
                'volume': float(volume_score),
                'regulation': float(regulation_score),
                'security': float(security_score)
            },
            'risk_level': risk_level
        }
        
    @staticmethod
    def convert_symbol_to_contract(exchange: ccxt.Exchange, symbol: str) -> str:
        """
        将现货交易对转换为对应的永续合约符号
        
        Args:
            exchange: 交易所实例
            symbol: 原始交易对 (例如: 'LSK/USDT')
            
        Returns:
            str: 永续合约符号
        """
        if exchange.id.lower() == 'okx':
            # OKX格式: 'LSK/USDT' -> 'LSK/USDT:USDT'
            base, quote = symbol.split('/')
            return f'{base}/{quote}:{quote}'
        elif exchange.id.lower() == 'binance':
            # Binance格式: 'LSK/USDT' -> 'LSKUSDT'
            return symbol.replace('/', '')
        else:
            return symbol