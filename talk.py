import logging, time
import threading
import sys, os
import random
import schedule
import traceback
import asyncio
import copy
from functools import partial

from flask import Flask, send_from_directory, render_template, request, jsonify
from flask_cors import CORS

import keyboard
import pyaudio
import wave
import numpy as np
import speech_recognition as sr
from aip import AipSpeech
import signal

from utils.common import Common
from utils.logger import Configure_logger
from utils.config import Config
from utils.my_handle import My_handle

config = None
common = None
my_handle = None
last_username_list = None
# 空闲时间计数器
global_idle_time = 0

def start_server():
    global config, common, my_handle
    global thread, do_listen_and_comment_thread, stop_do_listen_and_comment_thread_event

    thread = None
    do_listen_and_comment_thread = None
    stop_do_listen_and_comment_thread_event = threading.Event()

    # 最新入场的用户名列表
    last_username_list = [""]

    common = Common()
    # 日志文件路径
    log_path = "./log/log-" + common.get_bj_time(1) + ".txt"
    Configure_logger(log_path)

    config_path = "config.json"
    config = Config(config_path)

    my_handle = My_handle(config_path)
    if my_handle is None:
        logging.error("程序初始化失败！")
        exit(0)

    # 冷却时间 0.5 秒
    cooldown = 0.5 
    last_pressed = 0

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

    """
    按键监听板块
    """
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

        config = Config(config_path)

        # 是否启用按键监听，不启用的话就不用执行了
        if False == config.get("talk", "key_listener_enable"):
            return

        while True:
            try:
                # 检查是否收到停止事件
                if stop_do_listen_and_comment_thread_event.is_set():
                    logging.info(f'停止录音~')
                    break

                config = Config(config_path)
            
                # 根据接入的语音识别类型执行
                if "baidu" == config.get("talk", "type"):
                    # 设置音频参数
                    FORMAT = pyaudio.paInt16
                    CHANNELS = config.get("talk", "CHANNELS")
                    RATE = config.get("talk", "RATE")

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
                elif "faster_whisper" == config.get("talk", "type"):
                    from faster_whisper import WhisperModel

                    # 设置音频参数
                    FORMAT = pyaudio.paInt16
                    CHANNELS = config.get("talk", "CHANNELS")
                    RATE = config.get("talk", "RATE")

                    audio_out_path = config.get("play_audio", "out_path")

                    if not os.path.isabs(audio_out_path):
                        if not audio_out_path.startswith('./'):
                            audio_out_path = './' + audio_out_path
                    file_name = 'faster_whisper_' + common.get_bj_time(4) + '.wav'
                    WAVE_OUTPUT_FILENAME = common.get_new_audio_path(audio_out_path, file_name)
                    # WAVE_OUTPUT_FILENAME = './out/faster_whisper_' + common.get_bj_time(4) + '.wav'

                    frames = audio_listen(config.get("talk", "volume_threshold"), config.get("talk", "silence_threshold"))

                    # 将音频保存为WAV文件
                    with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                        wf.setframerate(RATE)
                        wf.writeframes(b''.join(frames))

                    # Run on GPU with FP16
                    model = WhisperModel(model_size_or_path=config.get("talk", "faster_whisper", "model_size"), \
                                        device=config.get("talk", "faster_whisper", "device"), \
                                        compute_type=config.get("talk", "faster_whisper", "compute_type"), \
                                        download_root=config.get("talk", "faster_whisper", "download_root"))

                    segments, info = model.transcribe(WAVE_OUTPUT_FILENAME, beam_size=config.get("talk", "faster_whisper", "beam_size"))

                    logging.debug("识别语言为：'%s'，概率：%f" % (info.language, info.language_probability))

                    content = ""
                    for segment in segments:
                        logging.info("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
                        content += segment.text + "。"
                    
                    if content == "":
                        return

                    # 输出识别结果
                    logging.info("识别结果：" + content)
                    user_name = config.get("talk", "username")

                    data = {
                        "platform": "本地聊天",
                        "username": user_name,
                        "content": content
                    }

                    my_handle.process_data(data, "talk")

                if not status:
                    return
            except Exception as e:
                logging.error(traceback.format_exc())


    def on_key_press(event):
        global do_listen_and_comment_thread, stop_do_listen_and_comment_thread_event

        # 是否启用按键监听，不启用的话就不用执行了
        if False == config.get("talk", "key_listener_enable"):
            return

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

    if config.get("talk", "key_listener_enable"):
        logging.info(f'单击键盘 {trigger_key} 按键进行录音喵~ 由于其他任务还要启动，如果按键没有反应，请等待一段时间')

    # 创建并启动按键监听线程
    thread = threading.Thread(target=key_listener)
    thread.start()

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
            "platform": "聊天模式",
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
                                "platform": "聊天模式",
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
                                "platform": "聊天模式",
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


    # 起飞
    # audio_listen_google()


# 退出程序
def exit_handler(signum, frame):
    print("Received signal:", signum)

    # threading.current_thread().exit()

    # os._exit(0)


if __name__ == '__main__':
    # 键盘监听线程
    thread = None
    do_listen_and_comment_thread = None
    stop_do_listen_and_comment_thread_event = None

    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)

    start_server()

    thread.join() # 等待子线程退出

    os._exit(0)
