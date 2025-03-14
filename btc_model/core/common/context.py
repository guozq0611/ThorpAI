import datetime
import threading


class Context(object):
    """
    策略、指标的上下文
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Context, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __repr__(self):
        items = ("%s = %r" % (k, v)
                 for k, v in self.__dict__.items()
                 if not callable(v) and not k.startswith("_"))
        return "Context({%s})" % (', '.join(items),)

    def __init__(self):
        """初始化上下文"""
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._config = None
        self.market_data_service = None
        self._initialized = True

    @staticmethod
    def get_instance():
        """获取上下文实例"""
        return Context()

    @property
    def now(self):
        """
        """
        return datetime.datetime.now()

