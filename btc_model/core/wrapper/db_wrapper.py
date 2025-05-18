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


class DBWrapper:
    __instance = None

    def __init__(self):
        self.db_engine = get_db_engine(DB_DATABASE)

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()

        return cls.__instance
    
    def fetch_result(self, sql: str, params: dict = None):
        with self.db_engine.connect() as conn:
            result = conn.execute(text(sql), params)
            return result.fetchall()
        
    def execute_sql(self, sql: str, params: dict = None):
        with self.db_engine.connect() as conn:
            cursor = conn.execute(text(sql), params)
            conn.commit()
            return cursor.lastrowid

  
