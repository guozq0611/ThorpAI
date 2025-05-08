import time
from typing import Dict, Any
from btc_model.core.util.log_util import Logger
from btc_model.strategy.funding_rate_arbitrage.position_manager import PositionManager
from btc_model.strategy.funding_rate_arbitrage.exchange_connector import ExchangeConnector
from btc_model.strategy.funding_rate_arbitrage.strategy_params import StrategyParams

class ExecutionManager:
    def __init__(self, 
                 exchange_connector: ExchangeConnector, 
                 position_manager: PositionManager, 
                 strategy_params: StrategyParams
                 ):
        """
        初始化交易执行管理器。

        Args:
            exchange_connector: ExchangeConnector 实例。
            position_manager: PositionManager 实例。
            config: 包含执行参数的配置字典。
        """
        self.exchange_connector = exchange_connector
        self.position_manager = position_manager
        self.strategy_params = strategy_params

        # 从配置加载执行参数
        self.spot_td_mode = self.strategy_params.execution_params.spot_td_mode # 现货交易模式 (通常是cash)
        self.swap_td_mode = self.strategy_params.execution_params.swap_td_mode # 永续合约交易模式 (cross 或 isolated)
        self.spot_order_type_open = self.strategy_params.execution_params.spot_order_type_open # 现货开仓订单类型 (market, limit)
        self.swap_order_type_open = self.strategy_params.execution_params.swap_order_type_open # 永续合约开仓订单类型 (market, limit)
        self.spot_order_type_close = self.strategy_params.execution_params.spot_order_type_close # 现货平仓订单类型
        self.swap_order_type_close = self.strategy_params.execution_params.swap_order_type_close # 永续合约平仓订单类型
        # TODO: 添加滑点容忍度、限价单偏移量等参数

        # 用于存储正在处理的订单信息，例如 {client_order_id: {'position_id': ..., 'leg_type': ..., 'order_id': ...}}
        self._pending_orders: Dict[str, Dict[str, Any]] = {}

        Logger.info("Execution Manager initialized.")

        # TODO: 在实际系统中，需要启动一个独立的线程或异步任务来定期查询 _pending_orders 中的订单状态

    def handle_open_instruction(self, instruction: Dict[str, Any]):
        """
        处理来自 Strategy 的开仓指令。

        Args:
            instruction: 包含开仓详情的字典，例如
                         {'position_id': '...', 'inst_id': 'BTC-USDT', 'size_coin': 0.001}
        """
        position_id = instruction.get('position_id')
        inst_id = instruction.get('inst_id') # 例如 'BTC-USDT'
        size_coin = instruction.get('size_coin') # 以币为单位的数量

        if not all([position_id, inst_id, size_coin]) or size_coin <= 0:
            Logger.error(f"Invalid open instruction received: {instruction}")
            # TODO: 触发告警，指令无效
            return

        Logger.info(f"Received open instruction for position {position_id} ({inst_id}, size: {size_coin})")

        # TODO: 在这里需要根据 inst_id 获取对应的永续合约 ID (例如 'BTC-USDT-SWAP')
        # 以及合约乘数 (如果需要将币数量转换为合约张数)
        # 这部分逻辑可能放在 DataProcessor 或一个独立的工具类中更合适
        swap_inst_id = f"{inst_id}-SWAP" # 假设永续合约ID规则
        # contract_multiplier = self._get_contract_multiplier(swap_inst_id) # TODO: 获取合约乘数
        # swap_size_contract = size_coin / contract_multiplier # 将币数量转换为合约张数

        # 确保头寸状态是 OPENING
        position = self.pos_manager.get_position(position_id)
        if position is None or position['status'] != 'OPENING':
             Logger.warning(f"Position {position_id} is not in OPENING state. Skipping open execution.")
             return

        # --- 执行双腿开仓 ---

        # 1. 下达现货买单
        spot_client_order_id = f"{position_id}_spot_buy_{int(time.time())}" # 生成唯一的 clientOrderId
        # 注意：现货交易模式通常是 cash
        spot_order_response = self.api.place_order(
            instId=inst_id, # 现货交易对
            tdMode=self.spot_td_mode,
            side='buy',
            posSide='', # 现货没有持仓方向
            ordType=self.spot_order_type_open,
            sz=str(size_coin), # 数量通常需要是字符串
            # px=... # 如果是 limit order 需要价格
            clientOrdId=spot_client_order_id
        )

        if spot_order_response and spot_order_response['code'] == '0':
            spot_order_info = spot_order_response['data'][0]
            Logger.info(f"Spot buy order placed: {spot_order_info}")
            # 记录订单信息，等待成交
            self._pending_orders[spot_client_order_id] = {
                'position_id': position_id,
                'leg_type': 'spot',
                'order_id': spot_order_info['ordId'],
                'inst_id': inst_id,
                'client_order_id': spot_client_order_id,
                'status': 'live' # 标记为活跃订单
            }
            # TODO: 更新 position_manager 中对应腿的订单ID
            # position['spot_leg']['open_order_id'] = spot_order_info['ordId']
            # position['spot_leg']['client_order_id'] = spot_client_order_id
            # self.pos_manager.save_positions() # 保存状态

        else:
            Logger.error(f"Failed to place spot buy order for {position_id}: {spot_order_response}")
            # TODO: 触发告警：单腿下单失败！
            # TODO: 触发风险处理：需要立即尝试撤销另一腿（如果已下单），或者标记头寸为失败
            self._handle_single_leg_failure(position_id, 'spot_buy')
            return # 如果现货下单失败，停止永续合约下单


        # 2. 下达永续合约卖单 (开空)
        swap_client_order_id = f"{position_id}_swap_short_{int(time.time())}" # 生成唯一的 clientOrderId
        # 注意：永续合约交易模式通常是 cross 或 isolated，持仓方向是 short
        swap_order_response = self.api.place_order(
            instId=swap_inst_id, # 永续合约交易对
            tdMode=self.swap_td_mode,
            side='sell', # 卖出是开空
            posSide='short', # 指定持仓方向为 short
            ordType=self.swap_order_type_open,
            sz=str(size_coin), # 数量通常需要是字符串，以币为单位
            # px=... # 如果是 limit order 需要价格
            clientOrdId=swap_client_order_id
        )

        if swap_order_response and swap_order_response['code'] == '0':
            swap_order_info = swap_order_response['data'][0]
            Logger.info(f"Swap short order placed: {swap_order_info}")
            # 记录订单信息，等待成交
            self._pending_orders[swap_client_order_id] = {
                'position_id': position_id,
                'leg_type': 'swap',
                'order_id': swap_order_info['ordId'],
                'inst_id': swap_inst_id,
                'client_order_id': swap_client_order_id,
                'status': 'live' # 标记为活跃订单
            }
            # TODO: 更新 position_manager 中对应腿的订单ID
            # position['swap_leg']['open_order_id'] = swap_order_info['ordId']
            # position['swap_leg']['client_order_id'] = swap_client_order_id
            # self.pos_manager.save_positions() # 保存状态

        else:
            Logger.error(f"Failed to place swap short order for {position_id}: {swap_order_response}")
            # TODO: 触发告警：单腿下单失败！
            # TODO: 触发风险处理：需要立即尝试撤销另一腿（现货买单），或者标记头寸为失败
            self._handle_single_leg_failure(position_id, 'swap_short')
            # 注意：如果永续合约下单失败，现货买单可能已经成交了，需要紧急处理！

        Logger.info(f"Open order pair initiated for position {position_id}. Monitoring pending orders.")
        # TODO: 启动或确保订单监控任务正在监控这两个订单

    def handle_close_instruction(self, instruction: Dict[str, Any]):
        """
        处理来自 Strategy 的平仓指令。

        Args:
            instruction: 包含平仓详情的字典，例如
                         {'position_id': '...', 'inst_id': 'BTC-USDT'}
        """
        position_id = instruction.get('position_id')
        inst_id = instruction.get('inst_id') # 例如 'BTC-USDT'

        if not all([position_id, inst_id]):
            Logger.error(f"Invalid close instruction received: {instruction}")
            # TODO: 触发告警，指令无效
            return

        Logger.info(f"Received close instruction for position {position_id} ({inst_id})")

        # 获取头寸详情，以便知道要平仓的数量
        position = self.pos_manager.get_position(position_id)
        if position is None or position['status'] != 'CLOSING': # 确保头寸状态是 CLOSING
             Logger.warning(f"Position {position_id} is not in CLOSING state. Skipping close execution.")
             return

        # TODO: 获取需要平仓的精确数量
        # 对于现货，是 spot_leg['current_qty']
        # 对于永续合约，是 swap_leg['current_qty_coin']
        # 需要确保这两个数量是准确的，最好是刚从交易所同步过的
        spot_size_to_close = position['spot_leg']['current_qty'] # TODO: Get actual qty
        swap_size_to_close = position['swap_leg']['current_qty_coin'] # TODO: Get actual qty
        swap_inst_id = f"{inst_id}-SWAP" # 假设永续合约ID规则


        # --- 执行双腿平仓 ---

        # 1. 下达现货卖单
        spot_client_order_id = f"{position_id}_spot_sell_{int(time.time())}" # 生成唯一的 clientOrderId
        if spot_size_to_close > 0:
            spot_order_response = self.api.place_order(
                instId=inst_id, # 现货交易对
                tdMode=self.spot_td_mode,
                side='sell',
                posSide='',
                ordType=self.spot_order_type_close,
                sz=str(spot_size_to_close), # 数量通常需要是字符串
                # px=... # 如果是 limit order 需要价格
                clientOrdId=spot_client_order_id
            )

            if spot_order_response and spot_order_response['code'] == '0':
                spot_order_info = spot_order_response['data'][0]
                Logger.info(f"Spot sell order placed: {spot_order_info}")
                self._pending_orders[spot_client_order_id] = {
                    'position_id': position_id,
                    'leg_type': 'spot',
                    'order_id': spot_order_info['ordId'],
                    'inst_id': inst_id,
                    'client_order_id': spot_client_order_id,
                    'status': 'live'
                }
                # TODO: 更新 position_manager
            else:
                Logger.error(f"Failed to place spot sell order for {position_id}: {spot_order_response}")
                # TODO: 触发告警：单腿平仓失败！
                # TODO: 触发风险处理：需要立即尝试撤销另一腿（如果已下单），或者标记头寸为错误状态
                self._handle_single_leg_failure(position_id, 'spot_sell')
                # 注意：平仓失败比开仓失败更危险，可能导致单边持仓！

        else:
             Logger.warning(f"Spot size to close is zero for position {position_id}. Skipping spot sell order.")


        # 2. 下达永续合约买单 (平空)
        swap_client_order_id = f"{position_id}_swap_buy_close_{int(time.time())}" # 生成唯一的 clientOrderId
        if swap_size_to_close > 0:
            swap_order_response = self.api.place_order(
                instId=swap_inst_id, # 永续合约交易对
                tdMode=self.swap_td_mode,
                side='buy', # 买入是平空
                posSide='short', # 指定平掉 short 仓位
                ordType=self.swap_order_type_close,
                sz=str(swap_size_to_close), # 数量通常需要是字符串，以币为单位
                # px=... # 如果是 limit order 需要价格
                clientOrdId=swap_client_order_id
            )

            if swap_order_response and swap_order_response['code'] == '0':
                swap_order_info = swap_order_response['data'][0]
                Logger.info(f"Swap buy (close short) order placed: {swap_order_info}")
                self._pending_orders[swap_client_order_id] = {
                    'position_id': position_id,
                    'leg_type': 'swap',
                    'order_id': swap_order_info['ordId'],
                    'inst_id': swap_inst_id,
                    'client_order_id': swap_client_order_id,
                    'status': 'live'
                }
                # TODO: 更新 position_manager
            else:
                Logger.error(f"Failed to place swap buy (close short) order for {position_id}: {swap_order_response}")
                # TODO: 触发告警：单腿平仓失败！
                # TODO: 触发风险处理：需要立即尝试撤销另一腿（现货卖单），或者标记头寸为失败
                self._handle_single_leg_failure(position_id, 'swap_buy_close')


        Logger.info(f"Close order pair initiated for position {position_id}. Monitoring pending orders.")
        # TODO: 启动或确保订单监控任务正在监控这两个订单

    def _handle_single_leg_failure(self, position_id: str, failed_leg: str):
        """
        内部方法：处理开仓或平仓时单腿下单失败的情况。
        这是一个非常关键的风险控制点。
        """
        Logger.critical(f"SINGLE LEG ORDER FAILED for position {position_id}, leg: {failed_leg}! Immediate action required!")
        # TODO: 触发高优先级告警！通知人工介入！
        # self.trigger_alert(...) # 需要一个告警机制

        # TODO: 这里的处理逻辑非常重要且复杂，取决于具体情况：
        # 1. 检查另一条腿是否已下单成功。
        # 2. 如果另一条腿已下单成功：
        #    a. 如果是开仓失败：尝试立即撤销已成功下单的那条腿。如果撤销失败，您就有了单边持仓，需要立即告警并可能触发紧急平仓。
        #    b. 如果是平仓失败：您已经有单边持仓了。需要立即告警，并可能尝试重新下单平掉剩余的单边仓位。
        # 3. 如果另一条腿也下单失败（双腿都失败）：记录错误，标记头寸为失败状态，等待人工检查。
        # 4. 更新 position_manager 中头寸的状态为 ERROR 或 FAILED_OPENING/CLOSING。
        # 5. 移除 _pending_orders 中与该头寸相关的订单。

        # For now, just log and trigger alert (placeholder)
        pass # TODO: Implement robust single leg failure handling

    # --- 订单监控和处理 (需要一个独立的运行机制) ---

    def monitor_orders(self):
        """
        (伪代码/概念) 独立的任务，定期查询 _pending_orders 中的订单状态。
        """
        Logger.debug("Monitoring pending orders...")
        orders_to_remove = []
        for client_order_id, order_info in list(self._pending_orders.items()): # 遍历副本
            position_id = order_info['position_id']
            order_id = order_info['order_id']
            inst_id = order_info['inst_id']
            leg_type = order_info['leg_type']

            try:
                # 调用 API 查询订单状态
                latest_order_state = self.api.get_order(instId=inst_id, ordId=order_id)

                if latest_order_state:
                    state = latest_order_state.get('state')
                    Logger.debug(f"Order {order_id} ({client_order_id}) status: {state}")

                    if state == 'filled':
                        Logger.info(f"Order {order_id} ({client_order_id}) FULLY FILLED.")
                        # TODO: 从 latest_order_state 中提取成交详情 (成交数量 accFillSz, 平均成交价 avgPx)
                        fill_details = {
                            'executed_qty': float(latest_order_state.get('accFillSz', 0)),
                            'executed_price': float(latest_order_state.get('avgPx', 0)),
                            # TODO: 其他需要的成交信息
                        }
                        # 通知 PositionManager 更新头寸状态
                        self.pos_manager.update_position_on_order_fill(position_id, leg_type, fill_details)

                        # 检查头寸是否双腿都已成交 (开仓) 或都已平仓 (平仓)
                        # 这需要在 PositionManager 中实现一个方法来检查
                        # if self.pos_manager.is_position_fully_opened(position_id):
                        #      Logger.info(f"Position {position_id} fully OPENED.")
                        #      self.pos_manager.get_position(position_id)['status'] = 'OPENED' # 更新状态
                        #      self.pos_manager.save_positions() # 保存状态
                        #      orders_to_remove.append(client_order_id) # 移除已完成的订单

                        # if self.pos_manager.is_position_fully_closed(position_id):
                        #      Logger.info(f"Position {position_id} fully CLOSED.")
                        #      self.pos_manager.get_position(position_id)['status'] = 'CLOSED' # 更新状态
                        #      # TODO: 计算最终盈亏，记录历史
                        #      self.pos_manager.remove_position(position_id) # 从活跃列表中移除
                        #      orders_to_remove.append(client_order_id) # 移除已完成的订单


                    elif state == 'partially-filled':
                        Logger.info(f"Order {order_id} ({client_order_id}) PARTIALLY FILLED.")
                        # TODO: 从 latest_order_state 中提取部分成交详情 (fillSz, fillPx, accFillSz)
                        fill_details = {
                            'executed_qty': float(latest_order_state.get('accFillSz', 0)), # 当前累计成交数量
                            'executed_price': float(latest_order_state.get('avgPx', 0)), # 当前平均成交价
                            # TODO: 其他需要的成交信息
                        }
                        # 通知 PositionManager 更新头寸的部分成交状态
                        self.pos_manager.update_position_on_order_fill(position_id, leg_type, fill_details)
                        # 订单仍需继续监控

                    elif state in ['canceled', 'failed']:
                        Logger.warning(f"Order {order_id} ({client_order_id}) status: {state}.")
                        # TODO: 触发告警！订单未能完全成交或被取消！
                        # TODO: 触发风险处理：检查对冲状态，可能需要重新下单或紧急平仓
                        self._handle_order_failure(position_id, client_order_id, state)
                        orders_to_remove.append(client_order_id) # 移除失败的订单

                    elif state == 'live':
                        # 订单仍在活跃中，继续监控
                        pass

                    # TODO: 处理其他可能的订单状态

                else:
                    Logger.warning(f"Could not get latest state for order {order_id} ({client_order_id}). API returned None.")
                    # TODO: 触发告警：无法查询订单状态，可能API有问题
                    # TODO: 考虑重试或标记为监控异常

            except Exception as e:
                Logger.error(f"Error monitoring order {order_id} ({client_order_id}): {e}")
                # TODO: 触发告警：订单监控过程中出现错误

        # 移除已处理完成或失败的订单
        for client_order_id in orders_to_remove:
            if client_order_id in self._pending_orders:
                del self._pending_orders[client_order_id]
                Logger.debug(f"Removed processed order {client_order_id} from pending list.")


    def _handle_order_failure(self, position_id: str, client_order_id: str, state: str):
        """
        内部方法：处理订单最终未能完全成交（取消或失败）的情况。
        """
        Logger.critical(f"ORDER FAILURE: Order {client_order_id} for position {position_id} ended in state: {state}!")
        # TODO: 触发高优先级告警！通知人工介入！

        # TODO: 检查该头寸的另一条腿的状态：
        # - 如果另一条腿也失败了：整个开/平仓操作失败，标记头寸为 ERROR。
        # - 如果另一条腿已成交：您现在有单边持仓！需要立即告警，并可能尝试重新下单平掉剩余的单边仓位。
        # - 如果另一条腿还在 live/partially-filled：尝试撤销另一条腿，然后根据情况决定是重试还是标记失败。

        # For now, just log and alert (placeholder)
        pass # TODO: Implement robust order failure handling

    # TODO: 添加其他辅助方法，例如获取合约乘数 _get_contract_multiplier
