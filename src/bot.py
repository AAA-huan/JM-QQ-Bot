import os
import platform
import re
import signal
import sys
import threading
import time
from typing import Any, Dict, Optional

from src.command_parser import CommandParser
from src.config_manager import ConfigManager
from src.download_manager import DownloadManager
from src.websocket_client import WebSocketClient
from src.permission_manager import PermissionManager
from src.logger_config import LoggerConfig


class MangaBot:
    # 机器人版本号
    VERSION = "2.3.12"

    def __init__(self) -> None:
        """初始化MangaBot机器人"""
        # 配置日志
        self.logger = LoggerConfig.setup_logger()
        # 记录启动信息，包含版本号
        self.logger.info(f"JMComic QQ机器人 版本 {self.VERSION} 启动中...")

        # 检查操作系统兼容性
        self._check_platform_compatibility()

        # 初始化配置管理器
        self.config_manager = ConfigManager()
        self.config_manager.load_config()

        # 初始化权限管理器
        self.permission_manager = PermissionManager(
            group_whitelist=self.config_manager.group_whitelist,
            private_whitelist=self.config_manager.private_whitelist,
            global_blacklist=self.config_manager.global_blacklist,
        )

        # 初始化下载管理器
        self.download_manager = DownloadManager(self.config_manager, self.logger)

        # 初始化WebSocket客户端
        self.ws_client = WebSocketClient(
            config_manager=self.config_manager,
            logger=self.logger,
            message_handler=self.handle_event,
        )

        # 初始化命令解析器
        self.command_parser = CommandParser()

        # 创建下载目录
        self.config_manager.create_download_directory()
        self.logger.info(f"下载路径设置为: {self.config_manager.get('MANGA_DOWNLOAD_PATH')}")

        # 记录黑白名单配置信息
        self.logger.info(
            f"黑白名单配置加载完成 - 群组白名单: {len(self.config_manager.group_whitelist)}个, "
            f"私信白名单: {len(self.config_manager.private_whitelist)}个, "
            f"全局黑名单: {len(self.config_manager.global_blacklist)}个"
        )

        # 清理下载失败的文件
        self.download_manager.cleanup_failed_downloads()

    def _check_platform_compatibility(self) -> None:
        """检查操作系统兼容性，确保在Linux和Windows上都能正常运行"""
        current_platform: str = platform.system().lower()
        python_version: str = platform.python_version()

        self.logger.info(f"检测到操作系统: {current_platform}")
        self.logger.info(f"Python版本: {python_version}")

        # 检查支持的操作系统
        supported_platforms: list[str] = ["linux", "windows"]
        if current_platform not in supported_platforms:
            error_msg: str = (
                f"不支持的平台: {current_platform}。仅支持 {supported_platforms}"
            )
            self.logger.error(error_msg)
            raise OSError(error_msg)

        # 检查Python版本
        python_version_tuple: tuple = sys.version_info
        if python_version_tuple < (3, 7):
            error_msg: str = (
                f"Python版本过低: {python_version}。需要Python 3.7或更高版本"
            )
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        self.logger.info(f"平台兼容性检查通过: {current_platform}")

    def handle_event(self, data: Dict[str, Any]) -> None:
        """事件处理函数"""
        try:
            # 生成唯一的事件ID用于追踪
            event_id = hash(str(data))
            # 安全获取时间戳，确保不会出现KeyError
            timestamp = data.get("time", time.time())

            # 安全获取事件类型字段，防止KeyError
            post_type = data.get("post_type", "UNKNOWN")
            event_type = data.get(
                "meta_event_type", data.get("message_type", "UNKNOWN")
            )

            # 详细日志，记录事件的唯一标识符和时间戳
            self.logger.info(
                f"收到事件 [ID:{event_id}] - 类型: {post_type}, {event_type}, 时间戳: {timestamp}"
            )
            self.logger.debug(f"事件详细数据: {str(data)[:200]}...")

            # 直接从消息的根级别获取self_id
            self_id_value = data.get("self_id")
            if self_id_value:
                if not self.ws_client.SELF_ID or self.ws_client.SELF_ID != self_id_value:
                    self.ws_client.SELF_ID = self_id_value
                    self.logger.info(f"从消息中获取到自身ID: {self.ws_client.SELF_ID}")
        except Exception as e:
            # 捕获所有异常，防止事件处理中断
            self.logger.error(f"处理事件时出错: {str(e)}")
            # 使用更简单的错误记录方式
            error_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{error_time} - 处理事件失败: {str(e)}")

        # 处理元事件
        if data.get("post_type") == "meta_event":
            return

        # 处理私聊消息（私聊消息无需@）
        if data.get("post_type") == "message" and data.get("message_type") == "private":
            user_id = str(data.get("user_id"))
            message = data.get("raw_message")

            # 黑白名单权限检查
            if not self.permission_manager.check_user_permission(user_id, private=True):
                self.logger.warning(f"拒绝处理私信 - 用户 {user_id} 权限不足")
                return

            self.logger.info(f"收到私聊消息 - 用户{user_id}: {message}")
            # 确保私聊消息始终被处理，不检查@
            try:
                self.handle_command(user_id, message, private=True)
                self.logger.debug(f"私聊消息处理完成 - 用户{user_id}")
            except Exception as e:
                self.logger.error(f"处理私聊消息时出错: {e}")
                # 即使出错也尝试通知用户
                try:
                    self.ws_client.send_message(
                        user_id,
                        f"处理消息时出错: {str(e)}\n快让主人帮我检查一下ヽ(ﾟДﾟ)ﾉ",
                        private=True,
                    )
                except:
                    pass  # 避免嵌套异常
        # 处理群消息（需要被@才回应）
        elif data.get("post_type") == "message" and data.get("message_type") == "group":
            group_id = str(data.get("group_id"))
            user_id = str(data.get("user_id"))
            message = data.get("raw_message")

            # 黑白名单权限检查
            if not self.permission_manager.check_user_permission(
                user_id, group_id=group_id, private=False
            ):
                self.logger.warning(
                    f"拒绝处理群消息 - 群组 {group_id} 用户 {user_id} 权限不足"
                )
                return

            self.logger.info(f"收到群消息 - 群{group_id} 用户{user_id}: {message}")

            # 记录原始消息中是否包含CQ:reply格式
            has_reply_format = '[CQ:reply,' in message
            
            # 首先移除消息中所有CQ:reply格式的内容（如[CQ:reply,id=1321]）
            # 使用正则表达式匹配所有CQ:reply格式
            message = re.sub(r'\[CQ:reply,id=\d+\]', '', message)
            
            # 添加日志确认CQ:reply部分是否被移除
            if has_reply_format:
                self.logger.debug(f"CQ:reply格式已从消息中移除")

            # 检查是否被@
            at_self = False

            # 简化@检测逻辑
            if self.ws_client.SELF_ID:
                # 方法1：检查raw_message中是否包含@机器人信息
                if (
                    f"@{self.ws_client.SELF_ID}" in message
                    or f"[CQ:at,qq={self.ws_client.SELF_ID}]" in message
                ):
                    at_self = True
                self.logger.debug(f"SELF_ID: {self.ws_client.SELF_ID}, 被@状态: {at_self}")
            else:
                self.logger.warning("SELF_ID未初始化，无法检测@状态")

            # 如果没有被@，则不处理消息
            if not at_self:
                self.logger.debug("未被@，忽略消息")
                return

            # 如果被@，移除@部分，只保留命令内容
            # 移除CQ码格式的@
            message = message.replace(f"[CQ:at,qq={self.ws_client.SELF_ID}]", "")
            # 移除纯文本格式的@
            message = message.replace(f"@{self.ws_client.SELF_ID}", "")
            # 移除多余的空格
            message = message.strip()

            self.logger.info(f"收到群消息并被@ - 群{group_id} 用户{user_id}: {message}")
            self.handle_command(user_id, message, group_id=group_id, private=False)

    def handle_command(self, user_id: str, message: str, group_id: Optional[str] = None, private: bool = True) -> None:
        """
        处理用户命令的函数，使用命令解析器进行标准化处理

        Args:
            user_id: 用户ID
            message: 原始消息内容
            group_id: 群组ID（群聊时提供）
            private: 是否为私聊
        """
        # 命令处理函数
        command_id = hash(str(time.time()) + message[:50])
        self.logger.info(
            f"[命令ID:{command_id}] 开始处理命令 - 用户{user_id}, 私聊={private}"
        )

        # 确保message不为None
        if message is None:
            self.logger.warning(f"[命令ID:{command_id}] 收到空消息，忽略处理")
            self.ws_client.send_message(
                user_id,
                "(｡•﹃•｡)叽里咕噜说什么呢，听不懂。\n发送漫画帮助看看我怎么用吧！",
                group_id,
                private,
            )
            return

        # 使用命令解析器处理用户输入
        try:
            cmd, args = self.command_parser.parse(message)
        except ValueError as e:
            self.logger.warning(f"[命令ID:{command_id}] 命令解析失败: {e}")
            self.ws_client.send_message(
                user_id,
                "❌ 命令格式错误，请输入有效的命令\n发送'漫画帮助'查看可用命令",
                group_id,
                private,
            )
            return

        self.logger.info(
            f"[命令ID:{command_id}] 处理命令 - 用户{user_id}: 标准化命令='{cmd}', 参数='{args}', 私聊={private}"
        )

        # 验证命令参数
        if not self.command_parser.validate_params(cmd, args):
            error_msg = self.command_parser.get_error_message(cmd)
            self.logger.warning(f"[命令ID:{command_id}] 参数验证失败: {error_msg}")
            self.ws_client.send_message(user_id, error_msg, group_id, private)
            return

        # 帮助命令
        if cmd == "help":
            self.send_help(user_id, group_id, private)
        # 漫画下载命令
        elif cmd == "download":
            self.handle_manga_download(user_id, args, group_id, private)
        # 发送已下载漫画命令
        elif cmd == "send":
            self.handle_manga_send(user_id, args, group_id, private)
        # 查询已下载漫画列表命令
        elif cmd == "list":
            self.query_downloaded_manga(user_id, group_id, private)
        # 查询指定漫画ID是否已下载
        elif cmd == "query":
            self.query_manga_existence(user_id, args, group_id, private)
        # 漫画版本查询命令
        elif cmd == "version":
            self.send_version_info(user_id, group_id, private)
        # 下载进度查询命令
        elif cmd == "progress":
            self.show_download_progress(user_id, group_id or "", private)
        # 测试命令，显示当前SELF_ID状态
        elif cmd == "test_id":
            # 测试命令，显示机器人当前的SELF_ID状态
            if self.ws_client.SELF_ID:
                self.ws_client.send_message(
                    user_id, f"✅ 机器人ID: {self.ws_client.SELF_ID}", group_id, private
                )
            else:
                self.ws_client.send_message(user_id, "❌ 机器人ID未获取", group_id, private)
        elif cmd == "test_file":
            # 测试文件发送功能
            self.ws_client.send_message(user_id, "🔍 开始测试文件发送功能...", group_id, private)

            # 创建一个简单的测试文件
            test_file_path = os.path.join(os.getcwd(), "test_file.txt")
            try:
                with open(test_file_path, "w", encoding="utf-8") as f:
                    f.write("这是一个测试文件，用于验证机器人的文件发送功能。\n")
                    f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"机器人ID: {self.ws_client.SELF_ID or '未获取'}\n")

                self.ws_client.send_message(
                    user_id, f"📄 已创建测试文件: {test_file_path}", group_id, private
                )
                self.ws_client.send_message(user_id, "🚀 开始发送测试文件...", group_id, private)

                # 发送测试文件
                self.ws_client.send_file(user_id, test_file_path, group_id, private)

                # 清理测试文件
                if os.path.exists(test_file_path):
                    os.remove(test_file_path)
                    self.logger.debug(f"已清理测试文件: {test_file_path}")

            except Exception as e:
                self.logger.error(f"创建测试文件失败: {e}")
                self.ws_client.send_message(
                    user_id, f"❌ 创建测试文件失败: {str(e)}", group_id, private
                )
        # 欢迎消息
        elif any(
            keyword in message.lower() for keyword in ["你好", "hi", "hello", "在吗"]
        ):
            response = "你好！我是高性能JM机器人૮₍♡>𖥦<₎ა，可以帮你下载JMComic的漫画哦~~~\n输入 '漫画帮助' 就可以查看我的使用方法啦~"
            self.ws_client.send_message(user_id, response, group_id, private)

    def query_downloaded_manga(self, user_id: str, group_id: Optional[str], private: bool) -> None:
        """查询已下载的漫画"""
        self.logger.info(f"开始处理漫画列表查询 - 用户{user_id}")
        try:
            # 检查下载目录是否存在
            download_path = str(self.config_manager.get("MANGA_DOWNLOAD_PATH"))
            if not os.path.exists(download_path):
                self.logger.info(f"发送下载目录不存在消息 - 用户{user_id}")
                self.ws_client.send_message(
                    user_id,
                    "❌ 下载目录不存在！\n快让主人帮我检查一下ヽ(ﾟДﾟ)ﾉ",
                    group_id,
                    private,
                )
                return

            # 查找所有PDF格式的文件
            pdf_files = []
            for file_name in os.listdir(download_path):
                if file_name.endswith(".pdf"):
                    # 提取文件名（不含扩展名）
                    name_without_ext = os.path.splitext(file_name)[0]
                    pdf_files.append(name_without_ext)

            # 根据漫画ID进行排序
            pdf_files.sort()

            # 构建回复消息
            if not pdf_files:
                response = "📚↖(^ω^)↗ 目前没有已下载的漫画PDF文件！\n把你们珍藏的车牌号都统统交给我吧~~~"
            else:
                response = "📚 已下载的漫画列表：\n\n"
                # 每5个漫画为一组显示
                for i in range(0, len(pdf_files), 5):
                    group = pdf_files[i : i + 5]
                    response += "\n".join(
                        [f"{j+1}. {name}" for j, name in enumerate(group, start=i)]
                    )
                    response += "\n\n"

                response += f"总计：{len(pdf_files)} 个漫画PDF文件"

            self.logger.info(
                f"准备发送漫画列表消息 - 用户{user_id}, 消息长度: {len(response)}"
            )
            self.ws_client.send_message(user_id, response, group_id, private)
            self.logger.info(f"漫画列表消息发送完成 - 用户{user_id}")
        except Exception as e:
            self.logger.error(f"查询已下载漫画出错: {e}")
            self.ws_client.send_message(
                user_id, f"❌ 查询失败了(｡•﹃•｡)：{str(e)}", group_id, private
            )

    def query_manga_existence(self, user_id: str, manga_id: str, group_id: Optional[str], private: bool) -> None:
        """
        查询指定漫画ID是否已下载或正在下载

        参数:
            user_id: 用户ID
            manga_id: 漫画ID (由CommandParser验证)
            group_id: 群ID
            private: 是否为私聊
        """
        self.logger.info(f"查询漫画存在性 - 用户{user_id}, 漫画ID: {manga_id}")
        try:
            # 首先检查是否正在下载
            if self.download_manager.is_downloading(manga_id):
                response = (
                    f"⏳ 漫画ID {manga_id} 正在下载中！请耐心等待下载完成后再尝试发送。"
                )
                self.ws_client.send_message(user_id, response, group_id, private)
                return

            # 检查漫画是否已存在
            found, found_files = self.download_manager.check_manga_exists(manga_id)

        except Exception as e:
            self.logger.error(f"查询漫画存在性出错: {e}")
            self.ws_client.send_message(
                user_id, f"❌ 查询失败了(｡•﹃•｡)：{str(e)}", group_id, private
            )

    def handle_manga_download(self, user_id: str, manga_id: str, group_id: Optional[str], private: bool) -> None:
        """
        处理漫画下载请求

        参数:
            user_id: 用户ID
            manga_id: 漫画ID
            group_id: 群ID
            private: 是否为私聊
        """
        download_command_id = hash(str(time.time()) + manga_id)
        self.logger.info(
            f"[下载命令ID:{download_command_id}] 开始处理漫画下载 - 用户{user_id}, 漫画ID: {manga_id}"
        )

        try:
            # 检查是否正在下载
            if self.download_manager.is_downloading(manga_id):
                response = f"⏳ 漫画ID {manga_id} 正在下载中！请耐心等待下载完成。"
                self.ws_client.send_message(user_id, response, group_id, private)
                return

            # 检查漫画是否已存在
            found, found_files = self.download_manager.check_manga_exists(manga_id)
            if found:
                response = f"✅ 漫画ID {manga_id} 已下载完成！\n发送'发送 {manga_id}'即可获取文件。"
                if found_files:
                    response += f"\n文件列表: {', '.join(found_files[:3])}" + (
                        "..." if len(found_files) > 3 else ""
                    )
                self.ws_client.send_message(user_id, response, group_id, private)
                return

            # 检查下载队列是否已有此任务
            if manga_id in self.download_manager.queued_tasks:
                position = list(self.download_manager.queued_tasks.keys()).index(manga_id) + 1
                response = f"⏳ 漫画ID {manga_id} 已在下载队列中，当前位置: {position}"
                self.ws_client.send_message(user_id, response, group_id, private)
                return

            # 添加下载任务到队列
            self.download_manager.add_download_task(user_id, manga_id, group_id, private)

            # 获取队列长度
            queue_size = len(self.download_manager.queued_tasks)
            downloading_count = len(self.download_manager.downloading_mangas)

            response = (
                f"✅ 已添加漫画ID {manga_id} 到下载队列！\n\n"
                f"📊 当前状态:\n"
                f"• 正在下载: {downloading_count} 个\n"
                f"• 队列等待: {queue_size} 个\n"
                f"• 你的位置: {queue_size + 1}\n\n"
                f"请耐心等待，下载完成后会通知你。\n"
                f"你可以发送'下载进度'查看当前进度。"
            )

            self.ws_client.send_message(user_id, response, group_id, private)
            self.logger.info(f"[下载命令ID:{download_command_id}] 下载任务已添加到队列 - 漫画ID: {manga_id}")

        except Exception as e:
            self.logger.error(f"[下载命令ID:{download_command_id}] 处理下载请求失败: {e}")
            self.ws_client.send_message(
                user_id, f"❌ 添加下载任务失败(｡•﹃•｡)：{str(e)}", group_id, private
            )

    def handle_manga_send(self, user_id: str, manga_id: str, group_id: Optional[str], private: bool) -> None:
        """
        处理漫画发送请求

        参数:
            user_id: 用户ID
            manga_id: 漫画ID
            group_id: 群ID
            private: 是否为私聊
        """
        send_command_id = hash(str(time.time()) + manga_id)
        self.logger.info(
            f"[发送命令ID:{send_command_id}] 开始处理漫画发送 - 用户{user_id}, 漫画ID: {manga_id}"
        )

        try:
            # 首先检查是否正在下载
            if self.download_manager.is_downloading(manga_id):
                response = f"⏳ 漫画ID {manga_id} 正在下载中！请耐心等待下载完成后再尝试发送。"
                self.ws_client.send_message(user_id, response, group_id, private)
                return

            # 检查漫画是否已存在
            found, found_files = self.download_manager.check_manga_exists(manga_id)

            if not found:
                response = (
                    f"❌ 漫画ID {manga_id} 尚未下载完成或不存在！\n\n"
                    f"你可以:\n"
                    f"1. 发送'下载 {manga_id}'开始下载\n"
                    f"2. 发送'漫画列表'查看已下载的漫画"
                )
                self.ws_client.send_message(user_id, response, group_id, private)
                return

            # 查找对应的PDF文件
            download_path = str(self.config_manager.get("MANGA_DOWNLOAD_PATH"))
            pdf_file = None

            for file_name in os.listdir(download_path):
                if file_name.endswith(".pdf"):
                    name_without_ext = os.path.splitext(file_name)[0]
                    if (
                        name_without_ext.startswith(manga_id + "-")
                        or name_without_ext == manga_id
                    ):
                        pdf_file = os.path.join(download_path, file_name)
                        break

            if not pdf_file or not os.path.exists(pdf_file):
                response = f"❌ 漫画ID {manga_id} 的PDF文件未找到！文件可能已损坏。"
                self.ws_client.send_message(user_id, response, group_id, private)
                return

            # 获取文件信息
            file_size = os.path.getsize(pdf_file)
            file_size_mb = file_size / (1024 * 1024)

            # 发送准备消息
            preparation_msg = (
                f"📦 准备发送漫画: {manga_id}\n"
                f"📊 文件大小: {file_size_mb:.2f} MB\n"
                f"⏳ 正在发送中，请稍候..."
            )
            self.ws_client.send_message(user_id, preparation_msg, group_id, private)

            # 发送文件
            self.logger.info(f"[发送命令ID:{send_command_id}] 开始发送PDF文件: {pdf_file}")
            self.ws_client.send_file(user_id, pdf_file, group_id, private)

            # 发送完成消息
            completion_msg = f"✅ 漫画 {manga_id} 发送完成！请查收。"
            self.ws_client.send_message(user_id, completion_msg, group_id, private)
            self.logger.info(f"[发送命令ID:{send_command_id}] 漫画发送完成 - 用户{user_id}")

        except Exception as e:
            self.logger.error(f"[发送命令ID:{send_command_id}] 发送漫画失败: {e}")
            self.ws_client.send_message(
                user_id, f"❌ 发送漫画失败(｡•﹃•｡)：{str(e)}", group_id, private
            )

    def show_download_progress(self, user_id: str, group_id: str, private: bool) -> None:
        """显示当前下载进度"""
        self.logger.info(f"开始处理下载进度查询 - 用户{user_id}")

        try:
            # 获取下载进度信息
            downloading_mangas, queued_mangas = self.download_manager.get_download_progress()

            # 构建响应消息
            if not downloading_mangas and not queued_mangas:
                response = "📊 当前没有任务在下载或等待中！\n发送'漫画下载 [ID]'开始下载漫画吧！"
            else:
                response = "📊 当前下载进度：\n\n"

                if downloading_mangas:
                    response += "🔄 正在下载：\n"
                    for i, manga_id in enumerate(downloading_mangas, 1):
                        response += f"  {i}. {manga_id}\n"
                    response += "\n"

                if queued_mangas:
                    response += "⏳ 等待队列：\n"
                    for i, manga_id in enumerate(queued_mangas, 1):
                        response += f"  {i}. {manga_id}\n"
                    response += "\n"

                response += f"📈 总计：{len(downloading_mangas)} 个正在下载，{len(queued_mangas)} 个等待中"

            self.ws_client.send_message(user_id, response, group_id, private)
            self.logger.info(f"下载进度消息发送完成 - 用户{user_id}")

        except Exception as e:
            self.logger.error(f"查询下载进度出错: {e}")
            self.ws_client.send_message(
                user_id, f"❌ 查询下载进度失败(｡•﹃•｡)：{str(e)}", group_id, private
            )

    def send_help(self, user_id: str, group_id: Optional[str], private: bool) -> None:
        """发送帮助信息"""
        help_message = (
            "📚 JMComic QQ机器人使用指南 📚\n\n"
            "🌟 基本命令：\n"
            "• 漫画帮助 - 显示此帮助信息\n"
            "• 漫画下载 [ID] - 下载指定ID的漫画\n"
            "• 发送 [ID] - 发送已下载的漫画\n"
            "• 漫画列表 - 查看已下载的漫画列表\n"
            "• 查询漫画 [ID] - 查询漫画是否已下载\n"
            "• 下载进度 - 查看当前下载进度\n"
            "• 漫画版本 - 查看机器人版本信息\n\n"
            "💡 使用示例：\n"
            "• 私聊或@我发送：漫画下载 350234\n"
            "• 等待下载完成后发送：发送 350234\n"
            "• 查看已下载的漫画：漫画列表\n\n"
            "🔒 注意事项：\n"
            "• 每个漫画下载需要时间，请耐心等待\n"
            "• 下载完成后会自动转换为PDF格式\n"
            "• 支持多个漫画同时下载（按队列顺序）\n\n"
            "🆘 遇到问题？请确保漫画ID正确，或联系管理员！"
        )

        self.ws_client.send_message(user_id, help_message, group_id, private)
        self.logger.info(f"已发送帮助信息给用户 {user_id}")

    def send_version_info(self, user_id: str, group_id: Optional[str], private: bool) -> None:
        """发送版本信息"""
        version_message = (
            f"🤖 JMComic QQ机器人\n"
            f"版本: {self.VERSION}\n"
            f"状态: 运行中\n"
            f"下载目录: {self.config_manager.get('MANGA_DOWNLOAD_PATH')}\n\n"
            f"💝 感谢使用！如有问题请联系管理员。"
        )

        self.ws_client.send_message(user_id, version_message, group_id, private)
        self.logger.info(f"已发送版本信息给用户 {user_id}")

    def handle_safe_close(self) -> None:
        """设置安全关闭信号处理"""
        def signal_handler(signum, frame):
            self.logger.info(f"收到关闭信号 {signum}，开始安全关闭...")
            
            # 停止下载队列
            self.download_manager.stop_queue()
            self.logger.info("下载队列已停止")
            
            # 关闭WebSocket连接
            if self.ws_client:
                self.ws_client.close()
                self.logger.info("WebSocket连接已关闭")
            
            self.logger.info("机器人安全关闭完成")
            sys.exit(0)

        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        self.logger.info("安全关闭信号处理器已注册")
