import os, sys, threading, json, random
import difflib
import logging
from datetime import datetime
import traceback
import importlib
import pyautogui
import copy
import re

from .config import Config
from .common import Common
from .audio import Audio
from .gpt_model.gpt import GPT_MODEL
from .logger import Configure_logger
from .db import SQLiteDB
from .my_translate import My_Translate


"""
	___ _                       
	|_ _| | ____ _ _ __ ___  ___ 
	 | || |/ / _` | '__/ _ \/ __|
	 | ||   < (_| | | | (_) \__ \
	|___|_|\_\__,_|_|  \___/|___/

"""
class SingletonMeta(type):
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
            return cls._instances[cls]


class My_handle(metaclass=SingletonMeta):
    common = None
    config = None
    audio = None
    my_translate = None

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

    # 答谢板块文案数据临时存储
    thanks_entrance_copy = []
    thanks_gift_copy = []
    thanks_follow_copy = []

    def __init__(self, config_path):
        logging.info("初始化My_handle...")

        try:
            if My_handle.common is None:
                My_handle.common = Common()
            if My_handle.config is None:
                My_handle.config = Config(config_path)
            if My_handle.audio is None:
                My_handle.audio = Audio(config_path)
            if My_handle.my_translate is None:
                My_handle.my_translate = My_Translate(config_path)


            # 日志文件路径
            file_path = "./log/log-" + My_handle.common.get_bj_time(1) + ".txt"
            Configure_logger(file_path)

            self.proxy = None
            # self.proxy = {
            #     "http": "http://127.0.0.1:10809",
            #     "https": "http://127.0.0.1:10809"
            # }
            
            # 数据丢弃部分相关的实现
            self.data_lock = threading.Lock()
            self.timers = {}

            self.db = None

            # 设置会话初始值
            self.session_config = None
            self.sessions = {}
            self.current_key_index = 0

            # 点歌模块
            self.choose_song_song_lists = None

            """
            新增LLM后，这边先定义下各个变量，下面会用到
            """
            self.chatgpt = None
            self.claude = None
            self.claude2 = None
            self.chatglm = None
            self.alice = None
            self.chat_with_file = None
            self.text_generation_webui = None
            self.sparkdesk = None
            self.langchain_chatglm = None
            self.langchain_chatchat = None
            self.zhipu = None
            self.bard_api = None
            self.yiyan = None
            self.tongyi = None
            self.tongyixingchen = None
            self.my_qianfan = None
            self.my_wenxinworkshop = None
            self.gemini = None

            # 配置加载
            self.config_load()

            logging.info(f"配置数据加载成功。")
        except Exception as e:
            logging.error(traceback.format_exc())     


    def get_chat_model(self, chat_type, config):
        if chat_type == "claude":
            self.claude = GPT_MODEL.get(chat_type)
            if not self.claude.reset_claude():
                logging.error("重置Claude会话失败喵~")
        elif chat_type == "claude2":
            GPT_MODEL.set_model_config(chat_type, config.get(chat_type))
            self.claude2 = GPT_MODEL.get(chat_type)
            if self.claude2.get_organization_id() is None:
                logging.error("重置Claude2会话失败喵~")
        else:
            if chat_type in ["chatterbot", "chat_with_file"]:
                # 对这些类型做特殊处理
                pass
            else:
                GPT_MODEL.set_model_config(chat_type, config.get(chat_type))
            self.__dict__[chat_type] = GPT_MODEL.get(chat_type)


    def handle_chat_type(self):
        chat_type = My_handle.config.get("chat_type")
        self.get_chat_model(chat_type, My_handle.config)

        if chat_type == "chatterbot":
            from chatterbot import ChatBot
            self.chatterbot_config = My_handle.config.get("chatterbot")
            try:
                self.bot = ChatBot(
                    self.chatterbot_config["name"],
                    database_uri='sqlite:///' + self.chatterbot_config["db_path"]
                )
            except Exception as e:
                logging.info(e)
                exit(0)
        elif chat_type == "chat_with_file":
            from utils.chat_with_file.chat_with_file import Chat_with_file
            self.chat_with_file = Chat_with_file(My_handle.config.get("chat_with_file"))
        elif chat_type == "game":
            self.game = importlib.import_module("game." + My_handle.config.get("game", "module_name"))

    # 配置加载
    def config_load(self):
        self.session_config = {'msg': [{"role": "system", "content": My_handle.config.get('chatgpt', 'preset')}]}

        # 设置GPT_Model全局模型列表
        GPT_MODEL.set_model_config("openai", My_handle.config.get("openai"))
        GPT_MODEL.set_model_config("chatgpt", My_handle.config.get("chatgpt"))
        GPT_MODEL.set_model_config("claude", My_handle.config.get("claude"))  

        # 聊天相关类实例化
        self.handle_chat_type()

        # 判断是否使能了SD
        if My_handle.config.get("sd")["enable"]:
            from utils.sd import SD

            self.sd = SD(My_handle.config.get("sd"))

        # 日志文件路径
        self.log_file_path = "./log/log-" + My_handle.common.get_bj_time(1) + ".txt"
        if os.path.isfile(self.log_file_path):
            logging.info(f'{self.log_file_path} 日志文件已存在，跳过')
        else:
            with open(self.log_file_path, 'w') as f:
                f.write('')
                logging.info(f'{self.log_file_path} 日志文件已创建')

        # 生成弹幕文件
        self.comment_file_path = "./log/comment-" + My_handle.common.get_bj_time(1) + ".txt"
        if os.path.isfile(self.comment_file_path):
            logging.info(f'{self.comment_file_path} 弹幕文件已存在，跳过')
        else:
            with open(self.comment_file_path, 'w') as f:
                f.write('')
                logging.info(f'{self.comment_file_path} 弹幕文件已创建')

        """                                                                                                                
                                                                                                                                        
            .............  '>)xcn)I                                                                                 
            }}}}}}}}}}}}](v0kaaakad\..                                                                              
            ++++++~~++<_xpahhhZ0phah>                                                                               
            _________+(OhhkamuCbkkkh+                                                                               
            ?????????nbhkhkn|makkkhQ^                                                                               
            [[[[[[[}UhkbhZ]fbhkkkhb<                                                                                
            1{1{1{1ChkkaXicohkkkhk]                                                                                 
            ))))))JhkkhrICakkkkap-                                                                                  
            \\\\|ckkkat;0akkkka0>                                                                                   
            ttt/fpkka/;Oakhhaku"                                                                                    
            jjjjUmkau^QabwQX\< '!<++~>iI       .;>++++<>I'     :+}}{?;                                              
            xxxcpdkO"capmmZ/^ +Y-;,,;-Lf     ItX/+l:",;>1cx>  .`"x#d>`        .`.                                   
            uuvqwkh+1ahaaL_  'Zq;     ;~   '/bQ!         "uhc: . 1oZ'         "vj.     ^'                           
            ccc0kaz!kawX}'   .\hbv?:      .jop;           .C*L^  )oO`        .':I^. ."_L!^^.    ':;,'               
            XXXXph_cU_"        >rZhbC\!   "qaC...          faa~  )oO`        ;-jqj .l[mb1]_'  ^(|}\Ow{              
            XXXz00i+             '!1Ukkc, 'JoZ` .          uop;  )oO'          >ou   .Lp"  . ,0j^^>Yvi              
            XXXzLn. .        ^>      lC#(  lLot.          _kq- . 1o0'          >on   .Qp,    }*|><i^  .             
            YYYXQ|           ,O]^.   "XQI . `10c~^.    '!t0f:   .t*q;....'l1. ._#c.. .Qkl`I_"Iw0~"`,<|i.            
            (|((f1           ^t1]++-}(?`      '>}}}/rrx1]~^    ^?jvv/]--]{r) .i{x/+;  ]Xr1_;. :(vnrj\i.             
                '1..             .''.   .         .Itq*Z}`             ..                                           
                 +; .                                "}XmQf-i!;.                                                    
                  .                                     ';><iI"                                                     
                                                                                                                                        
                                                                                                                                                                                                                                                     
        """
        try:
            # 数据库
            self.db = SQLiteDB(My_handle.config.get("database", "path"))
            logging.info(f'创建数据库:{My_handle.config.get("database", "path")}')

            # 创建弹幕表
            create_table_sql = '''
            CREATE TABLE IF NOT EXISTS danmu (
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                ts DATETIME NOT NULL
            )
            '''
            self.db.execute(create_table_sql)
            logging.debug('创建danmu（弹幕）表')

            create_table_sql = '''
            CREATE TABLE IF NOT EXISTS entrance (
                username TEXT NOT NULL,
                ts DATETIME NOT NULL
            )
            '''
            self.db.execute(create_table_sql)
            logging.debug('创建entrance（入场）表')

            create_table_sql = '''
            CREATE TABLE IF NOT EXISTS gift (
                username TEXT NOT NULL,
                gift_name TEXT NOT NULL,
                gift_num INT NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL,
                ts DATETIME NOT NULL
            )
            '''
            self.db.execute(create_table_sql)
            logging.debug('创建gift（礼物）表')

            create_table_sql = '''
            CREATE TABLE IF NOT EXISTS integral (
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                uid TEXT NOT NULL,
                integral INT NOT NULL,
                view_num INT NOT NULL,
                sign_num INT NOT NULL,
                last_sign_ts DATETIME NOT NULL,
                total_price INT NOT NULL,
                last_ts DATETIME NOT NULL
            )
            '''
            self.db.execute(create_table_sql)
            logging.debug('创建integral（积分）表')
        except Exception as e:
            logging.error(traceback.format_exc())


    # 重载config
    def reload_config(self, config_path):
        My_handle.config = Config(config_path)
        My_handle.audio.reload_config(config_path)
        My_handle.my_translate.reload_config(config_path)

        self.config_load()


    def get_room_id(self):
        return My_handle.config.get("room_display_id")


    # 音频合成处理
    def audio_synthesis_handle(self, data_json):
        """音频合成处理

        Args:
            data_json (dict): 传递的json数据

            核心参数:
            type目前有
                comment 弹幕
                local_qa_audio 本地问答音频
                song 歌曲
                reread 复读
                direct_reply 直接回复
                read_comment 念弹幕
                gift 礼物
                entrance 用户入场
                follow 用户关注
                idle_time_task 闲时任务
                abnormal_alarm 异常报警

        """
        # 如果虚拟身体-Unity，则发送数据到中转站
        if My_handle.config.get("visual_body") == "unity":
            # 判断 'config' 是否存在于字典中
            if 'config' in data_json:
                # 删除 'config' 对应的键值对
                data_json.pop('config')

            data_json["password"] = My_handle.config.get("unity", "password")

            resp_json = My_handle.common.send_request(My_handle.config.get("unity", "api_ip_port"), "POST", data_json)
            if resp_json:
                if resp_json["code"] == 200:
                    logging.info("请求unity中转站成功")
                else:
                    logging.info(f"请求unity中转站出错，{resp_json['message']}")
            else:
                logging.error("请求unity中转站失败")
        else:
            # 音频合成（edge-tts / vits_fast）并播放
            My_handle.audio.audio_synthesis(data_json)

            logging.debug(f'data_json={data_json}')

            # 数据类型不在需要触发助播条件的范围内，则直接返回
            if data_json["type"] not in My_handle.config.get("assistant_anchor", "type"):
                return

            # 1、匹配本地问答库 触发后不执行后面的其他功能
            if My_handle.config.get("assistant_anchor", "local_qa", "text", "enable") == True:
                # 根据类型，执行不同的问答匹配算法
                if My_handle.config.get("assistant_anchor", "local_qa", "text", "format") == "text":
                    tmp = self.find_answer(data_json["content"], My_handle.config.get("assistant_anchor", "local_qa", "text", "file_path"), My_handle.config.get("assistant_anchor", "local_qa", "text", "similarity"))
                else:
                    tmp = self.find_similar_answer(data_json["content"], My_handle.config.get("assistant_anchor", "local_qa", "text", "file_path"), My_handle.config.get("assistant_anchor", "local_qa", "text", "similarity"))

                if tmp != None:
                    logging.info(f'触发本地问答库-文本 [{My_handle.config.get("assistant_anchor", "username")}]: {data_json["content"]}')
                    # 将问答库中设定的参数替换为指定内容，开发者可以自定义替换内容
                    if "{cur_time}" in tmp:
                        tmp = tmp.format(cur_time=My_handle.common.get_bj_time(5))
                    if "{username}" in tmp:
                        tmp = tmp.format(username=My_handle.config.get("assistant_anchor", "username"))
                    else:
                        tmp = tmp
                    
                    logging.info(f"助播 本地问答库-文本回答为: {tmp}")

                    resp_content = tmp
                    # 将 AI 回复记录到日志文件中
                    with open(self.comment_file_path, "r+", encoding="utf-8") as f:
                        tmp_content = f.read()
                        # 将指针移到文件头部位置（此目的是为了让直播中读取日志文件时，可以一直让最新内容显示在顶部）
                        f.seek(0, 0)
                        # 不过这个实现方式，感觉有点低效
                        # 设置单行最大字符数，主要目的用于接入直播弹幕显示时，弹幕过长导致的显示溢出问题
                        max_length = 20
                        resp_content_substrings = [resp_content[i:i + max_length] for i in
                                                range(0, len(resp_content), max_length)]
                        resp_content_joined = '\n'.join(resp_content_substrings)

                        # 根据 弹幕日志类型进行各类日志写入
                        if My_handle.config.get("comment_log_type") == "问答":
                            f.write(f'[{My_handle.config.get("assistant_anchor", "username")} 提问]:{data_json["content"]}\n[AI回复{My_handle.config.get("assistant_anchor", "username")}]:{resp_content_joined}\n' + tmp_content)
                        elif My_handle.config.get("comment_log_type") == "问题":
                            f.write(f'[{My_handle.config.get("assistant_anchor", "username")} 提问]:{data_json["content"]}\n' + tmp_content)
                        elif My_handle.config.get("comment_log_type") == "回答":
                            f.write(f'[AI回复{My_handle.config.get("assistant_anchor", "username")}]:{resp_content_joined}\n' + tmp_content)

                    message = {
                        "type": "assistant_anchor_text",
                        "tts_type": My_handle.config.get("audio_synthesis_type"),
                        "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                        "config": My_handle.config.get("filter"),
                        "user_name": My_handle.config.get("assistant_anchor", "username"),
                        "content": resp_content
                    }

                    if "insert_index" in message:
                        message["insert_index"] = data_json["insert_index"]

                    
                    My_handle.audio.audio_synthesis(message)

                    return True
                
            # 如果开启了助播功能，则根据当前播放内容的文本信息，进行助播音频的播放
            if My_handle.config.get("assistant_anchor", "enable") == True:
                # 2、匹配本地问答音频库 触发后不执行后面的其他功能
                if My_handle.config.get("assistant_anchor", "local_qa", "audio", "enable") == True:
                    # 输出当前用户发送的弹幕消息
                    # logging.info(f"[{user_name}]: {content}")
                    # 获取本地问答音频库文件夹内所有的音频文件名
                    local_qa_audio_filename_list = My_handle.audio.get_dir_audios_filename(My_handle.config.get("assistant_anchor", "local_qa", "audio", "file_path"), type=1)
                    local_qa_audio_list = My_handle.audio.get_dir_audios_filename(My_handle.config.get("assistant_anchor", "local_qa", "audio", "file_path"), type=0)

                    if My_handle.config.get("assistant_anchor", "local_qa", "audio", "type") == "相似度匹配":
                        # 不含拓展名，在本地音频名列表中做查找
                        local_qv_audio_filename = My_handle.common.find_best_match(data_json["content"], local_qa_audio_filename_list, My_handle.config.get("assistant_anchor", "local_qa", "audio", "similarity"))
                    elif My_handle.config.get("assistant_anchor", "local_qa", "audio", "type") == "包含关系":
                        # 在本地音频名列表中查找是否包含于当前这个传入的文本内容
                        local_qv_audio_filename = My_handle.common.find_substring_in_list(data_json["content"], local_qa_audio_filename_list)

                    # print(f"local_qv_audio_filename={local_qv_audio_filename}")

                    # 找到了匹配的结果
                    if local_qv_audio_filename is not None:
                        logging.info(f'触发 助播 本地问答库-语音 [{My_handle.config.get("assistant_anchor", "username")}]: {data_json["content"]}')
                        # 把结果从原文件名列表中在查找一遍，补上拓展名。相似度设置为0，就能必定有返回的结果
                        local_qv_audio_filename = My_handle.common.find_best_match(local_qv_audio_filename, local_qa_audio_list, 0)

                        # 寻找对应的文件
                        resp_content = My_handle.audio.search_files(My_handle.config.get("assistant_anchor", "local_qa", "audio", "file_path"), local_qv_audio_filename)
                        if resp_content != []:
                            logging.debug(f"匹配到的音频原相对路径：{resp_content[0]}")

                            # 拼接音频文件路径
                            resp_content = f'{My_handle.config.get("assistant_anchor", "local_qa", "audio", "file_path")}/{resp_content[0]}'
                            logging.info(f"匹配到的音频路径：{resp_content}")
                            message = {
                                "type": "assistant_anchor_audio",
                                "tts_type": My_handle.config.get("audio_synthesis_type"),
                                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                                "config": My_handle.config.get("filter"),
                                "user_name": My_handle.config.get("assistant_anchor", "username"),
                                "content": data_json["content"],
                                "file_path": resp_content
                            }

                            if "insert_index" in message:
                                message["insert_index"] = data_json["insert_index"]

                            My_handle.audio.audio_synthesis(message)

                            return True


    # 从本地问答库中搜索问题的答案(文本数据是一问一答的单行格式)
    def find_answer(self, question, qa_file_path, similarity=1):
        """从本地问答库中搜索问题的答案(文本数据是一问一答的单行格式)

        Args:
            question (str): 问题文本
            qa_file_path (str): 问答库的路径
            similarity (float): 相似度

        Returns:
            str: 答案文本 或 None
        """

        with open(qa_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        q_list = [lines[i].strip() for i in range(0, len(lines), 2)]
        q_to_answer_index = {q: i + 1 for i, q in enumerate(q_list)}

        q = My_handle.common.find_best_match(question, q_list, similarity)
        # print(f"q={q}")

        if q is not None:
            answer_index = q_to_answer_index.get(q)
            # print(f"answer_index={answer_index}")
            if answer_index is not None and answer_index < len(lines):
                return lines[answer_index * 2 - 1].strip()

        return None


    # 本地问答库 文本模式  根据相似度查找答案(文本数据是json格式)
    def find_similar_answer(self, input_str, qa_file_path, min_similarity=0.8):
        """本地问答库 文本模式  根据相似度查找答案(文本数据是json格式)

        Args:
            input_str (str): 输入的待查找字符串
            qa_file_path (str): 问答库的路径
            min_similarity (float, optional): 最低匹配相似度. 默认 0.8.

        Returns:
            response (str): 匹配到的结果，如果匹配不到则返回None
        """
        def load_data_from_file(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    return data
            except (FileNotFoundError, json.JSONDecodeError):
                return None
            
        # 从文件加载数据
        data = load_data_from_file(qa_file_path)
        if data is None:
            return None

        # 存储相似度与回答的元组列表
        similarity_responses = []
        
        # 遍历json中的每个条目，找到与输入字符串相似的关键词
        for entry in data:
            for keyword in entry.get("关键词", []):
                similarity = difflib.SequenceMatcher(None, input_str, keyword).ratio()
                similarity_responses.append((similarity, entry.get("回答", [])))
        
        # 过滤相似度低于设定阈值的回答
        similarity_responses = [(similarity, response) for similarity, response in similarity_responses if similarity >= min_similarity]
        
        # 如果没有符合条件的回答，返回None
        if not similarity_responses:
            return None
        
        # 按相似度降序排序
        similarity_responses.sort(reverse=True, key=lambda x: x[0])
        
        # 获取相似度最高的回答列表
        top_response = similarity_responses[0][1]
        
        # 随机选择一个回答
        response = random.choice(top_response)
        
        return response


    # 本地问答库 处理
    def local_qa_handle(self, data):
        """本地问答库 处理

        Args:
            data (dict): 用户名 弹幕数据

        Returns:
            bool: 是否触发并处理
        """
        user_name = data["username"]
        content = data["content"]

        # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
        user_name = My_handle.common.merge_consecutive_asterisks(user_name)

        # 最大保留的用户名长度
        user_name = user_name[:self.config.get("local_qa", "text", "username_max_len")]

        # 1、匹配本地问答库 触发后不执行后面的其他功能
        if My_handle.config.get("local_qa", "text", "enable") == True:
            # 根据类型，执行不同的问答匹配算法
            if My_handle.config.get("local_qa", "text", "type") == "text":
                tmp = self.find_answer(content, My_handle.config.get("local_qa", "text", "file_path"), My_handle.config.get("local_qa", "text", "similarity"))
            else:
                tmp = self.find_similar_answer(content, My_handle.config.get("local_qa", "text", "file_path"), My_handle.config.get("local_qa", "text", "similarity"))

            if tmp != None:
                logging.info(f"触发本地问答库-文本 [{user_name}]: {content}")
                # 将问答库中设定的参数替换为指定内容，开发者可以自定义替换内容
                if "{cur_time}" in tmp:
                    tmp = tmp.format(cur_time=My_handle.common.get_bj_time(5))
                if "{username}" in tmp:
                    tmp = tmp.format(username=user_name)
                else:
                    tmp = tmp
                
                logging.info(f"本地问答库-文本回答为: {tmp}")

                resp_content = tmp
                # 将 AI 回复记录到日志文件中
                with open(self.comment_file_path, "r+", encoding="utf-8") as f:
                    tmp_content = f.read()
                    # 将指针移到文件头部位置（此目的是为了让直播中读取日志文件时，可以一直让最新内容显示在顶部）
                    f.seek(0, 0)
                    # 不过这个实现方式，感觉有点低效
                    # 设置单行最大字符数，主要目的用于接入直播弹幕显示时，弹幕过长导致的显示溢出问题
                    max_length = 20
                    resp_content_substrings = [resp_content[i:i + max_length] for i in
                                               range(0, len(resp_content), max_length)]
                    resp_content_joined = '\n'.join(resp_content_substrings)

                    # 根据 弹幕日志类型进行各类日志写入
                    if My_handle.config.get("comment_log_type") == "问答":
                        f.write(f"[{user_name} 提问]:{content}\n[AI回复{user_name}]:{resp_content_joined}\n" + tmp_content)
                    elif My_handle.config.get("comment_log_type") == "问题":
                        f.write(f"[{user_name} 提问]:{content}\n" + tmp_content)
                    elif My_handle.config.get("comment_log_type") == "回答":
                        f.write(f"[AI回复{user_name}]:{resp_content_joined}\n" + tmp_content)

                message = {
                    "type": "comment",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "user_name": user_name,
                    "content": resp_content
                }

                
                self.audio_synthesis_handle(message)

                return True

        # 2、匹配本地问答音频库 触发后不执行后面的其他功能
        if My_handle.config.get("local_qa")["audio"]["enable"] == True:
            # 输出当前用户发送的弹幕消息
            # logging.info(f"[{user_name}]: {content}")
            # 获取本地问答音频库文件夹内所有的音频文件名
            local_qa_audio_filename_list = My_handle.audio.get_dir_audios_filename(My_handle.config.get("local_qa", "audio", "file_path"), type=1)
            local_qa_audio_list = My_handle.audio.get_dir_audios_filename(My_handle.config.get("local_qa", "audio", "file_path"), type=0)

            # 不含拓展名做查找
            local_qv_audio_filename = My_handle.common.find_best_match(content, local_qa_audio_filename_list, My_handle.config.get("local_qa", "audio", "similarity"))
            
            # print(f"local_qv_audio_filename={local_qv_audio_filename}")

            # 找到了匹配的结果
            if local_qv_audio_filename is not None:
                logging.info(f"触发本地问答库-语音 [{user_name}]: {content}")
                # 把结果从原文件名列表中在查找一遍，补上拓展名
                local_qv_audio_filename = My_handle.common.find_best_match(local_qv_audio_filename, local_qa_audio_list, 0)

                # 寻找对应的文件
                resp_content = My_handle.audio.search_files(My_handle.config.get("local_qa", "audio", "file_path"), local_qv_audio_filename)
                if resp_content != []:
                    logging.debug(f"匹配到的音频原相对路径：{resp_content[0]}")

                    # 拼接音频文件路径
                    resp_content = f'{My_handle.config.get("local_qa", "audio", "file_path")}/{resp_content[0]}'
                    logging.info(f"匹配到的音频路径：{resp_content}")
                    message = {
                        "type": "local_qa_audio",
                        "tts_type": My_handle.config.get("audio_synthesis_type"),
                        "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                        "config": My_handle.config.get("filter"),
                        "user_name": user_name,
                        "content": content,
                        "file_path": resp_content
                    }

                    
                    self.audio_synthesis_handle(message)

                    return True
            
        return False


    # 点歌模式 处理
    def choose_song_handle(self, data):
        """点歌模式 处理

        Args:
            data (dict): 用户名 弹幕数据

        Returns:
            bool: 是否触发并处理
        """
        user_name = data["username"]
        content = data["content"]

        # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
        user_name = My_handle.common.merge_consecutive_asterisks(user_name)

        if My_handle.config.get("choose_song")["enable"] == True:
            start_cmd = My_handle.common.starts_with_any(content, My_handle.config.get("choose_song", "start_cmd"))
            stop_cmd = My_handle.common.starts_with_any(content, My_handle.config.get("choose_song", "stop_cmd"))
            random_cmd = My_handle.common.starts_with_any(content, My_handle.config.get("choose_song", "random_cmd"))

            
            # 判断随机点歌命令是否正确
            if random_cmd:
                resp_content = My_handle.common.random_search_a_audio_file(My_handle.config.get("choose_song", "song_path"))
                if resp_content is None:
                    return True
                
                logging.info(f"随机到的音频路径：{resp_content}")

                message = {
                    "type": "song",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "user_name": user_name,
                    "content": resp_content
                }

                
                self.audio_synthesis_handle(message)

                return True
            # 判断点歌命令是否正确
            elif start_cmd:
                logging.info(f"[{user_name}]: {content}")

                # 获取本地音频文件夹内所有的音频文件名（不含拓展名）
                choose_song_song_lists = My_handle.audio.get_dir_audios_filename(My_handle.config.get("choose_song", "song_path"), 1)

                # 去除命令前缀
                content = content[len(start_cmd):]
                # 判断是否有此歌曲
                song_filename = My_handle.common.find_best_match(content, choose_song_song_lists, similarity=My_handle.config.get("choose_song", "similarity"))
                if song_filename is None:
                    # resp_content = f"抱歉，我还没学会唱{content}"
                    # 根据配置的 匹配失败回复文案来进行合成
                    resp_content = My_handle.config.get("choose_song", "match_fail_copy").format(content=content)
                    logging.info(f"[AI回复{user_name}]：{resp_content}")

                    message = {
                        "type": "comment",
                        "tts_type": My_handle.config.get("audio_synthesis_type"),
                        "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                        "config": My_handle.config.get("filter"),
                        "user_name": user_name,
                        "content": resp_content
                    }

                    
                    self.audio_synthesis_handle(message)

                    return True
                
                resp_content = My_handle.audio.search_files(My_handle.config.get('choose_song', 'song_path'), song_filename, True)
                if resp_content == []:
                    return True
                
                logging.debug(f"匹配到的音频原相对路径：{resp_content[0]}")

                # 拼接音频文件路径
                resp_content = f"{My_handle.config.get('choose_song', 'song_path')}/{resp_content[0]}"
                resp_content = os.path.abspath(resp_content)
                logging.info(f"匹配到的音频路径：{resp_content}")
                
                message = {
                    "type": "song",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "user_name": user_name,
                    "content": resp_content
                }

                
                self.audio_synthesis_handle(message)

                return True
            # 判断取消点歌命令是否正确
            elif stop_cmd:
                My_handle.audio.stop_current_audio()

                return True
            

        return False


    """
    
         ]@@@@@               =@@       @@^              =@@@@@@].  .@@` ./@@@ ,@@@^                /@^                     
        @@^      @@*          =@@       @@^              =@@   ,@@\      =@@   @@^                                          
        \@@].  =@@@@@.=@@@@@` =@@@@@@@. @@^ ./@@@@\.     =@@    .@@^.@@.@@@@@@@@@@@.@@   @@^ /@@@@^ @@^ ./@@@@@]  @@/@@@@.  
          ,\@@\  @@*   .]]/@@ =@@.  =@\ @@^ @@\]]/@^     =@@     @@^.@@. =@@   @@^ .@@   @@^ @@\`   @@^ @@^   \@^ @@`  \@^  
             @@^ @@* ,@@` =@@ =@@   =@/ @@^ @@`          =@@   ./@/ .@@. =@@   @@^ .@@.  @@^   ,\@@ @@^ @@^   /@^ @@*  =@^  
       .@@@@@@/  \@@@.@@@@@@@ =@@@@@@/  @@^ .\@@@@@.     =@@@@@@/`  .@@. =@@   @@^  =@@@@@@^.@@@@@^ @@^ .\@@@@@`  @@*  =@^ 
    
    """

    # 画图模式 SD 处理
    def sd_handle(self, data):
        """画图模式 SD 处理

        Args:
            data (dict): 用户名 弹幕数据

        Returns:
            bool: 是否触发并处理
        """
        user_name = data["username"]
        content = data["content"]

        # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
        user_name = My_handle.common.merge_consecutive_asterisks(user_name)

        if content.startswith(My_handle.config.get("sd", "trigger")):
            # 违禁检测
            content = self.prohibitions_handle(content)
            if content is None:
                return
        
            if My_handle.config.get("sd", "enable") == False:
                logging.info("您还未启用SD模式，无法使用画画功能")
                return True
            else:
                # 输出当前用户发送的弹幕消息
                logging.info(f"[{user_name}]: {content}")

                # 删除文本中的命令前缀
                content = content[len(My_handle.config.get("sd", "trigger")):]

                # 判断翻译类型 进行翻译工作
                tmp = My_handle.my_translate.trans(content, My_handle.config.get("sd", "translate_type"))
                if tmp:
                    content = tmp

                """
                根据聊天类型执行不同逻辑
                """ 
                chat_type = My_handle.config.get("sd", "prompt_llm", "type")
                # 新增LLM需要在这里追加
                if chat_type in ["chatgpt", "claude", "claude2", "chatglm", "chat_with_file", "text_generation_webui", \
                    "sparkdesk", "langchain_chatglm", "langchain_chatchat", "zhipu", "bard", "yiyan", "tongyi", \
                    "tongyixingchen", "my_qianfan", "my_wenxinworkshop", "gemini"]:
                    content = My_handle.config.get("sd", "prompt_llm", "before_prompt") + \
                        content + My_handle.config.get("after_prompt")
                    
                    data_json = {
                        "user_name": user_name,
                        "content": content
                    }
                    resp_content = self.llm_handle(chat_type, data_json)
                    if resp_content is not None:
                        logging.info(f"[AI回复{user_name}]：{resp_content}")
                    else:
                        resp_content = ""
                        logging.warning(f"警告：{chat_type}无返回")
                elif chat_type == "none" or chat_type == "reread" or chat_type == "game":
                    resp_content = content
                else:
                    resp_content = content

                logging.info(f"传给SD接口的内容：{resp_content}")

                self.sd.process_input(resp_content)
                return True
            
        return False


    # 弹幕格式检查和特殊字符替换
    def comment_check_and_replace(self, content):
        """弹幕格式检查和特殊字符替换

        Args:
            content (str): 待处理的弹幕内容

        Returns:
            str: 处理完毕后的弹幕内容/None
        """
        # 判断弹幕是否以xx起始，如果是则返回None
        if My_handle.config.get("filter", "before_filter_str") and any(
                content.startswith(prefix) for prefix in My_handle.config.get("filter", "before_filter_str")):
            return None

        # 判断弹幕是否以xx结尾，如果是则返回None
        if My_handle.config.get("filter", "after_filter_str") and any(
                content.endswith(prefix) for prefix in My_handle.config.get("filter", "after_filter_str")):
            return None

        # 判断弹幕是否以xx起始，如果不是则返回None
        if My_handle.config.get("filter", "before_must_str") and not any(
                content.startswith(prefix) for prefix in My_handle.config.get("filter", "before_must_str")):
            return None
        else:
            for prefix in My_handle.config.get("filter", "before_must_str"):
                if content.startswith(prefix):
                    content = content[len(prefix):]  # 删除匹配的开头
                    break

        # 判断弹幕是否以xx结尾，如果不是则返回None
        if My_handle.config.get("filter", "after_must_str") and not any(
                content.endswith(prefix) for prefix in My_handle.config.get("filter", "after_must_str")):
            return None
        else:
            for prefix in My_handle.config.get("filter", "after_must_str"):
                if content.endswith(prefix):
                    content = content[:-len(prefix)]  # 删除匹配的结尾
                    break

        # 全为标点符号
        if My_handle.common.is_punctuation_string(content):
            return None

        # 换行转为,
        content = content.replace('\n', ',')

        # 表情弹幕过滤
        if My_handle.config.get("filter", "emoji"):
            # 如b站的表情弹幕就是[表情名]的这种格式，采用正则表达式进行过滤
            content = re.sub(r'\[.*?\]', '', content)
            logging.info(f"表情弹幕过滤后：{content}")

        # 语言检测
        if My_handle.common.lang_check(content, My_handle.config.get("need_lang")) is None:
            logging.warning("语言检测不通过，已过滤")
            return None

        return content


    # 违禁处理
    def prohibitions_handle(self, content):
        """违禁处理

        Args:
            content (str): 带判断的字符串内容

        Returns:
            str: 是：None 否返回：content
        """
        # 含有链接
        if My_handle.common.is_url_check(content):
            logging.warning(f"链接：{content}")
            return None
        
        # 违禁词检测
        if My_handle.config.get("filter", "badwords", "enable"):
            if My_handle.common.profanity_content(content):
                logging.warning(f"违禁词：{content}")
                return None
            
            bad_word = My_handle.common.check_sensitive_words2(My_handle.config.get("filter", "badwords", "path"), content)
            if bad_word is not None:
                logging.warning(f"命中本地违禁词：{bad_word}")

                # 是否丢弃
                if My_handle.config.get("filter", "badwords", "discard"):
                    return None
                
                # 进行违禁词替换
                content = content.replace(bad_word, My_handle.config.get("filter", "badwords", "replace"))

                logging.info(f"违禁词替换后：{content}")

                # 回调，多次进行违禁词过滤替换
                return self.prohibitions_handle(content)


            # 同拼音违禁词过滤
            if My_handle.config.get("filter", "badwords", "bad_pinyin_path") != "":
                if My_handle.common.check_sensitive_words3(My_handle.config.get("filter", "badwords", "bad_pinyin_path"), content):
                    logging.warning(f"同音违禁词：{content}")
                    return None

        return content


    # 直接复读
    def reread_handle(self, data):
        """复读处理

        Args:
            data (dict): 包含用户名,弹幕内容

        Returns:
            _type_: 寂寞
        """

        username = data["username"]
        content = data["content"]

        logging.info(f"复读内容：{content}")
        
        # 音频合成时需要用到的重要数据
        message = {
            "type": "reread",
            "tts_type": My_handle.config.get("audio_synthesis_type"),
            "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
            "config": My_handle.config.get("filter"),
            "user_name": username,
            "content": content
        }

        # 音频插入的索引（适用于audio_player_v2）
        if "insert_index" in data:
            message["insert_index"] = data["insert_index"]

        logging.debug(message)

        self.audio_synthesis_handle(message)

    # 调教
    def tuning_handle(self, data_json):
        """调教LLM处理

        Args:
            data_json (dict): 包含用户名,弹幕内容

        Returns:
            _type_: 寂寞
        """
        logging.info(f"调教命令：{data_json['content']}")

        """
        根据聊天类型执行不同逻辑
        """ 
        chat_type = My_handle.config.get("chat_type")
        # 新增LLM需要在这里追加
        if chat_type in ["chatgpt", "claude", "claude2", "chatglm", "alice", "chat_with_file", "text_generation_webui", \
            "sparkdesk", "langchain_chatglm", "langchain_chatchat", "zhipu", "bard", "yiyan", "tongyi", \
            "tongyixingchen", "my_qianfan", "my_wenxinworkshop", "gemini"]:
            resp_content = self.llm_handle(chat_type, data_json)
            if resp_content is not None:
                logging.info(f"[AI回复{My_handle.config.get('talk', 'username')}]：{resp_content}")
            else:
                logging.warning(f"警告：{chat_type}无返回")


    """

                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@@@@@@^         /@@@@@@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@@@@@@@        ,@@@@@@@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@@@@@@@^       /@@@@@@@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@@@@@@@@.     ,@@@@@@@@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@@@@@@@@^     /@@@@@@@@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@=@@@@@@@.   ,@@@@@@@^@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@.@@@@@@@^   @@@@@@@@.@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@ =@@@@@@@. =@@@@@@@^.@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@ .@@@@@@@^ @@@@@@@@ .@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@  =@@@@@@@=@@@@@@@^ .@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@  .@@@@@@@@@@@@@@@  .@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@   =@@@@@@@@@@@@@^  .@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@   .@@@@@@@@@@@@/   .@@@@@@@@@              
                 .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@    =@@@@@@@@@@@`   .@@@@@@@@@              
                 .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@    .@@@@@@@@@@/    .@@@@@@@@@              
                 .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@     =@@@@@@@@@`    .@@@@@@@@@              
                 .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@     .@@@@@@@@/     .@@@@@@@@@  

    """


    # LLM处理
    def llm_handle(self, chat_type, data):
        """LLM统一处理

        Args:
            chat_type (str): 聊天类型
            data (str): dict，含用户名和内容

        Returns:
            str: LLM返回的结果
        """
        # 使用 getattr 来动态获取属性
        if getattr(self, chat_type, None) is None:
            self.get_chat_model(chat_type, My_handle.config)
            # setattr(self, chat_type, GPT_MODEL.get(chat_type))
            
        resp_content = None
        # print(f'''data: {data}''')

        # 新增LLM需要在这里追加
        chat_model_methods = {
            "chatgpt": lambda: self.chatgpt.get_gpt_resp(data["user_name"], data["content"]),
            "claude": lambda: self.claude.get_resp(data["content"]),
            "claude2": lambda: self.claude2.get_resp(data["content"]),
            "chatterbot": lambda: self.bot.get_response(data["content"]).text,
            "chatglm": lambda: self.chatglm.get_resp(data["content"]),
            "alice": lambda: self.alice.get_resp(data["user_name"], data["content"]),
            "chat_with_file": lambda: self.chat_with_file.get_model_resp(data["content"]),
            "text_generation_webui": lambda: self.text_generation_webui.get_resp(data["content"]),
            "sparkdesk": lambda: self.sparkdesk.get_resp(data["content"]),
            "langchain_chatglm": lambda: self.langchain_chatglm.get_resp(data["content"]),
            "langchain_chatchat": lambda: self.langchain_chatchat.get_resp(data["content"]),
            "zhipu": lambda: self.zhipu.get_resp(data["content"]),
            "bard": lambda: self.bard_api.get_resp(data["content"]),
            "yiyan": lambda: self.yiyan.get_resp(data["content"]),
            "tongyi": lambda: self.tongyi.get_resp(data["content"]),
            "tongyixingchen": lambda: self.tongyixingchen.get_resp(data["content"]),
            "my_qianfan": lambda: self.my_qianfan.get_resp(data["content"]),
            "my_wenxinworkshop": lambda: self.my_wenxinworkshop.get_resp(data["content"]),
            "gemini": lambda: self.gemini.get_resp(data["content"]),
            "reread": lambda: data["content"]
        }

        # 使用字典映射的方式来获取响应内容
        resp_content = chat_model_methods.get(chat_type, lambda: data["content"])()

        logging.debug(f"resp_content={resp_content}")

        # 返回为空，触发异常报警
        if resp_content is None:
            self.abnormal_alarm_handle("llm")

        return resp_content


    # 积分处理
    def integral_handle(self, type, data):
        """积分处理

        Args:
            type (str): 消息数据类型（comment/gift/entrance）
            data (dict): 平台侧传入的data数据，直接拿来做解析

        Returns:
            bool: 是否正常触发了积分事件，是True 否False
        """
        user_name = data["username"]
        
        if My_handle.config.get("integral", "enable"):
            # 根据消息类型进行对应处理
            if "comment" == type:
                content = data["content"]

                # 是否开启了签到功能
                if My_handle.config.get("integral", "sign", "enable"):
                    # 判断弹幕内容是否是命令
                    if content in My_handle.config.get("integral", "sign", "cmd"):
                        # 查询数据库中是否有当前用户的积分记录（缺个UID）
                        common_sql = '''
                        SELECT * FROM integral WHERE username =?
                        '''
                        integral_data = self.db.fetch_all(common_sql, (user_name,))

                        logging.debug(f"integral_data={integral_data}")

                        # 获取文案并合成语音，传入签到天数自动检索
                        def get_copywriting_and_audio_synthesis(sign_num):
                            # 判断当前签到天数在哪个签到数区间内，根据不同的区间提供不同的文案回复
                            for integral_sign_copywriting in My_handle.config.get("integral", "sign", "copywriting"):
                                # 在此区间范围内，所以你的配置一定要对，不然这里就崩溃了！！！
                                if int(integral_sign_copywriting["sign_num_interval"].split("-")[0]) <= \
                                    sign_num <= \
                                    int(integral_sign_copywriting["sign_num_interval"].split("-")[1]):
                                    # 匹配文案
                                    resp_content = random.choice(integral_sign_copywriting["copywriting"])
                                    
                                    logging.debug(f"resp_content={resp_content}")

                                    data_json = {
                                        "user_name": data["username"],
                                        "get_integral": int(My_handle.config.get("integral", "sign", "get_integral")),
                                        "sign_num": sign_num + 1
                                    } 

                                    resp_content = self.common.dynamic_variable_replacement(resp_content, data_json)
                                    
                                    # 生成回复内容
                                    message = {
                                        "type": "direct_reply",
                                        "tts_type": My_handle.config.get("audio_synthesis_type"),
                                        "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                                        "config": My_handle.config.get("filter"),
                                        "user_name": user_name,
                                        "content": resp_content
                                    }

                                    
                                    self.audio_synthesis_handle(message)

                        if integral_data == []:
                            # 积分表中没有该用户，插入数据
                            insert_data_sql = '''
                            INSERT INTO integral (platform, username, uid, integral, view_num, sign_num, last_sign_ts, total_price, last_ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            '''
                            self.db.execute(insert_data_sql, (
                                data["platform"], 
                                user_name, 
                                user_name, 
                                My_handle.config.get("integral", "sign", "get_integral"), 
                                1,
                                1,
                                datetime.now(),
                                0,
                                datetime.now())
                            )

                            logging.info(f"integral积分表 新增 用户：{user_name}")

                            get_copywriting_and_audio_synthesis(0)

                            return True
                        else:
                            integral_data = integral_data[0]
                            # 积分表中有该用户，更新数据

                            # 先判断last_sign_ts是否是今天，如果是，则说明已经打卡过了，不能重复打卡
                            # 获取日期时间字符串字段，此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                            date_string = integral_data[6]

                            # 获取日期部分（前10个字符），并与当前日期字符串比较
                            if date_string[:10] == datetime.now().date().strftime("%Y-%m-%d"):
                                message = {
                                    "type": "direct_reply",
                                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                                    "config": My_handle.config.get("filter"),
                                    "user_name": user_name,
                                    "content": f"{user_name}您今天已经签到过了，不能重复打卡哦~"
                                }

                                
                                self.audio_synthesis_handle(message)

                                return True

                            # 更新下用户数据
                            update_data_sql = '''
                            UPDATE integral SET integral=?, view_num=?, sign_num=?, last_sign_ts=?, last_ts=? WHERE username =?
                            '''
                            self.db.execute(update_data_sql, (
                                # 此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                                integral_data[3] + My_handle.config.get("integral", "sign", "get_integral"), 
                                integral_data[4] + 1,
                                integral_data[5] + 1,
                                datetime.now(),
                                datetime.now(),
                                user_name
                                )
                            )

                            logging.info(f"integral积分表 更新 用户：{user_name}")

                            get_copywriting_and_audio_synthesis(integral_data[5] + 1)

                            return True
            elif "gift" == type:
                # 是否开启了礼物功能
                if My_handle.config.get("integral", "gift", "enable"):
                    # 查询数据库中是否有当前用户的积分记录（缺个UID）
                    common_sql = '''
                    SELECT * FROM integral WHERE username =?
                    '''
                    integral_data = self.db.fetch_all(common_sql, (user_name,))

                    logging.debug(f"integral_data={integral_data}")

                    get_integral = int(float(My_handle.config.get("integral", "gift", "get_integral_proportion")) * data["total_price"])

                    # 获取文案并合成语音，传入总礼物金额自动检索
                    def get_copywriting_and_audio_synthesis(total_price):
                        # 判断当前礼物金额在哪个礼物金额区间内，根据不同的区间提供不同的文案回复
                        for integral_gift_copywriting in My_handle.config.get("integral", "gift", "copywriting"):
                            # 在此区间范围内，所以你的配置一定要对，不然这里就崩溃了！！！
                            if float(integral_gift_copywriting["gift_price_interval"].split("-")[0]) <= \
                                total_price <= \
                                float(integral_gift_copywriting["gift_price_interval"].split("-")[1]):
                                # 匹配文案
                                resp_content = random.choice(integral_gift_copywriting["copywriting"])
                                
                                logging.debug(f"resp_content={resp_content}")

                                data_json = {
                                    "user_name": data["username"],
                                    "gift_name": data["gift_name"],
                                    "get_integral": get_integral
                                } 

                                resp_content = self.common.dynamic_variable_replacement(resp_content, data_json)
                                
                                # 生成回复内容
                                message = {
                                    "type": "direct_reply",
                                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                                    "config": My_handle.config.get("filter"),
                                    "user_name": user_name,
                                    "content": resp_content
                                }

                                self.audio_synthesis_handle(message)

                    # TODO：此处有计算bug！！！ 总礼物价值计算不对，后期待优化
                    if integral_data == []:
                        # 积分表中没有该用户，插入数据
                        insert_data_sql = '''
                        INSERT INTO integral (platform, username, uid, integral, view_num, sign_num, last_sign_ts, total_price, last_ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        '''
                        self.db.execute(insert_data_sql, (
                            data["platform"], 
                            user_name, 
                            user_name, 
                            get_integral, 
                            1,
                            1,
                            datetime.now(),
                            data["total_price"],
                            datetime.now())
                        )

                        logging.info(f"integral积分表 新增 用户：{user_name}")

                        get_copywriting_and_audio_synthesis(data["total_price"])

                        return True
                    else:
                        integral_data = integral_data[0]
                        # 积分表中有该用户，更新数据

                        # 更新下用户数据
                        update_data_sql = '''
                        UPDATE integral SET integral=?, total_price=?, last_ts=? WHERE username =?
                        '''
                        self.db.execute(update_data_sql, (
                            # 此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                            integral_data[3] + get_integral, 
                            integral_data[7] + data["total_price"],
                            datetime.now(),
                            user_name
                            )
                        )

                        logging.info(f"integral积分表 更新 用户：{user_name}")

                        get_copywriting_and_audio_synthesis(data["total_price"])

                        return True
            elif "entrance" == type:
                # 是否开启了入场功能
                if My_handle.config.get("integral", "entrance", "enable"):
                    # 查询数据库中是否有当前用户的积分记录（缺个UID）
                    common_sql = '''
                    SELECT * FROM integral WHERE username =?
                    '''
                    integral_data = self.db.fetch_all(common_sql, (user_name,))

                    logging.debug(f"integral_data={integral_data}")

                    # 获取文案并合成语音，传入观看天数自动检索
                    def get_copywriting_and_audio_synthesis(view_num):
                        # 判断当前签到天数在哪个签到数区间内，根据不同的区间提供不同的文案回复
                        for integral_entrance_copywriting in My_handle.config.get("integral", "entrance", "copywriting"):
                            # 在此区间范围内，所以你的配置一定要对，不然这里就崩溃了！！！
                            if int(integral_entrance_copywriting["entrance_num_interval"].split("-")[0]) <= \
                                view_num <= \
                                int(integral_entrance_copywriting["entrance_num_interval"].split("-")[1]):
                                # 匹配文案
                                resp_content = random.choice(integral_entrance_copywriting["copywriting"])
                                
                                logging.debug(f"resp_content={resp_content}")

                                data_json = {
                                    "user_name": data["username"],
                                    "get_integral": int(My_handle.config.get("integral", "entrance", "get_integral")),
                                    "entrance_num": view_num + 1
                                } 

                                resp_content = self.common.dynamic_variable_replacement(resp_content, data_json)
                                
                                # 生成回复内容
                                message = {
                                    "type": "direct_reply",
                                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                                    "config": My_handle.config.get("filter"),
                                    "user_name": user_name,
                                    "content": resp_content
                                }

                                
                                self.audio_synthesis_handle(message)

                    if integral_data == []:
                        # 积分表中没有该用户，插入数据
                        insert_data_sql = '''
                        INSERT INTO integral (platform, username, uid, integral, view_num, sign_num, last_sign_ts, total_price, last_ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        '''
                        self.db.execute(insert_data_sql, (
                            data["platform"], 
                            user_name, 
                            user_name, 
                            My_handle.config.get("integral", "entrance", "get_integral"), 
                            1,
                            0,
                            datetime.now(),
                            0,
                            datetime.now())
                        )

                        logging.info(f"integral积分表 新增 用户：{user_name}")

                        get_copywriting_and_audio_synthesis(1)

                        return True
                    else:
                        integral_data = integral_data[0]
                        # 积分表中有该用户，更新数据

                        # 先判断last_ts是否是今天，如果是，则说明已经观看过了，不能重复记录
                        # 获取日期时间字符串字段，此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                        date_string = integral_data[8]

                        # 获取日期部分（前10个字符），并与当前日期字符串比较
                        if date_string[:10] == datetime.now().date().strftime("%Y-%m-%d"):
                            return False

                        # 更新下用户数据
                        update_data_sql = '''
                        UPDATE integral SET integral=?, view_num=?, last_ts=? WHERE username =?
                        '''
                        self.db.execute(update_data_sql, (
                            # 此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                            integral_data[3] + My_handle.config.get("integral", "entrance", "get_integral"), 
                            integral_data[4] + 1,
                            datetime.now(),
                            user_name
                            )
                        )

                        logging.info(f"integral积分表 更新 用户：{user_name}")

                        get_copywriting_and_audio_synthesis(integral_data[4] + 1)

                        return True
            elif "crud" == type:
                content = data["content"]
                
                # 是否开启了查询功能
                if My_handle.config.get("integral", "crud", "query", "enable"):
                    # 判断弹幕内容是否是命令
                    if content in My_handle.config.get("integral", "crud", "query", "cmd"):
                        # 查询数据库中是否有当前用户的积分记录（缺个UID）
                        common_sql = '''
                        SELECT * FROM integral WHERE username =?
                        '''
                        integral_data = self.db.fetch_all(common_sql, (user_name,))

                        logging.debug(f"integral_data={integral_data}")

                        # 获取文案并合成语音，传入积分总数自动检索
                        def get_copywriting_and_audio_synthesis(total_integral):
                            # 匹配文案
                            resp_content = random.choice(My_handle.config.get("integral", "crud", "query", "copywriting"))
                            
                            logging.debug(f"resp_content={resp_content}")

                            data_json = {
                                "user_name": data["username"],
                                "integral": total_integral
                            }

                            resp_content = self.common.dynamic_variable_replacement(resp_content, data_json)

                            # 如果积分为0，则返回个没积分的回复。不过这个基本没可能，除非有bug
                            if total_integral == 0:
                                resp_content = data["username"] + "，查询到您无积分。"
                            
                            # 生成回复内容
                            message = {
                                "type": "direct_reply",
                                "tts_type": My_handle.config.get("audio_synthesis_type"),
                                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                                "config": My_handle.config.get("filter"),
                                "user_name": user_name,
                                "content": resp_content
                            }

                            
                            self.audio_synthesis_handle(message)

                        if integral_data == []:
                            logging.info(f"integral积分表 查询不到 用户：{user_name}")

                            get_copywriting_and_audio_synthesis(0)

                            return True
                        else:
                            integral_data = integral_data[0]
                            # 积分表中有该用户

                            # 获取日期时间字符串字段，此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                            date_string = integral_data[3]

                            logging.info(f"integral积分表 用户：{user_name}，总积分：{date_string}")

                            get_copywriting_and_audio_synthesis(int(date_string))

                            return True
        return False


    # 按键映射处理
    def key_mapping_handle(self, type, data):
        """按键映射处理

        Args:
            type (str): 数据来源类型（弹幕/回复）
            data (dict): 平台侧传入的data数据，直接拿来做解析

        Returns:
            bool: 是否正常触发了按键映射事件，是True 否False
        """
        flag = False

        # 官方文档：https://pyautogui.readthedocs.io/en/latest/keyboard.html#keyboard-keys
        if My_handle.config.get("key_mapping", "enable"):
            # 判断传入的数据是否包含gift_name键值，有的话则是礼物数据
            if "gift_name" in data:
                # 获取key_mapping 所有 config数据
                key_mapping_configs = My_handle.config.get("key_mapping", "config")

                # 遍历key_mapping_configs
                for key_mapping_config in key_mapping_configs:
                    # 遍历单个配置中所有礼物名
                    for gift in key_mapping_config["gift"]:
                        # 判断礼物名是否相同
                        if gift == data["gift_name"]:
                            # 触发对应按键按下释放
                            for key in key_mapping_config["keys"]:
                                pyautogui.keyDown(key)
                            for key in key_mapping_config["keys"]:
                                pyautogui.keyUp(key)

                            logging.info(f'【触发按键映射】礼物：{gift} 按键：{key_mapping_config["keys"]}')

                            flag = True
            else:
                content = data["content"]
                # 判断命令头是否匹配
                start_cmd = My_handle.config.get("key_mapping", "start_cmd")
                if start_cmd != "" and content.startswith(start_cmd):
                    # 删除命令头部
                    content = content[len(start_cmd):]

                key_mapping_configs = My_handle.config.get("key_mapping", "config")

                for key_mapping_config in key_mapping_configs:
                    similarity = float(key_mapping_config["similarity"])
                    for keyword in key_mapping_config["keywords"]:
                        if type == "弹幕":
                            # 判断相似度
                            ratio = difflib.SequenceMatcher(None, content, keyword).ratio()
                            if ratio >= similarity:
                                # 触发对应按键按下释放
                                for key in key_mapping_config["keys"]:
                                    pyautogui.keyDown(key)
                                for key in key_mapping_config["keys"]:
                                    pyautogui.keyUp(key)

                                logging.info(f'【触发按键映射】关键词：{keyword} 按键：{key_mapping_config["keys"]}')

                                flag = True
                        elif type == "回复":
                            logging.debug(f"keyword={keyword}, content={content}")
                            if keyword in content:
                                logging.info(f'【触发按键映射】关键词：{keyword} 按键：{key_mapping_config["keys"]}')

                                # 触发对应按键按下释放
                                for key in key_mapping_config["keys"]:
                                    pyautogui.keyDown(key)
                                for key in key_mapping_config["keys"]:
                                    pyautogui.keyUp(key)

                                flag = True
            
        return flag


    """                                                              
                                                                           
                                                         ,`                
                             @@@@`               =@@\`   /@@/              
                ,/@@] =@@@`  @@@/                 =@@\/@@@@@@@@@[          
           .\@@/[@@@@` ,@@@ =@/.             ,[[[[.=@^ ,@@@@\`             
                *@@^,`  .]]]@@@@@@\`          ,@@@@@@[[[. =@@@@.           
           .]]]]/@@`\@@/ *@@^  =@@@/           ,@@@@@@@@/`@@@`             
            =@@*    .@@@@@@@@/`@@@^             ,@@\]]/@@@@@.              
            =@@      =@@*.@@\]/@@^               ,\@@\   ,]]@@@@]          
          ,/@@@@@@@^  \@/[@@^               .@@@@@@@@@[[[\@\.              
          ,@/. .@@@      .@@\]/@@@@@@`          ,@@@,@@@.,]@@@`            
               .@@/@@@@@/[@@/                  /@@\]@@@@@@@@@@@@@]         
               =@@^      .@@^                ]@@@@@^ @@@  @@@ ,@@@@@@\].   
           ,]]/@@@`      .@@^             ./@/` .@@^.@@@/@@@/              
             \@@@`       .@@^                       .@@@ .[[               
                         .@@`                        @@^                   
                                                                                                                                          

    """

    # 弹幕处理
    def comment_handle(self, data):
        """弹幕处理

        Args:
            data (dict): 包含用户名,弹幕内容

        Returns:
            _type_: 寂寞
        """

        try:
            user_name = data["username"]
            content = data["content"]

            # 输出当前用户发送的弹幕消息
            logging.debug(f"[{user_name}]: {content}")

            # 记录数据库
            if My_handle.config.get("database", "comment_enable"):
                insert_data_sql = '''
                INSERT INTO danmu (username, content, ts) VALUES (?, ?, ?)
                '''
                self.db.execute(insert_data_sql, (user_name, content, datetime.now()))



            # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
            user_name = My_handle.common.merge_consecutive_asterisks(user_name)

            # 0、积分机制运转
            if self.integral_handle("comment", data):
                return
            if self.integral_handle("crud", data):
                return

            """
            用户名也得过滤一下，防止炸弹人
            """
            # 用户名以及弹幕违禁判断
            user_name = self.prohibitions_handle(user_name)
            if user_name is None:
                return
            
            content = self.prohibitions_handle(content)
            if content is None:
                return
            
            # 弹幕格式检查和特殊字符替换
            content = self.comment_check_and_replace(content)
            if content is None:
                return
            
            # 判断字符串是否全为标点符号，是的话就过滤
            if My_handle.common.is_punctuation_string(content):
                logging.debug(f"用户:{user_name}]，发送纯符号的弹幕，已过滤")
                return
            
            # 判断按键映射触发类型
            if My_handle.config.get("key_mapping", "type") == "弹幕" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                # 按键映射 触发后不执行后面的其他功能
                if self.key_mapping_handle("弹幕", data):
                    return
            
            try:
                # 念弹幕
                if My_handle.config.get("read_comment", "enable"):
                    logging.debug(f"念弹幕 content:{content}")

                    # 音频合成时需要用到的重要数据
                    message = {
                        "type": "read_comment",
                        "tts_type": My_handle.config.get("audio_synthesis_type"),
                        "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                        "config": My_handle.config.get("filter"),
                        "user_name": user_name,
                        "content": content
                    }

                    # 判断是否需要念用户名
                    if My_handle.config.get("read_comment", "read_username_enable"):
                        # 将用户名中特殊字符替换为空
                        message['user_name'] = self.common.replace_special_characters(message['user_name'], "！!@#￥$%^&*_-+/——=()（）【】}|{:;<>~`\\")
                        message['user_name'] = message['user_name'][:self.config.get("read_comment", "username_max_len")]
                        tmp_content = random.choice(self.config.get("read_comment", "read_username_copywriting"))
                        if "{username}" in tmp_content:
                            message['content'] = tmp_content.format(username=message['user_name']) + message['content']

                    
                    self.audio_synthesis_handle(message)
            except Exception as e:
                logging.error(traceback.format_exc())

            # 1、本地问答库 处理
            if self.local_qa_handle(data):
                return

            # 2、点歌模式 触发后不执行后面的其他功能
            if self.choose_song_handle(data):
                return

            # 3、画图模式 触发后不执行后面的其他功能
            if self.sd_handle(data):
                return
            
            # 弹幕内容是否进行翻译
            if My_handle.config.get("translate", "enable") and (My_handle.config.get("translate", "trans_type") == "弹幕" or \
                My_handle.config.get("translate", "trans_type") == "弹幕+回复"):
                tmp = My_handle.my_translate.trans(content)
                if tmp:
                    content = tmp
                    # logging.info(f"翻译后：{content}")

            data_json = {
                "user_name": user_name,
                "content": content
            }

            """
            根据聊天类型执行不同逻辑
            """ 
            chat_type = My_handle.config.get("chat_type")
            # 新增LLM需要在这里追加
            if chat_type in ["chatgpt", "claude", "claude2", "chatglm", "alice", "chat_with_file", "text_generation_webui", \
                "sparkdesk", "langchain_chatglm", "langchain_chatchat", "zhipu", "bard", "yiyan", "tongyi", \
                "tongyixingchen", "my_qianfan", "my_wenxinworkshop", "gemini"]:
                data_json["content"] = My_handle.config.get("before_prompt") + content + My_handle.config.get("after_prompt")
                resp_content = self.llm_handle(chat_type, data_json)
                if resp_content is not None:
                    logging.info(f"[AI回复{user_name}]：{resp_content}")
                else:
                    resp_content = ""
                    logging.warning(f"警告：{chat_type}无返回")
            elif chat_type == "game":
                if My_handle.config.get("game", "enable"):
                    self.game.parse_keys_and_simulate_keys_press(content.split(), 2)
                return
            elif chat_type == "none":
                return
            elif chat_type == "reread":
                resp_content = self.llm_handle(chat_type, data_json)
            else:
                resp_content = content

            # 空数据结束
            if resp_content == "" or resp_content is None:
                return

            """
            双重过滤，为您保驾护航
            """
            resp_content = resp_content.strip()

            resp_content = resp_content.replace('\n', '。')
            
            # LLM回复的内容进行违禁判断
            resp_content = self.prohibitions_handle(resp_content)
            if resp_content is None:
                return

            # logger.info("resp_content=" + resp_content)

            # 回复内容是否进行翻译
            if My_handle.config.get("translate", "enable") and (My_handle.config.get("translate", "trans_type") == "回复" or \
                My_handle.config.get("translate", "trans_type") == "弹幕+回复"):
                tmp = My_handle.my_translate.trans(resp_content)
                if tmp:
                    resp_content = tmp

            # 将 AI 回复记录到日志文件中
            with open(self.comment_file_path, "r+", encoding="utf-8") as f:
                tmp_content = f.read()
                # 将指针移到文件头部位置（此目的是为了让直播中读取日志文件时，可以一直让最新内容显示在顶部）
                f.seek(0, 0)
                # 不过这个实现方式，感觉有点低效
                # 设置单行最大字符数，主要目的用于接入直播弹幕显示时，弹幕过长导致的显示溢出问题
                max_length = 20
                resp_content_substrings = [resp_content[i:i + max_length] for i in range(0, len(resp_content), max_length)]
                resp_content_joined = '\n'.join(resp_content_substrings)

                # 根据 弹幕日志类型进行各类日志写入
                if My_handle.config.get("comment_log_type") == "问答":
                    f.write(f"[{user_name} 提问]:\n{content}\n[AI回复{user_name}]:{resp_content_joined}\n" + tmp_content)
                elif My_handle.config.get("comment_log_type") == "问题":
                    f.write(f"[{user_name} 提问]:\n{content}\n" + tmp_content)
                elif My_handle.config.get("comment_log_type") == "回答":
                    f.write(f"[AI回复{user_name}]:\n{resp_content_joined}\n" + tmp_content)

            # 判断按键映射触发类型
            if My_handle.config.get("key_mapping", "type") == "回复" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                # 替换内容
                data["content"] = resp_content
                # 按键映射 触发后不执行后面的其他功能
                if self.key_mapping_handle("回复", data):
                    pass

            # 音频合成时需要用到的重要数据
            message = {
                "type": "comment",
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "user_name": user_name,
                "content": resp_content
            }

            self.audio_synthesis_handle(message)
        except Exception as e:
            logging.error(traceback.format_exc())


    # 礼物处理
    def gift_handle(self, data):
        try:
            # 记录数据库
            if My_handle.config.get("database", "gift_enable"):
                insert_data_sql = '''
                INSERT INTO gift (username, gift_name, gift_num, unit_price, total_price, ts) VALUES (?, ?, ?, ?, ?, ?)
                '''
                self.db.execute(insert_data_sql, (
                    data['username'], 
                    data['gift_name'], 
                    data['num'], 
                    data['unit_price'], 
                    data['total_price'],
                    datetime.now())
                )

            # 按键映射 触发后仍然执行后面的其他功能
            self.key_mapping_handle("弹幕", data)
            
            # 违禁处理
            data['username'] = self.prohibitions_handle(data['username'])
            if data['username'] is None:
                return
            
            # 积分处理
            if self.integral_handle("gift", data):
                return

            # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
            data['username'] = My_handle.common.merge_consecutive_asterisks(data['username'])
            # 删除用户名中的特殊字符
            data['username'] = My_handle.common.replace_special_characters(data['username'], "！!@#￥$%^&*_-+/——=()（）【】}|{:;<>~`\\")  

            data['username'] = data['username'][:self.config.get("thanks", "username_max_len")]

            # logging.debug(f"[{data['username']}]: {data}")
        
            if False == My_handle.config.get("thanks")["gift_enable"]:
                return

            # 如果礼物总价低于设置的礼物感谢最低值
            if data["total_price"] < My_handle.config.get("thanks")["lowest_price"]:
                return

            if My_handle.config.get("thanks", "gift_random"):
                resp_content = random.choice(My_handle.config.get("thanks", "gift_copy")).format(username=data["username"], gift_name=data["gift_name"])
            else:
                # 类变量list中是否有数据，没有就拷贝下数据再顺序取出首个数据
                if len(My_handle.thanks_gift_copy) == 0:
                    My_handle.thanks_gift_copy = copy.copy(My_handle.config.get("thanks", "gift_copy"))
                resp_content = My_handle.thanks_gift_copy.pop(0).format(username=data["username"], gift_name=data["gift_name"])
            
            message = {
                "type": "gift",
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "user_name": data["username"],
                "content": resp_content,
                "gift_info": data
            }

            
            self.audio_synthesis_handle(message)
        except Exception as e:
            logging.error(traceback.format_exc())


    # 入场处理
    def entrance_handle(self, data):
        try:
            # 记录数据库
            if My_handle.config.get("database", "entrance_enable"):
                insert_data_sql = '''
                INSERT INTO entrance (username, ts) VALUES (?, ?)
                '''
                self.db.execute(insert_data_sql, (data['username'], datetime.now()))

            # 违禁处理
            data['username'] = self.prohibitions_handle(data['username'])
            if data['username'] is None:
                return
            
            if self.integral_handle("entrance", data):
                return

            # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
            data['username'] = My_handle.common.merge_consecutive_asterisks(data['username'])
            # 删除用户名中的特殊字符
            data['username'] = My_handle.common.replace_special_characters(data['username'], "！!@#￥$%^&*_-+/——=()（）【】}|{:;<>~`\\")

            data['username'] = data['username'][:self.config.get("thanks", "username_max_len")]

            # logging.debug(f"[{data['username']}]: {data['content']}")
        
            if False == My_handle.config.get("thanks")["entrance_enable"]:
                return

            if My_handle.config.get("thanks", "entrance_random"):
                resp_content = random.choice(My_handle.config.get("thanks", "entrance_copy")).format(username=data["username"])
            else:
                # 类变量list中是否有数据，没有就拷贝下数据再顺序取出首个数据
                if len(My_handle.thanks_entrance_copy) == 0:
                    My_handle.thanks_entrance_copy = copy.copy(My_handle.config.get("thanks", "entrance_copy"))
                resp_content = My_handle.thanks_entrance_copy.pop(0).format(username=data["username"])

            message = {
                "type": "entrance",
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "user_name": data['username'],
                "content": resp_content
            }

            
            self.audio_synthesis_handle(message)
        except Exception as e:
            logging.error(traceback.format_exc())


    # 关注处理
    def follow_handle(self, data):
        try:
            # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
            data['username'] = My_handle.common.merge_consecutive_asterisks(data['username'])
            # 删除用户名中的特殊字符
            data['username'] = My_handle.common.replace_special_characters(data['username'], "！!@#￥$%^&*_-+/——=()（）【】}|{:;<>~`\\")

            data['username'] = data['username'][:self.config.get("thanks", "username_max_len")]

            # 违禁处理
            data['username'] = self.prohibitions_handle(data['username'])
            if data['username'] is None:
                return

            # logging.debug(f"[{data['username']}]: {data['content']}")
        
            if False == My_handle.config.get("thanks")["follow_enable"]:
                return

            if My_handle.config.get("thanks", "follow_random"):
                resp_content = random.choice(My_handle.config.get("thanks", "follow_copy")).format(username=data["username"])
            else:
                # 类变量list中是否有数据，没有就拷贝下数据再顺序取出首个数据
                if len(My_handle.thanks_follow_copy) == 0:
                    My_handle.thanks_follow_copy = copy.copy(My_handle.config.get("thanks", "follow_copy"))
                resp_content = My_handle.thanks_follow_copy.pop(0).format(username=data["username"])
            

            message = {
                "type": "follow",
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "user_name": data['username'],
                "content": resp_content
            }

            
            self.audio_synthesis_handle(message)
        except Exception as e:
            logging.error(traceback.format_exc())

    # 定时处理
    def schedule_handle(self, data):
        try:
            content = data["content"]

            message = {
                "type": "entrance",
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "user_name": data['username'],
                "content": content
            }

            
            self.audio_synthesis_handle(message)
        except Exception as e:
            logging.error(traceback.format_exc())

    # 闲时任务处理
    def idle_time_task_handle(self, data):
        try:
            type = data["type"]
            content = data["content"]
            user_name = data["username"]

            if type == "comment":
                # 记录数据库
                if My_handle.config.get("database", "comment_enable"):
                    insert_data_sql = '''
                    INSERT INTO danmu (username, content, ts) VALUES (?, ?, ?)
                    '''
                    self.db.execute(insert_data_sql, (user_name, content, datetime.now()))

                # 输出当前用户发送的弹幕消息
                logging.info(f"[{user_name}]: {content}")

                # 弹幕格式检查和特殊字符替换
                content = self.comment_check_and_replace(content)
                if content is None:
                    return
                
                # 判断按键映射触发类型
                if My_handle.config.get("key_mapping", "type") == "弹幕" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                    # 按键映射 触发后不执行后面的其他功能
                    if self.key_mapping_handle("弹幕", data):
                        return
                
                # 1、本地问答库 处理
                if self.local_qa_handle(data):
                    return

                # 2、点歌模式 触发后不执行后面的其他功能
                if self.choose_song_handle(data):
                    return

                # 3、画图模式 触发后不执行后面的其他功能
                if self.sd_handle(data):
                    return

                """
                根据聊天类型执行不同逻辑
                """ 
                chat_type = My_handle.config.get("chat_type")
                if chat_type == "game":
                    if My_handle.config.get("game", "enable"):
                        self.game.parse_keys_and_simulate_keys_press(content.split(), 2)
                    return
                elif chat_type == "none":
                    return
                else:
                    # 通用的data_json构造
                    data_json = {
                        "user_name": user_name,
                        "content": My_handle.config.get("before_prompt") + content + My_handle.config.get("after_prompt") if chat_type != "reread" else content
                    }
                    
                    # 调用LLM统一接口，获取返回内容
                    resp_content = self.llm_handle(chat_type, data_json) if chat_type != "game" else ""

                    if resp_content:
                        logging.info(f"[AI回复{user_name}]：{resp_content}")
                    else:
                        logging.warning(f"警告：{chat_type}无返回")
                        resp_content = ""

                """
                双重过滤，为您保驾护航
                """
                resp_content = resp_content.replace('\n', '。')
                
                # LLM回复的内容进行违禁判断
                resp_content = self.prohibitions_handle(resp_content)
                if resp_content is None:
                    return

                # logger.info("resp_content=" + resp_content)

                # 将 AI 回复记录到日志文件中
                with open(self.comment_file_path, "r+", encoding="utf-8") as f:
                    tmp_content = f.read()
                    # 将指针移到文件头部位置（此目的是为了让直播中读取日志文件时，可以一直让最新内容显示在顶部）
                    f.seek(0, 0)
                    # 不过这个实现方式，感觉有点低效
                    # 设置单行最大字符数，主要目的用于接入直播弹幕显示时，弹幕过长导致的显示溢出问题
                    max_length = 20
                    resp_content_substrings = [resp_content[i:i + max_length] for i in range(0, len(resp_content), max_length)]
                    resp_content_joined = '\n'.join(resp_content_substrings)

                    # 根据 弹幕日志类型进行各类日志写入
                    if My_handle.config.get("comment_log_type") == "问答":
                        f.write(f"[{user_name} 提问]:\n{content}\n[AI回复{user_name}]:{resp_content_joined}\n" + tmp_content)
                    elif My_handle.config.get("comment_log_type") == "问题":
                        f.write(f"[{user_name} 提问]:\n{content}\n" + tmp_content)
                    elif My_handle.config.get("comment_log_type") == "回答":
                        f.write(f"[AI回复{user_name}]:\n{resp_content_joined}\n" + tmp_content)

                # 判断按键映射触发类型
                if My_handle.config.get("key_mapping", "type") == "回复" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                    # 替换内容
                    data["content"] = resp_content
                    # 按键映射 触发后不执行后面的其他功能
                    if self.key_mapping_handle("回复", data):
                        pass

                # 音频合成时需要用到的重要数据
                message = {
                    "type": "idle_time_task",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "user_name": user_name,
                    "content": resp_content,
                    "content_type": "comment"
                }

                
                self.audio_synthesis_handle(message)
            elif type == "local_audio":
                logging.info(f'[{user_name}]: {data["file_path"]}')

                message = {
                    "type": "idle_time_task",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "user_name": user_name,
                    "content": content,
                    "content_type": "local_audio",
                    "file_path": os.path.abspath(data["file_path"])
                }

                
                self.audio_synthesis_handle(message)
        except Exception as e:
            logging.error(traceback.format_exc())


    """
    数据丢弃部分
    增加新的处理事件时，需要进行这块部分的内容追加
    """
    def process_data(self, data, timer_flag):
        with self.data_lock:
            if timer_flag not in self.timers or not self.timers[timer_flag].is_alive():
                self.timers[timer_flag] = threading.Timer(self.get_interval(timer_flag), self.process_last_data, args=(timer_flag,))
                self.timers[timer_flag].start()

            # self.timers[timer_flag].last_data = data
            if hasattr(self.timers[timer_flag], 'last_data'):
                self.timers[timer_flag].last_data.append(data)
                # 这里需要注意配置命名!!!
                if len(self.timers[timer_flag].last_data) > int(My_handle.config.get("filter", timer_flag + "_forget_reserve_num")):
                    self.timers[timer_flag].last_data.pop(0)
            else:
                self.timers[timer_flag].last_data = [data]

    def process_last_data(self, timer_flag):
        with self.data_lock:
            timer = self.timers.get(timer_flag)
            if timer and timer.last_data is not None and timer.last_data != []:
                logging.debug(f"预处理定时器触发 type={timer_flag}，data={timer.last_data}")

                if timer_flag == "comment":
                    for data in timer.last_data:
                        self.comment_handle(data)
                elif timer_flag == "gift":
                    for data in timer.last_data:
                        self.gift_handle(data)
                    #self.gift_handle(timer.last_data)
                elif timer_flag == "entrance":
                    for data in timer.last_data:
                        self.entrance_handle(data)
                    #self.entrance_handle(timer.last_data)
                elif timer_flag == "follow":
                    for data in timer.last_data:
                        self.follow_handle(data)
                elif timer_flag == "talk":
                    # 聊天暂时共用弹幕处理逻辑
                    for data in timer.last_data:
                        self.comment_handle(data)
                    #self.comment_handle(timer.last_data)
                elif timer_flag == "schedule":
                    # 定时任务处理
                    for data in timer.last_data:
                        self.schedule_handle(data)
                    #self.schedule_handle(timer.last_data)
                elif timer_flag == "idle_time_task":
                    # 定时任务处理
                    for data in timer.last_data:
                        self.idle_time_task_handle(data)
                    #self.idle_time_task_handle(timer.last_data)

                # 清空数据
                timer.last_data = []

    def get_interval(self, timer_flag):
        # 根据标志定义不同计时器的间隔
        intervals = {
            "comment": My_handle.config.get("filter", "comment_forget_duration"),
            "gift": My_handle.config.get("filter", "gift_forget_duration"),
            "entrance": My_handle.config.get("filter", "entrance_forget_duration"),
            "follow": My_handle.config.get("filter", "follow_forget_duration"),
            "talk": My_handle.config.get("filter", "talk_forget_duration"),
            "schedule": My_handle.config.get("filter", "schedule_forget_duration"),
            "idle_time_task": My_handle.config.get("filter", "idle_time_task_forget_duration")
            # 根据需要添加更多计时器及其间隔，记得添加config.json中的配置项
        }

        # 默认间隔为0.1秒
        return intervals.get(timer_flag, 0.1)


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
            My_handle.abnormal_alarm_data[type]["error_count"] += 1

            if not My_handle.config.get("abnormal_alarm", type, "enable"):
                return True
            
            if My_handle.config.get("abnormal_alarm", type, "type") == "local_audio":
                # 是否错误数大于 自动重启错误数
                if My_handle.abnormal_alarm_data[type]["error_count"] >= My_handle.config.get("abnormal_alarm", type, "auto_restart_error_num"):
                    data = {
                        "type": "restart",
                        "api_type": "api",
                        "data": {
                            "config_path": "config.json"
                        }
                    }

                    My_handle.common.send_request(f'http://{My_handle.config.get("webui", "ip")}:{My_handle.config.get("webui", "port")}/sys_cmd', "POST", data)

                # 是否错误数小于 开始报警错误数，是则不触发报警
                if My_handle.abnormal_alarm_data[type]["error_count"] < My_handle.config.get("abnormal_alarm", type, "start_alarm_error_num"):
                    return

                path_list = My_handle.common.get_all_file_paths(My_handle.config.get("abnormal_alarm", type, "local_audio_path"))

                # 随机选择列表中的一个元素
                audio_path = random.choice(path_list)

                message = {
                    "type": "abnormal_alarm",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "user_name": "系统",
                    "content": os.path.join(My_handle.config.get("abnormal_alarm", type, "local_audio_path"), My_handle.common.extract_filename(audio_path, True))
                }

                logging.warning(f"【异常报警-{type}】 {My_handle.common.extract_filename(audio_path, False)}")

                self.audio_synthesis_handle(message)

        except Exception as e:
            logging.error(traceback.format_exc())

            return False

        return True

