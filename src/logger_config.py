import sys
import time
import os
from datetime import datetime, timezone, timedelta
from loguru import logger as loguru_logger  # type: ignore[import]


class LoggerConfig:
    """日志配置管理器"""

    @staticmethod
    def setup_logger() -> loguru_logger:
        """配置loguru日志系统并返回logger实例"""
        # 清除已有的处理器
        loguru_logger.remove()

        # 创建日志目录
        log_dir: str = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file: str = os.path.join(log_dir, f'{time.strftime("%Y-%m-%d")}.log')

        # 配置东八区时区转换函数
        def cst_formatter(record):
            try:
                # 创建东八区时区对象
                cst_timezone = timezone(timedelta(hours=8))

                # 安全地获取时间戳，防止KeyError
                timestamp = record.get("time", time.time())

                # 处理不同类型的时间戳
                if hasattr(timestamp, "timestamp"):
                    # 如果是datetime对象
                    cst_time = datetime.fromtimestamp(
                        timestamp.timestamp(), cst_timezone
                    )
                else:
                    # 如果是数值型时间戳
                    cst_time = datetime.fromtimestamp(timestamp, cst_timezone)

                # 格式化时间字符串
                formatted_time = cst_time.strftime("%Y-%m-%d %H:%M:%S")

                # 安全获取其他必要字段
                name = record.get("name", "UNKNOWN")
                level_name = record.get(
                    "level", type("obj", (object,), {"name": "UNKNOWN"})
                ).name
                message = record.get("message", "")

                # 返回完全格式化的日志消息，确保所有特殊字符都正确处理
                # 转义大括号以防止format错误
                safe_message = str(message).replace("{", "{{").replace("}", "}}")
                return (
                    f"{formatted_time} CST - {name} - {level_name} - {safe_message}\n"
                )
            except Exception as e:
                # 如果格式化失败，返回基本错误信息
                fallback_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return f"{fallback_time} CST - ERROR - 日志格式化失败: {str(e)}\n"

        # 配置控制台日志（INFO级别，无彩色）
        loguru_logger.add(
            sys.stdout,
            level="INFO",
            format=cst_formatter,
            colorize=False,
        )

        # 配置文件日志（DEBUG级别）
        loguru_logger.add(
            log_file,
            level="DEBUG",
            format=cst_formatter,
            encoding="utf-8",
            rotation="00:00",  # 每天凌晨滚动日志文件
            retention="7 days",  # 保留7天的日志
        )

        return loguru_logger
