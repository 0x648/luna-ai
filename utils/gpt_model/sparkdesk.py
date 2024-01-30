import json, logging
import requests

from sparkdesk_web.core import SparkWeb
from sparkdesk_api.core import SparkAPI

from utils.common import Common
from utils.logger import Configure_logger


class SPARKDESK:
    def __init__(self, data):
        self.common = Common()
        # 日志文件路径
        file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        Configure_logger(file_path)

        self.type = data["type"]
        # web版配置
        self.cookie = data["cookie"]
        self.fd = data["fd"]
        self.GtToken = data["GtToken"]
        # api版配置
        self.app_id = data["app_id"]
        self.api_secret = data["api_secret"]
        self.api_key = data["api_key"]
        self.version = data["version"]

        self.sparkWeb = None
        self.sparkAPI = None

        if self.cookie != "" and self.fd != "" and self.GtToken != "":
            self.sparkWeb = SparkWeb(
                cookie = self.cookie,
                fd = self.fd,
                GtToken = self.GtToken
            )
        elif self.app_id != "" and self.api_secret != "" and self.api_key != "" and self.version != "":
            self.sparkAPI = SparkAPI(
                app_id = self.app_id,
                api_secret = self.api_secret,
                api_key = self.api_key,
                version = self.version
            )
        else:
            logging.info("讯飞星火配置为空")


    def get_resp(self, prompt):
        if self.type == "web":
            return self.sparkWeb.chat(prompt)
        elif self.type == "api":
            return self.sparkAPI.chat(prompt)
        else:
            logging.error("你瞎动什么配置？？？")
            exit(0)
