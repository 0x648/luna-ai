from nicegui import ui, app
import sys, os, json, subprocess, importlib, re, threading, signal
import logging, traceback
import time
import asyncio
# from functools import partial

import http.server
import socketserver

from utils.config import Config
from utils.common import Common
from utils.logger import Configure_logger
from utils.audio import Audio


"""

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@.:;;;++;;;;:,@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@:;+++++;;++++;;;.@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@:++++;;;;;;;;;;+++;,@@@@@@@@@@@@@@@@@
@@@@@@@@@@@.;+++;;;;;;;;;;;;;;++;:@@@@@@@@@@@@@@@@
@@@@@@@@@@;+++;;;;;;;;;;;;;;;;;;++;:@@@@@@@@@@@@@@
@@@@@@@@@:+++;;;;;;;;;;;;;;;;;;;;++;.@@@@@@@@@@@@@
@@@@@@@@;;+;;;;;;;;;;;;;;;;;;;;;;;++:@@@@@@@@@@@@@
@@@@@@@@;+;;;;:::;;;;;;;;;;;;;;;;:;+;,@@@@@@@@@@@@
@@@@@@@:+;;:;;:::;:;;:;;;;::;;:;:::;+;.@@@@@@@@@@@
@@@@@@.;+;::;:,:;:;;+:++:;:::+;:::::++:+@@@@@@@@@@
@@@@@@:+;;:;;:::;;;+%;*?;;:,:;*;;;;:;+;:@@@@@@@@@@
@@@@@@;;;+;;+;:;;;+??;*?++;,:;+++;;;:++:@@@@@@@@@@
@@@@@.++*+;;+;;;;+?;?**??+;:;;+.:+;;;;+;;@@@@@@@@@
@@@@@,+;;;;*++*;+?+;**;:?*;;;;*:,+;;;;+;,@@@@@@@@@
@@@@@,:,+;+?+?++?+;,?#%*??+;;;*;;:+;;;;+:@@@@@@@@@
@@@@@@@:+;*?+?#%;;,,?###@#+;;;*;;,+;;;;+:@@@@@@@@@
@@@@@@@;+;??+%#%;,,,;SSS#S*+++*;..:+;?;+;@@@@@@@@@
@@@@@@@:+**?*?SS,,,,,S#S#+***?*;..;?;**+;@@@@@@@@@
@@@@@@@:+*??*??S,,,,,*%SS+???%++;***;+;;;.@@@@@@@@
@@@@@@@:*?*;*+;%:,,,,;?S?+%%S?%+,:?;+:,,,@@@@@@@@
@@@@@@@,*?,;+;+S:,,,,%?+;S%S%++:+??+:,,,:@@@@@@@@
@@@@@@@,:,@;::;+,,,,,+?%*+S%#?*???*;,,,,,.@@@@@@@@
@@@@@@@@:;,::;;:,,,,,,,,,?SS#??*?+,.,,,:,@@@@@@@@@
@@@@@@;;+;;+:,:%?%*;,,,,SS#%*??%,.,,,,,:@@@@@@@@@
@@@@@.+++,++:;???%S?%;.+#####??;.,,,,,,:@@@@@@@@@
@@@@@:++::??+S#??%#??S%?#@#S*+?*,,,,,,:,@@@@@@@@@@
@@@@@:;;:*?;+%#%?S#??%SS%+#%..;+:,,,,,,@@@@@@@@@@@
@@@@@@,,*S*;?SS?%##%?S#?,.:#+,,+:,,,,,,@@@@@@@@@@@
@@@@@@@;%?%#%?*S##??##?,..*#,,+:,,;*;.@@@@@@@@@@@
@@@@@@.*%??#S*?S#@###%;:*,.:#:,+;:;*+:@@@@@@@@@@@@
@@@@@@,%S??SS%##@@#%S+..;;.,#*;???*?+++:@@@@@@@@@@
@@@@@@:S%??%####@@S,,*,.;*;+#*;+?%??#S%+.@@@@@@@@@
@@@@@@:%???%@###@@?,,:**S##S*;.,%S?;+*?+.,..@@@@@@
@@@@@@;%??%#@###@@#:.;@@#@%%,.,%S*;++*++++;.@@@@@
@@@@@@,%S?S@@###@@@%+#@@#@?;,.:?;??++?%?***+.@@@@@
@@@@@@.*S?S####@@####@@##@?..:*,+:??**%+;;;;..@@@@
@@@@@@:+%?%####@@####@@#@%;:.;;:,+;?**;++;,:;:,@@@
@@@@@@;;*%?%@##@@@###@#S#*:;*+,;.+***?******+:.@@@
@@@@@@:;:??%@###%##@#%++;+*:+;,:;+%?*;+++++;:.@@@@
@@@@@@.+;:?%@@#%;+S*;;,:::**+,;:%??*+.@....@@@@@@@
@@@@@@@;*::?#S#S+;,..,:,;:?+?++*%?+::@@@@@@@@@@@@@
@@@@@@@.+*+++?%S++...,;:***??+;++:.@@@@@@@@@@@@@@@
@@@@@@@@:::..,;+*+;;+*?**+;;;+;:.@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@,+*++;;:,..@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@::,.@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

"""


"""
全局变量
"""
# 创建一个全局变量，用于表示程序是否正在运行
running_flag = False

# 创建一个子进程对象，用于存储正在运行的外部程序
running_process = None

common = None
config = None
audio = None
my_handle = None
config_path = None


web_server_port = 12345


"""
初始化基本配置
"""
def init():
    global config_path, config, common, audio

    common = Common()

    if getattr(sys, 'frozen', False):
        # 当前是打包后的可执行文件
        bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
        file_relative_path = os.path.dirname(os.path.abspath(bundle_dir))
    else:
        # 当前是源代码
        file_relative_path = os.path.dirname(os.path.abspath(__file__))

    # logging.info(file_relative_path)

    # 初始化文件夹
    def init_dir():
        # 创建日志文件夹
        log_dir = os.path.join(file_relative_path, 'log')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 创建音频输出文件夹
        audio_out_dir = os.path.join(file_relative_path, 'out')
        if not os.path.exists(audio_out_dir):
            os.makedirs(audio_out_dir)
            
        # # 创建配置文件夹
        # config_dir = os.path.join(file_relative_path, 'config')
        # if not os.path.exists(config_dir):
        #     os.makedirs(config_dir)

    init_dir()

    # 配置文件路径
    config_path = os.path.join(file_relative_path, 'config.json')

    audio = Audio(config_path, 2)

    # 日志文件路径
    file_path = "./log/log-" + common.get_bj_time(1) + ".txt"
    Configure_logger(file_path)

    # 获取 httpx 库的日志记录器
    httpx_logger = logging.getLogger("httpx")
    # 设置 httpx 日志记录器的级别为 WARNING
    httpx_logger.setLevel(logging.WARNING)

    # 获取特定库的日志记录器
    watchfiles_logger = logging.getLogger("watchfiles")
    # 设置日志级别为WARNING或更高，以屏蔽INFO级别的日志消息
    watchfiles_logger.setLevel(logging.WARNING)

    logging.debug("配置文件路径=" + str(config_path))

    # 实例化配置类
    config = Config(config_path)


init()

# 暗夜模式
dark = ui.dark_mode()

"""
通用函数
"""
def textarea_data_change(data):
    """
    字符串数组数据格式转换
    """
    tmp_str = ""
    for tmp in data:
        tmp_str = tmp_str + tmp + "\n"
    
    return tmp_str


# web服务线程
async def web_server_thread(web_server_port):
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", web_server_port), Handler) as httpd:
        logging.info(f"Web运行在端口：{web_server_port}")
        logging.info(f"可以直接访问Live2D页， http://127.0.0.1:{web_server_port}/Live2D/")
        httpd.serve_forever()


"""
                                                                                                    
                                               .@@@@@                           @@@@@.              
                                               .@@@@@                           @@@@@.              
        ]]]]]   .]]]]`   .]]]]`   ,]@@@@@\`    .@@@@@,/@@@\`   .]]]]]   ]]]]]`  ]]]]].              
        =@@@@^  =@@@@@`  =@@@@. =@@@@@@@@@@@\  .@@@@@@@@@@@@@  *@@@@@   @@@@@^  @@@@@.              
         =@@@@ ,@@@@@@@ .@@@@` =@@@@^   =@@@@^ .@@@@@`  =@@@@^ *@@@@@   @@@@@^  @@@@@.              
          @@@@^@@@@\@@@^=@@@^  @@@@@@@@@@@@@@@ .@@@@@   =@@@@@ *@@@@@   @@@@@^  @@@@@.              
          ,@@@@@@@^ \@@@@@@@   =@@@@^          .@@@@@.  =@@@@^ *@@@@@  .@@@@@^  @@@@@.              
           =@@@@@@  .@@@@@@.    \@@@@@]/@@@@@` .@@@@@@]/@@@@@. .@@@@@@@@@@@@@^  @@@@@.              
            \@@@@`   =@@@@^      ,\@@@@@@@@[   .@@@@^\@@@@@[    .\@@@@@[=@@@@^  @@@@@.    
            
"""
# 配置
webui_ip = config.get("webui", "ip")
webui_port = config.get("webui", "port")
webui_title = config.get("webui", "title")

# CSS
theme_choose = config.get("webui", "theme", "choose")
tab_panel_css = config.get("webui", "theme", "list", theme_choose, "tab_panel")
card_css = config.get("webui", "theme", "list", theme_choose, "card")
button_bottom_css = config.get("webui", "theme", "list", theme_choose, "button_bottom")
button_bottom_color = config.get("webui", "theme", "list", theme_choose, "button_bottom_color")
button_internal_css = config.get("webui", "theme", "list", theme_choose, "button_internal")
button_internal_color = config.get("webui", "theme", "list", theme_choose, "button_internal_color")
switch_internal_css = config.get("webui", "theme", "list", theme_choose, "switch_internal")

def goto_func_page():
    """
    跳转到功能页
    """
    global audio

    """

      =@@^      ,@@@^        .@@@. .....   =@@.      ]@\  ,]]]]]]]]]]]]]]].  .]]]]]]]]]]]]]]]]]]]]    ,]]]]]]]]]]]]]]]]]`    ,/. @@@^ /]  ,@@@.               
      =@@^ .@@@@@@@@@@@@@@^  /@@\]]@@@@@=@@@@@@@@@.  \@@@`=@@@@@@@@@@@@@@@.  .@@@@@@@@@@@@@@@@@@@@    =@@@@@@@@@@@@@@@@@^   .\@@^@@@\@@@`.@@@^                
    @@@@@@@^@@@@@@@@@@@@@@^ =@@@@@^ =@@\]]]/@@]]@@].  =@/`=@@^  .@@@  .@@@.  .@@@^    @@@^    =@@@             ,/@@@@/`     =@@@@@@@@@@@^=@@@@@@@@@.          
    @@@@@@@^@@@^@@\`   =@@^.@@@]]]`=@@^=@@@@@@@@@@@.]]]]` =@@^=@@@@@@@^@@@.  .@@@\]]]]@@@\]]]]/@@@   @@@\/@\..@@@@[./@/@@@. ,[[\@@@@/[[[\@@@`..@@@`           
      =@@^ ,]]]/@@@]]]]]]]].\@@@@@^@@@OO=@@@@@@@@@..@@@@^ =@@^]]]@@@]]`@@@.  .@@@@@@@@@@@@@@@@@@@@   @@@^=@@@^@@@^/@@@\@@@..]@@@@@@@@@@]@@@@^ .@@@.           
      =@@@@=@@@@@@@@@@@@@@@. =@@^ .OO@@@.[[\@@[[[[.  =@@^ =@@^@@@@@@@@^@@@.  .@@@^    @@@^    =@@@   @@@^ .`,]@@@^`,` =@@@. \@/.]@@@^,@@@@@@\ =@@^            
   .@@@@@@@. .@@@`   /@@/  .@@@@@@@,.=@@=@@@@@@@@@^  =@@^,=@@^=@@@@@@@.@@@.  .@@@\]]]]@@@\]]]]/@@@   @@@^]@@@@@@@@@@@]=@@@. ]]]@@@\]]]]] .=@@\@@@.            
    @@\@@^  .@@@\.  /@@@.    =@@^ =@\@@^.../@@.....  =@@@@=@@^=@@[[\@@.@@@.  .@@@@@@@@@@@@@@@@@@@@   @@@@@@/..@@@^,@@@@@@@. O@@@@@@@@@@@  .@@@@@^             
      =@@^   ,\@@@@@@@@.     =@@^/^\@@@`@@@@@@@@@@^  /@@@/@@@`=@@OO@@@.@@@.  =@@@`    @@@^    =@@@   @@@^  \@@@@@^   .=@@@. .@@@@\`/@@/    /@@@\.             
      =@@^    ,/@@@@@@@@]    =@@@@^/@@@@]` =@@.     .\@/.=@@@ =@@[[[[[.@@@.  /@@@     @@@^   ./@@@   @@@^.............=@@@.    O@@@@@@\`,/@@@@@@@@`           
    @@@@@^.@@@@@@@/..[@@@@/. ,@@`/@@@`[@@@@@@@@@@@@.    /@@@^      =@@@@@@. /@@@^     @@@^,@@@@@@^   @@@@@@@@@@@@@@@@@@@@@..\@@@@@[,\@@\@@@@` ,@@@^           
    ,[[[.  .O[[.        [`        ,/         ......       ,^       .[[[[`     ,`      .... [[[[`                      ,[[[. .[.         ,/.     .`

    """
    # 创建一个函数，用于运行外部程序
    def run_external_program(config_path="config.json", type="webui"):
        global running_flag, running_process

        if running_flag:
            if type == "webui":
                ui.notify(position="top", type="warning", message="运行中，请勿重复运行")
            return

        try:
            running_flag = True

            # 在这里指定要运行的程序和参数
            # 例如，运行一个名为 "bilibili.py" 的 Python 脚本
            running_process = subprocess.Popen(["python", f"{select_platform.value}.py"])

            if type == "webui":
                ui.notify(position="top", type="positive", message="程序开始运行")
            logging.info("程序开始运行")

            return {"code": 200, "msg": "程序开始运行"}
        except Exception as e:
            if type == "webui":
                ui.notify(position="top", type="negative", message=f"错误：{e}")
            logging.error(traceback.format_exc())
            running_flag = False

            return {"code": -1, "msg": f"运行失败！{e}"}


    # 定义一个函数，用于停止正在运行的程序
    def stop_external_program(type="webui"):
        global running_flag, running_process

        if running_flag:
            try:
                running_process.terminate()  # 终止子进程
                running_flag = False
                if type == "webui":
                    ui.notify(position="top", type="positive", message="程序已停止")
                logging.info("程序已停止")
            except Exception as e:
                if type == "webui":
                    ui.notify(position="top", type="negative", message=f"停止错误：{e}")
                logging.error(f"停止错误：{e}")

                return {"code": -1, "msg": f"重启失败！{e}"}


    # 开关灯
    def change_light_status(type="webui"):
        if dark.value:
            button_light.set_text("关灯")
        else:
            button_light.set_text("开灯")
        dark.toggle()

    # 重启
    def restart_application(type="webui"):
        try:
            # 先停止运行
            stop_external_program(type)

            logging.info(f"重启webui")
            if type == "webui":
                ui.notify(position="top", type="ongoing", message=f"重启中...")
            python = sys.executable
            os.execl(python, python, *sys.argv)  # Start a new instance of the application
        except Exception as e:
            logging.error(traceback.format_exc())
            return {"code": -1, "msg": f"重启失败！{e}"}
        
    # 恢复出厂配置
    def factory(src_path='config.json.bak', dst_path='config.json', type="webui"):
        # src_path = 'config.json.bak'
        # dst_path = 'config.json'

        try:
            with open(src_path, 'r', encoding="utf-8") as source:
                with open(dst_path, 'w', encoding="utf-8") as destination:
                    destination.write(source.read())
            logging.info("恢复出厂配置成功！")
            if type == "webui":
                ui.notify(position="top", type="positive", message=f"恢复出厂配置成功！")
            
            # 重启
            restart_application()

            return {"code": 200, "msg": "恢复出厂配置成功！"}
        except Exception as e:
            logging.error(f"恢复出厂配置失败！\n{e}")
            if type == "webui":
                ui.notify(position="top", type="negative", message=f"恢复出厂配置失败！\n{e}")
            
            return {"code": -1, "msg": f"恢复出厂配置失败！\n{e}"}
    
    
        
    # openai 测试key可用性
    def test_openai_key():
        data_json = {
            "base_url": input_openai_api.value, 
            "api_keys": textarea_openai_api_key.value, 
            "model": select_chatgpt_model.value,
            "temperature": round(float(input_chatgpt_temperature.value), 1),
            "max_tokens": int(input_chatgpt_max_tokens.value),
            "top_p": round(float(input_chatgpt_top_p.value), 1),
            "presence_penalty": round(float(input_chatgpt_presence_penalty.value), 1),
            "frequency_penalty": round(float(input_chatgpt_frequency_penalty.value), 1),
            "preset": input_chatgpt_preset.value
        }

        if common.test_openai_key(data_json):
            ui.notify(position="top", type="positive", message=f"测试通过！")
        else:
            ui.notify(position="top", type="negative", message=f"测试失败！")
            

    """

                  /@@@@@@@@          @@@@@@@@@@@@@@@].      =@@@@@@@       
                 =@@@@@@@@@^         @@@@@@@@@@@@@@@@@@`    =@@@@@@@       
                ,@@@@@@@@@@@`        @@@@@@@@@@@@@@@@@@@^   =@@@@@@@       
               .@@@@@@\@@@@@@.       @@@@@@@^   .\@@@@@@\   =@@@@@@@       
               /@@@@@/ \@@@@@\       @@@@@@@^    =@@@@@@@   =@@@@@@@       
              =@@@@@@. .@@@@@@^      @@@@@@@\]]]@@@@@@@@^   =@@@@@@@       
             ,@@@@@@^   =@@@@@@`     @@@@@@@@@@@@@@@@@@/    =@@@@@@@       
            .@@@@@@@@@@@@@@@@@@@.    @@@@@@@@@@@@@@@@/`     =@@@@@@@       
            /@@@@@@@@@@@@@@@@@@@\    @@@@@@@^               =@@@@@@@       
           =@@@@@@@@@@@@@@@@@@@@@^   @@@@@@@^               =@@@@@@@       
          ,@@@@@@@.       ,@@@@@@@`  @@@@@@@^               =@@@@@@@       
          @@@@@@@^         =@@@@@@@. @@@@@@@^               =@@@@@@@   

    """
    from starlette.requests import Request

    """
    系统命令
        type 命令类型（run/stop/restart/factory）
        data 传入的json

    data_json = {
        "type": "命令名",
        "data": {
            "key": "value"
        }
    }

    return:
        {"code": 200, "msg": "成功"}
        {"code": -1, "msg": "失败"}
    """
    @app.post('/sys_cmd')
    async def sys_cmd(request: Request):
        try:
            data_json = await request.json()
            logging.info(f'收到数据：{data_json}')
            logging.info(f"开始执行 {data_json['type']}命令...")

            resp_json = {}

            if data_json['type'] == 'run':
                """
                {
                    "type": "run",
                    "data": {
                        "config_path": "config.json"
                    }
                }
                """
                # 运行
                resp_json = run_external_program(data_json['data']['config_path'], type="api")
            elif data_json['type'] =='stop':
                """
                {
                    "type": "stop",
                    "data": {
                        "config_path": "config.json"
                    }
                }
                """
                # 停止
                resp_json = stop_external_program(type="api")
            elif data_json['type'] =='restart':
                """
                {
                    "type": "restart",
                    "api_type": "webui",
                    "data": {
                        "config_path": "config.json"
                    }
                }
                """
                # 重启
                resp_json = restart_application(type=data_json['api_type'])
            elif data_json['type'] =='factory':
                """
                {
                    "type": "factory",
                    "api_type": "webui",
                    "data": {
                        "src_path": "config.json.bak",
                        "dst_path": "config.json"
                    }
                }
                """
                # 恢复出厂
                resp_json = factory(data_json['data']['src_path'], data_json['data']['dst_path'], type="api")

            return resp_json
        except Exception as e:
            logging.error(traceback.format_exc())
            return {"code": -1, "msg": f"{data_json['type']}执行失败！{e}"}

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

    # 文案页-增加
    def copywriting_add():
        data_len = len(copywriting_config_var)
        tmp_config = {
            "file_path": f"data/copywriting{int(data_len / 5) + 1}/",
            "audio_path": f"out/copywriting{int(data_len / 5) + 1}/",
            "continuous_play_num": 2,
            "max_play_time": 10.0,
            "play_list": []
        }

        with copywriting_config_card.style(card_css):
            with ui.row():
                copywriting_config_var[str(data_len)] = ui.input(label=f"文案存储路径#{int(data_len / 5) + 1}", value=tmp_config["file_path"], placeholder='文案文件存储路径。不建议更改。').style("width:200px;")
                copywriting_config_var[str(data_len + 1)] = ui.input(label=f"音频存储路径#{int(data_len / 5) + 1}", value=tmp_config["audio_path"], placeholder='文案音频文件存储路径。不建议更改。').style("width:200px;")
                copywriting_config_var[str(data_len + 2)] = ui.input(label=f"连续播放数#{int(data_len / 5) + 1}", value=tmp_config["continuous_play_num"], placeholder='文案播放列表中连续播放的音频文件个数，如果超过了这个个数就会切换下一个文案列表').style("width:200px;")
                copywriting_config_var[str(data_len + 3)] = ui.input(label=f"连续播放时间#{int(data_len / 5) + 1}", value=tmp_config["max_play_time"], placeholder='文案播放列表中连续播放音频的时长，如果超过了这个时长就会切换下一个文案列表').style("width:200px;")
                copywriting_config_var[str(data_len + 4)] = ui.textarea(label=f"播放列表#{int(data_len / 5) + 1}", value=textarea_data_change(tmp_config["play_list"]), placeholder='此处填写需要播放的音频文件全名，填写完毕后点击 保存配置。文件全名从音频列表中复制，换行分隔，请勿随意填写').style("width:500px;")

    # 文案页-删除
    def copywriting_del(index):
        try:
            copywriting_config_card.remove(int(index) - 1)
            # 删除操作
            keys_to_delete = [str(5 * (int(index) - 1) + i) for i in range(5)]
            for key in keys_to_delete:
                if key in copywriting_config_var:
                    del copywriting_config_var[key]

            # 重新编号剩余的键
            updates = {}
            for key in sorted(copywriting_config_var.keys(), key=int):
                new_key = str(int(key) - 5 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = copywriting_config_var[key]

            # 应用更新
            copywriting_config_var.clear()
            copywriting_config_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logging.error(traceback.format_exc())

    # 文案页-加载文本
    def copywriting_text_load():
        copywriting_text_path = input_copywriting_text_path.value
        if "" == copywriting_text_path:
            logging.warning(f"请输入 文案文本路径喵~")
            ui.notify(position="top", type="warning", message="请输入 文案文本路径喵~")
            return
        
        # 传入完整文件路径 绝对或相对
        logging.info(f"准备加载 文件：[{copywriting_text_path}]")
        new_file_path = os.path.join(copywriting_text_path)

        content = common.read_file_return_content(new_file_path)
        if content is None:
            logging.error(f"读取失败！请检测配置、文件路径、文件名")
            ui.notify(position="top", type="negative", message="读取失败！请检测配置、文件路径、文件名")
            return
        
        # 数据写入文本输入框中
        textarea_copywriting_text.value = content

        logging.info(f"成功加载文案：{copywriting_text_path}")
        ui.notify(position="top", type="positive", message=f"成功加载文案：{copywriting_text_path}")


    # 文案页-保存文案
    def copywriting_save_text():
        content = textarea_copywriting_text.value
        copywriting_text_path = input_copywriting_text_path.value
        if "" == copywriting_text_path:
            logging.warning(f"请输入 文案文本路径喵~")
            ui.notify(position="top", type="warning", message="请输入 文案文本路径喵~")
            return
        
        new_file_path = os.path.join(copywriting_text_path)
        if True == common.write_content_to_file(new_file_path, content):
            ui.notify(position="top", type="positive", message=f"保存成功~")
        else:
            ui.notify(position="top", type="negative", message=f"保存失败！请查看日志排查问题")


    # 文案页-合成音频
    async def copywriting_audio_synthesis():
        ui.notify(position="top", type="warning", message="文案音频合成中，将会阻塞其他任务运行，请勿做其他操作，查看日志情况，耐心等待")
        logging.warning("文案音频合成中，将会阻塞其他任务运行，请勿做其他操作，查看日志情况，耐心等待")
        
        copywriting_text_path = input_copywriting_text_path.value
        copywriting_audio_save_path = input_copywriting_audio_save_path.value

        file_path = await audio.copywriting_synthesis_audio(copywriting_text_path, copywriting_audio_save_path)

        if file_path:
            ui.notify(position="top", type="positive", message=f"文案音频合成成功，存储于：{file_path}")
        else:
            ui.notify(position="top", type="negative", message=f"文案音频合成失败！请查看日志排查问题")


    # 文案页-循环播放
    def copywriting_loop_play():
        if running_flag != 1:
            ui.notify(position="top", type="warning", message=f"请先点击“一键运行”，然后再进行播放")
            return
        
        logging.info("开始循环播放文案~")
        ui.notify(position="top", type="positive", message="开始循环播放文案~")
        
        audio.unpause_copywriting_play()

    # 文案页-暂停播放
    def copywriting_pause_play():
        if running_flag != 1:
            ui.notify(position="top", type="warning", message=f"请先点击“一键运行”，然后再进行暂停")
            return
        
        audio.pause_copywriting_play()
        logging.info("暂停文案完毕~")
        ui.notify(position="top", type="positive", message="暂停文案完毕~")

    """
    配置操作
    """
    # 配置检查
    def check_config():
        # 通用配置 页面
        if select_platform.value == 'bilibili2' and select_bilibili_login_type.value == 'cookie' and input_bilibili_cookie.value == '':
            ui.notify(position="top", type="warning", message="请先前往 通用配置-哔哩哔哩，填写B站cookie")
            return False
        elif select_platform.value == 'bilibili2' and select_bilibili_login_type.value == 'open_live' and \
            (input_bilibili_open_live_ACCESS_KEY_ID.value == '' or input_bilibili_open_live_ACCESS_KEY_SECRET.value == '' or \
            input_bilibili_open_live_APP_ID.value == '' or input_bilibili_open_live_ROOM_OWNER_AUTH_CODE.value == ''):
            ui.notify(position="top", type="warning", message="请先前往 通用配置-哔哩哔哩，填写开放平台配置")
            return False

        return True

    # 保存配置
    def save_config():
        global config, config_path

        # 配置检查
        if not check_config():
            return

        try:
            with open(config_path, 'r', encoding="utf-8") as config_file:
                config_data = json.load(config_file)
        except Exception as e:
            logging.error(f"无法读取配置文件！\n{e}")
            ui.notify(position="top", type="negative", message=f"无法读取配置文件！{e}")
            return False

        def common_textarea_handle(content):
            """通用的textEdit 多行文本内容处理

            Args:
                content (str): 原始多行文本内容

            Returns:
                _type_: 处理好的多行文本内容
            """
            # 通用多行分隔符
            separators = [" ", "\n"]

            ret = [token.strip() for separator in separators for part in content.split(separator) if (token := part.strip())]
            if 0 != len(ret):
                ret = ret[1:]

            return ret


        try:
            """
            通用配置
            """
            if True:
                config_data["platform"] = select_platform.value
                config_data["room_display_id"] = input_room_display_id.value
                config_data["chat_type"] = select_chat_type.value
                config_data["visual_body"] = select_visual_body.value
                config_data["need_lang"] = select_need_lang.value
                config_data["before_prompt"] = input_before_prompt.value
                config_data["after_prompt"] = input_after_prompt.value
                config_data["audio_synthesis_type"] = select_audio_synthesis_type.value

                # 哔哩哔哩
                config_data["bilibili"]["login_type"] = select_bilibili_login_type.value
                config_data["bilibili"]["cookie"] = input_bilibili_cookie.value
                config_data["bilibili"]["ac_time_value"] = input_bilibili_ac_time_value.value
                config_data["bilibili"]["username"] = input_bilibili_username.value
                config_data["bilibili"]["password"] = input_bilibili_password.value
                config_data["bilibili"]["open_live"]["ACCESS_KEY_ID"] = input_bilibili_open_live_ACCESS_KEY_ID.value
                config_data["bilibili"]["open_live"]["ACCESS_KEY_SECRET"] = input_bilibili_open_live_ACCESS_KEY_SECRET.value
                config_data["bilibili"]["open_live"]["APP_ID"] = int(input_bilibili_open_live_APP_ID.value)
                config_data["bilibili"]["open_live"]["ROOM_OWNER_AUTH_CODE"] = input_bilibili_open_live_ROOM_OWNER_AUTH_CODE.value

                # twitch
                config_data["twitch"]["token"] = input_twitch_token.value
                config_data["twitch"]["user"] = input_twitch_user.value
                config_data["twitch"]["proxy_server"] = input_twitch_proxy_server.value
                config_data["twitch"]["proxy_port"] = input_twitch_proxy_port.value

                # 音频播放
                config_data["play_audio"]["enable"] = switch_play_audio_enable.value
                config_data["play_audio"]["text_split_enable"] = switch_play_audio_text_split_enable.value
                config_data["play_audio"]["normal_interval"] = round(float(input_play_audio_normal_interval.value), 2)
                config_data["play_audio"]["out_path"] = input_play_audio_out_path.value
                config_data["play_audio"]["player"] = select_play_audio_player.value

                # audio_player
                config_data["audio_player"]["api_ip_port"] = input_audio_player_api_ip_port.value

                # 念弹幕
                config_data["read_comment"]["enable"] = switch_read_comment_enable.value
                config_data["read_comment"]["read_username_enable"] = switch_read_comment_read_username_enable.value
                config_data["read_comment"]["username_max_len"] = int(input_read_comment_username_max_len.value)
                config_data["read_comment"]["voice_change"] = switch_read_comment_voice_change.value
                config_data["read_comment"]["read_username_copywriting"] = common_textarea_handle(textarea_read_comment_read_username_copywriting.value)

                # 回复时念用户名
                config_data["read_user_name"]["enable"] = switch_read_user_name_enable.value
                config_data["read_user_name"]["username_max_len"] = int(input_read_user_name_username_max_len.value)
                config_data["read_user_name"]["voice_change"] = switch_read_user_name_voice_change.value
                config_data["read_user_name"]["reply_before"] = common_textarea_handle(textarea_read_user_name_reply_before.value)
                config_data["read_user_name"]["reply_after"] = common_textarea_handle(textarea_read_user_name_reply_after.value)

                # 日志
                config_data["comment_log_type"] = select_comment_log_type.value
                config_data["captions"]["enable"] = switch_captions_enable.value
                config_data["captions"]["file_path"] = input_captions_file_path.value
                config_data["captions"]["raw_file_path"] = input_captions_raw_file_path.value

                # 本地问答
                config_data["local_qa"]["text"]["enable"] = switch_local_qa_text_enable.value
                local_qa_text_type = select_local_qa_text_type.value
                if local_qa_text_type == "自定义json":
                    config_data["local_qa"]["text"]["type"] = "json"
                elif local_qa_text_type == "一问一答":
                    config_data["local_qa"]["text"]["type"] = "text"
                config_data["local_qa"]["text"]["file_path"] = input_local_qa_text_file_path.value
                config_data["local_qa"]["text"]["similarity"] = round(float(input_local_qa_text_similarity.value), 2)
                config_data["local_qa"]["text"]["username_max_len"] = int(input_local_qa_text_username_max_len.value)
                config_data["local_qa"]["audio"]["enable"] = switch_local_qa_audio_enable.value
                config_data["local_qa"]["audio"]["file_path"] = input_local_qa_audio_file_path.value
                config_data["local_qa"]["audio"]["similarity"] = round(float(input_local_qa_audio_similarity.value), 2)
            
                # 过滤
                config_data["filter"]["before_must_str"] = common_textarea_handle(textarea_filter_before_must_str.value)
                config_data["filter"]["after_must_str"] = common_textarea_handle(textarea_filter_after_must_str.value)
                config_data["filter"]["before_filter_str"] = common_textarea_handle(textarea_filter_before_filter_str.value)
                config_data["filter"]["after_filter_str"] = common_textarea_handle(textarea_filter_after_filter_str.value)
                config_data["filter"]["badwords"]["enable"] = switch_filter_badwords_enable.value
                config_data["filter"]["badwords"]["discard"] = switch_filter_badwords_discard.value
                config_data["filter"]["badwords"]["path"] = input_filter_badwords_path.value
                config_data["filter"]["badwords"]["bad_pinyin_path"] = input_filter_badwords_bad_pinyin_path.value
                config_data["filter"]["badwords"]["replace"] = input_filter_badwords_replace.value
                config_data["filter"]["emoji"] = switch_filter_emoji.value
                config_data["filter"]["max_len"] = int(input_filter_max_len.value)
                config_data["filter"]["max_char_len"] = int(input_filter_max_char_len.value)
                config_data["filter"]["comment_forget_duration"] = round(float(input_filter_comment_forget_duration.value), 2)
                config_data["filter"]["comment_forget_reserve_num"] = int(input_filter_comment_forget_reserve_num.value)
                config_data["filter"]["gift_forget_duration"] = round(float(input_filter_gift_forget_duration.value), 2)
                config_data["filter"]["gift_forget_reserve_num"] = int(input_filter_gift_forget_reserve_num.value)
                config_data["filter"]["entrance_forget_duration"] = round(float(input_filter_entrance_forget_duration.value), 2)
                config_data["filter"]["entrance_forget_reserve_num"] = int(input_filter_entrance_forget_reserve_num.value)
                config_data["filter"]["follow_forget_duration"] = round(float(input_filter_follow_forget_duration.value), 2)
                config_data["filter"]["follow_forget_reserve_num"] = int(input_filter_follow_forget_reserve_num.value)
                config_data["filter"]["talk_forget_duration"] = round(float(input_filter_talk_forget_duration.value), 2)
                config_data["filter"]["talk_forget_reserve_num"] = int(input_filter_talk_forget_reserve_num.value)
                config_data["filter"]["schedule_forget_duration"] = round(float(input_filter_schedule_forget_duration.value), 2)
                config_data["filter"]["schedule_forget_reserve_num"] = int(input_filter_schedule_forget_reserve_num.value)

                # 答谢
                config_data["thanks"]["username_max_len"] = int(input_thanks_username_max_len.value)
                config_data["thanks"]["entrance_enable"] = switch_thanks_entrance_enable.value
                config_data["thanks"]["entrance_random"] = switch_thanks_entrance_random.value
                config_data["thanks"]["entrance_copy"] = common_textarea_handle(textarea_thanks_entrance_copy.value)
                config_data["thanks"]["gift_enable"] = switch_thanks_gift_enable.value
                config_data["thanks"]["gift_random"] = switch_thanks_gift_random.value
                config_data["thanks"]["gift_copy"] = common_textarea_handle(textarea_thanks_gift_copy.value)
                config_data["thanks"]["lowest_price"] = round(float(input_thanks_lowest_price.value), 2)
                config_data["thanks"]["follow_enable"] = switch_thanks_follow_enable.value
                config_data["thanks"]["follow_random"] = switch_thanks_follow_random.value
                config_data["thanks"]["follow_copy"] = common_textarea_handle(textarea_thanks_follow_copy.value)

                # 音频随机变速
                config_data["audio_random_speed"]["normal"]["enable"] = switch_audio_random_speed_normal_enable.value
                config_data["audio_random_speed"]["normal"]["speed_min"] = round(float(input_audio_random_speed_normal_speed_min.value), 2)
                config_data["audio_random_speed"]["normal"]["speed_max"] = round(float(input_audio_random_speed_normal_speed_max.value), 2)
                config_data["audio_random_speed"]["copywriting"]["enable"] = switch_audio_random_speed_copywriting_enable.value
                config_data["audio_random_speed"]["copywriting"]["speed_min"] = round(float(input_audio_random_speed_copywriting_speed_min.value), 2)
                config_data["audio_random_speed"]["copywriting"]["speed_max"] = round(float(input_audio_random_speed_copywriting_speed_max.value), 2)

                # 点歌模式
                config_data["choose_song"]["enable"] = switch_choose_song_enable.value
                config_data["choose_song"]["start_cmd"] = common_textarea_handle(textarea_choose_song_start_cmd.value)
                config_data["choose_song"]["stop_cmd"] = common_textarea_handle(textarea_choose_song_stop_cmd.value)
                config_data["choose_song"]["random_cmd"] = common_textarea_handle(textarea_choose_song_random_cmd.value)
                config_data["choose_song"]["song_path"] = input_choose_song_song_path.value
                config_data["choose_song"]["match_fail_copy"] = input_choose_song_match_fail_copy.value
                config_data["choose_song"]["similarity"] = round(float(input_choose_song_similarity.value), 2)

                # 定时任务
                tmp_arr = []
                # logging.info(schedule_var)
                for index in range(len(schedule_var) // 3):
                    tmp_json = {
                        "enable": False,
                        "time": 60,
                        "copy": []
                    }
                    tmp_json["enable"] = schedule_var[str(3 * index)].value
                    tmp_json["time"] = round(float(schedule_var[str(3 * index + 1)].value), 1)
                    tmp_json["copy"] = common_textarea_handle(schedule_var[str(3 * index + 2)].value)

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["schedule"] = tmp_arr

                # 闲时任务
                config_data["idle_time_task"]["enable"] = switch_idle_time_task_enable.value
                config_data["idle_time_task"]["idle_time"] = input_idle_time_task_idle_time.value
                config_data["idle_time_task"]["random_time"] = switch_idle_time_task_random_time.value
                config_data["idle_time_task"]["comment"]["enable"] = switch_idle_time_task_comment_enable.value
                config_data["idle_time_task"]["comment"]["random"] = switch_idle_time_task_comment_random.value
                config_data["idle_time_task"]["comment"]["copy"] = common_textarea_handle(textarea_idle_time_task_comment_copy.value)
                config_data["idle_time_task"]["local_audio"]["enable"] = switch_idle_time_task_local_audio_enable.value
                config_data["idle_time_task"]["local_audio"]["random"] = switch_idle_time_task_local_audio_random.value
                config_data["idle_time_task"]["local_audio"]["path"] = common_textarea_handle(textarea_idle_time_task_local_audio_path.value)

                # SD
                config_data["sd"]["enable"] = switch_sd_enable.value
                config_data["sd"]["translate_type"] = select_sd_translate_type.value
                config_data["sd"]["prompt_llm"]["type"] = select_sd_prompt_llm_type.value
                config_data["sd"]["prompt_llm"]["before_prompt"] = input_sd_prompt_llm_before_prompt.value
                config_data["sd"]["prompt_llm"]["after_prompt"] = input_sd_prompt_llm_after_prompt.value
                config_data["sd"]["trigger"] = input_sd_trigger.value
                config_data["sd"]["ip"] = input_sd_ip.value
                sd_port = input_sd_port.value
                config_data["sd"]["port"] = int(sd_port)
                config_data["sd"]["negative_prompt"] = input_sd_negative_prompt.value
                config_data["sd"]["seed"] = float(input_sd_seed.value)
                # 获取多行文本输入框的内容
                config_data["sd"]["styles"] = common_textarea_handle(textarea_sd_styles.value)
                config_data["sd"]["cfg_scale"] = int(input_sd_cfg_scale.value)
                config_data["sd"]["steps"] = int(input_sd_steps.value)
                config_data["sd"]["hr_resize_x"] = int(input_sd_hr_resize_x.value)
                config_data["sd"]["hr_resize_y"] = int(input_sd_hr_resize_y.value)
                config_data["sd"]["enable_hr"] = switch_sd_enable_hr.value
                config_data["sd"]["hr_scale"] = int(input_sd_hr_scale.value)
                config_data["sd"]["hr_second_pass_steps"] = int(input_sd_hr_second_pass_steps.value)
                config_data["sd"]["denoising_strength"] = round(float(input_sd_denoising_strength.value), 1)
                config_data["sd"]["save_enable"] = switch_sd_save_enable.value
                config_data["sd"]["loop_cover"] = switch_sd_loop_cover.value
                config_data["sd"]["save_path"] = input_sd_save_path.value

                # 动态文案
                config_data["trends_copywriting"]["enable"] = switch_trends_copywriting_enable.value
                config_data["trends_copywriting"]["random_play"] = switch_trends_copywriting_random_play.value
                config_data["trends_copywriting"]["play_interval"] = int(input_trends_copywriting_play_interval.value)
                tmp_arr = []
                for index in range(len(trends_copywriting_copywriting_var) // 3):
                    tmp_json = {
                        "folder_path": "",
                        "prompt_change_enable": False,
                        "prompt_change_content": ""
                    }
                    tmp_json["folder_path"] = trends_copywriting_copywriting_var[str(3 * index)].value
                    tmp_json["prompt_change_enable"] = trends_copywriting_copywriting_var[str(3 * index + 1)].value
                    tmp_json["prompt_change_content"] = trends_copywriting_copywriting_var[str(3 * index + 2)].value

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["trends_copywriting"]["copywriting"] = tmp_arr

                # web字幕打印机
                config_data["web_captions_printer"]["enable"] = switch_web_captions_printer_enable.value
                config_data["web_captions_printer"]["api_ip_port"] = input_web_captions_printer_api_ip_port.value

                # 数据库
                config_data["database"]["path"] = input_database_path.value
                config_data["database"]["comment_enable"] = switch_database_comment_enable.value
                config_data["database"]["entrance_enable"] = switch_database_entrance_enable.value
                config_data["database"]["gift_enable"] = switch_database_gift_enable.value

                # 按键映射
                config_data["key_mapping"]["enable"] = switch_key_mapping_enable.value
                config_data["key_mapping"]["type"] = select_key_mapping_type.value
                # logging.info(select_key_mapping_type.value)
                config_data["key_mapping"]["start_cmd"] = input_key_mapping_start_cmd.value
                tmp_arr = []
                # logging.info(key_mapping_config_var)
                for index in range(len(key_mapping_config_var) // 4):
                    tmp_json = {
                        "keywords": [],
                        "gift": [],
                        "keys": [],
                        "similarity": 1
                    }
                    tmp_json["keywords"] = common_textarea_handle(key_mapping_config_var[str(4 * index)].value)
                    tmp_json["gift"] = common_textarea_handle(key_mapping_config_var[str(4 * index + 1)].value)
                    tmp_json["keys"] = common_textarea_handle(key_mapping_config_var[str(4 * index + 2)].value)
                    tmp_json["similarity"] = key_mapping_config_var[str(4 * index + 3)].value

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["key_mapping"]["config"] = tmp_arr

                # 动态配置
                config_data["trends_config"]["enable"] = switch_trends_config_enable.value
                tmp_arr = []
                # logging.info(trends_config_path_var)
                for index in range(len(trends_config_path_var) // 2):
                    tmp_json = {
                        "online_num": "0-999999999",
                        "path": "config.json"
                    }
                    tmp_json["online_num"] = trends_config_path_var[str(2 * index)].value
                    tmp_json["path"] = trends_config_path_var[str(2 * index + 1)].value

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["trends_config"]["path"] = tmp_arr

                # 异常报警
                config_data["abnormal_alarm"]["platform"]["enable"] = switch_abnormal_alarm_platform_enable.value
                config_data["abnormal_alarm"]["platform"]["type"] = select_abnormal_alarm_platform_type.value
                config_data["abnormal_alarm"]["platform"]["start_alarm_error_num"] = int(input_abnormal_alarm_platform_start_alarm_error_num.value)
                config_data["abnormal_alarm"]["platform"]["auto_restart_error_num"] = int(input_abnormal_alarm_platform_auto_restart_error_num.value)
                config_data["abnormal_alarm"]["platform"]["local_audio_path"] = input_abnormal_alarm_platform_local_audio_path.value
                config_data["abnormal_alarm"]["llm"]["enable"] = switch_abnormal_alarm_llm_enable.value
                config_data["abnormal_alarm"]["llm"]["type"] = select_abnormal_alarm_llm_type.value
                config_data["abnormal_alarm"]["llm"]["start_alarm_error_num"] = int(input_abnormal_alarm_llm_start_alarm_error_num.value)
                config_data["abnormal_alarm"]["llm"]["auto_restart_error_num"] = int(input_abnormal_alarm_llm_auto_restart_error_num.value)
                config_data["abnormal_alarm"]["llm"]["local_audio_path"] = input_abnormal_alarm_llm_local_audio_path.value
                config_data["abnormal_alarm"]["tts"]["enable"] = switch_abnormal_alarm_tts_enable.value
                config_data["abnormal_alarm"]["tts"]["type"] = select_abnormal_alarm_tts_type.value
                config_data["abnormal_alarm"]["tts"]["start_alarm_error_num"] = int(input_abnormal_alarm_tts_start_alarm_error_num.value)
                config_data["abnormal_alarm"]["tts"]["auto_restart_error_num"] = int(input_abnormal_alarm_tts_auto_restart_error_num.value)
                config_data["abnormal_alarm"]["tts"]["local_audio_path"] = input_abnormal_alarm_tts_local_audio_path.value
                config_data["abnormal_alarm"]["svc"]["enable"] = switch_abnormal_alarm_svc_enable.value
                config_data["abnormal_alarm"]["svc"]["type"] = select_abnormal_alarm_svc_type.value
                config_data["abnormal_alarm"]["svc"]["start_alarm_error_num"] = int(input_abnormal_alarm_svc_start_alarm_error_num.value)
                config_data["abnormal_alarm"]["svc"]["auto_restart_error_num"] = int(input_abnormal_alarm_svc_auto_restart_error_num.value)
                config_data["abnormal_alarm"]["svc"]["local_audio_path"] = input_abnormal_alarm_svc_local_audio_path.value
                config_data["abnormal_alarm"]["visual_body"]["enable"] = switch_abnormal_alarm_visual_body_enable.value
                config_data["abnormal_alarm"]["visual_body"]["type"] = select_abnormal_alarm_visual_body_type.value
                config_data["abnormal_alarm"]["visual_body"]["start_alarm_error_num"] = int(input_abnormal_alarm_visual_body_start_alarm_error_num.value)
                config_data["abnormal_alarm"]["visual_body"]["auto_restart_error_num"] = int(input_abnormal_alarm_visual_body_auto_restart_error_num.value)
                config_data["abnormal_alarm"]["visual_body"]["local_audio_path"] = input_abnormal_alarm_visual_body_local_audio_path.value
                config_data["abnormal_alarm"]["other"]["enable"] = switch_abnormal_alarm_other_enable.value
                config_data["abnormal_alarm"]["other"]["type"] = select_abnormal_alarm_other_type.value
                config_data["abnormal_alarm"]["other"]["start_alarm_error_num"] = int(input_abnormal_alarm_other_start_alarm_error_num.value)
                config_data["abnormal_alarm"]["other"]["auto_restart_error_num"] = int(input_abnormal_alarm_other_auto_restart_error_num.value)
                config_data["abnormal_alarm"]["other"]["local_audio_path"] = input_abnormal_alarm_other_local_audio_path.value

            """
            LLM
            """
            if True:
                config_data["openai"]["api"] = input_openai_api.value
                config_data["openai"]["api_key"] = common_textarea_handle(textarea_openai_api_key.value)
                # logging.info(select_chatgpt_model.value)
                config_data["chatgpt"]["model"] = select_chatgpt_model.value
                config_data["chatgpt"]["temperature"] = round(float(input_chatgpt_temperature.value), 1)
                config_data["chatgpt"]["max_tokens"] = int(input_chatgpt_max_tokens.value)
                config_data["chatgpt"]["top_p"] = round(float(input_chatgpt_top_p.value), 1)
                config_data["chatgpt"]["presence_penalty"] = round(float(input_chatgpt_presence_penalty.value), 1)
                config_data["chatgpt"]["frequency_penalty"] = round(float(input_chatgpt_frequency_penalty.value), 1)
                config_data["chatgpt"]["preset"] = input_chatgpt_preset.value

                config_data["claude"]["slack_user_token"] = input_claude_slack_user_token.value
                config_data["claude"]["bot_user_id"] = input_claude_bot_user_id.value

                config_data["claude2"]["cookie"] = input_claude2_cookie.value
                config_data["claude2"]["use_proxy"] = switch_claude2_use_proxy.value
                config_data["claude2"]["proxies"]["http"] = input_claude2_proxies_http.value
                config_data["claude2"]["proxies"]["https"] = input_claude2_proxies_https.value
                config_data["claude2"]["proxies"]["socks5"] = input_claude2_proxies_socks5.value

                config_data["chatglm"]["api_ip_port"] = input_chatglm_api_ip_port.value
                config_data["chatglm"]["max_length"] = int(input_chatglm_max_length.value)
                config_data["chatglm"]["top_p"] = round(float(input_chatglm_top_p.value), 1)
                config_data["chatglm"]["temperature"] = round(float(input_chatglm_temperature.value), 2)
                config_data["chatglm"]["history_enable"] = switch_chatglm_history_enable.value
                config_data["chatglm"]["history_max_len"] = int(input_chatglm_history_max_len.value)

                config_data["alice"]["api_ip_port"] = input_alice_api_ip_port.value
                config_data["alice"]["max_length"] = int(input_alice_max_length.value)
                config_data["alice"]["top_p"] = round(float(input_alice_top_p.value), 1)
                config_data["alice"]["temperature"] = round(float(input_alice_temperature.value), 2)
                config_data["alice"]["history_enable"] = switch_alice_history_enable.value
                config_data["alice"]["history_max_len"] = int(input_alice_history_max_len.value)
                config_data["alice"]["preset"] = input_alice_preset.value

                config_data["chat_with_file"]["chat_mode"] = select_chat_with_file_chat_mode.value
                config_data["chat_with_file"]["data_path"] = input_chat_with_file_data_path.value
                config_data["chat_with_file"]["separator"] = input_chat_with_file_separator.value
                config_data["chat_with_file"]["chunk_size"] = int(input_chat_with_file_chunk_size.value)
                config_data["chat_with_file"]["chunk_overlap"] = int(input_chat_with_file_chunk_overlap.value)
                config_data["chat_with_file"]["local_vector_embedding_model"] = select_chat_with_file_local_vector_embedding_model.value
                config_data["chat_with_file"]["chain_type"] = input_chat_with_file_chain_type.value
                config_data["chat_with_file"]["question_prompt"] = input_chat_with_file_question_prompt.value
                config_data["chat_with_file"]["local_max_query"] = int(input_chat_with_file_local_max_query.value)
                config_data["chat_with_file"]["show_token_cost"] = switch_chat_with_file_show_token_cost.value

                config_data["chatterbot"]["name"] = input_chatterbot_name.value
                config_data["chatterbot"]["db_path"] = input_chatterbot_db_path.value

                config_data["text_generation_webui"]["type"] = select_text_generation_webui_type.value
                config_data["text_generation_webui"]["api_ip_port"] = input_text_generation_webui_api_ip_port.value
                config_data["text_generation_webui"]["max_new_tokens"] = int(input_text_generation_webui_max_new_tokens.value)
                config_data["text_generation_webui"]["history_enable"] = switch_text_generation_webui_history_enable.value
                config_data["text_generation_webui"]["history_max_len"] = int(input_text_generation_webui_history_max_len.value)
                config_data["text_generation_webui"]["mode"] = select_text_generation_webui_mode.value
                config_data["text_generation_webui"]["character"] = input_text_generation_webui_character.value
                config_data["text_generation_webui"]["instruction_template"] = input_text_generation_webui_instruction_template.value
                config_data["text_generation_webui"]["your_name"] = input_text_generation_webui_your_name.value
                config_data["text_generation_webui"]["top_p"] = round(float(input_text_generation_webui_top_p.value), 2)
                config_data["text_generation_webui"]["top_k"] = int(input_text_generation_webui_top_k.value)
                config_data["text_generation_webui"]["temperature"] = round(float(input_text_generation_webui_temperature.value), 2)
                config_data["text_generation_webui"]["seed"] = float(input_text_generation_webui_seed.value)

                config_data["sparkdesk"]["type"] = select_sparkdesk_type.value
                config_data["sparkdesk"]["cookie"] = input_sparkdesk_cookie.value
                config_data["sparkdesk"]["fd"] = input_sparkdesk_fd.value
                config_data["sparkdesk"]["GtToken"] = input_sparkdesk_GtToken.value
                config_data["sparkdesk"]["app_id"] = input_sparkdesk_app_id.value
                config_data["sparkdesk"]["api_secret"] = input_sparkdesk_api_secret.value
                config_data["sparkdesk"]["api_key"] = input_sparkdesk_api_key.value
                config_data["sparkdesk"]["version"] = round(float(select_sparkdesk_version.value), 1)

                config_data["langchain_chatglm"]["api_ip_port"] = input_langchain_chatglm_api_ip_port.value
                config_data["langchain_chatglm"]["chat_type"] = select_langchain_chatglm_chat_type.value
                config_data["langchain_chatglm"]["knowledge_base_id"] = input_langchain_chatglm_knowledge_base_id.value
                config_data["langchain_chatglm"]["history_enable"] = switch_langchain_chatglm_history_enable.value
                config_data["langchain_chatglm"]["history_max_len"] = int(input_langchain_chatglm_history_max_len.value)

                config_data["langchain_chatchat"]["api_ip_port"] = input_langchain_chatchat_api_ip_port.value
                config_data["langchain_chatchat"]["chat_type"] = select_langchain_chatchat_chat_type.value
                config_data["langchain_chatchat"]["history_enable"] = switch_langchain_chatchat_history_enable.value
                config_data["langchain_chatchat"]["history_max_len"] = int(input_langchain_chatchat_history_max_len.value)
                config_data["langchain_chatchat"]["llm"]["model_name"] = input_langchain_chatchat_llm_model_name.value
                config_data["langchain_chatchat"]["llm"]["temperature"] = round(float(input_langchain_chatchat_llm_temperature.value), 2)
                config_data["langchain_chatchat"]["llm"]["max_tokens"] = int(input_langchain_chatchat_llm_max_tokens.value)
                config_data["langchain_chatchat"]["llm"]["prompt_name"] = input_langchain_chatchat_llm_prompt_name.value
                config_data["langchain_chatchat"]["knowledge_base"]["knowledge_base_name"] = input_langchain_chatchat_knowledge_base_knowledge_base_name.value
                config_data["langchain_chatchat"]["knowledge_base"]["top_k"] = int(input_langchain_chatchat_knowledge_base_top_k.value)
                config_data["langchain_chatchat"]["knowledge_base"]["score_threshold"] = round(float(input_langchain_chatchat_knowledge_base_score_threshold.value), 2)
                config_data["langchain_chatchat"]["knowledge_base"]["model_name"] = input_langchain_chatchat_knowledge_base_model_name.value
                config_data["langchain_chatchat"]["knowledge_base"]["temperature"] = round(float(input_langchain_chatchat_knowledge_base_temperature.value), 2)
                config_data["langchain_chatchat"]["knowledge_base"]["max_tokens"] = int(input_langchain_chatchat_knowledge_base_max_tokens.value)
                config_data["langchain_chatchat"]["knowledge_base"]["prompt_name"] = input_langchain_chatchat_knowledge_base_prompt_name.value
                config_data["langchain_chatchat"]["search_engine"]["search_engine_name"] = select_langchain_chatchat_search_engine_search_engine_name.value
                config_data["langchain_chatchat"]["search_engine"]["top_k"] = int(input_langchain_chatchat_search_engine_top_k.value)
                config_data["langchain_chatchat"]["search_engine"]["model_name"] = input_langchain_chatchat_search_engine_model_name.value
                config_data["langchain_chatchat"]["search_engine"]["temperature"] = round(float(input_langchain_chatchat_search_engine_temperature.value), 2)
                config_data["langchain_chatchat"]["search_engine"]["max_tokens"] = int(input_langchain_chatchat_search_engine_max_tokens.value)
                config_data["langchain_chatchat"]["search_engine"]["prompt_name"] = input_langchain_chatchat_search_engine_prompt_name.value


                config_data["zhipu"]["api_key"] = input_zhipu_api_key.value
                config_data["zhipu"]["model"] = select_zhipu_model.value
                config_data["zhipu"]["top_p"] = input_zhipu_top_p.value
                config_data["zhipu"]["temperature"] = input_zhipu_temperature.value
                config_data["zhipu"]["history_enable"] = switch_zhipu_history_enable.value
                config_data["zhipu"]["history_max_len"] = input_zhipu_history_max_len.value
                config_data["zhipu"]["user_info"] = input_zhipu_user_info.value
                config_data["zhipu"]["bot_info"] = input_zhipu_bot_info.value
                config_data["zhipu"]["bot_name"] = input_zhipu_bot_name.value
                config_data["zhipu"]["user_name"] = input_zhipu_user_name.value
                config_data["zhipu"]["remove_useless"] = switch_zhipu_remove_useless.value

                config_data["bard"]["token"] = input_bard_token.value

                config_data["yiyan"]["type"] = select_yiyan_type.value
                config_data["yiyan"]["history_enable"] = switch_yiyan_history_enable.value
                config_data["yiyan"]["history_max_len"] = int(input_yiyan_history_max_len.value)
                config_data["yiyan"]["api"]["api_key"] = input_yiyan_api_api_key.value
                config_data["yiyan"]["api"]["secret_key"] = input_yiyan_api_secret_key.value
                config_data["yiyan"]["web"]["api_ip_port"] = input_yiyan_web_api_ip_port.value
                config_data["yiyan"]["web"]["cookie"] = input_yiyan_web_cookie.value

                config_data["tongyi"]["type"] = select_tongyi_type.value
                config_data["tongyi"]["cookie_path"] = input_tongyi_cookie_path.value

                config_data["tongyixingchen"]["access_token"] = input_tongyixingchen_access_token.value
                config_data["tongyixingchen"]["type"] = select_tongyixingchen_type.value
                config_data["tongyixingchen"]["history_enable"] = switch_tongyixingchen_history_enable.value
                config_data["tongyixingchen"]["history_max_len"] = input_tongyixingchen_history_max_len.value
                config_data["tongyixingchen"]["固定角色"]["character_id"] = input_tongyixingchen_GDJS_character_id.value
                config_data["tongyixingchen"]["固定角色"]["top_p"] = round(float(input_tongyixingchen_GDJS_top_p.value), 2)
                config_data["tongyixingchen"]["固定角色"]["temperature"] = round(float(input_tongyixingchen_GDJS_temperature.value), 2)
                config_data["tongyixingchen"]["固定角色"]["seed"] = int(input_tongyixingchen_GDJS_seed.value)
                config_data["tongyixingchen"]["固定角色"]["user_id"] = input_tongyixingchen_GDJS_user_id.value
                config_data["tongyixingchen"]["固定角色"]["user_name"] = input_tongyixingchen_GDJS_user_name.value
                config_data["tongyixingchen"]["固定角色"]["role_name"] = input_tongyixingchen_GDJS_role_name.value

                # config_data["my_qianfan"]["model"] = select_my_qianfan_model.value
                # config_data["my_qianfan"]["access_key"] = input_my_qianfan_access_key.value
                # config_data["my_qianfan"]["secret_key"] = input_my_qianfan_secret_key.value
                # config_data["my_qianfan"]["top_p"] = round(float(input_my_qianfan_top_p.value), 2)
                # config_data["my_qianfan"]["temperature"] = round(float(input_my_qianfan_temperature.value), 2)
                # config_data["my_qianfan"]["penalty_score"] = round(float(input_my_qianfan_penalty_score.value), 2)
                # config_data["my_qianfan"]["history_enable"] = switch_my_qianfan_history_enable.value
                # config_data["my_qianfan"]["history_max_len"] = int(input_my_qianfan_history_max_len.value)

                config_data["my_wenxinworkshop"]["model"] = select_my_wenxinworkshop_model.value
                config_data["my_wenxinworkshop"]["api_key"] = input_my_wenxinworkshop_api_key.value
                config_data["my_wenxinworkshop"]["secret_key"] = input_my_wenxinworkshop_secret_key.value
                config_data["my_wenxinworkshop"]["top_p"] = round(float(input_my_wenxinworkshop_top_p.value), 2)
                config_data["my_wenxinworkshop"]["temperature"] = round(float(input_my_wenxinworkshop_temperature.value), 2)
                config_data["my_wenxinworkshop"]["penalty_score"] = round(float(input_my_wenxinworkshop_penalty_score.value), 2)
                config_data["my_wenxinworkshop"]["history_enable"] = switch_my_wenxinworkshop_history_enable.value
                config_data["my_wenxinworkshop"]["history_max_len"] = int(input_my_wenxinworkshop_history_max_len.value)

                config_data["gemini"]["api_key"] = input_gemini_api_key.value
                config_data["gemini"]["model"] = select_gemini_model.value
                config_data["gemini"]["history_enable"] = switch_gemini_history_enable.value
                config_data["gemini"]["history_max_len"] = int(input_gemini_history_max_len.value)
                config_data["gemini"]["http_proxy"] = input_gemini_http_proxy.value
                config_data["gemini"]["https_proxy"] = input_gemini_https_proxy.value
                config_data["gemini"]["max_output_tokens"] = int(input_gemini_max_output_tokens.value)
                config_data["gemini"]["temperature"] = round(float(input_gemini_max_temperature.value), 2)
                config_data["gemini"]["top_p"] = round(float(input_gemini_top_p.value), 2)
                config_data["gemini"]["top_k"] = int(input_gemini_top_k.value)

            """
            TTS
            """
            if True:
                config_data["edge-tts"]["voice"] = select_edge_tts_voice.value
                config_data["edge-tts"]["rate"] = input_edge_tts_rate.value
                config_data["edge-tts"]["volume"] = input_edge_tts_volume.value

                config_data["vits"]["type"] = select_vits_type.value
                config_data["vits"]["config_path"] = input_vits_config_path.value
                config_data["vits"]["api_ip_port"] = input_vits_api_ip_port.value
                config_data["vits"]["id"] = input_vits_id.value
                config_data["vits"]["lang"] = select_vits_lang.value
                config_data["vits"]["length"] = input_vits_length.value
                config_data["vits"]["noise"] = input_vits_noise.value
                config_data["vits"]["noisew"] = input_vits_noisew.value
                config_data["vits"]["max"] = input_vits_max.value
                config_data["vits"]["format"] = input_vits_format.value
                config_data["vits"]["sdp_radio"] = input_vits_sdp_radio.value

                config_data["bert_vits2"]["type"] = select_bert_vits2_type.value
                config_data["bert_vits2"]["api_ip_port"] = input_bert_vits2_api_ip_port.value
                config_data["bert_vits2"]["model_id"] = int(input_vits_model_id.value)
                config_data["bert_vits2"]["speaker_name"] = input_vits_speaker_name.value
                config_data["bert_vits2"]["speaker_id"] = int(input_vits_speaker_id.value)
                config_data["bert_vits2"]["language"] = select_bert_vits2_language.value
                config_data["bert_vits2"]["length"] = round(float(input_bert_vits2_length.value), 2)
                config_data["bert_vits2"]["noise"] = round(float(input_bert_vits2_noise.value), 2)
                config_data["bert_vits2"]["noisew"] = round(float(input_bert_vits2_noisew.value), 2)
                config_data["bert_vits2"]["sdp_radio"] = round(float(input_bert_vits2_sdp_radio.value), 2)
                config_data["bert_vits2"]["emotion"] = input_bert_vits2_emotion.value
                config_data["bert_vits2"]["style_text"] = input_bert_vits2_style_text.value
                config_data["bert_vits2"]["style_weight"] = round(float(input_bert_vits2_style_weight.value), 2)
                config_data["bert_vits2"]["auto_translate"] = switch_bert_vits2_auto_translate.value
                config_data["bert_vits2"]["auto_split"] = switch_bert_vits2_auto_split.value

                config_data["vits_fast"]["config_path"] = input_vits_fast_config_path.value
                config_data["vits_fast"]["api_ip_port"] = input_vits_fast_api_ip_port.value
                config_data["vits_fast"]["character"] = input_vits_fast_character.value
                config_data["vits_fast"]["language"] = select_vits_fast_language.value
                config_data["vits_fast"]["speed"] = input_vits_fast_speed.value
                
                config_data["elevenlabs"]["api_key"] = input_elevenlabs_api_key.value
                config_data["elevenlabs"]["voice"] = input_elevenlabs_voice.value
                config_data["elevenlabs"]["model"] = input_elevenlabs_model.value

                config_data["genshinvoice_top"]["speaker"] = select_genshinvoice_top_speaker.value
                config_data["genshinvoice_top"]["noise"] = input_genshinvoice_top_noise.value
                config_data["genshinvoice_top"]["noisew"] = input_genshinvoice_top_noisew.value
                config_data["genshinvoice_top"]["length"] = input_genshinvoice_top_length.value
                config_data["genshinvoice_top"]["format"] = input_genshinvoice_top_format.value
                config_data["genshinvoice_top"]["language"] = select_genshinvoice_top_language.value

                config_data["tts_ai_lab_top"]["speaker"] = select_tts_ai_lab_top_speaker.value
                config_data["tts_ai_lab_top"]["appid"] = input_tts_ai_lab_top_appid.value
                config_data["tts_ai_lab_top"]["token"] = input_tts_ai_lab_top_token.value
                config_data["tts_ai_lab_top"]["noise"] = input_tts_ai_lab_top_noise.value
                config_data["tts_ai_lab_top"]["noisew"] = input_tts_ai_lab_top_noisew.value
                config_data["tts_ai_lab_top"]["length"] = input_tts_ai_lab_top_length.value
                config_data["tts_ai_lab_top"]["sdp_ratio"] = input_tts_ai_lab_top_sdp_ratio.value

                config_data["bark_gui"]["api_ip_port"] = input_bark_gui_api_ip_port.value
                config_data["bark_gui"]["spk"] = input_bark_gui_spk.value
                config_data["bark_gui"]["generation_temperature"] = input_bark_gui_generation_temperature.value
                config_data["bark_gui"]["waveform_temperature"] = input_bark_gui_waveform_temperature.value
                config_data["bark_gui"]["end_of_sentence_probability"] = input_bark_gui_end_of_sentence_probability.value
                config_data["bark_gui"]["quick_generation"] = switch_bark_gui_quick_generation.value
                config_data["bark_gui"]["seed"] = input_bark_gui_seed.value
                config_data["bark_gui"]["batch_count"] = input_bark_gui_batch_count.value

                config_data["vall_e_x"]["api_ip_port"] = input_vall_e_x_api_ip_port.value
                config_data["vall_e_x"]["language"] = select_vall_e_x_language.value
                config_data["vall_e_x"]["accent"] = select_vall_e_x_accent.value
                config_data["vall_e_x"]["voice_preset"] = input_vall_e_x_voice_preset.value
                config_data["vall_e_x"]["voice_preset_file_path"] = input_vall_e_x_voice_preset_file_path.value

                config_data["openai_tts"]["type"] = select_openai_tts_type.value
                config_data["openai_tts"]["api_ip_port"] = input_openai_tts_api_ip_port.value
                config_data["openai_tts"]["model"] = select_openai_tts_model.value
                config_data["openai_tts"]["voice"] = select_openai_tts_voice.value
                config_data["openai_tts"]["api_key"] = input_openai_tts_api_key.value
                
                config_data["reecho_ai"]["Authorization"] = input_reecho_ai_Authorization.value
                config_data["reecho_ai"]["model"] = input_reecho_ai_model.value
                config_data["reecho_ai"]["voiceId"] = input_reecho_ai_voiceId.value
                config_data["reecho_ai"]["randomness"] = int(number_reecho_ai_randomness.value)
                config_data["reecho_ai"]["stability_boost"] = int(number_reecho_ai_stability_boost.value)

                config_data["gradio_tts"]["request_parameters"] = textarea_gradio_tts_request_parameters.value

                config_data["gpt_sovits"]["api_ip_port"] = input_gpt_sovits_api_ip_port.value
                config_data["gpt_sovits"]["ref_audio_path"] = input_gpt_sovits_ref_audio_path.value
                config_data["gpt_sovits"]["prompt_text"] = input_gpt_sovits_prompt_text.value
                config_data["gpt_sovits"]["prompt_language"] = select_gpt_sovits_prompt_language.value
                config_data["gpt_sovits"]["language"] = select_gpt_sovits_language.value
        
            """
            SVC
            """
            if True:
                config_data["ddsp_svc"]["enable"] = switch_ddsp_svc_enable.value
                config_data["ddsp_svc"]["config_path"] = input_ddsp_svc_config_path.value
                config_data["ddsp_svc"]["api_ip_port"] = input_ddsp_svc_api_ip_port.value
                config_data["ddsp_svc"]["fSafePrefixPadLength"] = round(float(input_ddsp_svc_fSafePrefixPadLength.value), 1)
                config_data["ddsp_svc"]["fPitchChange"] = round(float(input_ddsp_svc_fPitchChange.value), 1)
                config_data["ddsp_svc"]["sSpeakId"] = int(input_ddsp_svc_sSpeakId.value)
                config_data["ddsp_svc"]["sampleRate"] = int(input_ddsp_svc_sampleRate.value)

                config_data["so_vits_svc"]["enable"] = switch_so_vits_svc_enable.value
                config_data["so_vits_svc"]["config_path"] = input_so_vits_svc_config_path.value
                config_data["so_vits_svc"]["api_ip_port"] = input_so_vits_svc_api_ip_port.value
                config_data["so_vits_svc"]["spk"] = input_so_vits_svc_spk.value
                config_data["so_vits_svc"]["tran"] = round(float(input_so_vits_svc_tran.value), 1)
                config_data["so_vits_svc"]["wav_format"] = input_so_vits_svc_wav_format.value

            """
            虚拟身体
            """
            if True:
                config_data["live2d"]["enable"] = switch_live2d_enable.value
                config_data["live2d"]["port"] = int(input_live2d_port.value)
                # config_data["live2d"]["name"] = input_live2d_name.value
                
                config_data["xuniren"]["api_ip_port"] = input_xuniren_api_ip_port.value

                # config_data["unity"]["enable"] = switch_unity_enable.value
                config_data["unity"]["api_ip_port"] = input_unity_api_ip_port.value
                config_data["unity"]["password"] = input_unity_password.value
                    
            """
            文案
            """
            if True:
                config_data["copywriting"]["auto_play"] = switch_copywriting_auto_play.value
                config_data["copywriting"]["random_play"] = switch_copywriting_random_play.value
                config_data["copywriting"]["audio_interval"] = input_copywriting_audio_interval.value
                config_data["copywriting"]["switching_interval"] = input_copywriting_switching_interval.value
                config_data["copywriting"]["text_path"] = input_copywriting_text_path.value
                config_data["copywriting"]["audio_save_path"] = input_copywriting_audio_save_path.value
                
                tmp_arr = []
                # logging.info(copywriting_config_var)
                for index in range(len(copywriting_config_var) // 5):
                    tmp_json = {
                        "file_path": "",
                        "audio_path": "",
                        "continuous_play_num": 1,
                        "max_play_time": 10.0,
                        "play_list": []
                    }
                    tmp_json["file_path"] = copywriting_config_var[str(5 * index)].value
                    tmp_json["audio_path"] = copywriting_config_var[str(5 * index + 1)].value
                    tmp_json["continuous_play_num"] = int(copywriting_config_var[str(5 * index + 2)].value)
                    tmp_json["max_play_time"] = float(copywriting_config_var[str(5 * index + 3)].value)
                    tmp_json["play_list"] = common_textarea_handle(copywriting_config_var[str(5 * index + 4)].value)
                    

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["copywriting"]["config"] = tmp_arr

            """
            积分
            """
            if True:
                config_data["integral"]["enable"] = switch_integral_enable.value

                config_data["integral"]["sign"]["enable"] = switch_integral_sign_enable.value
                config_data["integral"]["sign"]["get_integral"] = int(input_integral_sign_get_integral.value)
                config_data["integral"]["sign"]["cmd"] = common_textarea_handle(textarea_integral_sign_cmd.value)
                tmp_arr = []
                # logging.info(integral_sign_copywriting_var)
                for index in range(len(integral_sign_copywriting_var) // 2):
                    tmp_json = {
                        "sign_num_interval": "",
                        "copywriting": []
                    }
                    tmp_json["sign_num_interval"] = integral_sign_copywriting_var[str(2 * index)].value
                    tmp_json["copywriting"] = common_textarea_handle(integral_sign_copywriting_var[str(2 * index + 1)].value)

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["integral"]["sign"]["copywriting"] = tmp_arr

                config_data["integral"]["gift"]["enable"] = switch_integral_gift_enable.value
                config_data["integral"]["gift"]["get_integral_proportion"] = float(input_integral_gift_get_integral_proportion.value)
                tmp_arr = []
                for index in range(len(integral_gift_copywriting_var) // 2):
                    tmp_json = {
                        "gift_price_interval": "",
                        "copywriting": []
                    }
                    tmp_json["gift_price_interval"] = integral_gift_copywriting_var[str(2 * index)].value
                    tmp_json["copywriting"] = common_textarea_handle(integral_gift_copywriting_var[str(2 * index + 1)].value)

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["integral"]["gift"]["copywriting"] = tmp_arr

                config_data["integral"]["entrance"]["enable"] = switch_integral_entrance_enable.value
                config_data["integral"]["entrance"]["get_integral"] = int(input_integral_entrance_get_integral.value)
                tmp_arr = []
                for index in range(len(integral_entrance_copywriting_var) // 2):
                    tmp_json = {
                        "entrance_num_interval": "",
                        "copywriting": []
                    }
                    tmp_json["entrance_num_interval"] = integral_entrance_copywriting_var[str(2 * index)].value
                    tmp_json["copywriting"] = common_textarea_handle(integral_entrance_copywriting_var[str(2 * index + 1)].value)

                    tmp_arr.append(tmp_json)
                # logging.info(tmp_arr)
                config_data["integral"]["entrance"]["copywriting"] = tmp_arr

                config_data["integral"]["crud"]["query"]["enable"] = switch_integral_crud_query_enable.value
                config_data["integral"]["crud"]["query"]["cmd"] = common_textarea_handle(textarea_integral_crud_query_cmd.value)
                config_data["integral"]["crud"]["query"]["copywriting"] = common_textarea_handle(textarea_integral_crud_query_copywriting.value)

            """
            聊天
            """
            if True:
                config_data["talk"]["key_listener_enable"] = switch_talk_key_listener_enable.value
                config_data["talk"]["device_index"] = select_talk_device_index.value
                config_data["talk"]["username"] = input_talk_username.value
                config_data["talk"]["continuous_talk"] = switch_talk_continuous_talk.value
                config_data["talk"]["trigger_key"] = select_talk_trigger_key.value
                config_data["talk"]["stop_trigger_key"] = select_talk_stop_trigger_key.value
                config_data["talk"]["volume_threshold"] = float(input_talk_volume_threshold.value)
                config_data["talk"]["silence_threshold"] = float(input_talk_silence_threshold.value)
                config_data["talk"]["CHANNELS"] = int(input_talk_silence_CHANNELS.value)
                config_data["talk"]["RATE"] = int(input_talk_silence_RATE.value)
                config_data["talk"]["type"] = select_talk_type.value
                config_data["talk"]["google"]["tgt_lang"] = select_talk_google_tgt_lang.value
                config_data["talk"]["baidu"]["app_id"] = input_talk_baidu_app_id.value
                config_data["talk"]["baidu"]["api_key"] = input_talk_baidu_api_key.value
                config_data["talk"]["baidu"]["secret_key"] = input_talk_baidu_secret_key.value
                config_data["talk"]["faster_whisper"]["model_size"] = input_faster_whisper_model_size.value
                config_data["talk"]["faster_whisper"]["device"] = select_faster_whisper_device.value
                config_data["talk"]["faster_whisper"]["compute_type"] = select_faster_whisper_compute_type.value
                config_data["talk"]["faster_whisper"]["download_root"] = input_faster_whisper_download_root.value
                config_data["talk"]["faster_whisper"]["beam_size"] = int(input_faster_whisper_beam_size.value)

            """
            助播
            """
            if True:
                config_data["assistant_anchor"]["enable"] = switch_assistant_anchor_enable.value
                config_data["assistant_anchor"]["username"] = input_assistant_anchor_username.value
                tmp_arr = []
                for index in range(len(assistant_anchor_type_var)):
                    if assistant_anchor_type_var[str(index)].value:
                        tmp_arr.append(assistant_anchor_type_var[str(index)].text)
                # logging.info(tmp_arr)
                config_data["assistant_anchor"]["type"] = tmp_arr
                config_data["assistant_anchor"]["local_qa"]["text"]["enable"] = switch_assistant_anchor_local_qa_text_enable.value
                local_qa_text_format = select_assistant_anchor_local_qa_text_format.value
                if local_qa_text_format == "自定义json":
                    config_data["assistant_anchor"]["local_qa"]["text"]["format"] = "json"
                elif local_qa_text_format == "一问一答":
                    config_data["assistant_anchor"]["local_qa"]["text"]["format"] = "text"
                config_data["assistant_anchor"]["local_qa"]["text"]["file_path"] = input_assistant_anchor_local_qa_text_file_path.value
                config_data["assistant_anchor"]["local_qa"]["text"]["similarity"] = round(float(input_assistant_anchor_local_qa_text_similarity.value), 2)
                config_data["assistant_anchor"]["local_qa"]["audio"]["enable"] = switch_assistant_anchor_local_qa_audio_enable.value
                config_data["assistant_anchor"]["local_qa"]["audio"]["type"] = select_assistant_anchor_local_qa_audio_type.value
                config_data["assistant_anchor"]["local_qa"]["audio"]["file_path"] = input_assistant_anchor_local_qa_audio_file_path.value
                config_data["assistant_anchor"]["local_qa"]["audio"]["similarity"] = round(float(input_assistant_anchor_local_qa_audio_similarity.value), 2)
            

            """
            翻译
            """
            if True:
                config_data["translate"]["enable"] = switch_translate_enable.value
                config_data["translate"]["type"] = select_translate_type.value
                config_data["translate"]["trans_type"] = select_translate_trans_type.value
                config_data["translate"]["baidu"]["appid"] = input_translate_baidu_appid.value
                config_data["translate"]["baidu"]["appkey"] = input_translate_baidu_appkey.value
                config_data["translate"]["baidu"]["from_lang"] = select_translate_baidu_from_lang.value
                config_data["translate"]["baidu"]["to_lang"] = select_translate_baidu_to_lang.value
                config_data["translate"]["google"]["proxy"] = input_translate_google_proxy.value
                config_data["translate"]["google"]["src_lang"] = select_translate_google_src_lang.value
                config_data["translate"]["google"]["tgt_lang"] = select_translate_google_tgt_lang.value

            """
            UI配置
            """
            if True:
                config_data["webui"]["title"] = input_webui_title.value
                config_data["webui"]["ip"] = input_webui_ip.value
                config_data["webui"]["port"] = int(input_webui_port.value)
                config_data["webui"]["auto_run"] = switch_webui_auto_run.value

                config_data["webui"]["show_card"]["read_comment"] = switch_webui_show_card_read_comment.value
                config_data["webui"]["show_card"]["read_user_name"] = switch_webui_show_card_read_user_name.value
                config_data["webui"]["show_card"]["filter"] = switch_webui_show_card_filter.value
                config_data["webui"]["show_card"]["thanks"] = switch_webui_show_card_thanks.value
                config_data["webui"]["show_card"]["live2d"] = switch_webui_show_card_live2d.value
                config_data["webui"]["show_card"]["audio_random_speed"] = switch_webui_show_card_audio_random_speed.value
                config_data["webui"]["show_card"]["so_vits_svc"] = switch_webui_show_card_so_vits_svc.value
                config_data["webui"]["show_card"]["ddsp_svc"] = switch_webui_show_card_ddsp_svc.value
                config_data["webui"]["show_card"]["local_qa"] = switch_webui_show_card_local_qa.value
                config_data["webui"]["show_card"]["choose_song"] = switch_webui_show_card_choose_song.value
                config_data["webui"]["show_card"]["sd"] = switch_webui_show_card_sd.value
                config_data["webui"]["show_card"]["log"] = switch_webui_show_card_log.value
                config_data["webui"]["show_card"]["schedule"] = switch_webui_show_card_schedule.value
                config_data["webui"]["show_card"]["idle_time_task"] = switch_webui_show_card_idle_time_task.value
                config_data["webui"]["show_card"]["database"] = switch_webui_show_card_database.value
                config_data["webui"]["show_card"]["play_audio"] = switch_webui_show_card_play_audio.value
                config_data["webui"]["show_card"]["web_captions_printer"] = switch_webui_show_card_web_captions_printer.value
                config_data["webui"]["show_card"]["key_mapping"] = switch_webui_show_card_key_mapping.value
                config_data["webui"]["show_card"]["unity"] = switch_webui_show_card_unity.value

                config_data["webui"]["theme"]["choose"] = select_webui_theme_choose.value

                config_data["login"]["enable"] = switch_login_enable.value
                config_data["login"]["username"] = input_login_username.value
                config_data["login"]["password"] = input_login_password.value

        except Exception as e:
            logging.error(f"无法写入配置文件！\n{e}")
            ui.notify(position="top", type="negative", message=f"无法写入配置文件！\n{e}")
            logging.error(traceback.format_exc())

        # return True

        try:
            with open(config_path, 'w', encoding="utf-8") as config_file:
                json.dump(config_data, config_file, indent=2, ensure_ascii=False)
                config_file.flush()  # 刷新缓冲区，确保写入立即生效

            logging.info("配置数据已成功写入文件！")
            ui.notify(position="top", type="positive", message="配置数据已成功写入文件！")

            return True
        except Exception as e:
            logging.error(f"无法写入配置文件！\n{e}")
            ui.notify(position="top", type="negative", message=f"无法写入配置文件！\n{e}")
            return False
    
    # Live2D线程
    try:
        if config.get("live2d", "enable"):
            web_server_port = int(config.get("live2d", "port"))
            threading.Thread(target=lambda: asyncio.run(web_server_thread(web_server_port))).start()
    except Exception as e:
        logging.error(traceback.format_exc())
        os._exit(0)



    """

    ..............................................................................................................
    ..............................................................................................................
    ..........................,]].................................................................................
    .........................O@@@@^...............................................................................
    .....=@@@@@`.....O@@@....,\@@[.....................................,@@@@@@@@@@]....O@@@^......=@@@@....O@@@^..
    .....=@@@@@@.....O@@@............................................=@@@@/`..,[@@/....O@@@^......=@@@@....O@@@^..
    .....=@@@@@@@....O@@@....,]]]].......]@@@@@]`.....,/@@@@\`....../@@@@..............O@@@^......=@@@@....O@@@^..
    .....=@@@/@@@\...O@@@....=@@@@....,@@@@@@@@@@^..,@@@@@@@@@@\...=@@@@...............O@@@^......=@@@@....O@@@^..
    .....=@@@^,@@@\..O@@@....=@@@@...,@@@@`........=@@@/....=@@@\..=@@@@....]]]]]]]]...O@@@^......=@@@@....O@@@^..
    .....=@@@^.=@@@^.O@@@....=@@@@...O@@@^.........@@@@......@@@@..=@@@@....=@@@@@@@...O@@@^......=@@@@....O@@@^..
    .....=@@@^..\@@@^=@@@....=@@@@...@@@@^........,@@@@@@@@@@@@@@..=@@@@.......=@@@@...O@@@^......=@@@@....O@@@^..
    .....=@@@^...\@@@/@@@....=@@@@...O@@@^.........@@@@`...........,@@@@`......=@@@@...O@@@^......=@@@@....O@@@^..
    .....=@@@^....@@@@@@@....=@@@@...,@@@@`........=@@@@......,.....=@@@@`.....=@@@@...=@@@@`.....@@@@^....O@@@^..
    .....=@@@^....,@@@@@@....=@@@@....,@@@@@@@@@@`..=@@@@@@@@@@@`....,@@@@@@@@@@@@@@....,@@@@@@@@@@@@`.....O@@@^..
    .....,[[[`.....,[[[[[....,[[[[.......[@@@@@[`.....,[@@@@@[`.........,\@@@@@@[`.........[@@@@@@[........[[[[`..
    ..............................................................................................................
    ..............................................................................................................

    """

    with ui.tabs().classes('w-full') as tabs:
        common_config_page = ui.tab('通用配置')
        llm_page = ui.tab('大语言模型')
        tts_page = ui.tab('文本转语音')
        svc_page = ui.tab('变声')
        visual_body_page = ui.tab('虚拟身体')
        copywriting_page = ui.tab('文案')
        integral_page = ui.tab('积分')
        talk_page = ui.tab('聊天')
        assistant_anchor_page = ui.tab('助播')
        translate_page = ui.tab('翻译')
        web_page = ui.tab('页面配置')
        docs_page = ui.tab('文档')
        about_page = ui.tab('关于')

    with ui.tab_panels(tabs, value=common_config_page).classes('w-full'):
        with ui.tab_panel(common_config_page).style(tab_panel_css):
            with ui.row():
                select_platform = ui.select(
                    label='平台', 
                    options={
                        'talk': '聊天模式', 
                        'bilibili': '哔哩哔哩', 
                        'bilibili2': '哔哩哔哩2', 
                        'dy': '抖音', 
                        'ks': '快手',
                        'wxlive': '微信视频号',
                        'douyu': '斗鱼', 
                        'youtube': 'YouTube', 
                        'twitch': 'twitch'
                    }, 
                    value=config.get("platform")
                ).style("width:200px;")

                input_room_display_id = ui.input(label='直播间号', placeholder='一般为直播间URL最后/后面的字母或数字', value=config.get("room_display_id")).style("width:200px;")

                select_chat_type = ui.select(
                    label='聊天类型', 
                    options={
                        'none': '不启用', 
                        'reread': '复读机', 
                        'chatgpt': 'ChatGPT/闻达', 
                        'claude': 'Claude', 
                        'claude2': 'Claude2',
                        'chatglm': 'ChatGLM',
                        'alice': 'Qwen-Alice',
                        'chat_with_file': 'chat_with_file',
                        'chatterbot': 'Chatterbot',
                        'text_generation_webui': 'text_generation_webui',
                        'sparkdesk': '讯飞星火',
                        'langchain_chatglm': 'langchain_chatglm',
                        'langchain_chatchat': 'langchain_chatchat',
                        'zhipu': '智谱AI',
                        'bard': 'Bard',
                        'yiyan': '文心一言',
                        'tongyixingchen': '通义星尘',
                        'my_wenxinworkshop': '千帆大模型',
                        'gemini': 'Gemini',
                        'tongyi': '通义千问',
                    }, 
                    value=config.get("chat_type")
                ).style("width:200px;")

                select_visual_body = ui.select(label='虚拟身体', options={'xuniren': 'xuniren', 'unity': 'unity', '其他': '其他'}, value=config.get("visual_body")).style("width:200px;")

                select_audio_synthesis_type = ui.select(
                    label='语音合成', 
                    options={
                        'edge-tts': 'Edge-TTS', 
                        'vits': 'VITS', 
                        'bert_vits2': 'bert_vits2',
                        'vits_fast': 'VITS-Fast', 
                        'elevenlabs': 'elevenlabs',
                        'genshinvoice_top': 'genshinvoice_top',
                        'tts_ai_lab_top': 'tts_ai_lab_top',
                        'bark_gui': 'bark_gui',
                        'vall_e_x': 'VALL-E-X',
                        'openai_tts': 'OpenAI TTS',
                        'reecho_ai': '睿声AI',
                        'gradio_tts': 'Gradio',
                        'gpt_sovits': 'GPT_SoVITS',
                    }, 
                    value=config.get("audio_synthesis_type")
                ).style("width:200px;")

            with ui.row():
                select_need_lang = ui.select(
                    label='回复语言', 
                    options={'none': '所有', 'zh': '中文', 'en': '英文', 'jp': '日文'}, 
                    value=config.get("need_lang")
                ).style("width:200px;")

                input_before_prompt = ui.input(label='提示词前缀', placeholder='此配置会追加在弹幕前，再发送给LLM处理', value=config.get("before_prompt")).style("width:200px;")

                input_after_prompt = ui.input(label='提示词后缀', placeholder='此配置会追加在弹幕后，再发送给LLM处理', value=config.get("after_prompt")).style("width:200px;")
            
            with ui.card().style(card_css):
                ui.label('平台相关')
                with ui.card().style(card_css):
                    ui.label('哔哩哔哩')
                    with ui.row():
                        select_bilibili_login_type = ui.select(
                            label='登录方式',
                            options={'手机扫码': '手机扫码', '手机扫码-终端': '手机扫码-终端', 'cookie': 'cookie', '账号密码登录': '账号密码登录', 'open_live': '开放平台', '不登录': '不登录'},
                            value=config.get("bilibili", "login_type")
                        ).style("width:100px")
                        input_bilibili_cookie = ui.input(label='cookie', placeholder='b站登录后F12抓网络包获取cookie，强烈建议使用小号！有封号风险', value=config.get("bilibili", "cookie")).style("width:500px;")
                        input_bilibili_ac_time_value = ui.input(label='ac_time_value', placeholder='b站登录后，F12控制台，输入window.localStorage.ac_time_value获取(如果没有，请重新登录)', value=config.get("bilibili", "ac_time_value")).style("width:500px;")
                    with ui.row():
                        input_bilibili_username = ui.input(label='账号', value=config.get("bilibili", "username"), placeholder='b站账号（建议使用小号）').style("width:300px;")
                        input_bilibili_password = ui.input(label='密码', value=config.get("bilibili", "password"), placeholder='b站密码（建议使用小号）').style("width:300px;")
                    with ui.row():
                        with ui.card().style(card_css):
                            ui.label('开放平台')
                            with ui.row():
                                input_bilibili_open_live_ACCESS_KEY_ID = ui.input(label='ACCESS_KEY_ID', value=config.get("bilibili", "open_live", "ACCESS_KEY_ID"), placeholder='开放平台ACCESS_KEY_ID').style("width:300px;")
                                input_bilibili_open_live_ACCESS_KEY_SECRET = ui.input(label='ACCESS_KEY_SECRET', value=config.get("bilibili", "open_live", "ACCESS_KEY_SECRET"), placeholder='开放平台ACCESS_KEY_SECRET').style("width:300px;")
                                input_bilibili_open_live_APP_ID = ui.input(label='项目ID', value=config.get("bilibili", "open_live", "APP_ID"), placeholder='开放平台 创作者服务中心 项目ID').style("width:200px;")
                                input_bilibili_open_live_ROOM_OWNER_AUTH_CODE = ui.input(label='身份码', value=config.get("bilibili", "open_live", "ROOM_OWNER_AUTH_CODE"), placeholder='直播中心用户 身份码').style("width:200px;")
                with ui.card().style(card_css):
                    ui.label('twitch')
                    with ui.row():
                        input_twitch_token = ui.input(label='token', value=config.get("twitch", "token"), placeholder='访问 https://twitchapps.com/tmi/ 获取，格式为：oauth:xxx').style("width:300px;")
                        input_twitch_user = ui.input(label='用户名', value=config.get("twitch", "user"), placeholder='你的twitch账号用户名').style("width:300px;")
                        input_twitch_proxy_server = ui.input(label='HTTP代理IP地址', value=config.get("twitch", "proxy_server"), placeholder='代理软件，http协议监听的ip地址，一般为：127.0.0.1').style("width:200px;")
                        input_twitch_proxy_port = ui.input(label='HTTP代理端口', value=config.get("twitch", "proxy_port"), placeholder='代理软件，http协议监听的端口，一般为：1080').style("width:200px;")
                        
            with ui.card().style(card_css):
                ui.label('音频播放')
                with ui.row():
                    switch_play_audio_enable = ui.switch('启用', value=config.get("play_audio", "enable")).style(switch_internal_css)
                    switch_play_audio_text_split_enable = ui.switch('启用文本切分', value=config.get("play_audio", "text_split_enable")).style(switch_internal_css)
                    input_play_audio_normal_interval = ui.input(label='普通音频播放间隔', value=config.get("play_audio", "normal_interval"), placeholder='就是弹幕回复、唱歌等音频播放结束后到播放下一个音频之间的一个间隔时间，单位：秒')
                    input_play_audio_out_path = ui.input(label='音频输出路径', placeholder='音频文件合成后存储的路径，支持相对路径或绝对路径', value=config.get("play_audio", "out_path"))
                    select_play_audio_player = ui.select(
                        label='播放器',
                        options={'pygame': 'pygame', 'audio_player_v2': 'audio_player_v2', 'audio_player': 'audio_player'},
                        value=config.get("play_audio", "player")
                    ).style("width:200px")
            
                with ui.card().style(card_css):
                    ui.label('audio_player')
                    with ui.row():
                        input_audio_player_api_ip_port = ui.input(label='API地址', value=config.get("audio_player", "api_ip_port"), placeholder='audio_player的API地址，只需要 http://ip:端口 即可').style("width:200px;")

            with ui.card().style(card_css):
                ui.label('念弹幕')
                with ui.grid(columns=3):
                    switch_read_comment_enable = ui.switch('启用', value=config.get("read_comment", "enable")).style(switch_internal_css)
                    switch_read_comment_read_username_enable = ui.switch('念用户名', value=config.get("read_comment", "read_username_enable")).style(switch_internal_css)
                    input_read_comment_username_max_len = ui.input(label='用户名最大长度', value=config.get("read_comment", "username_max_len"), placeholder='需要保留的用户名的最大长度，超出部分将被丢弃').style("width:100px;") 
                    switch_read_comment_voice_change = ui.switch('变声', value=config.get("read_comment", "voice_change")).style(switch_internal_css)
                with ui.grid(columns=2):
                    textarea_read_comment_read_username_copywriting = ui.textarea(label='念用户名文案', placeholder='念用户名时使用的文案，可以自定义编辑多个（换行分隔），实际中会随机一个使用', value=textarea_data_change(config.get("read_comment", "read_username_copywriting"))).style("width:500px;")
            with ui.card().style(card_css):
                ui.label('回复时念用户名')
                with ui.grid(columns=2):
                    switch_read_user_name_enable = ui.switch('启用', value=config.get("read_user_name", "enable")).style(switch_internal_css)
                    input_read_user_name_username_max_len = ui.input(label='用户名最大长度', value=config.get("read_user_name", "username_max_len"), placeholder='需要保留的用户名的最大长度，超出部分将被丢弃').style("width:100px;") 
                    switch_read_user_name_voice_change = ui.switch('启用变声', value=config.get("read_user_name", "voice_change")).style(switch_internal_css)
                with ui.grid(columns=2):
                    textarea_read_user_name_reply_before = ui.textarea(label='前置回复', placeholder='在正经回复前的念用户名的文案，目前是本地问答库-文本 触发时使用', value=textarea_data_change(config.get("read_user_name", "reply_before"))).style("width:500px;")
                    textarea_read_user_name_reply_after = ui.textarea(label='后置回复', placeholder='在正经回复后的念用户名的文案，目前是本地问答库-音频 触发时使用', value=textarea_data_change(config.get("read_user_name", "reply_after"))).style("width:500px;")
            with ui.card().style(card_css):
                ui.label('日志')
                with ui.grid(columns=4):
                    switch_captions_enable = ui.switch('启用', value=config.get("captions", "enable")).style(switch_internal_css)

                    select_comment_log_type = ui.select(
                        label='弹幕日志类型',
                        options={'问答': '问答', '问题': '问题', '回答': '回答', '不记录': '不记录'},
                        value=config.get("comment_log_type")
                    )

                    input_captions_file_path = ui.input(label='字幕日志路径', value=config.get("captions", "file_path"), placeholder='字幕日志存储路径').style("width:200px;")
                    input_captions_raw_file_path = ui.input(label='原文字幕日志路径', placeholder='原文字幕日志存储路径',
                                                        value=config.get("captions", "raw_file_path")).style("width:200px;")
            with ui.card().style(card_css):
                ui.label('本地问答')
                with ui.grid(columns=5):
                    switch_local_qa_text_enable = ui.switch('启用文本匹配', value=config.get("local_qa", "text", "enable")).style(switch_internal_css)
                    select_local_qa_text_type = ui.select(
                        label='弹幕日志类型',
                        options={'json': '自定义json', 'text': '一问一答'},
                        value=config.get("local_qa", "text", "type")
                    )
                    input_local_qa_text_file_path = ui.input(label='文本问答数据路径', placeholder='本地问答文本数据存储路径', value=config.get("local_qa", "text", "file_path")).style("width:200px;")
                    input_local_qa_text_similarity = ui.input(label='文本最低相似度', placeholder='最低文本匹配相似度，就是说用户发送的内容和本地问答库中设定的内容的最低相似度。\n低了就会被当做一般弹幕处理', value=config.get("local_qa", "text", "similarity")).style("width:200px;")
                    input_local_qa_text_username_max_len = ui.input(label='用户名最大长度', value=config.get("local_qa", "text", "username_max_len"), placeholder='需要保留的用户名的最大长度，超出部分将被丢弃').style("width:100px;")       
                with ui.grid(columns=4):
                    switch_local_qa_audio_enable = ui.switch('启用音频匹配', value=config.get("local_qa", "audio", "enable")).style(switch_internal_css)
                    input_local_qa_audio_file_path = ui.input(label='音频存储路径', placeholder='本地问答音频文件存储路径', value=config.get("local_qa", "audio", "file_path")).style("width:200px;")
                    input_local_qa_audio_similarity = ui.input(label='音频最低相似度', placeholder='最低音频匹配相似度，就是说用户发送的内容和本地音频库中音频文件名的最低相似度。\n低了就会被当做一般弹幕处理', value=config.get("local_qa", "audio", "similarity")).style("width:200px;")
            with ui.card().style(card_css):
                ui.label('过滤')    
                with ui.grid(columns=4):
                    textarea_filter_before_must_str = ui.textarea(label='弹幕触发前缀', placeholder='前缀必须携带其中任一字符串才能触发\n例如：配置#，那么这个会触发：#你好', value=textarea_data_change(config.get("filter", "before_must_str"))).style("width:300px;")
                    textarea_filter_after_must_str = ui.textarea(label='弹幕触发后缀', placeholder='后缀必须携带其中任一字符串才能触发\n例如：配置。那么这个会触发：你好。', value=textarea_data_change(config.get("filter", "before_must_str"))).style("width:300px;")
                    textarea_filter_before_filter_str = ui.textarea(label='弹幕过滤前缀', placeholder='当前缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：#你好', value=textarea_data_change(config.get("filter", "before_filter_str"))).style("width:300px;")
                    textarea_filter_after_filter_str = ui.textarea(label='弹幕过滤后缀', placeholder='当后缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：你好#', value=textarea_data_change(config.get("filter", "before_filter_str"))).style("width:300px;")
                with ui.grid(columns=3):
                    input_filter_max_len = ui.input(label='最大单词数', placeholder='最长阅读的英文单词数（空格分隔）', value=config.get("filter", "max_len")).style("width:150px;")
                    input_filter_max_char_len = ui.input(label='最大单词数', placeholder='最长阅读的字符数，双重过滤，避免溢出', value=config.get("filter", "max_char_len")).style("width:150px;")
                    switch_filter_emoji = ui.switch('弹幕表情过滤', value=config.get("filter", "emoji")).style(switch_internal_css)
                with ui.grid(columns=5):
                    switch_filter_badwords_enable = ui.switch('违禁词过滤', value=config.get("filter", "badwords", "enable")).style(switch_internal_css)
                    switch_filter_badwords_discard = ui.switch('违禁语句丢弃', value=config.get("filter", "badwords", "discard")).style(switch_internal_css)
                    input_filter_badwords_path = ui.input(label='违禁词路径', value=config.get("filter", "badwords", "path"), placeholder='本地违禁词数据路径（你如果不需要，可以清空文件内容）').style("width:200px;")
                    input_filter_badwords_bad_pinyin_path = ui.input(label='违禁拼音路径', value=config.get("filter", "badwords", "bad_pinyin_path"), placeholder='本地违禁拼音数据路径（你如果不需要，可以清空文件内容）').style("width:200px;")
                    input_filter_badwords_replace = ui.input(label='违禁词替换', value=config.get("filter", "badwords", "replace"), placeholder='在不丢弃违禁语句的前提下，将违禁词替换成此项的文本').style("width:200px;")
                with ui.grid(columns=4):
                    input_filter_comment_forget_duration = ui.input(label='弹幕遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "comment_forget_duration")).style("width:200px;")
                    input_filter_comment_forget_reserve_num = ui.input(label='弹幕保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "comment_forget_reserve_num")).style("width:200px;")
                    input_filter_gift_forget_duration = ui.input(label='礼物遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "gift_forget_duration")).style("width:200px;")
                    input_filter_gift_forget_reserve_num = ui.input(label='礼物保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "gift_forget_reserve_num")).style("width:200px;")
                with ui.grid(columns=4):
                    input_filter_entrance_forget_duration = ui.input(label='入场遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "entrance_forget_duration")).style("width:200px;")
                    input_filter_entrance_forget_reserve_num = ui.input(label='入场保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "entrance_forget_reserve_num")).style("width:200px;")
                    input_filter_follow_forget_duration = ui.input(label='关注遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "follow_forget_duration")).style("width:200px;")
                    input_filter_follow_forget_reserve_num = ui.input(label='关注保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "follow_forget_reserve_num")).style("width:200px;")
                with ui.grid(columns=4):
                    input_filter_talk_forget_duration = ui.input(label='聊天遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "talk_forget_duration")).style("width:200px;")
                    input_filter_talk_forget_reserve_num = ui.input(label='聊天保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "talk_forget_reserve_num")).style("width:200px;")
                    input_filter_schedule_forget_duration = ui.input(label='定时遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "schedule_forget_duration")).style("width:200px;")
                    input_filter_schedule_forget_reserve_num = ui.input(label='定时保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "schedule_forget_reserve_num")).style("width:200px;")
            with ui.card().style(card_css):
                ui.label('答谢')  
                with ui.row():
                    input_thanks_username_max_len = ui.input(label='用户名最大长度', value=config.get("thanks", "username_max_len"), placeholder='需要保留的用户名的最大长度，超出部分将被丢弃').style("width:100px;")       
                with ui.row():
                    switch_thanks_entrance_enable = ui.switch('启用入场欢迎', value=config.get("thanks", "entrance_enable")).style(switch_internal_css)
                    switch_thanks_entrance_random = ui.switch('随机选取', value=config.get("thanks", "entrance_random")).style(switch_internal_css)
                    textarea_thanks_entrance_copy = ui.textarea(label='入场文案', value=textarea_data_change(config.get("thanks", "entrance_copy")), placeholder='用户进入直播间的相关文案，请勿动 {username}，此字符串用于替换用户名').style("width:500px;")
                with ui.row():
                    switch_thanks_gift_enable = ui.switch('启用礼物答谢', value=config.get("thanks", "gift_enable")).style(switch_internal_css)
                    switch_thanks_gift_random = ui.switch('随机选取', value=config.get("thanks", "gift_random")).style(switch_internal_css)
                    textarea_thanks_gift_copy = ui.textarea(label='礼物文案', value=textarea_data_change(config.get("thanks", "gift_copy")), placeholder='用户赠送礼物的相关文案，请勿动 {username} 和 {gift_name}，此字符串用于替换用户名和礼物名').style("width:500px;")
                    input_thanks_lowest_price = ui.input(label='最低答谢礼物价格', value=config.get("thanks", "lowest_price"), placeholder='设置最低答谢礼物的价格（元），低于这个设置的礼物不会触发答谢').style("width:100px;")
                with ui.row():
                    switch_thanks_follow_enable = ui.switch('启用关注答谢', value=config.get("thanks", "follow_enable")).style(switch_internal_css)
                    switch_thanks_follow_random = ui.switch('随机选取', value=config.get("thanks", "follow_random")).style(switch_internal_css)
                    textarea_thanks_follow_copy = ui.textarea(label='关注文案', value=textarea_data_change(config.get("thanks", "follow_copy")), placeholder='用户关注时的相关文案，请勿动 {username}，此字符串用于替换用户名').style("width:500px;")
            
            with ui.card().style(card_css):
                ui.label('音频随机变速')     
                with ui.grid(columns=3):
                    switch_audio_random_speed_normal_enable = ui.switch('普通音频变速', value=config.get("audio_random_speed", "normal", "enable")).style(switch_internal_css)
                    input_audio_random_speed_normal_speed_min = ui.input(label='速度下限', value=config.get("audio_random_speed", "normal", "speed_min")).style("width:200px;")
                    input_audio_random_speed_normal_speed_max = ui.input(label='速度上限', value=config.get("audio_random_speed", "normal", "speed_max")).style("width:200px;")
                with ui.grid(columns=3):
                    switch_audio_random_speed_copywriting_enable = ui.switch('文案音频变速', value=config.get("audio_random_speed", "copywriting", "enable")).style(switch_internal_css)
                    input_audio_random_speed_copywriting_speed_min = ui.input(label='速度下限', value=config.get("audio_random_speed", "copywriting", "speed_min")).style("width:200px;")
                    input_audio_random_speed_copywriting_speed_max = ui.input(label='速度上限', value=config.get("audio_random_speed", "copywriting", "speed_max")).style("width:200px;")

            with ui.card().style(card_css):
                ui.label('Live2D') 
                with ui.grid(columns=2):
                    switch_live2d_enable = ui.switch('启用', value=config.get("live2d", "enable")).style(switch_internal_css)
                    input_live2d_port = ui.input(label='端口', value=config.get("live2d", "port")).style("width:200px;")

            with ui.card().style(card_css):
                ui.label('点歌模式') 
                with ui.row():
                    switch_choose_song_enable = ui.switch('启用', value=config.get("choose_song", "enable")).style(switch_internal_css)
                    textarea_choose_song_start_cmd = ui.textarea(label='点歌触发命令', value=textarea_data_change(config.get("choose_song", "start_cmd")), placeholder='点歌触发命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）').style("width:200px;")
                    textarea_choose_song_stop_cmd = ui.textarea(label='取消点歌命令', value=textarea_data_change(config.get("choose_song", "stop_cmd")), placeholder='停止点歌命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）').style("width:200px;")
                    textarea_choose_song_random_cmd = ui.textarea(label='随机点歌命令', value=textarea_data_change(config.get("choose_song", "random_cmd")), placeholder='随机点歌命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）').style("width:200px;")
                with ui.row():
                    input_choose_song_song_path = ui.input(label='歌曲路径', value=config.get("choose_song", "song_path"), placeholder='歌曲音频存放的路径，会自动读取音频文件').style("width:200px;")
                    input_choose_song_match_fail_copy = ui.input(label='匹配失败文案', value=config.get("choose_song", "match_fail_copy"), placeholder='匹配失败返回的音频文案 注意 {content} 这个是用于替换用户发送的歌名的，请务必不要乱删！影响使用！').style("width:300px;")
                    input_choose_song_similarity = ui.input(label='匹配最低相似度', value=config.get("choose_song", "similarity"), placeholder='最低音频匹配相似度，就是说用户发送的内容和本地音频库中音频文件名的最低相似度。\n低了就会被当做一般弹幕处理').style("width:200px;")
        
            with ui.card().style(card_css):
                ui.label('定时任务')
                schedule_var = {}
                for index, schedule in enumerate(config.get("schedule")):
                    with ui.row():
                        schedule_var[str(3 * index)] = ui.switch(text=f"启用任务{index}", value=schedule["enable"]).style(switch_internal_css)
                        schedule_var[str(3 * index + 1)] = ui.input(label="循环周期", value=schedule["time"], placeholder='定时任务循环的周期时长（秒），即每间隔这个周期就会执行一次').style("width:200px;")
                        schedule_var[str(3 * index + 2)] = ui.textarea(label="文案列表", value=textarea_data_change(schedule["copy"]), placeholder='存放文案的列表，通过空格或换行分割，通过{变量}来替换关键数据，可修改源码自定义功能').style("width:500px;")
            with ui.card().style(card_css):
                ui.label('闲时任务')
                with ui.row():
                    switch_idle_time_task_enable = ui.switch('启用', value=config.get("idle_time_task", "enable")).style(switch_internal_css)
                    input_idle_time_task_idle_time = ui.input(label='闲时时间', value=config.get("idle_time_task", "idle_time"), placeholder='闲时间隔时间（正整数，单位：秒），就是在没有弹幕情况下经过的时间').style("width:200px;")
                    switch_idle_time_task_random_time = ui.switch('随机闲时时间', value=config.get("idle_time_task", "random_time")).style(switch_internal_css)
                with ui.row():
                    switch_idle_time_task_comment_enable = ui.switch('LLM模式', value=config.get("idle_time_task", "comment", "enable")).style(switch_internal_css)
                    switch_idle_time_task_comment_random = ui.switch('随机文案', value=config.get("idle_time_task", "comment", "random")).style(switch_internal_css)
                    textarea_idle_time_task_comment_copy = ui.textarea(label='文案列表', value=textarea_data_change(config.get("idle_time_task", "comment", "copy")), placeholder='文案列表，文案之间用换行分隔，文案会丢LLM进行处理后直接合成返回的结果').style("width:800px;")
                with ui.row():
                    switch_idle_time_task_local_audio_enable = ui.switch('本地音频模式', value=config.get("idle_time_task", "local_audio", "enable")).style(switch_internal_css)
                    switch_idle_time_task_local_audio_random = ui.switch('随机本地音频', value=config.get("idle_time_task", "local_audio", "random")).style(switch_internal_css)
                    textarea_idle_time_task_local_audio_path = ui.textarea(label='本地音频路径列表', value=textarea_data_change(config.get("idle_time_task", "local_audio", "path")), placeholder='本地音频路径列表，相对/绝对路径之间用换行分隔，音频文件会直接丢进音频播放队列').style("width:800px;")
                
            with ui.card().style(card_css):
                ui.label('Stable Diffusion')
                with ui.row():
                    switch_sd_enable = ui.switch('启用', value=config.get("sd", "enable")).style(switch_internal_css) 
                    select_sd_translate_type = ui.select(
                        label='翻译类型',
                        options={'none': '不启用', 'baidu': '百度翻译', 'google': '谷歌翻译'},
                        value=config.get("sd", "translate_type")
                    ).style("width:100px;")
                    select_sd_prompt_llm_type = ui.select(
                        label='LLM类型',
                        options={
                            'chatgpt': 'ChatGPT/闻达', 
                            'claude': 'Claude', 
                            'claude2': 'Claude2',
                            'chatglm': 'ChatGLM',
                            'chat_with_file': 'chat_with_file',
                            'chatterbot': 'Chatterbot',
                            'text_generation_webui': 'text_generation_webui',
                            'sparkdesk': '讯飞星火',
                            'langchain_chatglm': 'langchain_chatglm',
                            'langchain_chatchat': 'langchain_chatchat',
                            'zhipu': '智谱AI',
                            'bard': 'Bard',
                            'yiyan': '文心一言',
                            'tongyixingchen': '通义星尘',
                            'my_wenxinworkshop': '千帆大模型',
                            'gemini': 'Gemini',
                            "none":"不启用"
                        },
                        value=config.get("sd", "prompt_llm", "type")
                    ).style("width:100px;")
                    input_sd_prompt_llm_before_prompt = ui.input(label='提示词前缀', value=config.get("sd", "prompt_llm", "before_prompt"), placeholder='LLM提示词前缀').style("width:300px;")
                    input_sd_prompt_llm_after_prompt = ui.input(label='提示词后缀', value=config.get("sd", "prompt_llm", "after_prompt"), placeholder='LLM提示词后缀').style("width:300px;")
                with ui.row(): 
                    input_sd_trigger = ui.input(label='弹幕触发前缀', value=config.get("sd", "trigger"), placeholder='触发的关键词（弹幕头部触发）').style("width:200px;")
                    input_sd_ip = ui.input(label='IP地址', value=config.get("sd", "ip"), placeholder='服务运行的IP地址').style("width:200px;")
                    input_sd_port = ui.input(label='端口', value=config.get("sd", "port"), placeholder='服务运行的端口').style("width:100px;")
                    input_sd_negative_prompt = ui.input(label='负面提示词', value=config.get("sd", "negative_prompt"), placeholder='负面文本提示，用于指定与生成图像相矛盾或相反的内容').style("width:200px;")
                    input_sd_seed = ui.input(label='随机种子', value=config.get("sd", "seed"), placeholder='随机种子，用于控制生成过程的随机性。可以设置一个整数值，以获得可重复的结果。').style("width:100px;")
                    textarea_sd_styles = ui.textarea(label='图像风格', placeholder='样式列表，用于指定生成图像的风格。可以包含多个风格，例如 ["anime", "portrait"]', value=textarea_data_change(config.get("sd", "styles"))).style("width:200px;")
                with ui.row():
                    input_sd_cfg_scale = ui.input(label='提示词相关性', value=config.get("sd", "cfg_scale"), placeholder='提示词相关性，无分类器指导信息影响尺度(Classifier Free Guidance Scale) -图像应在多大程度上服从提示词-较低的值会产生更有创意的结果。').style("width:100px;")
                    input_sd_steps = ui.input(label='生成图像步数', value=config.get("sd", "steps"), placeholder='生成图像的步数，用于控制生成的精确程度。').style("width:100px;") 
                    input_sd_hr_resize_x = ui.input(label='图像水平像素', value=config.get("sd", "hr_resize_x"), placeholder='生成图像的水平尺寸。').style("width:100px;")
                    input_sd_hr_resize_y = ui.input(label='图像垂直像素', value=config.get("sd", "hr_resize_y"), placeholder='生成图像的垂直尺寸。').style("width:100px;")
                    input_sd_denoising_strength = ui.input(label='去噪强度', value=config.get("sd", "denoising_strength"), placeholder='去噪强度，用于控制生成图像中的噪点。').style("width:100px;")
                with ui.row():
                    switch_sd_enable_hr = ui.switch('高分辨率生成', value=config.get("sd", "enable_hr")).style(switch_internal_css)
                    input_sd_hr_scale = ui.input(label='高分辨率缩放因子', value=config.get("sd", "hr_scale"), placeholder='高分辨率缩放因子，用于指定生成图像的高分辨率缩放级别。').style("width:200px;")
                    input_sd_hr_second_pass_steps = ui.input(label='高分生二次传递步数', value=config.get("sd", "hr_second_pass_steps"), placeholder='高分辨率生成的第二次传递步数。').style("width:200px;")
                    switch_sd_save_enable = ui.switch('保存图片到本地', value=config.get("sd", "save_enable")).style(switch_internal_css)
                    switch_sd_loop_cover = ui.switch('本地图片循环覆盖', value=config.get("sd", "loop_cover")).style(switch_internal_css)
                    input_sd_save_path = ui.input(label='图片保存路径', value=config.get("sd", "save_path"), placeholder='生成图片存储路径，不建议修改').style("width:200px;")
                    
            with ui.card().style(card_css):
                ui.label('动态文案')
                with ui.grid(columns=3):
                    switch_trends_copywriting_enable = ui.switch('启用', value=config.get("trends_copywriting", "enable")).style(switch_internal_css)
                    switch_trends_copywriting_random_play = ui.switch('随机播放', value=config.get("trends_copywriting", "random_play")).style(switch_internal_css)
                    input_trends_copywriting_play_interval = ui.input(label='文案播放间隔', value=config.get("trends_copywriting", "play_interval"), placeholder='文案于文案之间的播放间隔时间（秒）').style("width:200px;")
                trends_copywriting_copywriting_var = {}
                for index, trends_copywriting_copywriting in enumerate(config.get("trends_copywriting", "copywriting")):
                    with ui.grid(columns=3):
                        trends_copywriting_copywriting_var[str(3 * index)] = ui.input(label=f"文案路径{index}", value=trends_copywriting_copywriting["folder_path"], placeholder='文案文件存储的文件夹路径').style("width:200px;")
                        trends_copywriting_copywriting_var[str(3 * index + 1)] = ui.switch(text="提示词转换", value=trends_copywriting_copywriting["prompt_change_enable"])
                        trends_copywriting_copywriting_var[str(3 * index + 2)] = ui.input(label="提示词转换内容", value=trends_copywriting_copywriting["prompt_change_content"], placeholder='使用此提示词内容对文案内容进行转换后再进行合成，使用的LLM为聊天类型配置').style("width:200px;")
        
            with ui.card().style(card_css):
                ui.label('web字幕打印机')
                with ui.grid(columns=2):
                    switch_web_captions_printer_enable = ui.switch('启用', value=config.get("web_captions_printer", "enable")).style(switch_internal_css)
                    input_web_captions_printer_api_ip_port = ui.input(label='API地址', value=config.get("web_captions_printer", "api_ip_port"), placeholder='web字幕打印机的API地址，只需要 http://ip:端口 即可').style("width:200px;")
            
            with ui.card().style(card_css):
                ui.label('数据库')
                with ui.grid(columns=4):
                    switch_database_comment_enable = ui.switch('弹幕日志', value=config.get("database", "comment_enable")).style(switch_internal_css)
                    switch_database_entrance_enable = ui.switch('入场日志', value=config.get("database", "entrance_enable")).style(switch_internal_css)
                    switch_database_gift_enable = ui.switch('礼物日志', value=config.get("database", "gift_enable")).style(switch_internal_css)
                    input_database_path = ui.input(label='数据库路径', value=config.get("database", "path"), placeholder='数据库文件存储路径').style("width:200px;")
                    

            with ui.card().style(card_css):
                ui.label('按键映射')
                with ui.row():
                    switch_key_mapping_enable = ui.switch('启用', value=config.get("key_mapping", "enable")).style(switch_internal_css)
                    select_key_mapping_type = ui.select(
                        label='类型',
                        options={'弹幕': '弹幕', '回复': '回复', '弹幕+回复': '弹幕+回复'},
                        value=config.get("key_mapping", "type")
                    ).style("width:300px")
                    input_key_mapping_start_cmd = ui.input(label='命令前缀', value=config.get("key_mapping", "start_cmd"), placeholder='想要触发此功能必须以这个字符串做为命令起始，不然将不会被解析为按键映射命令').style("width:200px;")
                key_mapping_config_var = {}
                for index, key_mapping_config in enumerate(config.get("key_mapping", "config")):
                    with ui.grid(columns=4):
                        key_mapping_config_var[str(4 * index)] = ui.textarea(label="关键词", value=textarea_data_change(key_mapping_config["keywords"]), placeholder='此处输入触发的关键词，多个请以换行分隔').style("width:200px;")
                        key_mapping_config_var[str(4 * index + 1)] = ui.textarea(label="礼物", value=textarea_data_change(key_mapping_config["gift"]), placeholder='此处输入触发的礼物名，多个请以换行分隔').style("width:200px;")
                        key_mapping_config_var[str(4 * index + 2)] = ui.textarea(label="按键", value=textarea_data_change(key_mapping_config["keys"]), placeholder='此处输入你要映射的按键，多个按键请以换行分隔（按键名参考pyautogui规则）').style("width:100px;")
                        key_mapping_config_var[str(4 * index + 3)] = ui.input(label="相似度", value=key_mapping_config["similarity"], placeholder='关键词与用户输入的相似度，默认1即100%').style("width:200px;")

            with ui.card().style(card_css):
                ui.label('动态配置')
                with ui.row():
                    switch_trends_config_enable = ui.switch('启用', value=config.get("trends_config", "enable")).style(switch_internal_css)
                trends_config_path_var = {}
                for index, trends_config_path in enumerate(config.get("trends_config", "path")):
                    with ui.grid(columns=2):
                        trends_config_path_var[str(2 * index)] = ui.input(label="在线人数范围", value=trends_config_path["online_num"], placeholder='在线人数范围，用减号-分隔，例如：0-10').style("width:200px;")
                        trends_config_path_var[str(2 * index + 1)] = ui.input(label="配置路径", value=trends_config_path["path"], placeholder='此处输入加载的配置文件的路径').style("width:200px;")
            
            with ui.card().style(card_css):
                ui.label('异常报警')
                with ui.row():
                    switch_abnormal_alarm_platform_enable = ui.switch('启用平台报警', value=config.get("abnormal_alarm", "platform", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_platform_type = ui.select(
                        label='类型',
                        options={'local_audio': '本地音频'},
                        value=config.get("abnormal_alarm", "platform", "type")
                    )
                    input_abnormal_alarm_platform_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "platform", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                    input_abnormal_alarm_platform_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "platform", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                    input_abnormal_alarm_platform_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "platform", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                with ui.row():
                    switch_abnormal_alarm_llm_enable = ui.switch('启用LLM报警', value=config.get("abnormal_alarm", "llm", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_llm_type = ui.select(
                        label='类型',
                        options={'local_audio': '本地音频'},
                        value=config.get("abnormal_alarm", "llm", "type")
                    )
                    input_abnormal_alarm_llm_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "llm", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                    input_abnormal_alarm_llm_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "llm", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                    input_abnormal_alarm_llm_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "llm", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                with ui.row():
                    switch_abnormal_alarm_tts_enable = ui.switch('启用TTS报警', value=config.get("abnormal_alarm", "tts", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_tts_type = ui.select(
                        label='类型',
                        options={'local_audio': '本地音频'},
                        value=config.get("abnormal_alarm", "tts", "type")
                    )
                    input_abnormal_alarm_tts_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "tts", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                    input_abnormal_alarm_tts_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "tts", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                    input_abnormal_alarm_tts_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "tts", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                with ui.row():
                    switch_abnormal_alarm_svc_enable = ui.switch('启用SVC报警', value=config.get("abnormal_alarm", "svc", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_svc_type = ui.select(
                        label='类型',
                        options={'local_audio': '本地音频'},
                        value=config.get("abnormal_alarm", "svc", "type")
                    )
                    input_abnormal_alarm_svc_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "svc", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                    input_abnormal_alarm_svc_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "svc", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                    input_abnormal_alarm_svc_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "svc", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                with ui.row():
                    switch_abnormal_alarm_visual_body_enable = ui.switch('启用虚拟身体报警', value=config.get("abnormal_alarm", "visual_body", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_visual_body_type = ui.select(
                        label='类型',
                        options={'local_audio': '本地音频'},
                        value=config.get("abnormal_alarm", "visual_body", "type")
                    )
                    input_abnormal_alarm_visual_body_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "visual_body", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                    input_abnormal_alarm_visual_body_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "visual_body", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                    input_abnormal_alarm_visual_body_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "visual_body", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                with ui.row():
                    switch_abnormal_alarm_other_enable = ui.switch('启用其他报警', value=config.get("abnormal_alarm", "other", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_other_type = ui.select(
                        label='类型',
                        options={'local_audio': '本地音频'},
                        value=config.get("abnormal_alarm", "other", "type")
                    )
                    input_abnormal_alarm_other_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "other", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                    input_abnormal_alarm_other_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "other", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                    input_abnormal_alarm_other_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "other", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                
        
        with ui.tab_panel(llm_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label("ChatGPT/闻达")
                with ui.row():
                    input_openai_api = ui.input(label='API地址', placeholder='API请求地址，支持代理', value=config.get("openai", "api")).style("width:200px;")
                    textarea_openai_api_key = ui.textarea(label='API密钥', placeholder='API KEY，支持代理', value=textarea_data_change(config.get("openai", "api_key"))).style("width:400px;")
                    button_openai_test = ui.button('测试', on_click=lambda: test_openai_key(), color=button_bottom_color).style(button_bottom_css)
                with ui.row():
                    chatgpt_models = ["gpt-3.5-turbo",
                        "gpt-3.5-turbo-0301",
                        "gpt-3.5-turbo-0613",
                        "gpt-3.5-turbo-1106",
                        "gpt-3.5-turbo-16k",
                        "gpt-3.5-turbo-16k-0613",
                        "gpt-3.5-turbo-instruct",
                        "gpt-3.5-turbo-instruct-0914",
                        "gpt-4",
                        "gpt-4-0314",
                        "gpt-4-0613",
                        "gpt-4-32k",
                        "gpt-4-32k-0314",
                        "gpt-4-32k-0613",
                        "gpt-4-1106-preview",
                        "text-embedding-ada-002",
                        "text-davinci-003",
                        "text-davinci-002",
                        "text-curie-001",
                        "text-babbage-001",
                        "text-ada-001",
                        "text-moderation-latest",
                        "text-moderation-stable",
                        "rwkv",
                        "chatglm3-6b"]
                    data_json = {}
                    for line in chatgpt_models:
                        data_json[line] = line
                    select_chatgpt_model = ui.select(
                        label='模型', 
                        options=data_json, 
                        value=config.get("chatgpt", "model")
                    )
                    input_chatgpt_temperature = ui.input(label='温度', placeholder='控制生成文本的随机性。较高的温度值会使生成的文本更随机和多样化，而较低的温度值会使生成的文本更加确定和一致。', value=config.get("chatgpt", "temperature")).style("width:200px;")
                    input_chatgpt_max_tokens = ui.input(label='最大令牌数', placeholder='限制生成回答的最大长度。', value=config.get("chatgpt", "max_tokens")).style("width:200px;")
                    input_chatgpt_top_p = ui.input(label='前p个选择', placeholder='Nucleus采样。这个参数控制模型从累积概率大于一定阈值的令牌中进行采样。较高的值会产生更多的多样性，较低的值会产生更少但更确定的回答。', value=config.get("chatgpt", "top_p")).style("width:200px;")
                with ui.row():
                    input_chatgpt_presence_penalty = ui.input(label='存在惩罚', placeholder='控制模型生成回答时对给定问题提示的关注程度。较高的存在惩罚值会减少模型对给定提示的重复程度，鼓励模型更自主地生成回答。', value=config.get("chatgpt", "presence_penalty")).style("width:200px;")
                    input_chatgpt_frequency_penalty = ui.input(label='频率惩罚', placeholder='控制生成回答时对已经出现过的令牌的惩罚程度。较高的频率惩罚值会减少模型生成已经频繁出现的令牌，以避免重复和过度使用特定词语。', value=config.get("chatgpt", "frequency_penalty")).style("width:200px;")

                    input_chatgpt_preset = ui.input(label='预设', placeholder='用于指定一组预定义的设置，以便模型更好地适应特定的对话场景。', value=config.get("chatgpt", "preset")).style("width:500px") 
            with ui.card().style(card_css):
                ui.label("Claude")
                with ui.row():
                    input_claude_slack_user_token = ui.input(label='slack_user_token', placeholder='Slack平台配置的用户Token，参考文档的Claude板块进行配置', value=config.get("claude", "slack_user_token"))
                    input_claude_slack_user_token.style("width:400px")
                    input_claude_bot_user_id = ui.input(label='bot_user_id', placeholder='Slack平台添加的Claude显示的成员ID，参考文档的Claude板块进行配置', value=config.get("claude", "bot_user_id"))
                    input_claude_slack_user_token.style("width:400px") 
            with ui.card().style(card_css):
                ui.label("Claude2")
                with ui.row():
                    input_claude2_cookie = ui.input(label='cookie', placeholder='claude.ai官网，打开F12，随便提问抓个包，请求头cookie配置于此', value=config.get("claude2", "cookie"))
                    input_claude2_cookie.style("width:400px")
                    switch_claude2_use_proxy = ui.switch('启用代理', value=config.get("claude2", "use_proxy")).style(switch_internal_css)
                with ui.row():
                    input_claude2_proxies_http = ui.input(label='proxies_http', placeholder='http代理地址，默认为 http://127.0.0.1:10809', value=config.get("claude2", "proxies", "http"))
                    input_claude2_proxies_http.style("width:400px") 
                    input_claude2_proxies_https = ui.input(label='proxies_https', placeholder='https代理地址，默认为 http://127.0.0.1:10809', value=config.get("claude2", "proxies", "https"))
                    input_claude2_proxies_https.style("width:400px")
                    input_claude2_proxies_socks5 = ui.input(label='proxies_socks5', placeholder='socks5代理地址，默认为 socks://127.0.0.1:10808', value=config.get("claude2", "proxies", "socks5"))
                    input_claude2_proxies_socks5.style("width:400px") 
            with ui.card().style(card_css):
                ui.label("ChatGLM")
                with ui.row():
                    input_chatglm_api_ip_port = ui.input(label='API地址', placeholder='ChatGLM的API版本运行后的服务链接（需要完整的URL）', value=config.get("chatglm", "api_ip_port"))
                    input_chatglm_api_ip_port.style("width:400px")
                    input_chatglm_max_length = ui.input(label='最大长度限制', placeholder='生成回答的最大长度限制，以令牌数或字符数为单位。', value=config.get("chatglm", "max_length"))
                    input_chatglm_max_length.style("width:200px")
                    input_chatglm_top_p = ui.input(label='前p个选择', placeholder='也称为 Nucleus采样。控制模型生成时选择概率的阈值范围。', value=config.get("chatglm", "top_p"))
                    input_chatglm_top_p.style("width:200px")
                    input_chatglm_temperature = ui.input(label='温度', placeholder='温度参数，控制生成文本的随机性。较高的温度值会产生-更多的随机性和多样性。', value=config.get("chatglm", "temperature"))
                    input_chatglm_temperature.style("width:200px")
                with ui.row():
                    switch_chatglm_history_enable = ui.switch('上下文记忆', value=config.get("chatglm", "history_enable")).style(switch_internal_css)
                    input_chatglm_history_max_len = ui.input(label='最大记忆长度', placeholder='最大记忆的上下文字符数量，不建议设置过大，容易爆显存，自行根据情况配置', value=config.get("chatglm", "history_max_len"))
                    input_chatglm_history_max_len.style("width:200px")
            with ui.card().style(card_css):
                ui.label("Qwen-Alice")
                with ui.row():
                    input_alice_api_ip_port = ui.input(label='API地址', placeholder='ChatGLM的API版本运行后的服务链接（需要完整的URL）', value=config.get("alice", "api_ip_port"))
                    input_alice_api_ip_port.style("width:400px")
                    input_alice_max_length = ui.input(label='最大长度限制', placeholder='生成回答的最大长度限制，以令牌数或字符数为单位。', value=config.get("alice", "max_length"))
                    input_alice_max_length.style("width:200px")
                    input_alice_top_p = ui.input(label='前p个选择', placeholder='也称为 Nucleus采样。控制模型生成时选择概率的阈值范围。', value=config.get("alice", "top_p"))
                    input_alice_top_p.style("width:200px")
                    input_alice_temperature = ui.input(label='温度', placeholder='温度参数，控制生成文本的随机性。较高的温度值会产生更多的随机性和多样性。', value=config.get("alice", "temperature"))
                    input_alice_temperature.style("width:200px")
                with ui.row():
                    switch_alice_history_enable = ui.switch('上下文记忆', value=config.get("alice", "history_enable")).style(switch_internal_css)
                    input_alice_history_max_len = ui.input(label='最大记忆轮数', placeholder='最大记忆的上下文轮次数量，不建议设置过大，容易爆显存，自行根据情况配置', value=config.get("alice", "history_max_len"))
                    input_alice_history_max_len.style("width:200px")
                    input_alice_preset = ui.input(label='预设',
                                                    placeholder='用于指定一组预定义的设置，以便模型更好地适应特定的对话场景。',
                                                    value=config.get("chatgpt", "preset")).style("width:500px")


            with ui.card().style(card_css):
                ui.label("chat_with_file")
                with ui.row():
                    lines = ["claude", "openai_gpt", "openai_vector_search"]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_chat_with_file_chat_mode = ui.select(
                        label='聊天模式', 
                        options=data_json, 
                        value=config.get("chat_with_file", "chat_mode")
                    )
                    input_chat_with_file_data_path = ui.input(label='数据文件路径', placeholder='加载的本地zip数据文件路径（到x.zip）, 如：./data/伊卡洛斯百度百科.zip', value=config.get("chat_with_file", "data_path"))
                    input_chat_with_file_data_path.style("width:400px")
                with ui.row():
                    input_chat_with_file_separator = ui.input(label='分隔符', placeholder='拆分文本的分隔符，这里使用 换行符 作为分隔符。', value=config.get("chat_with_file", "separator"))
                    input_chat_with_file_separator.style("width:300px")
                    input_chat_with_file_chunk_size = ui.input(label='块大小', placeholder='每个文本块的最大字符数(文本块字符越多，消耗token越多，回复越详细)', value=config.get("chat_with_file", "chunk_size"))
                    input_chat_with_file_chunk_size.style("width:300px")
                    input_chat_with_file_chunk_overlap = ui.input(label='块重叠', placeholder='两个相邻文本块之间的重叠字符数。这种重叠可以帮助保持文本的连贯性，特别是当文本被用于训练语言模型或其他需要上下文信息的机器学习模型时', value=config.get("chat_with_file", "chunk_overlap"))
                    input_chat_with_file_chunk_overlap.style("width:300px")
                    lines = ["sebastian-hofstaetter/distilbert-dot-tas_b-b256-msmarco", "GanymedeNil/text2vec-large-chinese"]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_chat_with_file_local_vector_embedding_model = ui.select(
                        label='模型', 
                        options=data_json, 
                        value=config.get("chat_with_file", "local_vector_embedding_model")
                    )
                with ui.row():
                    input_chat_with_file_chain_type = ui.input(label='链类型', placeholder='指定要生成的语言链的类型，例如：stuff', value=config.get("chat_with_file", "chain_type"))
                    input_chat_with_file_chain_type.style("width:300px")
                    input_chat_with_file_question_prompt = ui.input(label='问题总结提示词', placeholder='通过LLM总结本地向量数据库输出内容，此处填写总结用提示词', value=config.get("chat_with_file", "question_prompt"))
                    input_chat_with_file_question_prompt.style("width:300px")
                    input_chat_with_file_local_max_query = ui.input(label='最大查询数据库次数', placeholder='最大查询数据库次数。限制次数有助于节省token', value=config.get("chat_with_file", "local_max_query"))
                    input_chat_with_file_local_max_query.style("width:300px")
                    switch_chat_with_file_show_token_cost = ui.switch('显示成本', value=config.get("chat_with_file", "show_token_cost")).style(switch_internal_css)
            with ui.card().style(card_css):
                ui.label("Chatterbot")
                with ui.grid(columns=2):
                    input_chatterbot_name = ui.input(label='bot名称', placeholder='bot名称', value=config.get("chatterbot", "name"))
                    input_chatterbot_name.style("width:400px")
                    input_chatterbot_db_path = ui.input(label='数据库路径', placeholder='数据库路径（绝对或相对路径）', value=config.get("chatterbot", "db_path"))
                    input_chatterbot_db_path.style("width:400px")
            with ui.card().style(card_css):
                ui.label("text_generation_webui")
                with ui.row():
                    select_text_generation_webui_type = ui.select(
                        label='类型', 
                        options={"官方API": "官方API", "coyude": "coyude"}, 
                        value=config.get("text_generation_webui", "type")
                    )
                    input_text_generation_webui_api_ip_port = ui.input(label='API地址', placeholder='text-generation-webui开启API模式后监听的IP和端口地址', value=config.get("text_generation_webui", "api_ip_port"))
                    input_text_generation_webui_api_ip_port.style("width:300px")
                    input_text_generation_webui_max_new_tokens = ui.input(label='max_new_tokens', placeholder='自行查阅', value=config.get("text_generation_webui", "max_new_tokens"))
                    input_text_generation_webui_max_new_tokens.style("width:200px")
                    switch_text_generation_webui_history_enable = ui.switch('上下文记忆', value=config.get("text_generation_webui", "history_enable")).style(switch_internal_css)
                    input_text_generation_webui_history_max_len = ui.input(label='最大记忆长度', placeholder='最大记忆的上下文字符数量，不建议设置过大，容易爆显存，自行根据情况配置', value=config.get("text_generation_webui", "history_max_len"))
                    input_text_generation_webui_history_max_len.style("width:200px")
                with ui.row():
                    select_text_generation_webui_mode = ui.select(
                        label='类型', 
                        options={"chat": "chat", "chat-instruct": "chat-instruct", "instruct": "instruct"}, 
                        value=config.get("text_generation_webui", "mode")
                    ).style("width:150px")
                    input_text_generation_webui_character = ui.input(label='character', placeholder='自行查阅', value=config.get("text_generation_webui", "character"))
                    input_text_generation_webui_character.style("width:100px")
                    input_text_generation_webui_instruction_template = ui.input(label='instruction_template', placeholder='自行查阅', value=config.get("text_generation_webui", "instruction_template"))
                    input_text_generation_webui_instruction_template.style("width:150px")
                    input_text_generation_webui_your_name = ui.input(label='your_name', placeholder='自行查阅', value=config.get("text_generation_webui", "your_name"))
                    input_text_generation_webui_your_name.style("width:100px")
                with ui.row():
                    input_text_generation_webui_top_p = ui.input(label='top_p', value=config.get("text_generation_webui", "top_p"), placeholder='topP生成时，核采样方法的概率阈值。例如，取值为0.8时，仅保留累计概率之和大于等于0.8的概率分布中的token，作为随机采样的候选集。取值范围为(0,1.0)，取值越大，生成的随机性越高；取值越低，生成的随机性越低。默认值 0.95。注意，取值不要大于等于1')
                    input_text_generation_webui_top_k = ui.input(label='top_k', value=config.get("text_generation_webui", "top_k"), placeholder='匹配搜索结果条数')
                    input_text_generation_webui_temperature = ui.input(label='temperature', value=config.get("text_generation_webui", "temperature"), placeholder='较高的值将使输出更加随机，而较低的值将使输出更加集中和确定。可选，默认取值0.92')
                    input_text_generation_webui_seed = ui.input(label='seed', value=config.get("text_generation_webui", "seed"), placeholder='seed生成时，随机数的种子，用于控制模型生成的随机性。如果使用相同的种子，每次运行生成的结果都将相同；当需要复现模型的生成结果时，可以使用相同的种子。seed参数支持无符号64位整数类型。默认值 1683806810')
                
            with ui.card().style(card_css):
                ui.label("讯飞星火")
                with ui.grid(columns=2):
                    lines = ["web", "api"]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_sparkdesk_type = ui.select(
                        label='类型', 
                        options=data_json, 
                        value=config.get("sparkdesk", "type")
                    )
                    input_sparkdesk_cookie = ui.input(label='cookie', placeholder='web抓包请求头中的cookie，参考文档教程', value=config.get("sparkdesk", "cookie"))
                    input_sparkdesk_cookie.style("width:400px")
                with ui.row():
                    input_sparkdesk_fd = ui.input(label='fd', placeholder='web抓包负载中的fd，参考文档教程', value=config.get("sparkdesk", "fd"))
                    input_sparkdesk_fd.style("width:300px")      
                    input_sparkdesk_GtToken = ui.input(label='GtToken', placeholder='web抓包负载中的GtToken，参考文档教程', value=config.get("sparkdesk", "GtToken"))
                    input_sparkdesk_GtToken.style("width:300px")
                with ui.row():
                    input_sparkdesk_app_id = ui.input(label='app_id', placeholder='申请官方API后，云平台中提供的APPID', value=config.get("sparkdesk", "app_id"))
                    input_sparkdesk_app_id.style("width:300px")      
                    input_sparkdesk_api_secret = ui.input(label='api_secret', placeholder='申请官方API后，云平台中提供的APISecret', value=config.get("sparkdesk", "api_secret"))
                    input_sparkdesk_api_secret.style("width:300px") 
                    input_sparkdesk_api_key = ui.input(label='api_key', placeholder='申请官方API后，云平台中提供的APIKey', value=config.get("sparkdesk", "api_key"))
                    input_sparkdesk_api_key.style("width:300px") 
                    lines = ["3.1", "2.1", "1.1"]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_sparkdesk_version = ui.select(
                        label='版本', 
                        options=data_json, 
                        value=str(config.get("sparkdesk", "version"))
                    ).style("width:100px") 
            with ui.card().style(card_css):
                ui.label("Langchain_ChatGLM")
                with ui.row():
                    input_langchain_chatglm_api_ip_port = ui.input(label='API地址', placeholder='langchain_chatglm的API版本运行后的服务链接（需要完整的URL）', value=config.get("langchain_chatglm", "api_ip_port"))
                    input_langchain_chatglm_api_ip_port.style("width:400px")
                    lines = ["模型", "知识库", "必应"]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_langchain_chatglm_chat_type = ui.select(
                        label='类型', 
                        options=data_json, 
                        value=config.get("langchain_chatglm", "chat_type")
                    )
                with ui.row():
                    input_langchain_chatglm_knowledge_base_id = ui.input(label='知识库名称', placeholder='本地存在的知识库名称，日志也有输出知识库列表，可以查看', value=config.get("langchain_chatglm", "knowledge_base_id"))
                    input_langchain_chatglm_knowledge_base_id.style("width:400px")
                    switch_langchain_chatglm_history_enable = ui.switch('上下文记忆', value=config.get("langchain_chatglm", "history_enable")).style(switch_internal_css)
                    input_langchain_chatglm_history_max_len = ui.input(label='最大记忆长度', placeholder='最大记忆的上下文字符数量，不建议设置过大，容易爆显存，自行根据情况配置', value=config.get("langchain_chatglm", "history_max_len"))
                    input_langchain_chatglm_history_max_len.style("width:400px")
            with ui.card().style(card_css):
                ui.label("Langchain_ChatChat")
                with ui.row():
                    input_langchain_chatchat_api_ip_port = ui.input(label='API地址', placeholder='langchain_chatchat的API版本运行后的服务链接（需要完整的URL）', value=config.get("langchain_chatchat", "api_ip_port"))
                    input_langchain_chatchat_api_ip_port.style("width:400px")
                    lines = ["模型", "知识库", "搜索引擎"]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_langchain_chatchat_chat_type = ui.select(
                        label='类型', 
                        options=data_json, 
                        value=config.get("langchain_chatchat", "chat_type")
                    )
                    switch_langchain_chatchat_history_enable = ui.switch('上下文记忆', value=config.get("langchain_chatchat", "history_enable")).style(switch_internal_css)
                    input_langchain_chatchat_history_max_len = ui.input(label='最大记忆长度', placeholder='最大记忆的上下文字符数量，不建议设置过大，容易爆显存，自行根据情况配置', value=config.get("langchain_chatchat", "history_max_len"))
                    input_langchain_chatchat_history_max_len.style("width:400px")
                with ui.row():
                    with ui.card().style(card_css):
                        ui.label("模型")
                        with ui.row():
                            input_langchain_chatchat_llm_model_name = ui.input(label='LLM模型', value=config.get("langchain_chatchat", "llm", "model_name"), placeholder='本地加载的LLM模型名')
                            input_langchain_chatchat_llm_temperature = ui.input(label='温度', value=config.get("langchain_chatchat", "llm", "temperature"), placeholder='采样温度，控制输出的随机性，必须为正数\n取值范围是：(0.0,1.0]，不能等于 0,默认值为 0.95\n值越大，会使输出更随机，更具创造性；值越小，输出会更加稳定或确定\n建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数')
                            input_langchain_chatchat_llm_max_tokens = ui.input(label='max_tokens', value=config.get("langchain_chatchat", "llm", "max_tokens"), placeholder='大于0的正整数，不建议太大，你可能会爆显存')
                            input_langchain_chatchat_llm_prompt_name = ui.input(label='Prompt模板', value=config.get("langchain_chatchat", "llm", "prompt_name"), placeholder='本地存在的提示词模板文件名')
                with ui.row():
                    with ui.card().style(card_css):
                        ui.label("知识库")
                        with ui.row():
                            input_langchain_chatchat_knowledge_base_knowledge_base_name = ui.input(label='知识库名', value=config.get("langchain_chatchat", "knowledge_base", "knowledge_base_name"), placeholder='本地添加的知识库名，运行时会自动检索存在的知识库列表，输出到cmd，请自行查看')
                            input_langchain_chatchat_knowledge_base_top_k = ui.input(label='匹配搜索结果条数', value=config.get("langchain_chatchat", "knowledge_base", "top_k"), placeholder='匹配搜索结果条数')
                            input_langchain_chatchat_knowledge_base_score_threshold = ui.input(label='知识匹配分数阈值', value=config.get("langchain_chatchat", "knowledge_base", "score_threshold"), placeholder='0.00-2.00之间')
                            input_langchain_chatchat_knowledge_base_model_name = ui.input(label='LLM模型', value=config.get("langchain_chatchat", "knowledge_base", "model_name"), placeholder='本地加载的LLM模型名')
                            input_langchain_chatchat_knowledge_base_temperature = ui.input(label='温度', value=config.get("langchain_chatchat", "knowledge_base", "temperature"), placeholder='采样温度，控制输出的随机性，必须为正数\n取值范围是：(0.0,1.0]，不能等于 0,默认值为 0.95\n值越大，会使输出更随机，更具创造性；值越小，输出会更加稳定或确定\n建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数')
                            input_langchain_chatchat_knowledge_base_max_tokens = ui.input(label='max_tokens', value=config.get("langchain_chatchat", "knowledge_base", "max_tokens"), placeholder='大于0的正整数，不建议太大，你可能会爆显存')
                            input_langchain_chatchat_knowledge_base_prompt_name = ui.input(label='Prompt模板', value=config.get("langchain_chatchat", "knowledge_base", "prompt_name"), placeholder='本地存在的提示词模板文件名')
                with ui.row():
                    with ui.card().style(card_css):
                        ui.label("搜索引擎")
                        with ui.row():
                            lines = ['bing', 'duckduckgo', 'metaphor']
                            data_json = {}
                            for line in lines:
                                data_json[line] = line
                            select_langchain_chatchat_search_engine_search_engine_name = ui.select(
                                label='搜索引擎', 
                                options=data_json, 
                                value=config.get("langchain_chatchat", "search_engine", "search_engine_name")
                            )
                            input_langchain_chatchat_search_engine_top_k = ui.input(label='匹配搜索结果条数', value=config.get("langchain_chatchat", "search_engine", "top_k"), placeholder='匹配搜索结果条数')
                            input_langchain_chatchat_search_engine_model_name = ui.input(label='LLM模型', value=config.get("langchain_chatchat", "search_engine", "model_name"), placeholder='本地加载的LLM模型名')
                            input_langchain_chatchat_search_engine_temperature = ui.input(label='温度', value=config.get("langchain_chatchat", "search_engine", "temperature"), placeholder='采样温度，控制输出的随机性，必须为正数\n取值范围是：(0.0,1.0]，不能等于 0,默认值为 0.95\n值越大，会使输出更随机，更具创造性；值越小，输出会更加稳定或确定\n建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数')
                            input_langchain_chatchat_search_engine_max_tokens = ui.input(label='max_tokens', value=config.get("langchain_chatchat", "search_engine", "max_tokens"), placeholder='大于0的正整数，不建议太大，你可能会爆显存')
                            input_langchain_chatchat_search_engine_prompt_name = ui.input(label='Prompt模板', value=config.get("langchain_chatchat", "search_engine", "prompt_name"), placeholder='本地存在的提示词模板文件名')
            with ui.card().style(card_css):
                ui.label("智谱AI")
                with ui.row():
                    input_zhipu_api_key = ui.input(label='api key', placeholder='具体参考官方文档，申请地址：https://open.bigmodel.cn/usercenter/apikeys', value=config.get("zhipu", "api_key"))
                    input_zhipu_api_key.style("width:400px")
                    lines = ['chatglm_turbo', 'characterglm', 'chatglm_pro', 'chatglm_std', 'chatglm_lite', 'chatglm_lite_32k']
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_zhipu_model = ui.select(
                        label='模型', 
                        options=data_json, 
                        value=config.get("zhipu", "model")
                    )
                with ui.row():
                    input_zhipu_top_p = ui.input(label='top_p', placeholder='用温度取样的另一种方法，称为核取样\n取值范围是：(0.0,1.0)；开区间，不能等于 0 或 1，默认值为 0.7\n模型考虑具有 top_p 概率质量的令牌的结果。所以 0.1 意味着模型解码器只考虑从前 10% 的概率的候选集中取tokens\n建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数', value=config.get("zhipu", "top_p"))
                    input_zhipu_top_p.style("width:200px")
                    input_zhipu_temperature = ui.input(label='temperature', placeholder='采样温度，控制输出的随机性，必须为正数\n取值范围是：(0.0,1.0]，不能等于 0,默认值为 0.95\n值越大，会使输出更随机，更具创造性；值越小，输出会更加稳定或确定\n建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数', value=config.get("zhipu", "temperature"))
                    input_zhipu_temperature.style("width:200px")
                    switch_zhipu_history_enable = ui.switch('上下文记忆', value=config.get("zhipu", "history_enable")).style(switch_internal_css)
                    input_zhipu_history_max_len = ui.input(label='最大记忆长度', placeholder='最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米', value=config.get("zhipu", "history_max_len"))
                    input_zhipu_history_max_len.style("width:200px")
                with ui.row():
                    input_zhipu_user_info = ui.input(label='用户信息', placeholder='用户信息，当使用characterglm时需要配置', value=config.get("zhipu", "user_info"))
                    input_zhipu_user_info.style("width:400px")
                    input_zhipu_bot_info = ui.input(label='角色信息', placeholder='角色信息，当使用characterglm时需要配置', value=config.get("zhipu", "bot_info"))
                    input_zhipu_bot_info.style("width:400px")
                    input_zhipu_bot_name = ui.input(label='角色名称', placeholder='角色名称，当使用characterglm时需要配置', value=config.get("zhipu", "bot_name"))
                    input_zhipu_bot_name.style("width:200px")
                    input_zhipu_user_name = ui.input(label='用户名称', placeholder='用户名称，默认值为用户，当使用characterglm时需要配置', value=config.get("zhipu", "user_name"))
                    input_zhipu_user_name.style("width:200px")
                with ui.row():
                    switch_zhipu_remove_useless = ui.switch('删除无用字符', value=config.get("zhipu", "remove_useless")).style(switch_internal_css)
            with ui.card().style(card_css):
                ui.label("Bard")
                with ui.grid(columns=2):
                    input_bard_token = ui.input(label='token', placeholder='登录bard，打开F12，在cookie中获取 __Secure-1PSID 对应的值', value=config.get("bard", "token"))
                    input_bard_token.style("width:400px")
            with ui.card().style(card_css):
                ui.label("文心一言")
                with ui.row():
                    lines = ['api', 'web']
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_yiyan_type = ui.select(
                        label='类型', 
                        options=data_json, 
                        value=config.get("yiyan", "type")
                    ).style("width:100px")
                    switch_yiyan_history_enable = ui.switch('上下文记忆', value=config.get("yiyan", "history_enable")).style(switch_internal_css)
                    input_yiyan_history_max_len = ui.input(label='最大记忆长度', value=config.get("yiyan", "history_max_len"), placeholder='最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米')
                with ui.row(): 
                    input_yiyan_api_api_key = ui.input(label='API Key', placeholder='千帆大模型 应用接入的API Key', value=config.get("yiyan", "api", "api_key"))
                    input_yiyan_api_secret_key = ui.input(label='Secret Key', placeholder='千帆大模型 应用接入的Secret Key', value=config.get("yiyan", "api", "secret_key"))
                with ui.row():    
                    input_yiyan_web_api_ip_port = ui.input(label='API地址', placeholder='yiyan-api启动后监听的ip端口地址', value=config.get("yiyan", "web", "api_ip_port"))
                    input_yiyan_web_api_ip_port.style("width:300px")
                    input_yiyan_web_cookie = ui.input(label='cookie', placeholder='文心一言登录后，跳过debug后，抓取请求包中的cookie', value=config.get("yiyan", "web", "cookie"))
                    input_yiyan_web_cookie.style("width:300px")
            with ui.card().style(card_css):
                ui.label("通义星尘")
                with ui.row():
                    input_tongyixingchen_access_token = ui.input(label='密钥', value=config.get("tongyixingchen", "access_token"), placeholder='官网申请开通API-KEY，然后找官方申请调用权限')
                    lines = ['固定角色']
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_tongyixingchen_type = ui.select(
                        label='类型', 
                        options=data_json, 
                        value=config.get("tongyixingchen", "type")
                    ).style("width:100px")
                    switch_tongyixingchen_history_enable = ui.switch('上下文记忆', value=config.get("tongyixingchen", "history_enable")).style(switch_internal_css)
                    input_tongyixingchen_history_max_len = ui.input(label='最大记忆长度', value=config.get("tongyixingchen", "history_max_len"), placeholder='最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米')
                with ui.card().style(card_css):
                    ui.label("固定角色")
                    with ui.row():
                        input_tongyixingchen_GDJS_character_id = ui.input(label='角色ID', value=config.get("tongyixingchen", "固定角色", "character_id"), placeholder='官网聊天页，创建的角色，然后点开角色的信息，可以看见ID')
                        input_tongyixingchen_GDJS_top_p = ui.input(label='top_p', value=config.get("tongyixingchen", "固定角色", "top_p"), placeholder='topP生成时，核采样方法的概率阈值。例如，取值为0.8时，仅保留累计概率之和大于等于0.8的概率分布中的token，作为随机采样的候选集。取值范围为(0,1.0)，取值越大，生成的随机性越高；取值越低，生成的随机性越低。默认值 0.95。注意，取值不要大于等于1')
                        input_tongyixingchen_GDJS_temperature = ui.input(label='temperature', value=config.get("tongyixingchen", "固定角色", "temperature"), placeholder='较高的值将使输出更加随机，而较低的值将使输出更加集中和确定。可选，默认取值0.92')
                        input_tongyixingchen_GDJS_seed = ui.input(label='seed', value=config.get("tongyixingchen", "固定角色", "seed"), placeholder='seed生成时，随机数的种子，用于控制模型生成的随机性。如果使用相同的种子，每次运行生成的结果都将相同；当需要复现模型的生成结果时，可以使用相同的种子。seed参数支持无符号64位整数类型。默认值 1683806810')
                    with ui.row():
                        input_tongyixingchen_GDJS_user_id = ui.input(label='用户ID', value=config.get("tongyixingchen", "固定角色", "user_id"), placeholder='业务系统用户唯一标识，同一用户不能并行对话，必须待上次对话回复结束后才可发起下轮对话')
                        input_tongyixingchen_GDJS_user_name = ui.input(label='对话用户名称', value=config.get("tongyixingchen", "固定角色", "user_name"), placeholder='对话用户名称，即你的名字')
                        input_tongyixingchen_GDJS_role_name = ui.input(label='固定角色名称', value=config.get("tongyixingchen", "固定角色", "role_name"), placeholder='角色ID对应的角色名称，自己编写的别告诉我你不知道！')
            with ui.card().style(card_css):
                ui.label("千帆大模型")
                with ui.row():
                    input_my_wenxinworkshop_api_key = ui.input(label='api_key', value=config.get("my_wenxinworkshop", "api_key"), placeholder='千帆大模型平台，开通对应服务。应用接入-创建应用，填入api key')
                    input_my_wenxinworkshop_secret_key = ui.input(label='secret_key', value=config.get("my_wenxinworkshop", "secret_key"), placeholder='千帆大模型平台，开通对应服务。应用接入-创建应用，填入secret key')
                    lines = [
                        "ERNIEBot",
                        "ERNIEBot_turbo",
                        "ERNIEBot_4_0",
                        "BLOOMZ_7B",
                        "LLAMA_2_7B",
                        "LLAMA_2_13B",
                        "LLAMA_2_70B",
                        "ERNIEBot_4_0",
                        "QIANFAN_BLOOMZ_7B_COMPRESSED",
                        "QIANFAN_CHINESE_LLAMA_2_7B",
                        "CHATGLM2_6B_32K",
                        "AQUILACHAT_7B",
                        "ERNIE_BOT_8K",
                        "CODELLAMA_7B_INSTRUCT",
                        "XUANYUAN_70B_CHAT",
                        "CHATLAW",
                        "QIANFAN_BLOOMZ_7B_COMPRESSED",
                    ]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_my_wenxinworkshop_model = ui.select(
                        label='模型', 
                        options=data_json, 
                        value=config.get("my_wenxinworkshop", "model")
                    ).style("width:150px")
                    switch_my_wenxinworkshop_history_enable = ui.switch('上下文记忆', value=config.get("my_wenxinworkshop", "history_enable")).style(switch_internal_css)
                    input_my_wenxinworkshop_history_max_len = ui.input(label='最大记忆长度', value=config.get("my_wenxinworkshop", "history_max_len"), placeholder='最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米')
                with ui.row():
                    input_my_wenxinworkshop_temperature = ui.input(label='温度', value=config.get("my_wenxinworkshop", "temperature"), placeholder='(0, 1.0] 控制生成文本的随机性。较高的温度值会使生成的文本更随机和多样化，而较低的温度值会使生成的文本更加确定和一致。').style("width:200px;")
                    input_my_wenxinworkshop_top_p = ui.input(label='前p个选择', value=config.get("my_wenxinworkshop", "top_p"), placeholder='[0, 1.0] Nucleus采样。这个参数控制模型从累积概率大于一定阈值的令牌中进行采样。较高的值会产生更多的多样性，较低的值会产生更少但更确定的回答。').style("width:200px;")
                    input_my_wenxinworkshop_penalty_score = ui.input(label='惩罚得分', value=config.get("my_wenxinworkshop", "penalty_score"), placeholder='[1.0, 2.0] 在生成文本时对某些词语或模式施加的惩罚。这是一种调节生成内容的机制，用来减少或避免不希望出现的内容。').style("width:200px;")
                    
            # with ui.card().style(card_css):
            #     ui.label("千帆大模型（兼容问题暂不启用）")
            #     with ui.row():
            #         input_my_qianfan_access_key = ui.input(label='access_key', value=config.get("my_qianfan", "access_key"), placeholder='官网右上角安全认证申请开通access_key')
            #         input_my_qianfan_secret_key = ui.input(label='secret_key', value=config.get("my_qianfan", "secret_key"), placeholder='官网右上角安全认证申请开通access_key')
            #         lines = [
            #             'ERNIE-Bot-turbo', 
            #             'ERNIE-Bot',
            #             'ERNIE-Bot-4',
            #             'BLOOMZ-7B',
            #             'Llama-2-7b-chat',
            #             'Llama-2-13b-chat',
            #             'Llama-2-70b-chat',
            #             'Qianfan-BLOOMZ-7B-compressed',
            #             'Qianfan-Chinese-Llama-2-7B',
            #             'ChatGLM2-6B-32K',
            #             'AquilaChat-7B'
            #         ]
            #         data_json = {}
            #         for line in lines:
            #             data_json[line] = line
            #         select_my_qianfan_model = ui.select(
            #             label='模型', 
            #             options=data_json, 
            #             value=config.get("my_qianfan", "model")
            #         ).style("width:150px")
            #         switch_my_qianfan_history_enable = ui.switch('上下文记忆', value=config.get("my_qianfan", "history_enable")).style(switch_internal_css)
            #         input_my_qianfan_history_max_len = ui.input(label='最大记忆长度', value=config.get("my_qianfan", "history_max_len"), placeholder='最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米')
            #     with ui.row():
            #         input_my_qianfan_temperature = ui.input(label='温度', value=config.get("my_qianfan", "temperature"), placeholder='控制生成文本的随机性。较高的温度值会使生成的文本更随机和多样化，而较低的温度值会使生成的文本更加确定和一致。').style("width:200px;")
            #         input_my_qianfan_top_p = ui.input(label='前p个选择', value=config.get("my_qianfan", "top_p"), placeholder='Nucleus采样。这个参数控制模型从累积概率大于一定阈值的令牌中进行采样。较高的值会产生更多的多样性，较低的值会产生更少但更确定的回答。').style("width:200px;")
            #         input_my_qianfan_penalty_score = ui.input(label='惩罚得分', value=config.get("my_qianfan", "penalty_score"), placeholder='在生成文本时对某些词语或模式施加的惩罚。这是一种调节生成内容的机制，用来减少或避免不希望出现的内容。').style("width:200px;")
            with ui.card().style(card_css):
                ui.label("Gemini")
                with ui.row():
                    input_gemini_api_key = ui.input(label='api_key', value=config.get("gemini", "api_key"), placeholder='谷歌AI Studio创建api key')
                    lines = [
                        "gemini-pro",
                    ]
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_gemini_model = ui.select(
                        label='模型', 
                        options=data_json, 
                        value=config.get("gemini", "model")
                    ).style("width:150px")
                    switch_gemini_history_enable = ui.switch('上下文记忆', value=config.get("gemini", "history_enable")).style(switch_internal_css)
                    input_gemini_history_max_len = ui.input(label='最大记忆长度', value=config.get("gemini", "history_max_len"), placeholder='最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米')
                with ui.row():
                    input_gemini_http_proxy = ui.input(label='HTTP代理地址', value=config.get("gemini", "http_proxy"), placeholder='http代理地址，需要魔法才能使用，所以需要配置此项。').style("width:200px;")
                    input_gemini_https_proxy = ui.input(label='HTTPS代理地址', value=config.get("gemini", "https_proxy"), placeholder='https代理地址，需要魔法才能使用，所以需要配置此项。').style("width:200px;")
                with ui.row():
                    input_gemini_max_output_tokens = ui.input(label='最大输出token数', value=config.get("gemini", "max_output_tokens"), placeholder='候选输出中包含的最大token数')
                    input_gemini_max_temperature = ui.input(label='temperature', value=config.get("gemini", "temperature"), placeholder='控制输出的随机性。值范围为[0.0,1.0]，包括0.0和1.0。值越接近1.0，生成的响应将更加多样化和创造性，而值越接近0.0，通常会导致模型产生更加直接的响应。')
                    input_gemini_top_p = ui.input(label='top_p', value=config.get("gemini", "top_p"), placeholder='在抽样时考虑的标记的最大累积概率。根据其分配的概率对标记进行排序，以仅考虑最可能的标记。Top-k采样直接限制要考虑的标记的最大数量，而Nucleus采样则基于累积概率限制标记的数量。')
                    input_gemini_top_k = ui.input(label='top_k', value=config.get("gemini", "top_k"), placeholder='在抽样时考虑的标记的最大数量。Top-k采样考虑一组top_k最有可能的标记。默认值为40。')
                     
            with ui.card().style(card_css):
                ui.label("通义千问")
                with ui.row():
                    lines = ['web']
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_tongyi_type = ui.select(
                        label='模型', 
                        options=data_json, 
                        value=config.get("tongyi", "type")
                    )
                    input_tongyi_cookie_path = ui.input(label='cookie路径', placeholder='通义千问登录后，通过浏览器插件Cookie Editor获取Cookie JSON串，然后将数据保存在这个路径的文件中', value=config.get("tongyi", "cookie_path"))
                    input_tongyi_cookie_path.style("width:400px")
        with ui.tab_panel(tts_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label("Edge-TTS")
                with ui.row():
                    with open('data/edge-tts-voice-list.txt', 'r') as file:
                        file_content = file.read()
                    # 按行分割内容，并去除每行末尾的换行符
                    lines = file_content.strip().split('\n')
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_edge_tts_voice = ui.select(
                        label='说话人', 
                        options=data_json, 
                        value=config.get("edge-tts", "voice")
                    )

                    input_edge_tts_rate = ui.input(label='语速增益', placeholder='语速增益 默认是 +0%，可以增减，注意 + - %符合别搞没了，不然会影响语音合成', value=config.get("edge-tts", "rate")).style("width:200px;")

                    input_edge_tts_volume = ui.input(label='音量增益', placeholder='音量增益 默认是 +0%，可以增减，注意 + - %符合别搞没了，不然会影响语音合成', value=config.get("edge-tts", "volume")).style("width:200px;")
            with ui.card().style(card_css):
                ui.label("VITS")
                with ui.row():
                    select_vits_type = ui.select(
                        label='类型', 
                        options={'vits': 'vits', 'bert_vits2': 'bert_vits2'}, 
                        value=config.get("vits", "type")
                    ).style("width:200px;")
                    input_vits_config_path = ui.input(label='配置文件路径', placeholder='模型配置文件存储路径', value=config.get("vits", "config_path")).style("width:200px;")

                    input_vits_api_ip_port = ui.input(label='API地址', placeholder='vits-simple-api启动后监听的ip端口地址', value=config.get("vits", "api_ip_port")).style("width:300px;")
                with ui.row():
                    input_vits_id = ui.input(label='说话人ID', placeholder='API启动时会给配置文件重新划分id，一般为拼音顺序排列，从0开始', value=config.get("vits", "id")).style("width:200px;")

                    select_vits_lang = ui.select(
                        label='语言', 
                        options={'自动': '自动', '中文': '中文', '英文': '英文', '日文': '日文'}, 
                        value=config.get("vits", "lang")
                    ).style("width:100px;")
                    input_vits_length = ui.input(label='语音长度', placeholder='调节语音长度，相当于调节语速，该数值越大语速越慢', value=config.get("vits", "length")).style("width:200px;")

                with ui.row():
                    input_vits_noise = ui.input(label='噪声', placeholder='控制感情变化程度', value=config.get("vits", "noise")).style("width:200px;")
                
                    input_vits_noisew = ui.input(label='噪声偏差', placeholder='控制音素发音长度', value=config.get("vits", "noisew")).style("width:200px;")

                    input_vits_max = ui.input(label='分段阈值', placeholder='按标点符号分段，加起来大于max时为一段文本。max<=0表示不分段。', value=config.get("vits", "max")).style("width:200px;")
                    input_vits_format = ui.input(label='音频格式', placeholder='支持wav,ogg,silk,mp3,flac', value=config.get("vits", "format")).style("width:200px;")

                    input_vits_sdp_radio = ui.input(label='SDP/DP混合比', placeholder='SDP/DP混合比：SDP在合成时的占比，理论上此比率越高，合成的语音语调方差越大。', value=config.get("vits", "sdp_radio")).style("width:200px;")
            with ui.card().style(card_css):
                ui.label("bert_vits2")
                with ui.row():
                    select_bert_vits2_type = ui.select(
                        label='类型', 
                        options={'hiyori': 'hiyori'}, 
                        value=config.get("bert_vits2", "type")
                    ).style("width:200px;")
                    input_bert_vits2_api_ip_port = ui.input(label='API地址', placeholder='bert_vits2启动后Hiyori UI后监听的ip端口地址', value=config.get("bert_vits2", "api_ip_port")).style("width:300px;")
                with ui.row():
                    input_vits_model_id = ui.input(label='模型ID', placeholder='给配置文件重新划分id，一般为拼音顺序排列，从0开始', value=config.get("bert_vits2", "model_id")).style("width:200px;")
                    input_vits_speaker_name = ui.input(label='说话人名称', value=config.get("bert_vits2", "speaker_name"), placeholder='配置文件中，对应的说话人的名称').style("width:200px;")
                    input_vits_speaker_id = ui.input(label='说话人ID', value=config.get("bert_vits2", "speaker_id"), placeholder='给配置文件重新划分id，一般为拼音顺序排列，从0开始').style("width:200px;")
                    
                    select_bert_vits2_language = ui.select(
                        label='语言', 
                        options={'auto': '自动', 'ZH': '中文', 'JP': '日文', 'EN': '英文'}, 
                        value=config.get("bert_vits2", "language")
                    ).style("width:100px;")
                    input_bert_vits2_length = ui.input(label='语音长度', placeholder='调节语音长度，相当于调节语速，该数值越大语速越慢', value=config.get("bert_vits2", "length")).style("width:200px;")

                with ui.row():
                    input_bert_vits2_noise = ui.input(label='噪声', value=config.get("bert_vits2", "noise"), placeholder='控制感情变化程度').style("width:200px;")
                    input_bert_vits2_noisew = ui.input(label='噪声偏差', value=config.get("bert_vits2", "noisew"), placeholder='控制音素发音长度').style("width:200px;")
                    input_bert_vits2_sdp_radio = ui.input(label='SDP/DP混合比', value=config.get("bert_vits2", "sdp_radio"), placeholder='SDP/DP混合比：SDP在合成时的占比，理论上此比率越高，合成的语音语调方差越大。').style("width:200px;")
                with ui.row():
                    input_bert_vits2_emotion = ui.input(label='emotion', value=config.get("bert_vits2", "emotion"), placeholder='emotion').style("width:200px;")
                    input_bert_vits2_style_text = ui.input(label='风格文本', value=config.get("bert_vits2", "style_text"), placeholder='style_text').style("width:200px;")
                    input_bert_vits2_style_weight = ui.input(label='风格权重', value=config.get("bert_vits2", "style_weight"), placeholder='主文本和辅助文本的bert混合比率，0表示仅主文本，1表示仅辅助文本0.7').style("width:200px;")
                    switch_bert_vits2_auto_translate = ui.switch('自动翻译', value=config.get("bert_vits2", "auto_translate")).style(switch_internal_css)
                    switch_bert_vits2_auto_split = ui.switch('自动切分', value=config.get("bert_vits2", "auto_split")).style(switch_internal_css)
                    
            with ui.card().style(card_css):
                ui.label("VITS-Fast")
                with ui.row():
                    input_vits_fast_config_path = ui.input(label='配置文件路径', placeholder='配置文件的路径，例如：E:\\inference\\finetune_speaker.json', value=config.get("vits_fast", "config_path"))
    
                    input_vits_fast_api_ip_port = ui.input(label='API地址', placeholder='推理服务运行的链接（需要完整的URL）', value=config.get("vits_fast", "api_ip_port"))
                    input_vits_fast_character = ui.input(label='说话人', placeholder='选择的说话人，配置文件中的speaker中的其中一个', value=config.get("vits_fast", "character"))

                    select_vits_fast_language = ui.select(
                        label='语言', 
                        options={'自动识别': '自动识别', '日本語': '日本語', '简体中文': '简体中文', 'English': 'English', 'Mix': 'Mix'}, 
                        value=config.get("vits_fast", "language")
                    )
                    input_vits_fast_speed = ui.input(label='语速', placeholder='语速，默认为1', value=config.get("vits_fast", "speed"))
            with ui.card().style(card_css):
                ui.label("elevenlabs")
                with ui.row():
                    input_elevenlabs_api_key = ui.input(label='api密钥', placeholder='elevenlabs密钥，可以不填，默认也有一定额度的免费使用权限，具体多少不知道', value=config.get("elevenlabs", "api_key"))

                    input_elevenlabs_voice = ui.input(label='说话人', placeholder='选择的说话人名', value=config.get("elevenlabs", "voice"))

                    input_elevenlabs_model = ui.input(label='模型', placeholder='选择的模型', value=config.get("elevenlabs", "model"))
            with ui.card().style(card_css):
                ui.label("genshinvoice.top")
                with ui.row():
                    with open('data/genshinvoice_top_speak_list.txt', 'r', encoding='utf-8') as file:
                        file_content = file.read()
                    # 按行分割内容，并去除每行末尾的换行符
                    lines = file_content.strip().split('\n')
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_genshinvoice_top_speaker = ui.select(
                        label='角色', 
                        options=data_json, 
                        value=config.get("genshinvoice_top", "speaker")
                    )

                    input_genshinvoice_top_noise = ui.input(label='感情', placeholder='控制感情变化程度，默认为0.2', value=config.get("genshinvoice_top", "noise"))
                    input_genshinvoice_top_noisew = ui.input(label='音素长度', placeholder='控制音节发音长度变化程度，默认为0.9', value=config.get("genshinvoice_top", "noisew"))
                    input_genshinvoice_top_length = ui.input(label='语速', placeholder='可用于控制整体语速。默认为1.2', value=config.get("genshinvoice_top", "length"))
                    input_genshinvoice_top_format = ui.input(label='格式', placeholder='原有接口以WAV格式合成语音，在MP3格式合成语音的情况下，涉及到音频格式转换合成速度会变慢，建议选择WAV格式', value=config.get("genshinvoice_top", "format"))
                    select_genshinvoice_top_language = ui.select(
                        label='语言', 
                        options={'ZH': 'ZH', 'EN': 'EN', 'JP': 'JP'}, 
                        value=config.get("genshinvoice_top", "language")
                    ).style("width:100px")
            with ui.card().style(card_css):
                ui.label("tts.ai-lab.top")
                with ui.row():
                    with open('data/tts_ai_lab_top_speak_list.txt', 'r', encoding='utf-8') as file:
                        file_content = file.read()
                    # 按行分割内容，并去除每行末尾的换行符
                    lines = file_content.strip().split('\n')
                    data_json = {}
                    for line in lines:
                        data_json[line] = line
                    select_tts_ai_lab_top_speaker = ui.select(
                        label='角色', 
                        options=data_json, 
                        value=config.get("tts_ai_lab_top", "speaker")
                    )
                    input_tts_ai_lab_top_appid = ui.input(label='appid', placeholder='前往 https://tts.ai-hobbyist.org/，F12抓合成请求包，在负载中获取', value=config.get("tts_ai_lab_top", "appid"))
                    input_tts_ai_lab_top_token = ui.input(label='token', placeholder='前往 https://tts.ai-hobbyist.org/，F12抓合成请求包，在负载中获取', value=config.get("tts_ai_lab_top", "token"))
                    input_tts_ai_lab_top_noise = ui.input(label='感情', placeholder='控制感情变化程度，默认为0.2', value=config.get("tts_ai_lab_top", "noise"))
                    input_tts_ai_lab_top_noisew = ui.input(label='音素长度', placeholder='控制音节发音长度变化程度，默认为0.9', value=config.get("tts_ai_lab_top", "noisew"))
                    input_tts_ai_lab_top_length = ui.input(label='语速', placeholder='可用于控制整体语速。默认为1.2', value=config.get("tts_ai_lab_top", "length"))
                    input_tts_ai_lab_top_sdp_ratio = ui.input(label='SDP/DP混合比', placeholder='SDP/DP混合比：SDP在合成时的占比，理论上此比率越高，合成的语音语调方差越大。', value=config.get("tts_ai_lab_top", "sdp_ratio"))
            
            with ui.card().style(card_css):
                ui.label("bark_gui")
                with ui.row():
                    input_bark_gui_api_ip_port = ui.input(label='API地址', placeholder='bark-gui开启webui后监听的IP和端口地址', value=config.get("bark_gui", "api_ip_port")).style("width:200px;")
                    input_bark_gui_spk = ui.input(label='说话人', placeholder='选择的说话人，webui的voice中对应的说话人', value=config.get("bark_gui", "spk")).style("width:200px;")

                    input_bark_gui_generation_temperature = ui.input(label='生成温度', placeholder='控制合成过程中生成语音的随机性。较高的值（接近1.0）会使输出更加随机，而较低的值（接近0.0）则使其更加确定性和集中。', value=config.get("bark_gui", "generation_temperature")).style("width:200px;")
                    input_bark_gui_waveform_temperature = ui.input(label='波形温度', placeholder='类似于generation_temperature，但该参数专门控制从语音模型生成的波形的随机性', value=config.get("bark_gui", "waveform_temperature")).style("width:200px;")
                with ui.row():
                    input_bark_gui_end_of_sentence_probability = ui.input(label='句末概率', placeholder='该参数确定在句子结尾添加停顿或间隔的可能性。较高的值会增加停顿的几率，而较低的值则会减少。', value=config.get("bark_gui", "end_of_sentence_probability")).style("width:200px;")
                    switch_bark_gui_quick_generation = ui.switch('快速生成', value=config.get("bark_gui", "quick_generation")).style(switch_internal_css)
                    input_bark_gui_seed = ui.input(label='随机种子', placeholder='用于随机数生成器的种子值。使用特定的种子确保相同的输入文本每次生成的语音输出都是相同的。值为-1表示将使用随机种子。', value=config.get("bark_gui", "seed")).style("width:200px;")
                    input_bark_gui_batch_count = ui.input(label='批量数', placeholder='指定一次批量合成的句子或话语数量。将其设置为1意味着逐句合成一次。', value=config.get("bark_gui", "batch_count")).style("width:200px;")
            with ui.card().style(card_css):
                ui.label("vall_e_x")
                with ui.row():
                    input_vall_e_x_api_ip_port = ui.input(label='API地址', placeholder='VALL-E-X启动后监听的ip端口地址', value=config.get("vall_e_x", "api_ip_port")).style("width:200px;")
                    select_vall_e_x_language = ui.select(
                        label='language', 
                        options={'auto-detect':'auto-detect', 'English':'English', '中文':'中文', '日本語':'日本語', 'Mix':'Mix'}, 
                        value=config.get("vall_e_x", "language")
                    ).style("width:200px;")

                    select_vall_e_x_accent = ui.select(
                        label='accent', 
                        options={'no-accent':'no-accent', 'English':'English', '中文':'中文', '日本語':'日本語'}, 
                        value=config.get("vall_e_x", "accent")
                    ).style("width:200px;")

                    input_vall_e_x_voice_preset = ui.input(label='voice preset', placeholder='VALL-E-X说话人预设名（Prompt name）', value=config.get("vall_e_x", "voice_preset")).style("width:300px;")
                    input_vall_e_x_voice_preset_file_path = ui.input(label='voice_preset_file_path', placeholder='VALL-E-X说话人预设文件路径（npz）', value=config.get("vall_e_x", "voice_preset_file_path")).style("width:300px;")
            with ui.card().style(card_css):
                ui.label("OpenAI TTS")
                with ui.row():
                    select_openai_tts_type = ui.select(
                        label='类型', 
                        options={'api': 'api', 'huggingface': 'huggingface'}, 
                        value=config.get("openai_tts", "type")
                    ).style("width:200px;")
                    input_openai_tts_api_ip_port = ui.input(label='API地址', value=config.get("openai_tts", "api_ip_port"), placeholder='huggingface上对应项目的API地址').style("width:200px;")
                with ui.row():
                    select_openai_tts_model = ui.select(
                        label='模型', 
                        options={'tts-1': 'tts-1', 'tts-1-hd': 'tts-1-hd'}, 
                        value=config.get("openai_tts", "model")
                    ).style("width:200px;")
                    select_openai_tts_voice = ui.select(
                        label='说话人', 
                        options={'alloy': 'alloy', 'echo': 'echo', 'fable': 'fable', 'onyx': 'onyx', 'nova': 'nova', 'shimmer': 'shimmer'}, 
                        value=config.get("openai_tts", "voice")
                    ).style("width:200px;")
                    input_openai_tts_api_key = ui.input(label='api key', value=config.get("openai_tts", "api_key"), placeholder='OpenAI API KEY').style("width:200px;")
            with ui.card().style(card_css):
                ui.label("睿声AI")
                with ui.row():
                    input_reecho_ai_Authorization = ui.input(label='API Key', value=config.get("reecho_ai", "Authorization"), placeholder='API Key').style("width:200px;")
                    input_reecho_ai_model = ui.input(label='模型ID', value=config.get("reecho_ai", "model"), placeholder='要使用的模型ID (目前统一为reecho-neural-voice-001)').style("width:200px;")
                    input_reecho_ai_voiceId = ui.input(label='角色ID', value=config.get("reecho_ai", "voiceId"), placeholder='要使用的角色ID，必须位于账号的角色列表库中，记得展开详情').style("width:300px;")
                with ui.row():
                    number_reecho_ai_randomness = ui.number(label='随机度', value=config.get("reecho_ai", "randomness"), format='%d', min=0, max=100, step=1, placeholder='随机度 (0-100，默认请填写97)').style("width:200px;")
                    number_reecho_ai_stability_boost = ui.number(label='稳定性增强', value=config.get("reecho_ai", "stability_boost"), format='%d', min=0, max=100, step=1, placeholder='稳定性增强 (0-100，默认请填写40)').style("width:200px;")
            with ui.card().style(card_css):
                ui.label("Gradio")
                with ui.row():
                    textarea_gradio_tts_request_parameters = ui.textarea(label='请求参数', value=config.get("gradio_tts", "request_parameters"), placeholder='一定要注意格式啊！{content}用于替换待合成的文本。\nurl是请求地址；\nfn_index是api对应的索引；\ndata_analysis是数据解析规则，暂时只支持元组和列表数据的index索引，请参考模板进行配置\n键不影响请求，需要注意的是参数顺序需要和API请求保持一致\n那么数据可以用json库将dict转成str，这样再用来配置就可靠很多').style("width:800px;")
            with ui.card().style(card_css):
                ui.label("GPT-SoVITS")
                with ui.row():
                    input_gpt_sovits_api_ip_port = ui.input(label='API地址（WS）', value=config.get("gpt_sovits", "api_ip_port"), placeholder='启动TTS推理后，ws的接口地址').style("width:200px;")
                    input_gpt_sovits_ref_audio_path = ui.input(label='参考音频路径', value=config.get("gpt_sovits", "ref_audio_path"), placeholder='参考音频路径，建议填绝对路径').style("width:200px;")
                    input_gpt_sovits_prompt_text = ui.input(label='参考音频的文本', value=config.get("gpt_sovits", "prompt_text"), placeholder='参考音频的文本').style("width:200px;")
                    select_gpt_sovits_prompt_language = ui.select(
                        label='参考音频的语种', 
                        options={'中文':'中文', '日文':'日文', '英文':'英文'}, 
                        value=config.get("gpt_sovits", "prompt_language")
                    ).style("width:200px;")
                    select_gpt_sovits_language = ui.select(
                        label='需要合成的语种', 
                        options={'自动识别':'自动识别', '中文':'中文', '日文':'日文', '英文':'英文'}, 
                        value=config.get("gpt_sovits", "language")
                    ).style("width:200px;")
        
        with ui.tab_panel(svc_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label("DDSP-SVC")
                with ui.row():
                    switch_ddsp_svc_enable = ui.switch('启用', value=config.get("ddsp_svc", "enable")).style(switch_internal_css)
                    input_ddsp_svc_config_path = ui.input(label='配置文件路径', placeholder='模型配置文件config.yaml的路径(此处可以不配置，暂时没有用到)', value=config.get("ddsp_svc", "config_path"))
                    input_ddsp_svc_config_path.style("width:400px")

                    input_ddsp_svc_api_ip_port = ui.input(label='API地址', placeholder='flask_api服务运行的ip端口，例如：http://127.0.0.1:6844', value=config.get("ddsp_svc", "api_ip_port"))
                    input_ddsp_svc_api_ip_port.style("width:400px")
                    input_ddsp_svc_fSafePrefixPadLength = ui.input(label='安全前缀填充长度', placeholder='安全前缀填充长度，不知道干啥用，默认为0', value=config.get("ddsp_svc", "fSafePrefixPadLength"))
                    input_ddsp_svc_fSafePrefixPadLength.style("width:300px")
                with ui.row():
                    input_ddsp_svc_fPitchChange = ui.input(label='变调', placeholder='音调设置，默认为0', value=config.get("ddsp_svc", "fPitchChange"))
                    input_ddsp_svc_fPitchChange.style("width:300px")
                    input_ddsp_svc_sSpeakId = ui.input(label='说话人ID', placeholder='说话人ID，需要和模型数据对应，默认为0', value=config.get("ddsp_svc", "sSpeakId"))
                    input_ddsp_svc_sSpeakId.style("width:400px")

                    input_ddsp_svc_sampleRate = ui.input(label='采样率', placeholder='DAW所需的采样率，默认为44100', value=config.get("ddsp_svc", "sampleRate"))
                    input_ddsp_svc_sampleRate.style("width:300px")
            with ui.card().style(card_css):
                ui.label("SO-VITS-SVC")
                with ui.row():
                    switch_so_vits_svc_enable = ui.switch('启用', value=config.get("so_vits_svc", "enable")).style(switch_internal_css)
                    input_so_vits_svc_config_path = ui.input(label='配置文件路径', placeholder='模型配置文件config.json的路径', value=config.get("so_vits_svc", "config_path"))
                    input_so_vits_svc_config_path.style("width:400px")
                with ui.grid(columns=2):
                    input_so_vits_svc_api_ip_port = ui.input(label='API地址', placeholder='flask_api_full_song服务运行的ip端口，例如：http://127.0.0.1:1145', value=config.get("so_vits_svc", "api_ip_port"))
                    input_so_vits_svc_api_ip_port.style("width:400px")
                    input_so_vits_svc_spk = ui.input(label='说话人', placeholder='说话人，需要和配置文件内容对应', value=config.get("so_vits_svc", "spk"))
                    input_so_vits_svc_spk.style("width:400px") 
                    input_so_vits_svc_tran = ui.input(label='音调', placeholder='音调设置，默认为1', value=config.get("so_vits_svc", "tran"))
                    input_so_vits_svc_tran.style("width:300px")
                    input_so_vits_svc_wav_format = ui.input(label='输出音频格式', placeholder='音频合成后输出的格式', value=config.get("so_vits_svc", "wav_format"))
                    input_so_vits_svc_wav_format.style("width:300px") 
        with ui.tab_panel(visual_body_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label("Live2D")
                with ui.row():
                    switch_live2d_enable = ui.switch('启用', value=config.get("live2d", "enable")).style(switch_internal_css)
                    input_live2d_port = ui.input(label='端口', value=config.get("live2d", "port"), placeholder='web服务运行的端口号，默认：12345，范围:0-65535，没事不要乱改就好')
                    # input_live2d_name = ui.input(label='模型名', value=config.get("live2d", "name"), placeholder='模型名称，模型存放于Live2D\live2d-model路径下，请注意路径和模型内容是否匹配')
            with ui.card().style(card_css):
                ui.label("xuniren")
                with ui.row():
                    input_xuniren_api_ip_port = ui.input(label='API地址', value=config.get("xuniren", "api_ip_port"), placeholder='xuniren应用启动API后，监听的ip和端口')
            with ui.card().style(card_css):
                ui.label("Unity")
                with ui.row():
                    # switch_unity_enable = ui.switch('启用', value=config.get("unity", "enable")).style(switch_internal_css)
                    input_unity_api_ip_port = ui.input(label='API地址', value=config.get("unity", "api_ip_port"), placeholder='对接Unity应用使用的HTTP中转站监听的ip和端口')
                    input_unity_password = ui.input(label='密码', value=config.get("unity", "password"), placeholder='对接Unity应用使用的HTTP中转站的密码')
                    
        with ui.tab_panel(copywriting_page).style(tab_panel_css):
            with ui.row():
                switch_copywriting_auto_play = ui.switch('自动播放', value=config.get("copywriting", "auto_play")).style(switch_internal_css)
                switch_copywriting_random_play = ui.switch('音频随机播放', value=config.get("copywriting", "random_play")).style(switch_internal_css)
                input_copywriting_audio_interval = ui.input(label='音频播放间隔', value=config.get("copywriting", "audio_interval"), placeholder='文案音频播放之间的间隔时间。就是前一个文案播放完成后，到后一个文案开始播放之间的间隔时间。')
                input_copywriting_switching_interval = ui.input(label='音频切换间隔', value=config.get("copywriting", "switching_interval"), placeholder='文案音频切换到弹幕音频的切换间隔时间（反之一样）。\n就是在播放文案时，有弹幕触发并合成完毕，此时会暂停文案播放，然后等待这个间隔时间后，再播放弹幕回复音频。')
            with ui.row():
                input_copywriting_index = ui.input(label='文案索引', value="", placeholder='文案组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
                button_copywriting_add = ui.button('增加文案组', on_click=copywriting_add, color=button_internal_color).style(button_internal_css)
                button_copywriting_del = ui.button('删除文案组', on_click=lambda: copywriting_del(input_copywriting_index.value), color=button_internal_color).style(button_internal_css)

            copywriting_config_var = {}
            copywriting_config_card = ui.card()
            for index, copywriting_config in enumerate(config.get("copywriting", "config")):
                with copywriting_config_card.style(card_css):
                    with ui.row():
                        copywriting_config_var[str(5 * index)] = ui.input(label=f"文案存储路径#{index + 1}", value=copywriting_config["file_path"], placeholder='文案文件存储路径。不建议更改。').style("width:200px;")
                        copywriting_config_var[str(5 * index + 1)] = ui.input(label=f"音频存储路径#{index + 1}", value=copywriting_config["audio_path"], placeholder='文案音频文件存储路径。不建议更改。').style("width:200px;")
                        copywriting_config_var[str(5 * index + 2)] = ui.input(label=f"连续播放数#{index + 1}", value=copywriting_config["continuous_play_num"], placeholder='文案播放列表中连续播放的音频文件个数，如果超过了这个个数就会切换下一个文案列表').style("width:200px;")
                        copywriting_config_var[str(5 * index + 3)] = ui.input(label=f"连续播放时间#{index + 1}", value=copywriting_config["max_play_time"], placeholder='文案播放列表中连续播放音频的时长，如果超过了这个时长就会切换下一个文案列表').style("width:200px;")
                        copywriting_config_var[str(5 * index + 4)] = ui.textarea(label=f"播放列表#{index + 1}", value=textarea_data_change(copywriting_config["play_list"]), placeholder='此处填写需要播放的音频文件全名，填写完毕后点击 保存配置。文件全名从音频列表中复制，换行分隔，请勿随意填写').style("width:500px;")

            with ui.card().style(card_css):
                ui.label("文案音频合成")
                with ui.row():
                    input_copywriting_text_path = ui.input(label='文案文本路径', value=config.get("copywriting", "text_path"), placeholder='待合成的文案文本文件的路径').style("width:250px;")
                    button_copywriting_text_load = ui.button('加载文本', on_click=copywriting_text_load, color=button_internal_color).style(button_internal_css)
                    input_copywriting_audio_save_path = ui.input(label='音频存储路径', value=config.get("copywriting", "audio_save_path"), placeholder='音频合成后存储的路径').style("width:250px;")
                    # input_copywriting_chunking_stop_time = ui.input(label='断句停顿时长', value=config.get("copywriting", "chunking_stop_time"), placeholder='自动根据标点断句后，2个句子之间的无声时长').style("width:150px;")
                with ui.row():
                    textarea_copywriting_text = ui.textarea(label='文案文本', value='', placeholder='此处对需要合成文案音频的文本内容进行编辑。文案会自动根据逻辑进行切分，然后根据配置合成完整的一个音频文件。').style("width:1000px;")
                with ui.row():
                    button_copywriting_save_text = ui.button('保存文案', on_click=copywriting_save_text, color=button_internal_color).style(button_internal_css)
                    button_copywriting_audio_synthesis = ui.button('合成音频', on_click=copywriting_audio_synthesis, color=button_internal_color).style(button_internal_css)
                
        with ui.tab_panel(integral_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label("通用")
                with ui.grid(columns=3):
                    switch_integral_enable = ui.switch('启用', value=config.get("integral", "enable")).style(switch_internal_css)
            with ui.card().style(card_css):
                ui.label("签到")
                with ui.grid(columns=3):
                    switch_integral_sign_enable = ui.switch('启用', value=config.get("integral", "sign", "enable")).style(switch_internal_css)
                    input_integral_sign_get_integral = ui.input(label='获得积分数', value=config.get("integral", "sign", "get_integral"), placeholder='签到成功可以获得的积分数，请填写正整数！')
                    textarea_integral_sign_cmd = ui.textarea(label='命令', value=textarea_data_change(config.get("integral", "sign", "cmd")), placeholder='弹幕发送以下命令可以触发签到功能，换行分隔命令')
                with ui.card().style(card_css):
                    ui.label("文案")
                    integral_sign_copywriting_var = {}
                    for index, integral_sign_copywriting in enumerate(config.get("integral", "sign", "copywriting")):
                        with ui.grid(columns=2):
                            integral_sign_copywriting_var[str(2 * index)] = ui.input(label=f"签到数区间#{index}", value=integral_sign_copywriting["sign_num_interval"], placeholder='限制在此区间内的签到数来触发对应的文案，用-号来进行区间划分，包含边界值')
                            integral_sign_copywriting_var[str(2 * index + 1)] = ui.textarea(label=f"文案#{index}", value=textarea_data_change(integral_sign_copywriting["copywriting"]), placeholder='在此签到区间内，触发的文案内容，换行分隔').style("width:400px;")
            with ui.card().style(card_css):
                ui.label("礼物")
                with ui.grid(columns=3):
                    switch_integral_gift_enable = ui.switch('启用', value=config.get("integral", "gift", "enable")).style(switch_internal_css)
                    input_integral_gift_get_integral_proportion = ui.input(label='获得积分比例', value=config.get("integral", "gift", "get_integral_proportion"), placeholder='此比例和礼物真实金额（元）挂钩，默认就是1元=10积分')
                with ui.card().style(card_css):
                    ui.label("文案")
                    integral_gift_copywriting_var = {}
                    for index, integral_gift_copywriting in enumerate(config.get("integral", "gift", "copywriting")):
                        with ui.grid(columns=2):
                            integral_gift_copywriting_var[str(2 * index)] = ui.input(label=f"礼物价格区间#{index}", value=integral_gift_copywriting["gift_price_interval"], placeholder='限制在此区间内的礼物价格来触发对应的文案，用-号来进行区间划分，包含边界值')
                            integral_gift_copywriting_var[str(2 * index + 1)] = ui.textarea(label=f"文案#{index}", value=textarea_data_change(integral_gift_copywriting["copywriting"]), placeholder='在此礼物区间内，触发的文案内容，换行分隔').style("width:400px;")
            with ui.card().style(card_css):
                ui.label("入场")
                with ui.grid(columns=3):
                    switch_integral_entrance_enable = ui.switch('启用', value=config.get("integral", "entrance", "enable")).style(switch_internal_css)
                    input_integral_entrance_get_integral = ui.input(label='获得积分数', value=config.get("integral", "entrance", "get_integral"), placeholder='签到成功可以获得的积分数，请填写正整数！')
                with ui.card().style(card_css):
                    ui.label("文案")
                    integral_entrance_copywriting_var = {}
                    for index, integral_entrance_copywriting in enumerate(config.get("integral", "entrance", "copywriting")):
                        with ui.grid(columns=2):
                            integral_entrance_copywriting_var[str(2 * index)] = ui.input(label=f"入场数区间#{index}", value=integral_entrance_copywriting["entrance_num_interval"], placeholder='限制在此区间内的入场数来触发对应的文案，用-号来进行区间划分，包含边界值')
                            integral_entrance_copywriting_var[str(2 * index + 1)] = ui.textarea(label=f"文案#{index}", value=textarea_data_change(integral_entrance_copywriting["copywriting"]), placeholder='在此入场区间内，触发的文案内容，换行分隔').style("width:400px;")
            with ui.card().style(card_css):
                ui.label("增删改查")
                with ui.card().style(card_css):
                    ui.label("查询")
                    with ui.grid(columns=3):
                        switch_integral_crud_query_enable = ui.switch('启用', value=config.get("integral", "crud", "query", "enable")).style(switch_internal_css)
                        textarea_integral_crud_query_cmd = ui.textarea(label="命令", value=textarea_data_change(config.get("integral", "crud", "query", "cmd")), placeholder='弹幕发送以下命令可以触发查询功能，换行分隔命令')
                        textarea_integral_crud_query_copywriting = ui.textarea(label="文案", value=textarea_data_change(config.get("integral", "crud", "query", "copywriting")), placeholder='触发查询功能后返回的文案内容，换行分隔命令').style("width:400px;")

        with ui.tab_panel(talk_page).style(tab_panel_css):   
            with ui.row():
                switch_talk_key_listener_enable = ui.switch('启用按键监听', value=config.get("talk", "key_listener_enable")).style(switch_internal_css)
                audio_device_info_list = common.get_all_audio_device_info("in")
                # logging.info(f"audio_device_info_list={audio_device_info_list}")
                audio_device_info_dict = {str(device['device_index']): device['device_info'] for device in audio_device_info_list}

                logging.debug(f"声卡输入设备={audio_device_info_dict}")

                select_talk_device_index = ui.select(
                    label='声卡输入设备', 
                    options=audio_device_info_dict, 
                    value=config.get("talk", "device_index")
                ).style("width:300px;")
                
                input_talk_username = ui.input(label='你的名字', value=config.get("talk", "username"), placeholder='日志中你的名字，暂时没有实质作用').style("width:200px;")
                switch_talk_continuous_talk = ui.switch('连续对话', value=config.get("talk", "continuous_talk")).style(switch_internal_css)
            with ui.row():
                data_json = {}
                for line in ["google", "baidu", "faster_whisper"]:
                    data_json[line] = line
                select_talk_type = ui.select(
                    label='录音类型', 
                    options=data_json, 
                    value=config.get("talk", "type")
                ).style("width:200px;")

                with open('data/keyboard.txt', 'r') as file:
                    file_content = file.read()
                # 按行分割内容，并去除每行末尾的换行符
                lines = file_content.strip().split('\n')
                data_json = {}
                for line in lines:
                    data_json[line] = line
                select_talk_trigger_key = ui.select(
                    label='录音按键', 
                    options=data_json, 
                    value=config.get("talk", "trigger_key")
                ).style("width:100px;")
                select_talk_stop_trigger_key = ui.select(
                    label='停录按键', 
                    options=data_json, 
                    value=config.get("talk", "stop_trigger_key")
                ).style("width:100px;")

                input_talk_volume_threshold = ui.input(label='音量阈值', value=config.get("talk", "volume_threshold"), placeholder='音量阈值，指的是触发录音的起始音量值，请根据自己的麦克风进行微调到最佳')
                input_talk_silence_threshold = ui.input(label='沉默阈值', value=config.get("talk", "silence_threshold"), placeholder='沉默阈值，指的是触发停止路径的最低音量值，请根据自己的麦克风进行微调到最佳')
                input_talk_silence_CHANNELS = ui.input(label='CHANNELS', value=config.get("talk", "CHANNELS"), placeholder='录音用的参数')
                input_talk_silence_RATE = ui.input(label='RATE', value=config.get("talk", "RATE"), placeholder='录音用的参数')
            
            with ui.card().style(card_css):
                ui.label("谷歌")
                with ui.grid(columns=1):
                    data_json = {}
                    for line in ["zh-CN", "en-US", "ja-JP"]:
                        data_json[line] = line
                    select_talk_google_tgt_lang = ui.select(
                        label='目标翻译语言', 
                        options=data_json, 
                        value=config.get("talk", "google", "tgt_lang")
                    ).style("width:200px")
            with ui.card().style(card_css):
                ui.label("百度")
                with ui.grid(columns=3):    
                    input_talk_baidu_app_id = ui.input(label='AppID', value=config.get("talk", "baidu", "app_id"), placeholder='百度云 语音识别应用的 AppID')
                    input_talk_baidu_api_key = ui.input(label='API Key', value=config.get("talk", "baidu", "api_key"), placeholder='百度云 语音识别应用的 API Key')
                    input_talk_baidu_secret_key = ui.input(label='Secret Key', value=config.get("talk", "baidu", "secret_key"), placeholder='百度云 语音识别应用的 Secret Key')
            with ui.card().style(card_css):
                ui.label("faster_whisper")
                with ui.row():    
                    input_faster_whisper_model_size = ui.input(label='model_size', value=config.get("talk", "faster_whisper", "model_size"), placeholder='Size of the model to use')
                    data_json = {}
                    for line in ["cuda", "cpu", "auto"]:
                        data_json[line] = line
                    select_faster_whisper_device = ui.select(
                        label='device', 
                        options=data_json, 
                        value=config.get("talk", "faster_whisper", "device")
                    ).style("width:200px")
                    data_json = {}
                    for line in ["float16", "int8_float16", "int8"]:
                        data_json[line] = line
                    select_faster_whisper_compute_type = ui.select(
                        label='compute_type', 
                        options=data_json, 
                        value=config.get("talk", "faster_whisper", "compute_type")
                    ).style("width:200px")
                    input_faster_whisper_download_root = ui.input(label='download_root', value=config.get("talk", "faster_whisper", "download_root"), placeholder='模型下载路径')
                    input_faster_whisper_beam_size = ui.input(label='beam_size', value=config.get("talk", "faster_whisper", "beam_size"), placeholder='系统在每个步骤中要考虑的最可能的候选序列数。具有较大的beam_size将使系统产生更准确的结果，但可能需要更多的计算资源；较小的beam_size会减少计算需求，但可能降低结果的准确性。')

            with ui.row():
                textarea_talk_chat_box = ui.textarea(label='聊天框', value="", placeholder='此处填写对话内容可以直接进行对话（前面配置好聊天模式，记得运行先）').style("width:500px;")
                
                '''
                    聊天页相关的函数
                '''

                # 发送 聊天框内容
                def talk_chat_box_send():
                    global running_flag
                    
                    if running_flag != 1:
                        ui.notify(position="top", type="info", message="请先点击“一键运行”，然后再进行聊天")
                        return

                    # 获取用户名和文本内容
                    user_name = input_talk_username.value
                    content = textarea_talk_chat_box.value

                    # 清空聊天框
                    textarea_talk_chat_box.value = ""

                    data = {
                        "type": "comment",
                        "platform": "webui",
                        "username": user_name,
                        "content": content
                    }

                    logging.debug(f"data={data}")

                    common.send_request(f'http://{config.get("api_ip")}:{config.get("api_port")}/send', "POST", data)


                # 发送 聊天框内容 进行复读
                def talk_chat_box_reread(insert_index=-1):
                    global running_flag

                    if running_flag != 1:
                        ui.notify(position="top", type="warning", message="请先点击“一键运行”，然后再进行聊天")
                        return
                    
                    # 获取用户名和文本内容
                    user_name = input_talk_username.value
                    content = textarea_talk_chat_box.value

                    # 清空聊天框
                    textarea_talk_chat_box.value = ""

                    if insert_index == -1:
                        data = {
                            "type": "reread",
                            "username": user_name,
                            "content": content
                        }
                    else:
                        # 重载一下配置
                        tmp_config = Config(config_path)

                        # 判断下播放器类型
                        if tmp_config.get("play_audio", "player") != "audio_player_v2":
                            ui.notify(position="top", type="warning", message="插队功能仅在音频播放器为audio_player_v2的情况下可用")
                            return

                        data = {
                            "type": "reread",
                            "username": user_name,
                            "content": content,
                            "insert_index": insert_index
                        }

                    common.send_request(f'http://{config.get("api_ip")}:{config.get("api_port")}/send', "POST", data)

                # 发送 聊天框内容 进行LLM的调教
                def talk_chat_box_tuning():
                    global running_flag

                    if running_flag != 1:
                        ui.notify(position="top", type="warning", message="请先点击“一键运行”，然后再进行聊天")
                        return
                    
                    # 获取用户名和文本内容
                    user_name = input_talk_username.value
                    content = textarea_talk_chat_box.value

                    # 清空聊天框
                    textarea_talk_chat_box.value = ""

                    data = {
                        "type": "tuning",
                        "user_name": user_name,
                        "content": content
                    }

                    common.send_request(f'http://{config.get("api_ip")}:{config.get("api_port")}/send', "POST", data)

                button_talk_chat_box_send = ui.button('发送', on_click=lambda: talk_chat_box_send(), color=button_internal_color).style(button_internal_css)
                button_talk_chat_box_reread = ui.button('直接复读', on_click=lambda: talk_chat_box_reread(), color=button_internal_color).style(button_internal_css)
                button_talk_chat_box_tuning = ui.button('调教', on_click=lambda: talk_chat_box_tuning(), color=button_internal_color).style(button_internal_css)
                button_talk_chat_box_reread_first = ui.button('直接复读-插队首', on_click=lambda: talk_chat_box_reread(0), color=button_internal_color).style(button_internal_css)
        
        with ui.tab_panel(assistant_anchor_page).style(tab_panel_css):
            with ui.row():
                switch_assistant_anchor_enable = ui.switch('启用', value=config.get("assistant_anchor", "enable")).style(switch_internal_css)
                input_assistant_anchor_username = ui.input(label='助播名', value=config.get("assistant_anchor", "username"), placeholder='助播的用户名，暂时没啥用')
            with ui.card().style(card_css):
                ui.label("触发类型")
                with ui.row():
                    # 类型列表源自audio_synthesis_handle 音频合成的所支持的type值
                    assistant_anchor_type_list = ["comment", "local_qa_audio", "song", "reread", "direct_reply", "read_comment", "gift", 
                                                  "entrance", "follow", "idle_time_task"]
                    assistant_anchor_type_var = {}
                    
                    for index, assistant_anchor_type in enumerate(assistant_anchor_type_list):
                        if assistant_anchor_type in config.get("assistant_anchor", "type"):
                            assistant_anchor_type_var[str(index)] = ui.checkbox(text=assistant_anchor_type, value=True)
                        else:
                            assistant_anchor_type_var[str(index)] = ui.checkbox(text=assistant_anchor_type, value=False)
            with ui.grid(columns=4):
                switch_assistant_anchor_local_qa_text_enable = ui.switch('启用文本匹配', value=config.get("assistant_anchor", "local_qa", "text", "enable")).style(switch_internal_css)
                select_assistant_anchor_local_qa_text_format = ui.select(
                    label='存储格式',
                    options={'json': '自定义json', 'text': '一问一答'},
                    value=config.get("assistant_anchor", "local_qa", "text", "format")
                )
                input_assistant_anchor_local_qa_text_file_path = ui.input(label='文本问答数据路径', value=config.get("assistant_anchor", "local_qa", "text", "file_path"), placeholder='本地问答文本数据存储路径').style("width:200px;")
                input_assistant_anchor_local_qa_text_similarity = ui.input(label='文本最低相似度', value=config.get("assistant_anchor", "local_qa", "text", "similarity"), placeholder='最低文本匹配相似度，就是说用户发送的内容和本地问答库中设定的内容的最低相似度。\n低了就会被当做一般弹幕处理').style("width:200px;")
            with ui.grid(columns=4):
                switch_assistant_anchor_local_qa_audio_enable = ui.switch('启用音频匹配', value=config.get("assistant_anchor", "local_qa", "audio", "enable")).style(switch_internal_css)
                select_assistant_anchor_local_qa_audio_type = ui.select(
                    label='匹配算法',
                    options={'包含关系': '包含关系', '相似度匹配': '相似度匹配'},
                    value=config.get("assistant_anchor", "local_qa", "audio", "type")
                )
                input_assistant_anchor_local_qa_audio_file_path = ui.input(label='音频存储路径', value=config.get("assistant_anchor", "local_qa", "audio", "file_path"), placeholder='本地问答音频文件存储路径').style("width:200px;")
                input_assistant_anchor_local_qa_audio_similarity = ui.input(label='音频最低相似度', value=config.get("assistant_anchor", "local_qa", "audio", "similarity"), placeholder='最低音频匹配相似度，就是说用户发送的内容和本地音频库中音频文件名的最低相似度。\n低了就会被当做一般弹幕处理').style("width:200px;")
        
        with ui.tab_panel(translate_page).style(tab_panel_css):
            with ui.row():
                switch_translate_enable = ui.switch('启用', value=config.get("translate", "enable")).style(switch_internal_css)
                select_translate_type = ui.select(
                        label='类型', 
                        options={'baidu': '百度翻译', 'google': '谷歌翻译'}, 
                        value=config.get("translate", "type")
                    ).style("width:100px;")
                select_translate_trans_type = ui.select(
                        label='翻译类型', 
                        options={'弹幕': '弹幕', '回复': '回复', '弹幕+回复': '弹幕+回复'}, 
                        value=config.get("translate", "trans_type")
                    ).style("width:150px;")
            with ui.card().style(card_css):
                ui.label("百度翻译")
                with ui.row():
                    input_translate_baidu_appid = ui.input(label='APP ID', value=config.get("translate", "baidu", "appid"), placeholder='翻译开放平台 开发者中心 APP ID')
                    input_translate_baidu_appkey = ui.input(label='密钥', value=config.get("translate", "baidu", "appkey"), placeholder='翻译开放平台 开发者中心 密钥')
                    select_translate_baidu_from_lang = ui.select(
                        label='源语言', 
                        options={'auto': '自动检测', 'zh': '中文', 'cht': '繁体中文', 'en': '英文', 'jp': '日文', 'kor': '韩文', 'yue': '粤语', 'wyw': '文言文'}, 
                        value=config.get("translate", "baidu", "from_lang")
                    ).style("width:100px;")
                    select_translate_baidu_to_lang = ui.select(
                        label='目标语言', 
                        options={'zh': '中文', 'cht': '繁体中文', 'en': '英文', 'jp': '日文', 'kor': '韩文', 'yue': '粤语', 'wyw': '文言文'}, 
                        value=config.get("translate", "baidu", "to_lang")
                    ).style("width:100px;")
            with ui.card().style(card_css):
                ui.label("谷歌翻译")
                with ui.row():
                    input_translate_google_proxy = ui.input(label='代理地址', value=config.get("translate", "google", "proxy"), placeholder='代理的完整地址，请携带协议')
                    select_translate_google_src_lang = ui.select(
                        label='源语言', 
                        options={'auto': '自动', 'zh-CN': '中文', 'en': '英文', 'ja': '日文'}, 
                        value=config.get("translate", "google", "src_lang")
                    ).style("width:100px;")
                    select_translate_google_tgt_lang = ui.select(
                        label='目标语言', 
                        options={'zh-CN': '中文', 'en': '英文', 'ja': '日文'}, 
                        value=config.get("translate", "google", "tgt_lang")
                    ).style("width:100px;")
                    
        with ui.tab_panel(web_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label("webui配置")
                with ui.row():
                    input_webui_title = ui.input(label='标题', placeholder='webui的标题', value=config.get("webui", "title")).style("width:250px;")
                    input_webui_ip = ui.input(label='IP地址', placeholder='webui监听的IP地址', value=config.get("webui", "ip")).style("width:150px;")
                    input_webui_port = ui.input(label='端口', placeholder='webui监听的端口', value=config.get("webui", "port")).style("width:100px;")
                    switch_webui_auto_run = ui.switch('自动运行', value=config.get("webui", "auto_run")).style(switch_internal_css)

            with ui.card().style(card_css):
                ui.label("板块显影")
                with ui.row():
                    switch_webui_show_card_read_comment = ui.switch('念弹幕', value=config.get("webui", "show_card", "read_comment")).style(switch_internal_css)
                    switch_webui_show_card_read_user_name = ui.switch('回复时念用户名', value=config.get("webui", "show_card", "read_user_name")).style(switch_internal_css)
                    switch_webui_show_card_filter = ui.switch('过滤', value=config.get("webui", "show_card", "filter")).style(switch_internal_css)
                    switch_webui_show_card_thanks = ui.switch('答谢', value=config.get("webui", "show_card", "thanks")).style(switch_internal_css)
                    switch_webui_show_card_live2d = ui.switch('live2d', value=config.get("webui", "show_card", "live2d")).style(switch_internal_css)
                    switch_webui_show_card_audio_random_speed = ui.switch('音频随机变速', value=config.get("webui", "show_card", "audio_random_speed")).style(switch_internal_css)
                    switch_webui_show_card_so_vits_svc = ui.switch('SO-VITS-SVC', value=config.get("webui", "show_card", "so_vits_svc")).style(switch_internal_css)
                    switch_webui_show_card_ddsp_svc = ui.switch('DDSP-SVC', value=config.get("webui", "show_card", "ddsp_svc")).style(switch_internal_css)
                    switch_webui_show_card_local_qa = ui.switch('本地问答', value=config.get("webui", "show_card", "local_qa")).style(switch_internal_css)
                    switch_webui_show_card_choose_song = ui.switch('点歌', value=config.get("webui", "show_card", "choose_song")).style(switch_internal_css)
                    switch_webui_show_card_sd = ui.switch('Stable Diffusion', value=config.get("webui", "show_card", "sd")).style(switch_internal_css)
                    switch_webui_show_card_log = ui.switch('日志', value=config.get("webui", "show_card", "log")).style(switch_internal_css)
                    switch_webui_show_card_schedule = ui.switch('定时任务', value=config.get("webui", "show_card", "schedule")).style(switch_internal_css)
                    switch_webui_show_card_idle_time_task = ui.switch('闲时任务', value=config.get("webui", "show_card", "idle_time_task")).style(switch_internal_css)
                    switch_webui_show_card_database = ui.switch('数据库', value=config.get("webui", "show_card", "database")).style(switch_internal_css)
                    switch_webui_show_card_play_audio = ui.switch('音频播放', value=config.get("webui", "show_card", "play_audio")).style(switch_internal_css)
                    switch_webui_show_card_web_captions_printer = ui.switch('web字幕打印机', value=config.get("webui", "show_card", "web_captions_printer")).style(switch_internal_css)
                    switch_webui_show_card_key_mapping = ui.switch('按键映射', value=config.get("webui", "show_card", "key_mapping")).style(switch_internal_css)
                    switch_webui_show_card_unity = ui.switch('Unity', value=config.get("webui", "show_card", "unity")).style(switch_internal_css)
                    
            with ui.card().style(card_css):
                ui.label("CSS")
                with ui.row():
                    theme_list = config.get("webui", "theme", "list").keys()
                    data_json = {}
                    for line in theme_list:
                        data_json[line] = line
                    select_webui_theme_choose = ui.select(
                        label='主题', 
                        options=data_json, 
                        value=config.get("webui", "theme", "choose")
                    )
            with ui.card().style(card_css):
                ui.label("账号管理")
                with ui.row():
                    switch_login_enable = ui.switch('登录功能', value=config.get("login", "enable")).style(switch_internal_css)
                    input_login_username = ui.input(label='用户名', placeholder='您的账号喵，配置在config.json中', value=config.get("login", "username")).style("width:250px;")
                    input_login_password = ui.input(label='密码', password=True, placeholder='您的密码喵，配置在config.json中', value=config.get("login", "password")).style("width:250px;")
        with ui.tab_panel(docs_page).style(tab_panel_css):
            with ui.row():
                ui.label('在线文档：')
                ui.link('https://luna.docs.ie.cx/', 'https://luna.docs.ie.cx/', new_tab=True)
            with ui.row():
                ui.label('NiceGUI官方文档：')
                ui.link('https://nicegui.io/documentation', 'https://nicegui.io/documentation', new_tab=True)
            
            ui.html('<iframe src="https://luna.docs.ie.cx/" width="1800" height="800"></iframe>').style("width:100%")
        with ui.tab_panel(about_page).style(tab_panel_css):
            with ui.card().style(card_css):
                ui.label('介绍').style("font-size:24px;")
                ui.label('AI Vtuber 是一款结合了最先进技术的虚拟AI主播。它的核心是一系列高效的人工智能模型，包括 ChatterBot、GPT、Claude、langchain、chatglm、text-generation-webui、讯飞星火、智谱AI、谷歌Bard、文心一言 和 通义星尘。这些模型既可以在本地运行，也可以通过云端服务提供支持。')
                ui.label('AI Vtuber 的外观由 Live2D、Vtube Studio、xuniren 和 UE5 结合 Audio2Face 技术打造，为用户提供了一个生动、互动的虚拟形象。这使得 AI Vtuber 能够在各大直播平台，如 Bilibili、抖音、快手、斗鱼、YouTube 和 Twitch，进行实时互动直播。当然，它也可以在本地环境中与您进行个性化对话。')
                ui.label('为了使交流更加自然，AI Vtuber 使用了先进的自然语言处理技术，结合文本转语音系统，如 Edge-TTS、VITS-Fast、elevenlabs、bark-gui、VALL-E-X、睿声AI、genshinvoice.top 和 tts.ai-lab.top。这不仅让它能够生成流畅的回答，还可以通过 so-vits-svc 和 DDSP-SVC 实现声音的变化，以适应不同的场景和角色。')
                ui.label('此外，AI Vtuber 还能够通过特定指令与 Stable Diffusion 协作，展示画作。用户还可以自定义文案，让 AI Vtuber 循环播放，以满足不同场合的需求。')
            with ui.card().style(card_css):
                ui.label('许可证').style("font-size:24px;")
                ui.label('这个项目采用 GNU通用公共许可证（GPL） 进行许可。有关详细信息，请参阅 LICENSE 文件。')
            with ui.card().style(card_css):
                ui.label('注意').style("font-size:24px;")
                ui.label('严禁将此项目用于一切违反《中华人民共和国宪法》，《中华人民共和国刑法》，《中华人民共和国治安管理处罚法》和《中华人民共和国民法典》之用途。')
                ui.label('严禁用于任何政治相关用途。')
    with ui.grid(columns=6).style("position: fixed; bottom: 10px; text-align: center;"):
        button_save = ui.button('保存配置', on_click=lambda: save_config(), color=button_bottom_color).style(button_bottom_css)
        button_run = ui.button('一键运行', on_click=lambda: run_external_program(), color=button_bottom_color).style(button_bottom_css)
        # 创建一个按钮，用于停止正在运行的程序
        button_stop = ui.button("停止运行", on_click=lambda: stop_external_program(), color=button_bottom_color).style(button_bottom_css)
        button_light = ui.button('关灯', on_click=lambda: change_light_status(), color=button_bottom_color).style(button_bottom_css)
        # button_stop.enabled = False  # 初始状态下停止按钮禁用
        restart_light = ui.button('重启', on_click=lambda: restart_application(), color=button_bottom_color).style(button_bottom_css)
        # factory_btn = ui.button('恢复出厂配置', on_click=lambda: factory(), color=button_bottom_color).style(tab_panel_css)

    # 是否启用自动运行功能
    if config.get("webui", "auto_run"):
        logging.info("自动运行 已启用")
        run_external_program(type="api")

# 是否启用登录功能（暂不合理）
if config.get("login", "enable"):
    logging.info(config.get("login", "enable"))

    def my_login():
        username = input_login_username.value
        password = input_login_password.value

        if username == "" or password == "":
            ui.notify(position="top", type="info", message=f"用户名或密码不能为空")
            return

        if username != config.get("login", "username") or password != config.get("login", "password"):
            ui.notify(position="top", type="info", message=f"用户名或密码不正确")
            return

        ui.notify(position="top", type="info", message=f"登录成功")

        label_login.delete()
        input_login_username.delete()
        input_login_password.delete()
        button_login.delete()
        button_login_forget_password.delete()

        login_column.style("")
        login_card.style("position: unset;")

        goto_func_page()

        return

    # @ui.page('/forget_password')
    def forget_password():
        ui.notify(position="top", type="info", message=f"好忘喵~ 好忘~o( =∩ω∩= )m")


    login_column = ui.column().style("width:100%;text-align: center;")
    with login_column:
        login_card = ui.card().style(config.get("webui", "theme", "list", theme_choose, "login_card"))
        with login_card:
            label_login = ui.label('AI    Vtuber').style("font-size: 30px;letter-spacing: 5px;color: #3b3838;")
            input_login_username = ui.input(label='用户名', placeholder='您的账号喵，配置在config.json中', value="").style("width:250px;")
            input_login_password = ui.input(label='密码', password=True, placeholder='您的密码喵，配置在config.json中', value="").style("width:250px;")
            button_login = ui.button('登录', on_click=lambda: my_login()).style("width:250px;")
            button_login_forget_password = ui.button('忘记账号/密码怎么办？', on_click=lambda: forget_password()).style("width:250px;")
            # link_login_forget_password = ui.link('忘记账号密码怎么办？', forget_password)

else:
    login_column = ui.column().style("width:100%;text-align: center;")
    with login_column:
        login_card = ui.card().style(config.get("webui", "theme", "list", theme_choose, "login_card"))
        
        # 跳转到功能页
        goto_func_page()


ui.run(host=webui_ip, port=webui_port, title=webui_title, favicon="./ui/favicon-64.ico", language="zh-CN", dark=False, reload=False)
