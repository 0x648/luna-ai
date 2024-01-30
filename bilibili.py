import logging, os
import threading
import schedule
import random
import asyncio
import traceback
import copy

from functools import partial

from flask import Flask, send_from_directory, render_template, request, jsonify
from flask_cors import CORS

# 导入所需的库
from bilibili_api import Credential, live, sync, login

from utils.common import Common
from utils.config import Config
from utils.logger import Configure_logger
from utils.my_handle import My_handle

"""
	___ _                       
	|_ _| | ____ _ _ __ ___  ___ 
	 | || |/ / _` | '__/ _ \/ __|
	 | ||   < (_| | | | (_) \__ \
	|___|_|\_\__,_|_|  \___/|___/

"""

config = None
common = None
my_handle = None
# last_liveroom_data = None
last_username_list = None
# 空闲时间计数器
global_idle_time = 0

# 点火起飞
def start_server():
    global config, common, my_handle, last_username_list

    config_path = "config.json"

    common = Common()
    config = Config(config_path)
    # 日志文件路径
    log_path = "./log/log-" + common.get_bj_time(1) + ".txt"
    Configure_logger(log_path)

    # 获取 httpx 库的日志记录器
    httpx_logger = logging.getLogger("httpx")
    # 设置 httpx 日志记录器的级别为 WARNING
    httpx_logger.setLevel(logging.WARNING)

    # 最新入场的用户名列表
    last_username_list = [""]

    my_handle = My_handle(config_path)
    if my_handle is None:
        logging.error("程序初始化失败！")
        os._exit(0)

    # HTTP API线程
    def http_api_thread():
        app = Flask(__name__, static_folder='./')
        CORS(app)  # 允许跨域请求
        
        @app.route('/send', methods=['POST'])
        def send():
            global my_handle, config

            try:
                try:
                    data_json = request.get_json()
                    logging.info(f"API收到数据：{data_json}")

                    if data_json["type"] == "reread":
                        my_handle.reread_handle(data_json)
                    elif data_json["type"] == "comment":
                        my_handle.process_data(data_json, "comment")
                    elif data_json["type"] == "tuning":
                        my_handle.tuning_handle(data_json)

                    return jsonify({"code": 200, "message": "发送数据成功！"})
                except Exception as e:
                    logging.error(f"发送数据失败！{e}")
                    return jsonify({"code": -1, "message": f"发送数据失败！{e}"})

            except Exception as e:
                return jsonify({"code": -1, "message": f"发送数据失败！{e}"})
            
        app.run(host=config.get("api_ip"), port=config.get("api_port"), debug=False)
    
    # HTTP API线程并启动
    schedule_thread = threading.Thread(target=http_api_thread)
    schedule_thread.start()

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
    def run_schedule():
        global config

        try:
            for index, task in enumerate(config.get("schedule")):
                if task["enable"]:
                    # print(task)
                    # 设置定时任务，每隔n秒执行一次
                    schedule.every(task["time"]).seconds.do(partial(schedule_task, index))
        except Exception as e:
            logging.error(traceback.format_exc())

        while True:
            schedule.run_pending()
            # time.sleep(1)  # 控制每次循环的间隔时间，避免过多占用 CPU 资源


    if any(item['enable'] for item in config.get("schedule")):
        # 创建定时任务子线程并启动
        schedule_thread = threading.Thread(target=run_schedule)
        schedule_thread.start()


    # 启动动态文案
    async def run_trends_copywriting():
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

                        # 空数据判断
                        if data_json["content"] != None and data_json["content"] != "":
                            # 发给直接复读进行处理
                            my_handle.reread_handle(data_json)

                            await asyncio.sleep(config.get("trends_copywriting", "play_interval"))
        except Exception as e:
            logging.error(traceback.format_exc())

    if config.get("trends_copywriting", "enable"):
        # 创建动态文案子线程并启动
        threading.Thread(target=lambda: asyncio.run(run_trends_copywriting())).start()

    # 闲时任务
    async def idle_time_task():
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
                                "platform": "哔哩哔哩",
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
                        if last_mode == 1 or not config.get("idle_time_task", "comment", "enable"):
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

                            # 发送给处理函数
                            data = {
                                "platform": "哔哩哔哩",
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

        except Exception as e:
            logging.error(traceback.format_exc())

    if config.get("idle_time_task", "enable"):
        # 创建闲时任务子线程并启动
        threading.Thread(target=lambda: asyncio.run(idle_time_task())).start()


    try:
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
        my_handle.abnormal_alarm_handle("platform")
        # os._exit(0)

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


if __name__ == '__main__':
    start_server()
