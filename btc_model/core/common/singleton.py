import threading
from typing import TypeVar, Type

T = TypeVar('T')

class Singleton:
    """单例模式基类"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls: Type[T]) -> T:
        """重写 __new__ 方法以实现单例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False  # 添加初始化标记
        return cls._instance

    def __init__(self):
        """确保初始化代码只执行一次"""
        if not self._initialized:
            self._initialize()
            self._initialized = True

    def _initialize(self):
        """子类重写此方法实现具体的初始化逻辑"""
        pass

    @classmethod
    def get_instance(cls: Type[T]) -> T:
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance