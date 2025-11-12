#!/bin/bash

# JMComic下载机器人启动脚本（Linux版本）
# 基于NapCat框架

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到Python3。请先安装Python3并将其添加到环境变量中。"
    exit 1
fi

# 检查pip是否安装
if ! command -v pip3 &> /dev/null; then
    echo "错误：未找到pip3。请先安装pip3。"
    exit 1
fi

# 安装或更新依赖
echo "正在安装/更新依赖..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "警告：依赖安装失败。请检查网络连接或手动运行 pip3 install -r requirements.txt"
fi

# 创建下载目录
mkdir -p downloads

# 显示启动信息
echo "============================"
echo "    JMComic下载机器人（Linux）"
echo "    基于NapCat框架"
echo "============================"

echo "正在启动机器人..."
python3 bot.py