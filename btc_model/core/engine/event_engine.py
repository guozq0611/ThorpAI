"""
事件引擎模块，用于处理交易系统中的各种事件
"""

from collections import defaultdict
from queue import Queue, Empty
from threading import Thread
from time import sleep
from typing import Any, Callable, List

class Event:
    """
    事件对象，包含事件类型和数据
    """
    
    def __init__(self, type: str, data: Any = None):
        """
        初始化事件对象
        
        Args:
            type: 事件类型
            data: 事件数据
        """
        self.type = type
        self.data = data


class EventEngine:
    """
    事件引擎，用于事件的处理和分发
    """
    
    def __init__(self, interval: float = 0.1):
        """
        初始化事件引擎
        
        Args:
            interval: 事件处理间隔（秒）
        """
        self._interval = interval
        self._queue = Queue()
        self._active = False
        self._thread = Thread(target=self._run)
        self._handlers = defaultdict(list)
        self._general_handlers = []
    
    def _run(self):
        """
        引擎运行主循环
        """
        while self._active:
            try:
                event = self._queue.get(block=True, timeout=self._interval)
                self._process(event)
            except Empty:
                pass
    
    def _process(self, event: Event):
        """
        处理事件
        """
        # 处理特定类型的事件处理函数
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"处理事件时发生错误: {e}")
        
        # 处理通用事件处理函数
        for handler in self._general_handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"处理事件时发生错误: {e}")
    
    def start(self):
        """
        启动事件引擎
        """
        self._active = True
        self._thread.start()
    
    def stop(self):
        """
        停止事件引擎
        """
        self._active = False
        self._thread.join()
    
    def register(self, type: str, handler: Callable[[Event], None]):
        """
        注册事件处理函数
        
        Args:
            type: 事件类型
            handler: 事件处理函数
        """
        handler_list = self._handlers[type]
        if handler not in handler_list:
            handler_list.append(handler)
    
    def unregister(self, type: str, handler: Callable[[Event], None]):
        """
        注销事件处理函数
        
        Args:
            type: 事件类型
            handler: 事件处理函数
        """
        handler_list = self._handlers[type]
        if handler in handler_list:
            handler_list.remove(handler)
        
        if not handler_list:
            del self._handlers[type]
    
    def register_general(self, handler: Callable[[Event], None]):
        """
        注册通用事件处理函数
        
        Args:
            handler: 通用事件处理函数
        """
        if handler not in self._general_handlers:
            self._general_handlers.append(handler)
    
    def unregister_general(self, handler: Callable[[Event], None]):
        """
        注销通用事件处理函数
        
        Args:
            handler: 通用事件处理函数
        """
        if handler in self._general_handlers:
            self._general_handlers.remove(handler)
    
    def put(self, event: Event):
        """
        将事件放入队列
        
        Args:
            event: 事件对象
        """
        self._queue.put(event)
    
    def put_event(self, type: str, data: Any = None):
        """
        创建事件并放入队列
        
        Args:
            type: 事件类型
            data: 事件数据
        """
        event = Event(type, data)
        self.put(event) 