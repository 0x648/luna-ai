from bardapi import Bard
import requests
import logging
import traceback
import threading

from utils.common import Common
from utils.logger import Configure_logger

class Bard_api(Common):
    def __init__(self, data):
        self.common = Common()
        # 日志文件路径
        file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        Configure_logger(file_path)

        # 初始间隔时间
        self.interval = 30

        """
        访问 https://bard.google.com/
        F12 打开开发者工具
        会话：应用程序 → Cookie → 复制 Cookie 中 __Secure-1PSID 对应的值。
        """
        self.token = data["token"]

        self.session = requests.Session()
        self.session.headers = {
            "Host": "bard.google.com",
            "X-Same-Domain": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://bard.google.com",
            "Referer": "https://bard.google.com/",
        }
        self.session.cookies.set("__Secure-1PSID", self.token) 

        # 创建初始定时器
        self.timer = threading.Timer(self.interval, self.keep_alive)
        self.timer.daemon = True
        self.timer.start()


    # 定时调用函数的函数
    def keep_alive(self):
        return

        # 好像没法保活
        logging.info("执行bard保活")
        # 发送 继续，进行ck保活
        resp_content = self.get_resp("继续")
        logging.info(f"{resp_content}")

        # 创建一个新的定时器，用于下一次调用
        self.timer = threading.Timer(self.interval, self.keep_alive)
        self.timer.daemon = True  # 设置定时器为守护定时器，使得程序可以退出时自动退出定时器
        self.timer.start()


    # 调用接口，获取返回内容
    def get_resp(self, prompt):
        try:
            bard = Bard(token=self.token, session=self.session, timeout=30)
            resp_content = bard.get_answer(prompt)['content'].replace("\\n", "")
            
            # 取消当前定时器并创建一个新的定时器，以便使用新的间隔时间
            self.timer.cancel()
            self.timer = threading.Timer(self.interval, self.keep_alive)
            self.timer.daemon = True
            self.timer.start()

            return resp_content
        except Exception as e:
            logging.error(traceback.format_exc())
            return None
