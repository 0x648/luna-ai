import json, logging, traceback
import requests, re
from urllib.parse import urljoin

from utils.common import Common
from utils.logger import Configure_logger

class TEXT_GENERATION_WEBUI:
    def __init__(self, data):
        self.common = Common()
        # 日志文件路径
        file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        Configure_logger(file_path)

        # 配置过多，点到为止，需要的请自行修改
        # http://127.0.0.1:5000
        self.config_data = data

        self.api_ip_port = data["api_ip_port"]
        self.max_new_tokens = data["max_new_tokens"]
        self.mode = data["mode"]
        self.character = data["character"]
        self.instruction_template = data["instruction_template"]
        self.your_name = data["your_name"]

        self.history_enable = data["history_enable"]
        self.history_max_len = data["history_max_len"]

        if self.config_data["type"] == "coyude":
            self.history = {"internal": [], "visible": []}
        else:
            self.history = []

    # 合并函数
    def merge_jsons(self, json_list):
        merged_json = {"internal": [], "visible": []}
        
        for json_obj in json_list:
            merged_json["internal"].extend(json_obj["internal"])
            merged_json["visible"].extend(json_obj["visible"])
        
        return merged_json
    
    def remove_first_group(self, json_obj):
        """
        删除 JSON 对象中 'internal' 和 'visible' 列表的第一组数据。
        """
        if json_obj["internal"]:
            json_obj["internal"].pop(0)
        if json_obj["visible"]:
            json_obj["visible"].pop(0)
        return json_obj

    def get_resp(self, user_input):
        if self.config_data["type"] == "coyude":
            request = {
                'user_input': user_input,
                'max_new_tokens': self.max_new_tokens,
                'history': self.history,
                'mode': self.mode,  # Valid options: 'chat', 'chat-instruct', 'instruct'
                'character': self.character, # 'TavernAI-Gawr Gura'
                'instruction_template': self.instruction_template,
                'your_name': self.your_name,

                'regenerate': False,
                '_continue': False,
                'stop_at_newline': False,
                'chat_generation_attempts': 1,
                'chat-instruct_command': 'Continue the chat dialogue below. Write a single reply for the character "<|character|>".\n\n<|prompt|>',

                # Generation params. If 'preset' is set to different than 'None', the values
                # in presets/preset-name.yaml are used instead of the individual numbers.
                'preset': 'None',
                'do_sample': True,
                'temperature': 0.7,
                'top_p': 0.1,
                'typical_p': 1,
                'epsilon_cutoff': 0,  # In units of 1e-4
                'eta_cutoff': 0,  # In units of 1e-4
                'tfs': 1,
                'top_a': 0,
                'repetition_penalty': 1.18,
                'repetition_penalty_range': 0,
                'top_k': 40,
                'min_length': 0,
                'no_repeat_ngram_size': 0,
                'num_beams': 1,
                'penalty_alpha': 0,
                'length_penalty': 1,
                'early_stopping': False,
                'mirostat_mode': 0,
                'mirostat_tau': 5,
                'mirostat_eta': 0.1,

                'seed': -1,
                'add_bos_token': True,
                'truncation_length': 2048,
                'ban_eos_token': False,
                'skip_special_tokens': True,
                'stopping_strings': []
            }

            try:
                url = urljoin(self.api_ip_port, "/api/v1/chat")
                response = requests.post(url=url, json=request)

                if response.status_code == 200:
                    result = response.json()['results'][0]['history']
                    # logging.info(json.dumps(result, indent=4))
                    # print(result['visible'][-1][1])
                    resp_content = result['visible'][-1][1]

                    # 启用历史就给我记住！
                    if self.history_enable:
                        while True:
                            # 统计字符数
                            total_chars = sum(len(item) for sublist in self.history['internal'] for item in sublist)
                            total_chars += sum(len(item) for sublist in self.history['visible'] for item in sublist)
                            logging.info(f"total_chars={total_chars}")
                            # 如果大于限定最大历史数，就剔除第一个元素
                            if total_chars > self.history_max_len:
                                self.history = self.remove_first_group(self.history)
                            else:
                                self.history = result
                                break

                    return resp_content
                else:
                    return None
            except Exception as e:
                logging.error(traceback.format_exc())
                return None
        else:
            try:
                url = urljoin(self.api_ip_port, "/v1/chat/completions")

                headers = {
                    "Content-Type": "application/json"
                }

                self.history.append({"role": "user", "content": user_input})

                data = {
                    "messages": self.history,
                    "temperature": self.config_data["temperature"],
                    "top_p": self.config_data["top_p"],
                    "top_k": self.config_data["top_k"],
                    # "user": "string",
                    "mode": self.mode,
                    "character": self.character,
                    "max_tokens": self.max_new_tokens,
                    "instruction_template": self.instruction_template,
                    "stream": False,
                    "seed": self.config_data["seed"],
                    # "preset": self.config_data["preset"],
                    # "stop": "string",
                    # "n": 1,
                    # "presence_penalty": 0,
                    # "model": "string",
                    # "instruction_template_str": "string",
                    # "frequency_penalty": 0,
                    # "function_call": "string",
                    # "functions": [
                    #     {}
                    # ],
                    # "logit_bias": {},
                    # "name1": "string",
                    # "name2": "string",
                    # "context": "string",
                    # "greeting": "string",
                    # "chat_template_str": "string",
                    # "chat_instruct_command": "string",
                    # "continue_": False,
                    # "min_p": 0,
                    # "repetition_penalty": 1,
                    # "repetition_penalty_range": 1024,
                    # "typical_p": 1,
                    # "tfs": 1,
                    # "top_a": 0,
                    # "epsilon_cutoff": 0,
                    # "eta_cutoff": 0,
                    # "guidance_scale": 1,
                    # "negative_prompt": "",
                    # "penalty_alpha": 0,
                    # "mirostat_mode": 0,
                    # "mirostat_tau": 5,
                    # "mirostat_eta": 0.1,
                    # "temperature_last": False,
                    # "do_sample": True,
                    # "encoder_repetition_penalty": 1,
                    # "no_repeat_ngram_size": 0,
                    # "min_length": 0,
                    # "num_beams": 1,
                    # "length_penalty": 1,
                    # "early_stopping": False,
                    # "truncation_length": 0,
                    # "max_tokens_second": 0,
                    # "custom_token_bans": "",
                    # "auto_max_new_tokens": False,
                    # "ban_eos_token": False,
                    # "add_bos_token": True,
                    # "skip_special_tokens": True,
                    # "grammar_string": ""
                }

                logging.debug(data)

                response = requests.post(url, headers=headers, json=data, verify=False)
                resp_json = response.json()
                logging.debug(resp_json)

                resp_content = resp_json['choices'][0]['message']['content']
                # 过滤多余的 \n
                resp_content = re.sub(r'\n+', '\n', resp_content)
                # 从字符串的两端或者一端删除指定的字符，默认是空格或者换行符
                resp_content = resp_content.rstrip('\n')
                self.history.append({"role": "assistant", "content": resp_content})

                # 启用历史就给我记住！
                if self.history_enable:
                    while True:
                        total_chars = sum(len(i['content']) for i in self.history)
                        # 如果大于限定最大历史数，就剔除第1 个元素
                        if total_chars > self.history_max_len:
                            self.history.pop(0)
                            # self.history.pop(0)
                        else:
                            break

                return resp_content
            except Exception as e:
                logging.error(traceback.format_exc())
                return None


    # 源于官方 api-example.py
    def get_resp2(self, prompt):
        request = {
            'prompt': prompt,
            'max_new_tokens': self.max_new_tokens,

            # Generation params. If 'preset' is set to different than 'None', the values
            # in presets/preset-name.yaml are used instead of the individual numbers.
            'preset': 'None',  
            'do_sample': True,
            'temperature': 0.7,
            'top_p': 0.1,
            'typical_p': 1,
            'epsilon_cutoff': 0,  # In units of 1e-4
            'eta_cutoff': 0,  # In units of 1e-4
            'tfs': 1,
            'top_a': 0,
            'repetition_penalty': 1.18,
            'repetition_penalty_range': 0,
            'top_k': 40,
            'min_length': 0,
            'no_repeat_ngram_size': 0,
            'num_beams': 1,
            'penalty_alpha': 0,
            'length_penalty': 1,
            'early_stopping': False,
            'mirostat_mode': 0,
            'mirostat_tau': 5,
            'mirostat_eta': 0.1,

            'seed': -1,
            'add_bos_token': True,
            'truncation_length': 2048,
            'ban_eos_token': False,
            'skip_special_tokens': True,
            'stopping_strings': []
        }

        response = requests.post(self.api_ip_port + "/api/v1/generate", json=request)

        try:
            if response.status_code == 200:
                result = response.json()['results'][0]['text']
                print(prompt + result)

                return result
            else:
                return None
        except Exception as e:
            logging.error(e)
            return None
