from sqlalchemy import create_engine
from sqlalchemy import text

from btc_model.setting.setting import get_settings

settings = get_settings('database.mysql')

DB_USER = settings['user']
DB_PASSWORD = settings['password']
DB_HOST = settings['host']
DB_PORT = settings['port']
DB_DATABASE = settings['database']

_db_engine = None

def get_db_engine(database_name=''):
    global _db_engine
    if _db_engine is not None:
        return _db_engine

    if database_name is None or database_name == '':
        database_name = DB_DATABASE

    db_link = f'''mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{database_name}'''
    _db_engine = create_engine(db_link, echo=False, max_overflow=10, pool_size=50, pool_reset_on_return=None)
    return _db_engine


class DBUtil:
    def __init__(self):
        self.db_engine = get_db_engine(DB_DATABASE)

    def get_blacklist_symbols(self, exchange_id: str = None, strategy_name: str = None, active: bool = True):
        with self.db_engine.connect() as conn:
            query = """
            SELECT * FROM blacklist_symbols
            WHERE 1 = 1
            """

            if exchange_id:
                query += " AND exchange_id = :exchange_id"

            if strategy_name:
                query += " AND strategy_name = :strategy_name"
            
            if active:
                query += " AND active = :active"

            params = {}
            if exchange_id:
                params['exchange_id'] = exchange_id
            if strategy_name:
                params['strategy_name'] = strategy_name
            if active:
                params['active'] = active

            result = conn.execute(text(query), params)
            return result.fetchall()
        
    def update_blacklist_symbols(
            self, 
            symbol_id: str, 
            exchange_id: str = None, 
            strategy_name: str = None, 
            active: bool = True, 
            reason: str = None
            ):
        with self.db_engine.connect() as conn:
            query = """
            insert into blacklist_symbols (
                symbol_id, 
                exchange_id, 
                strategy_name, 
                active, 
                reason
            ) values (
                :symbol_id, 
                :exchange_id, 
                :strategy_name, 
                :active, 
                :reason
            )on duplicate key update 
                exchange_id = :exchange_id,
                strategy_name = :strategy_name,
                active = :active,
                reason = :reason
            """

            params = {  
                'symbol_id': symbol_id,
                'exchange_id': exchange_id,
                'strategy_name': strategy_name,
                'active': active,
                'reason': reason
            }

            conn.execute(text(query), params)
            conn.commit()


if __name__ == "__main__":
    db_util = DBUtil()
    print(db_util.get_blacklist_symbols(active=True))