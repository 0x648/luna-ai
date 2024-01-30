from playwright.sync_api import sync_playwright
import logging, os
import time
import threading
import schedule
import random
import traceback
import asyncio
import copy

from functools import partial

from flask import Flask, send_from_directory, render_template, request, jsonify
from flask_cors import CORS

from google.protobuf.json_format import MessageToDict
from configparser import ConfigParser
import kuaishou_pb2

from utils.common import Common
from utils.logger import Configure_logger
from utils.my_handle import My_handle
from utils.config import Config


config = None
common = None
my_handle = None
last_username_list = None
# 空闲时间计数器
global_idle_time = 0


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
            my_handle.abnormal_alarm_handle("platform")
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


def start_server():
    global config, common, my_handle, last_username_list

    config_path = "config.json"

    config = Config(config_path)
    common = Common()
    # 日志文件路径
    log_path = "./log/log-" + common.get_bj_time(1) + ".txt"
    Configure_logger(log_path)

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

    # 定时任务
    def schedule_task(index):
        global config, common, my_handle, last_username_list

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
            # 'user_num': last_liveroom_data["OnlineUserCount"],
            'last_username': last_username_list[-1],
        }

        # 使用字典进行字符串替换
        if any(var in random_copy for var in variables):
            content = random_copy.format(**{var: value for var, value in variables.items() if var in random_copy})
        else:
            content = random_copy

        data = {
            "platform": "快手",
            "username": None,
            "content": content
        }

        logging.info(f"定时任务：{content}")

        my_handle.process_data(data, "schedule")


    # 启动定时任务
    def run_schedule():
        try:
            for index, task in enumerate(config.get("schedule")):
                if task["enable"]:
                    # print(task)
                    # 设置定时任务，每隔n秒执行一次
                    schedule.every(task["time"]).seconds.do(partial(schedule_task, index))
        except Exception as e:
            logging.error(e)

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
                                "platform": "快手",
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
                                "platform": "快手",
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


    run().run_live()


if __name__ == '__main__':
    start_server()
    