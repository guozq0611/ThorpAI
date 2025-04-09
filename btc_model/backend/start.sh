#!/bin/bash

echo "正在启动ThorpAI服务..."
echo "====================================="

# 获取当前脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 切换到项目根目录
cd $DIR/../..

# 启动主应用
python -m btc_model.main_app

echo "====================================="
echo "服务已关闭" 