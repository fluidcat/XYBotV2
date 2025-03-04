import asyncio
import base64
import tomllib
from random import sample

from PIL import Image, ImageDraw

from WechatAPI import WechatAPIClient
from database.XYBotDB import XYBotDB
from utils.decorators import *
from utils.plugin_base import PluginBase


class Gomoku(PluginBase):
    description = "五子棋游戏"
    author = "HenryXiaoYang"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/Gomoku/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["Gomoku"]

        self.enable = config["enable"]
        self.command_format = config["command-format"]
        self.timeout = config["timeout"]

        self.command = config["command"]
        self.create_game_commands = config["create-game-commands"]
        self.accept_game_commands = config["accept-game-commands"]
        self.play_game_commands = config["play-game-commands"]

        self.db = XYBotDB()

        # 游戏状态存储
        self.gomoku_games = {}  # 存储所有进行中的游戏
        self.gomoku_players = {}  # 存储玩家与游戏的对应关系

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        content = str(message["Content"]).strip(" ")
        command = content.split(" ")

        if command[0] in self.create_game_commands:
            await self.create_game(bot, message)
        elif command[0] in self.accept_game_commands:
            await self.accept_game(bot, message)
        elif command[0] in self.play_game_commands:
            await self.play_game(bot, message)
        elif command[0] in self.command:  # 当用户只输入"五子棋"时显示帮助
            await bot.send_text_message(message["FromWxid"], f"{self.command_format}")

    async def create_game(self, bot: WechatAPIClient, message: dict):
        """创建五子棋游戏"""
        error = ''
        room_id = message["FromWxid"]
        sender = message["SenderWxid"]

        if not message["IsGroup"]:
            error = '❌请在群聊中游玩五子棋'
        elif sender in self.gomoku_players:
            error = '❌您已经在一场游戏中了！'

        if error:
            await bot.send_text_message(message["FromWxid"], error)
            return

        # 获取被邀请者
        if len(message["Ats"]) != 1:
            await bot.send_text_message(room_id, '❌请@要邀请的玩家！')
            return

        invitee_wxid = message["Ats"][0]
        if invitee_wxid in self.gomoku_players:
            await bot.send_text_message(room_id, '❌对方已经在一场游戏中！')
            return

        # 创建游戏
        game_id = self._generate_game_id()
        self.gomoku_players[sender] = game_id
        self.gomoku_players[invitee_wxid] = game_id

        inviter_nick = await bot.get_nickname(sender)

        # 发送邀请消息
        out_message = (f"\n"
                       f"🎉您收到了来自 {inviter_nick} 的五子棋比赛邀请！\n"
                       f"\n"
                       f"⚙️请在{self.timeout}秒内发送:\n"
                       f"接受 {game_id}")
        await bot.send_at_message(room_id, out_message, [invitee_wxid])

        # 创建游戏数据
        self.gomoku_games[game_id] = {
            'black': sender,
            'white': invitee_wxid,
            'board': None,
            'turn': None,
            'status': 'inviting',
            'chatroom': room_id,
            'timeout_task': asyncio.create_task(
                self._handle_invite_timeout(bot, game_id, sender, invitee_wxid, room_id)
            )
        }

    async def accept_game(self, bot: WechatAPIClient, message: dict):
        """接受五子棋游戏"""
        error = ''
        room_id = message["FromWxid"]
        sender = message["SenderWxid"]

        if not message["IsGroup"]:
            error = '❌请在群聊中游玩五子棋'

        command = message["Content"].strip().split()
        if len(command) != 2:
            error = f'❌指令格式错误\n\n{self.command_format}'

        if error:
            await bot.send_text_message(message["FromWxid"], error)
            return

        game_id = command[1]

        if game_id not in self.gomoku_games:
            await bot.send_text_message(room_id, '❌该游戏不存在！')
            return

        game = self.gomoku_games[game_id]

        if game['white'] != sender:
            await bot.send_text_message(room_id, '❌您没有被邀请参加该游戏！')
            return

        if game['status'] != 'inviting':
            await bot.send_text_message(room_id, '❌该游戏已经开始或结束！')
            return

        if room_id != game['chatroom']:
            await bot.send_text_message(room_id, '❌请在原群聊中接受邀请！')
            return

        # 取消超时任务
        game['timeout_task'].cancel()

        # 初始化游戏
        game['status'] = 'playing'
        game['board'] = [[0 for _ in range(17)] for _ in range(17)]
        game['turn'] = game['black']

        # 发送游戏开始信息
        black_nick = await bot.get_nickname(game['black'])
        white_nick = await bot.get_nickname(game['white'])

        start_msg = (
            f"🎉五子棋游戏 {game_id} 开始！\n"
            f"\n"
            f"⚫️黑方：{black_nick}\n"
            f"⚪️白方：{white_nick}\n"
            f"\n"
            f"⏰每回合限时：{self.timeout}秒\n"
            f"\n"
            f"⚫️黑方先手！\n"
            f"\n"
            f"⚙️请发送: 下棋 坐标\n"
            f"例如: 下棋 C5"
        )
        await bot.send_text_message(room_id, start_msg)

        # 发送棋盘
        board_base64 = self._draw_board(game_id)
        await bot.send_image_message(room_id, board_base64)

        # 设置回合超时
        game['timeout_task'] = asyncio.create_task(
            self._handle_turn_timeout(bot, game_id, game['black'], room_id)
        )

    async def play_game(self, bot: WechatAPIClient, message: dict):
        """处理下棋操作"""
        error = ''
        room_id = message["FromWxid"]
        sender = message["SenderWxid"]

        if not message["IsGroup"]:
            error = '❌请在群聊中游玩五子棋'

        command = message["Content"].strip().split()
        if len(command) != 2:
            error = f'❌指令格式错误\n\n{self.command_format}'

        if error:
            await bot.send_text_message(message["FromWxid"], error)
            return

        if sender not in self.gomoku_players:
            await bot.send_text_message(room_id, '❌您不在任何游戏中！')
            return

        game_id = self.gomoku_players[sender]
        game = self.gomoku_games[game_id]

        if game['status'] != 'playing':
            await bot.send_text_message(room_id, '❌游戏已经结束！')
            return

        if sender != game['turn']:
            await bot.send_text_message(room_id, '❌还没到您的回合！')
            return

        # 解析坐标
        coord = command[1].upper()
        if not (len(coord) >= 2 and coord[0] in 'ABCDEFGHIJKLMNOPQ' and coord[1:].isdigit()):
            await bot.send_text_message(room_id, '❌无效的坐标格式！')
            return

        x = ord(coord[0]) - ord('A')
        y = 16 - int(coord[1:])

        if not (0 <= x <= 16 and 0 <= y <= 16):
            await bot.send_text_message(room_id, '❌坐标超出范围！')
            return

        if game['board'][y][x] != 0:
            await bot.send_text_message(room_id, '❌该位置已有棋子！')
            return

        # 取消超时任务
        game['timeout_task'].cancel()

        # 落子
        game['board'][y][x] = 1 if sender == game['black'] else 2

        # 绘制并发送新棋盘
        board_base64 = self._draw_board(game_id, highlight=(x, y))
        await bot.send_image_message(room_id, board_base64)

        # 检查是否获胜
        winner = self._check_winner(game_id)
        if winner:
            if winner == 'draw':
                await bot.send_text_message(room_id, f'🎉五子棋游戏 {game_id} 结束！\n\n平局！⚖️')
            else:
                winner_wxid = game['black'] if winner == 'black' else game['white']
                winner_nick = await bot.get_nickname(winner_wxid)
                await bot.send_text_message(
                    room_id,
                    f'🎉五子棋游戏 {game_id} 结束！\n\n'
                    f'{"⚫️黑方" if winner == "black" else "⚪️白方"}：{winner_nick} 获胜！🏆'
                )

            # 清理游戏数据
            self.gomoku_players.pop(game['black'])
            self.gomoku_players.pop(game['white'])
            self.gomoku_games.pop(game_id)
            return

        # 切换回合
        game['turn'] = game['white'] if sender == game['black'] else game['black']

        # 发送回合信息
        current_nick = await bot.get_nickname(sender)
        next_nick = await bot.get_nickname(game['turn'])
        current_color = '⚫️' if sender == game['black'] else '⚪️'
        next_color = '⚫️' if game['turn'] == game['black'] else '⚪️'

        turn_msg = (
            f"{current_color}{current_nick} 把棋子落在了 {coord}！\n"
            f"轮到 {next_color}{next_nick} 下子了！\n"
            f"\n"
            f"⏰限时：{self.timeout}秒\n"
            f"\n"
            f"⚙️请发送: 下棋 坐标\n"
            f"例如: 下棋 C5"
        )
        await bot.send_text_message(room_id, turn_msg)

        # 设置新的回合超时
        game['timeout_task'] = asyncio.create_task(
            self._handle_turn_timeout(bot, game_id, game['turn'], room_id)
        )

    def _generate_game_id(self) -> str:
        """生成游戏ID"""
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        while True:
            game_id = ''.join(sample(chars, 6))
            if game_id not in self.gomoku_games:
                return game_id

    def _draw_board(self, game_id: str, highlight: tuple = None) -> str:
        """绘制棋盘并返回base64编码"""
        board_img = Image.open('resource/images/gomoku_board_original.png')
        draw = ImageDraw.Draw(board_img)

        board = self.gomoku_games[game_id]['board']

        # 绘制棋子
        for y in range(17):
            for x in range(17):
                if board[y][x] != 0:
                    color = 'black' if board[y][x] == 1 else 'white'
                    draw.ellipse(
                        (24 + x * 27 - 8, 24 + y * 27 - 8,
                         24 + x * 27 + 8, 24 + y * 27 + 8),
                        fill=color
                    )

        # 绘制高亮
        if highlight:
            x, y = highlight
            draw.ellipse(
                (24 + x * 27 - 8, 24 + y * 27 - 8,
                 24 + x * 27 + 8, 24 + y * 27 + 8),
                outline='red',
                width=2
            )

        # 转换为bytes
        from io import BytesIO
        img_byte_arr = BytesIO()
        board_img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        # 转换为base64
        return base64.b64encode(img_byte_arr).decode()

    def _check_winner(self, game_id: str) -> str:
        """检查是否有获胜者"""
        board = self.gomoku_games[game_id]['board']

        # 检查所有方向
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for y in range(17):
            for x in range(17):
                if board[y][x] == 0:
                    continue

                for dx, dy in directions:
                    count = 1
                    nx, ny = x + dx, y + dy

                    while (0 <= nx < 17 and 0 <= ny < 17 and
                           board[ny][nx] == board[y][x]):
                        count += 1
                        nx += dx
                        ny += dy

                    if count >= 5:
                        return 'black' if board[y][x] == 1 else 'white'

        # 检查平局
        if all(board[y][x] != 0 for y in range(17) for x in range(17)):
            return 'draw'

        return ''

    async def _handle_invite_timeout(self, bot: WechatAPIClient, game_id: str,
                                     inviter: str, invitee: str, room_id: str):
        """处理邀请超时"""
        await asyncio.sleep(self.timeout)

        if (game_id in self.gomoku_games and
                self.gomoku_games[game_id]['status'] == 'inviting'):
            # 清理游戏数据
            self.gomoku_players.pop(inviter)
            self.gomoku_players.pop(invitee)
            self.gomoku_games.pop(game_id)

            await bot.send_at_message(
                room_id,
                f'❌五子棋游戏 {game_id} 邀请超时！',
                [inviter]
            )

    async def _handle_turn_timeout(self, bot: WechatAPIClient, game_id: str,
                                   player: str, room_id: str):
        """处理回合超时"""
        await asyncio.sleep(self.timeout)

        if (game_id in self.gomoku_games and
                self.gomoku_games[game_id]['status'] == 'playing' and
                self.gomoku_games[game_id]['turn'] == player):
            game = self.gomoku_games[game_id]
            winner = game['white'] if player == game['black'] else game['black']

            # 清理游戏数据
            self.gomoku_players.pop(game['black'])
            self.gomoku_players.pop(game['white'])
            self.gomoku_games.pop(game_id)

            loser_nick = await bot.get_nickname(player)
            winner_nick = await bot.get_nickname(winner)

            await bot.send_text_message(
                room_id,
                f''
                f'{loser_nick} 落子超时！\n'
                f'🏆 {winner_nick} 获胜！'
            )
