#!/usr/bin/env python3
"""
JMComic QQ机器人 - 主程序入口点
重构版本，模块化设计
"""

import signal
import sys
import threading
import time

from src.bot import MangaBot


def main():
    """主函数"""
    try:
        # 创建机器人实例
        bot = MangaBot()
        
        # 设置安全关闭机制
        bot.handle_safe_close()
        
        # 连接WebSocket
        bot.ws_client.connect()
        
        # 启动WebSocket重连管理线程
        threading.Thread(target=bot.ws_client.reconnect_manager, daemon=True).start()
        
        # 记录启动成功信息
        bot.logger.info("JMComic QQ机器人启动成功！")
        bot.logger.info("按 Ctrl+C 安全关闭机器人")
        
        # 保持主程序运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n收到关闭信号，正在安全关闭机器人...")
        # 安全关闭逻辑将在handle_safe_close中处理
    except Exception as e:
        print(f"机器人启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
