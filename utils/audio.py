import time, logging
import requests, re
import json, threading
import subprocess
import pygame
from queue import Queue, Empty
import edge_tts
import asyncio
from copy import deepcopy
import aiohttp
import glob
import os, random
import copy
import traceback

from elevenlabs import generate, play, set_api_key

from pydub import AudioSegment

from .common import Common
from .logger import Configure_logger
from .config import Config
from utils.audio_handle.my_tts import MY_TTS
from utils.audio_handle.audio_player import AUDIO_PLAYER


class Audio:
    # 文案播放标志 0手动暂停 1临时暂停  2循环播放
    copywriting_play_flag = -1

    # 初始化多个pygame.mixer实例
    mixer_normal = pygame.mixer
    mixer_copywriting = pygame.mixer

    # 全局变量用于保存恢复文案播放计时器对象
    unpause_copywriting_play_timer = None

    audio_player = None
    # # 创建消息队列
    # message_queue = Queue()
    # # 创建音频路径队列
    # voice_tmp_path_queue = Queue()
    # # 文案单独一个线程排队播放
    # only_play_copywriting_thread = None

    abnormal_alarm_data = {
        "platform": {
            "error_count": 0
        },
        "llm": {
            "error_count": 0
        },
        "tts": {
            "error_count": 0
        },
        "svc": {
            "error_count": 0
        },
        "visual_body": {
            "error_count": 0
        },
        "other": {
            "error_count": 0
        }
    }

    def __init__(self, config_path, type=1):  
        self.config = Config(config_path)
        self.common = Common()
        self.my_tts = MY_TTS(config_path)

        # 文案模式
        if type == 2:
            logging.info("文案模式的Audio初始化...")
            return
    
        # 创建消息队列
        self.message_queue = Queue()
        # 创建音频路径队列
        self.voice_tmp_path_queue = Queue()
        # 文案单独一个线程排队播放
        self.only_play_copywriting_thread = None
        
        # 日志文件路径
        file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        Configure_logger(file_path)

        # 旧版同步写法
        # threading.Thread(target=self.message_queue_thread).start()
        # 改异步
        threading.Thread(target=lambda: asyncio.run(self.message_queue_thread())).start()

        # 音频合成单独一个线程排队播放
        threading.Thread(target=lambda: asyncio.run(self.only_play_audio())).start()
        # self.only_play_audio_thread = threading.Thread(target=self.only_play_audio)
        # self.only_play_audio_thread.start()

        # 文案单独一个线程排队播放
        if self.only_play_copywriting_thread == None:
            # self.only_play_copywriting_thread = threading.Thread(target=lambda: asyncio.run(self.only_play_copywriting()))
            self.only_play_copywriting_thread = threading.Thread(target=self.start_only_play_copywriting)
            self.only_play_copywriting_thread.start()

        Audio.audio_player =  AUDIO_PLAYER(self.config.get("audio_player"))


    # 重载config
    def reload_config(self, config_path):
        self.config = Config(config_path)
        self.my_tts = MY_TTS(config_path)

    # 从指定文件夹中搜索指定文件，返回搜索到的文件路径
    def search_files(self, root_dir, target_file="", ignore_extension=False):
        matched_files = []

        # 如果忽略扩展名，只取目标文件的基本名
        target_for_comparison = os.path.splitext(target_file)[0] if ignore_extension else target_file

        for root, dirs, files in os.walk(root_dir):
            for file in files:
                # 根据 ignore_extension 判断是否要去除扩展名后再比较
                file_to_compare = os.path.splitext(file)[0] if ignore_extension else file

                if file_to_compare == target_for_comparison:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, root_dir)
                    relative_path = relative_path.replace("\\", "/")  # 将反斜杠替换为斜杠
                    matched_files.append(relative_path)

        return matched_files


    # 获取本地音频文件夹内所有的音频文件名
    def get_dir_audios_filename(self, audio_path, type=0):
        """获取本地音频文件夹内所有的音频文件名

        Args:
            audio_path (str): 音频文件路径
            type (int, 可选): 区分返回内容，0返回完整文件名，1返回文件名不含拓展名. 默认是0

        Returns:
            list: 文件名列表
        """
        try:
            # 使用 os.walk 遍历文件夹及其子文件夹
            audio_files = []
            for root, dirs, files in os.walk(audio_path):
                for file in files:
                    if file.endswith(('.mp3', '.wav', '.MP3', '.WAV', '.flac', '.aac', '.ogg', '.m4a')):
                        audio_files.append(os.path.join(root, file))

            # 提取文件名或保留完整文件名
            if type == 1:
                # 只返回文件名不含拓展名
                file_names = [os.path.splitext(os.path.basename(file))[0] for file in audio_files]
            else:
                # 返回完整文件名
                file_names = [os.path.basename(file) for file in audio_files]
                # 保留子文件夹路径
                # file_names = [os.path.relpath(file, audio_path) for file in audio_files]

            logging.debug("获取到本地音频文件名列表如下：")
            logging.debug(file_names)

            return file_names
        except Exception as e:
            logging.error(traceback.format_exc())
            return None


    # 音频合成消息队列线程
    async def message_queue_thread(self):
        logging.info("创建音频合成消息队列线程")
        while True:  # 无限循环，直到队列为空时退出
            try:
                message = self.message_queue.get(block=True)
                logging.debug(message)
                await self.my_play_voice(message)
                self.message_queue.task_done()

                # 加个延时 降低点edge-tts的压力
                # await asyncio.sleep(0.5)
            except Exception as e:
                logging.error(traceback.format_exc())


    # 调用so-vits-svc的api
    async def so_vits_svc_api(self, audio_path=""):
        try:
            url = f"{self.config.get('so_vits_svc', 'api_ip_port')}/wav2wav"
            
            params = {
                "audio_path": audio_path,
                "tran": self.config.get("so_vits_svc", "tran"),
                "spk": self.config.get("so_vits_svc", "spk"),
                "wav_format": self.config.get("so_vits_svc", "wav_format")
            }

            # logging.info(params)

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=params) as response:
                    if response.status == 200:
                        output_path = "out/so-vits-svc_" + self.common.get_bj_time(4) + ".wav"  # Replace with the desired path to save the output WAV file
                        with open(output_path, "wb") as f:
                            f.write(await response.read())
                        logging.debug(f"so-vits-svc转换完成，音频保存在：{output_path}")

                        return output_path
                    else:
                        logging.error(await response.text())

                        return None
        except Exception as e:
            logging.error(traceback.format_exc())
            return None


    # 调用ddsp_svc的api
    async def ddsp_svc_api(self, audio_path=""):
        try:
            url = f"{self.config.get('ddsp_svc', 'api_ip_port')}/voiceChangeModel"
                
            # 读取音频文件
            with open(audio_path, "rb") as file:
                audio_file = file.read()

            data = aiohttp.FormData()
            data.add_field('sample', audio_file)
            data.add_field('fSafePrefixPadLength', str(self.config.get('ddsp_svc', 'fSafePrefixPadLength')))
            data.add_field('fPitchChange', str(self.config.get('ddsp_svc', 'fPitchChange')))
            data.add_field('sSpeakId', str(self.config.get('ddsp_svc', 'sSpeakId')))
            data.add_field('sampleRate', str(self.config.get('ddsp_svc', 'sampleRate')))

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    # 检查响应状态
                    if response.status == 200:
                        output_path = "out/ddsp-svc_" + self.common.get_bj_time(4) + ".wav"  # Replace with the desired path to save the output WAV file
                        with open(output_path, "wb") as f:
                            f.write(await response.read())
                        logging.debug(f"ddsp-svc转换完成，音频保存在：{output_path}")

                        return output_path
                    else:
                        logging.error(f"请求ddsp-svc失败，状态码：{response.status}")
                        return None

        except Exception as e:
            logging.error(traceback.format_exc())
            return None
        

    # 调用xuniren的api
    async def xuniren_api(self, audio_path=""):
        try:
            url = f"{self.config.get('xuniren', 'api_ip_port')}/audio_to_video?file_path={os.path.abspath(audio_path)}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    # 检查响应状态
                    if response.status == 200:
                        logging.info(f"xuniren合成完成")

                        return True
                    else:
                        logging.error(f"xuniren合成失败，状态码：{response.status}")
                        return False

        except Exception as e:
            logging.error(traceback.format_exc())
            return False


    # 音频合成（edge-tts / vits_fast）并播放
    def audio_synthesis(self, message):
        try:
            logging.debug(message)

            # 判断是否是点歌模式
            if message['type'] == "song":
                # 拼接json数据，存入队列
                data_json = {
                    "type": message['type'],
                    "tts_type": "none",
                    "voice_path": message['content'],
                    "content": message["content"]
                }

                if "insert_index" in data_json:
                    data_json["insert_index"] = message["insert_index"]

                # 是否开启了音频播放 
                if self.config.get("play_audio", "enable"):
                    # self.voice_tmp_path_queue.put(data_json)
                    self.message_queue.put(data_json)
                return
            # 异常报警
            elif message['type'] == "abnormal_alarm":
                # 拼接json数据，存入队列
                data_json = {
                    "type": message['type'],
                    "tts_type": "none",
                    "voice_path": message['content'],
                    "content": message["content"]
                }

                if "insert_index" in data_json:
                    data_json["insert_index"] = message["insert_index"]

                # 是否开启了音频播放 
                if self.config.get("play_audio", "enable"):
                    # self.voice_tmp_path_queue.put(data_json)
                    self.message_queue.put(data_json)
                return
            # 是否为本地问答音频
            elif message['type'] == "local_qa_audio":
                # 拼接json数据，存入队列
                data_json = {
                    "type": message['type'],
                    "tts_type": "none",
                    "voice_path": message['file_path'],
                    "content": message["content"]
                }

                if "insert_index" in data_json:
                    data_json["insert_index"] = message["insert_index"]

                # 回复时是否念用户名字
                if self.config.get("read_user_name", "enable"):
                    # 由于线程是独立的，所以回复音频的合成会慢于本地音频直接播放，所以以倒述的形式回复
                    tmp_message = deepcopy(message)
                    tmp_message['type'] = "reply"
                    tmp_message['content'] = random.choice(self.config.get("read_user_name", "reply_after"))
                    if "{username}" in tmp_message['content']:
                        tmp_message['content'] = tmp_message['content'].format(username=message['user_name'][:self.config.get("read_user_name", "username_max_len")])
                    
                    logging.info(f"tmp_message={tmp_message}")
                    
                    self.message_queue.put(tmp_message)
                # else:
                #     logging.info(f"message={message}")
                #     self.message_queue.put(message)

                # 是否开启了音频播放
                if self.config.get("play_audio", "enable"):
                    # self.voice_tmp_path_queue.put(data_json)
                    self.message_queue.put(data_json)
                return
            # 是否为助播-本地问答音频
            elif message['type'] == "assistant_anchor_audio":
                # 拼接json数据，存入队列
                data_json = {
                    "type": message['type'],
                    "tts_type": "none",
                    "voice_path": message['file_path'],
                    "content": message["content"]
                }

                if "insert_index" in data_json:
                    data_json["insert_index"] = message["insert_index"]

                # 是否开启了音频播放
                if self.config.get("play_audio", "enable"):
                    # self.voice_tmp_path_queue.put(data_json)
                    self.message_queue.put(data_json)
                return

            # 只有信息类型是 弹幕，才会进行念用户名
            elif message['type'] == "comment":
                # 回复时是否念用户名字
                if self.config.get("read_user_name", "enable"):
                    tmp_message = deepcopy(message)
                    tmp_message['type'] = "reply"
                    tmp_message['content'] = random.choice(self.config.get("read_user_name", "reply_before"))
                    if "{username}" in tmp_message['content']:
                        # 将用户名中特殊字符替换为空
                        message['user_name'] = self.common.replace_special_characters(message['user_name'], "！!@#￥$%^&*_-+/——=()（）【】}|{:;<>~`\\")
                        tmp_message['content'] = tmp_message['content'].format(username=message['user_name'][:self.config.get("read_user_name", "username_max_len")])
                    self.message_queue.put(tmp_message)
            # 闲时任务
            elif message['type'] == "idle_time_task":
                if message['content_type'] == "comment":
                    pass
                elif message['content_type'] == "local_audio":
                    # 拼接json数据，存入队列
                    data_json = {
                        "type": message['type'],
                        "tts_type": "none",
                        "voice_path": message['file_path'],
                        "content": message["content"]
                    }

                    if "insert_index" in data_json:
                        data_json["insert_index"] = message["insert_index"]
                    
                    # self.voice_tmp_path_queue.put(data_json)
                    self.message_queue.put(data_json)

                    return

            # 是否语句切分
            if self.config.get("play_audio", "text_split_enable"):
                sentences = self.common.split_sentences(message['content'])
                for s in sentences:
                    message_copy = deepcopy(message)  # 创建 message 的副本
                    message_copy["content"] = s  # 修改副本的 content
                    logging.debug(f"s={s}")
                    if not self.common.is_all_space_and_punct(s):
                        self.message_queue.put(message_copy)  # 将副本放入队列中
            else:
                self.message_queue.put(message)
            

            # 单独开线程播放
            # threading.Thread(target=self.my_play_voice, args=(type, data, config, content,)).start()
        except Exception as e:
            logging.error(traceback.format_exc())
            return


    # 音频变声 so-vits-svc + ddsp
    async def voice_change(self, voice_tmp_path):
        """音频变声 so-vits-svc + ddsp

        Args:
            voice_tmp_path (str): 待变声音频路径

        Returns:
            str: 变声后的音频路径
        """
        # 转换为绝对路径
        voice_tmp_path = os.path.abspath(voice_tmp_path)

        # 是否启用ddsp-svc来变声
        if True == self.config.get("ddsp_svc", "enable"):
            voice_tmp_path = await self.ddsp_svc_api(audio_path=voice_tmp_path)
            if voice_tmp_path:
                logging.info(f"ddsp-svc合成成功，输出到={voice_tmp_path}")
            else:
                logging.error(f"ddsp-svc合成失败，请检查配置")
                self.abnormal_alarm_handle("svc")
                return None

        # 转换为绝对路径
        voice_tmp_path = os.path.abspath(voice_tmp_path)

        # 是否启用so-vits-svc来变声
        if True == self.config.get("so_vits_svc", "enable"):
            voice_tmp_path = await self.so_vits_svc_api(audio_path=voice_tmp_path)
            if voice_tmp_path:
                logging.info(f"so_vits_svc合成成功，输出到={voice_tmp_path}")
            else:
                logging.error(f"so_vits_svc合成失败，请检查配置")
                self.abnormal_alarm_handle("svc")
                
                return None
        
        return voice_tmp_path
    

    # 播放音频
    async def my_play_voice(self, message):
        logging.debug(message)

        try:
            # 如果是tts类型为none，暂时这类为直接播放音频，所以就丢给路径队列
            if message["tts_type"] == "none":
                self.voice_tmp_path_queue.put(message)
                return
        except Exception as e:
            logging.error(traceback.format_exc())
            return

        try:
            logging.debug(f"合成音频前的原始数据：{message['content']}")
            message["content"] = self.common.remove_extra_words(message["content"], message["config"]["max_len"], message["config"]["max_char_len"])
            # logging.info("裁剪后的合成文本:" + text)

            message["content"] = message["content"].replace('\n', '。')

            # 空数据就散了吧
            if message["content"] == "":
                return
        except Exception as e:
            logging.error(traceback.format_exc())
            return
        

        # 判断消息类型，再变声并封装数据发到队列 减少冗余
        async def voice_change_and_put_to_queue(message, voice_tmp_path):
            # 拼接json数据，存入队列
            data_json = {
                "type": message['type'],
                "voice_path": voice_tmp_path,
                "content": message["content"]
            }

            if "insert_index" in message:
                data_json["insert_index"] = message["insert_index"]

            # 区分消息类型是否是 回复xxx 并且 关闭了变声
            if message["type"] == "reply" and False == self.config.get("read_user_name", "voice_change"):
                # 是否开启了音频播放，如果没开，则不会传文件路径给播放队列
                if self.config.get("play_audio", "enable"):
                    self.voice_tmp_path_queue.put(data_json)
                    return True
            # 区分消息类型是否是 念弹幕 并且 关闭了变声
            elif message["type"] == "read_comment" and False == self.config.get("read_comment", "voice_change"):
                # 是否开启了音频播放，如果没开，则不会传文件路径给播放队列
                if self.config.get("play_audio", "enable"):
                    self.voice_tmp_path_queue.put(data_json)
                    return True

            voice_tmp_path = await self.voice_change(voice_tmp_path)
            
            # 更新音频路径
            data_json["voice_path"] = voice_tmp_path

            # 是否开启了音频播放，如果没开，则不会传文件路径给播放队列
            if self.config.get("play_audio", "enable"):
                self.voice_tmp_path_queue.put(data_json)

            return True

        # 区分TTS类型
        try:
            if message["tts_type"] == "vits":
                # 语言检测
                language = self.common.lang_check(message["content"])

                logging.debug(f"message['content']={message['content']}")

                # 自定义语言名称（需要匹配请求解析）
                language_name_dict = {"en": "英文", "zh": "中文", "jp": "日文"}  

                if language in language_name_dict:
                    language = language_name_dict[language]
                else:
                    language = "自动"  # 无法识别出语言代码时的默认值

                # logging.info("language=" + language)

                data = {
                    "type": message["data"]["type"],
                    "api_ip_port": message["data"]["api_ip_port"],
                    "id": message["data"]["id"],
                    "format": message["data"]["format"],
                    "lang": language,
                    "length": message["data"]["length"],
                    "noise": message["data"]["noise"],
                    "noisew": message["data"]["noisew"],
                    "max": message["data"]["max"],
                    "sdp_radio": message["data"]["sdp_radio"],
                    "content": message["content"]
                }

                # 调用接口合成语音
                voice_tmp_path = await self.my_tts.vits_api(data)
            elif message["tts_type"] == "bert_vits2":
                if message["data"]["type"] == "hiyori":
                    if message["data"]["language"] == "auto":
                        # 自动检测语言
                        language = self.common.lang_check(message["content"])

                        logging.debug(f'language={language}')

                        # 自定义语言名称（需要匹配请求解析）
                        language_name_dict = {"en": "EN", "zh": "ZH", "ja": "JP"}  

                        if language in language_name_dict:
                            language = language_name_dict[language]
                        else:
                            language = "ZH"  # 无法识别出语言代码时的默认值
                    else:
                        language = message["data"]["language"]

                    data = {
                        "api_ip_port": message["data"]["api_ip_port"],
                        "type": message["data"]["type"],
                        "model_id": message["data"]["model_id"],
                        "speaker_name": message["data"]["speaker_name"],
                        "speaker_id": message["data"]["speaker_id"],
                        "language": language,
                        "length": message["data"]["length"],
                        "noise": message["data"]["noise"],
                        "noisew": message["data"]["noisew"],
                        "sdp_radio": message["data"]["sdp_radio"],
                        "auto_translate": message["data"]["auto_translate"],
                        "auto_split": message["data"]["auto_split"],
                        "emotion": message["data"]["emotion"],
                        "style_text": message["data"]["style_text"],
                        "style_weight": message["data"]["style_weight"],
                        "content": message["content"]
                    }

                    

                # 调用接口合成语音
                voice_tmp_path = await self.my_tts.bert_vits2_api(data)
            elif message["tts_type"] == "vits_fast":
                if message["data"]["language"] == "自动识别":
                    # 自动检测语言
                    language = self.common.lang_check(message["content"])

                    logging.debug(f'language={language}')

                    # 自定义语言名称（需要匹配请求解析）
                    language_name_dict = {"en": "English", "zh": "简体中文", "ja": "日本語"}  

                    if language in language_name_dict:
                        language = language_name_dict[language]
                    else:
                        language = "简体中文"  # 无法识别出语言代码时的默认值
                else:
                    language = message["data"]["language"]

                # logging.info("language=" + language)

                data = {
                    "api_ip_port": message["data"]["api_ip_port"],
                    "character": message["data"]["character"],
                    "speed": message["data"]["speed"],
                    "language": language,
                    "content": message["content"]
                }

                # 调用接口合成语音
                voice_tmp_path = self.my_tts.vits_fast_api(data)
                # logging.info(data_json)
            elif message["tts_type"] == "edge-tts":
                data = {
                    "content": message["content"],
                    "voice": message["data"]["voice"],
                    "rate": message["data"]["rate"],
                    "volume": message["data"]["volume"]
                }

                # 调用接口合成语音
                voice_tmp_path = await self.my_tts.edge_tts_api(data)
            elif message["tts_type"] == "elevenlabs":
                # 如果配置了密钥就设置上0.0
                if message["data"]["api_key"] != "":
                    set_api_key(message["data"]["api_key"])

                audio = generate(
                    text=message["content"],
                    voice=message["data"]["voice"],
                    model=message["data"]["model"]
                )

                play(audio)
                logging.info(f"elevenlabs合成内容：【{message['content']}】")

                return
            elif message["tts_type"] == "genshinvoice_top":
                voice_tmp_path = await self.my_tts.genshinvoice_top_api(message["content"])
            elif message["tts_type"] == "tts_ai_lab_top":
                voice_tmp_path = await self.my_tts.tts_ai_lab_top_api(message["content"])
            elif message["tts_type"] == "bark_gui":
                data = {
                    "api_ip_port": message["data"]["api_ip_port"],
                    "spk": message["data"]["spk"],
                    "generation_temperature": message["data"]["generation_temperature"],
                    "waveform_temperature": message["data"]["waveform_temperature"],
                    "end_of_sentence_probability": message["data"]["end_of_sentence_probability"],
                    "quick_generation": message["data"]["quick_generation"],
                    "seed": message["data"]["seed"],
                    "batch_count": message["data"]["batch_count"],
                    "content": message["content"]
                }

                # 调用接口合成语音
                voice_tmp_path = self.my_tts.bark_gui_api(data)
            elif message["tts_type"] == "vall_e_x":
                data = {
                    "api_ip_port": message["data"]["api_ip_port"],
                    "language": message["data"]["language"],
                    "accent": message["data"]["accent"],
                    "voice_preset": message["data"]["voice_preset"],
                    "voice_preset_file_path": message["data"]["voice_preset_file_path"],
                    "content": message["content"]
                }

                # 调用接口合成语音
                voice_tmp_path = self.my_tts.vall_e_x_api(data)
            elif message["tts_type"] == "openai_tts":
                data = {
                    "type": message["data"]["type"],
                    "api_ip_port": message["data"]["api_ip_port"],
                    "model": message["data"]["model"],
                    "voice": message["data"]["voice"],
                    "api_key": message["data"]["api_key"],
                    "content": message["content"]
                }

                # 调用接口合成语音
                voice_tmp_path = self.my_tts.openai_tts_api(data)
            elif message["tts_type"] == "reecho_ai":
                voice_tmp_path = await self.my_tts.reecho_ai_api(message["content"])
            elif message["tts_type"] == "gradio_tts":
                data = {
                    "request_parameters": message["data"]["request_parameters"],
                    "content": message["content"]
                }

                voice_tmp_path = self.my_tts.gradio_tts_api(data)  
            elif message["tts_type"] == "gpt_sovits":
                if message["data"]["language"] == "自动识别":
                    # 自动检测语言
                    language = self.common.lang_check(message["content"])

                    logging.debug(f'language={language}')

                    # 自定义语言名称（需要匹配请求解析）
                    language_name_dict = {"en": "英文", "zh": "中文", "ja": "日文"}  

                    if language in language_name_dict:
                        language = language_name_dict[language]
                    else:
                        language = "中文"  # 无法识别出语言代码时的默认值
                else:
                    language = message["data"]["language"]
                    
                data = {
                    "api_ip_port": message["data"]["api_ip_port"],
                    "ref_audio_path": message["data"]["ref_audio_path"],
                    "prompt_text": message["data"]["prompt_text"],
                    "prompt_language": message["data"]["prompt_language"],
                    "language": language,
                    "content": message["content"]
                }

                voice_tmp_path = await self.my_tts.gpt_sovits_api(data)  
            elif message["tts_type"] == "none":
                pass
        except Exception as e:
            logging.error(traceback.format_exc())
            return False
        
        if voice_tmp_path is None:
            logging.error(f"{message['tts_type']}合成失败，请排查配置、网络等问题")
            self.abnormal_alarm_handle("tts")
            
            return False
        
        logging.info(f"{message['tts_type']}合成成功，合成内容：【{message['content']}】，输出到={voice_tmp_path}")
                 
        await voice_change_and_put_to_queue(message, voice_tmp_path)  

        return True

    # 音频变速
    def audio_speed_change(self, audio_path, speed_factor=1.0, pitch_factor=1.0):
        """音频变速

        Args:
            audio_path (str): 音频路径
            speed (int, optional): 部分速度倍率.  默认 1.
            type (int, optional): 变调倍率 1为不变调.  默认 1.

        Returns:
            str: 变速后的音频路径
        """
        logging.debug(f"audio_path={audio_path}, speed_factor={speed_factor}, pitch_factor={pitch_factor}")

        # 使用 pydub 打开音频文件
        audio = AudioSegment.from_file(audio_path)

        # 变速
        if speed_factor > 1.0:
            audio_changed = audio.speedup(playback_speed=speed_factor)
        elif speed_factor < 1.0:
            # 如果要放慢,使用set_frame_rate调帧率
            orig_frame_rate = audio.frame_rate
            slow_frame_rate = int(orig_frame_rate * speed_factor)
            audio_changed = audio._spawn(audio.raw_data, overrides={"frame_rate": slow_frame_rate})
        else:
            audio_changed = audio

        # 变调
        if pitch_factor != 1.0:
            semitones = 12 * (pitch_factor - 1)
            audio_changed = audio_changed._spawn(audio_changed.raw_data, overrides={
                "frame_rate": int(audio_changed.frame_rate * (2.0 ** (semitones / 12.0)))
            }).set_frame_rate(audio_changed.frame_rate)

        # 变速
        # audio_changed = audio.speedup(playback_speed=speed_factor)

        # # 变调
        # if pitch_factor != 1.0:
        #     semitones = 12 * (pitch_factor - 1)
        #     audio_changed = audio_changed._spawn(audio_changed.raw_data, overrides={
        #         "frame_rate": int(audio_changed.frame_rate * (2.0 ** (semitones / 12.0)))
        #     }).set_frame_rate(audio_changed.frame_rate)

        # 导出为临时文件
        audio_out_path = self.config.get("play_audio", "out_path")
        if not os.path.isabs(audio_out_path):
            if not audio_out_path.startswith('./'):
                audio_out_path = './' + audio_out_path
        file_name = f"temp_{self.common.get_bj_time(4)}.wav"
        temp_path = self.common.get_new_audio_path(audio_out_path, file_name)

        # 导出为新音频文件
        audio_changed.export(temp_path, format="wav")

        # 转换为绝对路径
        temp_path = os.path.abspath(temp_path)

        return temp_path


    # 只进行普通音频播放   
    async def only_play_audio(self):
        try:
            captions_config = self.config.get("captions")

            Audio.mixer_normal.init()
            while True:
                try:
                    # 从队列中获取音频文件路径 队列为空时阻塞等待
                    data_json = self.voice_tmp_path_queue.get(block=True)

                    logging.debug(f"普通音频播放队列 data_json={data_json}")

                    voice_tmp_path = data_json["voice_path"]

                    # 如果文案标志位为2，则说明在播放中，需要暂停
                    if Audio.copywriting_play_flag == 2:
                        logging.debug(f"暂停文案播放，等待一个切换间隔")
                        # 文案暂停
                        self.pause_copywriting_play()
                        Audio.copywriting_play_flag = 1
                        # 等待一个切换时间
                        await asyncio.sleep(float(self.config.get("copywriting", "switching_interval")))
                        logging.debug(f"切换间隔结束，准备播放普通音频")

                    # 是否启用字幕输出
                    if captions_config["enable"]:
                        # 输出当前播放的音频文件的文本内容到字幕文件中
                        self.common.write_content_to_file(captions_config["file_path"], data_json["content"], write_log=False)


                    # 判断是否发送web字幕打印机
                    if self.config.get("web_captions_printer", "enable"):
                        self.common.send_to_web_captions_printer(self.config.get("web_captions_printer", "api_ip_port"), data_json)

                    # 不仅仅是说话间隔，还是等待文本捕获刷新数据
                    await asyncio.sleep(self.config.get("play_audio", "normal_interval"))

                    # 音频变速
                    random_speed = 1
                    if self.config.get("audio_random_speed", "normal", "enable"):
                        random_speed = self.common.get_random_value(self.config.get("audio_random_speed", "normal", "speed_min"),
                                                                    self.config.get("audio_random_speed", "normal", "speed_max"))
                        voice_tmp_path = self.audio_speed_change(voice_tmp_path, random_speed)

                    # print(voice_tmp_path)

                    # 根据接入的虚拟身体类型执行不同逻辑
                    if self.config.get("visual_body") == "xuniren":
                        await self.xuniren_api(voice_tmp_path)
                    else:
                        if self.config.get("play_audio", "player") in ["audio_player", "audio_player_v2"]:
                            if "insert_index" in data_json:
                                data_json = {
                                    "type": data_json["type"],
                                    "voice_path": voice_tmp_path,
                                    "content": data_json["content"],
                                    "random_speed": {
                                        "enable": False,
                                        "max": 1.3,
                                        "min": 0.8
                                    },
                                    "speed": 1,
                                    "insert_index": data_json["insert_index"]
                                }
                            else:
                                data_json = {
                                    "type": data_json["type"],
                                    "voice_path": voice_tmp_path,
                                    "content": data_json["content"],
                                    "random_speed": {
                                        "enable": False,
                                        "max": 1.3,
                                        "min": 0.8
                                    },
                                    "speed": 1
                                }
                            Audio.audio_player.play(data_json)
                        else:
                            logging.debug(f"voice_tmp_path={voice_tmp_path}")
                            # 使用pygame播放音频
                            Audio.mixer_normal.music.load(voice_tmp_path)
                            Audio.mixer_normal.music.play()
                            while Audio.mixer_normal.music.get_busy():
                                pygame.time.Clock().tick(10)
                            Audio.mixer_normal.music.stop()

                    # 是否启用字幕输出
                    #if captions_config["enable"]:
                        # 清空字幕文件
                        # self.common.write_content_to_file(captions_config["file_path"], "")

                    if Audio.copywriting_play_flag == 1:
                        # 延时执行恢复文案播放
                        self.delayed_execution_unpause_copywriting_play()
                except Exception as e:
                    logging.error(traceback.format_exc())
            Audio.mixer_normal.quit()
        except Exception as e:
            logging.error(traceback.format_exc())


    # 停止当前播放的音频
    def stop_current_audio(self):
        if self.config.get("play_audio", "player") == "audio_player":
            Audio.audio_player.skip_current_stream()
        else:
            Audio.mixer_normal.music.fadeout(1000)

    """
                                                     ./@\]                    
                   ,@@@@\*                             \@@^ ,]]]              
                      [[[*                      /@@]@@@@@/[[\@@@@/            
                        ]]@@@@@@\              /@@^  @@@^]]`[[                
                ]]@@@@@@@[[*                   ,[`  /@@\@@@@@@@@@@@@@@^       
             [[[[[`   @@@/                 \@@@@[[[\@@^ =@@/                  
              .\@@\* *@@@`                           [\@@@@@@\`               
                 ,@@\=@@@                         ,]@@@/`  ,\@@@@*            
                   ,@@@@`                     ,[[[[`  =@@@   ]]/O             
                   /@@@@@`                    ]]]@@@@@@@@@/[[[[[`             
                ,@@@@[ \@@@\`                      ./@@@@@@@]                 
          ,]/@@@@/`      \@@@@@\]]               ,@@@/,@@^ \@@@\]             
                           ,@@@@@@@@/[*       ,/@@/*  /@@^   [@@@@@@@\*       
                                                      ,@@^                    
                                                              
    """
    # 延时执行恢复文案播放
    def delayed_execution_unpause_copywriting_play(self):
        # 如果已经有计时器在运行，则取消之前的计时器
        if Audio.unpause_copywriting_play_timer is not None and Audio.unpause_copywriting_play_timer.is_alive():
            Audio.unpause_copywriting_play_timer.cancel()

        # 创建新的计时器并启动
        Audio.unpause_copywriting_play_timer = threading.Timer(float(self.config.get("copywriting", "switching_interval")), 
                                                               self.unpause_copywriting_play)
        Audio.unpause_copywriting_play_timer.start()


    # 只进行文案播放 正经版
    def start_only_play_copywriting(self):
        logging.info(f"文案播放线程运行中...")
        asyncio.run(self.only_play_copywriting())


    # 只进行文案播放   
    async def only_play_copywriting(self):
        
        try:
            Audio.mixer_copywriting.init()

            async def random_speed_and_play(audio_path):
                """对音频进行变速和播放，内置延时，其实就是提取了公共部分

                Args:
                    audio_path (str): 音频路径
                """
                # 音频变速
                random_speed = 1
                if self.config.get("audio_random_speed", "copywriting", "enable"):
                    random_speed = self.common.get_random_value(self.config.get("audio_random_speed", "copywriting", "speed_min"),
                                                                self.config.get("audio_random_speed", "copywriting", "speed_max"))
                    audio_path = self.audio_speed_change(audio_path, random_speed)

                logging.info(f"变速后音频输出在 {audio_path}")

                # 根据接入的虚拟身体类型执行不同逻辑
                if self.config.get("visual_body") == "xuniren":
                    await self.xuniren_api(audio_path)
                else:
                    if self.config.get("play_audio", "player") in ["audio_player", "audio_player_v2"]:
                            data_json = {
                                "type": "copywriting",
                                "voice_path": audio_path,
                                "content": audio_path,
                                "random_speed": {
                                    "enable": False,
                                    "max": 1.3,
                                    "min": 0.8
                                },
                                "speed": 1
                            }
                            Audio.audio_player.play(data_json)
                    else:
                        # 使用pygame播放音频
                        Audio.mixer_copywriting.music.load(audio_path)
                        Audio.mixer_copywriting.music.play()
                        while Audio.mixer_copywriting.music.get_busy():
                            pygame.time.Clock().tick(10)
                        Audio.mixer_copywriting.music.stop()

                # 添加延时，暂停执行n秒钟
                await asyncio.sleep(float(self.config.get("copywriting", "audio_interval")))


            def reload_tmp_play_list(index, play_list_arr):
                """重载播放列表

                Args:
                    index (int): 文案索引
                """
                # 获取文案配置
                copywriting_configs = self.config.get("copywriting", "config")
                tmp_play_list = copy.copy(copywriting_configs[index]["play_list"])
                play_list_arr[index] = tmp_play_list

                # 是否开启随机列表播放
                if self.config.get("copywriting", "random_play"):
                    for play_list in play_list_arr:
                        # 随机打乱列表内容
                        random.shuffle(play_list)


            try:
                # 获取文案配置
                copywriting_configs = self.config.get("copywriting", "config")

                # 获取自动播放配置
                if self.config.get("copywriting", "auto_play"):
                    self.unpause_copywriting_play()

                file_path_arr = []
                audio_path_arr = []
                play_list_arr = []
                continuous_play_num_arr = []
                max_play_time_arr = []
                # 记录最后一次播放的音频列表的索引值
                last_index = -1

                # 重载所有数据
                def all_data_reload(file_path_arr, audio_path_arr, play_list_arr, continuous_play_num_arr, max_play_time_arr):      
                    logging.info("重载所有文案数据")

                    file_path_arr = []
                    audio_path_arr = []
                    play_list_arr = []
                    continuous_play_num_arr = []
                    max_play_time_arr = []
                    
                    # 遍历文案配置载入数组
                    for copywriting_config in copywriting_configs:
                        file_path_arr.append(copywriting_config["file_path"])
                        audio_path_arr.append(copywriting_config["audio_path"])
                        tmp_play_list = copy.copy(copywriting_config["play_list"])
                        play_list_arr.append(tmp_play_list)
                        continuous_play_num_arr.append(copywriting_config["continuous_play_num"])
                        max_play_time_arr.append(copywriting_config["max_play_time"])


                    # 是否开启随机列表播放
                    if self.config.get("copywriting", "random_play"):
                        for play_list in play_list_arr:
                            # 随机打乱列表内容
                            random.shuffle(play_list)

                    return file_path_arr, audio_path_arr, play_list_arr, continuous_play_num_arr, max_play_time_arr

                file_path_arr, audio_path_arr, play_list_arr, continuous_play_num_arr, max_play_time_arr = all_data_reload(file_path_arr, audio_path_arr, play_list_arr, continuous_play_num_arr, max_play_time_arr)

                while True:
                    # print(f"Audio.copywriting_play_flag={Audio.copywriting_play_flag}")

                    # 判断播放标志位
                    if Audio.copywriting_play_flag in [0, 1, -1]:
                        await asyncio.sleep(float(self.config.get("copywriting", "audio_interval")))  # 添加延迟减少循环频率
                        continue

                    # print(f"play_list_arr={play_list_arr}")

                    # 遍历 play_list_arr 中的每个 play_list
                    for index, play_list in enumerate(play_list_arr):
                        # print(f"play_list_arr={play_list_arr}")

                        # 判断播放标志位 防止播放过程中无法暂停
                        if Audio.copywriting_play_flag in [0, 1, -1]:
                            # print(f"Audio.copywriting_play_flag={Audio.copywriting_play_flag}")
                            file_path_arr, audio_path_arr, play_list_arr, continuous_play_num_arr, max_play_time_arr = all_data_reload(file_path_arr, audio_path_arr, play_list_arr, continuous_play_num_arr, max_play_time_arr)

                            break

                        # 判断当前播放列表的索引值是否小于上一次的索引值，小的话就下一个，用于恢复到被打断前的播放位置
                        if index < last_index:
                            continue

                        start_time = float(self.common.get_bj_time(3))

                        # 根据连续播放的文案数量进行循环
                        for i in range(0, continuous_play_num_arr[index]):
                            # print(f"continuous_play_num_arr[index]={continuous_play_num_arr[index]}")
                            # 判断播放标志位 防止播放过程中无法暂停
                            if Audio.copywriting_play_flag in [0, 1, -1]:
                                file_path_arr, audio_path_arr, play_list_arr, continuous_play_num_arr, max_play_time_arr = all_data_reload(file_path_arr, audio_path_arr, play_list_arr, continuous_play_num_arr, max_play_time_arr)

                                break
                            
                            # 判断当前时间是否已经超过限定的播放时间，超时则退出循环
                            if (float(self.common.get_bj_time(3)) - start_time) > max_play_time_arr[index]:
                                break

                            # 判断当前 play_list 是否有音频数据
                            if len(play_list) > 0:
                                # 移出一个音频路径
                                voice_tmp_path = play_list.pop(0)
                                audio_path = os.path.join(audio_path_arr[index], voice_tmp_path)
                                audio_path = os.path.abspath(audio_path)
                                logging.info(f"即将播放音频 {audio_path}")

                                await random_speed_and_play(audio_path)
                            else:
                                # 重载播放列表
                                reload_tmp_play_list(index, play_list_arr)

                        # 放在这一级别，只有这一索引的播放列表的音频播放完后才会记录最后一次的播放索引位置
                        last_index = index if index < (len(play_list_arr) - 1) else -1
            except Exception as e:
                logging.error(traceback.format_exc())
            Audio.mixer_copywriting.quit()
        except Exception as e:
            logging.error(traceback.format_exc())


    # 暂停文案播放
    def pause_copywriting_play(self):
        logging.info("暂停文案播放")
        Audio.copywriting_play_flag = 0
        if self.config.get("play_audio", "player") == "audio_player":
            pass
            Audio.audio_player.pause_stream()
        # 由于v2的暂停不会更换音频，所以这个只暂停文案就没有意义了
        elif self.config.get("play_audio", "player") == "audio_player_v2":
            pass
            # Audio.audio_player.pause_stream()
        else:
            Audio.mixer_copywriting.music.pause()

    
    # 恢复暂停文案播放
    def unpause_copywriting_play(self):
        logging.info("恢复文案播放")
        Audio.copywriting_play_flag = 2
        # print(f"Audio.copywriting_play_flag={Audio.copywriting_play_flag}")
        if self.config.get("play_audio", "player") in ["audio_player", "audio_player_v2"]:
            pass
            Audio.audio_player.resume_stream()
        else:
            Audio.mixer_copywriting.music.unpause()

    
    # 停止文案播放
    def stop_copywriting_play(self):
        logging.info("停止文案播放")
        Audio.copywriting_play_flag = 0
        if self.config.get("play_audio", "player") == "audio_player":
            Audio.audio_player.pause_stream()
        # 由于v2的暂停不会更换音频，所以这个只暂停文案就没有意义了
        elif self.config.get("play_audio", "player") == "audio_player_v2":
            pass
            # Audio.audio_player.pause_stream()
        else:
            Audio.mixer_copywriting.music.stop()


    # 合并文案音频文件
    def merge_audio_files(self, directory, base_filename, last_index, pause_duration=1, format="wav"):
        merged_audio = None

        for i in range(1, last_index+1):
            filename = f"{base_filename}-{i}.{format}"  # 假设音频文件为 wav 格式
            filepath = os.path.join(directory, filename)

            if os.path.isfile(filepath):
                audio_segment = AudioSegment.from_file(filepath)
                
                if pause_duration > 0 and merged_audio is not None:
                    pause = AudioSegment.silent(duration=pause_duration * 1000)  # 将秒数转换为毫秒
                    merged_audio += pause
                
                if merged_audio is None:
                    merged_audio = audio_segment
                else:
                    merged_audio += audio_segment

                os.remove(filepath)  # 删除已合并的音频文件

        if merged_audio is not None:
            merged_filename = f"{base_filename}.wav"  # 合并后的文件名
            merged_filepath = os.path.join(directory, merged_filename)
            merged_audio.export(merged_filepath, format="wav")
            logging.info(f"音频文件合并成功：{merged_filepath}")
        else:
            logging.error("没有找到要合并的音频文件")


    # 只进行文案音频合成
    async def copywriting_synthesis_audio(self, file_path, out_audio_path="out/"):
        try:
            max_len = self.config.get("filter", "max_len")
            max_char_len = self.config.get("filter", "max_char_len")
            audio_synthesis_type = self.config.get("audio_synthesis_type")
            vits = self.config.get("vits")
            vits_fast = self.config.get("vits_fast")
            edge_tts_config = self.config.get("edge-tts")
            bark_gui = self.config.get("bark_gui")
            vall_e_x = self.config.get("vall_e_x")
            openai_tts = self.config.get("openai_tts")
            genshinvoice_top = self.config.get("genshinvoice_top")
            file_path = os.path.join(file_path)

            audio_out_path = self.config.get("play_audio", "out_path")

            if not os.path.isabs(audio_out_path):
                if audio_out_path.startswith('./'):
                    audio_out_path = audio_out_path[2:]

                audio_out_path = os.path.join(os.getcwd(), audio_out_path)
                # 确保路径最后有斜杠
                if not audio_out_path.endswith(os.path.sep):
                    audio_out_path += os.path.sep


            logging.info(f"即将合成的文案：{file_path}")
            
            # 从文件路径提取文件名
            file_name = self.common.extract_filename(file_path)
            # 获取文件内容
            content = self.common.read_file_return_content(file_path)

            logging.debug(f"合成音频前的原始数据：{content}")
            content = self.common.remove_extra_words(content, max_len, max_char_len)
            # logging.info("裁剪后的合成文本:" + text)

            content = content.replace('\n', '。')

            # 变声并移动音频文件 减少冗余
            async def voice_change_and_put_to_queue(voice_tmp_path):
                voice_tmp_path = await self.voice_change(voice_tmp_path)

                if voice_tmp_path:
                    # 移动音频到 临时音频路径 并重命名
                    out_file_path = audio_out_path # os.path.join(os.getcwd(), audio_out_path)
                    logging.info(f"移动临时音频到 {out_file_path}")
                    self.common.move_file(voice_tmp_path, out_file_path, file_name + "-" + str(file_index))
                
                return voice_tmp_path

            # 文件名自增值，在后期多合一的时候起到排序作用
            file_index = 0

            # 是否语句切分
            if self.config.get("play_audio", "text_split_enable"):
                sentences = self.common.split_sentences(content)
            else:
                sentences = [content]

            logging.info(f"sentences={sentences}")
            
            # 遍历逐一合成文案音频
            for content in sentences:
                # 使用正则表达式替换头部的标点符号
                # ^ 表示字符串开始，[^\w\s] 匹配任何非字母数字或空白字符
                content = re.sub(r'^[^\w\s]+', '', content)

                # 设置重试次数
                retry_count = 3  
                while retry_count > 0:
                    file_index = file_index + 1

                    try:
                        if audio_synthesis_type == "vits":
                            # 语言检测
                            language = self.common.lang_check(content)

                            # logging.info("language=" + language)

                            data = {
                                "type": vits["type"],
                                "api_ip_port": vits["api_ip_port"],
                                "id": vits["id"],
                                "format": vits["format"],
                                "lang": language,
                                "length": vits["length"],
                                "noise": vits["noise"],
                                "noisew": vits["noisew"],
                                "max": vits["max"],
                                "sdp_radio": vits["sdp_radio"],
                                "content": content
                            }

                            # 调用接口合成语音
                            voice_tmp_path = await self.my_tts.vits_api(data)
                                

                        elif audio_synthesis_type == "bert_vits2":
                            if self.config.get("bert_vits2", "type") == "hiyori":
                                if self.config.get("bert_vits2", "language") == "auto":
                                    # 自动检测语言
                                    language = self.common.lang_check(content)

                                    logging.debug(f'language={language}')

                                    # 自定义语言名称（需要匹配请求解析）
                                    language_name_dict = {"en": "EN", "zh": "ZH", "ja": "JP"}  

                                    if language in language_name_dict:
                                        language = language_name_dict[language]
                                    else:
                                        language = "ZH"  # 无法识别出语言代码时的默认值
                                else:
                                    language = self.config.get("bert_vits2", "language")
                                    
                                data = {
                                    "api_ip_port": self.config.get("bert_vits2", "api_ip_port"),
                                    "type": self.config.get("bert_vits2", "type"),
                                    "model_id": self.config.get("bert_vits2", "model_id"),
                                    "speaker_name": self.config.get("bert_vits2", "speaker_name"),
                                    "speaker_id": self.config.get("bert_vits2", "speaker_id"),
                                    "language": language,
                                    "length": self.config.get("bert_vits2", "length"),
                                    "noise": self.config.get("bert_vits2", "noise"),
                                    "noisew": self.config.get("bert_vits2", "noisew"),
                                    "sdp_radio": self.config.get("bert_vits2", "sdp_radio"),
                                    "auto_translate": self.config.get("bert_vits2", "auto_translate"),
                                    "auto_split": self.config.get("bert_vits2", "auto_split"),
                                    "emotion": self.config.get("bert_vits2", "emotion"),
                                    "style_text": self.config.get("bert_vits2", "style_text"),
                                    "style_weight": self.config.get("bert_vits2", "style_weight"),
                                    "content": content
                                }

                                logging.info(f"data={data}")

                                # 调用接口合成语音
                                voice_tmp_path = await self.my_tts.bert_vits2_api(data)
                        elif audio_synthesis_type == "vits_fast":
                            if vits_fast["language"] == "自动识别":
                                # 自动检测语言
                                language = self.common.lang_check(content)

                                logging.debug(f'language={language}')

                                # 自定义语言名称（需要匹配请求解析）
                                language_name_dict = {"en": "English", "zh": "简体中文", "ja": "日本語"}  

                                if language in language_name_dict:
                                    language = language_name_dict[language]
                                else:
                                    language = "简体中文"  # 无法识别出语言代码时的默认值
                            else:
                                language = vits_fast["language"]

                            # logging.info("language=" + language)

                            data = {
                                "api_ip_port": vits_fast["api_ip_port"],
                                "character": vits_fast["character"],
                                "speed": vits_fast["speed"],
                                "language": language,
                                "content": content
                            }

                            # 调用接口合成语音
                            voice_tmp_path = self.my_tts.vits_fast_api(data)
                        elif audio_synthesis_type == "edge-tts":
                            data = {
                                "content": content,
                                "voice": edge_tts_config["voice"],
                                "rate": edge_tts_config["rate"],
                                "volume": edge_tts_config["volume"]
                            }

                            # 调用接口合成语音
                            voice_tmp_path = await self.my_tts.edge_tts_api(data)

                        elif audio_synthesis_type == "elevenlabs":
                            return
                        
                            try:
                                # 如果配置了密钥就设置上0.0
                                if message["data"]["elevenlabs_api_key"] != "":
                                    set_api_key(message["data"]["elevenlabs_api_key"])

                                audio = generate(
                                    text=message["content"],
                                    voice=message["data"]["elevenlabs_voice"],
                                    model=message["data"]["elevenlabs_model"]
                                )

                                # play(audio)
                            except Exception as e:
                                logging.error(traceback.format_exc())
                                return
                        elif audio_synthesis_type == "bark_gui":
                            data = {
                                "api_ip_port": bark_gui["api_ip_port"],
                                "spk": bark_gui["spk"],
                                "generation_temperature": bark_gui["generation_temperature"],
                                "waveform_temperature": bark_gui["waveform_temperature"],
                                "end_of_sentence_probability": bark_gui["end_of_sentence_probability"],
                                "quick_generation": bark_gui["quick_generation"],
                                "seed": bark_gui["seed"],
                                "batch_count": bark_gui["batch_count"],
                                "content": content
                            }

                            # 调用接口合成语音
                            voice_tmp_path = self.my_tts.bark_gui_api(data)
                        elif audio_synthesis_type == "vall_e_x":
                            data = {
                                "api_ip_port": vall_e_x["api_ip_port"],
                                "language": vall_e_x["language"],
                                "accent": vall_e_x["accent"],
                                "voice_preset": vall_e_x["voice_preset"],
                                "voice_preset_file_path":vall_e_x["voice_preset_file_path"],
                                "content": content
                            }

                            # 调用接口合成语音
                            voice_tmp_path = self.my_tts.vall_e_x_api(data)
                        elif audio_synthesis_type == "genshinvoice_top":
                            # 调用接口合成语音
                            voice_tmp_path = await self.my_tts.genshinvoice_top_api(content)

                        elif audio_synthesis_type == "tts_ai_lab_top":
                            # 调用接口合成语音
                            voice_tmp_path = await self.my_tts.tts_ai_lab_top_api(content)

                        elif audio_synthesis_type == "openai_tts":
                            data = {
                                "type": openai_tts["type"],
                                "api_ip_port": openai_tts["api_ip_port"],
                                "model": openai_tts["model"],
                                "voice": openai_tts["voice"],
                                "api_key": openai_tts["api_key"],
                                "content": content
                            }

                            # 调用接口合成语音
                            voice_tmp_path = self.my_tts.openai_tts_api(data)
                            
                        elif audio_synthesis_type == "reecho_ai":
                            # 调用接口合成语音
                            voice_tmp_path = await self.my_tts.reecho_ai_api(data)
        
                        elif audio_synthesis_type == "gradio_tts":
                            data = {
                                "request_parameters": self.config.get("gradio_tts", "request_parameters"),
                                "content": content
                            }
                            # 调用接口合成语音
                            voice_tmp_path = self.my_tts.gradio_tts_api(data)
                        elif audio_synthesis_type == "gpt_sovits":
                            if self.config.get("gpt_sovits", "language") == "自动识别":
                                # 自动检测语言
                                language = self.common.lang_check(content)

                                logging.debug(f'language={language}')

                                # 自定义语言名称（需要匹配请求解析）
                                language_name_dict = {"en": "英文", "zh": "中文", "ja": "日文"}  

                                if language in language_name_dict:
                                    language = language_name_dict[language]
                                else:
                                    language = "中文"  # 无法识别出语言代码时的默认值
                            else:
                                language = self.config.get("gpt_sovits", "language")

                            data = {
                                "api_ip_port": self.config.get("gpt_sovits", "api_ip_port"),
                                "ref_audio_path": self.config.get("gpt_sovits", "ref_audio_path"),
                                "prompt_text": self.config.get("gpt_sovits", "prompt_text"),
                                "prompt_language": self.config.get("gpt_sovits", "prompt_language"),
                                "language": language,
                                "content": content
                            }
                                    
                            # 调用接口合成语音
                            voice_tmp_path = await self.my_tts.gpt_sovits_api(content)
                            
                        if voice_tmp_path is None:
                            raise Exception(f"{audio_synthesis_type}合成失败")
                        
                        logging.info(f"{audio_synthesis_type}合成成功，合成内容：【{content}】，输出到={voice_tmp_path}") 

                        # 变声并移动音频文件 减少冗余
                        tmp_path = await voice_change_and_put_to_queue(voice_tmp_path)
                        if tmp_path is None:
                            raise Exception(f"{audio_synthesis_type}合成失败")

                        break
                        # self.voice_tmp_path_queue.put(voice_tmp_path)
                    except Exception as e:
                        logging.error(f"尝试失败，剩余重试次数：{retry_count - 1}")
                        logging.error(traceback.format_exc())
                        retry_count -= 1  # 减少重试次数
                        if retry_count <= 0:
                            logging.error(f"重试次数用尽，{audio_synthesis_type}合成最终失败，请排查配置、网络等问题")
                            self.abnormal_alarm_handle("tts")
                            return

            # 进行音频合并 输出到文案音频路径
            out_file_path = os.path.join(os.getcwd(), audio_out_path)
            self.merge_audio_files(out_file_path, file_name, file_index)

            file_path = os.path.join(os.getcwd(), audio_out_path, file_name + ".wav")
            logging.info(f"合成完毕后的音频位于 {file_path}")
            # 移动音频到 指定的文案音频路径 out_audio_path
            out_file_path = os.path.join(os.getcwd(), out_audio_path)
            logging.info(f"移动音频到 {out_file_path}")
            self.common.move_file(file_path, out_file_path)
            file_path = os.path.join(out_audio_path, file_name + ".wav")

            return file_path
        except Exception as e:
            logging.error(traceback.format_exc())
            return None
        

    """
    其他
    """
    
    """
    异常报警
    """
    def abnormal_alarm_handle(self, type):
        """异常报警

        Args:
            type (str): 报警类型

        Returns:
            bool: True/False
        """

        try:
            Audio.abnormal_alarm_data[type]["error_count"] += 1

            if not self.config.get("abnormal_alarm", type, "enable"):
                return True
            
            if self.config.get("abnormal_alarm", type, "type") == "local_audio":
                # 是否错误数大于 自动重启错误数
                if Audio.abnormal_alarm_data[type]["error_count"] >= self.config.get("abnormal_alarm", type, "auto_restart_error_num"):
                    logging.warning(f"【异常报警-{type}】 出错数超过自动重启错误数，即将自动重启")
                    data = {
                        "type": "restart",
                        "api_type": "api",
                        "data": {
                            "config_path": "config.json"
                        }
                    }

                    self.common.send_request(f'http://{self.config.get("webui", "ip")}:{self.config.get("webui", "port")}/sys_cmd', "POST", data)
                    
                # 是否错误数小于 开始报警错误数，是则不触发报警
                if Audio.abnormal_alarm_data[type]["error_count"] < self.config.get("abnormal_alarm", type, "start_alarm_error_num"):
                    return
                
                path_list = self.common.get_all_file_paths(self.config.get("abnormal_alarm", type, "local_audio_path"))

                # 随机选择列表中的一个元素
                audio_path = random.choice(path_list)

                data_json = {
                    "type": "abnormal_alarm",
                    "tts_type": self.config.get("audio_synthesis_type"),
                    "data": self.config.get(self.config.get("audio_synthesis_type")),
                    "config": self.config.get("filter"),
                    "user_name": "系统",
                    "content": os.path.join(self.config.get("abnormal_alarm", type, "local_audio_path"), self.common.extract_filename(audio_path, True))
                }

                logging.warning(f"【异常报警-{type}】 {self.common.extract_filename(audio_path, False)}")

                self.audio_synthesis(data_json)

        except Exception as e:
            logging.error(traceback.format_exc())

            return False

        return True
