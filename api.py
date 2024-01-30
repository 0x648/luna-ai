import logging, os, sys, json
import threading
import schedule, time
import random
import aiohttp, asyncio
import traceback
import copy
import webbrowser

from functools import partial

import http.cookies
from typing import *

from flask import Flask, send_from_directory, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from utils.common import Common
from utils.config import Config
from utils.logger import Configure_logger
from utils.my_handle import My_handle

"""
全局变量
"""
# 创建一个全局变量，用于表示程序是否正在运行
running_flag = False

# 创建一个子进程对象，用于存储正在运行的外部程序
running_process = None
config = None
common = None
my_handle = None
# last_liveroom_data = None
last_username_list = None
# 空闲时间计数器
global_idle_time = 0
# 键盘监听线程
thread = None
do_listen_and_comment_thread = None
stop_do_listen_and_comment_thread_event = None


# 这里填一个已登录账号的cookie。不填cookie也可以连接，但是收到弹幕的用户名会打码，UID会变成0
SESSDATA = ''
session: Optional[aiohttp.ClientSession] = None

# 最新的直播间数据
last_liveroom_data = {
    'OnlineUserCount': 0, 
    'TotalUserCount': 0, 
    'TotalUserCountStr': '0', 
    'OnlineUserCountStr': '0', 
    'MsgId': 0, 
    'User': None, 
    'Content': '当前直播间人数 0，累计直播间人数 0', 
    'RoomId': 0
}

# 最新入场的用户名列表
last_username_list = [""]

common = Common()

# 日志文件路径
log_path = "./log/log-" + common.get_bj_time(1) + ".txt"
Configure_logger(log_path)

# 获取 werkzeug 库的日志记录器
werkzeug_logger = logging.getLogger("werkzeug")
# 设置 httpx 日志记录器的级别为 WARNING
werkzeug_logger.setLevel(logging.WARNING)

# 点火起飞
def start_server(config_path, sub_thread_exit_events):
    global log_path, config, common, my_handle, last_username_list, last_liveroom_data
    global SESSDATA
    global thread, do_listen_and_comment_thread, stop_do_listen_and_comment_thread_event

    # 创建和启动子线程
    sub_threads = []

    config = Config(config_path)

    # 获取 httpx 库的日志记录器
    httpx_logger = logging.getLogger("httpx")
    # 设置 httpx 日志记录器的级别为 WARNING
    httpx_logger.setLevel(logging.WARNING)

    my_handle = My_handle(config_path)
    if my_handle is None:
        logging.error("程序初始化失败！")
        os._exit(0)

    # 添加用户名到最新的用户名列表
    def add_username_to_last_username_list(data):
        global last_username_list

        # 添加数据到 最新入场的用户名列表
        last_username_list.append(data)
        
        # 保留最新的3个数据
        last_username_list = last_username_list[-3:]


    # 定时任务
    def schedule_task(index):
        logging.debug("定时任务执行中...")
        hour, min = common.get_bj_time(6)

        if 0 <= hour and hour < 6:
            time = f"凌晨{hour}点{min}分"
        elif 6 <= hour and hour < 9:
            time = f"早晨{hour}点{min}分"
        elif 9 <= hour and hour < 12:
            time = f"上午{hour}点{min}分"
        elif hour == 12:
            time = f"中午{hour}点{min}分"
        elif 13 <= hour and hour < 18:
            time = f"下午{hour - 12}点{min}分"
        elif 18 <= hour and hour < 20:
            time = f"傍晚{hour - 12}点{min}分"
        elif 20 <= hour and hour < 24:
            time = f"晚上{hour - 12}点{min}分"


        # 根据对应索引从列表中随机获取一个值
        random_copy = random.choice(config.get("schedule")[index]["copy"])

        # 假设有多个未知变量，用户可以在此处定义动态变量
        variables = {
            'time': time,
            'user_num': "N",
            'last_username': last_username_list[-1],
        }

        # 使用字典进行字符串替换
        if any(var in random_copy for var in variables):
            content = random_copy.format(**{var: value for var, value in variables.items() if var in random_copy})
        else:
            content = random_copy

        data = {
            "platform": "哔哩哔哩",
            "username": None,
            "content": content
        }

        logging.info(f"定时任务：{content}")

        my_handle.process_data(data, "schedule")


    # 启动定时任务
    def run_schedule(exit_event):
        global config

        try:
            for index, task in enumerate(config.get("schedule")):
                if task["enable"]:
                    # logging.info(task)
                    # 设置定时任务，每隔n秒执行一次
                    schedule.every(task["time"]).seconds.do(partial(schedule_task, index))
        except Exception as e:
            logging.error(traceback.format_exc())

        while True:
            schedule.run_pending()
            # time.sleep(1)  # 控制每次循环的间隔时间，避免过多占用 CPU 资源

            if exit_event.is_set():
                return


    if any(item['enable'] for item in config.get("schedule")):
        # 创建定时任务子线程并启动
        schedule_thread = threading.Thread(target=run_schedule, args=(sub_thread_exit_events[1],))
        schedule_thread.start()
        sub_threads.append(schedule_thread)


    # 启动动态文案
    async def run_trends_copywriting(exit_event):
        global config

        try:
            if False == config.get("trends_copywriting", "enable"):
                return
            
            logging.info(f"动态文案任务线程运行中...")

            while True:
                # 文案文件路径列表
                copywriting_file_path_list = []

                # 获取动态文案列表
                for copywriting in config.get("trends_copywriting", "copywriting"):
                    # 获取文件夹内所有文件的文件绝对路径，包括文件扩展名
                    for tmp in common.get_all_file_paths(copywriting["folder_path"]):
                        copywriting_file_path_list.append(tmp)

                    # 是否开启随机播放
                    if config.get("trends_copywriting", "random_play"):
                        random.shuffle(copywriting_file_path_list)

                    logging.debug(f"copywriting_file_path_list={copywriting_file_path_list}")

                    # 遍历文案文件路径列表  
                    for copywriting_file_path in copywriting_file_path_list:
                        # 获取文案文件内容
                        copywriting_file_content = common.read_file_return_content(copywriting_file_path)
                        # 是否启用提示词对文案内容进行转换
                        if copywriting["prompt_change_enable"]:
                            data_json = {
                                "username": "trends_copywriting",
                                "content": copywriting["prompt_change_content"] + copywriting_file_content
                            }

                            # 调用函数进行LLM处理，以及生成回复内容，进行音频合成，需要好好考虑考虑实现
                            data_json["content"] = my_handle.llm_handle(config.get("chat_type"), data_json)
                        else:
                            data_json = {
                                "username": "trends_copywriting",
                                "content": copywriting_file_content
                            }

                        logging.debug(f'copywriting_file_content={copywriting_file_content},content={data_json["content"]}')

                        # 空数据判断
                        if data_json["content"] != None and data_json["content"] != "":
                            # 发给直接复读进行处理
                            my_handle.reread_handle(data_json)

                            await asyncio.sleep(config.get("trends_copywriting", "play_interval"))
        
                if exit_event.is_set():
                    return
        except Exception as e:
            logging.error(traceback.format_exc())

    if config.get("trends_copywriting", "enable"):
        # 创建动态文案子线程并启动
        trends_copywriting_thread = threading.Thread(target=lambda: asyncio.run(run_trends_copywriting()), args=(sub_thread_exit_events[2],))
        trends_copywriting_thread.start()
        sub_threads.append(trends_copywriting_thread)

    # 闲时任务
    async def idle_time_task(exit_event):
        global config, global_idle_time

        try:
            if False == config.get("idle_time_task", "enable"):
                return
            
            logging.info(f"闲时任务线程运行中...")

            # 记录上一次触发的任务类型
            last_mode = 0
            comment_copy_list = None
            local_audio_path_list = None

            overflow_time = int(config.get("idle_time_task", "idle_time"))
            # 是否开启了随机闲时时间
            if config.get("idle_time_task", "random_time"):
                overflow_time = random.randint(0, overflow_time)
            
            logging.info(f"闲时时间={overflow_time}秒")

            def load_data_list(type):
                if type == "comment":
                    tmp = config.get("idle_time_task", "comment", "copy")
                elif type == "local_audio":
                    tmp = config.get("idle_time_task", "local_audio", "path")
                tmp2 = copy.copy(tmp)
                return tmp2

            comment_copy_list = load_data_list("comment")
            local_audio_path_list = load_data_list("local_audio")

            logging.debug(f"comment_copy_list={comment_copy_list}")
            logging.debug(f"local_audio_path_list={local_audio_path_list}")

            while True:
                # 每隔一秒的睡眠进行闲时计数
                await asyncio.sleep(1)
                global_idle_time = global_idle_time + 1

                # 闲时计数达到指定值，进行闲时任务处理
                if global_idle_time >= overflow_time:
                    # 闲时计数清零
                    global_idle_time = 0

                    # 闲时任务处理
                    if config.get("idle_time_task", "comment", "enable"):
                        if last_mode == 0 or not config.get("idle_time_task", "local_audio", "enable"):
                            # 是否开启了随机触发
                            if config.get("idle_time_task", "comment", "random"):
                                logging.debug("切换到文案触发模式")
                                if comment_copy_list != []:
                                    # 随机打乱列表中的元素
                                    random.shuffle(comment_copy_list)
                                    comment_copy = comment_copy_list.pop(0)
                                else:
                                    # 刷新list数据
                                    comment_copy_list = load_data_list("comment")
                                    # 随机打乱列表中的元素
                                    random.shuffle(comment_copy_list)
                                    comment_copy = comment_copy_list.pop(0)
                            else:
                                if comment_copy_list != []:
                                    comment_copy = comment_copy_list.pop(0)
                                else:
                                    # 刷新list数据
                                    comment_copy_list = load_data_list("comment")
                                    comment_copy = comment_copy_list.pop(0)

                            # 发送给处理函数
                            data = {
                                "platform": "哔哩哔哩2",
                                "username": "闲时任务",
                                "type": "comment",
                                "content": comment_copy
                            }

                            my_handle.process_data(data, "idle_time_task")

                            # 模式切换
                            last_mode = 1

                            overflow_time = int(config.get("idle_time_task", "idle_time"))
                            # 是否开启了随机闲时时间
                            if config.get("idle_time_task", "random_time"):
                                overflow_time = random.randint(0, overflow_time)
                            logging.info(f"闲时时间={overflow_time}秒")

                            continue
                    
                    if config.get("idle_time_task", "local_audio", "enable"):
                        if last_mode == 1 or (not config.get("idle_time_task", "comment", "enable")):
                            logging.debug("切换到本地音频模式")

                            # 是否开启了随机触发
                            if config.get("idle_time_task", "local_audio", "random"):
                                if local_audio_path_list != []:
                                    # 随机打乱列表中的元素
                                    random.shuffle(local_audio_path_list)
                                    local_audio_path = local_audio_path_list.pop(0)
                                else:
                                    # 刷新list数据
                                    local_audio_path_list = load_data_list("local_audio")
                                    # 随机打乱列表中的元素
                                    random.shuffle(local_audio_path_list)
                                    local_audio_path = local_audio_path_list.pop(0)
                            else:
                                if local_audio_path_list != []:
                                    local_audio_path = local_audio_path_list.pop(0)
                                else:
                                    # 刷新list数据
                                    local_audio_path_list = load_data_list("local_audio")
                                    local_audio_path = local_audio_path_list.pop(0)

                            logging.debug(f"local_audio_path={local_audio_path}")

                            # 发送给处理函数
                            data = {
                                "platform": "哔哩哔哩2",
                                "username": "闲时任务",
                                "type": "local_audio",
                                "content": common.extract_filename(local_audio_path, False),
                                "file_path": local_audio_path
                            }

                            my_handle.process_data(data, "idle_time_task")

                            # 模式切换
                            last_mode = 0

                            overflow_time = int(config.get("idle_time_task", "idle_time"))
                            # 是否开启了随机闲时时间
                            if config.get("idle_time_task", "random_time"):
                                overflow_time = random.randint(0, overflow_time)
                            logging.info(f"闲时时间={overflow_time}秒")

                            continue

                if exit_event.is_set():
                    return

        except Exception as e:
            logging.error(traceback.format_exc())

    if config.get("idle_time_task", "enable"):
        # 创建闲时任务子线程并启动
        idle_time_task_thread = threading.Thread(target=lambda: asyncio.run(idle_time_task()), args=(sub_thread_exit_events[3],))
        idle_time_task_thread.start()
        sub_threads.append(idle_time_task_thread)

    if config.get("platform") == "bilibili":
        try:
            # 导入所需的库
            from bilibili_api import Credential, live, sync, login

            if config.get("bilibili", "login_type") == "cookie":
                logging.info("b站登录后F12抓网络包获取cookie，强烈建议使用小号！有封号风险")
                logging.info("b站登录后，F12控制台，输入 window.localStorage.ac_time_value 回车获取(如果没有，请重新登录)")

                bilibili_cookie = config.get("bilibili", "cookie")
                bilibili_ac_time_value = config.get("bilibili", "ac_time_value")
                if bilibili_ac_time_value == "":
                    bilibili_ac_time_value = None

                # print(f'SESSDATA={common.parse_cookie_data(bilibili_cookie, "SESSDATA")}')
                # print(f'bili_jct={common.parse_cookie_data(bilibili_cookie, "bili_jct")}')
                # print(f'buvid3={common.parse_cookie_data(bilibili_cookie, "buvid3")}')
                # print(f'DedeUserID={common.parse_cookie_data(bilibili_cookie, "DedeUserID")}')

                # 生成一个 Credential 对象
                credential = Credential(
                    sessdata=common.parse_cookie_data(bilibili_cookie, "SESSDATA"), 
                    bili_jct=common.parse_cookie_data(bilibili_cookie, "bili_jct"), 
                    buvid3=common.parse_cookie_data(bilibili_cookie, "buvid3"), 
                    dedeuserid=common.parse_cookie_data(bilibili_cookie, "DedeUserID"), 
                    ac_time_value=bilibili_ac_time_value
                )
            elif config.get("bilibili", "login_type") == "手机扫码":
                credential = login.login_with_qrcode()
            elif config.get("bilibili", "login_type") == "手机扫码-终端":
                credential = login.login_with_qrcode_term()
            elif config.get("bilibili", "login_type") == "账号密码登录":
                bilibili_username = config.get("bilibili", "username")
                bilibili_password = config.get("bilibili", "password")

                credential = login.login_with_password(bilibili_username, bilibili_password)
            elif config.get("bilibili", "login_type") == "不登录":
                credential = None
            else:
                credential = login.login_with_qrcode()

            # 初始化 Bilibili 直播间
            room = live.LiveDanmaku(my_handle.get_room_id(), credential=credential)
        except Exception as e:
            logging.error(traceback.format_exc())
            os._exit(0)

        """
        DANMU_MSG: 用户发送弹幕
        SEND_GIFT: 礼物
        COMBO_SEND：礼物连击
        GUARD_BUY：续费大航海
        SUPER_CHAT_MESSAGE：醒目留言（SC）
        SUPER_CHAT_MESSAGE_JPN：醒目留言（带日语翻译？）
        WELCOME: 老爷进入房间
        WELCOME_GUARD: 房管进入房间
        NOTICE_MSG: 系统通知（全频道广播之类的）
        PREPARING: 直播准备中
        LIVE: 直播开始
        ROOM_REAL_TIME_MESSAGE_UPDATE: 粉丝数等更新
        ENTRY_EFFECT: 进场特效
        ROOM_RANK: 房间排名更新
        INTERACT_WORD: 用户进入直播间
        ACTIVITY_BANNER_UPDATE_V2: 好像是房间名旁边那个xx小时榜
        本模块自定义事件：
        VIEW: 直播间人气更新
        ALL: 所有事件
        DISCONNECT: 断开连接（传入连接状态码参数）
        TIMEOUT: 心跳响应超时
        VERIFICATION_SUCCESSFUL: 认证成功
        """

        @room.on('DANMU_MSG')
        async def _(event):
            """
            处理直播间弹幕事件
            :param event: 弹幕事件数据
            """
            global global_idle_time

            # 闲时计数清零
            global_idle_time = 0
        
            content = event["data"]["info"][1]  # 获取弹幕内容
            user_name = event["data"]["info"][2][1]  # 获取发送弹幕的用户昵称

            logging.info(f"[{user_name}]: {content}")

            data = {
                "platform": "哔哩哔哩",
                "username": user_name,
                "content": content
            }

            my_handle.process_data(data, "comment")

        @room.on('COMBO_SEND')
        async def _(event):
            """
            处理直播间礼物连击事件
            :param event: 礼物连击事件数据
            """

            gift_name = event["data"]["data"]["gift_name"]
            user_name = event["data"]["data"]["uname"]
            # 礼物数量
            combo_num = event["data"]["data"]["combo_num"]
            # 总金额
            combo_total_coin = event["data"]["data"]["combo_total_coin"]

            logging.info(f"用户：{user_name} 赠送 {combo_num} 个 {gift_name}，总计 {combo_total_coin}电池")

            data = {
                "platform": "哔哩哔哩",
                "gift_name": gift_name,
                "username": user_name,
                "num": combo_num,
                "unit_price": combo_total_coin / combo_num / 1000,
                "total_price": combo_total_coin / 1000
            }

            my_handle.process_data(data, "gift")

        @room.on('SEND_GIFT')
        async def _(event):
            """
            处理直播间礼物事件
            :param event: 礼物事件数据
            """

            # print(event)

            gift_name = event["data"]["data"]["giftName"]
            user_name = event["data"]["data"]["uname"]
            # 礼物数量
            num = event["data"]["data"]["num"]
            # 总金额
            combo_total_coin = event["data"]["data"]["combo_total_coin"]
            # 单个礼物金额
            discount_price = event["data"]["data"]["discount_price"]

            logging.info(f"用户：{user_name} 赠送 {num} 个 {gift_name}，单价 {discount_price}电池，总计 {combo_total_coin}电池")

            data = {
                "platform": "哔哩哔哩",
                "gift_name": gift_name,
                "username": user_name,
                "num": num,
                "unit_price": discount_price / 1000,
                "total_price": combo_total_coin / 1000
            }

            my_handle.process_data(data, "gift")

        @room.on('GUARD_BUY')
        async def _(event):
            """
            处理直播间续费大航海事件
            :param event: 续费大航海事件数据
            """

            logging.info(event)

        @room.on('SUPER_CHAT_MESSAGE')
        async def _(event):
            """
            处理直播间醒目留言（SC）事件
            :param event: 醒目留言（SC）事件数据
            """
            message = event["data"]["data"]["message"]
            uname = event["data"]["data"]["user_info"]["uname"]
            price = event["data"]["data"]["price"]

            logging.info(f"用户：{uname} 发送 {price}元 SC：{message}")

            data = {
                "platform": "哔哩哔哩",
                "gift_name": "SC",
                "username": uname,
                "num": 1,
                "unit_price": price,
                "total_price": price,
                "content": message
            }

            my_handle.process_data(data, "gift")

            my_handle.process_data(data, "comment")
            

        @room.on('INTERACT_WORD')
        async def _(event):
            """
            处理直播间用户进入直播间事件
            :param event: 用户进入直播间事件数据
            """
            global last_username_list

            user_name = event["data"]["data"]["uname"]

            logging.info(f"用户：{user_name} 进入直播间")

            # 添加用户名到最新的用户名列表
            add_username_to_last_username_list(user_name)

            data = {
                "platform": "哔哩哔哩",
                "username": user_name,
                "content": "进入直播间"
            }

            my_handle.process_data(data, "entrance")

        # @room.on('WELCOME')
        # async def _(event):
        #     """
        #     处理直播间老爷进入房间事件
        #     :param event: 老爷进入房间事件数据
        #     """

        #     print(event)

        # @room.on('WELCOME_GUARD')
        # async def _(event):
        #     """
        #     处理直播间房管进入房间事件
        #     :param event: 房管进入房间事件数据
        #     """

        #     print(event)


        try:
            # 启动 Bilibili 直播间连接
            sync(room.connect())
        except KeyboardInterrupt:
            logging.warning('程序被强行退出')
        finally:
            logging.warning('关闭连接...可能是直播间号配置有误或者其他原因导致的')
            os._exit(0)
    elif config.get("platform") == "bilibili2":
        try:
            import blivedm
            import blivedm.models.web as web_models
            import blivedm.models.open_live as open_models

            # 直播间ID的取值看直播间URL
            TEST_ROOM_IDS = [my_handle.get_room_id()]

            if config.get("bilibili", "login_type") == "cookie":
                bilibili_cookie = config.get("bilibili", "cookie")
                SESSDATA = common.parse_cookie_data(bilibili_cookie, "SESSDATA")
            elif config.get("bilibili", "login_type") == "open_live":
                # 在开放平台申请的开发者密钥 https://open-live.bilibili.com/open-manage
                ACCESS_KEY_ID = config.get("bilibili", "open_live", "ACCESS_KEY_ID")
                ACCESS_KEY_SECRET = config.get("bilibili", "open_live", "ACCESS_KEY_SECRET")
                # 在开放平台创建的项目ID
                APP_ID = config.get("bilibili", "open_live", "APP_ID")
                # 主播身份码 直播中心获取
                ROOM_OWNER_AUTH_CODE = config.get("bilibili", "open_live", "ROOM_OWNER_AUTH_CODE")

        except Exception as e:
            logging.error(traceback.format_exc())

        async def main_func():
            global session

            if config.get("bilibili", "login_type") == "open_live":
                await run_single_client2()
            else:
                try:
                    init_session()

                    await run_single_client()
                    await run_multi_clients()
                finally:
                    await session.close()


        def init_session():
            global session, SESSDATA

            cookies = http.cookies.SimpleCookie()
            cookies['SESSDATA'] = SESSDATA
            cookies['SESSDATA']['domain'] = 'bilibili.com'

            # logging.info(f"SESSDATA={SESSDATA}")

            session = aiohttp.ClientSession()
            session.cookie_jar.update_cookies(cookies)


        async def run_single_client():
            """
            演示监听一个直播间
            """
            global session

            room_id = random.choice(TEST_ROOM_IDS)
            client = blivedm.BLiveClient(room_id, session=session)
            handler = MyHandler()
            client.set_handler(handler)

            client.start()
            try:
                # 演示5秒后停止
                await asyncio.sleep(5)
                client.stop()

                await client.join()
            finally:
                await client.stop_and_close()

        async def run_single_client2():
            """
            演示监听一个直播间 开放平台
            """
            client = blivedm.OpenLiveClient(
                access_key_id=ACCESS_KEY_ID,
                access_key_secret=ACCESS_KEY_SECRET,
                app_id=APP_ID,
                room_owner_auth_code=ROOM_OWNER_AUTH_CODE,
            )
            handler = MyHandler2()
            client.set_handler(handler)

            client.start()
            try:
                # 演示70秒后停止
                # await asyncio.sleep(70)
                # client.stop()

                await client.join()
            finally:
                await client.stop_and_close()

        async def run_multi_clients():
            """
            演示同时监听多个直播间
            """
            global session

            clients = [blivedm.BLiveClient(room_id, session=session) for room_id in TEST_ROOM_IDS]
            handler = MyHandler()
            for client in clients:
                client.set_handler(handler)
                client.start()

            try:
                await asyncio.gather(*(
                    client.join() for client in clients
                ))
            finally:
                await asyncio.gather(*(
                    client.stop_and_close() for client in clients
                ))


        class MyHandler(blivedm.BaseHandler):
            # 演示如何添加自定义回调
            _CMD_CALLBACK_DICT = blivedm.BaseHandler._CMD_CALLBACK_DICT.copy()
            
            # 入场消息回调
            def __interact_word_callback(self, client: blivedm.BLiveClient, command: dict):
                # logging.info(f"[{client.room_id}] INTERACT_WORD: self_type={type(self).__name__}, room_id={client.room_id},"
                #     f" uname={command['data']['uname']}")
                
                global last_username_list

                user_name = command['data']['uname']

                logging.info(f"用户：{user_name} 进入直播间")

                # 添加用户名到最新的用户名列表
                add_username_to_last_username_list(user_name)

                data = {
                    "platform": "哔哩哔哩2",
                    "username": user_name,
                    "content": "进入直播间"
                }

                my_handle.process_data(data, "entrance")

            _CMD_CALLBACK_DICT['INTERACT_WORD'] = __interact_word_callback  # noqa

            def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
                logging.debug(f'[{client.room_id}] 心跳')

            def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
                global global_idle_time

                # 闲时计数清零
                global_idle_time = 0

                # logging.info(f'[{client.room_id}] {message.uname}：{message.msg}')
                content = message.msg  # 获取弹幕内容
                user_name = message.uname  # 获取发送弹幕的用户昵称

                logging.info(f"[{user_name}]: {content}")

                data = {
                    "platform": "哔哩哔哩2",
                    "username": user_name,
                    "content": content
                }

                my_handle.process_data(data, "comment")

            def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
                # logging.info(f'[{client.room_id}] {message.uname} 赠送{message.gift_name}x{message.num}'
                #     f' （{message.coin_type}瓜子x{message.total_coin}）')
                
                gift_name = message.gift_name
                user_name = message.uname
                # 礼物数量
                combo_num = message.num
                # 总金额
                combo_total_coin = message.total_coin

                logging.info(f"用户：{user_name} 赠送 {combo_num} 个 {gift_name}，总计 {combo_total_coin}电池")

                data = {
                    "platform": "哔哩哔哩2",
                    "gift_name": gift_name,
                    "username": user_name,
                    "num": combo_num,
                    "unit_price": combo_total_coin / combo_num / 1000,
                    "total_price": combo_total_coin / 1000
                }

                my_handle.process_data(data, "gift")

            def _on_buy_guard(self, client: blivedm.BLiveClient, message: web_models.GuardBuyMessage):
                logging.info(f'[{client.room_id}] {message.username} 购买{message.gift_name}')

            def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
                # logging.info(f'[{client.room_id}] 醒目留言 ¥{message.price} {message.uname}：{message.message}')

                message = message.message
                uname = message.uname
                price = message.price

                logging.info(f"用户：{uname} 发送 {price}元 SC：{message}")

                data = {
                    "platform": "哔哩哔哩2",
                    "gift_name": "SC",
                    "username": uname,
                    "num": 1,
                    "unit_price": price,
                    "total_price": price,
                    "content": message
                }

                my_handle.process_data(data, "gift")

                my_handle.process_data(data, "comment")

        class MyHandler2(blivedm.BaseHandler):
            def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
                logging.debug(f'[{client.room_id}] 心跳')

            def _on_open_live_danmaku(self, client: blivedm.OpenLiveClient, message: open_models.DanmakuMessage):
                global global_idle_time

                # 闲时计数清零
                global_idle_time = 0

                # logging.info(f'[{client.room_id}] {message.uname}：{message.msg}')
                content = message.msg  # 获取弹幕内容
                user_name = message.uname  # 获取发送弹幕的用户昵称

                logging.info(f"[{user_name}]: {content}")

                data = {
                    "platform": "哔哩哔哩2",
                    "username": user_name,
                    "content": content
                }

                my_handle.process_data(data, "comment")

            def _on_open_live_gift(self, client: blivedm.OpenLiveClient, message: open_models.GiftMessage):
                gift_name = message.gift_name
                user_name = message.uname
                # 礼物数量
                combo_num = message.gift_num
                # 总金额
                combo_total_coin = message.price * message.gift_num

                logging.info(f"用户：{user_name} 赠送 {combo_num} 个 {gift_name}，总计 {combo_total_coin}电池")

                data = {
                    "platform": "哔哩哔哩2",
                    "gift_name": gift_name,
                    "username": user_name,
                    "num": combo_num,
                    "unit_price": combo_total_coin / combo_num / 1000,
                    "total_price": combo_total_coin / 1000
                }

                my_handle.process_data(data, "gift")


            def _on_open_live_buy_guard(self, client: blivedm.OpenLiveClient, message: open_models.GuardBuyMessage):
                logging.info(f'[{client.room_id}] {message.user_info.uname} 购买 大航海等级={message.guard_level}')

            def _on_open_live_super_chat(
                self, client: blivedm.OpenLiveClient, message: open_models.SuperChatMessage
            ):
                print(f'[{message.room_id}] 醒目留言 ¥{message.rmb} {message.uname}：{message.message}')

                message = message.message
                uname = message.uname
                price = message.rmb

                logging.info(f"用户：{uname} 发送 {price}元 SC：{message}")

                data = {
                    "platform": "哔哩哔哩2",
                    "gift_name": "SC",
                    "username": uname,
                    "num": 1,
                    "unit_price": price,
                    "total_price": price,
                    "content": message
                }

                my_handle.process_data(data, "gift")

                my_handle.process_data(data, "comment")

            def _on_open_live_super_chat_delete(
                self, client: blivedm.OpenLiveClient, message: open_models.SuperChatDeleteMessage
            ):
                logging.info(f'[直播间 {message.room_id}] 删除醒目留言 message_ids={message.message_ids}')

            def _on_open_live_like(self, client: blivedm.OpenLiveClient, message: open_models.LikeMessage):
                logging.info(f'用户：{message.uname} 点了个赞')

        asyncio.run(main_func())
    elif config.get("platform") == "douyu":
        import websockets

        async def on_message(websocket, path):
            global last_liveroom_data, last_username_list
            global global_idle_time

            async for message in websocket:
                # print(f"收到消息: {message}")
                # await websocket.send("服务器收到了你的消息: " + message)

                try:
                    data_json = json.loads(message)
                    # logging.debug(data_json)
                    if data_json["type"] == "comment":
                        # logging.info(data_json)
                        # 闲时计数清零
                        global_idle_time = 0

                        user_name = data_json["username"]
                        content = data_json["content"]
                        
                        logging.info(f'[📧直播间弹幕消息] [{user_name}]：{content}')

                        data = {
                            "platform": "斗鱼",
                            "username": user_name,
                            "content": content
                        }
                        
                        my_handle.process_data(data, "comment")

                        # 添加用户名到最新的用户名列表
                        add_username_to_last_username_list(user_name)

                except Exception as e:
                    logging.error(e)
                    logging.error("数据解析错误！")
                    continue
            

        async def ws_server():
            ws_url = "127.0.0.1"
            ws_port = 5000
            server = await websockets.serve(on_message, ws_url, ws_port)
            logging.info(f"WebSocket 服务器已在 {ws_url}:{ws_port} 启动")
            await server.wait_closed()


        asyncio.run(ws_server())
    elif config.get("platform") == "dy":
        import websocket

        def on_message(ws, message):
            global last_liveroom_data, last_username_list, config, config_path
            global global_idle_time

            message_json = json.loads(message)
            # logging.debug(message_json)
            if "Type" in message_json:
                type = message_json["Type"]
                data_json = json.loads(message_json["Data"])
                
                if type == 1:
                    # 闲时计数清零
                    global_idle_time = 0

                    user_name = data_json["User"]["Nickname"]
                    content = data_json["Content"]
                    
                    logging.info(f'[📧直播间弹幕消息] [{user_name}]：{content}')

                    data = {
                        "platform": "抖音",
                        "username": user_name,
                        "content": content
                    }
                    
                    my_handle.process_data(data, "comment")

                    pass

                elif type == 2:
                    user_name = data_json["User"]["Nickname"]
                    count = data_json["Count"]

                    logging.info(f'[👍直播间点赞消息] {user_name} 点了{count}赞')                

                elif type == 3:
                    user_name = data_json["User"]["Nickname"]

                    logging.info(f'[🚹🚺直播间成员加入消息] 欢迎 {user_name} 进入直播间')

                    data = {
                        "platform": "抖音",
                        "username": user_name,
                        "content": "进入直播间"
                    }

                    # 添加用户名到最新的用户名列表
                    add_username_to_last_username_list(user_name)

                    my_handle.process_data(data, "entrance")

                elif type == 4:
                    user_name = data_json["User"]["Nickname"]

                    logging.info(f'[➕直播间关注消息] 感谢 {data_json["User"]["Nickname"]} 的关注')

                    data = {
                        "platform": "抖音",
                        "username": user_name
                    }
                    
                    my_handle.process_data(data, "follow")

                    pass

                elif type == 5:
                    gift_name = data_json["GiftName"]
                    user_name = data_json["User"]["Nickname"]
                    # 礼物数量
                    num = data_json["GiftCount"]
                    # 礼物重复数量
                    repeat_count = data_json["RepeatCount"]

                    try:
                        # 暂时是写死的
                        data_path = "data/抖音礼物价格表.json"

                        # 读取JSON文件
                        with open(data_path, "r", encoding="utf-8") as file:
                            # 解析JSON数据
                            data_json = json.load(file)

                        if gift_name in data_json:
                            # 单个礼物金额 需要自己维护礼物价值表
                            discount_price = data_json[gift_name]
                        else:
                            logging.warning(f"数据文件：{data_path} 中，没有 {gift_name} 对应的价值，请手动补充数据")
                            discount_price = 1
                    except Exception as e:
                        logging.error(traceback.format_exc())
                        discount_price = 1


                    # 总金额
                    combo_total_coin = repeat_count * discount_price

                    logging.info(f'[🎁直播间礼物消息] 用户：{user_name} 赠送 {num} 个 {gift_name}，单价 {discount_price}抖币，总计 {combo_total_coin}抖币')

                    data = {
                        "platform": "抖音",
                        "gift_name": gift_name,
                        "username": user_name,
                        "num": num,
                        "unit_price": discount_price / 10,
                        "total_price": combo_total_coin / 10
                    }

                    my_handle.process_data(data, "gift")

                elif type == 6:
                    logging.info(f'[直播间数据] {data_json["Content"]}')
                    # {'OnlineUserCount': 50, 'TotalUserCount': 22003, 'TotalUserCountStr': '2.2万', 'OnlineUserCountStr': '50', 
                    # 'MsgId': 7260517442466662207, 'User': None, 'Content': '当前直播间人数 50，累计直播间人数 2.2万', 'RoomId': 7260415920948906807}
                    # print(f"data_json={data_json}")

                    last_liveroom_data = data_json

                    # 当前在线人数
                    OnlineUserCount = data_json["OnlineUserCount"]

                    try:
                        # 是否开启了动态配置功能
                        if config.get("trends_config", "enable"):
                            for path_config in config.get("trends_config", "path"):
                                online_num_min = int(path_config["online_num"].split("-")[0])
                                online_num_max = int(path_config["online_num"].split("-")[1])

                                # 判断在线人数是否在此范围内
                                if OnlineUserCount >= online_num_min and OnlineUserCount <= online_num_max:
                                    logging.debug(f"当前配置文件：{path_config['path']}")
                                    # 如果配置文件相同，则跳过
                                    if config_path == path_config["path"]:
                                        break

                                    config_path = path_config["path"]
                                    config = Config(config_path)

                                    my_handle.reload_config(config_path)

                                    logging.info(f"切换配置文件：{config_path}")

                                    break
                    except Exception as e:
                        logging.error(traceback.format_exc())

                    pass

                elif type == 8:
                    logging.info(f'[分享直播间] 感谢 {data_json["User"]["Nickname"]} 分享了直播间')

                    pass

        def on_error(ws, error):
            logging.error("Error:", error)


        def on_close(ws):
            logging.debug("WebSocket connection closed")

        def on_open(ws):
            logging.debug("WebSocket connection established")

        try: 
            # WebSocket连接URL
            ws_url = "ws://127.0.0.1:8888"

            logging.info(f"监听地址：{ws_url}")

            # 不设置日志等级
            websocket.enableTrace(False)
            # 创建WebSocket连接
            ws = websocket.WebSocketApp(ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open)

            # 运行WebSocket连接
            ws.run_forever()
        except KeyboardInterrupt:
            logging.warning('程序被强行退出')
        finally:
            logging.info('关闭连接...可能是直播间不存在或下播或网络问题')
            os._exit(0)
    elif config.get("platform") == "ks":
        from playwright.sync_api import sync_playwright
        from google.protobuf.json_format import MessageToDict
        from configparser import ConfigParser
        import kuaishou_pb2

        class kslive(object):
            def __init__(self):
                global config, common, my_handle

                self.path = os.path.abspath('')
                self.chrome_path = r"\firefox-1419\firefox\firefox.exe"
                self.ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
                self.uri = 'https://live.kuaishou.com/u/'
                self.context = None
                self.browser = None
                self.page = None

                try:
                    self.live_ids = config.get("room_display_id")
                    self.thread = 2
                    # 没什么用的手机号配置，也就方便登录
                    self.phone = "123"
                except Exception as e:
                    logging.error(traceback.format_exc())
                    logging.error("请检查配置文件")
                    exit()

            def find_file(self, find_path, file_type) -> list:
                """
                寻找文件
                :param find_path: 子路径
                :param file_type: 文件类型
                :return:
                """
                path = self.path + "\\" + find_path
                data_list = []
                for root, dirs, files in os.walk(path):
                    if root != path:
                        break
                    for file in files:
                        file_path = os.path.join(root, file)
                        if file_path.find(file_type) != -1:
                            data_list.append(file_path)
                return data_list

            def main(self, lid, semaphore):
                if not os.path.exists(self.path + "\\cookie"):
                    os.makedirs(self.path + "\\cookie")
                
                cookie_path=self.path + "\\cookie\\" + self.phone + ".json"
                # if not os.path.exists(cookie_path):
                #     with open(cookie_path, 'w') as file:
                #         file.write('{"a":"a"}')
                #     logging.info(f"'{cookie_path}' 创建成功")
                # else:
                #     logging.info(f"'{cookie_path}' 已存在，无需创建")

                with semaphore:
                    thread_name = threading.current_thread().name.split("-")[0]
                    with sync_playwright() as p:
                        self.browser = p.firefox.launch(headless=False)
                        # executable_path=self.path + self.chrome_path
                        cookie_list = self.find_file("cookie", "json")
                    
                        if not os.path.exists(cookie_path):
                            self.context = self.browser.new_context(storage_state=None, user_agent=self.ua)
                        else:
                            self.context = self.browser.new_context(storage_state=cookie_list[0], user_agent=self.ua)
                        self.page = self.context.new_page()
                        self.page.add_init_script("Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});")
                        self.page.goto("https://live.kuaishou.com/")
                        element = self.page.get_attribute('.no-login', "style")
                        if not element:
                            self.page.locator('.login').click()
                            self.page.locator('li.tab-panel:nth-child(2) > h4:nth-child(1)').click()
                            self.page.locator(
                                'div.normal-login-item:nth-child(1) > div:nth-child(1) > input:nth-child(1)').fill(
                                self.phone)
                        try:
                            self.page.wait_for_selector("#app > section > div.header-placeholder > header > div.header-main > "
                                                        "div.right-part > div.user-info > div.tooltip-trigger > span",
                                                        timeout=1000 * 60 * 2)
                            if not os.path.exists(self.path + "\\cookie"):
                                os.makedirs(self.path + "\\cookie")
                            self.context.storage_state(path=cookie_path)
                            # 检测是否开播
                            selector = "html body div#app div.live-room div.detail div.player " \
                                    "div.kwai-player.kwai-player-container.kwai-player-rotation-0 " \
                                    "div.kwai-player-container-video div.kwai-player-plugins div.center-state div.state " \
                                    "div.no-live-detail div.desc p.tip"  # 检测正在直播时下播的选择器
                            try:
                                msg = self.page.locator(selector).text_content(timeout=3000)
                                logging.info("当前%s" % thread_name + "，" + msg)
                                self.context.close()
                                self.browser.close()

                            except Exception as e:
                                logging.info("当前%s，[%s]正在直播" % (thread_name, lid))
                                self.page.goto(self.uri + lid)
                                self.page.on("websocket", self.web_sockets)
                                self.page.wait_for_selector(selector, timeout=86400000)
                                logging.error("当前%s，[%s]的直播结束了" % (thread_name, lid))
                                self.context.close()
                                self.browser.close()

                        except Exception:
                            logging.info("登录失败")
                            self.context.close()
                            self.browser.close()

            def web_sockets(self, web_socket):
                logging.info("web_sockets...")
                urls = web_socket.url
                logging.info(urls)
                if '/websocket' in urls:
                    web_socket.on("close", self.websocket_close)
                    web_socket.on("framereceived", self.handler)

            def websocket_close(self):
                self.context.close()
                self.browser.close()

            def handler(self, websocket):
                global global_idle_time

                Message = kuaishou_pb2.SocketMessage()
                Message.ParseFromString(websocket)
                if Message.payloadType == 310:
                    SCWebFeedPUsh = kuaishou_pb2.SCWebFeedPush()
                    SCWebFeedPUsh.ParseFromString(Message.payload)
                    obj = MessageToDict(SCWebFeedPUsh, preserving_proto_field_name=True)

                    logging.debug(obj)

                    if obj.get('commentFeeds', ''):
                        msg_list = obj.get('commentFeeds', '')
                        for i in msg_list:
                            # 闲时计数清零
                            global_idle_time = 0

                            username = i['user']['userName']
                            pid = i['user']['principalId']
                            content = i['content']
                            logging.info(f"[📧直播间弹幕消息] [{username}]:{content}")

                            data = {
                                "platform": "快手",
                                "username": username,
                                "content": content
                            }
                            
                            my_handle.process_data(data, "comment")
                    if obj.get('giftFeeds', ''):
                        msg_list = obj.get('giftFeeds', '')
                        for i in msg_list:
                            username = i['user']['userName']
                            # pid = i['user']['principalId']
                            giftId = i['giftId']
                            comboCount = i['comboCount']
                            logging.info(f"[🎁直播间礼物消息] 用户：{username} 赠送礼物Id={giftId} 连击数={comboCount}")
                    if obj.get('likeFeeds', ''):
                        msg_list = obj.get('likeFeeds', '')
                        for i in msg_list:
                            username = i['user']['userName']
                            pid = i['user']['principalId']
                            logging.info(f"{username}")


        class run(kslive):
            def __init__(self):
                super().__init__()
                self.ids_list = self.live_ids.split(",")

            def run_live(self):
                """
                主程序入口
                :return:
                """
                t_list = []
                # 允许的最大线程数
                if self.thread < 1:
                    self.thread = 1
                elif self.thread > 8:
                    self.thread = 8
                    logging.info("线程最大允许8，线程数最好设置cpu核心数")

                semaphore = threading.Semaphore(self.thread)
                # 用于记录数量
                n = 0
                if not self.live_ids:
                    logging.info("请导入网页直播id，多个以','间隔")
                    return

                for i in self.ids_list:
                    n += 1
                    t = threading.Thread(target=kslive().main, args=(i, semaphore), name=f"线程：{n}-{i}")
                    t.start()
                    t_list.append(t)
                for i in t_list:
                    i.join()

        run().run_live()
    elif config.get("platform") == "talk":
        import keyboard
        import pyaudio
        import wave
        import numpy as np
        import speech_recognition as sr
        from aip import AipSpeech
        import signal

        # 冷却时间 0.3 秒
        cooldown = 0.3 
        last_pressed = 0

        stop_do_listen_and_comment_thread_event = threading.Event()
        
        # signal.signal(signal.SIGINT, exit_handler)
        # signal.signal(signal.SIGTERM, exit_handler)

        # 录音功能(录音时间过短进入openai的语音转文字会报错，请一定注意)
        def record_audio():
            pressdown_num = 0
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 44100
            WAVE_OUTPUT_FILENAME = "out/record.wav"
            p = pyaudio.PyAudio()
            stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)
            frames = []
            print("Recording...")
            flag = 0
            while 1:
                while keyboard.is_pressed('RIGHT_SHIFT'):
                    flag = 1
                    data = stream.read(CHUNK)
                    frames.append(data)
                    pressdown_num = pressdown_num + 1
                if flag:
                    break
            print("Stopped recording.")
            stream.stop_stream()
            stream.close()
            p.terminate()
            wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            if pressdown_num >= 5:         # 粗糙的处理手段
                return 1
            else:
                print("杂鱼杂鱼，好短好短(录音时间过短,按右shift重新录制)")
                return 0


        # THRESHOLD 设置音量阈值,默认值800.0,根据实际情况调整  silence_threshold 设置沉默阈值，根据实际情况调整
        def audio_listen(volume_threshold=800.0, silence_threshold=15):
            audio = pyaudio.PyAudio()

            # 设置音频参数
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            CHUNK = 1024

            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=int(config.get("talk", "device_index"))
            )

            frames = []  # 存储录制的音频帧

            is_speaking = False  # 是否在说话
            silent_count = 0  # 沉默计数
            speaking_flag = False   #录入标志位 不重要

            while True:
                # 读取音频数据
                data = stream.read(CHUNK)
                audio_data = np.frombuffer(data, dtype=np.short)
                max_dB = np.max(audio_data)
                # print(max_dB)
                if max_dB > volume_threshold:
                    is_speaking = True
                    silent_count = 0
                elif is_speaking is True:
                    silent_count += 1

                if is_speaking is True:
                    frames.append(data)
                    if speaking_flag is False:
                        logging.info("[录入中……]")
                        speaking_flag = True

                if silent_count >= silence_threshold:
                    break

            logging.info("[语音录入完成]")

            # 将音频保存为WAV文件
            '''with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))'''
            return frames
        

        # 执行录音、识别&提交
        def do_listen_and_comment(status=True):
            global stop_do_listen_and_comment_thread_event

            while True:
                # 检查是否收到停止事件
                if stop_do_listen_and_comment_thread_event.is_set():
                    logging.info(f'停止录音~')
                    break

                config = Config(config_path)
            
                # 根据接入的语音识别类型执行
                if "baidu" == config.get("talk", "type"):
                    # 设置音频参数
                    FORMAT = pyaudio.paInt16
                    CHANNELS = 1
                    RATE = 16000

                    audio_out_path = config.get("play_audio", "out_path")

                    if not os.path.isabs(audio_out_path):
                        if not audio_out_path.startswith('./'):
                            audio_out_path = './' + audio_out_path
                    file_name = 'baidu_' + common.get_bj_time(4) + '.wav'
                    WAVE_OUTPUT_FILENAME = common.get_new_audio_path(audio_out_path, file_name)
                    # WAVE_OUTPUT_FILENAME = './out/baidu_' + common.get_bj_time(4) + '.wav'

                    frames = audio_listen(config.get("talk", "volume_threshold"), config.get("talk", "silence_threshold"))

                    # 将音频保存为WAV文件
                    with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                        wf.setframerate(RATE)
                        wf.writeframes(b''.join(frames))

                    # 读取音频文件
                    with open(WAVE_OUTPUT_FILENAME, 'rb') as fp:
                        audio = fp.read()

                    # 初始化 AipSpeech 对象
                    baidu_client = AipSpeech(config.get("talk", "baidu", "app_id"), config.get("talk", "baidu", "api_key"), config.get("talk", "baidu", "secret_key"))

                    # 识别音频文件
                    res = baidu_client.asr(audio, 'wav', 16000, {
                        'dev_pid': 1536,
                    })
                    if res['err_no'] == 0:
                        content = res['result'][0]

                        # 输出识别结果
                        logging.info("识别结果：" + content)
                        user_name = config.get("talk", "username")

                        data = {
                            "platform": "本地聊天",
                            "username": user_name,
                            "content": content
                        }

                        my_handle.process_data(data, "talk")
                    else:
                        logging.error(f"百度接口报错：{res}")  
                elif "google" == config.get("talk", "type"):
                    # 创建Recognizer对象
                    r = sr.Recognizer()

                    try:
                        # 打开麦克风进行录音
                        with sr.Microphone() as source:
                            logging.info(f'录音中...')
                            # 从麦克风获取音频数据
                            audio = r.listen(source)
                            logging.info("成功录制")

                            # 进行谷歌实时语音识别 en-US zh-CN ja-JP
                            content = r.recognize_google(audio, language=config.get("talk", "google", "tgt_lang"))

                            # 输出识别结果
                            # logging.info("识别结果：" + content)
                            user_name = config.get("talk", "username")

                            data = {
                                "platform": "本地聊天",
                                "username": user_name,
                                "content": content
                            }

                            my_handle.process_data(data, "talk")
                    except sr.UnknownValueError:
                        logging.warning("无法识别输入的语音")
                    except sr.RequestError as e:
                        logging.error("请求出错：" + str(e))
                
                if not status:
                    return


        def on_key_press(event):
            global do_listen_and_comment_thread, stop_do_listen_and_comment_thread_event

            # if event.name in ['z', 'Z', 'c', 'C'] and keyboard.is_pressed('ctrl'):
                # print("退出程序")

                # os._exit(0)
            
            # 按键CD
            current_time = time.time()
            if current_time - last_pressed < cooldown:
                return
            

            """
            触发按键部分的判断
            """
            trigger_key_lower = None
            stop_trigger_key_lower = None

            # trigger_key是字母, 整个小写
            if trigger_key.isalpha():
                trigger_key_lower = trigger_key.lower()

            # stop_trigger_key是字母, 整个小写
            if stop_trigger_key.isalpha():
                stop_trigger_key_lower = stop_trigger_key.lower()
            
            if trigger_key_lower:
                if event.name == trigger_key or event.name == trigger_key_lower:
                    logging.info(f'检测到单击键盘 {event.name}，即将开始录音~')
                elif event.name == stop_trigger_key or event.name == stop_trigger_key_lower:
                    logging.info(f'检测到单击键盘 {event.name}，即将停止录音~')
                    stop_do_listen_and_comment_thread_event.set()
                    return
                else:
                    return
            else:
                if event.name == trigger_key:
                    logging.info(f'检测到单击键盘 {event.name}，即将开始录音~')
                elif event.name == stop_trigger_key:
                    logging.info(f'检测到单击键盘 {event.name}，即将停止录音~')
                    stop_do_listen_and_comment_thread_event.set()
                    return
                else:
                    return

            # 是否启用连续对话模式
            if config.get("talk", "continuous_talk"):
                stop_do_listen_and_comment_thread_event.clear()
                do_listen_and_comment_thread = threading.Thread(target=do_listen_and_comment, args=(True,))
                do_listen_and_comment_thread.start()
            else:
                stop_do_listen_and_comment_thread_event.clear()
                do_listen_and_comment_thread = threading.Thread(target=do_listen_and_comment, args=(False,))
                do_listen_and_comment_thread.start()


        # 按键监听
        def key_listener():
            # 注册按键按下事件的回调函数
            keyboard.on_press(on_key_press)

            try:
                # 进入监听状态，等待按键按下
                keyboard.wait()
            except KeyboardInterrupt:
                os._exit(0)

        # 从配置文件中读取触发键的字符串配置
        trigger_key = config.get("talk", "trigger_key")
        stop_trigger_key = config.get("talk", "stop_trigger_key")

        logging.info(f'单击键盘 {trigger_key} 按键进行录音喵~ 由于其他任务还要启动，如果按键没有反应，请等待一段时间')

        # 创建并启动按键监听线程
        thread = threading.Thread(target=key_listener)
        thread.start()
    elif config.get("platform") == "twitch":
        import socks
        from emoji import demojize

        try:
            server = 'irc.chat.twitch.tv'
            port = 6667
            nickname = '主人'

            try:
                channel = '#' + config.get("room_display_id") # 要从中检索消息的频道，注意#必须携带在头部 The channel you want to retrieve messages from
                token = config.get("twitch", "token") # 访问 https://twitchapps.com/tmi/ 获取
                user = config.get("twitch", "user") # 你的Twitch用户名 Your Twitch username
                # 代理服务器的地址和端口
                proxy_server = config.get("twitch", "proxy_server")
                proxy_port = int(config.get("twitch", "proxy_port"))
            except Exception as e:
                logging.error("获取Twitch配置失败！\n{0}".format(e))

            # 配置代理服务器
            socks.set_default_proxy(socks.HTTP, proxy_server, proxy_port)

            # 创建socket对象
            sock = socks.socksocket()

            try:
                sock.connect((server, port))
                logging.info("成功连接 Twitch IRC server")
            except Exception as e:
                logging.error(f"连接 Twitch IRC server 失败: {e}")


            sock.send(f"PASS {token}\n".encode('utf-8'))
            sock.send(f"NICK {nickname}\n".encode('utf-8'))
            sock.send(f"JOIN {channel}\n".encode('utf-8'))

            regex = r":(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.+)"

            # 重连次数
            retry_count = 0

            while True:
                try:
                    resp = sock.recv(2048).decode('utf-8')

                    # 输出所有接收到的内容，包括PING/PONG
                    # logging.info(resp)

                    if resp.startswith('PING'):
                            sock.send("PONG\n".encode('utf-8'))

                    elif not user in resp:
                        # 闲时计数清零
                        global_idle_time = 0

                        resp = demojize(resp)

                        logging.debug(resp)

                        match = re.match(regex, resp)

                        user_name = match.group(1)
                        content = match.group(2)
                        content = content.rstrip()

                        logging.info(f"[{user_name}]: {content}")

                        data = {
                            "platform": "twitch",
                            "username": user_name,
                            "content": content
                        }

                        my_handle.process_data(data, "comment")
                except AttributeError as e:
                    logging.error(f"捕获到异常: {e}")
                    logging.error("发生异常，重新连接socket")

                    if retry_count >= 3:
                        logging.error(f"多次重连失败，程序结束！")
                        return
                    
                    retry_count += 1
                    logging.error(f"重试次数: {retry_count}")

                    # 在这里添加重新连接socket的代码
                    # 例如，你可能想要关闭旧的socket连接，然后重新创建一个新的socket连接
                    sock.close()

                    # 创建socket对象
                    sock = socks.socksocket()

                    try:
                        sock.connect((server, port))
                        logging.info("成功连接 Twitch IRC server")
                    except Exception as e:
                        logging.error(f"连接 Twitch IRC server 失败: {e}")

                    sock.send(f"PASS {token}\n".encode('utf-8'))
                    sock.send(f"NICK {nickname}\n".encode('utf-8'))
                    sock.send(f"JOIN {channel}\n".encode('utf-8'))
                except Exception as e:
                    logging.error("Error receiving chat: {0}".format(e))
        except Exception as e:
            logging.error(traceback.format_exc())
    elif config.get("platform") == "youtube":
        import pytchat

        try:
            try:
                video_id = config.get("room_display_id")
            except Exception as e:
                logging.error("获取直播间号失败！\n{0}".format(e))

            live = pytchat.create(video_id=video_id)
            while live.is_alive():
                try:
                    for c in live.get().sync_items():
                        # 过滤表情包
                        chat_raw = re.sub(r':[^\s]+:', '', c.message)
                        chat_raw = chat_raw.replace('#', '')
                        if chat_raw != '':
                            # 闲时计数清零
                            global_idle_time = 0

                            # chat_author makes the chat look like this: "Nightbot: Hello". So the assistant can respond to the user's name
                            # chat = '[' + c.author.name + ']: ' + chat_raw
                            # logging.info(chat)

                            content = chat_raw  # 获取弹幕内容
                            user_name = c.author.name  # 获取发送弹幕的用户昵称

                            logging.info(f"[{user_name}]: {content}")

                            data = {
                                "platform": "YouTube",
                                "username": user_name,
                                "content": content
                            }

                            my_handle.process_data(data, "comment")
                            
                        # time.sleep(1)
                except Exception as e:
                    logging.error("Error receiving chat: {0}".format(e))
        except KeyboardInterrupt:
            logging.warning('程序被强行退出')
        finally:
            logging.warning('关闭连接...')
            os._exit(0)

    while not sub_thread_exit_events[0].is_set():
        # 等待事件被设置或超时，每次检查之间暂停1秒
        sub_thread_exit_events[0].wait(1)

    # 关闭所有子线程
    for event in sub_thread_exit_events:
        event.set()
    for t in sub_threads:
        t.join()

    logging.info("start_server子线程退出")

# 退出程序
def exit_handler(signum, frame):
    logging.info("收到信号:", signum)

if __name__ == '__main__':
    os.environ['GEVENT_SUPPORT'] = 'True'

    port = 8082
    password = "中文的密码，怕了吧！"

    app = Flask(__name__, static_folder='static')
    CORS(app)  # 允许跨域请求
    socketio = SocketIO(app, cors_allowed_origins="*")

    @app.route('/static/<path:filename>')
    def static_files(filename):
        return send_from_directory(app.static_folder, filename)

    sub_thread_exit_events = [threading.Event() for _ in range(4)] # 为每个子线程创建退出事件

    """
    通用函数
    """
    def restart_application():
        """
        重启
        """
        try:
            # 获取当前 Python 解释器的可执行文件路径
            python_executable = sys.executable

            # 获取当前脚本的文件路径
            script_file = os.path.abspath(__file__)

            # 重启当前程序
            os.execv(python_executable, ['python', script_file])
        except Exception as e:
            logging.error(traceback.format_exc())
            return {"code": -1, "msg": f"重启失败！{e}"}

    # 创建一个函数，用于运行外部程序
    def run_external_program(config_path):
        global running_flag, running_process

        if running_flag:
            return {"code": 1, "msg": "运行中，请勿重复运行"}

        try:
            running_flag = True

            thread = threading.Thread(target=start_server, args=(config_path, sub_thread_exit_events,))
            thread.start()

            # thread.join()

            logging.info("程序开始运行")
            return {"code": 200, "msg": "程序开始运行"}
        except Exception as e:
            logging.error(traceback.format_exc())
            running_flag = False

            return {"code": -1, "msg": f"运行失败！{e}"}

    # 定义一个函数，用于停止正在运行的程序
    def stop_external_program():
        global running_flag, running_process

        if running_flag:
            try:
                # 通知子线程退出
                sub_thread_exit_events[0].set()

                running_flag = False
                logging.info("程序已停止")
                return {"code": 200, "msg": "停止成功"}
            except Exception as e:
                logging.error(traceback.format_exc())

                return {"code": -1, "msg": f"停止失败！{e}"}

    # 恢复出厂配置
    def factory(src_path, dst_path):
        try:
            with open(src_path, 'r', encoding="utf-8") as source:
                with open(dst_path, 'w', encoding="utf-8") as destination:
                    destination.write(source.read())
            logging.info("恢复出厂配置成功！")

            return {"code": 200, "msg": "恢复出厂配置成功！"}
        except Exception as e:
            logging.error(traceback.format_exc())
            
            return {"code": -1, "msg": f"恢复出厂配置失败！\n{e}"}


    # def check_password(data_json, ip):
    #     try:
    #         if data_json["password"] == password:
    #             return True
    #         else:
    #             return False
    #     except Exception as e:
    #         logging.error(f"[{ip}] 密码校验失败！{e}")
    #         return False


    """
    配置config
        config_path 配置文件路径（默认相对路径）
        data 传入的json将被写入配置文件

    data_json = {
        "config_path": "config.json",
        "data": {
            "key": "value"
        }
    }

    return:
        {"code": 200, "msg": "成功"}
        {"code": -1, "msg": "失败"}
    """
    @app.route('/set_config', methods=['POST'])
    def set_config():
        """
        {
            "config_path": "config.json",
            "data": {
                "platform": "bilibili"
            }
        }
        """
        try:
            data_json = request.get_json()
            logging.info(f'收到数据：{data_json}')

            # 打开JSON文件
            with open(data_json['config_path'], 'r+', encoding='utf-8') as file:
                # 读取文件内容
                data = json.load(file)

                # 遍历 data_json 并更新或添加到 data
                for key, value in data_json['data'].items():
                    data[key] = value

                # 将文件指针移动到文件开头
                file.seek(0)

                # 将修改后的数据写回文件
                json.dump(data, file, ensure_ascii=False, indent=2)

                # 截断文件
                file.truncate()

            logging.info(f'配置更新成功！')

            return jsonify({"code": 200, "msg": "配置更新成功！"})
        except Exception as e:
            logging.error(traceback.format_exc())
            return jsonify({"code": -1, "msg": f"配置更新失败！{e}"})

    """
    系统命令
        type 命令类型（run/stop/restart/factory）
        data 传入的json

    data_json = {
        "type": "命令名",
        "data": {
            "key": "value"
        }
    }

    return:
        {"code": 200, "msg": "成功"}
        {"code": -1, "msg": "失败"}
    """
    @app.route('/sys_cmd', methods=['POST'])
    def sys_cmd():
        try:
            data_json = request.get_json()
            logging.info(f'收到数据：{data_json}')
            logging.info(f"开始执行 {data_json['type']}命令...")

            resp_json = {}

            if data_json['type'] == 'run':
                """
                {
                    "type": "run",
                    "data": {
                        "config_path": "config.json"
                    }
                }
                """
                # 运行
                resp_json = run_external_program(data_json['data']['config_path'])
            elif data_json['type'] =='stop':
                """
                {
                    "type": "stop",
                    "data": {
                        "config_path": "config.json"
                    }
                }
                """
                # 停止
                resp_json = stop_external_program()
            elif data_json['type'] =='restart':
                """
                {
                    "type": "factory",
                    "data": {
                        "config_path": "config.json"
                    }
                }
                """
                # 重启
                resp_json = restart_application()
            elif data_json['type'] =='factory':
                """
                {
                    "type": "factory",
                    "data": {
                        "src_path": "config.json.bak",
                        "dst_path": "config.json"
                    }
                }
                """
                # 恢复出厂
                resp_json = factory(data_json['data']['src_path'], data_json['data']['dst_path'])

            return jsonify(resp_json)
        except Exception as e:
            logging.error(traceback.format_exc())
            return jsonify({"code": -1, "msg": f"{data_json['type']}执行失败！{e}"})

    """
    发送数据
        type 数据类型（comment/gift/entrance/reread/tuning/...）
        data 传入的json，根据数据类型自行适配

    data_json = {
        "type": "数据类型",
        "data": {
            "key": "value"
        }
    }

    return:
        {"code": 200, "msg": "成功"}
        {"code": -1, "msg": "失败"}
    """
    @app.route('/send', methods=['POST'])
    def send():
        global my_handle, config

        try:
            try:
                data_json = request.get_json()
                logging.info(f"send收到数据：{data_json}")

                if my_handle is None:
                    return jsonify({"code": -1, "msg": f"系统还没运行，请先运行后再发送数据！"})

                if data_json["type"] == "reread":
                    """
                    {
                        "type": "reread",
                        "data": {
                            "platform": "哔哩哔哩",
                            "username": "用户名",
                            "content": "弹幕内容"
                        }
                    }
                    """
                    my_handle.reread_handle(data_json['data'])
                elif data_json["type"] == "tuning":
                    """
                    {
                        "type": "tuning",
                        "data": {
                            "platform": "聊天模式",
                            "username": "用户名",
                            "content": "弹幕内容"
                        }
                    }
                    """
                    my_handle.tuning_handle(data_json['data'])
                elif data_json["type"] == "comment":
                    """
                    {
                        "type": "comment",
                        "data": {
                            "platform": "哔哩哔哩",
                            "username": "用户名",
                            "content": "弹幕内容"
                        }
                    }
                    """
                    my_handle.process_data(data_json['data'], "comment")
                elif data_json["type"] == "gift":
                    """
                    {
                        "type": "gift",
                        "data": {
                            "platform": "哔哩哔哩",
                            "gift_name": "礼物名",
                            "username": "用户名",
                            "num": 礼物数量,
                            "unit_price": 礼物单价,
                            "total_price": 礼物总价,
                            "content": "弹幕内容"
                        }
                    }
                    """
                    my_handle.process_data(data_json['data'], "gift")
                elif data_json["type"] == "entrance":
                    """
                    {
                        "type": "entrance",
                        "data": {
                            "platform": "哔哩哔哩",
                            "username": "用户名",
                            "content": "入场信息"
                        }
                    }
                    """
                    my_handle.process_data(data_json['data'], "entrance")

                return jsonify({"code": 200, "msg": "发送数据成功！"})
            except Exception as e:
                logging.error(traceback.format_exc())
                return jsonify({"code": -1, "msg": f"发送数据失败！{e}"})

        except Exception as e:
            logging.error(traceback.format_exc())
            return jsonify({"code": -1, "msg": f"发送数据失败！{e}"})

    url = f'http://localhost:{port}/static/index.html'
    webbrowser.open(url)
    logging.info(f"浏览器访问地址：{url}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
