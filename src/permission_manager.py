from typing import List, Optional


class PermissionManager:
    """权限管理器，负责用户权限检查"""

    def __init__(
        self,
        group_whitelist: List[str],
        private_whitelist: List[str],
        global_blacklist: List[str],
    ) -> None:
        """
        初始化权限管理器

        Args:
            group_whitelist: 群组白名单
            private_whitelist: 私信白名单
            global_blacklist: 全局黑名单
        """
        self.group_whitelist = group_whitelist
        self.private_whitelist = private_whitelist
        self.global_blacklist = global_blacklist

    def check_user_permission(
        self, user_id: str, group_id: Optional[str] = None, private: bool = True
    ) -> bool:
        """
        检查用户是否有权限使用机器人

        权限检查规则：
        1. 全局黑名单优先：如果用户在全局黑名单中，直接拒绝
        2. 白名单检查：
           - 私聊：检查用户是否在私信白名单中（如果白名单不为空）
           - 群聊：检查群组是否在群组白名单中（如果白名单不为空）
        3. 白名单为空表示不限制

        Args:
            user_id: 用户ID
            group_id: 群组ID（群聊时提供）
            private: 是否为私聊

        Returns:
            bool: 用户是否有权限使用机器人
        """
        # 全局黑名单检查（最高优先级）
        if user_id in self.global_blacklist:
            return False

        # 私聊权限检查
        if private:
            # 如果私信白名单不为空，则检查用户是否在白名单中
            if self.private_whitelist and user_id not in self.private_whitelist:
                return False
        # 群聊权限检查
        else:
            # 如果群组白名单不为空，则检查群组是否在白名单中
            if (
                group_id
                and self.group_whitelist
                and group_id not in self.group_whitelist
            ):
                return False

        # 权限检查通过
        return True
