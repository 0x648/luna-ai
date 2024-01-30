import logging, os
import threading
import schedule
import random
import asyncio
import traceback
import copy

from functools import partial

from typing import *

from flask import Flask, send_from_directory, render_template, request, jsonify
from flask_cors import CORS

from utils.common import Common
from utils.config import Config
from utils.logger import Configure_logger
from utils.my_handle import My_handle

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

    # 配置文件路径
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
            "platform": "微信视频号",
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
                    # logging.info(task)
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

        except Exception as e:
            logging.error(traceback.format_exc())

    if config.get("idle_time_task", "enable"):
        # 创建闲时任务子线程并启动
        threading.Thread(target=lambda: asyncio.run(idle_time_task())).start()


    app = Flask(__name__)
    CORS(app)  # 允许跨域请求

    # 用于去重用的列表
    seq_list = []

    @app.route('/wxlive', methods=['POST'])
    def wxlive():
        global my_handle, config, global_idle_time

        try:
            # 获取 POST 请求中的数据
            data = request.json
            # 这里可以添加代码处理接收到的数据
            logging.debug(data)

            if data['events'][0]['seq'] in seq_list:
                return jsonify({"code": 1, "message": "重复数据过滤"})

            # 如果列表长度达到30，移除最旧的元素
            if len(seq_list) >= 30:
                seq_list.pop(0)
            
            # 添加新元素
            seq_list.append(data['events'][0]['seq'])

            # 弹幕数据
            if data['events'][0]['decoded_type'] == "comment":
                # 闲时计数清零
                global_idle_time = 0

                content = data['events'][0]['content']  # 获取弹幕内容
                user_name = data['events'][0]['nickname']  # 获取发送弹幕的用户昵称

                logging.info(f"[{user_name}]: {content}")

                data = {
                    "platform": "微信视频号",
                    "username": user_name,
                    "content": content
                }

                my_handle.process_data(data, "comment")
            # 入场数据
            elif data['events'][0]['decoded_type'] == "enter":
                user_name = data['events'][0]['nickname']

                logging.info(f"用户：{user_name} 进入直播间")

                # 添加用户名到最新的用户名列表
                add_username_to_last_username_list(user_name)

                data = {
                    "platform": "微信视频号",
                    "username": user_name,
                    "content": "进入直播间"
                }

                my_handle.process_data(data, "entrance")
                pass

            # 响应
            return jsonify({"code": 200, "message": "成功接收"})
        except Exception as e:
            logging.error(traceback.format_exc())
            my_handle.abnormal_alarm_handle("platform")
            return jsonify({"code": -1, "message": f"发送数据失败！{e}"})
        
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
    # app.run(host="0.0.0.0", port=8082, debug=True)


if __name__ == '__main__':
    start_server()

