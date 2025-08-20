from abc import ABC, abstractmethod
from typing import Union
import ccxt.pro as ccxtpro
import ccxt
import threading

from btc_model.core.wrapper.db_wrapper import DBWrapper

class PositionManager(ABC):
    """
    仓位管理器
    """
    def __init__(self, 
                 exchange: Union[ccxt.Exchange, ccxtpro.Exchange],
                 db_wrapper: DBWrapper):
        self.exchange = exchange
        self.db_wrapper = db_wrapper

        self.lock = threading.Lock()

    @abstractmethod
    def create_position(self, pair_key, data):
        pass


    def update_position_to_db(self, position_dict: dict):
        with self.lock:
            sql = """
            INSERT INTO position (
                exchange_id,
                symbol_id,
                notional,
                margin_mode,
                liquidation_price,
                entry_price,
                unrealized_pnl,
                realized_pnl,
                pnl_percentage,
                contracts,
                contract_size,
                mark_price,
                side,
                maintenance_margin,
                maintenance_margin_percentage,
                collateral,
                initial_margin,
                initial_margin_percentage,
                leverage,
                margin_ratio
            )
            VALUES (
                :exchange_id,
                :symbol_id,
                :notional,
                :margin_mode,
                :liquidation_price,
                :entry_price,
                :unrealized_pnl,
                :realized_pnl,
                :pnl_percentage,
                :contracts,
                :contract_size,
                :mark_price,
                :side,
                :maintenance_margin,
                :maintenance_margin_percentage,
                :collateral,
                :initial_margin,
                :initial_margin_percentage,
                :leverage,
                :margin_ratio
            )
            ON DUPLICATE KEY UPDATE 
            notional = :notional,
            margin_mode = :margin_mode,
            liquidation_price = :liquidation_price,
            entry_price = :entry_price,
            unrealized_pnl = :unrealized_pnl,
            realized_pnl = :realized_pnl,
            pnl_percentage = :pnl_percentage,
            contracts = :contracts,
            contract_size = :contract_size,
            mark_price = :mark_price,
            side = :side,
            maintenance_margin = :maintenance_margin,
            maintenance_margin_percentage = :maintenance_margin_percentage,
            collateral = :collateral,
            initial_margin = :initial_margin,
            initial_margin_percentage = :initial_margin_percentage,
            leverage = :leverage,
            margin_ratio = :margin_ratio
            """

            params = {
                "exchange_id": position_dict['exchange_id'],
                "symbol_id": position_dict['symbol_id'],
                "notional": position_dict['notional'],
                "margin_mode": position_dict['margin_mode'],
                "liquidation_price": position_dict['liquidation_price'],
                "entry_price": position_dict['entry_price'],
                "unrealized_pnl": position_dict['unrealized_pnl'],
                "realized_pnl": position_dict['realized_pnl'],
                "pnl_percentage": position_dict['pnl_percentage'],
                "contracts": position_dict['contracts'],
                "contract_size": position_dict['contract_size'],
                "mark_price": position_dict['mark_price'],
                "side": position_dict['side'],
                "maintenance_margin": position_dict['maintenance_margin'],
                "maintenance_margin_percentage": position_dict['maintenance_margin_percentage'],
                "collateral": position_dict['collateral'],
                "initial_margin": position_dict['initial_margin'],
                "initial_margin_percentage": position_dict['initial_margin_percentage'],
                "leverage": position_dict['leverage'],
                "margin_ratio": position_dict['margin_ratio']
            }

            self.db_wrapper.execute_sql(sql, params=params)
    