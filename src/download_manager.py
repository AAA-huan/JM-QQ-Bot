import os
import re
import shutil
import sys
import queue
import threading
import time
from typing import Dict, List, Optional, Tuple
from PIL import Image

import jmcomic


class DownloadManager:
    """下载管理器，负责漫画下载和队列管理"""

    def __init__(self, config_manager, logger):
        """
        初始化下载管理器

        Args:
            config_manager: 配置管理器实例
            logger: 日志记录器实例
        """
        self.config_manager = config_manager
        self.logger = logger

        # 初始化下载队列
        self.download_queue: queue.Queue = queue.Queue()
        self.queue_running: bool = True
        self.downloading_mangas: Dict[str, bool] = {}
        self.queued_tasks: Dict[str, Tuple[str, Optional[str], bool]] = {}

        # 启动下载队列处理线程
        self._start_download_queue_processor()

    def _start_download_queue_processor(self) -> None:
        """
        启动下载队列处理线程
        该线程将不断从队列中取出下载任务并顺序执行
        """

        def process_queue() -> None:
            """下载队列处理函数，顺序执行队列中的下载任务"""
            while self.queue_running:
                try:
                    # 从队列中获取下载任务，设置超时以便定期检查running标志
                    task = self.download_queue.get(timeout=1)

                    # 解包任务数据
                    user_id, manga_id, group_id, private = task

                    # 执行下载任务
                    self._process_download_task(user_id, manga_id, group_id, private)

                    # 标记任务完成
                    self.download_queue.task_done()
                except queue.Empty:
                    # 队列为空，继续循环检查running标志
                    continue
                except Exception as e:
                    self.logger.error(f"处理下载队列任务时出错: {e}")
                    # 确保即使出错也标记任务完成，避免队列阻塞
                    try:
                        self.download_queue.task_done()
                    except:
                        pass

        # 创建并启动队列处理线程，设置为守护线程
        queue_thread = threading.Thread(target=process_queue, daemon=True)
        queue_thread.start()
        self.logger.info("下载队列处理线程已启动")

    def _process_download_task(
        self, user_id: str, manga_id: str, group_id: str, private: bool
    ) -> None:
        """
        处理队列中的下载任务
        实际执行漫画下载的方法，确保下载任务按顺序执行，避免并发下载导致的资源竞争

        参数:
            user_id: 用户ID，用于回复下载状态
            manga_id: 漫画ID，指定要下载的漫画
            group_id: 群ID，用于在群聊中发送消息
            private: 是否为私聊，决定消息发送的目标

        异常:
            所有下载相关的异常都会被捕获并记录，确保队列继续处理其他任务
        """
        # 下载漫画函数
        try:
            # 从队列任务跟踪中移除（已开始处理）
            if manga_id in self.queued_tasks:
                del self.queued_tasks[manga_id]
            # 标记该漫画正在下载中
            self.downloading_mangas[manga_id] = True

            # 使用jmcomic库下载漫画
            self.logger.info("开始下载漫画ID: %s", manga_id)
            # 从配置文件创建下载选项对象（使用相对路径）
            option = jmcomic.create_option_by_file("option.yml")
            # 确保使用环境变量中的下载路径
            option.dir_rule.base_dir = self.config_manager.get("MANGA_DOWNLOAD_PATH")

            # 设置目录命名规则，将漫画ID和名称组合在同一个文件夹名中
            # 使用f-string格式的规则，这样会创建 {base_dir}/{album_id}-{album_title}/{photo_title} 的目录结构
            # 在jmcomic v2.5.36+版本支持这种语法
            new_rule = "Bd / {Aid}-{Atitle}"
            from jmcomic.jm_option import DirRule

            # 创建新的DirRule对象并替换原有的
            option.dir_rule = DirRule(new_rule, base_dir=option.dir_rule.base_dir)

            jmcomic.download_album(manga_id, option=option)

            # 查找漫画文件夹 - 简化逻辑，只检查是否以漫画ID开头
            manga_dir = None
            # 直接在基础下载目录下查找
            download_path = str(self.config_manager.get("MANGA_DOWNLOAD_PATH"))
            if os.path.exists(download_path):
                for dir_name in os.listdir(download_path):
                    dir_path = os.path.join(download_path, dir_name)
                    # 检查是否是目录且以漫画ID开头
                    if os.path.isdir(dir_path) and dir_name.startswith(f"{manga_id}-"):
                        manga_dir = dir_path
                        break

            # 如果在基础目录没找到，再尝试递归查找（兼容可能的其他情况）
            if not manga_dir:
                for root, dirs, files in os.walk(download_path):
                    for dir_name in dirs:
                        if dir_name.startswith(f"{manga_id}-"):
                            manga_dir = os.path.join(root, dir_name)
                            break
                    if manga_dir:
                        break

            if manga_dir and os.path.exists(manga_dir):
                # 从manga_dir路径中提取文件夹名称
                folder_name = os.path.basename(manga_dir)
                pdf_path = os.path.join(download_path, f"{folder_name}.pdf")

                # 收集所有图片文件
                image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
                image_files = []

                for root, _, files in os.walk(manga_dir):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in image_extensions):
                            image_files.append(os.path.join(root, file))

                # 按文件名排序
                image_files.sort()

                if not image_files:
                    self.logger.warning(f"在漫画文件夹中未找到图片文件: {manga_dir}")
                    return

                self.logger.info(f"找到 {len(image_files)} 个图片文件，开始转换为PDF")

                # 转换为PDF
                try:
                    # 打开第一张图片作为PDF的第一页
                    first_image = Image.open(image_files[0])
                    # 确保图片为RGB模式
                    if first_image.mode == "RGBA":
                        first_image = first_image.convert("RGB")

                    # 准备其他图片
                    other_images = []
                    for img_path in image_files[1:]:
                        img = Image.open(img_path)
                        # 确保图片为RGB模式
                        if img.mode == "RGBA":
                            img = img.convert("RGB")
                        other_images.append(img)

                    # 保存为PDF
                    first_image.save(
                        pdf_path, save_all=True, append_images=other_images
                    )
                    self.logger.info(f"成功将漫画 {manga_id} 转换为PDF: {pdf_path}")

                    # 删除原漫画文件夹
                    self.logger.info(f"删除原漫画文件夹: {manga_dir}")
                    shutil.rmtree(manga_dir)

                except Exception as pdf_error:
                    self.logger.error(f"转换为PDF失败: {pdf_error}")
            else:
                self.logger.warning(f"未找到漫画文件夹: {manga_id}")

        except Exception as e:
            self.logger.error(f"下载漫画出错: {e}")
        finally:
            # 下载完成或失败后，移除正在下载的标记
            if manga_id in self.downloading_mangas:
                del self.downloading_mangas[manga_id]

    def add_download_task(
        self, user_id: str, manga_id: str, group_id: str, private: bool
    ) -> None:
        """
        添加下载任务到队列

        参数:
            user_id: 用户ID，用于回复下载状态
            manga_id: 漫画ID，指定要下载的漫画
            group_id: 群ID，用于在群聊中发送消息
            private: 是否为私聊，决定消息发送的目标
        """
        # 记录任务到状态跟踪字典
        self.queued_tasks[manga_id] = (user_id, group_id, private)
        # 将下载任务添加到队列
        self.download_queue.put((user_id, manga_id, group_id, private))
        self.logger.info(f"漫画ID {manga_id} 的下载任务已添加到队列")

    def check_manga_exists(self, manga_id: str) -> Tuple[bool, List[str]]:
        """
        检查漫画是否已存在

        参数:
            manga_id: 漫画ID

        返回:
            Tuple[bool, List[str]]: (是否存在, 找到的文件列表)
        """
        download_path = str(self.config_manager.get("MANGA_DOWNLOAD_PATH"))
        found = False
        found_files = []

        if not os.path.exists(download_path):
            return found, found_files

        # 遍历所有PDF文件
        for file_name in os.listdir(download_path):
            if file_name.endswith(".pdf"):
                # 检查文件名是否包含该漫画ID
                name_without_ext = os.path.splitext(file_name)[0]
                # 检查文件名是否以ID开头或包含ID-格式
                if (
                    name_without_ext.startswith(manga_id + "-")
                    or name_without_ext == manga_id
                ):
                    found = True
                    found_files.append(name_without_ext)

        return found, found_files

    def is_downloading(self, manga_id: str) -> bool:
        """检查漫画是否正在下载中"""
        return manga_id in self.downloading_mangas

    def get_download_progress(self) -> Tuple[List[str], List[str]]:
        """
        获取下载进度信息

        返回:
            Tuple[List[str], List[str]]: (正在下载的漫画列表, 队列等待的漫画列表)
        """
        downloading_mangas = list(self.downloading_mangas.keys())
        queued_mangas = list(self.queued_tasks.keys())
        return downloading_mangas, queued_mangas

    def stop_queue(self) -> None:
        """停止下载队列"""
        self.queue_running = False
        self.logger.info("下载队列已设置为停止状态")

    def cleanup_failed_downloads(self) -> None:
        """
        清理下载目录中下载失败的文件和文件夹
        - 删除未转换为PDF的漫画文件夹
        - 删除临时文件
        """
        download_path = str(self.config_manager.get("MANGA_DOWNLOAD_PATH"))
        self.logger.info(f"开始清理下载目录: {download_path}")

        if not os.path.exists(download_path):
            self.logger.info("下载目录不存在，跳过清理")
            return

        cleaned_count = 0

        # 遍历下载目录
        for item in os.listdir(download_path):
            item_path = os.path.join(download_path, item)

            # 检查是否为漫画文件夹（以数字ID开头）
            if os.path.isdir(item_path):
                # 检查文件夹名是否以数字开头（漫画ID）
                if re.match(r"^\d+", item):
                    # 检查是否有对应的PDF文件
                    pdf_file = os.path.join(download_path, f"{item}.pdf")
                    if not os.path.exists(pdf_file):
                        # 没有对应的PDF文件，说明下载或转换失败
                        self.logger.info(f"清理下载失败的漫画文件夹: {item}")
                        shutil.rmtree(item_path)
                        cleaned_count += 1

            # 检查是否为文件
            elif os.path.isfile(item_path):
                # 检查是否为临时文件
                if item.endswith(".tmp") or item.endswith(".temp"):
                    self.logger.info(f"清理临时文件: {item}")
                    os.remove(item_path)
                    cleaned_count += 1
                # 检查是否为以数字开头的非PDF文件（可能是下载失败的文件）
                elif re.match(r"^\d+", item) and not item.endswith(".pdf"):
                    self.logger.info(f"清理下载失败的文件: {item}")
                    os.remove(item_path)
                    cleaned_count += 1

        self.logger.info(f"下载目录清理完成，共清理 {cleaned_count} 个项目")
