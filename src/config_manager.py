import os
import re
from typing import Dict, List, Union


class ConfigManager:
    """配置管理器，负责加载和管理机器人配置"""

    def __init__(self) -> None:
        """初始化配置管理器"""
        self.config: Dict[str, Union[str, int]] = {}
        self.group_whitelist: List[str] = []
        self.private_whitelist: List[str] = []
        self.global_blacklist: List[str] = []

    def load_config(self) -> None:
        """加载环境变量和配置"""
        from dotenv import load_dotenv

        # 加载环境变量
        load_dotenv()

        # 简化token配置，只使用NAPCAT_TOKEN作为唯一的token配置项
        token = os.getenv("NAPCAT_TOKEN", "")  # 只使用NAPCAT_TOKEN

        # 构建带token的WebSocket URL（如果有token）
        base_ws_url = os.getenv("NAPCAT_WS_URL", "ws://localhost:8080/qq")
        if token:
            # 检查URL是否已经包含查询参数
            if "?" in base_ws_url:
                ws_url = f"{base_ws_url}&token={token}"
            else:
                ws_url = f"{base_ws_url}?token={token}"
        else:
            ws_url = base_ws_url

        # 获取下载路径配置
        download_path = os.getenv("MANGA_DOWNLOAD_PATH", "./downloads")
        # 处理Linux系统中的波浪号(~)路径，将其扩展为用户主目录
        if download_path.startswith("~"):
            download_path = os.path.expanduser(download_path)
        # 将相对路径转换为绝对路径，确保父级目录引用能正确解析
        absolute_download_path = os.path.abspath(download_path)

        self.config = {
            "MANGA_DOWNLOAD_PATH": absolute_download_path,
            "NAPCAT_WS_URL": ws_url,  # 存储完整的WebSocket URL（可能包含token）
            "NAPCAT_TOKEN": token,  # 使用NAPCAT_TOKEN作为配置键
        }

        # 加载黑白名单配置
        self.group_whitelist = self._parse_id_list(os.getenv("GROUP_WHITELIST", ""))
        self.private_whitelist = self._parse_id_list(os.getenv("PRIVATE_WHITELIST", ""))
        self.global_blacklist = self._parse_id_list(os.getenv("GLOBAL_BLACKLIST", ""))

    def _parse_id_list(self, id_string: str) -> List[str]:
        """
        解析ID列表字符串，将逗号分隔的ID转换为列表

        Args:
            id_string: 逗号分隔的ID字符串

        Returns:
            清理后的ID列表
        """
        if not id_string or not id_string.strip():
            return []

        # 分割字符串并清理每个ID
        ids = [id.strip() for id in id_string.split(",") if id.strip()]
        return ids

    def get(self, key: str, default: Union[str, int] = "") -> Union[str, int]:
        """获取配置值"""
        return self.config.get(key, default)

    def set(self, key: str, value: Union[str, int]) -> None:
        """设置配置值"""
        self.config[key] = value

    def create_download_directory(self) -> None:
        """创建下载目录"""
        download_path = str(self.config["MANGA_DOWNLOAD_PATH"])
        os.makedirs(download_path, exist_ok=True)
