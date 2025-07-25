# -*- coding: utf-8 -*-
"""
XP 狼人杀插件 for LangBot + NapCat
"""
import os
import sys
from typing import Dict

# 把当前目录加入搜索路径，可直接 import game
sys.path.insert(0, os.path.dirname(__file__))
from game import game_instance   # 刚刚暴露的实例

# -------------------- LangBot 插件标准入口 --------------------
class LangBotPlugin:
    """LangBot 插件包装器"""

    def __init__(self):
        self.name = "XP狼人杀"
        self.version = "1.0.0"
        self.author = "AI"
        self.description = "XP狼人杀完整逻辑，支持 8-20 人"

    # LangBot 会调用这里
    async def handle_group_message(self, ctx: Dict) -> Dict:
        """
        ctx 结构:
        {
          "group_id": 123456,
          "user_id": 987654,
          "message": "#开始XP狼人杀",
          ...
        }
        返回:
        {"reply": "xxx", "auto_escape": False}
        """
        user_id = ctx["user_id"]
        message = ctx["message"].strip()
        reply = game_instance.handle_message(
            user_id, message, is_private=False
        )
        return {"reply": reply, "auto_escape": False}

    async def handle_private_message(self, ctx: Dict) -> Dict:
        user_id = ctx["user_id"]
        message = ctx["message"].strip()
        reply = game_instance.handle_message(
            user_id, message, is_private=True
        )
        return {"reply": reply, "auto_escape": False}

    # 供 LangBot 查询插件信息
    def get_plugin_info(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "commands": [
                "#创建游戏副本", "#加入游戏副本", "#开始游戏副本",
                "#设置XP", "#袭击", "#毒杀", "#决斗", "#带走",
                "#描述", "#投票", "#结束夜晚", "#结束讨论", "#结束投票",
                "#查看状态", "#存活玩家", "#结束游戏副本"
            ]
        }

# LangBot 会实例化并注册
plugin = LangBotPlugin()