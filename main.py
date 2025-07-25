# -*- coding: utf-8 -*-
"""
XP狼人杀插件 for LangBot 4.x
"""
from pkg.plugin.context import register, handler, BasePlugin, EventContext
from pkg.plugin.events import *
import asyncio
import os
import sys

# 让插件目录可 import
sys.path.insert(0, os.path.dirname(__file__))
from game import game_instance   # 引入游戏核心

class XPWolfPlugin(BasePlugin):
    def __init__(self, host):
        super().__init__(host)

    # ---------- 群普通消息 ----------
    @handler(GroupNormalMessageReceived)
    async def group_msg(self, ctx: EventContext):
        msg = ctx.event.text_message.strip()
        reply = game_instance.handle_message(
            ctx.event.sender_id, msg, is_private=False
        )
        if reply:
            ctx.add_return("reply", [reply])
            ctx.prevent_default()

    # ---------- 私聊普通消息 ----------
    @handler(PersonNormalMessageReceived)
    async def private_msg(self, ctx: EventContext):
        msg = ctx.event.text_message.strip()
        reply = game_instance.handle_message(
            ctx.event.sender_id, msg, is_private=True
        )
        if reply:
            ctx.add_return("reply", [reply])
            ctx.prevent_default()

    # ---------- 插件初始化 ----------
    async def initialize(self):
        pass

# 注册插件
register(XPWolfPlugin)