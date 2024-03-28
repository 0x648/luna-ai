import json, logging, os
import aiohttp, requests, ssl
from urllib.parse import urlencode
from gradio_client import Client
import traceback
import edge_tts
from urllib.parse import urljoin
import random

from utils.common import Common
from utils.logger import Configure_logger
from utils.config import Config

class MY_TTS:
    def __init__(self, config_path):
        self.common = Common()
        self.config = Config(config_path)

        # 创建一个不执行证书验证的 SSLContext 对象
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        # 获取 werkzeug 库的日志记录器
        werkzeug_logger = logging.getLogger("werkzeug")
        # 设置 httpx 日志记录器的级别为 WARNING
        werkzeug_logger.setLevel(logging.WARNING)

        # 请求超时
        self.timeout = 60

        # 日志文件路径
        file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        Configure_logger(file_path)

        try:
            self.audio_out_path = self.config.get("play_audio", "out_path")

            if not os.path.isabs(self.audio_out_path):
                if not self.audio_out_path.startswith('./'):
                    self.audio_out_path = './' + self.audio_out_path
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error("请检查播放音频的音频输出路径配置！！！这将影响程序使用！")


    # 获取随机数，单数据就是原数值，有-则判断为范围性数据，随机一个数值，返回float数据
    def get_random_float(self, data):
        # 将非字符串的情况统一处理为长度相同的最小值和最大值
        if isinstance(data, str) and "-" in data:
            min, max = map(float, data.split("-"))
        else:
            min = max = float(data)
        
        # 返回指定范围内的随机浮点数
        return random.uniform(min, max)

    # 请求vits的api
    async def vits_api(self, data):
        try:
            logging.debug(f"data={data}")
            if data["type"] == "vits":
                # API地址 "http://127.0.0.1:23456/voice/vits"
                API_URL = urljoin(data["api_ip_port"], '/voice/vits')
                data_json = {
                    "text": data["content"],
                    "id": data["id"],
                    "format": data["format"],
                    "lang": "ja",
                    "length": data["length"],
                    "noise": data["noise"],
                    "noisew": data["noisew"],
                    "max": data["max"]
                }
                
                if data["lang"] == "中文" or data["lang"] == "汉语":
                    data_json["lang"] = "zh"
                elif data["lang"] == "英文" or data["lang"] == "英语":
                    data_json["lang"] = "en"
                elif data["lang"] == "韩文" or data["lang"] == "韩语":
                    data_json["lang"] = "ko"
                elif data["lang"] == "日文" or data["lang"] == "日语":
                    data_json["lang"] = "ja"
                elif data["lang"] == "自动":
                    data_json["lang"] = "auto"
                else:
                    data_json["lang"] = "auto"
            elif data["type"] == "bert_vits2":
                # API地址 "http://127.0.0.1:23456/voice/bert-vits2"
                API_URL = urljoin(data["api_ip_port"], '/voice/bert-vits2')

                data_json = {
                    "text": data["content"],
                    "id": data["id"],
                    "format": data["format"],
                    "lang": "ja",
                    "length": self.get_random_float(data["length"]),
                    "noise": self.get_random_float(data["noise"]),
                    "noisew": self.get_random_float(data["noisew"]),
                    "max": data["max"],
                    "sdp_radio": self.get_random_float(data["sdp_radio"])
                }
                
                if data["lang"] == "中文" or data["lang"] == "汉语":
                    data_json["lang"] = "zh"
                elif data["lang"] == "英文" or data["lang"] == "英语":
                    data_json["lang"] = "en"
                elif data["lang"] == "韩文" or data["lang"] == "韩语":
                    data_json["lang"] = "ko"
                elif data["lang"] == "日文" or data["lang"] == "日语":
                    data_json["lang"] = "ja"
                elif data["lang"] == "自动":
                    data_json["lang"] = "auto"
                else:
                    data_json["lang"] = "auto"
            elif data["type"] == "gpt_sovits":
                # 请求vits_simple_api的api gpt_sovits
                async def vits_simple_api_gpt_sovits_api(data):
                    try:
                        from aiohttp import FormData

                        logging.debug(f"data={data}")
                        API_URL = urljoin(data["api_ip_port"], '/voice/gpt-sovits')


                        data_json = {
                            "text": data["content"],
                            "id": data["gpt_sovits"]["id"],
                            "format": data["gpt_sovits"]["format"],
                            "lang": data["gpt_sovits"]["lang"],
                            "segment_size": data["gpt_sovits"]["segment_size"],
                            "prompt_text": data["gpt_sovits"]["prompt_text"],
                            "prompt_lang": data["gpt_sovits"]["prompt_lang"],
                            "preset": data["gpt_sovits"]["preset"],
                            "top_k": data["gpt_sovits"]["top_k"],
                            "top_p": data["gpt_sovits"]["top_p"],
                            "temperature": data["gpt_sovits"]["temperature"]
                        }

                        # 创建 FormData 对象
                        form_data = FormData()
                        # 添加文本字段
                        for key, value in data_json.items():
                            form_data.add_field(key, str(value))

                        # 以二进制读取模式打开音频文件，并添加到表单数据中
                        # 'reference_audio' 是字段名称，应与服务器端接收的名称一致
                        form_data.add_field('reference_audio',
                                    open(data["gpt_sovits"]["reference_audio"], 'rb'),
                                    content_type='audio/mpeg')  # 内容类型根据文件类型修改
                            
                        logging.debug(f"data_json={data_json}")

                        logging.debug(f"API_URL={API_URL}")

                        async with aiohttp.ClientSession() as session:
                            async with session.post(API_URL, data=form_data, timeout=self.timeout) as response:
                                response = await response.read()
                                # print(response)
                                file_name = 'vits_simple_api_' + self.common.get_bj_time(4) + '.wav'
                                voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)

                                with open(voice_tmp_path, 'wb') as f:
                                    f.write(response)
                                
                                return voice_tmp_path
                    except aiohttp.ClientError as e:
                        logging.error(traceback.format_exc())
                        logging.error(f'vits_simple_api gpt_sovits请求失败，请检查您的vits_simple_api是否启动/配置是否正确，报错内容: {e}')
                    except Exception as e:
                        logging.error(traceback.format_exc())
                        logging.error(f'vits_simple_api gpt_sovits未知错误，请检查您的vits_simple_api是否启动/配置是否正确，报错内容: {e}')
                    
                    return None
                
                voice_tmp_path = await vits_simple_api_gpt_sovits_api(data)
                return voice_tmp_path
                
            # logging.info(f"data_json={data_json}")
            # logging.info(f"data={data}")

            logging.debug(f"API_URL={API_URL}")

            url = f"{API_URL}?{urlencode(data_json)}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as response:
                    response = await response.read()
                    # print(response)
                    file_name = 'vits_' + self.common.get_bj_time(4) + '.wav'
                    voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
                    with open(voice_tmp_path, 'wb') as f:
                        f.write(response)
                    
                    return voice_tmp_path
        except aiohttp.ClientError as e:
            logging.error(traceback.format_exc())
            logging.error(f'vits请求失败，请检查您的vits-simple-api是否启动/配置是否正确，报错内容: {e}')
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'vits未知错误，请检查您的vits-simple-api是否启动/配置是否正确，报错内容: {e}')
        
        return None

    # 请求bert_vits2的api
    async def bert_vits2_api(self, data):
        try:
            logging.debug(f"data={data}")
            if data["type"] == "hiyori":
                # API地址 "http://127.0.0.1:5000/voice"
                API_URL = urljoin(data["api_ip_port"], '/voice')

                data_json = {
                    "text": data["content"],
                    "model_id": data["model_id"],
                    "speaker_name": data["speaker_name"],
                    "speaker_id": data["speaker_id"],
                    "language": data["language"],
                    "length": self.get_random_float(data["length"]),
                    "noise": self.get_random_float(data["noise"]),
                    "noisew": self.get_random_float(data["noisew"]),
                    "sdp_radio": self.get_random_float(data["sdp_radio"]),
                    "auto_translate": data["auto_translate"],
                    "auto_split": data["auto_split"],
                    "emotion": data["emotion"],
                    "style_text": data["style_text"],
                    "style_weight": self.get_random_float(data["style_weight"])
                }
                
            logging.debug(f"data_json={data_json}")
            # logging.info(f"data={data}")

            logging.debug(f"API_URL={API_URL}")

            url = f"{API_URL}?{urlencode(data_json)}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as response:
                    response = await response.read()
                    # print(response)
                    file_name = 'bert_vits2_' + self.common.get_bj_time(4) + '.wav'
                    voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
                    with open(voice_tmp_path, 'wb') as f:
                        f.write(response)
                    
                    return voice_tmp_path
        except aiohttp.ClientError as e:
            logging.error(traceback.format_exc())
            logging.error(f'bert_vits2请求失败，请检查您的bert_vits2 api是否启动/配置是否正确，报错内容: {e}')
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'bert_vits2未知错误，请检查您的bert_vits2 api是否启动/配置是否正确，报错内容: {e}')
        
        return None
    
    # 请求VITS fast接口获取合成后的音频路径
    def vits_fast_api(self, data):
        try:
            # API地址
            API_URL = urljoin(data["api_ip_port"], '/run/predict/')

            data_json = {
                "fn_index":0,
                "data":[
                    "こんにちわ。",
                    "ikaros",
                    "日本語",
                    1
                ],
                "session_hash":"mnqeianp9th"
            }

            data_json["data"] = [data["content"], data["character"], data["language"], data["speed"]]

            logging.debug(f'data_json={data_json}')

            response = requests.post(url=API_URL, json=data_json, timeout=self.timeout)
            response.raise_for_status()  # 检查响应的状态码

            result = response.content
            ret = json.loads(result)

            file_path = ret["data"][1]["name"]

            new_file_path = self.common.move_file(file_path, os.path.join(self.audio_out_path, 'vits_fast_' + self.common.get_bj_time(4)), 'vits_fast_' + self.common.get_bj_time(4))

            return new_file_path
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'vits-fast错误，请检查您的vits-fast推理程序是否启动/配置是否正确，报错内容: {e}')
            return None
    

    # 请求Edge-TTS接口获取合成后的音频路径
    async def edge_tts_api(self, data):
        try:
            file_name = 'edge_tts_' + self.common.get_bj_time(4) + '.mp3'
            voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
            # voice_tmp_path = './out/' + self.common.get_bj_time(4) + '.mp3'
            # 过滤" '字符
            data["content"] = data["content"].replace('"', '').replace("'", '')
            # 使用 Edge TTS 生成回复消息的语音文件
            communicate = edge_tts.Communicate(text=data["content"], voice=data["voice"], rate=data["rate"], volume=data["volume"])
            await communicate.save(voice_tmp_path)

            return voice_tmp_path
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(e)
            return None
        

    # 请求bark-gui的api
    def bark_gui_api(self, data):
        try:
            client = Client(data["api_ip_port"])
            result = client.predict(
                data["content"],	# str  in 'Input Text' Textbox component
                data["spk"],	# str (Option from: ['None', 'announcer', 'custom\\MeMyselfAndI', 'de_speaker_0', 'de_speaker_1', 'de_speaker_2', 'de_speaker_3', 'de_speaker_4', 'de_speaker_5', 'de_speaker_6', 'de_speaker_7', 'de_speaker_8', 'de_speaker_9', 'en_speaker_0', 'en_speaker_1', 'en_speaker_2', 'en_speaker_3', 'en_speaker_4', 'en_speaker_5', 'en_speaker_6', 'en_speaker_7', 'en_speaker_8', 'en_speaker_9', 'es_speaker_0', 'es_speaker_1', 'es_speaker_2', 'es_speaker_3', 'es_speaker_4', 'es_speaker_5', 'es_speaker_6', 'es_speaker_7', 'es_speaker_8', 'es_speaker_9', 'fr_speaker_0', 'fr_speaker_1', 'fr_speaker_2', 'fr_speaker_3', 'fr_speaker_4', 'fr_speaker_5', 'fr_speaker_6', 'fr_speaker_7', 'fr_speaker_8', 'fr_speaker_9', 'hi_speaker_0', 'hi_speaker_1', 'hi_speaker_2', 'hi_speaker_3', 'hi_speaker_4', 'hi_speaker_5', 'hi_speaker_6', 'hi_speaker_7', 'hi_speaker_8', 'hi_speaker_9', 'it_speaker_0', 'it_speaker_1', 'it_speaker_2', 'it_speaker_3', 'it_speaker_4', 'it_speaker_5', 'it_speaker_6', 'it_speaker_7', 'it_speaker_8', 'it_speaker_9', 'ja_speaker_0', 'ja_speaker_1', 'ja_speaker_2', 'ja_speaker_3', 'ja_speaker_4', 'ja_speaker_5', 'ja_speaker_6', 'ja_speaker_7', 'ja_speaker_8', 'ja_speaker_9', 'ko_speaker_0', 'ko_speaker_1', 'ko_speaker_2', 'ko_speaker_3', 'ko_speaker_4', 'ko_speaker_5', 'ko_speaker_6', 'ko_speaker_7', 'ko_speaker_8', 'ko_speaker_9', 'pl_speaker_0', 'pl_speaker_1', 'pl_speaker_2', 'pl_speaker_3', 'pl_speaker_4', 'pl_speaker_5', 'pl_speaker_6', 'pl_speaker_7', 'pl_speaker_8', 'pl_speaker_9', 'pt_speaker_0', 'pt_speaker_1', 'pt_speaker_2', 'pt_speaker_3', 'pt_speaker_4', 'pt_speaker_5', 'pt_speaker_6', 'pt_speaker_7', 'pt_speaker_8', 'pt_speaker_9', 'ru_speaker_0', 'ru_speaker_1', 'ru_speaker_2', 'ru_speaker_3', 'ru_speaker_4', 'ru_speaker_5', 'ru_speaker_6', 'ru_speaker_7', 'ru_speaker_8', 'ru_speaker_9', 'speaker_0', 'speaker_1', 'speaker_2', 'speaker_3', 'speaker_4', 'speaker_5', 'speaker_6', 'speaker_7', 'speaker_8', 'speaker_9', 'tr_speaker_0', 'tr_speaker_1', 'tr_speaker_2', 'tr_speaker_3', 'tr_speaker_4', 'tr_speaker_5', 'tr_speaker_6', 'tr_speaker_7', 'tr_speaker_8', 'tr_speaker_9', 'v2\\de_speaker_0', 'v2\\de_speaker_1', 'v2\\de_speaker_2', 'v2\\de_speaker_3', 'v2\\de_speaker_4', 'v2\\de_speaker_5', 'v2\\de_speaker_6', 'v2\\de_speaker_7', 'v2\\de_speaker_8', 'v2\\de_speaker_9', 'v2\\en_speaker_0', 'v2\\en_speaker_1', 'v2\\en_speaker_2', 'v2\\en_speaker_3', 'v2\\en_speaker_4', 'v2\\en_speaker_5', 'v2\\en_speaker_6', 'v2\\en_speaker_7', 'v2\\en_speaker_8', 'v2\\en_speaker_9', 'v2\\es_speaker_0', 'v2\\es_speaker_1', 'v2\\es_speaker_2', 'v2\\es_speaker_3', 'v2\\es_speaker_4', 'v2\\es_speaker_5', 'v2\\es_speaker_6', 'v2\\es_speaker_7', 'v2\\es_speaker_8', 'v2\\es_speaker_9', 'v2\\fr_speaker_0', 'v2\\fr_speaker_1', 'v2\\fr_speaker_2', 'v2\\fr_speaker_3', 'v2\\fr_speaker_4', 'v2\\fr_speaker_5', 'v2\\fr_speaker_6', 'v2\\fr_speaker_7', 'v2\\fr_speaker_8', 'v2\\fr_speaker_9', 'v2\\hi_speaker_0', 'v2\\hi_speaker_1', 'v2\\hi_speaker_2', 'v2\\hi_speaker_3', 'v2\\hi_speaker_4', 'v2\\hi_speaker_5', 'v2\\hi_speaker_6', 'v2\\hi_speaker_7', 'v2\\hi_speaker_8', 'v2\\hi_speaker_9', 'v2\\it_speaker_0', 'v2\\it_speaker_1', 'v2\\it_speaker_2', 'v2\\it_speaker_3', 'v2\\it_speaker_4', 'v2\\it_speaker_5', 'v2\\it_speaker_6', 'v2\\it_speaker_7', 'v2\\it_speaker_8', 'v2\\it_speaker_9', 'v2\\ja_speaker_0', 'v2\\ja_speaker_1', 'v2\\ja_speaker_2', 'v2\\ja_speaker_3', 'v2\\ja_speaker_4', 'v2\\ja_speaker_5', 'v2\\ja_speaker_6', 'v2\\ja_speaker_7', 'v2\\ja_speaker_8', 'v2\\ja_speaker_9', 'v2\\ko_speaker_0', 'v2\\ko_speaker_1', 'v2\\ko_speaker_2', 'v2\\ko_speaker_3', 'v2\\ko_speaker_4', 'v2\\ko_speaker_5', 'v2\\ko_speaker_6', 'v2\\ko_speaker_7', 'v2\\ko_speaker_8', 'v2\\ko_speaker_9', 'v2\\pl_speaker_0', 'v2\\pl_speaker_1', 'v2\\pl_speaker_2', 'v2\\pl_speaker_3', 'v2\\pl_speaker_4', 'v2\\pl_speaker_5', 'v2\\pl_speaker_6', 'v2\\pl_speaker_7', 'v2\\pl_speaker_8', 'v2\\pl_speaker_9', 'v2\\pt_speaker_0', 'v2\\pt_speaker_1', 'v2\\pt_speaker_2', 'v2\\pt_speaker_3', 'v2\\pt_speaker_4', 'v2\\pt_speaker_5', 'v2\\pt_speaker_6', 'v2\\pt_speaker_7', 'v2\\pt_speaker_8', 'v2\\pt_speaker_9', 'v2\\ru_speaker_0', 'v2\\ru_speaker_1', 'v2\\ru_speaker_2', 'v2\\ru_speaker_3', 'v2\\ru_speaker_4', 'v2\\ru_speaker_5', 'v2\\ru_speaker_6', 'v2\\ru_speaker_7', 'v2\\ru_speaker_8', 'v2\\ru_speaker_9', 'v2\\tr_speaker_0', 'v2\\tr_speaker_1', 'v2\\tr_speaker_2', 'v2\\tr_speaker_3', 'v2\\tr_speaker_4', 'v2\\tr_speaker_5', 'v2\\tr_speaker_6', 'v2\\tr_speaker_7', 'v2\\tr_speaker_8', 'v2\\tr_speaker_9', 'v2\\zh_speaker_0', 'v2\\zh_speaker_1', 'v2\\zh_speaker_2', 'v2\\zh_speaker_3', 'v2\\zh_speaker_4', 'v2\\zh_speaker_5', 'v2\\zh_speaker_6', 'v2\\zh_speaker_7', 'v2\\zh_speaker_8', 'v2\\zh_speaker_9', 'zh_speaker_0', 'zh_speaker_1', 'zh_speaker_2', 'zh_speaker_3', 'zh_speaker_4', 'zh_speaker_5', 'zh_speaker_6', 'zh_speaker_7', 'zh_speaker_8', 'zh_speaker_9']) in 'Voice' Dropdown component
                data["generation_temperature"],	# int | float (numeric value between 0.1 and 1.0) in 'Generation Temperature' Slider component
                data["waveform_temperature"],	# int | float (numeric value between 0.1 and 1.0) in 'Waveform temperature' Slider component
                data["end_of_sentence_probability"],	# int | float (numeric value between 0.0 and 0.5) in 'End of sentence probability' Slider component
                data["quick_generation"],	# bool  in 'Quick Generation' Checkbox component
                [],	# List[str]  in 'Detailed Generation Settings' Checkboxgroup component
                data["seed"],	# int | float  in 'Seed (default -1 = Random)' Number component
                data["batch_count"],	# int | float  in 'Batch count' Number component
                fn_index=3
            )

            new_file_path = self.common.move_file(result, os.path.join(self.audio_out_path, 'bark_gui_' + self.common.get_bj_time(4)), 'bark_gui_' + self.common.get_bj_time(4))

            return new_file_path
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'bark_gui请求失败，请检查您的bark_gui是否启动/配置是否正确，报错内容: {e}')
            return None
    

    # 请求VALL-E-X的api
    def vall_e_x_api(self, data):
        try:
            client = Client(data["api_ip_port"])
            result = client.predict(
				data["content"],	# str in 'Text' Textbox component
				data["language"],	# str (Option from: ['auto-detect', 'English', '中文', '日本語', 'Mix']) in 'language' Dropdown component
				data["accent"],	# str (Option from: ['no-accent', 'English', '中文', '日本語']) in 'accent' Dropdown component
				data["voice_preset"],	# str (Option from: ['astraea', 'cafe', 'dingzhen', 'esta', 'ikaros', 'MakiseKurisu', 'mikako', 'nymph', 'rosalia', 'seel', 'sohara', 'sukata', 'tomoki', 'tomoko', 'yaesakura', '早见沙织', '神里绫华-日语']) in 'Voice preset' Dropdown component
				data["voice_preset_file_path"],	# str (filepath or URL to file) in 'parameter_46' File component
				fn_index=5
            )

            new_file_path = self.common.move_file(result[1], os.path.join(self.audio_out_path, 'vall_e_x_' + self.common.get_bj_time(4)), 'vall_e_x_' + self.common.get_bj_time(4))

            return new_file_path
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'vall_e_x_api请求失败，请检查您的bark_gui是否启动/配置是否正确，报错内容: {e}')
            return None


    # 请求genshinvoice.top的api
    async def genshinvoice_top_api(self, text):
        url = 'https://genshinvoice.top/api'

        genshinvoice_top = self.config.get("genshinvoice_top")

        params = {
            'speaker': genshinvoice_top['speaker'],
            'text': text,
            'format': genshinvoice_top['format'],
            'length': genshinvoice_top['length'],
            'noise': genshinvoice_top['noise'],
            'noisew': genshinvoice_top['noisew'],
            'language': genshinvoice_top['language']
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=self.timeout) as response:
                    response = await response.read()
                    # voice_tmp_path = os.path.join(self.audio_out_path, 'genshinvoice_top_' + self.common.get_bj_time(4) + '.wav')
                    file_name = 'genshinvoice_top_' + self.common.get_bj_time(4) + '.wav'

                    voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)

                    with open(voice_tmp_path, 'wb') as f:
                        f.write(response)
                    
                    return voice_tmp_path
        except aiohttp.ClientError as e:
            logging.error(traceback.format_exc())
            logging.error(f'genshinvoice.top请求失败: {e}')
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'genshinvoice.top未知错误: {e}')
        
        return None

    # 请求https://tts.ai-hobbyist.org/的api
    async def tts_ai_lab_top_api(self, text):
        url = 'https://tirs.ai-lab.top/api/ex/vits'

        tts_ai_lab_top = self.config.get("tts_ai_lab_top")

        params = {
            "token": tts_ai_lab_top['token'],
            "appid": tts_ai_lab_top['appid'],
            'lang': tts_ai_lab_top['lang'],
            'speaker': tts_ai_lab_top['speaker'],
            'text': text,
            'sdp_ratio': float(tts_ai_lab_top['sdp_ratio']),
            'length': float(tts_ai_lab_top['length']),
            'noise': float(tts_ai_lab_top['noise']),
            'noisew': float(tts_ai_lab_top['noisew'])
        }

        logging.debug(f"params={params}")

        

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params, timeout=self.timeout) as response:
                    ret = await response.json()
                    logging.debug(ret)

                    file_url = ret["audio"]

                    if file_url is None:
                        logging.error(f'tts.ai-lab.top合成失败，错误信息: {ret["message"]}')
                        return None

                    async with session.get(file_url, timeout=self.timeout) as response:
                        if response.status == 200:
                            content = await response.read()

                            # voice_tmp_path = os.path.join(self.audio_out_path, 'tts_ai_lab_top_' + self.common.get_bj_time(4) + '.wav')
                            file_name = 'tts_ai_lab_top_' + self.common.get_bj_time(4) + '.wav'

                            voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
                            
                            with open(voice_tmp_path, 'wb') as file:
                                file.write(content)

                            return voice_tmp_path
                        else:
                            logging.error(f'tts.ai-lab.top下载音频失败: {response.status}')
                            return None
        except aiohttp.ClientError as e:
            logging.error(traceback.format_exc())
            logging.error(f'tts.ai-lab.top请求失败: {e}')
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'tts.ai-lab.top未知错误: {e}')
        
        return None

    # 请求OpenAI_TTS的api
    def openai_tts_api(self, data):
        try:
            if data["type"] == "huggingface":
                client = Client(data["api_ip_port"])
                result = client.predict(
                    data["content"],	# str in 'Text' Textbox component
                    data["model"],	# Literal[tts-1, tts-1-hd]  in 'Model' Dropdown component
                    data["voice"],	# Literal[alloy, echo, fable, onyx, nova, shimmer]  in 'Voice Options' Dropdown component
                    data["api_key"],	# str  in 'OpenAI API Key' Textbox component
                    api_name="/tts_enter_key"
                )

                new_file_path = self.common.move_file(result, os.path.join(self.audio_out_path, 'openai_tts_' + self.common.get_bj_time(4)), 'openai_tts_' + self.common.get_bj_time(4), "mp3")

                return new_file_path
            elif data["type"] == "api":
                from openai import OpenAI
                
                client = OpenAI(api_key=data["api_key"])

                response = client.audio.speech.create(
                    model=data["model"],
                    voice=data["voice"],
                    input=data["content"]
                )

                file_name = 'openai_tts_' + self.common.get_bj_time(4) + '.mp3'
                voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)

                response.stream_to_file(voice_tmp_path)

                return voice_tmp_path
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'OpenAI_TTS请求失败: {e}')
            return None

    # 请求睿声AI的api
    async def reecho_ai_api(self, text):
        url = 'https://v1.reecho.ai/api/tts/simple-generate'

        reecho_ai = self.config.get("reecho_ai")
        
        headers = {  
            "Authorization": f"Bearer {reecho_ai['Authorization']}",  
            "Content-Type": "application/json"
        }

        params = {
            "model": reecho_ai['model'],
            'randomness': reecho_ai['randomness'],
            'stability_boost': reecho_ai['stability_boost'],
            'voiceId': reecho_ai['voiceId'],
            'text': text
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=params, timeout=self.timeout) as response:
                    ret = await response.json()
                    logging.debug(ret)

                    file_url = ret["data"]["audio"]

                    async with session.get(file_url, timeout=self.timeout) as response:
                        if response.status == 200:
                            content = await response.read()

                            # voice_tmp_path = os.path.join(self.audio_out_path, 'reecho_ai_' + self.common.get_bj_time(4) + '.wav')
                            file_name = 'reecho_ai_' + self.common.get_bj_time(4) + '.mp3'

                            voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
                            
                            with open(voice_tmp_path, 'wb') as file:
                                file.write(content)

                            return voice_tmp_path
                        else:
                            logging.error(f'reecho.ai下载音频失败: {response.status}')
                            return None
        except aiohttp.ClientError as e:
            logging.error(f'reecho.ai请求失败: {e}')
        except Exception as e:
            logging.error(f'reecho.ai未知错误: {e}')
        
        return None


    # 请求gradio的api
    def gradio_tts_api(self, data):
        def get_value_by_index(response, index):
            try:
                # 确保响应是元组或列表，并且索引在范围内
                if isinstance(response, (tuple, list)) and index < len(response):
                    return response[index]
                else:
                    return None
            except IndexError:
                logging.error(traceback.format_exc())
                # 索引超出范围
                return None

        def get_file_path(data):
            try:
                url = data.pop('url')  # 获取并移除URL
                fn_index = data.pop('fn_index')  # 获取并移除函数索引
                data_analysis = data.pop('data_analysis')

                client = Client(url)

                # data是一个字典，包含了所有需要的参数
                data_values = list(data.values())
                result = client.predict(fn_index=fn_index, *data_values)

                logging.debug(result)

                if isinstance(result, (tuple, list)):
                    # 获取索引为1的元素
                    file_path = get_value_by_index(result, int(data_analysis))

                if file_path:
                    logging.debug(f"文件路径:{file_path}")
                    return file_path
                else:
                    logging.error("数据解析失败！Invalid index or response format.")
                    return None
            except Exception as e:
                logging.error(traceback.format_exc())
                # 索引超出范围
                return None

        logging.debug(f"data={data}")
        data_str = data["request_parameters"]
        formatted_data_str = data_str.format(content=data["content"])
        data_json = json.loads(formatted_data_str)

        file_path = get_file_path(data_json)

        new_file_path = self.common.move_file(file_path, os.path.join(self.audio_out_path, 'gradio_tts_' + self.common.get_bj_time(4)), 'gradio_tts_' + self.common.get_bj_time(4))

        return new_file_path


    async def gpt_sovits_api(self, data):
        import base64
        import mimetypes
        import websockets
        import asyncio

        def file_to_data_url(file_path):
            # 根据文件扩展名确定 MIME 类型
            mime_type, _ = mimetypes.guess_type(file_path)

            # 读取文件内容
            with open(file_path, "rb") as file:
                file_content = file.read()

            # 转换为 Base64 编码
            base64_encoded_data = base64.b64encode(file_content).decode('utf-8')

            # 构造完整的 Data URL
            return f"data:{mime_type};base64,{base64_encoded_data}"

        async def websocket_client(data_json):
            try:
                async with websockets.connect(data["ws_ip_port"]) as websocket:
                    # 设置最大连接时长（例如 30 秒）
                    return await asyncio.wait_for(websocket_client_logic(websocket, data_json), timeout=30)
            except asyncio.TimeoutError:
                logging.error("gpt_sovits WebSocket连接超时")
                return None

        async def websocket_client_logic(websocket, data_json):
            async for message in websocket:
                logging.debug(f"Received message: {message}")

                # 解析收到的消息
                data = json.loads(message)
                # 检查是否是预期的消息
                if "msg" in data:
                    if data["msg"] == "send_hash":
                        # 发送响应消息
                        response = json.dumps({"session_hash":"3obpzfqql7f","fn_index":3})
                        await websocket.send(response)
                        logging.debug(f"Sent message: {response}")
                    elif data["msg"] == "send_data":
                        # audio_path = "F:\\GPT-SoVITS\\raws\\ikaros\\1.wav"
                        audio_path = data_json["ref_audio_path"]

                        # 发送响应消息
                        response = json.dumps(
                            {
                                "session_hash":"3obpzfqql7f",
                                "fn_index":3,
                                "data":[
                                    {
                                        "data": file_to_data_url(audio_path),
                                        "name": os.path.basename(audio_path)
                                    },
                                    data_json["prompt_text"], 
                                    data_json["prompt_language"], 
                                    data_json["content"], 
                                    data_json["language"],
                                    data_json["cut"]
                                ]
                            }
                        )
                        await websocket.send(response)
                        logging.debug(f"Sent message: {response}")
                    elif data["msg"] == "process_completed":
                        return data["output"]["data"][0]["name"]
                    
        try:
            logging.debug(f"data={data}")
            
            if data["type"] == "gradio":
                # 调用函数并等待结果
                voice_tmp_path = await websocket_client(data)

                if voice_tmp_path:
                    new_file_path = self.common.move_file(voice_tmp_path, os.path.join(self.audio_out_path, 'gpt_sovits_' + self.common.get_bj_time(4)), 'gpt_sovits_' + self.common.get_bj_time(4))

                return new_file_path
            elif data["type"] == "api":
                try:
                    data_json = {
                        "refer_wav_path": data["ref_audio_path"],
                        "prompt_text": data["prompt_text"],
                        "prompt_language": data["prompt_language"],
                        "text": data["content"],
                        "text_language": data["language"]
                    }
                                        
                    async with aiohttp.ClientSession() as session:
                        async with session.post(data["api_ip_port"], json=data_json, timeout=self.timeout) as response:
                            response = await response.read()
                            
                            file_name = 'gpt_sovits_' + self.common.get_bj_time(4) + '.wav'

                            voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)

                            with open(voice_tmp_path, 'wb') as f:
                                f.write(response)

                            return voice_tmp_path
                except aiohttp.ClientError as e:
                    logging.error(traceback.format_exc())
                    logging.error(f'gpt_sovits请求失败: {e}')
                except Exception as e:
                    logging.error(traceback.format_exc())
                    logging.error(f'gpt_sovits未知错误: {e}')
            elif data["type"] == "webtts":
                try:
                    # 使用字典推导式构建 params 字典，只包含非空字符串的值
                    params = {
                        key: value
                        for key, value in data["webtts"].items()
                        if value != ""
                        if key != "api_ip_port"
                    }

                    params["speed"] = self.get_random_float(params["speed"])
                    params["text"] = data["content"]
                                        
                    async with aiohttp.ClientSession() as session:
                        async with session.get(data["webtts"]["api_ip_port"], params=params, timeout=self.timeout) as response:
                            response = await response.read()
                            
                            file_name = 'gpt_sovits_' + self.common.get_bj_time(4) + '.wav'

                            voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)

                            with open(voice_tmp_path, 'wb') as f:
                                f.write(response)

                            return voice_tmp_path
                except aiohttp.ClientError as e:
                    logging.error(traceback.format_exc())
                    logging.error(f'gpt_sovits请求失败: {e}')
                except Exception as e:
                    logging.error(traceback.format_exc())
                    logging.error(f'gpt_sovits未知错误: {e}')
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'gpt_sovits未知错误，请检查您的gpt_sovits推理是否启动/配置是否正确，报错内容: {e}')
        
        return None


    async def clone_voice_api(self, data):
        API_URL = urljoin(data["api_ip_port"], '/tts')

        # voice=cn-nan.wav&text=%E4%BD%A0%E5%A5%BD&language=zh-cn&speed=1
        params = {
            "voice": data["voice"],
            "language": data["language"],
            "speed": data["speed"],
            "text": data["content"]
        }

        logging.debug(f"params={params}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, data=params) as response:
                    ret = await response.json()
                    logging.debug(ret)

                    file_path = ret["filename"]

                    return file_path

        except aiohttp.ClientError as e:
            logging.error(traceback.format_exc())
            logging.error(f'clone_voice请求失败: {e}')
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'clone_voice未知错误: {e}')
        
        return None


    def azure_tts_api(self, data):
        """调用Azure TTS API合成音频返回音频路径

        Args:
            data (dict): JSON数据

        Returns:
            str: 音频路径
        """
        try:
            import azure.cognitiveservices.speech as speechsdk

            file_name = 'azure_tts_' + self.common.get_bj_time(4) + '.wav'
            voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
            
            # 创建语音配置对象，使用Azure订阅密钥和服务区域
            speech_config = speechsdk.SpeechConfig(subscription=self.config.get("azure_tts", "subscription_key"), region=self.config.get("azure_tts", "region"))
            speech_config.speech_synthesis_voice_name = self.config.get("azure_tts", "voice_name")

            # 创建音频配置对象，指定输出音频文件路径
            audio_config = speechsdk.audio.AudioOutputConfig(filename=voice_tmp_path)

            # 创建语音合成器对象
            speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

            # 执行文本到语音的转换
            result = speech_synthesizer.speak_text_async(data["content"]).get()

            # 检查结果
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logging.debug(f"音频已成功保存到: {voice_tmp_path}")
                return voice_tmp_path
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                logging.error(f"文本转语音取消: {str(cancellation_details.reason)}")
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    if cancellation_details.error_details:
                        logging.error(f"错误详情: {str(cancellation_details.error_details)}")

                return None
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'azure_tts未知错误: {e}')

            return None
        

    async def fish_speech_load_model(self, data):
        API_URL = urljoin(data["api_ip_port"], f'/v1/models/{data["model_name"]}')

        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(API_URL, json=data["model_config"]) as response:
                    if response.status == 200:
                        ret = await response.json()
                        logging.debug(ret)

                        if ret["name"] == data["model_name"]:
                            logging.info(f'fish_speech模型加载成功: {ret["name"]}')
                            return ret
                    else: 
                        return None

        except aiohttp.ClientError as e:
            logging.error(f'fish_speech请求失败: {e}')
        except Exception as e:
            logging.error(f'fish_speech未知错误: {e}')
        
        return None

    async def fish_speech_api(self, data):
        API_URL = urljoin(data["api_ip_port"], f'/v1/models/{data["model_name"]}/invoke')

        def replace_empty_strings_with_none(input_dict):
            for key, value in input_dict.items():
                if value == "":
                    input_dict[key] = None
            return input_dict

        data["tts_config"] = replace_empty_strings_with_none(data["tts_config"])

        logging.debug(f"data={data}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=data["tts_config"]) as response:
                    if response.status == 200:
                        content = await response.read()

                        voice_tmp_path = os.path.join(self.audio_out_path, 'fish_speech_' + self.common.get_bj_time(4) + '.wav')
                        file_name = 'fish_speech_' + self.common.get_bj_time(4) + '.wav'

                        voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)

                        with open(voice_tmp_path, 'wb') as file:
                            file.write(content)

                        return voice_tmp_path
                    else:
                        logging.error(f'fish_speech下载音频失败: {response.status}')
                        return None
        except aiohttp.ClientError as e:
            logging.error(f'fish_speech请求失败: {e}')
        except Exception as e:
            logging.error(f'fish_speech未知错误: {e}')
        
        return None

    
    