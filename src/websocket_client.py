import json
import threading
import time
from typing import Any, Dict, Optional
import websocket


class WebSocketClient:
    """WebSocket客户端管理器"""

    def __init__(self, config_manager, logger, message_handler):
        """
        初始化WebSocket客户端

        Args:
            config_manager: 配置管理器实例
            logger: 日志记录器实例
            message_handler: 消息处理函数
        """
        self.config_manager = config_manager
        self.logger = logger
        self.message_handler = message_handler
        self.ws: Optional[websocket.WebSocketApp] = None
        self.SELF_ID: Optional[str] = None

    def connect(self) -> None:
        """连接WebSocket服务器"""
        try:
            # 记录连接信息时不显示token，保护安全
            ws_url_display = self.config_manager.get("NAPCAT_WS_URL")
            if "token=" in ws_url_display:
                # 隐藏token值，只显示部分信息
                parts = ws_url_display.split("token=")
                ws_url_display = f"{parts[0]}token=****"

            self.logger.info(f"正在连接WebSocket: {ws_url_display}")
            self.ws = websocket.WebSocketApp(
                str(self.config_manager.get("NAPCAT_WS_URL")),  # 这里使用完整的URL，可能已包含token
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                # 可选：添加额外的HTTP头进行token认证
                header={
                    "Authorization": (
                        f'Bearer {self.config_manager.get("NAPCAT_TOKEN")}'
                        if self.config_manager.get("NAPCAT_TOKEN")
                        else None
                    )
                },
            )

            # 启动WebSocket线程，添加重连选项
            threading.Thread(
                target=lambda: self.ws.run_forever(
                    ping_interval=30, ping_timeout=10, reconnect=5
                ),
                daemon=True,
            ).start()
            self.logger.info("WebSocket连接启动成功，将自动尝试重连")
        except Exception as e:
            self.logger.error(f"连接WebSocket失败: {e}")

    def on_open(self, ws) -> None:
        """WebSocket连接打开处理"""
        self.logger.info("WebSocket连接已打开")

    def on_message(self, ws, message) -> None:
        """WebSocket消息处理函数"""
        try:
            self.logger.info(f"收到WebSocket消息: {message[:100]}...")
            data = json.loads(message)
            # 处理接收到的消息
            self.message_handler(data)
        except Exception as e:
            self.logger.error(f"处理WebSocket消息出错: {e}")

    def on_close(self, ws, close_status_code, close_msg) -> None:
        """WebSocket连接关闭处理"""
        self.logger.info(f"WebSocket连接已关闭: {close_status_code} - {close_msg}")

    def on_error(self, ws, error) -> None:
        """WebSocket连接错误处理"""
        self.logger.error(f"WebSocket连接错误: {error}")

    def send_message(
        self,
        user_id: str,
        message: Any,
        group_id: Optional[str] = None,
        private: bool = True,
    ) -> None:
        """发送消息函数"""
        try:
            payload: Dict[str, Any]
            if private:
                # 发送私聊消息
                payload = {
                    "action": "send_private_msg",
                    "params": {"user_id": user_id, "message": message},
                }
            else:
                # 发送群消息
                payload = {
                    "action": "send_group_msg",
                    "params": {"group_id": group_id, "message": message},
                }

            # 如果配置了Token，添加到请求中
            token = self.config_manager.get("NAPCAT_TOKEN")
            if token:
                payload["params"]["access_token"] = token

            # 通过WebSocket发送消息
            if self.ws and self.ws.sock and self.ws.sock.connected:
                message_json: str = json.dumps(payload)
                self.logger.info(
                    f"准备发送 - 用户:{user_id}, 类型:{'私聊' if private else '群聊'}"
                )
                self.ws.send(message_json)
                self.logger.info(f"发送成功: {str(message)[:20]}...")
            else:
                self.logger.warning(f"WebSocket连接未建立，消息发送失败")
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")

    def send_file(
        self,
        user_id: str,
        file_path: str,
        group_id: Optional[str] = None,
        private: bool = True,
    ) -> None:
        """发送文件函数

        Args:
            user_id: 用户ID
            file_path: 文件路径
            group_id: 群组ID（群聊时提供）
            private: 是否为私聊

        Returns:
            None
        """
        try:
            # 敏感信息只在DEBUG级别记录
            self.logger.debug(
                f"准备发送文件: {file_path}, 用户ID: {user_id}, 群ID: {group_id}, 私聊模式: {private}"
            )

            import os
            if not os.path.exists(file_path):
                # 错误消息保持在ERROR级别，但不包含完整路径
                self.logger.error(f"文件不存在: {os.path.basename(file_path)}")
                error_msg = f"❌ 文件不存在哦~，请让我下载之后再发送(｡•﹃•｡)"
                self.send_message(user_id, error_msg, group_id, private)
                return

            # 检查文件是否可读
            if not os.access(file_path, os.R_OK):
                # 错误消息保持在ERROR级别，但不包含完整路径
                self.logger.error(f"文件不可读: {os.path.basename(file_path)}")
                error_msg = f"❌ 文件不可读，叫主人帮我检查一下吧∑(O_O；)"
                self.send_message(user_id, error_msg, group_id, private)
                return

            # 获取文件名
            file_name = os.path.basename(file_path)
            self.logger.debug(f"原始文件名: {file_name}")

            # 简化处理：直接使用原始的绝对路径
            file_path_to_send = os.path.abspath(file_path)
            self.logger.debug(f"使用原始绝对路径: {file_path_to_send}")

            # 直接使用消息段数组方式发送文件，这是NapCat支持的方式
            self.logger.info(f"使用消息段数组方式发送文件")

            # 构建消息段数组
            message_segments = [
                {"type": "file", "data": {"file": file_path_to_send, "name": file_name}}
            ]

            # 发送消息
            if private:
                payload = {
                    "action": "send_private_msg",
                    "params": {"user_id": user_id, "message": message_segments},
                }
            else:
                payload = {
                    "action": "send_group_msg",
                    "params": {"group_id": group_id, "message": message_segments},
                }

            token = self.config_manager.get("NAPCAT_TOKEN")
            if token:
                payload["params"]["access_token"] = token

            if self.ws and self.ws.sock and self.ws.sock.connected:
                message_json = json.dumps(payload)
                self.logger.debug(f"发送消息段数组文件: {message_json}")
                self.ws.send(message_json)
                # 只记录文件名而非敏感的路径信息
                self.logger.info(f"文件发送请求已发送: {file_name}")
                # 等待一小段时间让API请求有机会返回结果
                time.sleep(1)
            else:
                self.logger.warning("WebSocket连接未建立，文件发送失败")
                raise Exception("WebSocket连接未建立")

        except Exception as e:
            self.logger.error(f"发送文件失败: {e}")
            error_msg = f"❌ 发送文件失败: {str(e)}\n快让主人帮我检查一下ヽ(ﾟДﾟ)ﾉ"
            self.send_message(user_id, error_msg, group_id, private)

    def reconnect_manager(self) -> None:
        """WebSocket重连管理线程"""
        while True:
            time.sleep(10)  # 每10秒检查一次连接状态

            if self.ws and (not self.ws.sock or not self.ws.sock.connected):
                self.logger.info("检测到WebSocket未连接，尝试重新连接...")
                try:
                    # 关闭现有连接
                    if self.ws:
                        self.ws.close()
                    # 重新连接
                    self.connect()
                except Exception as e:
                    self.logger.error(f"重连WebSocket失败: {e}")

    def close(self) -> None:
        """关闭WebSocket连接"""
        if self.ws is not None:
            try:
                if self.ws.sock and self.ws.sock.connected:
                    self.logger.info("关闭WebSocket连接...")
                    self.ws.close()
                    self.logger.info("WebSocket连接已成功关闭")
                else:
                    self.logger.info("WebSocket连接已断开，无需关闭")
            except Exception as ws_error:
                self.logger.error(f"关闭WebSocket连接时出错: {ws_error}")
                raise ws_error
