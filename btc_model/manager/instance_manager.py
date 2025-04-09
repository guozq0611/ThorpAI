import threading
from typing import Dict, Any, Type, TypeVar, Optional, Callable

T = TypeVar('T')

class InstanceManager:
    """
    全局实例管理器，用于集中管理应用中的单例实例
    
    用于集中管理和访问应用程序中的单例实例，提供延迟初始化、统一配置和获取实例的能力。  
    """
    
    _instances: Dict[str, Any] = {}
    _factories: Dict[str, Callable[..., Any]] = {}
    _lock = threading.Lock()
    
    @classmethod
    def register(cls, name: str, factory: Callable[..., Any]) -> None:
        """
        注册一个工厂函数，用于创建实例
        
        Args:
            name: 实例的唯一标识名
            factory: 创建实例的工厂函数，接受任意参数并返回实例
        """
        with cls._lock:
            cls._factories[name] = factory
    
    @classmethod
    def get_instance(cls, name: str, *args, **kwargs) -> Any:
        """
        获取指定名称的实例，如果不存在则创建
        
        Args:
            name: 实例的唯一标识名
            *args, **kwargs: 传递给工厂函数的参数
            
        Returns:
            对应名称的单例实例
            
        Raises:
            KeyError: 如果指定名称未注册对应的工厂函数
        """
        # 如果实例已存在，直接返回
        if name in cls._instances:
            return cls._instances[name]
        
        # 如果实例不存在，使用工厂函数创建
        with cls._lock:
            # 双重检查锁定模式，防止多线程问题
            if name in cls._instances:
                return cls._instances[name]
                
            if name not in cls._factories:
                raise KeyError(f"No factory registered for instance: {name}")
                
            instance = cls._factories[name](*args, **kwargs)
            cls._instances[name] = instance
            return instance
    
    @classmethod
    def set_instance(cls, name: str, instance: Any) -> None:
        """
        直接设置一个实例（通常用于测试或特殊情况）
        
        Args:
            name: 实例的唯一标识名
            instance: 要设置的实例
        """
        with cls._lock:
            cls._instances[name] = instance
    
    @classmethod
    def has_instance(cls, name: str) -> bool:
        """
        检查是否存在指定名称的实例
        
        Args:
            name: 实例的唯一标识名
            
        Returns:
            bool: 如果实例存在则返回True，否则返回False
        """
        return name in cls._instances
    
    @classmethod
    def clear_instance(cls, name: Optional[str] = None) -> None:
        """
        清除指定名称的实例或所有实例（通常用于测试）
        
        Args:
            name: 实例的唯一标识名，如果为None则清除所有实例
        """
        with cls._lock:
            if name is None:
                cls._instances.clear()
            elif name in cls._instances:
                del cls._instances[name]

# 导出函数别名，使API更简洁
register_instance = InstanceManager.register
get_instance = InstanceManager.get_instance
set_instance = InstanceManager.set_instance
has_instance = InstanceManager.has_instance
clear_instance = InstanceManager.clear_instance 
