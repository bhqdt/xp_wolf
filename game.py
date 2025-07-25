import json
import random
import time
from typing import Dict, List, Optional, Tuple
import asyncio

class XPLangGame:
    def __init__(self):
        self.game_state = "waiting"  # waiting, night, day, discussion, voting, ended
        self.players = {}  # {qq_id: {"number": int, "xp": str, "alive": bool, "role": str}}
        self.wolf_players = []  # 狼人QQ号列表
        self.special_roles = {}  # {role_name: qq_id}
        self.dead_players = []  # 死亡玩家QQ号列表
        self.current_player_index = 0
        self.discussion_order = []
        self.votes = {}  # {voter_qq: target_qq}
        self.vote_results = {}
        self.night_actions = {}  # 夜间行动记录
        self.knight_used = False
        self.wolf_king_killed = None  # 狼王技能目标
        self.current_victim = None
        self.game_creator = None
        self.discussion_timer = None
        self.free_discussion_time = 150  # 2分30秒
        self.player_description_time = 60  # 1分钟
        self.last_speech_time = 60  # 遗言时间
        
    def reset_game(self):
        """重置游戏状态"""
        self.game_state = "waiting"
        self.players = {}
        self.wolf_players = []
        self.special_roles = {}
        self.dead_players = []
        self.current_player_index = 0
        self.discussion_order = []
        self.votes = {}
        self.vote_results = {}
        self.night_actions = {}
        self.knight_used = False
        self.wolf_king_killed = None
        self.current_victim = None
        self.game_creator = None
        if self.discussion_timer:
            self.discussion_timer.cancel()
            self.discussion_timer = None

    def start_game(self, player_list: List[Tuple[int, int]]) -> str:
        """开始游戏，player_list为[(qq_id, number), ...]"""
        if len(player_list) < 8 or len(player_list) > 20:
            return f"游戏人数必须在8-20人之间，当前{len(player_list)}人"
        
        # 初始化玩家
        for qq_id, number in player_list:
            self.players[qq_id] = {
                "number": number,
                "xp": "",
                "alive": True,
                "role": "平民"
            }
        
        # 确定特殊角色配置
        player_count = len(self.players)
        if player_count <= 10:
            wolf_count = 1
            special_config = {"狼人": 1}
        elif player_count <= 15:
            wolf_count = 1
            special_config = {"狼王": 1, "狼人": 1, "骑士": 1}
        else:
            wolf_count = 1
            special_config = {"狼王": 2, "狼人": 1, "骑士": 1, "女巫": 1}
        
        # 随机分配特殊角色
        available_players = list(self.players.keys())
        random.shuffle(available_players)
        
        # 分配狼人
        wolf_players = available_players[:wolf_count]
        for qq_id in wolf_players:
            self.players[qq_id]["role"] = "狼人"
            self.wolf_players.append(qq_id)
        
        # 分配特殊角色
        start_index = wolf_count
        for role, count in special_config.items():
            if role == "狼人":
                continue
            for i in range(count):
                if start_index + i < len(available_players):
                    qq_id = available_players[start_index + i]
                    self.players[qq_id]["role"] = role
                    self.special_roles[role] = qq_id
                    if role != "狼人":  # 狼人已经在上面处理过了
                        start_index += 1
        
        self.game_state = "night"
        return self.get_night_info()

    def set_player_xp(self, qq_id: int, xp: str) -> str:
        """设置玩家XP"""
        if qq_id not in self.players:
            return "你不在游戏中"
        
        self.players[qq_id]["xp"] = xp
        return f"已记录你的XP: {xp}"

    def get_night_info(self) -> str:
        """获取夜间信息"""
        info = "游戏副本已开启，请各位玩家私聊主持人发送自己的XP\n"
        info += "狼人阵营请注意，夜晚降临，请私聊主持人协商袭击目标\n"
        info += f"当前存活玩家: {len([p for p in self.players.values() if p['alive']])}人\n"
        return info

    def wolf_attack(self, wolf_qq: int, target_qq: int) -> str:
        """狼人袭击"""
        if wolf_qq not in self.wolf_players:
            return "你不是狼人"
        
        if target_qq not in self.players or not self.players[target_qq]["alive"]:
            return "目标玩家不存在或已死亡"
        
        self.night_actions["attack"] = target_qq
        return f"已记录袭击目标: {self.players[target_qq]['number']}号玩家"

    def witch_poison(self, witch_qq: int, target_qq: int) -> str:
        """女巫毒杀"""
        if witch_qq not in self.special_roles.get("女巫", []):
            return "你不是女巫"
        
        if target_qq not in self.players or not self.players[target_qq]["alive"]:
            return "目标玩家不存在或已死亡"
        
        if "poison_used" in self.night_actions:
            return "毒药已使用"
        
        self.night_actions["poison"] = target_qq
        self.night_actions["poison_used"] = True
        return f"已毒杀{self.players[target_qq]['number']}号玩家"

    def end_night(self) -> str:
        """结束夜晚，进入白天"""
        victims = []
        
        # 处理袭击
        if "attack" in self.night_actions:
            victim_qq = self.night_actions["attack"]
            if self.players[victim_qq]["alive"]:
                victims.append(("袭击", victim_qq))
        
        # 处理毒杀
        if "poison" in self.night_actions:
            victim_qq = self.night_actions["poison"]
            if self.players[victim_qq]["alive"]:
                victims.append(("毒杀", victim_qq))
        
        # 处理死亡
        death_info = ""
        for reason, victim_qq in victims:
            self.players[victim_qq]["alive"] = False
            self.dead_players.append(victim_qq)
            death_info += f"\n{reason}死亡: {self.players[victim_qq]['number']}号玩家，XP: {self.players[victim_qq]['xp']}"
            
            # 检查狼王技能
            if self.players[victim_qq]["role"] == "狼王" and reason != "毒杀":
                self.wolf_king_killed = victim_qq
        
        self.game_state = "day"
        info = "天亮了！" + death_info
        
        # 检查胜利条件
        win_result = self.check_win_condition()
        if win_result:
            info += f"\n\n游戏结束！{win_result}"
            self.game_state = "ended"
            return info
        
        # 准备讨论顺序
        alive_players = [(qq, p["number"]) for qq, p in self.players.items() if p["alive"]]
        alive_players.sort(key=lambda x: x[1])  # 按编号排序
        self.discussion_order = [qq for qq, _ in alive_players]
        self.current_player_index = 0
        
        info += f"\n\n开始描述环节，请{self.players[self.discussion_order[0]]['number']}号玩家开始描述自己的XP"
        return info

    def player_describe(self, qq_id: int, description: str) -> str:
        """玩家描述XP"""
        if self.game_state != "day":
            return "当前不是描述环节"
        
        if qq_id != self.discussion_order[self.current_player_index]:
            return "还没轮到你描述"
        
        # 记录描述内容（这里简化处理，实际可能需要存储）
        info = f"{self.players[qq_id]['number']}号玩家描述完毕"
        
        # 切换到下一个玩家
        self.current_player_index += 1
        if self.current_player_index < len(self.discussion_order):
            next_qq = self.discussion_order[self.current_player_index]
            info += f"\n请{self.players[next_qq]['number']}号玩家描述自己的XP"
        else:
            info += "\n所有玩家描述完毕，进入自由讨论时间"
            self.game_state = "discussion"
            # 启动自由讨论计时器
            # 这里简化处理，实际应该启动异步计时器
            
        return info

    def knight_duel(self, knight_qq: int, target_qq: int) -> str:
        """骑士决斗"""
        if "骑士" not in self.special_roles or self.special_roles["骑士"] != knight_qq:
            return "你不是骑士"
        
        if self.knight_used:
            return "骑士技能已使用"
        
        if target_qq not in self.players or not self.players[target_qq]["alive"]:
            return "目标玩家不存在或已死亡"
        
        if target_qq == knight_qq:
            return "不能对自己使用技能"
        
        self.knight_used = True
        
        if self.players[target_qq]["role"] in ["狼人", "狼王"]:
            # 击杀狼人
            self.players[target_qq]["alive"] = False
            self.dead_players.append(target_qq)
            info = f"骑士决斗成功！{self.players[target_qq]['number']}号玩家是狼人，已被击杀！"
            info += f"\nXP: {self.players[target_qq]['xp']}"
            self.game_state = "night"  # 直接进入夜晚
        else:
            # 骑士死亡
            self.players[knight_qq]["alive"] = False
            self.dead_players.append(knight_qq)
            info = f"骑士决斗失败！{self.players[knight_qq]['number']}号玩家是好人，骑士阵亡！"
            info += f"\nXP: {self.players[knight_qq]['xp']}"
        
        return info

    def wolf_king_skill(self, wolf_king_qq: int, target_qq: int) -> str:
        """狼王技能"""
        if self.wolf_king_killed != wolf_king_qq:
            return "你不能使用狼王技能"
        
        if target_qq not in self.players or not self.players[target_qq]["alive"]:
            return "目标玩家不存在或已死亡"
        
        if target_qq == wolf_king_qq:
            return "不能对自己使用技能"
        
        self.players[target_qq]["alive"] = False
        self.dead_players.append(target_qq)
        self.wolf_king_killed = None  # 重置
        
        info = f"狼王发动技能！{self.players[target_qq]['number']}号玩家被击杀！"
        info += f"\nXP: {self.players[target_qq]['xp']}"
        return info

    def start_voting(self) -> str:
        """开始投票"""
        self.game_state = "voting"
        self.votes = {}
        alive_count = len([p for p in self.players.values() if p["alive"]])
        return f"开始投票环节，请存活的{alive_count}名玩家投票"

    def vote(self, voter_qq: int, target_qq: int) -> str:
        """投票"""
        if self.game_state != "voting":
            return "当前不是投票环节"
        
        if voter_qq not in self.players or not self.players[voter_qq]["alive"]:
            return "你已死亡，无法投票"
        
        if target_qq not in self.players or not self.players[target_qq]["alive"]:
            return "目标玩家不存在或已死亡"
        
        self.votes[voter_qq] = target_qq
        return f"你已投票给{self.players[target_qq]['number']}号玩家"

    def end_voting(self) -> str:
        """结束投票"""
        # 统计票数
        vote_count = {}
        for target_qq in self.votes.values():
            vote_count[target_qq] = vote_count.get(target_qq, 0) + 1
        
        # 找出最高票数
        if not vote_count:
            return "无人投票，进入夜晚"
        
        max_votes = max(vote_count.values())
        max_vote_players = [qq for qq, count in vote_count.items() if count == max_votes]
        
        if len(max_vote_players) > 1:
            info = "平票，无人出局"
        else:
            victim_qq = max_vote_players[0]
            self.players[victim_qq]["alive"] = False
            self.dead_players.append(victim_qq)
            info = f"{self.players[victim_qq]['number']}号玩家被投票出局！"
            info += f"\nXP: {self.players[victim_qq]['xp']}"
            
            # 检查狼王技能
            if self.players[victim_qq]["role"] == "狼王":
                self.wolf_king_killed = victim_qq
        
        # 显示投票结果
        info += "\n投票结果："
        for target_qq, count in vote_count.items():
            voters = [self.players[voter]["number"] for voter, t in self.votes.items() if t == target_qq]
            info += f"\n{self.players[target_qq]['number']}号玩家: {count}票 ({', '.join(map(str, voters))}号)"
        
        # 检查胜利条件
        win_result = self.check_win_condition()
        if win_result:
            info += f"\n\n游戏结束！{win_result}"
            self.game_state = "ended"
            return info
        
        self.game_state = "night"
        return info

    def check_win_condition(self) -> Optional[str]:
        """检查胜利条件"""
        alive_players = [p for p in self.players.values() if p["alive"]]
        alive_wolf = [p for p in alive_players if p["role"] in ["狼人", "狼王"]]
        alive_good = [p for p in alive_players if p["role"] not in ["狼人", "狼王"]]
        
        if len(alive_wolf) == 0:
            return "好人阵营获胜！"
        elif len(alive_good) <= len(alive_wolf):
            return "狼人阵营获胜！"
        
        return None

    def get_game_status(self) -> str:
        """获取游戏状态"""
        if self.game_state == "waiting":
            return "游戏等待开始"
        elif self.game_state == "night":
            return "夜晚阶段"
        elif self.game_state == "day":
            return "描述阶段"
        elif self.game_state == "discussion":
            return "自由讨论阶段"
        elif self.game_state == "voting":
            return "投票阶段"
        elif self.game_state == "ended":
            return "游戏结束"
        
        return "未知状态"

    def get_alive_players(self) -> str:
        """获取存活玩家列表"""
        alive_players = [p for p in self.players.values() if p["alive"]]
        alive_players.sort(key=lambda x: x["number"])
        info = "存活玩家："
        for player in alive_players:
            info += f"\n{player['number']}号 - {player['role']}"
        return info

    def end_game(self) -> str:
        """结束游戏，公布所有身份"""
        info = "游戏结束，所有玩家身份公布：\n"
        sorted_players = sorted(self.players.values(), key=lambda x: x["number"])
        for player in sorted_players:
            status = "存活" if player["alive"] else "死亡"
            info += f"{player['number']}号 [{status}] {player['role']} - XP: {player['xp']}\n"
        
        self.reset_game()
        return info

# QQ机器人插件主类
class XPLangBotPlugin:
    def __init__(self):
        self.game = XPLangGame()
        self.player_queue = []  # 玩家接龙队列
    
    def handle_message(self, user_id: int, message: str, is_private: bool = False) -> str:
        """处理消息"""
        try:
            # 管理员命令
            if message.startswith("#创建游戏副本"):
                if self.game.game_state != "waiting":
                    return "游戏已在进行中"
                self.game.game_creator = user_id
                self.player_queue = []
                return "游戏副本已创建，请玩家们发送【#加入游戏副本】进行接龙"
            
            elif message.startswith("#加入游戏副本"):
                if self.game.game_state != "waiting" or not self.game.game_creator:
                    return "游戏副本未创建或已开始"
                
                if user_id in [p[0] for p in self.player_queue]:
                    return "你已加入队列"
                
                self.player_queue.append([user_id, 0])  # [qq_id, number]
                return f"你已加入游戏副本，当前人数: {len(self.player_queue)}"
            
            elif message.startswith("#开始游戏副本"):
                if user_id != self.game.game_creator:
                    return "只有创建者可以开始游戏"
                
                if len(self.player_queue) < 8:
                    return f"游戏副本至少需要8人，当前{len(self.player_queue)}人"
                
                # 分配序号
                for i, (qq_id, _) in enumerate(self.player_queue):
                    self.player_queue[i][1] = i + 1
                
                # 开始游戏
                result = self.game.start_game(self.player_queue)
                return result
            
            elif message.startswith("#我的身份"):
                if user_id not in self.game.players:
                    return "你不在游戏中"
                
                player = self.game.players[user_id]
                status = "存活" if player["alive"] else "死亡"
                return f"你的身份：{player['number']}号 [{status}] {player['role']}"
            
            # 玩家设置XP
            elif message.startswith("#设置XP"):
                if self.game.game_state == "waiting":
                    return "游戏未开始"
                
                xp = message[6:].strip()  # 去掉"#设置XP"
                if not xp:
                    return "请提供你的XP"
                
                return self.game.set_player_xp(user_id, xp)
            
            # 狼人命令
            elif message.startswith("#袭击"):
                if self.game.game_state != "night":
                    return "当前不是夜晚"
                
                try:
                    target_number = int(message[3:])
                    target_qq = None
                    for qq, player in self.game.players.items():
                        if player["number"] == target_number:
                            target_qq = qq
                            break
                    
                    if not target_qq:
                        return "找不到目标玩家"
                    
                    return self.game.wolf_attack(user_id, target_qq)
                except ValueError:
                    return "请提供正确的玩家编号"
            
            # 女巫命令
            elif message.startswith("#毒杀"):
                if self.game.game_state != "night":
                    return "当前不是夜晚"
                
                try:
                    target_number = int(message[3:])
                    target_qq = None
                    for qq, player in self.game.players.items():
                        if player["number"] == target_number:
                            target_qq = qq
                            break
                    
                    if not target_qq:
                        return "找不到目标玩家"
                    
                    return self.game.witch_poison(user_id, target_qq)
                except ValueError:
                    return "请提供正确的玩家编号"
            
            # 骑士命令
            elif message.startswith("#决斗"):
                if self.game.game_state not in ["day", "discussion"]:
                    return "当前不能使用骑士技能"
                
                try:
                    target_number = int(message[3:])
                    target_qq = None
                    for qq, player in self.game.players.items():
                        if player["number"] == target_number:
                            target_qq = qq
                            break
                    
                    if not target_qq:
                        return "找不到目标玩家"
                    
                    result = self.game.knight_duel(user_id, target_qq)
                    
                    # 如果骑士技能导致进入夜晚，需要处理
                    if self.game.game_state == "night":
                        return result + "\n\n" + self.game.get_night_info()
                    
                    return result
                except ValueError:
                    return "请提供正确的玩家编号"
            
            # 狼王技能
            elif message.startswith("#带走"):
                try:
                    target_number = int(message[3:])
                    target_qq = None
                    for qq, player in self.game.players.items():
                        if player["number"] == target_number:
                            target_qq = qq
                            break
                    
                    if not target_qq:
                        return "找不到目标玩家"
                    
                    return self.game.wolf_king_skill(user_id, target_qq)
                except ValueError:
                    return "请提供正确的玩家编号"
            
            # 描述XP
            elif message.startswith("#描述"):
                description = message[3:].strip()
                return self.game.player_describe(user_id, description)
            
            # 投票
            elif message.startswith("#投票"):
                try:
                    target_number = int(message[3:])
                    target_qq = None
                    for qq, player in self.game.players.items():
                        if player["number"] == target_number:
                            target_qq = qq
                            break
                    
                    if not target_qq:
                        return "找不到目标玩家"
                    
                    return self.game.vote(user_id, target_qq)
                except ValueError:
                    return "请提供正确的玩家编号"
            
            # 主持人命令
            elif message.startswith("#结束夜晚"):
                if user_id != self.game.game_creator:
                    return "只有主持人可以执行此操作"
                
                if self.game.game_state != "night":
                    return "当前不是夜晚"
                
                return self.game.end_night()
            
            elif message.startswith("#结束讨论"):
                if user_id != self.game.game_creator:
                    return "只有主持人可以执行此操作"
                
                if self.game.game_state != "discussion":
                    return "当前不是讨论时间"
                
                return self.game.start_voting()
            
            elif message.startswith("#结束投票"):
                if user_id != self.game.game_creator:
                    return "只有主持人可以执行此操作"
                
                if self.game.game_state != "voting":
                    return "当前不是投票时间"
                
                result = self.game.end_voting()
                if self.game.game_state == "night":
                    result += "\n\n" + self.game.get_night_info()
                return result
            
            elif message.startswith("#查看状态"):
                if user_id != self.game.game_creator:
                    return "只有主持人可以执行此操作"
                
                return self.game.get_game_status()
            
            elif message.startswith("#存活玩家"):
                return self.game.get_alive_players()
            
            elif message.startswith("#结束游戏副本"):
                if user_id != self.game.game_creator:
                    return "只有主持人可以执行此操作"
                
                return self.game.end_game()
            
            else:
                return "未知命令，请查看游戏副本规则"
                
        except Exception as e:
            return f"处理命令时出错: {str(e)}"

game_instance = XPLangBotPlugin()