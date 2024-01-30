import time, logging
import asyncio, threading
import concurrent.futures

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from utils.common import Common
from utils.logger import Configure_logger
from utils.thread import RunThread


class Claude:
    slack_user_token = None
    bot_user_id = None
    client = None
    last_message_timestamp = None
    dm_channel_id = None
    

    def __init__(self, data):
        self.common = Common()
        # 日志文件路径
        file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        Configure_logger(file_path)

        if data["slack_user_token"] == "" or data["bot_user_id"] == "":
            logging.info("Claude slack_user_token or bot_user_id 为空，不进行实例化.")
            return None

        self.slack_user_token = data["slack_user_token"]
        self.bot_user_id = data["bot_user_id"]
        self.client = WebClient(token=self.slack_user_token)
        self.dm_channel_id = self.find_direct_message_channel(self.bot_user_id)
        if not self.dm_channel_id:
            logging.error("Could not find DM channel with the bot.")
            return None
        
        loop = asyncio.new_event_loop()

    ### claude
    def send_message(self, channel, text):
        try:
            return self.client.chat_postMessage(channel=channel, text=text)
        except SlackApiError as e:
            logging.error(f"Error sending message: {e}")
            return None


    def fetch_messages(self, channel, last_message_timestamp):
        response = self.client.conversations_history(channel=channel, oldest=last_message_timestamp)
        return [msg['text'] for msg in response['messages'] if msg['user'] == self.bot_user_id]


    async def get_new_messages(self, channel, last_message_timestamp):
        timeout = 60  # 超时时间设置为60秒
        start_time = time.time()

        while True:
            messages = self.fetch_messages(channel, last_message_timestamp)
            if messages and not messages[-1].endswith('Typing…_'):
                return messages[-1]
            if time.time() - start_time > timeout:
                return None
            
            await asyncio.sleep(3)
    

    def find_direct_message_channel(self, user_id):
        try:
            response = self.client.conversations_open(users=user_id)
            return response['channel']['id']
        except SlackApiError as e:
            logging.info(f"Error opening DM channel: {e}")
            return None

    # 获取claude返回内容
    def get_resp(self, text):
        response = self.send_message(self.dm_channel_id, text)
        if response:
            last_message_timestamp = response['ts']
        else:
            return None

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            thread = RunThread(self.get_new_messages(self.dm_channel_id, last_message_timestamp))
            thread.start()
            thread.join()
            new_message = thread.result
            thread.close()
        else:
            new_message = asyncio.run(self.get_new_messages(self.dm_channel_id, last_message_timestamp))
            
        if new_message is not None:
            return new_message
        return None

    # 重置会话
    def reset_claude(self):
        response = self.send_message(self.dm_channel_id, "/reset")
        if response:
            return True
        else:
            return False
