#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ThorpAI主应用程序入口
使用全局实例管理器启动所有服务
"""

import os
import sys
import time
import signal
import threading

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from btc_model.manager.service_manager import initialize_global_instances, shutdown_global_instances
from btc_model.core.util.log_util import Logger
from btc_model.core.util.instance_manager import register_instance, global_instance
from btc_model.strategy.exchange_arbitrage.exchange_arbitrage_strategy import ExchangeArbitrageStrategy, setup_exchanges, load_pairs


def initialize_strategy():
    """初始化交易所套利策略"""
    Logger.info("正在初始化交易所套利策略...")
    
    try:
        # 设置交易所
        Logger.info("设置交易所...")
        exchange_1, exchange_2, hedge_exchange = setup_exchanges(sandbox=True)
        
        # 加载交易对
        Logger.info("加载交易对...")
        pair_data = load_pairs()
        
        # 初始化策略
        Logger.info("初始化策略...")
        strategy = ExchangeArbitrageStrategy(
            exchange_1=exchange_1,
            exchange_2=exchange_2,
            hedge_exchange=hedge_exchange,
            pair_data=pair_data
        )
        
        # 注册策略实例
        register_instance("exchange_arbitrage_strategy", strategy)
        Logger.info("交易所套利策略初始化完成")
        
        return strategy
    except Exception as e:
        Logger.error(f"初始化策略失败: {e}")
        return None


def signal_handler(sig, frame):
    """处理终止信号"""
    Logger.info("收到终止信号，准备关闭应用...")
    shutdown_global_instances()
    sys.exit(0)


def main():
    """主函数，启动所有服务"""
    Logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    Logger.info("正在启动 ThorpAI 应用...")
    Logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # 注册信号处理函数，用于优雅地退出
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 初始化策略
        strategy = initialize_strategy()
        if not strategy:
            Logger.error("策略初始化失败，无法启动服务")
            return
        
        # 初始化全局实例（包括WebSocket和REST API服务器）
        initialize_global_instances()
        
        # 主线程保持运行，等待信号终止
        Logger.info("应用启动完成，按 Ctrl+C 终止...")
        
        # 保持主线程运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        Logger.info("收到键盘中断，准备关闭应用...")
    except Exception as e:
        Logger.error(f"应用运行出错: {e}")
    finally:
        # 关闭所有全局实例
        shutdown_global_instances()
        Logger.info("ThorpAI 应用已关闭")


if __name__ == "__main__":
    main() 