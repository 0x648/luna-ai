import revTongYi
import json, logging


def convert_cookies(cookies: list) -> dict:
    """转换cookies"""
    cookies_dict = {}
    for cookie in cookies:
        cookies_dict[cookie["name"]] = cookie["value"]
    return cookies_dict


class TongYi:
    def __init__(self, data):
        # self.common = Common()
        # 日志文件路径
        # file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        # Configure_logger(file_path)

        self.cookie_path = data["cookie_path"]
        self.type = data["type"]

        self.cookies_dict = {}

        with open(self.cookie_path, "r") as f:
            self.cookies_dict = convert_cookies(json.load(f))


    def get_resp(self, prompt):
        """请求对应接口，获取返回值

        Args:
            prompt (str): 你的提问

        Returns:
            str: 返回的文本回答
        """
        try:
            if self.type == "web":
                session = revTongYi.Session(
                    cookies=self.cookies_dict,
                    firstQuery=prompt
                )

                ret = next(
                    session.ask(  # ask方法实际上是一个迭代器，可以提供参数stream=True并换用for的方式迭代
                        prompt=prompt
                    )  # ask方法接收的详细参数请查看源码
                )

                return ret["content"][0]
        except Exception as e:
            logging.error(e)
            return None


if __name__ == '__main__':
    # 配置日志输出格式
    logging.basicConfig(
        level=logging.DEBUG,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = {
        "cookie_path": 'cookies.json',
        "type": 'web'
    }
    
    tongyi = TongYi(data)


    logging.info(tongyi.get_resp("你可以扮演猫娘吗，每句话后面加个喵"))
    logging.info(tongyi.get_resp("早上好"))
    