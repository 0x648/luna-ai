import sys, os, json, subprocess, importlib, re, threading, signal
import logging, traceback
import time
import asyncio
# from functools import partial

from utils.config import Config

from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QLabel, QComboBox, QLineEdit, QTextEdit, QCheckBox, QGroupBox
from PyQt5.QtGui import QFont, QDesktopServices, QIcon, QPixmap
from PyQt5.QtCore import QTimer, QThread, QEventLoop, pyqtSignal, QUrl, Qt, QEvent

import http.server
import socketserver

import UI_main

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


class AI_VTB(QMainWindow):
    proxy = None
    # proxy = {
    #     "http": "http://127.0.0.1:10809",
    #     "https": "http://127.0.0.1:10809"
    # }

    # 平台端线程
    platform_thread = None
    # 平台端进程
    platform_process = None

    terminate_event = threading.Event()
    _instance = None

    # 单例模式
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AI_VTB, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    

    '''
        初始化
    '''
    def __init__(self):
        logging.info("程序开始运行")
        
        self.app = QApplication(sys.argv)
        super().__init__()
        self.ui = UI_main.Ui_MainWindow()
        self.ui.setupUi(self)

        # 获取显示器分辨率
        self.desktop = QApplication.desktop()
        self.screenRect = self.desktop.screenGeometry()
        self.screenheight = self.screenRect.height()
        self.screenwidth = self.screenRect.width()

        logging.debug("Screen height {}".format(self.screenheight))
        logging.debug("Screen width {}".format(self.screenwidth))

        # self.height = int(self.screenheight * 0.7)
        # self.width = int(self.screenwidth * 0.7)

        # 设置软件图标
        app_icon = QIcon("ui/icon.png")
        self.setWindowIcon(app_icon)

        # self.resize(self.width, self.height)

        # 页面索引
        self.stackedWidget_index = 0

        # 调用设置背景图的方法
        self.set_background()

        # 设置实例
        self.CreateItems()
        # 读取配置文件 进行初始化
        self.init_config()
        # 初始化
        self.init_ui()


    # 设置背景图
    def set_background(self):
        # 创建一个 QLabel 用于显示背景图
        background_label = QLabel(self)
        
        # 加载背景图，替换 'background.jpg' 为你的图片路径
        pixmap = QPixmap('ui/bg.png')

        screen = QApplication.primaryScreen()
        screen_size = screen.size()

        # 计算缩放比例，使图片等比缩放至全屏
        scaled_pixmap = pixmap.scaled(screen_size, aspectRatioMode=Qt.KeepAspectRatio)
        
        # 设置 Label 大小为窗口大小
        background_label.setPixmap(scaled_pixmap)

        # 高度减一点，顶部菜单栏覆盖不到，什么dio问题
        background_label.setGeometry(0, 0, screen_size.width(), screen_size.height() - 15)

        # 让 Label 放置在顶层，成为背景
        background_label.lower()


    # 关闭窗口
    def closeEvent(self, event):
        global web_server_thread

        AI_VTB.terminate_event.set()

        if AI_VTB.platform_process:
            # 终止进程
            AI_VTB.platform_process.terminate()

        if AI_VTB.platform_thread:
            # 停止线程
            AI_VTB.platform_thread.terminate()

        if config.get("live2d", "enable"):
            web_server_thread.terminate()
        
        # 关闭窗口
        event.accept() 


    # 设置实例 
    def CreateItems(self):
        # 定时器
        self.timer = QTimer(self)
        self.eventLoop = QEventLoop(self)

        # self.timer_connection = None
    

    # 过滤 QComboBox 的选项并更新
    def filter_combobox(self, combo_box, text, manual_clear=True):
        if manual_clear:
            combo_box.lineEdit().textChanged.disconnect()  # 断开信号连接
            combo_box.clear()
        
        # print(text)

        if text:
            matching_items = [item for item in combo_box.original_items if text.lower() in item.lower()]
            combo_box.addItems(matching_items)
        elif text == '':
            combo_box.addItems(combo_box.original_items)

        # combo_box.setCurrentIndex(-1)  # 将当前索引设置为 -1，以取消选择

        combo_box.lineEdit().textChanged.connect(lambda text, combo=combo_box: self.filter_combobox(combo, text, manual_clear=True))
        
        
    # 从json数据中动态创建widgets
    def create_widgets_from_json(self, data):
        widgets = []

        for item in data:
            # logging.info(item)

            if item["label_text"] != "":
                label_text = item["label_text"]
                label = QLabel(label_text)
                label.setToolTip(item["label_tip"])
                widgets.append(label)

            data_type = type(item["data"])

            # 是否限定了widget的类型
            if "widget_type" in item:
                if item["widget_type"] == "combo_box":
                    widget = QComboBox()
                    # 允许编辑
                    widget.setEditable(True)  
                    # 添加多个item
                    widget.addItems(item["combo_data_list"])
                    # data必须在list中，不然，报错咯
                    widget.setCurrentIndex(item["combo_data_list"].index(item["data"]))

                    widget.original_items = item["combo_data_list"]

                    # 设置下拉列表的对象名称
                    widget.setObjectName(item["main_obj_name"] + "_QComboBox_" + str(item["index"]))

                    widget.lineEdit().textChanged.connect(lambda text, combo=widget: self.filter_combobox(combo, text, True))
            else:        
                # 根据数据类型，自动生成对应类实例
                if data_type == str or data_type == int or data_type == float:
                    widget = QLineEdit()
                    widget.setText(str(item["data"]))
                    widget.setObjectName(item["main_obj_name"] + "_QLineEdit_" + str(item["index"]))
                elif data_type == bool:
                    widget = QCheckBox()
                    if item["widget_text"] == "":
                        widget.setText("启用")
                    else:
                        widget.setText(item["widget_text"])
                    widget.setChecked(item["data"])
                    widget.setObjectName(item["main_obj_name"] + "_QCheckBox_" + str(item["index"]))

                    if item["click_func"] == "show_box":
                        widget.disconnect()
                        # 连接点击信号到槽函数
                        widget.clicked.connect(lambda state, text=item["main_obj_name"]: self.show_box_clicked(state, text))
                        # 直接运行恢复显隐状态
                        self.show_box_clicked(item["data"], item["main_obj_name"])

                elif data_type == list:
                    widget = QTextEdit()

                    tmp_str = ""
                    for tmp in item["data"]:
                        tmp_str = tmp_str + tmp + "\n"
                    widget.setText(tmp_str)
                    widget.setObjectName(item["main_obj_name"] + "_QTextEdit_" + str(item["index"]))

            # 判断readonly是否存在
            if item.get("readonly") is not None:
                widget.setReadOnly(item["readonly"])

            widgets.append(widget)

        return widgets


    # 从gridLayout中读取所有的widget，返回widget列表
    def read_widgets_from_gridLayout(self, gridLayout):
        widgets = []
        for row in range(gridLayout.rowCount()):
            for col in range(gridLayout.columnCount()):
                widget_item = gridLayout.itemAtPosition(row, col)
                if widget_item is not None:
                    widget = widget_item.widget()
                    if widget is not None:
                        widgets.append(widget)
        return widgets


    # 从gridLayout的widgets中获取数据到data
    def update_data_from_gridLayout(self, gridLayout, type=""):
        widgets = self.read_widgets_from_gridLayout(gridLayout)
        logging.debug(widgets)

        data = {}

        for index, widget in enumerate(widgets):
            if isinstance(widget, QLineEdit):
                # data["QLineEdit_" + str(index)] = widget.text()
                data[str(index)] = widget.text()
            elif isinstance(widget, QCheckBox):
                if type == "show_box":
                    data[widget.objectName()] = widget.isChecked()
                else:
                    # data["QCheckBox_" + str(index)] = widget.isChecked()
                    data[str(index)] = widget.isChecked()
            elif isinstance(widget, QTextEdit):
                data_list = widget.toPlainText().splitlines()
                # data["QTextEdit_" + str(index)] = data_list
                data[str(index)] = data_list
            elif isinstance(widget, QComboBox):
                # data["QComboBox_" + str(index)] = widget.text()
                data[str(index)] = widget.currentText()
                
        logging.debug(data)

        return data


    # 读取配置文件 进行初始化(开始堆shi喵)
    def init_config(self):
        global config, config_path

        # 如果配置文件不存在，创建一个新的配置文件
        if not os.path.exists(config_path):
            logging.error("配置文件不存在！！！请恢复")
            self.show_message_box("错误", f"配置文件不存在！！！请恢复", QMessageBox.Critical)
            os._exit(0)
            

        config = Config(config_path)


        try:
            # 运行标志位，避免重复运行
            self.running_flag = 0

            # 设置会话初始值
            self.session_config = {'msg': [{"role": "system", "content": config.get('chatgpt', 'preset')}]}
            self.sessions = {}
            self.current_key_index = 0

            self.platform = config.get("platform")
            
            # 直播间号
            self.room_id = config.get("room_display_id")

            self.before_prompt = config.get("before_prompt")
            self.after_prompt = config.get("after_prompt")

            self.comment_log_type = config.get("comment_log_type")

            # 日志
            self.captions_config = config.get("captions")

            # 本地问答
            self.local_qa_config = config.get("local_qa")

            # 过滤配置
            self.filter_config = config.get("filter")

            # 答谢
            self.thanks_config = config.get("thanks")

            self.chat_type = config.get("chat_type")

            self.need_lang = config.get("need_lang")

            self.live2d_config = config.get("live2d")

            # openai
            self.openai_config = config.get("openai")
            # chatgpt
            self.chatgpt_config = config.get("chatgpt")
            # claude
            self.claude_config = config.get("claude")
            # claude2
            self.claude2_config = config.get("claude2")
            # chatterbot
            self.chatterbot_config = config.get("chatterbot")
            # chat_with_file
            self.chat_with_file_config = config.get("chat_with_file")
            # chatglm
            self.chatglm_config = config.get("chatglm")
            # text_generation_webui
            self.text_generation_webui_config = config.get("text_generation_webui")
            # sparkdesk
            self.sparkdesk_config = config.get("sparkdesk")
            # 智谱AI
            self.zhipu_config = config.get("zhipu")

            # 音频合成使用技术
            self.audio_synthesis_type = config.get("audio_synthesis_type")

            self.edge_tts_config = config.get("edge-tts")
            self.vits_fast_config = config.get("vits_fast")
            self.elevenlabs_config = config.get("elevenlabs")
            self.genshinvoice_top_config = config.get("genshinvoice_top")
            self.bark_gui_config = config.get("bark_gui")
            
            # 点歌模式
            self.choose_song_config = config.get("choose_song")

            self.so_vits_svc_config = config.get("so_vits_svc")

            # SD
            self.sd_config = config.get("sd")

            # 文案
            self.copywriting_config = config.get("copywriting")

            self.header_config = config.get("header")

            # 聊天
            self.talk_config = config.get("talk")

            """
                配置Label提示
            """
            # 设置鼠标悬停时的提示文本
            self.ui.label_platform.setToolTip("运行的平台版本")  
            self.ui.label_room_display_id.setToolTip("待监听的直播间的房间号（直播间URL最后一个/后的数字和字母），需要是开播状态")
            self.ui.label_chat_type.setToolTip("弹幕对接的聊天类型")
            self.ui.label_visual_body.setToolTip("对接的虚拟身体应用，暂时只用于对接xuniren应用，预留给未来其他应用使用")
            self.ui.label_need_lang.setToolTip("只回复选中语言的弹幕，其他语言将被过滤")
            self.ui.label_before_prompt.setToolTip("提示词前缀，会自带追加在弹幕前，主要用于追加一些特殊的限制")
            self.ui.label_after_prompt.setToolTip("提示词后缀，会自带追加在弹幕后，主要用于追加一些特殊的限制")
            self.ui.label_comment_log_type.setToolTip("弹幕日志类型，用于记录弹幕触发时记录的内容，默认只记录回答，降低当用户使用弹幕日志显示在直播间时，因为用户的不良弹幕造成直播间被封禁问题")
            
            # 念用户名
            self.ui.label_read_user_name_enable.setToolTip("是否启用回复用户弹幕时，念用户的昵称，例：回复xxx。你好")
            self.ui.label_read_user_name_voice_change.setToolTip("是否启用变声功能，就是说不仅仅进行TTS，还进行变声，这是为了针对特定场景，区分念用户名和正经回复")
            self.ui.label_read_user_name_reply_before.setToolTip("在正经回复前的念用户名的文案，目前是本地问答库-文本 触发时使用")
            self.ui.label_read_user_name_reply_after.setToolTip("在正经回复后的念用户名的文案，目前是本地问答库-音频 触发时使用")

            self.ui.label_captions_enable.setToolTip("是否启用字幕日志记录，字幕输出内容为当前合成播放的音频的文本")
            self.ui.label_captions_file_path.setToolTip("字幕日志存储路径")

            # 本地问答
            self.ui.label_local_qa_text_enable.setToolTip("是否启用本地问答文本匹配，完全命中设定的问题后，自动合成对应的回答")
            self.ui.label_local_qa_text_type.setToolTip("本地问答文本匹配算法类型，默认就是json的自定义数据，更高级。\n一问一答就是旧版本的一行问题一行答案这种，适合新手")
            self.ui.label_local_qa_text_file_path.setToolTip("本地问答文本数据存储路径")
            self.ui.label_local_qa_text_similarity.setToolTip("最低文本匹配相似度，就是说用户发送的内容和本地问答库中设定的内容的最低相似度。\n低了就会被当做一般弹幕处理")
            self.ui.label_local_qa_audio_enable.setToolTip("是否启用本地问答音频匹配，部分命中音频文件名后，直接播放对应的音频文件")
            self.ui.label_local_qa_audio_file_path.setToolTip("本地问答音频文件存储路径")
            self.ui.label_local_qa_audio_similarity.setToolTip("最低音频匹配相似度，就是说用户发送的内容和本地音频库中音频文件名的最低相似度。\n低了就会被当做一般弹幕处理")

            # 过滤
            self.ui.label_filter_before_must_str.setToolTip("弹幕过滤，必须携带的触发前缀字符串（任一）\n例如：配置#，那么就需要发送：#你好")
            self.ui.label_filter_after_must_str.setToolTip("弹幕过滤，必须携带的触发后缀字符串（任一）\n例如：配置。那么就需要发送：你好。")
            self.ui.label_filter_badwords_path.setToolTip("本地违禁词数据路径（你如果不需要，可以清空文件内容）")
            self.ui.label_filter_bad_pinyin_path.setToolTip("本地违禁拼音数据路径（你如果不需要，可以清空文件内容）")
            self.ui.label_filter_max_len.setToolTip("最长阅读的英文单词数（空格分隔）")
            self.ui.label_filter_max_char_len.setToolTip("最长阅读的字符数，双重过滤，避免溢出")
            self.ui.label_filter_comment_forget_duration.setToolTip("指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义")
            self.ui.label_filter_comment_forget_reserve_num.setToolTip("保留最新收到的数据的数量")
            self.ui.label_filter_gift_forget_duration.setToolTip("指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义")
            self.ui.label_filter_gift_forget_reserve_num.setToolTip("保留最新收到的数据的数量")
            self.ui.label_filter_entrance_forget_duration.setToolTip("指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义")
            self.ui.label_filter_entrance_forget_reserve_num.setToolTip("保留最新收到的数据的数量")
            self.ui.label_filter_follow_forget_duration.setToolTip("指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义")
            self.ui.label_filter_follow_forget_reserve_num.setToolTip("保留最新收到的数据的数量")
            self.ui.label_filter_talk_forget_duration.setToolTip("指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义")
            self.ui.label_filter_talk_forget_reserve_num.setToolTip("保留最新收到的数据的数量")
            self.ui.label_filter_schedule_forget_duration.setToolTip("指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义")
            self.ui.label_filter_schedule_forget_reserve_num.setToolTip("保留最新收到的数据的数量")

            # 答谢
            self.ui.label_thanks_entrance_enable.setToolTip("是否启用欢迎用户进入直播间功能")
            self.ui.label_thanks_entrance_copy.setToolTip("用户进入直播间的相关文案，请勿动 {username}，此字符串用于替换用户名")
            self.ui.label_thanks_gift_enable.setToolTip("是否启用感谢用户赠送礼物功能")
            self.ui.label_thanks_gift_copy.setToolTip("用户赠送礼物的相关文案，请勿动 {username} 和 {gift_name}，此字符串用于替换用户名和礼物名")
            self.ui.label_thanks_lowest_price.setToolTip("设置最低答谢礼物的价格（元），低于这个设置的礼物不会触发答谢")
            self.ui.label_thanks_follow_enable.setToolTip("是否启用感谢用户关注的功能")
            self.ui.label_thanks_follow_copy.setToolTip("用户关注时的相关文案，请勿动 {username}，此字符串用于替换用户名")

            self.ui.label_live2d_enable.setToolTip("启动web服务，用于加载本地Live2D模型")
            self.ui.label_live2d_port.setToolTip("web服务运行的端口号，默认：12345，范围:0-65535，没事不要乱改就好")
            self.ui.label_live2d_name.setToolTip("模型名称，模型存放于Live2D\live2d-model路径下，请注意路径和模型内容是否匹配")

            # 音频随机变速
            self.ui.label_audio_random_speed_normal_enable.setToolTip("是否启用普通音频的随机变速功能")
            self.ui.label_audio_random_speed_normal_speed_min.setToolTip("普通音频的随机变速倍率的下限，就是正常语速乘以上下限直接随机出的数的倍率，\n就是变速后的语速，默认语速倍率为1")
            self.ui.label_audio_random_speed_normal_speed_max.setToolTip("普通音频的随机变速倍率的上限，就是正常语速乘以上下限直接随机出的数的倍率，\n就是变速后的语速，默认语速倍率为1")
            self.ui.label_audio_random_speed_normal_enable.setToolTip("是否启用文案音频的随机变速功能")
            self.ui.label_audio_random_speed_normal_speed_min.setToolTip("文案音频的随机变速倍率的下限，就是正常语速乘以上下限直接随机出的数的倍率，\n就是变速后的语速，默认语速倍率为1")
            self.ui.label_audio_random_speed_normal_speed_max.setToolTip("文案音频的随机变速倍率的上限，就是正常语速乘以上下限直接随机出的数的倍率，\n就是变速后的语速，默认语速倍率为1")

            self.ui.label_audio_synthesis_type.setToolTip("语音合成的类型")

            self.ui.label_openai_api.setToolTip("API请求地址，支持代理")
            self.ui.label_openai_api_key.setToolTip("API KEY，支持代理")
            self.ui.label_chatgpt_model.setToolTip("指定要使用的模型，可以去官方API文档查看模型列表")
            self.ui.label_chatgpt_temperature.setToolTip("控制生成文本的随机性。较高的温度值会使生成的文本更随机和多样化，而较低的温度值会使生成的文本更加确定和一致。")
            self.ui.label_chatgpt_max_tokens.setToolTip("限制生成回答的最大长度。")
            self.ui.label_chatgpt_top_p.setToolTip("也被称为 Nucleus采样。这个参数控制模型从累积概率大于一定阈值的令牌中进行采样。较高的值会产生更多的多样性，较低的值会产生更少但更确定的回答。")
            self.ui.label_chatgpt_presence_penalty.setToolTip("控制模型生成回答时对给定问题提示的关注程度。较高的存在惩罚值会减少模型对给定提示的重复程度，鼓励模型更自主地生成回答。")
            self.ui.label_chatgpt_frequency_penalty.setToolTip("控制生成回答时对已经出现过的令牌的惩罚程度。较高的频率惩罚值会减少模型生成已经频繁出现的令牌，以避免重复和过度使用特定词语。")
            self.ui.label_chatgpt_preset.setToolTip("用于指定一组预定义的设置，以便模型更好地适应特定的对话场景。")

            self.ui.label_claude_slack_user_token.setToolTip("Slack平台配置的用户Token，参考文档的Claude板块进行配置")
            self.ui.label_claude_bot_user_id.setToolTip("Slack平台添加的Claude显示的成员ID，参考文档的Claude板块进行配置")

            self.ui.label_claude2_cookie.setToolTip("claude.ai官网，打开F12，随便提问抓个包，请求头cookie配置于此")
            self.ui.label_claude2_use_proxy.setToolTip("是否启用代理发送请求")
            self.ui.label_claude2_proxies_http.setToolTip("http代理地址，默认为 http://127.0.0.1:10809")
            self.ui.label_claude2_proxies_https.setToolTip("https代理地址，默认为 http://127.0.0.1:10809")
            self.ui.label_claude2_proxies_socks5.setToolTip("socks5代理地址，默认为 socks://127.0.0.1:10808")

            # chatglm
            self.ui.label_chatglm_api_ip_port.setToolTip("ChatGLM的API版本运行后的服务链接（需要完整的URL）")
            self.ui.label_chatglm_max_length.setToolTip("生成回答的最大长度限制，以令牌数或字符数为单位。")
            self.ui.label_chatglm_top_p.setToolTip("也称为 Nucleus采样。控制模型生成时选择概率的阈值范围。")
            self.ui.label_chatglm_temperature.setToolTip("温度参数，控制生成文本的随机性。较高的温度值会产生更多的随机性和多样性。")
            self.ui.label_chatglm_history_enable.setToolTip("是否启用上下文历史记忆，让chatglm可以记得前面的内容")
            self.ui.label_chatglm_history_max_len.setToolTip("最大记忆的上下文字符数量，不建议设置过大，容易爆显存，自行根据情况配置")

            # langchain_chatglm
            self.ui.label_langchain_chatglm_api_ip_port.setToolTip("langchain_chatglm的API版本运行后的服务链接（需要完整的URL）")
            self.ui.label_langchain_chatglm_chat_type.setToolTip("选择的聊天类型：模型/知识库/必应")
            self.ui.label_langchain_chatglm_knowledge_base_id.setToolTip("本地存在的知识库名称，日志也有输出知识库列表，可以查看")
            self.ui.label_langchain_chatglm_history_enable.setToolTip("是否启用上下文历史记忆，让langchain_chatglm可以记得前面的内容")
            self.ui.label_langchain_chatglm_history_max_len.setToolTip("最大记忆的上下文字符数量，不建议设置过大，容易爆显存，自行根据情况配置")

            # 讯飞星火
            self.ui.label_sparkdesk_type.setToolTip("选择使用的类型，web抓包 或者 官方API")
            self.ui.label_sparkdesk_cookie.setToolTip("web抓包请求头中的cookie，参考文档教程")
            self.ui.label_sparkdesk_fd.setToolTip("web抓包负载中的fd，参考文档教程")
            self.ui.label_sparkdesk_GtToken.setToolTip("web抓包负载中的GtToken，参考文档教程")
            self.ui.label_sparkdesk_app_id.setToolTip("申请官方API后，云平台中提供的APPID")
            self.ui.label_sparkdesk_api_secret.setToolTip("申请官方API后，云平台中提供的APISecret")
            self.ui.label_sparkdesk_api_key.setToolTip("申请官方API后，云平台中提供的APIKey")
            self.ui.label_sparkdesk_version.setToolTip("此处选择模型版本号")
            
            self.ui.label_chat_with_file_chat_mode.setToolTip("本地向量数据库模式")
            self.ui.label_chat_with_file_data_path.setToolTip("加载的本地zip数据文件路径（到x.zip）, 如：./data/伊卡洛斯百度百科.zip")
            self.ui.label_chat_with_file_separator.setToolTip("拆分文本的分隔符，这里使用 换行符 作为分隔符。")
            self.ui.label_chat_with_file_chunk_size.setToolTip("每个文本块的最大字符数(文本块字符越多，消耗token越多，回复越详细)")
            self.ui.label_chat_with_file_chunk_overlap.setToolTip("两个相邻文本块之间的重叠字符数。这种重叠可以帮助保持文本的连贯性，特别是当文本被用于训练语言模型或其他需要上下文信息的机器学习模型时")
            self.ui.label_chat_with_file_local_vector_embedding_model.setToolTip("指定要使用的OpenAI模型名称")
            self.ui.label_chat_with_file_chain_type.setToolTip("指定要生成的语言链的类型，例如：stuff")
            self.ui.label_chat_with_file_show_token_cost.setToolTip("表示是否显示生成文本的成本。如果启用，将在终端中显示成本信息。")
            self.ui.label_chat_with_file_question_prompt.setToolTip("通过LLM总结本地向量数据库输出内容，此处填写总结用提示词")
            self.ui.label_chat_with_file_local_max_query.setToolTip("最大查询数据库次数。限制次数有助于节省token")

            self.ui.label_text_generation_webui_api_ip_port.setToolTip("text-generation-webui开启API模式后监听的IP和端口地址")
            self.ui.label_text_generation_webui_max_new_tokens.setToolTip("自行查阅")
            self.ui.label_text_generation_webui_mode.setToolTip("自行查阅")
            self.ui.label_text_generation_webui_character.setToolTip("自行查阅")
            self.ui.label_text_generation_webui_instruction_template.setToolTip("自行查阅")
            self.ui.label_text_generation_webui_your_name.setToolTip("自行查阅")

            self.ui.label_chatterbot_name.setToolTip("机器人名称")
            self.ui.label_chatterbot_db_path.setToolTip("数据库路径")

            self.ui.label_edge_tts_voice.setToolTip("选定的说话人(cmd执行：edge-tts -l 可以查看所有支持的说话人)")
            self.ui.label_edge_tts_rate.setToolTip("语速增益 默认是 +0%，可以增减，注意 + - %符合别搞没了，不然会影响语音合成")
            self.ui.label_edge_tts_volume.setToolTip("音量增益 默认是 +0%，可以增减，注意 + - %符合别搞没了，不然会影响语音合成")

            # vits_fast
            self.ui.label_vits_fast_config_path.setToolTip("配置文件的路径，例如：E:\\inference\\finetune_speaker.json")
            self.ui.label_vits_fast_api_ip_port.setToolTip("推理服务运行的链接（需要完整的URL）")
            self.ui.label_vits_fast_character.setToolTip("选择的说话人，配置文件中的speaker中的其中一个")
            self.ui.label_vits_fast_language.setToolTip("选择的合成文本的语言，建议和模型语言匹配，效果最佳")
            self.ui.label_vits_fast_speed.setToolTip("语速，默认为1")

            self.ui.label_elevenlabs_api_key.setToolTip("elevenlabs密钥，可以不填，默认也有一定额度的免费使用权限，具体多少不知道")
            self.ui.label_elevenlabs_voice.setToolTip("选择的说话人名")
            self.ui.label_elevenlabs_model.setToolTip("选择的模型")

            self.ui.label_genshinvoice_top_speaker.setToolTip("生成对应角色的语音")
            self.ui.label_genshinvoice_top_noise.setToolTip("控制感情变化程度，默认为0.2")
            self.ui.label_genshinvoice_top_noisew.setToolTip("控制音节发音长度变化程度，默认为0.9")
            self.ui.label_genshinvoice_top_length.setToolTip("可用于控制整体语速。默认为1.2")
            self.ui.label_genshinvoice_top_format.setToolTip("原有接口以WAV格式合成语音，在MP3格式合成语音的情况下，涉及到音频格式转换合成速度会变慢，建议选择WAV格式")
            self.ui.label_genshinvoice_top_language.setToolTip("合成文本对应的语言")

            # bark-gui
            self.ui.label_bark_gui_api_ip_port.setToolTip("bark-gui开启webui后监听的IP和端口地址")
            self.ui.label_bark_gui_spk.setToolTip("选择的说话人，webui的voice中对应的说话人")
            self.ui.label_bark_gui_generation_temperature.setToolTip("控制合成过程中生成语音的随机性。较高的值（接近1.0）会使输出更加随机，而较低的值（接近0.0）则使其更加确定性和集中。")
            self.ui.label_bark_gui_waveform_temperature.setToolTip("类似于generation_temperature，但该参数专门控制从语音模型生成的波形的随机性")
            self.ui.label_bark_gui_end_of_sentence_probability.setToolTip("该参数确定在句子结尾添加停顿或间隔的可能性。较高的值会增加停顿的几率，而较低的值则会减少。")
            self.ui.label_bark_gui_quick_generation.setToolTip("如果启用，可能会启用一些优化或在合成过程中采用更快的方式来生成语音。然而，这可能会影响语音的质量。")
            self.ui.label_bark_gui_seed.setToolTip("用于随机数生成器的种子值。使用特定的种子确保相同的输入文本每次生成的语音输出都是相同的。值为-1表示将使用随机种子。")
            self.ui.label_bark_gui_batch_count.setToolTip("指定一次批量合成的句子或话语数量。将其设置为1意味着逐句合成一次。")

            # 点歌
            self.ui.label_choose_song_enable.setToolTip("是否启用点歌模式")
            self.ui.label_choose_song_start_cmd.setToolTip("点歌触发命令（完全匹配才行）")
            self.ui.label_choose_song_stop_cmd.setToolTip("停止点歌命令（完全匹配才行）")
            self.ui.label_choose_song_random_cmd.setToolTip("随机点歌命令（完全匹配才行）")
            self.ui.label_choose_song_song_path.setToolTip("歌曲音频路径（默认为本项目的song文件夹）")
            self.ui.label_choose_song_match_fail_copy.setToolTip("匹配失败返回的音频文案 注意 {content} 这个是用于替换用户发送的歌名的，请务必不要乱删！影响使用！")

            # DDSP-SVC
            self.ui.label_ddsp_svc_enable.setToolTip("是否启用DDSP-SVC进行音频的变声")
            self.ui.label_ddsp_svc_config_path.setToolTip("模型配置文件config.yaml的路径(此处可以不配置，暂时没有用到)")
            self.ui.label_ddsp_svc_api_ip_port.setToolTip("flask_api服务运行的ip端口，例如：http://127.0.0.1:6844")
            self.ui.label_ddsp_svc_fSafePrefixPadLength.setToolTip("安全前缀填充长度，不知道干啥用，默认为0")
            self.ui.label_ddsp_svc_fPitchChange.setToolTip("音调设置，默认为0")
            self.ui.label_ddsp_svc_sSpeakId.setToolTip("说话人ID，需要和模型数据对应，默认为0")
            self.ui.label_ddsp_svc_sampleRate.setToolTip("DAW所需的采样率，默认为44100")

            # so-vits-svc
            self.ui.label_so_vits_svc_enable.setToolTip("是否启用so-vits-svc进行音频的变声")
            self.ui.label_so_vits_svc_config_path.setToolTip("模型配置文件config.json的路径")
            self.ui.label_so_vits_svc_api_ip_port.setToolTip("flask_api_full_song服务运行的ip端口，例如：http://127.0.0.1:1145")
            self.ui.label_so_vits_svc_spk.setToolTip("说话人，需要和配置文件内容对应")
            self.ui.label_so_vits_svc_tran.setToolTip("音调设置，默认为1")
            self.ui.label_so_vits_svc_wav_format.setToolTip("音频合成后输出的格式")

            # SD
            self.ui.label_sd_enable.setToolTip("是否启用SD来进行画图")
            self.ui.label_prompt_llm_type.setToolTip("选择LLM来对提示词进行优化")
            self.ui.label_prompt_llm_before_prompt.setToolTip("LLM提示词前缀")
            self.ui.label_prompt_llm_after_prompt.setToolTip("LLM提示词后缀")
            self.ui.label_sd_trigger.setToolTip("触发的关键词（弹幕头部触发）")
            self.ui.label_sd_ip.setToolTip("服务运行的IP地址")
            self.ui.label_sd_port.setToolTip("服务运行的端口")
            self.ui.label_sd_negative_prompt.setToolTip("负面文本提示，用于指定与生成图像相矛盾或相反的内容")
            self.ui.label_sd_seed.setToolTip("随机种子，用于控制生成过程的随机性。可以设置一个整数值，以获得可重复的结果。")
            self.ui.label_sd_styles.setToolTip("样式列表，用于指定生成图像的风格。可以包含多个风格，例如 [\"anime\", \"portrait\"]")
            self.ui.label_sd_cfg_scale.setToolTip("提示词相关性，无分类器指导信息影响尺度(Classifier Free Guidance Scale) -图像应在多大程度上服从提示词-较低的值会产生更有创意的结果。")
            self.ui.label_sd_steps.setToolTip("生成图像的步数，用于控制生成的精确程度。")
            self.ui.label_sd_enable_hr.setToolTip("是否启用高分辨率生成。默认为 False。")
            self.ui.label_sd_hr_scale.setToolTip("高分辨率缩放因子，用于指定生成图像的高分辨率缩放级别。")
            self.ui.label_sd_hr_second_pass_steps.setToolTip("高分辨率生成的第二次传递步数。")
            self.ui.label_sd_hr_resize_x.setToolTip("生成图像的水平尺寸。")
            self.ui.label_sd_hr_resize_y.setToolTip("生成图像的垂直尺寸。")
            self.ui.label_sd_denoising_strength.setToolTip("去噪强度，用于控制生成图像中的噪点。")

            self.ui.label_header_useragent.setToolTip("请求头，暂时没有用到，备用")

            # 文案
            self.ui.label_copywriting_config_index.setToolTip("文案编号索引，用于对指定编号进行增加删除操作")
            self.ui.pushButton_copywriting_config_index_add.setToolTip("对指定编号文案进行增加操作")
            self.ui.pushButton_copywriting_config_index_del.setToolTip("对指定编号文案进行删除操作")
            self.ui.label_copywriting_audio_interval.setToolTip("文案音频播放之间的间隔时间。就是前一个文案播放完成后，到后一个文案开始播放之间的间隔时间。")
            self.ui.label_copywriting_switching_interval.setToolTip("文案音频切换到弹幕音频的切换间隔时间（反之一样）。\n就是在播放文案时，有弹幕触发并合成完毕，此时会暂停文案播放，然后等待这个间隔时间后，再播放弹幕回复音频。")
            self.ui.label_copywriting_switching_auto_play.setToolTip("文案自动播放，就是说启用后，会自动播放，不需要手动点播放了")
            self.ui.label_copywriting_switching_random_play.setToolTip("文案随机播放，就是不根据播放音频文件列表的顺序播放，而是随机打乱顺序进行播放。")
            self.ui.label_copywriting_select.setToolTip("输入要加载的文案文件全名，文件全名从文案列表中复制。如果文件不存在，则会自动创建")
            self.ui.pushButton_copywriting_select.setToolTip("加载 左侧输入框中的文件相对/绝对路径的文件内容，输出到下方编辑框内。如果文件不存在，则会自动创建")
            self.ui.pushButton_copywriting_refresh_list.setToolTip("刷新 文案列表、音频列表中的内容，用于加载新数据")
            self.ui.label_copywriting_edit.setToolTip("此处由上方 选择的文案通过加载读取文件内容，在此可以修改文案内容，方便重新合成")
            self.ui.pushButton_copywriting_save.setToolTip("保存上方 文案编辑框中的内容到文案文件中")
            self.ui.pushButton_copywriting_synthetic_audio.setToolTip("读取当前选择的文案文件内容，通过配置的 语音合成模式来进行合成，和弹幕合成机制类似。\n需要注意，合成前记得保存文案，合成文案较多时，请耐心等待。建议：自行手动合成文案音频，放到文案音频目录中，这里合成感觉不太行")
            self.ui.pushButton_copywriting_loop_play.setToolTip("循环播放 播放列表中配置的音频文件（记得保存配置）。")
            self.ui.pushButton_copywriting_pause_play.setToolTip("暂停当前播放的音频")

            # 聊天
            self.ui.label_talk_username.setToolTip("日志中你的名字，暂时没有实质作用")
            self.ui.label_talk_continuous_talk.setToolTip("是否开启连续对话模式，点击触发按键后可以持续进行录音，点击停录按键停止录音")
            self.ui.label_talk_trigger_key.setToolTip("录音触发按键（单击此按键进行录音）")
            self.ui.label_talk_stop_trigger_key.setToolTip("停止录音按键（单击此按键停止下一次录音）")
            self.ui.label_talk_type.setToolTip("选择的语音识别类型")
            self.ui.label_talk_volume_threshold.setToolTip("音量阈值，指的是触发录音的起始音量值，请根据自己的麦克风进行微调到最佳")
            self.ui.label_talk_silence_threshold.setToolTip("沉默阈值，指的是触发停止路径的最低音量值，请根据自己的麦克风进行微调到最佳")
            self.ui.label_talk_baidu_app_id.setToolTip("百度云 语音识别应用的 AppID")
            self.ui.label_talk_baidu_api_key.setToolTip("百度云 语音识别应用的 API Key")
            self.ui.label_talk_baidu_secret_key.setToolTip("百度云 语音识别应用的 Secret Key")
            self.ui.label_talk_google_tgt_lang.setToolTip("录音后识别转换成的目标语言（就是你说的语言）")
            self.ui.label_talk_chat_box.setToolTip("此处填写对话内容可以直接进行对话（前面配置好聊天模式，记得运行先）")
            self.ui.pushButton_talk_chat_box_send.setToolTip("点击发送聊天框内的内容")
            self.ui.pushButton_talk_chat_box_reread.setToolTip("点击发送聊天框内的内容，直接让程序通过配置的TTS和变声进行复读")
            
            # 动态文案
            self.ui.label_trends_copywriting_enable.setToolTip("是否启用动态文案功能")
            self.ui.label_trends_copywriting_random_play.setToolTip("是否启用随机播放功能")
            self.ui.label_trends_copywriting_play_interval.setToolTip("文案于文案之间的播放间隔时间（秒）")

            # 按键映射
            self.ui.label_key_mapping_enable.setToolTip("是否启用按键映射功能")
            self.ui.label_key_mapping_type.setToolTip("触发按键映射功能的板块类型")
            self.ui.label_key_mapping_start_cmd.setToolTip("按键映射命令的命令起始，默认为：按键 ，如果弹幕不是这个命令打头，则不会触发")

            # 积分页
            self.ui.label_integral_common_enable.setToolTip("是否启用积分机制")

            """
                配置同步UI
            """
            # 修改下拉框内容
            self.ui.comboBox_platform.clear()
            self.ui.comboBox_platform.addItems(["聊天模式", "哔哩哔哩", "抖音", "快手", "斗鱼", "YouTube", "twitch", "哔哩哔哩2"])
            platform_index = 0
            if self.platform == "talk":
                platform_index = 0
            elif self.platform == "bilibili":
                platform_index = 1
            elif self.platform == "dy":
                platform_index = 2
            elif self.platform == "ks":
                platform_index = 3
            elif self.platform == "douyu":
                platform_index = 4
            elif self.platform == "youtube":
                platform_index = 5
            elif self.platform == "twitch":
                platform_index = 6
            elif self.platform == "bilibili2":
                platform_index = 7
            self.ui.comboBox_platform.setCurrentIndex(platform_index)
            
            # 修改输入框内容
            self.ui.lineEdit_room_display_id.setText(self.room_id)
            
            # 新增LLM时，需要为这块的下拉菜单追加配置项
            self.ui.comboBox_chat_type.clear()
            self.ui.comboBox_chat_type.addItems([
                "不启用", 
                "复读机", 
                "ChatGPT/闻达", 
                "Claude", 
                "Claude2", 
                "ChatGLM", 
                "chat_with_file", 
                "Chatterbot", 
                "text_generation_webui", 
                "讯飞星火",
                "langchain_chatglm",
                "智谱AI",
                "Bard",
                "文心一言",
                "通义千问"
            ])
            chat_type_index = 0
            if self.chat_type == "none":
                chat_type_index = 0
            elif self.chat_type == "reread":
                chat_type_index = 1
            elif self.chat_type == "chatgpt":
                chat_type_index = 2
            elif self.chat_type == "claude":
                chat_type_index = 3
            elif self.chat_type == "claude2":
                chat_type_index = 4
            elif self.chat_type == "chatglm":
                chat_type_index = 5
            elif self.chat_type == "chat_with_file":
                chat_type_index = 6
            elif self.chat_type == "chatterbot":
                chat_type_index = 7
            elif self.chat_type == "text_generation_webui":
                chat_type_index = 8
            elif self.chat_type == "sparkdesk":
                chat_type_index = 9
            elif self.chat_type == "langchain_chatglm":
                chat_type_index = 10
            elif self.chat_type == "zhipu":
                chat_type_index = 11
            elif self.chat_type == "bard":
                chat_type_index = 12
            elif self.chat_type == "yiyan":
                chat_type_index = 13
            elif self.chat_type == "tongyi":
                chat_type_index = 14
            self.ui.comboBox_chat_type.setCurrentIndex(chat_type_index)

            # 虚拟身体
            self.ui.comboBox_visual_body.clear()
            self.ui.comboBox_visual_body.addItems(["其他", "xuniren", "unity"])
            visual_body_index = 0
            if config.get("visual_body") == "其他":
                visual_body_index = 0
            elif config.get("visual_body") == "xuniren":
                visual_body_index = 1
            elif config.get("visual_body") == "unity":
                visual_body_index = 2
            self.ui.comboBox_visual_body.setCurrentIndex(visual_body_index)
            
            self.ui.comboBox_need_lang.clear()
            self.ui.comboBox_need_lang.addItems(["所有", "中文", "英文", "日文"])
            need_lang_index = 0
            if self.need_lang == "none":
                need_lang_index = 0
            elif self.need_lang == "zh":
                need_lang_index = 1
            elif self.need_lang == "en":
                need_lang_index = 2
            elif self.need_lang == "jp":
                need_lang_index = 3
            self.ui.comboBox_need_lang.setCurrentIndex(need_lang_index)

            self.ui.lineEdit_before_prompt.setText(self.before_prompt)
            self.ui.lineEdit_after_prompt.setText(self.after_prompt)

            # 本地问答
            if config.get("read_user_name", "enable"):
                self.ui.checkBox_read_user_name_enable.setChecked(True)
            if config.get("read_user_name", "voice_change"):
                self.ui.checkBox_read_user_name_voice_change.setChecked(True)
            tmp_str = ""
            for tmp in config.get("read_user_name", "reply_before"):
                tmp_str = tmp_str + tmp + "\n"
            self.ui.textEdit_read_user_name_reply_before.setText(tmp_str)
            tmp_str = ""
            for tmp in config.get("read_user_name", "reply_after"):
                tmp_str = tmp_str + tmp + "\n"
            self.ui.textEdit_read_user_name_reply_after.setText(tmp_str)

            self.ui.comboBox_comment_log_type.clear()
            comment_log_types = ["问答", "问题", "回答", "不记录"]
            self.ui.comboBox_comment_log_type.addItems(comment_log_types)
            comment_log_type_index = comment_log_types.index(self.comment_log_type)
            self.ui.comboBox_comment_log_type.setCurrentIndex(comment_log_type_index)


            # 日志
            if self.captions_config['enable']:
                self.ui.checkBox_captions_enable.setChecked(True)
            self.ui.lineEdit_captions_file_path.setText(self.captions_config['file_path'])

            # 本地问答
            if self.local_qa_config['text']['enable']:
                self.ui.checkBox_local_qa_text_enable.setChecked(True)
            self.ui.comboBox_local_qa_text_type.clear()
            local_qa_text_types = ["自定义json", "一问一答"]
            self.ui.comboBox_local_qa_text_type.addItems(local_qa_text_types)
            if self.local_qa_config['text']['type'] == "text":
                self.ui.comboBox_local_qa_text_type.setCurrentIndex(1)
            else:
                self.ui.comboBox_local_qa_text_type.setCurrentIndex(0)
            self.ui.lineEdit_local_qa_text_file_path.setText(self.local_qa_config['text']['file_path'])
            self.ui.lineEdit_local_qa_text_similarity.setText(str(self.local_qa_config['text']['similarity']))
            if self.local_qa_config['audio']['enable']:
                self.ui.checkBox_local_qa_audio_enable.setChecked(True)
            self.ui.lineEdit_local_qa_audio_file_path.setText(self.local_qa_config['audio']['file_path'])
            self.ui.lineEdit_local_qa_audio_similarity.setText(str(self.local_qa_config['audio']['similarity']))

            # 过滤
            tmp_str = ""
            for tmp in self.filter_config['before_must_str']:
                tmp_str = tmp_str + tmp + "\n"
            self.ui.textEdit_filter_before_must_str.setText(tmp_str)
            tmp_str = ""
            for tmp in self.filter_config['after_must_str']:
                tmp_str = tmp_str + tmp + "\n"
            self.ui.textEdit_filter_after_must_str.setText(tmp_str)
            self.ui.lineEdit_filter_badwords_path.setText(self.filter_config['badwords_path'])
            self.ui.lineEdit_filter_bad_pinyin_path.setText(self.filter_config['bad_pinyin_path'])
            self.ui.lineEdit_filter_max_len.setText(str(self.filter_config['max_len']))
            self.ui.lineEdit_filter_max_char_len.setText(str(self.filter_config['max_char_len']))
            self.ui.lineEdit_filter_comment_forget_duration.setText(str(self.filter_config['comment_forget_duration']))
            self.ui.lineEdit_filter_comment_forget_reserve_num.setText(str(self.filter_config['comment_forget_reserve_num']))
            self.ui.lineEdit_filter_gift_forget_duration.setText(str(self.filter_config['gift_forget_duration']))
            self.ui.lineEdit_filter_gift_forget_reserve_num.setText(str(self.filter_config['gift_forget_reserve_num']))
            self.ui.lineEdit_filter_entrance_forget_duration.setText(str(self.filter_config['entrance_forget_duration']))
            self.ui.lineEdit_filter_entrance_forget_reserve_num.setText(str(self.filter_config['entrance_forget_reserve_num']))
            self.ui.lineEdit_filter_follow_forget_duration.setText(str(self.filter_config['follow_forget_duration']))
            self.ui.lineEdit_filter_follow_forget_reserve_num.setText(str(self.filter_config['follow_forget_reserve_num']))
            self.ui.lineEdit_filter_talk_forget_duration.setText(str(self.filter_config['talk_forget_duration']))
            self.ui.lineEdit_filter_talk_forget_reserve_num.setText(str(self.filter_config['talk_forget_reserve_num']))
            self.ui.lineEdit_filter_schedule_forget_duration.setText(str(self.filter_config['schedule_forget_duration']))
            self.ui.lineEdit_filter_schedule_forget_reserve_num.setText(str(self.filter_config['schedule_forget_reserve_num']))
            

            # 答谢
            if self.thanks_config['entrance_enable']:
                self.ui.checkBox_thanks_entrance_enable.setChecked(True)
            self.ui.lineEdit_thanks_entrance_copy.setText(self.thanks_config['entrance_copy'])
            if self.thanks_config['gift_enable']:
                self.ui.checkBox_thanks_gift_enable.setChecked(True)
            self.ui.lineEdit_thanks_gift_copy.setText(self.thanks_config['gift_copy'])
            self.ui.lineEdit_thanks_lowest_price.setText(str(self.thanks_config['lowest_price']))
            if self.thanks_config['follow_enable']:
                self.ui.checkBox_thanks_follow_enable.setChecked(True)
            self.ui.lineEdit_thanks_follow_copy.setText(self.thanks_config['follow_copy'])

            if self.live2d_config['enable']:
                self.ui.checkBox_live2d_enable.setChecked(True)
            self.ui.lineEdit_live2d_port.setText(str(self.live2d_config['port']))
            self.ui.comboBox_live2d_name.clear()
            live2d_names = common.get_folder_names("Live2D/live2d-model") # 路径写死
            logging.info(f"本地Live2D模型名列表：{live2d_names}")
            self.ui.comboBox_live2d_name.addItems(live2d_names)
            live2d_model_name = common.get_live2d_model_name("Live2D/js/model_name.js") # 路径写死
            live2d_name_index = live2d_names.index(live2d_model_name)
            self.ui.comboBox_live2d_name.setCurrentIndex(live2d_name_index)
            self.ui.comboBox_live2d_name.setEditable(True)
            self.ui.comboBox_live2d_name.original_items = live2d_names
            self.ui.comboBox_live2d_name.lineEdit().textChanged.connect(lambda text, combo=self.ui.comboBox_live2d_name: self.filter_combobox(combo, text, manual_clear=True))
            

            # 音频随机变速
            if config.get("audio_random_speed", "normal", "enable"):
                self.ui.checkBox_audio_random_speed_normal_enable.setChecked(True)
            self.ui.lineEdit_audio_random_speed_normal_speed_min.setText(str(config.get("audio_random_speed", "normal", "speed_min")))
            self.ui.lineEdit_audio_random_speed_normal_speed_max.setText(str(config.get("audio_random_speed", "normal", "speed_max")))
            if config.get("audio_random_speed", "copywriting", "enable"):
                self.ui.checkBox_audio_random_speed_copywriting_enable.setChecked(True)
            self.ui.lineEdit_audio_random_speed_copywriting_speed_min.setText(str(config.get("audio_random_speed", "copywriting", "speed_min")))
            self.ui.lineEdit_audio_random_speed_copywriting_speed_max.setText(str(config.get("audio_random_speed", "copywriting", "speed_max")))

            self.ui.lineEdit_header_useragent.setText(self.header_config['userAgent'])

            self.ui.lineEdit_openai_api.setText(self.openai_config['api'])
            tmp_str = ""
            for tmp in self.openai_config['api_key']:
                tmp_str = tmp_str + tmp + "\n"
            self.ui.textEdit_openai_api_key.setText(tmp_str)

            self.ui.comboBox_chatgpt_model.clear()
            chatgpt_models = ["gpt-3.5-turbo",
                "gpt-3.5-turbo-0301",
                "gpt-3.5-turbo-0613",
                "gpt-3.5-turbo-16k",
                "gpt-3.5-turbo-16k-0613",
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
            self.ui.comboBox_chatgpt_model.addItems(chatgpt_models)
            chatgpt_model_index = chatgpt_models.index(self.chatgpt_config['model'])
            self.ui.comboBox_chatgpt_model.setCurrentIndex(chatgpt_model_index)
            self.ui.lineEdit_chatgpt_temperature.setText(str(self.chatgpt_config['temperature']))
            self.ui.lineEdit_chatgpt_max_tokens.setText(str(self.chatgpt_config['max_tokens']))
            self.ui.lineEdit_chatgpt_top_p.setText(str(self.chatgpt_config['top_p']))
            self.ui.lineEdit_chatgpt_presence_penalty.setText(str(self.chatgpt_config['presence_penalty']))
            self.ui.lineEdit_chatgpt_frequency_penalty.setText(str(self.chatgpt_config['frequency_penalty']))
            self.ui.lineEdit_chatgpt_preset.setText(self.chatgpt_config['preset'])

            self.ui.lineEdit_claude_slack_user_token.setText(self.claude_config['slack_user_token'])
            self.ui.lineEdit_claude_bot_user_id.setText(self.claude_config['bot_user_id'])

            self.ui.lineEdit_claude2_cookie.setText(self.claude2_config['cookie'])
            if self.claude2_config['use_proxy']:
                self.ui.checkBox_claude2_use_proxy.setChecked(True)
            self.ui.lineEdit_claude2_proxies_http.setText(self.claude2_config['proxies']['http'])
            self.ui.lineEdit_claude2_proxies_https.setText(self.claude2_config['proxies']['https'])
            self.ui.lineEdit_claude2_proxies_socks5.setText(self.claude2_config['proxies']['socks5'])

            # chatglm
            self.ui.lineEdit_chatglm_api_ip_port.setText(self.chatglm_config['api_ip_port'])
            self.ui.lineEdit_chatglm_max_length.setText(str(self.chatglm_config['max_length']))
            self.ui.lineEdit_chatglm_top_p.setText(str(self.chatglm_config['top_p']))
            self.ui.lineEdit_chatglm_temperature.setText(str(self.chatglm_config['temperature']))
            if self.chatglm_config['history_enable']:
                self.ui.checkBox_chatglm_history_enable.setChecked(True)
            self.ui.lineEdit_chatglm_history_max_len.setText(str(self.chatglm_config['history_max_len']))

            # langchain_chatglm
            self.ui.lineEdit_langchain_chatglm_api_ip_port.setText(config.get("langchain_chatglm", "api_ip_port"))
            self.ui.comboBox_langchain_chatglm_chat_type.clear()
            self.ui.comboBox_langchain_chatglm_chat_type.addItems(["模型", "知识库", "必应"])
            langchain_chatglm_chat_type_index = 0
            if config.get("langchain_chatglm", "chat_type") == "模型":
                langchain_chatglm_chat_type_index = 0
            elif config.get("langchain_chatglm", "chat_type") == "知识库":
                langchain_chatglm_chat_type_index = 1
            elif config.get("langchain_chatglm", "chat_type") == "必应":
                langchain_chatglm_chat_type_index = 2
            self.ui.comboBox_langchain_chatglm_chat_type.setCurrentIndex(langchain_chatglm_chat_type_index)
            self.ui.lineEdit_langchain_chatglm_knowledge_base_id.setText(config.get("langchain_chatglm", "knowledge_base_id"))
            if config.get("langchain_chatglm", "history_enable"):
                self.ui.checkBox_langchain_chatglm_history_enable.setChecked(True)
            self.ui.lineEdit_langchain_chatglm_history_max_len.setText(str(config.get("langchain_chatglm", "history_max_len")))

            self.ui.comboBox_chat_with_file_chat_mode.clear()
            self.ui.comboBox_chat_with_file_chat_mode.addItems(["claude", "openai_gpt", "openai_vector_search"])
            chat_with_file_chat_mode_index = 0
            if self.chat_with_file_config['chat_mode'] == "claude":
                chat_with_file_chat_mode_index = 0
            elif self.chat_with_file_config['chat_mode'] == "openai_gpt":
                chat_with_file_chat_mode_index = 1
            elif self.chat_with_file_config['chat_mode'] == "openai_vector_search":
                chat_with_file_chat_mode_index = 2
            self.ui.comboBox_chat_with_file_chat_mode.setCurrentIndex(chat_with_file_chat_mode_index)
            self.ui.comboBox_chat_with_file_local_vector_embedding_model.clear()
            self.ui.comboBox_chat_with_file_local_vector_embedding_model.addItems(["sebastian-hofstaetter/distilbert-dot-tas_b-b256-msmarco", "GanymedeNil/text2vec-large-chinese"])
            chat_with_file_local_vector_embedding_model_index = 0
            if self.chat_with_file_config['local_vector_embedding_model'] == "sebastian-hofstaetter/distilbert-dot-tas_b-b256-msmarco":
                chat_with_file_local_vector_embedding_model_index = 0
            elif self.chat_with_file_config['local_vector_embedding_model'] == "GanymedeNil/text2vec-large-chinese":
                chat_with_file_local_vector_embedding_model_index = 1
            self.ui.comboBox_chat_with_file_local_vector_embedding_model.setCurrentIndex(chat_with_file_local_vector_embedding_model_index)
            self.ui.lineEdit_chat_with_file_data_path.setText(self.chat_with_file_config['data_path'])
            self.ui.lineEdit_chat_with_file_separator.setText(self.chat_with_file_config['separator'])
            self.ui.lineEdit_chat_with_file_chunk_size.setText(str(self.chat_with_file_config['chunk_size']))
            self.ui.lineEdit_chat_with_file_chunk_overlap.setText(str(self.chat_with_file_config['chunk_overlap']))
            self.ui.lineEdit_chat_with_file_question_prompt.setText(str(self.chat_with_file_config['question_prompt']))
            self.ui.lineEdit_chat_with_file_local_max_query.setText(str(self.chat_with_file_config['local_max_query']))
            self.ui.lineEdit_chat_with_file_chain_type.setText(self.chat_with_file_config['chain_type'])
            if self.chat_with_file_config['show_token_cost']:
                self.ui.checkBox_chat_with_file_show_token_cost.setChecked(True)

            self.ui.lineEdit_chatterbot_name.setText(self.chatterbot_config['name'])
            self.ui.lineEdit_chatterbot_db_path.setText(self.chatterbot_config['db_path'])

            self.ui.lineEdit_text_generation_webui_api_ip_port.setText(str(self.text_generation_webui_config['api_ip_port']))
            self.ui.lineEdit_text_generation_webui_max_new_tokens.setText(str(self.text_generation_webui_config['max_new_tokens']))
            self.ui.lineEdit_text_generation_webui_mode.setText(str(self.text_generation_webui_config['mode']))
            self.ui.lineEdit_text_generation_webui_character.setText(str(self.text_generation_webui_config['character']))
            self.ui.lineEdit_text_generation_webui_instruction_template.setText(str(self.text_generation_webui_config['instruction_template']))
            self.ui.lineEdit_text_generation_webui_your_name.setText(str(self.text_generation_webui_config['your_name']))

            # 讯飞星火
            self.ui.comboBox_sparkdesk_type.clear()
            self.ui.comboBox_sparkdesk_type.addItems(["web", "api"])
            sparkdesk_type_index = 0
            if self.sparkdesk_config['type'] == "web":
                sparkdesk_type_index = 0
            elif self.sparkdesk_config['type'] == "api":
                sparkdesk_type_index = 1
            self.ui.comboBox_sparkdesk_type.setCurrentIndex(sparkdesk_type_index)
            self.ui.lineEdit_sparkdesk_cookie.setText(self.sparkdesk_config['cookie'])
            self.ui.lineEdit_sparkdesk_fd.setText(self.sparkdesk_config['fd'])
            self.ui.lineEdit_sparkdesk_GtToken.setText(self.sparkdesk_config['GtToken'])
            self.ui.lineEdit_sparkdesk_app_id.setText(self.sparkdesk_config['app_id'])
            self.ui.lineEdit_sparkdesk_api_secret.setText(self.sparkdesk_config['api_secret'])
            self.ui.lineEdit_sparkdesk_api_key.setText(self.sparkdesk_config['api_key'])
            self.ui.comboBox_sparkdesk_version.clear()
            self.ui.comboBox_sparkdesk_version.addItems(["3.1", "2.1", "1.1"])
            sparkdesk_version_index = 0
            if self.sparkdesk_config['version'] == 3.1:
                sparkdesk_version_index = 0
            elif self.sparkdesk_config['version'] == 2.1:
                sparkdesk_version_index = 1
            elif self.sparkdesk_config['version'] == 1.1:
                sparkdesk_version_index = 2
            self.ui.comboBox_sparkdesk_version.setCurrentIndex(sparkdesk_version_index)

            self.ui.comboBox_audio_synthesis_type.clear()
            self.ui.comboBox_audio_synthesis_type.addItems(["Edge-TTS", "VITS", "VITS-Fast", "elevenlabs", "genshinvoice_top", "bark_gui", "VALL-E-X", "OpenAI TTS"])
            audio_synthesis_type_index = 0
            if self.audio_synthesis_type == "edge-tts":
                audio_synthesis_type_index = 0
            elif self.audio_synthesis_type == "vits":
                audio_synthesis_type_index = 1
            elif self.audio_synthesis_type == "vits_fast":
                audio_synthesis_type_index = 2
            elif self.audio_synthesis_type == "elevenlabs":
                audio_synthesis_type_index = 3
            elif self.audio_synthesis_type == "genshinvoice_top":
                audio_synthesis_type_index = 4
            elif self.audio_synthesis_type == "bark_gui":
                audio_synthesis_type_index = 5
            elif self.audio_synthesis_type == "vall_e_x":
                audio_synthesis_type_index = 6
            elif self.audio_synthesis_type == "openai_tts":
                audio_synthesis_type_index = 7
            self.ui.comboBox_audio_synthesis_type.setCurrentIndex(audio_synthesis_type_index)

            # vits_fast
            self.ui.lineEdit_vits_fast_config_path.setText(self.vits_fast_config['config_path'])
            self.ui.lineEdit_vits_fast_api_ip_port.setText(self.vits_fast_config['api_ip_port'])
            self.ui.lineEdit_vits_fast_character.setText(self.vits_fast_config['character'])
            self.ui.comboBox_vits_fast_language.clear()
            self.ui.comboBox_vits_fast_language.addItems(["自动识别", "日本語", "简体中文", "English", "Mix"])
            vits_fast_language_index = 0
            if self.vits_fast_config['language'] == "自动识别":
                vits_fast_language_index = 0
            elif self.vits_fast_config['language'] == "日本語":
                vits_fast_language_index = 1
            elif self.vits_fast_config['language'] == "简体中文":
                vits_fast_language_index = 2
            elif self.vits_fast_config['language'] == "English":
                vits_fast_language_index = 3
            elif self.vits_fast_config['language'] == "Mix":
                vits_fast_language_index = 4
            self.ui.comboBox_vits_fast_language.setCurrentIndex(vits_fast_language_index)
            self.ui.lineEdit_vits_fast_speed.setText(str(self.vits_fast_config['speed']))

            self.ui.comboBox_edge_tts_voice.clear()
            with open('data\edge-tts-voice-list.txt', 'r') as file:
                file_content = file.read()
            # 按行分割内容，并去除每行末尾的换行符
            lines = file_content.strip().split('\n')
            # 存储到字符串数组中
            edge_tts_voices = [line for line in lines]
            # print(edge_tts_voices)
            self.ui.comboBox_edge_tts_voice.addItems(edge_tts_voices)
            edge_tts_voice_index = edge_tts_voices.index(self.edge_tts_config['voice'])
            self.ui.comboBox_edge_tts_voice.setCurrentIndex(edge_tts_voice_index)
            self.ui.lineEdit_edge_tts_rate.setText(self.edge_tts_config['rate'])
            self.ui.lineEdit_edge_tts_volume.setText(self.edge_tts_config['volume'])

            self.ui.lineEdit_elevenlabs_api_key.setText(self.elevenlabs_config['api_key'])
            self.ui.lineEdit_elevenlabs_voice.setText(self.elevenlabs_config['voice'])
            self.ui.lineEdit_elevenlabs_model.setText(self.elevenlabs_config['model'])

            self.ui.comboBox_genshinvoice_top_speaker.clear()
            with open('data\genshinvoice_top_speak_list.txt', 'r', encoding='utf-8') as file:
                file_content = file.read()
            # 按行分割内容，并去除每行末尾的换行符
            lines = file_content.strip().split('\n')
            # 存储到字符串数组中
            genshinvoice_top_speaker = [line for line in lines]
            # print(genshinvoice_top_speaker)
            self.ui.comboBox_genshinvoice_top_speaker.addItems(genshinvoice_top_speaker)
            self.ui.comboBox_genshinvoice_top_speaker.setEditable(True)
            self.ui.comboBox_genshinvoice_top_speaker.original_items = genshinvoice_top_speaker
            genshinvoice_top_speaker_index = genshinvoice_top_speaker.index(self.genshinvoice_top_config['speaker'])
            self.ui.comboBox_genshinvoice_top_speaker.setCurrentIndex(genshinvoice_top_speaker_index)
            self.ui.comboBox_genshinvoice_top_speaker.lineEdit().textChanged.connect(lambda text, combo=self.ui.comboBox_genshinvoice_top_speaker: self.filter_combobox(combo, text, manual_clear=True))
            self.ui.lineEdit_genshinvoice_top_noise.setText(self.genshinvoice_top_config['noise'])
            self.ui.lineEdit_genshinvoice_top_noisew.setText(self.genshinvoice_top_config['noisew'])
            self.ui.lineEdit_genshinvoice_top_length.setText(self.genshinvoice_top_config['length'])
            self.ui.lineEdit_genshinvoice_top_format.setText(self.genshinvoice_top_config['format'])
            self.ui.comboBox_genshinvoice_top_language.clear()
            self.ui.comboBox_genshinvoice_top_language.addItems(["ZH", "EN", "JP"])
            genshinvoice_top_language_index = 0
            if config.get("genshinvoice_top", "language") == "ZH":
                genshinvoice_top_language_index = 0
            elif config.get("genshinvoice_top", "language") == "EN":
                genshinvoice_top_language_index = 1
            elif config.get("genshinvoice_top", "language") == "JP":
                genshinvoice_top_language_index = 2 
            self.ui.comboBox_genshinvoice_top_language.setCurrentIndex(genshinvoice_top_language_index)

            # bark-gui
            self.ui.lineEdit_bark_gui_api_ip_port.setText(config.get("bark_gui", "api_ip_port"))
            self.ui.lineEdit_bark_gui_spk.setText(config.get("bark_gui", "spk"))
            self.ui.lineEdit_bark_gui_generation_temperature.setText(str(config.get("bark_gui", "generation_temperature")))
            self.ui.lineEdit_bark_gui_waveform_temperature.setText(str(config.get("bark_gui", "waveform_temperature")))
            self.ui.lineEdit_bark_gui_end_of_sentence_probability.setText(str(config.get("bark_gui", "end_of_sentence_probability")))
            if config.get("bark_gui", "quick_generation"):
                self.ui.checkBox_bark_gui_quick_generation.setChecked(True)
            self.ui.lineEdit_bark_gui_seed.setText(str(config.get("bark_gui", "seed")))
            self.ui.lineEdit_bark_gui_batch_count.setText(str(config.get("bark_gui", "batch_count")))

            # 点歌模式 配置回显部分
            if self.choose_song_config['enable']:
                self.ui.checkBox_choose_song_enable.setChecked(True)
            self.ui.lineEdit_choose_song_start_cmd.setText(self.choose_song_config['start_cmd'])
            self.ui.lineEdit_choose_song_stop_cmd.setText(self.choose_song_config['stop_cmd'])
            self.ui.lineEdit_choose_song_random_cmd.setText(self.choose_song_config['random_cmd'])
            self.ui.lineEdit_choose_song_song_path.setText(self.choose_song_config['song_path'])
            self.ui.lineEdit_choose_song_match_fail_copy.setText(self.choose_song_config['match_fail_copy'])

            # ddsp-svc
            if config.get("ddsp_svc", "enable"):
                self.ui.checkBox_ddsp_svc_enable.setChecked(True)
            self.ui.lineEdit_ddsp_svc_config_path.setText(config.get("ddsp_svc", "config_path"))
            self.ui.lineEdit_ddsp_svc_api_ip_port.setText(config.get("ddsp_svc", "api_ip_port"))
            self.ui.lineEdit_ddsp_svc_fSafePrefixPadLength.setText(str(config.get("ddsp_svc", "fSafePrefixPadLength")))
            self.ui.lineEdit_ddsp_svc_fPitchChange.setText(str(config.get("ddsp_svc", "fPitchChange")))
            self.ui.lineEdit_ddsp_svc_sSpeakId.setText(str(config.get("ddsp_svc", "sSpeakId")))
            self.ui.lineEdit_ddsp_svc_sampleRate.setText(str(config.get("ddsp_svc", "sampleRate")))

            if self.so_vits_svc_config['enable']:
                self.ui.checkBox_so_vits_svc_enable.setChecked(True)
            self.ui.lineEdit_so_vits_svc_config_path.setText(self.so_vits_svc_config['config_path'])
            self.ui.lineEdit_so_vits_svc_api_ip_port.setText(self.so_vits_svc_config['api_ip_port'])
            self.ui.lineEdit_so_vits_svc_spk.setText(self.so_vits_svc_config['spk'])
            self.ui.lineEdit_so_vits_svc_tran.setText(str(self.so_vits_svc_config['tran']))
            self.ui.lineEdit_so_vits_svc_wav_format.setText(self.so_vits_svc_config['wav_format'])

            # sd 配置回显部分
            if self.sd_config['enable']:
                self.ui.checkBox_sd_enable.setChecked(True)
            self.ui.lineEdit_sd_trigger.setText(self.sd_config['trigger'])
            self.ui.comboBox_prompt_llm_type.clear()
            self.ui.comboBox_prompt_llm_type.addItems(["chatgpt", "claude", "chatglm", "text_generation_webui", "none"])
            prompt_llm_type_index = 0
            if self.sd_config['prompt_llm']['type'] == "chatgpt":
                prompt_llm_type_index = 0
            elif self.sd_config['prompt_llm']['type'] == "claude":
                prompt_llm_type_index = 1
            elif self.sd_config['prompt_llm']['type'] == "chatglm":
                prompt_llm_type_index = 2 
            elif self.sd_config['prompt_llm']['type'] == "text_generation_webui":
                prompt_llm_type_index = 3
            elif self.sd_config['prompt_llm']['type'] == "none":
                prompt_llm_type_index = 4
            self.ui.comboBox_prompt_llm_type.setCurrentIndex(prompt_llm_type_index)
            self.ui.lineEdit_prompt_llm_before_prompt.setText(self.sd_config['prompt_llm']['before_prompt'])
            self.ui.lineEdit_prompt_llm_after_prompt.setText(self.sd_config['prompt_llm']['after_prompt'])
            self.ui.lineEdit_sd_ip.setText(self.sd_config['ip'])
            self.ui.lineEdit_sd_port.setText(str(self.sd_config['port']))
            self.ui.lineEdit_sd_negative_prompt.setText(self.sd_config['negative_prompt'])
            self.ui.lineEdit_sd_seed.setText(str(self.sd_config['seed']))
            tmp_str = ""
            for tmp in self.sd_config['styles']:
                tmp_str = tmp_str + tmp + "\n"
            self.ui.textEdit_sd_styles.setText(tmp_str)
            self.ui.lineEdit_sd_cfg_scale.setText(str(self.sd_config['cfg_scale']))
            self.ui.lineEdit_sd_steps.setText(str(self.sd_config['steps']))
            self.ui.lineEdit_sd_hr_resize_x.setText(str(self.sd_config['hr_resize_x']))
            self.ui.lineEdit_sd_hr_resize_y.setText(str(self.sd_config['hr_resize_y']))
            if self.sd_config['enable_hr']:
                self.ui.checkBox_sd_enable_hr.setChecked(True)
            self.ui.lineEdit_sd_hr_scale.setText(str(self.sd_config['hr_scale']))
            self.ui.lineEdit_sd_hr_second_pass_steps.setText(str(self.sd_config['hr_second_pass_steps']))
            self.ui.lineEdit_sd_denoising_strength.setText(str(self.sd_config['denoising_strength']))
            
            # 聊天
            self.ui.lineEdit_talk_username.setText(self.talk_config['username'])
            if self.talk_config['continuous_talk']:
                self.ui.checkBox_talk_continuous_talk.setChecked(True)
            self.ui.comboBox_talk_trigger_key.clear()
            with open('data\keyboard.txt', 'r') as file:
                file_content = file.read()
            # 按行分割内容，并去除每行末尾的换行符
            lines = file_content.strip().split('\n')
            # 存储到字符串数组中
            trigger_keys = [line for line in lines]
            # print(trigger_keys)
            self.ui.comboBox_talk_trigger_key.addItems(trigger_keys)
            trigger_key_index = trigger_keys.index(self.talk_config['trigger_key'])
            self.ui.comboBox_talk_trigger_key.setCurrentIndex(trigger_key_index)
            self.ui.comboBox_talk_stop_trigger_key.clear()
            self.ui.comboBox_talk_stop_trigger_key.addItems(trigger_keys)
            stop_trigger_key_index = trigger_keys.index(self.talk_config['stop_trigger_key'])
            self.ui.comboBox_talk_stop_trigger_key.setCurrentIndex(stop_trigger_key_index)
            self.ui.comboBox_talk_type.clear()
            self.ui.comboBox_talk_type.addItems(["baidu", "google"])
            talk_type_index = 0
            if self.talk_config['type'] == "baidu":
                talk_type_index = 0
            elif self.talk_config['type'] == "google":
                talk_type_index = 1
            self.ui.comboBox_talk_type.setCurrentIndex(talk_type_index)
            self.ui.lineEdit_talk_volume_threshold.setText(str(self.talk_config['volume_threshold']))
            self.ui.lineEdit_talk_silence_threshold.setText(str(self.talk_config['silence_threshold']))
            self.ui.lineEdit_talk_baidu_app_id.setText(self.talk_config['baidu']['app_id'])
            self.ui.lineEdit_talk_baidu_api_key.setText(self.talk_config['baidu']['api_key'])
            self.ui.lineEdit_talk_baidu_secret_key.setText(self.talk_config['baidu']['secret_key'])
            self.ui.comboBox_talk_google_tgt_lang.clear()
            self.ui.comboBox_talk_google_tgt_lang.addItems(["zh-CN", "en-US", "ja-JP"])
            talk_google_tgt_lang_index = 0
            if self.talk_config['google']['tgt_lang'] == "zh-CN":
                talk_google_tgt_lang_index = 0
            elif self.talk_config['google']['tgt_lang'] == "en-US":
                talk_google_tgt_lang_index = 1
            elif self.talk_config['google']['tgt_lang'] == "ja-JP":
                talk_google_tgt_lang_index = 2 
            self.ui.comboBox_talk_google_tgt_lang.setCurrentIndex(talk_google_tgt_lang_index)

            # 连接回车按键的信号与槽
            self.ui.textEdit_talk_chat_box.installEventFilter(self)
            
            """
            GUI部分 动态生成的widget
            推荐使用这种形式进行UI加载，更具动态，不过目前封装实现还是垃圾了些，不是很好用，待优化
            """
            # 自定义显隐各板块
            def get_box_name_by_key(key):
                # 定义键和值的映射关系，请和配置文件中的键保持一致
                # 添加时需要同步给配置文件中的show_box配置项追加你添加的键名
                key_value_map = {
                    "read_comment": "念弹幕",
                    "read_user_name": "念用户名",
                    "filter": "过滤",
                    "thanks": "答谢",
                    "live2d": "Live2D",
                    "audio_random_speed": "音频随机变速",
                    "so_vits_svc": "so-vits-svc",
                    "ddsp_svc": "DDSP-SVC",
                    "local_qa": "本地问答",
                    "choose_song": "点歌模式",
                    "sd": "Stable Diffusion",
                    "log": "日志",
                    "schedule": "定时任务",
                    "idle_time_task": "闲时任务",
                    "database": "数据库",
                    "play_audio": "播放音频",
                    "web_captions_printer": "web字幕打印机",
                    "key_mapping": "按键映射",
                    "unity": "Unity",
                    # 可以继续添加其他键和值
                }

                # 查找并返回对应的值，如果找不到键则返回None
                return key_value_map.get(key)

            data_json = []
            # 遍历字典并获取键名和对应值
            for index, (key, value) in enumerate(config.get("show_box").items()):
                tmp_json = {
                    "label_text": "",
                    "label_tip": "",
                    "data": value,
                    "widget_text": get_box_name_by_key(key),
                    "click_func": "show_box",
                    "main_obj_name": key,
                    "index": index
                }
                data_json.append(tmp_json)

            widgets = self.create_widgets_from_json(data_json)

            # 动态添加widget到对应的gridLayout
            row, col, max_col = 0, 0, 3
            for widget in widgets:
                self.ui.gridLayout_show_box.addWidget(widget, row, col)
                col += 1
                if col > max_col:
                    col = 0
                    row += 1


            # 定时任务动态加载
            data_json = []
            for index, tmp in enumerate(config.get("schedule")):
                tmp_json = {
                    "label_text": "任务" + str(index),
                    "label_tip": "是否启用此定时任务",
                    "data": tmp["enable"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "schedule",
                    "index": index
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "循环周期",
                    "label_tip": "定时任务循环的周期时长（秒），即每间隔这个周期就会执行一次",
                    "data": tmp["time"],
                    "main_obj_name": "schedule",
                    "index": index
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "文案列表",
                    "label_tip": "存放文案的列表，通过空格或换行分割，通过{变量}来替换关键数据，可修改源码自定义功能",
                    "data": tmp["copy"],
                    "main_obj_name": "schedule",
                    "index": index
                }
                data_json.append(tmp_json)
            widgets = self.create_widgets_from_json(data_json)

            # 动态添加widget到对应的gridLayout
            row = 0
            for i in range(0, len(widgets), 2):
                self.ui.gridLayout_schedule.addWidget(widgets[i], row, 0)
                self.ui.gridLayout_schedule.addWidget(widgets[i + 1], row, 1)
                row += 1

            # 闲时任务动态加载
            def idle_time_task_gui_create():
                data_json = []
                idle_time_task_config = config.get("idle_time_task")

                tmp_json = {
                    "label_text": "闲时任务",
                    "label_tip": "是否启用闲时任务",
                    "data": idle_time_task_config["enable"],
                    "widget_text": "启用",
                    "click_func": "",
                    "main_obj_name": "idle_time_task",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "闲时时间",
                    "label_tip": "闲时间隔时间（正整数），就是在没有弹幕情况下经过的时间",
                    "data": idle_time_task_config["idle_time"],
                    "main_obj_name": "zhipu",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "随机闲时时间",
                    "label_tip": "是否启用随机闲时时间，从0到闲时时间随机一个数",
                    "data": idle_time_task_config["random_time"],
                    "widget_text": "启用",
                    "click_func": "",
                    "main_obj_name": "idle_time_task",
                    "index": 2
                }
                data_json.append(tmp_json)

                # logging.info(data_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_idle_time_task.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_idle_time_task.addWidget(widgets[i + 1], row, 1)
                    row += 1

            idle_time_task_gui_create()

            def idle_time_task_comment_gui_create():
                data_json = []
                idle_time_task_config = config.get("idle_time_task")

                tmp_json = {
                    "label_text": "LLM模式",
                    "label_tip": "是否启用LLM模式",
                    "data": idle_time_task_config["comment"]["enable"],
                    "widget_text": "启用",
                    "click_func": "",
                    "main_obj_name": "idle_time_task",
                    "index": 3
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "随机文案",
                    "label_tip": "是否启用随机文案，打乱文案触发顺序",
                    "data": idle_time_task_config["comment"]["random"],
                    "widget_text": "启用",
                    "click_func": "",
                    "main_obj_name": "idle_time_task",
                    "index": 4
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "文案列表",
                    "label_tip": "文案列表，文案之间用换行分隔，文案会丢LLM进行处理后直接合成返回的结果",
                    "data": idle_time_task_config["comment"]["copy"],
                    "main_obj_name": "idle_time_task",
                    "index": 5
                }
                data_json.append(tmp_json)

                # logging.info(data_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_idle_time_task_comment.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_idle_time_task_comment.addWidget(widgets[i + 1], row, 1)
                    row += 1

            idle_time_task_comment_gui_create()

            def idle_time_task_local_audio_gui_create():
                data_json = []
                idle_time_task_config = config.get("idle_time_task")

                tmp_json = {
                    "label_text": "本地音频模式",
                    "label_tip": "是否启用本地音频模式",
                    "data": idle_time_task_config["local_audio"]["enable"],
                    "widget_text": "启用",
                    "click_func": "",
                    "main_obj_name": "idle_time_task",
                    "index": 6
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "随机本地音频",
                    "label_tip": "是否启用随机本地音频，打乱本地音频触发顺序",
                    "data": idle_time_task_config["local_audio"]["random"],
                    "widget_text": "启用",
                    "click_func": "",
                    "main_obj_name": "idle_time_task",
                    "index": 7
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "本地音频路径列表",
                    "label_tip": "本地音频路径列表，相对/绝对路径之间用换行分隔，音频文件会直接丢进音频播放队列",
                    "data": idle_time_task_config["local_audio"]["path"],
                    "main_obj_name": "idle_time_task",
                    "index": 8
                }
                data_json.append(tmp_json)

                # logging.info(data_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_idle_time_task_local_audio.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_idle_time_task_local_audio.addWidget(widgets[i + 1], row, 1)
                    row += 1

            idle_time_task_local_audio_gui_create()

            # 文案配置动态加载
            self.ui.lineEdit_copywriting_audio_interval.setText(str(self.copywriting_config['audio_interval']))
            self.ui.lineEdit_copywriting_switching_interval.setText(str(self.copywriting_config['switching_interval']))
            if self.copywriting_config['auto_play']:
                self.ui.checkBox_copywriting_switching_auto_play.setChecked(True)
            if self.copywriting_config['random_play']:
                self.ui.checkBox_copywriting_switching_random_play.setChecked(True)

            data_json = []
            for index, tmp in enumerate(config.get("copywriting", "config")):
                tmp_json = {
                    "label_text": "文案存储路径" + str(index),
                    "label_tip": "文案文件存储路径，默认不可编辑。不建议更改。",
                    "data": tmp["file_path"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_file_path",
                    "index": index
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "音频存储路径" + str(index),
                    "label_tip": "文案音频文件存储路径，默认不可编辑。不建议更改。",
                    "data": tmp["audio_path"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_audio_path",
                    "index": index
                }
                data_json.append(tmp_json)

                tmp_str = ""
                copywriting_file_names = self.get_dir_txt_filename(self.copywriting_config["config"][index]['file_path'])
                for tmp_copywriting_file_name in copywriting_file_names:
                    tmp_str = tmp_str + tmp_copywriting_file_name + "\n"
                tmp_json = {
                    "label_text": "文案列表" + str(index),
                    "label_tip": "加载配置文件中配置的文案路径下的所有文件，请勿放入其他非文案文件",
                    "data": [tmp_str],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_copywriting_list",
                    "readonly": True,
                    "index": index
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "播放列表" + str(index),
                    "label_tip": "此处填写需要播放的音频文件全名，填写完毕后点击 保存配置。文件全名从音频列表中复制，换行分隔，请勿随意填写",
                    "data": tmp["play_list"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_play_list",
                    "index": index
                }
                data_json.append(tmp_json)

                tmp_str = ""
                copywriting_audio_file_names = self.get_dir_audio_filename(self.copywriting_config["config"][index]['audio_path'])
                for tmp_copywriting_audio_file_name in copywriting_audio_file_names:
                    tmp_str = tmp_str + tmp_copywriting_audio_file_name + "\n"
                tmp_json = {
                    "label_text": "已合成\n音频列表" + str(index),
                    "label_tip": "加载配置文件中配置的音频路径下的所有文件，请勿放入其他非音频文件",
                    "data": [tmp_str],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_audio_list",
                    "readonly": True,
                    "index": index
                }
                data_json.append(tmp_json)
                
                tmp_json = {
                    "label_text": "连续播放数" + str(index),
                    "label_tip": "文案播放列表中连续播放的音频文件个数，如果超过了这个个数就会切换下一个文案列表",
                    "data": tmp["continuous_play_num"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_continuous_play_num",
                    "index": index
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "连续播放时间" + str(index),
                    "label_tip": "文案播放列表中连续播放音频的时长，如果超过了这个时长就会切换下一个文案列表",
                    "data": tmp["max_play_time"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_max_play_time",
                    "index": index
                }
                data_json.append(tmp_json)
            widgets = self.create_widgets_from_json(data_json)

            # 动态添加widget到对应的gridLayout
            row = 0
            for i in range(0, len(widgets), 2):
                self.ui.gridLayout_copywriting_config.addWidget(widgets[i], row, 0)
                self.ui.gridLayout_copywriting_config.addWidget(widgets[i + 1], row, 1)
                row += 1

            # 智谱AI
            def zhipu_gui_create():
                data_json = []
                zhipu_config = config.get("zhipu")

                tmp_json = {
                    "label_text": "api key",
                    "label_tip": "具体参考官方文档，申请地址：https://open.bigmodel.cn/usercenter/apikeys",
                    "data": zhipu_config["api_key"],
                    "main_obj_name": "zhipu",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "模型",
                    "label_tip": "使用的语言模型",
                    "widget_type": "combo_box",
                    "combo_data_list": ['chatglm_pro', 'chatglm_std', 'chatglm_lite', 'chatglm_lite_32k', 'characterglm'],
                    "data": zhipu_config["model"],
                    "main_obj_name": "zhipu",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "top_p",
                    "label_tip": "用温度取样的另一种方法，称为核取样\n取值范围是：(0.0,1.0)；开区间，不能等于 0 或 1，默认值为 0.7\n模型考虑具有 top_p 概率质量的令牌的结果。所以 0.1 意味着模型解码器只考虑从前 10% 的概率的候选集中取tokens\n建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数",
                    "data": zhipu_config["top_p"],
                    "main_obj_name": "zhipu",
                    "index": 2
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "temperature",
                    "label_tip": "采样温度，控制输出的随机性，必须为正数\n取值范围是：(0.0,1.0]，不能等于 0,默认值为 0.95\n值越大，会使输出更随机，更具创造性；值越小，输出会更加稳定或确定\n建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数",
                    "data": zhipu_config["temperature"],
                    "main_obj_name": "zhipu",
                    "index": 3
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "上下文记忆",
                    "label_tip": "是否开启上下文记忆功能，可以记住前面说的内容",
                    "data": zhipu_config["history_enable"],
                    "widget_text": "启用",
                    "click_func": "",
                    "main_obj_name": "zhipu",
                    "index": 4
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "最大记忆长度",
                    "label_tip": "最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米",
                    "data": zhipu_config["history_max_len"],
                    "main_obj_name": "zhipu",
                    "index": 5
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "用户信息",
                    "label_tip": "用户信息，当使用characterglm时需要配置",
                    "data": zhipu_config["user_info"],
                    "main_obj_name": "zhipu",
                    "index": 6
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "角色信息",
                    "label_tip": "角色信息，当使用characterglm时需要配置",
                    "data": zhipu_config["bot_info"],
                    "main_obj_name": "zhipu",
                    "index": 7
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "角色名称",
                    "label_tip": "角色名称，当使用characterglm时需要配置",
                    "data": zhipu_config["bot_name"],
                    "main_obj_name": "zhipu",
                    "index": 8
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "用户名称",
                    "label_tip": "用户名称，默认值为用户，当使用characterglm时需要配置",
                    "data": zhipu_config["user_name"],
                    "main_obj_name": "zhipu",
                    "index": 9
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "删除无用符号",
                    "label_tip": "是否开启删除无用符号功能，因为模型会有心理描述和啥特殊字符的内容，不需要的可以开启",
                    "data": zhipu_config["remove_useless"],
                    "widget_text": "启用",
                    "click_func": "",
                    "main_obj_name": "zhipu",
                    "index": 10
                }
                data_json.append(tmp_json)

                # logging.info(data_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_zhipu.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_zhipu.addWidget(widgets[i + 1], row, 1)
                    row += 1

            zhipu_gui_create()

            # VITS
            def vits_gui_create():
                data_json = []

                vits_config = config.get("vits")
                tmp_json = {
                    "label_text": "类型",
                    "label_tip": "选用的TTS模型",
                    "widget_type": "combo_box",
                    "combo_data_list": ["vits", "bert_vits2"],
                    "data": vits_config["type"],
                    "main_obj_name": "vits",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "配置文件路径",
                    "label_tip": "模型配置文件存储路径",
                    "data": vits_config["config_path"],
                    "main_obj_name": "vits",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "API地址",
                    "label_tip": "vits-simple-api启动后监听的ip端口地址",
                    "data": vits_config["api_ip_port"],
                    "main_obj_name": "vits",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "说话人ID",
                    "label_tip": "API启动时会给配置文件重新划分id，一般为拼音顺序排列，从0开始",
                    "data": vits_config["id"],
                    "main_obj_name": "vits",
                    "index": 2
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "语言",
                    "label_tip": "auto为自动识别语言模式，也是默认模式。lang=mix时，文本应该用[ZH] 或 [JA] 包裹。方言无法自动识别。",
                    "widget_type": "combo_box",
                    "combo_data_list": ["自动", "中文", "英文", "日文"],
                    "data": vits_config["lang"],
                    "main_obj_name": "vits",
                    "index": 4
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "语音长度",
                    "label_tip": "调节语音长度，相当于调节语速，该数值越大语速越慢",
                    "data": vits_config["length"],
                    "main_obj_name": "vits",
                    "index": 5
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "噪声",
                    "label_tip": "控制感情变化程度",
                    "data": vits_config["noise"],
                    "main_obj_name": "vits",
                    "index": 6
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "噪声偏差",
                    "label_tip": "控制音素发音长度",
                    "data": vits_config["noisew"],
                    "main_obj_name": "vits",
                    "index": 7
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "分段阈值",
                    "label_tip": "按标点符号分段，加起来大于max时为一段文本。max<=0表示不分段。",
                    "data": vits_config["max"],
                    "main_obj_name": "vits",
                    "index": 8
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "音频格式",
                    "label_tip": "支持wav,ogg,silk,mp3,flac",
                    "data": vits_config["format"],
                    "main_obj_name": "vits",
                    "index": 9
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "SDP/DP混合比",
                    "label_tip": "SDP/DP混合比：SDP在合成时的占比，理论上此比率越高，合成的语音语调方差越大。",
                    "data": vits_config["sdp_radio"],
                    "main_obj_name": "vits",
                    "index": 10
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_vits.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_vits.addWidget(widgets[i + 1], row, 1)
                    row += 1

            vits_gui_create()

            # 数据库
            def database_gui_create():
                data_json = []

                database_config = config.get("database")
                tmp_json = {
                    "label_text": "数据库路径",
                    "label_tip": "数据库文件存储路径",
                    "data": database_config["path"],
                    "main_obj_name": "database",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "弹幕日志",
                    "label_tip": "存储记录原始的用户弹幕数据，用于后期排查问题、分析用户画像等",
                    "data": database_config["comment_enable"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "database",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "入场日志",
                    "label_tip": "存储记录原始的用户入场数据，用于后期排查问题、分析流量等",
                    "data": database_config["entrance_enable"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "database",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "礼物日志",
                    "label_tip": "存储记录原始的用户礼物数据，用于后期排查问题、分析富哥富婆等",
                    "data": database_config["gift_enable"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "database",
                    "index": 1
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_database.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_database.addWidget(widgets[i + 1], row, 1)
                    row += 1

            database_gui_create()

            # 播放音频
            def play_audio_gui_create():
                data_json = []

                play_audio_config = config.get("play_audio")
                tmp_json = {
                    "label_text": "启用",
                    "label_tip": "是否开启音频播放，如果不启用，则会只合成音频文件，不会进行播放操作",
                    "data": play_audio_config["enable"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "play_audio",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "音频输出路径",
                    "label_tip": "音频文件合成后存储的路径，支持相对路径或绝对路径",
                    "data": play_audio_config["out_path"],
                    "main_obj_name": "play_audio",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "播放器",
                    "label_tip": "选择不同播放器播放音频，播放器不同，处理逻辑也有所不同",
                    "widget_type": "combo_box",
                    "combo_data_list": ['pygame', 'audio_player'],
                    "data": play_audio_config["player"],
                    "main_obj_name": "play_audio",
                    "index": 2
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_play_audio.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_play_audio.addWidget(widgets[i + 1], row, 1)
                    row += 1

            play_audio_gui_create()

            # audio_player
            def audio_player_gui_create():
                data_json = []

                audio_player_config = config.get("audio_player")
                tmp_json = {
                    "label_text": "API地址",
                    "label_tip": "audio_player的API地址，只需要 http://ip:端口 即可",
                    "data": audio_player_config["api_ip_port"],
                    "main_obj_name": "audio_player",
                    "index": 0
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_audio_player.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_audio_player.addWidget(widgets[i + 1], row, 1)
                    row += 1

            audio_player_gui_create()

            # 动态文案
            self.ui.checkBox_trends_copywriting_enable.setChecked(config.get("trends_copywriting", "enable"))
            self.ui.checkBox_trends_copywriting_random_play.setChecked(config.get("trends_copywriting", "random_play"))
            self.ui.lineEdit_trends_copywriting_play_interval.setText(str(config.get("trends_copywriting", "play_interval")))
            def trends_copywriting_gui_create():
                data_json = []

                trends_copywriting_config = config.get("trends_copywriting", "copywriting")
                for tmp in trends_copywriting_config:
                    tmp_json = {
                        "label_text": "文案路径",
                        "label_tip": "文案文件存储的文件夹路径",
                        "data": tmp["folder_path"],
                        "main_obj_name": "trends_copywriting",
                        "index": 0
                    }
                    data_json.append(tmp_json)

                    tmp_json = {
                        "label_text": "提示词转换",
                        "label_tip": "是否启用提示词对文案内容进行转换",
                        "data": tmp["prompt_change_enable"],
                        "widget_text": "",
                        "click_func": "",
                        "main_obj_name": "trends_copywriting",
                        "index": 0
                    }
                    data_json.append(tmp_json)

                    tmp_json = {
                        "label_text": "提示词转换内容",
                        "label_tip": "使用此提示词内容对文案内容进行转换后再进行合成，使用的LLM为聊天类型配置",
                        "data": tmp["prompt_change_content"],
                        "main_obj_name": "trends_copywriting",
                        "index": 0
                    }
                    data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_trends_copywriting_2.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_trends_copywriting_2.addWidget(widgets[i + 1], row, 1)
                    row += 1

            trends_copywriting_gui_create()

            # web字幕打印机
            def web_captions_printer_gui_create():
                data_json = []

                web_captions_printer_config = config.get("web_captions_printer")
                tmp_json = {
                    "label_text": "启用",
                    "label_tip": "是否启用web字幕打印机功能（需要先启动web字幕打印机程序才能使用）",
                    "data": web_captions_printer_config["enable"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "web_captions_printer",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "API地址",
                    "label_tip": "web字幕打印机的API地址，只需要 http://ip:端口 即可",
                    "data": web_captions_printer_config["api_ip_port"],
                    "main_obj_name": "web_captions_printer",
                    "index": 1
                }
                data_json.append(tmp_json)

                # tmp_json = {
                #     "label_text": "类型",
                #     "label_tip": "发送给web字幕打印机内容，可以自定义哪些内容发过去显示",
                #     "widget_type": "combo_box",
                #     "combo_data_list": ["弹幕", "回复", "复读", "弹幕+回复", "回复+复读", "弹幕+回复+复读"],
                #     "data": web_captions_printer_config["type"],
                #     "main_obj_name": "web_captions_printer",
                #     "index": 1
                # }
                # data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_web_captions_printer.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_web_captions_printer.addWidget(widgets[i + 1], row, 1)
                    row += 1

            web_captions_printer_gui_create()

            # VALL-E-X
            def vall_e_x_gui_create():
                data_json = []
                vall_e_x_config = config.get("vall_e_x")

                tmp_json = {
                    "label_text": "API地址",
                    "label_tip": "VALL-E-X启动后监听的ip端口地址",
                    "data": vall_e_x_config["api_ip_port"],
                    "main_obj_name": "vall_e_x",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "language",
                    "label_tip": "VALL-E-X language",
                    "widget_type": "combo_box",
                    "combo_data_list": ['auto-detect', 'English', '中文', '日本語', 'Mix'],
                    "data": vall_e_x_config["language"],
                    "main_obj_name": "vall_e_x",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "accent",
                    "label_tip": "VALL-E-X accent",
                    "widget_type": "combo_box",
                    "combo_data_list": ['no-accent', 'English', '中文', '日本語'],
                    "data": vall_e_x_config["accent"],
                    "main_obj_name": "vall_e_x",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "voice preset",
                    "label_tip": "VALL-E-X说话人预设名（Prompt name）",
                    "data": vall_e_x_config["voice_preset"],
                    "main_obj_name": "vall_e_x",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "voice_preset_file_path",
                    "label_tip": "VALL-E-X说话人预设文件路径（npz）",
                    "data": vall_e_x_config["voice_preset_file_path"],
                    "main_obj_name": "vall_e_x",
                    "index": 1
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_vall_e_x.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_vall_e_x.addWidget(widgets[i + 1], row, 1)
                    row += 1

            vall_e_x_gui_create()

            # OpenAI TTS
            def openai_tts_gui_create():
                data_json = []
                openai_tts_config = config.get("openai_tts")

                tmp_json = {
                    "label_text": "type",
                    "label_tip": "类型",
                    "widget_type": "combo_box",
                    "combo_data_list": ['api', 'huggingface'],
                    "data": openai_tts_config["type"],
                    "main_obj_name": "openai_tts",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "API地址",
                    "label_tip": "huggingface适配项目的API地址",
                    "data": openai_tts_config["api_ip_port"],
                    "main_obj_name": "openai_tts",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "模型",
                    "label_tip": "使用的模型",
                    "widget_type": "combo_box",
                    "combo_data_list": ['tts-1', 'tts-1-hd'],
                    "data": openai_tts_config["model"],
                    "main_obj_name": "openai_tts",
                    "index": 2
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "voice",
                    "label_tip": "说话人",
                    "widget_type": "combo_box",
                    "combo_data_list": ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
                    "data": openai_tts_config["voice"],
                    "main_obj_name": "openai_tts",
                    "index": 3
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "API Key",
                    "label_tip": "OpenAI API Key",
                    "data": openai_tts_config["api_key"],
                    "main_obj_name": "openai_tts",
                    "index": 4
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_openai_tts.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_openai_tts.addWidget(widgets[i + 1], row, 1)
                    row += 1

            openai_tts_gui_create()

            # 哔哩哔哩
            def bilibili_gui_create():
                data_json = []
                bilibili_config = config.get("bilibili")

                tmp_json = {
                    "label_text": "登录方式",
                    "label_tip": "选择登录b站账号的方式，用于获取b站账号相关信息",
                    "widget_type": "combo_box",
                    "combo_data_list": ['手机扫码', '手机扫码-终端', 'cookie', '账号密码登录', 'open_live', '不登录'],
                    "data": bilibili_config["login_type"],
                    "main_obj_name": "bilibili",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "cookie",
                    "label_tip": "b站登录后F12抓网络包获取cookie，强烈建议使用小号！有封号风险",
                    "data": bilibili_config["cookie"],
                    "main_obj_name": "bilibili",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "ac_time_value",
                    "label_tip": "b站登录后，F12控制台，输入window.localStorage.ac_time_value获取(如果没有，请重新登录)",
                    "data": bilibili_config["ac_time_value"],
                    "main_obj_name": "bilibili",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "用户名",
                    "label_tip": "b站账号（建议使用小号）",
                    "data": bilibili_config["username"],
                    "main_obj_name": "bilibili",
                    "index": 2
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "密码",
                    "label_tip": "b站密码（建议使用小号）",
                    "data": bilibili_config["password"],
                    "main_obj_name": "bilibili",
                    "index": 3
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_bilibili.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_bilibili.addWidget(widgets[i + 1], row, 1)
                    row += 1

            bilibili_gui_create()

            # twitch
            def twitch_gui_create():
                data_json = []
                twitch_config = config.get("twitch")

                tmp_json = {
                    "label_text": "token",
                    "label_tip": "访问 https://twitchapps.com/tmi/ 获取，格式为：oauth:xxx",
                    "data": twitch_config["token"],
                    "main_obj_name": "twitch",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "用户名",
                    "label_tip": "你的twitch账号用户名",
                    "data": twitch_config["user"],
                    "main_obj_name": "twitch",
                    "index": 2
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "HTTP代理IP地址",
                    "label_tip": "代理软件，http协议监听的ip地址，一般为：127.0.0.1",
                    "data": twitch_config["proxy_server"],
                    "main_obj_name": "twitch",
                    "index": 3
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "HTTP代理端口",
                    "label_tip": "代理软件，http协议监听的端口，一般为：1080",
                    "data": twitch_config["proxy_port"],
                    "main_obj_name": "twitch",
                    "index": 4
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_twitch.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_twitch.addWidget(widgets[i + 1], row, 1)
                    row += 1

            twitch_gui_create()

            # bard
            def bard_gui_create():
                data_json = []
                bard_config = config.get("bard")

                tmp_json = {
                    "label_text": "token",
                    "label_tip": "登录bard，打开F12，在cookie中获取 __Secure-1PSID 对应的值",
                    "data": bard_config["token"],
                    "main_obj_name": "bard",
                    "index": 1
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_bard.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_bard.addWidget(widgets[i + 1], row, 1)
                    row += 1

            bard_gui_create()

            # 文心一言
            def yiyan_gui_create():
                data_json = []
                yiyan_config = config.get("yiyan")

                tmp_json = {
                    "label_text": "API地址",
                    "label_tip": "yiyan-api启动后监听的ip端口地址",
                    "data": yiyan_config["api_ip_port"],
                    "main_obj_name": "yiyan",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "类型",
                    "label_tip": "使用的接口类型，暂时只提供web版",
                    "widget_type": "combo_box",
                    "combo_data_list": ['web'],
                    "data": yiyan_config["type"],
                    "main_obj_name": "yiyan",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "cookie",
                    "label_tip": "文心一言登录后，跳过debug后，抓取请求包中的cookie",
                    "data": yiyan_config["cookie"],
                    "main_obj_name": "yiyan",
                    "index": 2
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_yiyan.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_yiyan.addWidget(widgets[i + 1], row, 1)
                    row += 1

            yiyan_gui_create()

            # 通义千问
            def tongyi_gui_create():
                data_json = []
                tongyi_config = config.get("tongyi")

                tmp_json = {
                    "label_text": "类型",
                    "label_tip": "使用的接口类型，暂时只提供web版",
                    "widget_type": "combo_box",
                    "combo_data_list": ['web'],
                    "data": tongyi_config["type"],
                    "main_obj_name": "tongyi",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "cookie路径",
                    "label_tip": "通义千问登录后，通过浏览器插件Cookie Editor获取Cookie JSON串，然后将数据保存在这个路径的文件中",
                    "data": tongyi_config["cookie_path"],
                    "main_obj_name": "tongyi",
                    "index": 1
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_tongyi.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_tongyi.addWidget(widgets[i + 1], row, 1)
                    row += 1

            tongyi_gui_create()

            # 念弹幕
            def read_comment_create():
                data_json = []
                read_comment_config = config.get("read_comment")

                tmp_json = {
                    "label_text": "念弹幕",
                    "label_tip": "是否启用念弹幕的功能",
                    "data": read_comment_config["enable"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "read_comment",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "念用户名",
                    "label_tip": "是否启用念用户名的功能，就是说在念弹幕的前面顺便把用户名念一下",
                    "data": read_comment_config["read_username_enable"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "read_comment",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "变声",
                    "label_tip": "是否启用变声功能，会使用已配置的变声内容来进行变声",
                    "data": read_comment_config["voice_change"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "read_comment",
                    "index": 2
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "念用户名文案",
                    "label_tip": "念用户名时使用的文案，可以自定义编辑多个（换行分隔），实际中会随机一个使用",
                    "data": read_comment_config["read_username_copywriting"],
                    "main_obj_name": "read_comment",
                    "index": 3
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_read_comment.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_read_comment.addWidget(widgets[i + 1], row, 1)
                    row += 1

            read_comment_create()

            # 按键映射
            self.ui.checkBox_key_mapping_enable.setChecked(config.get("key_mapping", "enable"))
            self.ui.comboBox_key_mapping_type.clear()
            self.ui.comboBox_key_mapping_type.addItems(["弹幕", "回复", "弹幕+回复"])
            key_mapping_type_index = 0
            if config.get('key_mapping', 'type') == "弹幕":
                key_mapping_type_index = 0
            elif config.get('key_mapping', 'type') == "回复":
                key_mapping_type_index = 1
            elif config.get('key_mapping', 'type') == "弹幕+回复":
                key_mapping_type_index = 2 
            self.ui.comboBox_key_mapping_type.setCurrentIndex(key_mapping_type_index)
            self.ui.lineEdit_key_mapping_start_cmd.setText(config.get("key_mapping", "start_cmd"))

            def key_mapping_config_create():
                data_json = []
                for index, tmp in enumerate(config.get("key_mapping", "config")):
                    tmp_json = {
                        "label_text": "关键词#" + str(index),
                        "label_tip": "触发按键映射的关键词，可以配置多个，用换行进行分隔",
                        "data": tmp["keywords"],
                        "main_obj_name": "key_mapping_config",
                        "index": 3 * index
                    }
                    data_json.append(tmp_json)

                    tmp_json = {
                        "label_text": "按键#" + str(index),
                        "label_tip": "触发按键映射的对应的按键（参考pyautogui文档配置），可以配置多个，用换行进行分隔",
                        "data": tmp["keys"],
                        "main_obj_name": "key_mapping_config",
                        "index": 3 * index + 1
                    }
                    data_json.append(tmp_json)

                    tmp_json = {
                        "label_text": "相似度#" + str(index),
                        "label_tip": "关键词命中的相似度，默认1为100%命中后才会触发",
                        "data": tmp["similarity"],
                        "main_obj_name": "key_mapping_config",
                        "index": 3 * index + 2
                    }
                    data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_key_mapping_config.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_key_mapping_config.addWidget(widgets[i + 1], row, 1)
                    row += 1

            key_mapping_config_create()

            """
            积分页
            """
            self.ui.checkBox_integral_common_enable.setChecked(config.get("integral", "enable"))

            # 入场-文案
            def integral_entrance_copywriting_create():
                data_json = []
                for index, tmp in enumerate(config.get("integral", "entrance", "copywriting")):
                    tmp_json = {
                        "label_text": "入场数区间" + str(index),
                        "label_tip": "限制在此区间内的入场数来触发对应的文案，用-号来进行区间划分，包含边界值",
                        "data": tmp["entrance_num_interval"],
                        "main_obj_name": "integral_entrance_copywriting_entrance_num_interval",
                        "index": index
                    }
                    data_json.append(tmp_json)

                    tmp_json = {
                        "label_text": "文案" + str(index),
                        "label_tip": "在此入场区间内，触发的文案内容，换行分隔",
                        "data": tmp["copywriting"],
                        "widget_text": "",
                        "click_func": "",
                        "main_obj_name": "integral_entrance_copywriting_copywriting",
                        "index": index
                    }
                    data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_integral_entrance_copywriting.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_integral_entrance_copywriting.addWidget(widgets[i + 1], row, 1)
                    row += 1

            integral_entrance_copywriting_create()

            # 入场
            def integral_entrance_create():
                data_json = []
                integral_entrance_config = config.get("integral", "entrance")

                tmp_json = {
                    "label_text": "启用入场",
                    "label_tip": "是否启用入场功能",
                    "data": integral_entrance_config["enable"],
                    "widget_text": "是",
                    "click_func": "",
                    "main_obj_name": "integral_entrance",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "获得积分数",
                    "label_tip": "入场可以获得的积分数，请填写正整数！",
                    "data": integral_entrance_config["get_integral"],
                    "main_obj_name": "integral_entrance",
                    "index": 1
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_integral_entrance.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_integral_entrance.addWidget(widgets[i + 1], row, 1)
                    row += 1

            integral_entrance_create()

            # 签到-文案
            def integral_sign_copywriting_create():
                data_json = []
                for index, tmp in enumerate(config.get("integral", "sign", "copywriting")):
                    tmp_json = {
                        "label_text": "签到数区间" + str(index),
                        "label_tip": "限制在此区间内的签到数来触发对应的文案，用-号来进行区间划分，包含边界值",
                        "data": tmp["sign_num_interval"],
                        "main_obj_name": "integral_sign_copywriting_sign_num_interval",
                        "index": index
                    }
                    data_json.append(tmp_json)

                    tmp_json = {
                        "label_text": "文案" + str(index),
                        "label_tip": "在此签到区间内，触发的文案内容，换行分隔",
                        "data": tmp["copywriting"],
                        "widget_text": "",
                        "click_func": "",
                        "main_obj_name": "integral_sign_copywriting_copywriting",
                        "index": index
                    }
                    data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_integral_sign_copywriting.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_integral_sign_copywriting.addWidget(widgets[i + 1], row, 1)
                    row += 1

            integral_sign_copywriting_create()

            # 签到
            def integral_sign_create():
                data_json = []
                integral_sign_config = config.get("integral", "sign")

                tmp_json = {
                    "label_text": "启用签到",
                    "label_tip": "是否启用签到功能",
                    "data": integral_sign_config["enable"],
                    "widget_text": "是",
                    "click_func": "",
                    "main_obj_name": "integral_sign",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "签到命令",
                    "label_tip": "弹幕发送以下命令可以触发签到功能，换行分隔命令",
                    "data": integral_sign_config["cmd"],
                    "main_obj_name": "integral_sign",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "获得积分数",
                    "label_tip": "签到成功可以获得的积分数，请填写正整数！",
                    "data": integral_sign_config["get_integral"],
                    "main_obj_name": "integral_sign",
                    "index": 2
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_integral_sign.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_integral_sign.addWidget(widgets[i + 1], row, 1)
                    row += 1

            integral_sign_create()

            # 礼物-文案
            def integral_gift_copywriting_create():
                data_json = []
                for index, tmp in enumerate(config.get("integral", "gift", "copywriting")):
                    tmp_json = {
                        "label_text": "礼物价格区间" + str(index),
                        "label_tip": "限制在此区间内的礼物价格来触发对应的文案，用-号来进行区间划分，包含边界值",
                        "data": tmp["gift_price_interval"],
                        "main_obj_name": "integral_gift_copywriting_gift_price_interval",
                        "index": index
                    }
                    data_json.append(tmp_json)

                    tmp_json = {
                        "label_text": "文案" + str(index),
                        "label_tip": "在此礼物区间内，触发的文案内容，换行分隔",
                        "data": tmp["copywriting"],
                        "widget_text": "",
                        "click_func": "",
                        "main_obj_name": "integral_gift_copywriting_copywriting",
                        "index": index
                    }
                    data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_integral_gift_copywriting.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_integral_gift_copywriting.addWidget(widgets[i + 1], row, 1)
                    row += 1

            integral_gift_copywriting_create()

            # 礼物
            def integral_gift_create():
                data_json = []
                integral_gift_config = config.get("integral", "gift")

                tmp_json = {
                    "label_text": "启用礼物",
                    "label_tip": "是否启用礼物功能",
                    "data": integral_gift_config["enable"],
                    "widget_text": "是",
                    "click_func": "",
                    "main_obj_name": "integral_gift",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "获得积分比例",
                    "label_tip": "此比例和礼物真实金额（元）挂钩，默认就是1元=10积分",
                    "data": integral_gift_config["get_integral_proportion"],
                    "main_obj_name": "integral_gift",
                    "index": 2
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_integral_gift.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_integral_gift.addWidget(widgets[i + 1], row, 1)
                    row += 1

            integral_gift_create()

            # 增删改查
            # 查询
            def integral_crud_query_create():
                data_json = []
                integral_crud_query_config = config.get("integral", "crud", "query")

                tmp_json = {
                    "label_text": "启用查询",
                    "label_tip": "是否启用查询功能",
                    "data": integral_crud_query_config["enable"],
                    "widget_text": "是",
                    "click_func": "",
                    "main_obj_name": "integral_crud_query",
                    "index": 0
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "查询命令",
                    "label_tip": "弹幕发送以下命令可以触发查询功能，换行分隔命令",
                    "data": integral_crud_query_config["cmd"],
                    "main_obj_name": "integral_crud_query",
                    "index": 1
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "文案",
                    "label_tip": "触发查询功能后返回的文案内容，换行分隔命令",
                    "data": integral_crud_query_config["copywriting"],
                    "main_obj_name": "integral_crud_query",
                    "index": 2
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_integral_crud_query.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_integral_crud_query.addWidget(widgets[i + 1], row, 1)
                    row += 1

            integral_crud_query_create()

            # xuniren
            def xuniren_create():
                data_json = []

                xuniren_config = config.get("xuniren")
 
                tmp_json = {
                    "label_text": "API地址",
                    "label_tip": "xuniren应用启动API后，监听的ip和端口",
                    "data": xuniren_config["api_ip_port"],
                    "main_obj_name": "xuniren",
                    "index": 0
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_xuniren.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_xuniren.addWidget(widgets[i + 1], row, 1)
                    row += 1

            xuniren_create()
            
            # unity
            def unity_create():
                data_json = []

                unity_config = config.get("unity")

                # tmp_json = {
                #     "label_text": "Unity中转",
                #     "label_tip": "是否启用Unity中转功能",
                #     "data": unity_config["enable"],
                #     "widget_text": "启用",
                #     "click_func": "",
                #     "main_obj_name": "unity",
                #     "index": 0
                # }
                # data_json.append(tmp_json)
 
                tmp_json = {
                    "label_text": "API地址",
                    "label_tip": "对接Unity应用使用的HTTP中转站监听的ip和端口",
                    "data": unity_config["api_ip_port"],
                    "main_obj_name": "unity",
                    "index": 0
                }
                data_json.append(tmp_json)

                widgets = self.create_widgets_from_json(data_json)

                # 动态添加widget到对应的gridLayout
                row = 0
                # 分2列，左边就是label说明，右边就是输入框等
                for i in range(0, len(widgets), 2):
                    self.ui.gridLayout_unity.addWidget(widgets[i], row, 0)
                    self.ui.gridLayout_unity.addWidget(widgets[i + 1], row, 1)
                    row += 1

            unity_create()

            """
            ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
            -------------------------------------------------------------------------------------------------------------
            """

            # 显隐各板块
            self.oncomboBox_chat_type_IndexChanged(chat_type_index)
            self.oncomboBox_audio_synthesis_type_IndexChanged(audio_synthesis_type_index)
            self.oncomboBox_talk_type_IndexChanged(talk_type_index)

            # 打开Live2D页面
            # if self.live2d_config["enable"]:
            #     url = QUrl("http://127.0.0.1:12345/Live2D/")  # 指定要打开的网页地址
            #     QDesktopServices.openUrl(url)

            logging.info("配置文件加载成功。")
        except Exception as e:
            logging.error(traceback.format_exc())
            return None
    
    
    # ui初始化
    def init_ui(self):
        # 统一设置下样式先
        comboBox_common_css = '''
            margin: 5px 0px; 
            height: 40px;
            background-color: rgba(255, 255, 255, 100);
        '''

        # 无效设置
        font = QFont("仿宋", 14)  # 创建一个字体对象
        font.setWeight(QFont.Bold)  # 设置字体粗细

        comboBoxs = self.findChildren(QComboBox)
        for comboBox in comboBoxs:
            comboBox.setStyleSheet(comboBox_common_css)
            comboBox.setFont(font)

        label_common_css = '''
            background-color: rgba(255, 255, 255, 0);
        '''

        labels = self.findChildren(QLabel)
        for label in labels:
            label.setStyleSheet(label_common_css)
            label.setFont(font)
        
        
        groupBox_common_css = '''
            background-color: rgba(255, 255, 255, 0);
        '''

        groupBoxs = self.findChildren(QGroupBox)
        for groupBox in groupBoxs:
            groupBox.setStyleSheet(groupBox_common_css)
            groupBox.setFont(font)

        if False:
            # 统一设置下样式先
            common_css = "margin: 5px 0px; height: 40px;"

            # 无效设置
            font = QFont("微软雅黑", 14)  # 创建一个字体对象
            font.setWeight(QFont.Bold)  # 设置字体粗细

            labels = self.findChildren(QLabel)
            for label in labels:
                label.setStyleSheet(common_css)
                label.setFont(font)

        
            comboBoxs = self.findChildren(QComboBox)
            for comboBox in comboBoxs:
                comboBox.setStyleSheet(common_css)
                comboBox.setFont(font)

            lineEdits = self.findChildren(QLineEdit)
            for lineEdit in lineEdits:
                lineEdit.setStyleSheet(common_css)
                lineEdit.setFont(font)

            textEdits = self.findChildren(QTextEdit)
            for textEdit in textEdits:
                textEdit.setStyleSheet(common_css)
                textEdit.setFont(font)
        

        self.show()

        # 将按钮点击事件与自定义的功能函数进行连接
        self.ui.pushButton_save.disconnect()
        self.ui.pushButton_factory.disconnect()
        self.ui.pushButton_run.disconnect()
        self.ui.pushButton_config_page.disconnect()
        self.ui.pushButton_run_page.disconnect()
        self.ui.pushButton_copywriting_page.disconnect()
        self.ui.pushButton_talk_page.disconnect()
        self.ui.pushButton_integral_page.disconnect()
        self.ui.pushButton_save.clicked.connect(self.on_pushButton_save_clicked)
        self.ui.pushButton_factory.clicked.connect(self.on_pushButton_factory_clicked)
        self.ui.pushButton_run.clicked.connect(self.on_pushButton_run_clicked)
        self.ui.pushButton_config_page.clicked.connect(lambda: self.on_pushButton_change_page_clicked(0))
        self.ui.pushButton_run_page.clicked.connect(lambda: self.on_pushButton_change_page_clicked(1))
        self.ui.pushButton_copywriting_page.clicked.connect(lambda: self.on_pushButton_change_page_clicked(2))
        self.ui.pushButton_talk_page.clicked.connect(lambda: self.on_pushButton_change_page_clicked(3))
        self.ui.pushButton_integral_page.clicked.connect(lambda: self.on_pushButton_change_page_clicked(4))


        # 文案页
        self.ui.pushButton_copywriting_config_index_add.disconnect()
        self.ui.pushButton_copywriting_config_index_del.disconnect()
        self.ui.pushButton_copywriting_select.disconnect()
        self.ui.pushButton_copywriting_refresh_list.disconnect()
        self.ui.pushButton_copywriting_save.disconnect()
        self.ui.pushButton_copywriting_synthetic_audio.disconnect()
        self.ui.pushButton_copywriting_loop_play.disconnect()
        self.ui.pushButton_copywriting_pause_play.disconnect()
        self.ui.pushButton_copywriting_config_index_add.clicked.connect(self.on_pushButton_copywriting_config_index_add_clicked)
        self.ui.pushButton_copywriting_config_index_del.clicked.connect(self.on_pushButton_copywriting_config_index_del_clicked)
        self.ui.pushButton_copywriting_select.clicked.connect(self.on_pushButton_copywriting_select_clicked)
        self.ui.pushButton_copywriting_refresh_list.clicked.connect(self.on_pushButton_copywriting_refresh_list_clicked)
        self.ui.pushButton_copywriting_save.clicked.connect(self.on_pushButton_copywriting_save_clicked)
        self.ui.pushButton_copywriting_synthetic_audio.clicked.connect(self.on_pushButton_copywriting_synthetic_audio_clicked)
        self.ui.pushButton_copywriting_loop_play.clicked.connect(self.on_pushButton_copywriting_loop_play_clicked)
        self.ui.pushButton_copywriting_pause_play.clicked.connect(self.on_pushButton_copywriting_pause_play_clicked)

        # 聊天页
        self.ui.pushButton_talk_chat_box_send.disconnect()
        self.ui.pushButton_talk_chat_box_reread.disconnect()
        self.ui.pushButton_talk_chat_box_send.clicked.connect(self.on_pushButton_talk_chat_box_send_clicked)
        self.ui.pushButton_talk_chat_box_reread.clicked.connect(self.on_pushButton_talk_chat_box_reread_clicked)

        # 下拉框相关槽函数
        self.ui.comboBox_chat_type.disconnect()
        self.ui.comboBox_audio_synthesis_type.disconnect()
        self.ui.comboBox_talk_type.disconnect()
        self.ui.comboBox_chat_type.currentIndexChanged.connect(lambda index: self.oncomboBox_chat_type_IndexChanged(index))
        self.ui.comboBox_audio_synthesis_type.currentIndexChanged.connect(lambda index: self.oncomboBox_audio_synthesis_type_IndexChanged(index))
        self.ui.comboBox_talk_type.currentIndexChanged.connect(lambda index: self.oncomboBox_talk_type_IndexChanged(index))

        # 顶部餐单栏槽函数
        self.ui.action_official_store.triggered.connect(self.openBrowser_github)
        self.ui.action_video_tutorials.triggered.connect(self.openBrowser_video)
        self.ui.action_online_doc.triggered.connect(self.openBrowser_online_doc)
        self.ui.action_about.triggered.connect(self.alert_about)
        self.ui.action_exit.triggered.connect(self.exit_soft)
        self.ui.action_official_qq_group.triggered.connect(self.openBrowser_official_qq_group)

        # 创建节流函数，并将其保存为类的属性，delay秒内只执行一次
        self.throttled_save = self.throttle(self.save, 1)
        self.throttled_factory = self.throttle(self.factory, 1)
        self.throttled_run = self.throttle(self.run, 1)
        self.throttled_change_page = self.throttle(self.change_page, 0.5)
        self.throttled_copywriting_config_index_add = self.throttle(self.copywriting_config_index_add, 1)
        self.throttled_copywriting_config_index_del = self.throttle(self.copywriting_config_index_del, 1)
        self.throttled_copywriting_select = self.throttle(self.copywriting_select, 1)
        self.throttled_copywriting_refresh_list = self.throttle(self.copywriting_refresh_list, 1)
        self.throttled_copywriting_save = self.throttle(self.copywriting_save, 1)
        self.throttled_copywriting_synthetic_audio = self.throttle(self.copywriting_synthetic_audio, 1)
        self.throttled_copywriting_loop_play = self.throttle(self.copywriting_loop_play, 1)
        self.throttled_copywriting_pause_play = self.throttle(self.copywriting_pause_play, 1)
        self.throttled_talk_chat_box_send = self.throttle(self.talk_chat_box_send, 0.5)
        self.throttled_talk_chat_box_reread = self.throttle(self.talk_chat_box_reread, 0.5)



    '''
        按钮相关的函数
    '''
    # 保存喵(开始堆shi喵)
    def save(self):
        global config, config_path
        try:
            with open(config_path, 'r', encoding="utf-8") as config_file:
                config_data = json.load(config_file)
        except Exception as e:
            logging.error(f"无法写入配置文件！\n{e}")
            self.show_message_box("错误", f"无法写入配置文件！\n{e}", QMessageBox.Critical)
            return False

        def common_textEdit_handle(content):
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
            # 获取下拉框当前选中的内容
            platform = self.ui.comboBox_platform.currentText()
            if platform == "聊天模式":
                config_data["platform"] = "talk"
            elif platform == "哔哩哔哩":
                config_data["platform"] = "bilibili"
            elif platform == "抖音":
                config_data["platform"] = "dy"
            elif platform == "快手":
                config_data["platform"] = "ks"
            elif platform == "斗鱼":
                config_data["platform"] = "douyu"
            elif platform == "YouTube":
                config_data["platform"] = "youtube"
            elif platform == "twitch":
                config_data["platform"] = "twitch"
            elif platform == "哔哩哔哩2":
                config_data["platform"] = "bilibili2"

            # 获取单行文本输入框的内容
            room_display_id = self.ui.lineEdit_room_display_id.text()
            # 直播间号配置放宽
            # if False == self.is_alpha_numeric(room_display_id):
            #     logging.error("直播间号只由字母或数字组成，请勿输入错误内容")
            #     self.show_message_box("错误", "直播间号只由字母或数字组成，请勿输入错误内容", QMessageBox.Critical)
            #     return False
            config_data["room_display_id"] = room_display_id
                
            # 新增LLM时，这块也需要适配，保存回配置文件
            chat_type = self.ui.comboBox_chat_type.currentText()
            logging.info(f"chat_type={chat_type}")
            if chat_type == "不启用":
                config_data["chat_type"] = "none"
            elif chat_type == "复读机":
                config_data["chat_type"] = "reread"
            elif chat_type == "ChatGPT/闻达":
                config_data["chat_type"] = "chatgpt"
            elif chat_type == "Claude":
                config_data["chat_type"] = "claude"
            elif chat_type == "Claude2":
                config_data["chat_type"] = "claude2"
            elif chat_type == "ChatGLM":
                config_data["chat_type"] = "chatglm"
            elif chat_type == "chat_with_file":
                config_data["chat_type"] = "chat_with_file"
            elif chat_type == "Chatterbot":
                config_data["chat_type"] = "chatterbot"
            elif chat_type == "text_generation_webui":
                config_data["chat_type"] = "text_generation_webui"
            elif chat_type == "讯飞星火":
                config_data["chat_type"] = "sparkdesk"
            elif chat_type == "langchain_chatglm":
                config_data["chat_type"] = "langchain_chatglm"
            elif chat_type == "智谱AI":
                config_data["chat_type"] = "zhipu"
            elif chat_type == "Bard":
                config_data["chat_type"] = "bard"
            elif chat_type == "文心一言":
                config_data["chat_type"] = "yiyan"
            elif chat_type == "通义千问":
                config_data["chat_type"] = "tongyi"
            
            config_data["visual_body"] = self.ui.comboBox_visual_body.currentText()

            config_data["before_prompt"] = self.ui.lineEdit_before_prompt.text()
            config_data["after_prompt"] = self.ui.lineEdit_after_prompt.text()

            # 本地问答
            config_data["read_user_name"]["enable"] = self.ui.checkBox_read_user_name_enable.isChecked()
            config_data["read_user_name"]["voice_change"] = self.ui.checkBox_read_user_name_voice_change.isChecked()
            config_data["read_user_name"]["reply_before"] = common_textEdit_handle(self.ui.textEdit_read_user_name_reply_before.toPlainText())
            config_data["read_user_name"]["reply_after"] = common_textEdit_handle(self.ui.textEdit_read_user_name_reply_after.toPlainText())

            need_lang = self.ui.comboBox_need_lang.currentText()
            if need_lang == "所有":
                config_data["need_lang"] = "none"
            elif need_lang == "中文":
                config_data["need_lang"] = "zh"
            elif need_lang == "英文":
                config_data["need_lang"] = "en"
            elif need_lang == "日文":
                config_data["need_lang"] = "jp"

            config_data["comment_log_type"] = self.ui.comboBox_comment_log_type.currentText()

            # 日志
            config_data["captions"]["enable"] = self.ui.checkBox_captions_enable.isChecked()
            config_data["captions"]["file_path"] = self.ui.lineEdit_captions_file_path.text()

            # 本地问答
            config_data["local_qa"]["text"]["enable"] = self.ui.checkBox_local_qa_text_enable.isChecked()
            local_qa_text_type = self.ui.comboBox_local_qa_text_type.currentText()
            if local_qa_text_type == "自定义json":
                config_data["local_qa"]["text"]["type"] = "json"
            elif local_qa_text_type == "一问一答":
                config_data["local_qa"]["text"]["type"] = "text"
            config_data["local_qa"]["text"]["file_path"] = self.ui.lineEdit_local_qa_text_file_path.text()
            config_data["local_qa"]["text"]["similarity"] = round(float(self.ui.lineEdit_local_qa_text_similarity.text()), 2)
            config_data["local_qa"]["audio"]["enable"] = self.ui.checkBox_local_qa_audio_enable.isChecked()
            config_data["local_qa"]["audio"]["file_path"] = self.ui.lineEdit_local_qa_audio_file_path.text()
            config_data["local_qa"]["audio"]["similarity"] = round(float(self.ui.lineEdit_local_qa_audio_similarity.text()), 2)

            # 过滤
            config_data["filter"]["before_must_str"] = common_textEdit_handle(self.ui.textEdit_filter_before_must_str.toPlainText())
            config_data["filter"]["after_must_str"] = common_textEdit_handle(self.ui.textEdit_filter_after_must_str.toPlainText())
            config_data["filter"]["badwords_path"] = self.ui.lineEdit_filter_badwords_path.text()
            config_data["filter"]["bad_pinyin_path"] = self.ui.lineEdit_filter_bad_pinyin_path.text()
            config_data["filter"]["max_len"] = int(self.ui.lineEdit_filter_max_len.text())
            config_data["filter"]["max_char_len"] = int(self.ui.lineEdit_filter_max_char_len.text())
            config_data["filter"]["comment_forget_duration"] = round(float(self.ui.lineEdit_filter_comment_forget_duration.text()), 2)
            config_data["filter"]["comment_forget_reserve_num"] = int(self.ui.lineEdit_filter_comment_forget_reserve_num.text())
            config_data["filter"]["gift_forget_duration"] = round(float(self.ui.lineEdit_filter_gift_forget_duration.text()), 2)
            config_data["filter"]["gift_forget_reserve_num"] = int(self.ui.lineEdit_filter_gift_forget_reserve_num.text())
            config_data["filter"]["entrance_forget_duration"] = round(float(self.ui.lineEdit_filter_entrance_forget_duration.text()), 2)
            config_data["filter"]["entrance_forget_reserve_num"] = int(self.ui.lineEdit_filter_entrance_forget_reserve_num.text())
            config_data["filter"]["follow_forget_duration"] = round(float(self.ui.lineEdit_filter_follow_forget_duration.text()), 2)
            config_data["filter"]["follow_forget_reserve_num"] = int(self.ui.lineEdit_filter_follow_forget_reserve_num.text())
            config_data["filter"]["talk_forget_duration"] = round(float(self.ui.lineEdit_filter_talk_forget_duration.text()), 2)
            config_data["filter"]["talk_forget_reserve_num"] = int(self.ui.lineEdit_filter_talk_forget_reserve_num.text())
            config_data["filter"]["schedule_forget_duration"] = round(float(self.ui.lineEdit_filter_schedule_forget_duration.text()), 2)
            config_data["filter"]["schedule_forget_reserve_num"] = int(self.ui.lineEdit_filter_schedule_forget_reserve_num.text())

            # 答谢
            config_data["thanks"]["entrance_enable"] = self.ui.checkBox_thanks_entrance_enable.isChecked()
            config_data["thanks"]["entrance_copy"] = self.ui.lineEdit_thanks_entrance_copy.text()
            config_data["thanks"]["gift_enable"] = self.ui.checkBox_thanks_gift_enable.isChecked()
            config_data["thanks"]["gift_copy"] = self.ui.lineEdit_thanks_gift_copy.text()
            config_data["thanks"]["lowest_price"] = round(float(self.ui.lineEdit_thanks_lowest_price.text()), 2)
            config_data["thanks"]["follow_enable"] = self.ui.checkBox_thanks_follow_enable.isChecked()
            config_data["thanks"]["follow_copy"] = self.ui.lineEdit_thanks_follow_copy.text()

            config_data["live2d"]["enable"] = self.ui.checkBox_live2d_enable.isChecked()
            live2d_port = self.ui.lineEdit_live2d_port.text()
            config_data["live2d"]["port"] = int(live2d_port)
            tmp_str = f"var model_name = \"{self.ui.comboBox_live2d_name.currentText()}\";"
            common.write_content_to_file("Live2D/js/model_name.js", tmp_str)

            openai_api = self.ui.lineEdit_openai_api.text()
            config_data["openai"]["api"] = openai_api
            # 获取多行文本输入框的内容
            config_data["openai"]["api_key"] = common_textEdit_handle(self.ui.textEdit_openai_api_key.toPlainText())

            config_data["chatgpt"]["model"] = self.ui.comboBox_chatgpt_model.currentText()
            config_data["chatgpt"]["temperature"] = round(float(self.ui.lineEdit_chatgpt_temperature.text()), 1)
            config_data["chatgpt"]["max_tokens"] = int(self.ui.lineEdit_chatgpt_max_tokens.text())
            config_data["chatgpt"]["top_p"] = round(float(self.ui.lineEdit_chatgpt_top_p.text()), 1)
            config_data["chatgpt"]["presence_penalty"] = round(float(self.ui.lineEdit_chatgpt_presence_penalty.text()), 1)
            config_data["chatgpt"]["frequency_penalty"] = round(float(self.ui.lineEdit_chatgpt_frequency_penalty.text()), 1)
            config_data["chatgpt"]["preset"] = self.ui.lineEdit_chatgpt_preset.text()

            chatterbot_name = self.ui.lineEdit_chatterbot_name.text()
            config_data["chatterbot"]["name"] = chatterbot_name
            chatterbot_db_path = self.ui.lineEdit_chatterbot_db_path.text()
            config_data["chatterbot"]["db_path"] = chatterbot_db_path

            config_data["claude"]["slack_user_token"] = self.ui.lineEdit_claude_slack_user_token.text()
            config_data["claude"]["bot_user_id"] = self.ui.lineEdit_claude_bot_user_id.text()

            config_data["claude2"]["cookie"] = self.ui.lineEdit_claude2_cookie.text()
            config_data["claude2"]["use_proxy"] = self.ui.checkBox_claude2_use_proxy.isChecked()
            config_data["claude2"]["proxies"]["http"] = self.ui.lineEdit_claude2_proxies_http.text()
            config_data["claude2"]["proxies"]["https"] = self.ui.lineEdit_claude2_proxies_https.text()
            config_data["claude2"]["proxies"]["socks5"] = self.ui.lineEdit_claude2_proxies_socks5.text()

            config_data["chatglm"]["api_ip_port"] = self.ui.lineEdit_chatglm_api_ip_port.text()
            config_data["chatglm"]["max_length"] = int(self.ui.lineEdit_chatglm_max_length.text())
            config_data["chatglm"]["top_p"] = round(float(self.ui.lineEdit_chatglm_top_p.text()), 1)
            config_data["chatglm"]["temperature"] = round(float(self.ui.lineEdit_chatglm_temperature.text()), 2)
            config_data["chatglm"]["history_enable"] = self.ui.checkBox_chatglm_history_enable.isChecked()
            config_data["chatglm"]["history_max_len"] = int(self.ui.lineEdit_chatglm_history_max_len.text())

            config_data["langchain_chatglm"]["api_ip_port"] = self.ui.lineEdit_langchain_chatglm_api_ip_port.text()
            config_data["langchain_chatglm"]["chat_type"] = self.ui.comboBox_langchain_chatglm_chat_type.currentText()
            config_data["langchain_chatglm"]["knowledge_base_id"] = self.ui.lineEdit_langchain_chatglm_knowledge_base_id.text()
            config_data["langchain_chatglm"]["history_enable"] = self.ui.checkBox_langchain_chatglm_history_enable.isChecked()
            config_data["langchain_chatglm"]["history_max_len"] = int(self.ui.lineEdit_langchain_chatglm_history_max_len.text())

            config_data["chat_with_file"]["chat_mode"] = self.ui.comboBox_chat_with_file_chat_mode.currentText()
            chat_with_file_data_path = self.ui.lineEdit_chat_with_file_data_path.text()
            config_data["chat_with_file"]["data_path"] = chat_with_file_data_path
            chat_with_file_separator = self.ui.lineEdit_chat_with_file_separator.text()
            config_data["chat_with_file"]["separator"] = chat_with_file_separator
            chat_with_file_chunk_size = self.ui.lineEdit_chat_with_file_chunk_size.text()
            config_data["chat_with_file"]["chunk_size"] = int(chat_with_file_chunk_size)
            chat_with_file_chunk_overlap = self.ui.lineEdit_chat_with_file_chunk_overlap.text()
            config_data["chat_with_file"]["chunk_overlap"] = int(chat_with_file_chunk_overlap)
            config_data["chat_with_file"]["local_vector_embedding_model"] = self.ui.comboBox_chat_with_file_local_vector_embedding_model.currentText()
            chat_with_file_chain_type = self.ui.lineEdit_chat_with_file_chain_type.text()
            config_data["chat_with_file"]["chain_type"] = chat_with_file_chain_type
            # 获取复选框的选中状态
            chat_with_file_show_token_cost = self.ui.checkBox_chat_with_file_show_token_cost.isChecked()
            config_data["chat_with_file"]["show_token_cost"] = chat_with_file_show_token_cost
            chat_with_file_question_prompt = self.ui.lineEdit_chat_with_file_question_prompt.text()
            config_data["chat_with_file"]["question_prompt"] = chat_with_file_question_prompt
            chat_with_file_local_max_query = self.ui.lineEdit_chat_with_file_local_max_query.text()
            config_data["chat_with_file"]["local_max_query"] = int(chat_with_file_local_max_query)

            config_data["text_generation_webui"]["api_ip_port"] = self.ui.lineEdit_text_generation_webui_api_ip_port.text()
            config_data["text_generation_webui"]["max_new_tokens"] = int(self.ui.lineEdit_text_generation_webui_max_new_tokens.text())
            config_data["text_generation_webui"]["mode"] = self.ui.lineEdit_text_generation_webui_mode.text()
            config_data["text_generation_webui"]["character"] = self.ui.lineEdit_text_generation_webui_character.text()
            config_data["text_generation_webui"]["instruction_template"] = self.ui.lineEdit_text_generation_webui_instruction_template.text()
            config_data["text_generation_webui"]["your_name"] = self.ui.lineEdit_text_generation_webui_your_name.text()

            # sparkdesk
            config_data["sparkdesk"]["type"] = self.ui.comboBox_sparkdesk_type.currentText()
            config_data["sparkdesk"]["cookie"] = self.ui.lineEdit_sparkdesk_cookie.text()
            config_data["sparkdesk"]["fd"] = self.ui.lineEdit_sparkdesk_fd.text()
            config_data["sparkdesk"]["GtToken"] = self.ui.lineEdit_sparkdesk_GtToken.text()
            config_data["sparkdesk"]["app_id"] = self.ui.lineEdit_sparkdesk_app_id.text()
            config_data["sparkdesk"]["api_secret"] = self.ui.lineEdit_sparkdesk_api_secret.text()
            config_data["sparkdesk"]["api_key"] = self.ui.lineEdit_sparkdesk_api_key.text()
            config_data["sparkdesk"]["version"] = round(float(self.ui.comboBox_sparkdesk_version.currentText()), 1)

            audio_synthesis_type = self.ui.comboBox_audio_synthesis_type.currentText()
            if audio_synthesis_type == "Edge-TTS":
                config_data["audio_synthesis_type"] = "edge-tts"
            elif audio_synthesis_type == "VITS":
                config_data["audio_synthesis_type"] = "vits"
            elif audio_synthesis_type == "VITS-Fast":
                config_data["audio_synthesis_type"] = "vits_fast"
            elif audio_synthesis_type == "elevenlabs":
                config_data["audio_synthesis_type"] = "elevenlabs"
            elif audio_synthesis_type == "genshinvoice_top":
                config_data["audio_synthesis_type"] = "genshinvoice_top"
            elif audio_synthesis_type == "bark_gui":
                config_data["audio_synthesis_type"] = "bark_gui"
            elif audio_synthesis_type == "VALL-E-X":
                config_data["audio_synthesis_type"] = "vall_e_x"
            elif audio_synthesis_type == "OpenAI TTS":
                config_data["audio_synthesis_type"] = "openai_tts"

            # 音频随机变速
            config_data["audio_random_speed"]["normal"]["enable"] = self.ui.checkBox_audio_random_speed_normal_enable.isChecked()
            config_data["audio_random_speed"]["normal"]["speed_min"] = round(float(self.ui.lineEdit_audio_random_speed_normal_speed_min.text()), 2)
            config_data["audio_random_speed"]["normal"]["speed_max"] = round(float(self.ui.lineEdit_audio_random_speed_normal_speed_max.text()), 2)
            config_data["audio_random_speed"]["copywriting"]["enable"] = self.ui.checkBox_audio_random_speed_copywriting_enable.isChecked()
            config_data["audio_random_speed"]["copywriting"]["speed_min"] = round(float(self.ui.lineEdit_audio_random_speed_copywriting_speed_min.text()), 2)
            config_data["audio_random_speed"]["copywriting"]["speed_max"] = round(float(self.ui.lineEdit_audio_random_speed_copywriting_speed_max.text()), 2)

            config_data["vits_fast"]["config_path"] = self.ui.lineEdit_vits_fast_config_path.text()
            config_data["vits_fast"]["api_ip_port"] = self.ui.lineEdit_vits_fast_api_ip_port.text()
            config_data["vits_fast"]["character"] = self.ui.lineEdit_vits_fast_character.text()
            config_data["vits_fast"]["language"] = self.ui.comboBox_vits_fast_language.currentText()
            config_data["vits_fast"]["speed"] = round(float(self.ui.lineEdit_vits_fast_speed.text()), 1)

            config_data["edge-tts"]["voice"] = self.ui.comboBox_edge_tts_voice.currentText()
            config_data["edge-tts"]["rate"] = self.ui.lineEdit_edge_tts_rate.text()
            config_data["edge-tts"]["volume"] = self.ui.lineEdit_edge_tts_volume.text()

            config_data["elevenlabs"]["api_key"] = self.ui.lineEdit_elevenlabs_api_key.text()
            config_data["elevenlabs"]["voice"] = self.ui.lineEdit_elevenlabs_voice.text()
            config_data["elevenlabs"]["model"] = self.ui.lineEdit_elevenlabs_model.text()

            config_data["genshinvoice_top"]["speaker"] = self.ui.comboBox_genshinvoice_top_speaker.currentText()
            config_data["genshinvoice_top"]["noise"] = self.ui.lineEdit_genshinvoice_top_noise.text()
            config_data["genshinvoice_top"]["noisew"] = self.ui.lineEdit_genshinvoice_top_noisew.text()
            config_data["genshinvoice_top"]["length"] = self.ui.lineEdit_genshinvoice_top_length.text()
            config_data["genshinvoice_top"]["format"] = self.ui.lineEdit_genshinvoice_top_format.text()
            config_data["genshinvoice_top"]["language"] = self.ui.comboBox_genshinvoice_top_language.currentText()

            # bark-gui
            config_data["bark_gui"]["api_ip_port"] = self.ui.lineEdit_bark_gui_api_ip_port.text()
            config_data["bark_gui"]["spk"] = self.ui.lineEdit_bark_gui_spk.text()
            config_data["bark_gui"]["generation_temperature"] = round(float(self.ui.lineEdit_bark_gui_generation_temperature.text()), 1)
            config_data["bark_gui"]["waveform_temperature"] = round(float(self.ui.lineEdit_bark_gui_waveform_temperature.text()), 1)
            config_data["bark_gui"]["end_of_sentence_probability"] = round(float(self.ui.lineEdit_bark_gui_end_of_sentence_probability.text()), 2)
            config_data["bark_gui"]["quick_generation"] = self.ui.checkBox_bark_gui_quick_generation.isChecked()
            config_data["bark_gui"]["seed"] = round(float(self.ui.lineEdit_bark_gui_seed.text()), 2)
            config_data["bark_gui"]["batch_count"] = int(self.ui.lineEdit_bark_gui_batch_count.text())

            # 点歌
            config_data["choose_song"]["enable"] = self.ui.checkBox_choose_song_enable.isChecked()
            config_data["choose_song"]["start_cmd"] = self.ui.lineEdit_choose_song_start_cmd.text()
            config_data["choose_song"]["stop_cmd"] = self.ui.lineEdit_choose_song_stop_cmd.text()
            config_data["choose_song"]["random_cmd"] = self.ui.lineEdit_choose_song_random_cmd.text()
            config_data["choose_song"]["song_path"] = self.ui.lineEdit_choose_song_song_path.text()
            config_data["choose_song"]["match_fail_copy"] = self.ui.lineEdit_choose_song_match_fail_copy.text()

            # DDSP-SVC
            config_data["ddsp_svc"]["enable"] = self.ui.checkBox_ddsp_svc_enable.isChecked()
            config_data["ddsp_svc"]["config_path"] = self.ui.lineEdit_ddsp_svc_config_path.text()
            config_data["ddsp_svc"]["api_ip_port"] = self.ui.lineEdit_ddsp_svc_api_ip_port.text()
            config_data["ddsp_svc"]["fSafePrefixPadLength"] = round(float(self.ui.lineEdit_ddsp_svc_fSafePrefixPadLength.text()), 1)
            config_data["ddsp_svc"]["fPitchChange"] = round(float(self.ui.lineEdit_ddsp_svc_fPitchChange.text()), 1)
            config_data["ddsp_svc"]["sSpeakId"] = int(self.ui.lineEdit_ddsp_svc_sSpeakId.text())
            config_data["ddsp_svc"]["sampleRate"] = int(self.ui.lineEdit_ddsp_svc_sampleRate.text())

            # so-vits-svc
            config_data["so_vits_svc"]["enable"] = self.ui.checkBox_so_vits_svc_enable.isChecked()
            config_data["so_vits_svc"]["config_path"] = self.ui.lineEdit_so_vits_svc_config_path.text()
            config_data["so_vits_svc"]["api_ip_port"] = self.ui.lineEdit_so_vits_svc_api_ip_port.text()
            config_data["so_vits_svc"]["spk"] = self.ui.lineEdit_so_vits_svc_spk.text()
            config_data["so_vits_svc"]["tran"] = round(float(self.ui.lineEdit_so_vits_svc_tran.text()), 1)
            config_data["so_vits_svc"]["wav_format"] = self.ui.lineEdit_so_vits_svc_wav_format.text()

            # SD
            config_data["sd"]["enable"] = self.ui.checkBox_sd_enable.isChecked()
            config_data["sd"]["prompt_llm"]["type"] = self.ui.comboBox_prompt_llm_type.currentText()
            config_data["sd"]["prompt_llm"]["before_prompt"] = self.ui.lineEdit_prompt_llm_before_prompt.text()
            config_data["sd"]["prompt_llm"]["after_prompt"] = self.ui.lineEdit_prompt_llm_after_prompt.text()
            config_data["sd"]["trigger"] = self.ui.lineEdit_sd_trigger.text()
            config_data["sd"]["ip"] = self.ui.lineEdit_sd_ip.text()
            sd_port = self.ui.lineEdit_sd_port.text()
            # logging.info(f"sd_port={sd_port}")
            config_data["sd"]["port"] = int(sd_port)
            config_data["sd"]["negative_prompt"] = self.ui.lineEdit_sd_negative_prompt.text()
            config_data["sd"]["seed"] = float(self.ui.lineEdit_sd_seed.text())
            # 获取多行文本输入框的内容
            config_data["sd"]["styles"] = common_textEdit_handle(self.ui.textEdit_sd_styles.toPlainText())
            config_data["sd"]["cfg_scale"] = int(self.ui.lineEdit_sd_cfg_scale.text())
            config_data["sd"]["steps"] = int(self.ui.lineEdit_sd_steps.text())
            config_data["sd"]["hr_resize_x"] = int(self.ui.lineEdit_sd_hr_resize_x.text())
            config_data["sd"]["hr_resize_y"] = int(self.ui.lineEdit_sd_hr_resize_y.text())
            config_data["sd"]["enable_hr"] = self.ui.checkBox_sd_enable_hr.isChecked()
            config_data["sd"]["hr_scale"] = int(self.ui.lineEdit_sd_hr_scale.text())
            config_data["sd"]["hr_second_pass_steps"] = int(self.ui.lineEdit_sd_hr_second_pass_steps.text())
            config_data["sd"]["denoising_strength"] = round(float(self.ui.lineEdit_sd_denoising_strength.text()), 1)

            config_data["header"]["userAgent"] = self.ui.lineEdit_header_useragent.text()
            
            # 聊天
            config_data["talk"]["username"] = self.ui.lineEdit_talk_username.text()
            config_data["talk"]["continuous_talk"] = self.ui.checkBox_talk_continuous_talk.isChecked()
            config_data["talk"]["trigger_key"] = self.ui.comboBox_talk_trigger_key.currentText()
            config_data["talk"]["stop_trigger_key"] = self.ui.comboBox_talk_stop_trigger_key.currentText()
            config_data["talk"]["type"] = self.ui.comboBox_talk_type.currentText()
            config_data["talk"]["volume_threshold"] = round(float(self.ui.lineEdit_talk_volume_threshold.text()), 1)
            config_data["talk"]["silence_threshold"] = round(float(self.ui.lineEdit_talk_silence_threshold.text()), 1)
            config_data["talk"]["baidu"]["app_id"] = self.ui.lineEdit_talk_baidu_app_id.text()
            config_data["talk"]["baidu"]["api_key"] = self.ui.lineEdit_talk_baidu_api_key.text()
            config_data["talk"]["baidu"]["secret_key"] = self.ui.lineEdit_talk_baidu_secret_key.text()
            config_data["talk"]["google"]["tgt_lang"] = self.ui.comboBox_talk_google_tgt_lang.currentText()
            
            schedule_data = self.update_data_from_gridLayout(self.ui.gridLayout_schedule)

            """
            动态读取GUI内数据到配置变量
            """
            # 通用的函数用于将GridLayout数据重组为JSON格式列表
            def reorganize_grid_data_list(grid_data, keys_per_item):
                tmp_json = []
                keys = list(grid_data.keys())

                for i in range(0, len(keys), len(keys_per_item)):
                    item = {}
                    for j, key in enumerate(keys_per_item):
                        item[key] = grid_data[keys[i + j]]
                    tmp_json.append(item)

                logging.debug(f"tmp_json={tmp_json}")
                return tmp_json

            # 通用的函数用于将GridLayout数据重组为JSON格式
            def reorganize_grid_data(grid_data, keys_mapping):
                keys = list(grid_data.keys())
                tmp_json = {new_key: grid_data[keys[old_key]] for new_key, old_key in keys_mapping.items()}
                logging.debug(f"tmp_json={tmp_json}")
                return tmp_json

            def reorganize_schedule_data(schedule_data):
                tmp_json = []
                keys = list(schedule_data.keys())

                for i in range(0, len(keys), 3):
                    item = {}

                    key_checkbox = keys[i]
                    key_lineedit = keys[i + 1]
                    key_textedit = keys[i + 2]

                    item["enable"] = schedule_data[key_checkbox]

                    time_value = schedule_data[key_lineedit]
                    try:
                        item["time"] = float(time_value)
                    except ValueError:
                        item["time"] = 1.0

                    # 对于文本列表，确保处理成字符串列表类型
                    copy_list = schedule_data[key_textedit]
                    if isinstance(copy_list, list):
                        item["copy"] = [str(item) for item in copy_list if isinstance(item, str)]
                    else:
                        item["copy"] = []

                    tmp_json.append(item)

                logging.debug(f"tmp_json={tmp_json}")

                return tmp_json

            # 写回json
            config_data["schedule"] = reorganize_schedule_data(schedule_data)
            # logging.info(config_data)

            # 文案
            copywriting_config_data = self.update_data_from_gridLayout(self.ui.gridLayout_copywriting_config)

            def reorganize_copywriting_config_data(copywriting_config_data):
                tmp_json = []
                keys = list(copywriting_config_data.keys())

                for i in range(0, len(keys), 7):
                    item = {}

                    key_file_path = keys[i]
                    key_audio_path = keys[i + 1]
                    # 跳过1个
                    key_play_list = keys[i + 2 + 1]
                    # 跳过1个
                    key_continuous_play_num = keys[i + 3 + 2]
                    key_max_play_time = keys[i + 4 + 2]

                    item["file_path"] = copywriting_config_data[key_file_path]
                    item["audio_path"] = copywriting_config_data[key_audio_path]

                    # 对于文本列表，确保处理成字符串列表类型
                    play_list = copywriting_config_data[key_play_list]
                    if isinstance(play_list, list):
                        item["play_list"] = [str(item) for item in play_list if isinstance(item, str)]
                    else:
                        item["play_list"] = []

                    try:
                        item["continuous_play_num"] = int(copywriting_config_data[key_continuous_play_num])
                    except ValueError:
                        item["continuous_play_num"] = 1

                    max_play_time = copywriting_config_data[key_max_play_time]
                    try:
                        item["max_play_time"] = round(float(max_play_time), 2)
                    except ValueError:
                        item["max_play_time"] = 1.0

                    tmp_json.append(item)

                logging.debug(f"tmp_json={tmp_json}")

                return tmp_json

            config_data["copywriting"]["config"] = reorganize_copywriting_config_data(copywriting_config_data)
            config_data["copywriting"]["audio_interval"] = round(float(self.ui.lineEdit_copywriting_audio_interval.text()), 1)
            config_data["copywriting"]["switching_interval"] = round(float(self.ui.lineEdit_copywriting_switching_interval.text()), 1)
            config_data["copywriting"]["auto_play"] = self.ui.checkBox_copywriting_switching_auto_play.isChecked()
            config_data["copywriting"]["random_play"] = self.ui.checkBox_copywriting_switching_random_play.isChecked()

        
            # 定义每个GridLayout的键映射
            zhipu_keys_mapping = {
                "api_key": 0,
                "model": 1,
                "top_p": 2,
                "temperature": 3,
                "history_enable": 4,
                "history_max_len": 5,
                "user_info": 6,
                "bot_info": 7,
                "bot_name": 8,
                "user_name": 9,
                "remove_useless": 10
            }

            # 重组zhipu数据并写回json
            zhipu_data = self.update_data_from_gridLayout(self.ui.gridLayout_zhipu)
            config_data["zhipu"] = reorganize_grid_data(zhipu_data, zhipu_keys_mapping)

            # 动态文案
            config_data["trends_copywriting"]["enable"] = self.ui.checkBox_trends_copywriting_enable.isChecked()
            config_data["trends_copywriting"]["random_play"] = self.ui.checkBox_trends_copywriting_random_play.isChecked()
            config_data["trends_copywriting"]["play_interval"] = int(self.ui.lineEdit_trends_copywriting_play_interval.text())

            # 定义trends_copywriting GridLayout的键映射
            trends_copywriting_keys_per_item = ["folder_path", "prompt_change_enable", "prompt_change_content"]
            # 重组trends_copywriting数据并写回json
            trends_copywriting_data = self.update_data_from_gridLayout(self.ui.gridLayout_trends_copywriting_2)
            config_data["trends_copywriting"]["copywriting"] = reorganize_grid_data_list(trends_copywriting_data, trends_copywriting_keys_per_item)

            # 闲时文案
            idle_time_task_keys_mapping = {
                "enable": 0,
                "idle_time": 1,
                "random_time": 2
            }

            # 重组idle_time_task数据并写回json
            idle_time_task_data = self.update_data_from_gridLayout(self.ui.gridLayout_idle_time_task)
            config_data["idle_time_task"] = reorganize_grid_data(idle_time_task_data, idle_time_task_keys_mapping)

            idle_time_task_comment_keys_mapping = {
                "enable": 0,
                "random": 1,
                "copy": 2
            }

            # 重组idle_time_task_comment数据并写回json
            idle_time_task_comment_data = self.update_data_from_gridLayout(self.ui.gridLayout_idle_time_task_comment)
            config_data["idle_time_task"]["comment"] = reorganize_grid_data(idle_time_task_comment_data, idle_time_task_comment_keys_mapping)

            idle_time_task_local_audio_keys_mapping = {
                "enable": 0,
                "random": 1,
                "path": 2
            }

            # 重组idle_time_task_local_audio数据并写回json
            idle_time_task_local_audio_data = self.update_data_from_gridLayout(self.ui.gridLayout_idle_time_task_local_audio)
            config_data["idle_time_task"]["local_audio"] = reorganize_grid_data(idle_time_task_local_audio_data, idle_time_task_local_audio_keys_mapping)

            vits_keys_mapping = {
                "type": 0,
                "config_path": 1,
                "api_ip_port": 2,
                "id": 3,
                "lang": 4,
                "length": 5,
                "noise": 6,
                "noisew": 7,
                "max": 8,
                "format": 9,
                "sdp_radio": 10,
            }

            # 重组vits数据并写回json
            vits_data = self.update_data_from_gridLayout(self.ui.gridLayout_vits)
            config_data["vits"] = reorganize_grid_data(vits_data, vits_keys_mapping)

            database_keys_mapping = {
                "path": 0,
                "comment_enable": 1,
                "entrance_enable": 2,
                "gift_enable": 3
            }

            # 重组database数据并写回json
            database_data = self.update_data_from_gridLayout(self.ui.gridLayout_database)
            config_data["database"] = reorganize_grid_data(database_data, database_keys_mapping)

            play_audio_keys_mapping = {
                "enable": 0,
                "out_path": 1,
                "player": 2
            }

            # 重组play_audio数据并写回json
            play_audio_data = self.update_data_from_gridLayout(self.ui.gridLayout_play_audio)
            config_data["play_audio"] = reorganize_grid_data(play_audio_data, play_audio_keys_mapping)

            audio_player_keys_mapping = {
                "api_ip_port": 0
                # "type": 2  # 如果不需要该字段，可以注释掉或删除
            }

            # 重组audio_player数据并写回json
            audio_player_data = self.update_data_from_gridLayout(self.ui.gridLayout_audio_player)
            config_data["audio_player"] = reorganize_grid_data(audio_player_data, audio_player_keys_mapping)

            web_captions_printer_keys_mapping = {
                "enable": 0,
                "api_ip_port": 1
                # "type": 2  # 如果不需要该字段，可以注释掉或删除
            }

            # 重组web_captions_printer数据并写回json
            web_captions_printer_data = self.update_data_from_gridLayout(self.ui.gridLayout_web_captions_printer)
            config_data["web_captions_printer"] = reorganize_grid_data(web_captions_printer_data, web_captions_printer_keys_mapping)

            vall_e_x_keys_mapping = {
                "api_ip_port": 0,
                "language": 1,
                "accent": 2,
                "voice_preset": 3,
                "voice_preset_file_path": 4
            }

            # 重组bilibili数据并写回json
            vall_e_x_data = self.update_data_from_gridLayout(self.ui.gridLayout_vall_e_x)
            config_data["vall_e_x"] = reorganize_grid_data(vall_e_x_data, vall_e_x_keys_mapping)

            openai_tts_keys_mapping = {
                "type": 0,
                "api_ip_port": 1,
                "model": 2,
                "voice": 3,
                "api_key": 4
            }

            # 重组openai_tts数据并写回json
            openai_tts_data = self.update_data_from_gridLayout(self.ui.gridLayout_openai_tts)
            config_data["openai_tts"] = reorganize_grid_data(openai_tts_data, openai_tts_keys_mapping)

            bilibili_keys_mapping = {
                "login_type": 0,
                "cookie": 1,
                "ac_time_value": 2,
                "username": 3,
                "password": 4
            }

            # 重组bilibili数据并写回json
            bilibili_data = self.update_data_from_gridLayout(self.ui.gridLayout_bilibili)
            config_data["bilibili"] = reorganize_grid_data(bilibili_data, bilibili_keys_mapping)

            twitch_keys_mapping = {
                "token": 0,
                "user": 1,
                "proxy_server": 2,
                "proxy_port": 3
            }

            # 重组twitch数据并写回json
            twitch_data = self.update_data_from_gridLayout(self.ui.gridLayout_twitch)
            config_data["twitch"] = reorganize_grid_data(twitch_data, twitch_keys_mapping)


            bard_keys_mapping = {
                "token": 0
            }

            # 重组bard数据并写回json
            bard_data = self.update_data_from_gridLayout(self.ui.gridLayout_bard)
            config_data["bard"] = reorganize_grid_data(bard_data, bard_keys_mapping)

            # 文心一言
            yiyan_keys_mapping = {
                "api_ip_port": 0,
                "type": 1,
                "cookie": 2
            }

            # 重组yiyan数据并写回json
            yiyan_data = self.update_data_from_gridLayout(self.ui.gridLayout_yiyan)
            config_data["yiyan"] = reorganize_grid_data(yiyan_data, yiyan_keys_mapping)

            # 通义千问
            tongyi_keys_mapping = {
                "type": 0,
                "cookie_path": 1
            }

            tongyi_data = self.update_data_from_gridLayout(self.ui.gridLayout_tongyi)
            config_data["tongyi"] = reorganize_grid_data(tongyi_data, tongyi_keys_mapping)

            # 念弹幕
            read_comment_keys_mapping = {
                "enable": 0,
                "read_username_enable": 1,
                "voice_change": 2,
                "read_username_copywriting": 3
            }

            # 重组read_comment数据并写回json
            read_comment_data = self.update_data_from_gridLayout(self.ui.gridLayout_read_comment)
            config_data["read_comment"] = reorganize_grid_data(read_comment_data, read_comment_keys_mapping)

            # 按键映射
            config_data["key_mapping"]["enable"] = self.ui.checkBox_key_mapping_enable.isChecked()
            config_data["key_mapping"]["type"] = self.ui.comboBox_key_mapping_type.currentText()
            config_data["key_mapping"]["start_cmd"] = self.ui.lineEdit_key_mapping_start_cmd.text()

            key_mapping_config_keys_per_item = ["keywords", "keys", "similarity"]

            # 重组key_mapping_config数据并写回json
            key_mapping_config_data = self.update_data_from_gridLayout(self.ui.gridLayout_key_mapping_config)
            config_data["key_mapping"]["config"] = reorganize_grid_data_list(key_mapping_config_data, key_mapping_config_keys_per_item)

            """
            积分页
            """
            config_data["integral"]["enable"] = self.ui.checkBox_integral_common_enable.isChecked()

            # 入场
            def reorganize_integral_entrance_data(integral_entrance_data):
                keys = list(integral_entrance_data.keys())

                tmp_json = {
                    "enable": integral_entrance_data[keys[0]],
                    "get_integral": int(integral_entrance_data[keys[1]]),
                    "copywriting": []
                }

                logging.debug(f"tmp_json={tmp_json}")

                return tmp_json

            integral_entrance_data = self.update_data_from_gridLayout(self.ui.gridLayout_integral_entrance)
            # 写回json
            config_data["integral"]["entrance"] = reorganize_integral_entrance_data(integral_entrance_data)

            # 入场-文案
            # 定义 GridLayout的键映射
            integral_entrance_copywriting_keys_per_item = ["entrance_num_interval", "copywriting"]

            # 重组 数据并写回json
            integral_entrance_copywriting_data = self.update_data_from_gridLayout(self.ui.gridLayout_integral_entrance_copywriting)
            config_data["integral"]["entrance"]["copywriting"] = reorganize_grid_data_list(integral_entrance_copywriting_data, integral_entrance_copywriting_keys_per_item)

            # 签到
            def reorganize_integral_sign_data(integral_sign_data):
                keys = list(integral_sign_data.keys())

                tmp_json = {
                    "enable": integral_sign_data[keys[0]],
                    "cmd": integral_sign_data[keys[1]],
                    "get_integral": int(integral_sign_data[keys[2]]),
                    "copywriting": []
                }

                logging.debug(f"tmp_json={tmp_json}")

                return tmp_json

            integral_sign_data = self.update_data_from_gridLayout(self.ui.gridLayout_integral_sign)
            # 写回json
            config_data["integral"]["sign"] = reorganize_integral_sign_data(integral_sign_data)

            # 签到-文案
            # 定义integral_sign_copywriting GridLayout的键映射
            integral_sign_copywriting_keys_per_item = ["sign_num_interval", "copywriting"]

            # 重组integral_sign_copywriting数据并写回json
            integral_sign_copywriting_data = self.update_data_from_gridLayout(self.ui.gridLayout_integral_sign_copywriting)
            config_data["integral"]["sign"]["copywriting"] = reorganize_grid_data_list(integral_sign_copywriting_data, integral_sign_copywriting_keys_per_item)

            # 礼物
            def reorganize_integral_gift_data(integral_gift_data):
                keys = list(integral_gift_data.keys())

                tmp_json = {
                    "enable": integral_gift_data[keys[0]],
                    "get_integral_proportion": float(integral_gift_data[keys[1]]),
                    "copywriting": []
                }

                logging.debug(f"tmp_json={tmp_json}")

                return tmp_json

            integral_gift_data = self.update_data_from_gridLayout(self.ui.gridLayout_integral_gift)
            # 写回json
            config_data["integral"]["gift"] = reorganize_integral_gift_data(integral_gift_data)

            # 礼物-文案
            # 定义 GridLayout的键映射
            integral_gift_copywriting_keys_per_item = ["gift_price_interval", "copywriting"]

            # 重组 数据并写回json
            integral_gift_copywriting_data = self.update_data_from_gridLayout(self.ui.gridLayout_integral_gift_copywriting)
            config_data["integral"]["gift"]["copywriting"] = reorganize_grid_data_list(integral_gift_copywriting_data, integral_gift_copywriting_keys_per_item)

            # 增删查改
            def reorganize_integral_crud_query_data(integral_crud_query_data):
                keys = list(integral_crud_query_data.keys())

                tmp_json = {
                    "enable": integral_crud_query_data[keys[0]],
                    "cmd": integral_crud_query_data[keys[1]],
                    "copywriting": integral_crud_query_data[keys[2]]
                }

                logging.debug(f"tmp_json={tmp_json}")

                return tmp_json

            integral_crud_query_data = self.update_data_from_gridLayout(self.ui.gridLayout_integral_crud_query)
            # 写回json
            config_data["integral"]["crud"]["query"] = reorganize_integral_crud_query_data(integral_crud_query_data)

            xuniren_keys_mapping = {
                "api_ip_port": 0
                # "type": 2  # 如果不需要该字段，可以注释掉或删除
            }

            xuniren_data = self.update_data_from_gridLayout(self.ui.gridLayout_xuniren)
            config_data["xuniren"] = reorganize_grid_data(xuniren_data, xuniren_keys_mapping)

            unity_keys_mapping = {
                #"enable": 0,
                "api_ip_port": 0
                # "type": 2  # 如果不需要该字段，可以注释掉或删除
            }

            unity_data = self.update_data_from_gridLayout(self.ui.gridLayout_unity)
            config_data["unity"] = reorganize_grid_data(unity_data, unity_keys_mapping)

            """
            ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
            -------------------------------------------------------------------------------------------------------------
            """

            # 获取自定义板块显隐的数据
            show_box_data = self.update_data_from_gridLayout(self.ui.gridLayout_show_box, "show_box")
            show_box_json = {}
            for key, value in show_box_data.items():
                checkbox_name = key.split('_QCheckBox')[0]
                show_box_json[checkbox_name] = value

            logging.debug(show_box_json)
            config_data["show_box"] = show_box_json
            
        except Exception as e:
            logging.error(traceback.format_exc())
            self.show_message_box("错误", f"配置项格式有误，请检查配置！\n{e}", QMessageBox.Critical)
            return False

        try:
            with open(config_path, 'w', encoding="utf-8") as config_file:
                json.dump(config_data, config_file, indent=2, ensure_ascii=False)
                config_file.flush()  # 刷新缓冲区，确保写入立即生效

            logging.info("配置数据已成功写入文件！程序将在3秒后重启~")
            self.show_message_box("提示", "配置数据已成功写入文件！程序将在3秒后重启~", QMessageBox.Information, 3000)

            self.restart_application()

            return True
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f"无法写入配置文件！\n{e}")
            self.show_message_box("错误", f"无法写入配置文件！\n{e}", QMessageBox.Critical)
            return False


    '''
        按钮相关的函数
    '''

    # 恢复出厂配置
    def factory(self):
        result = QMessageBox.question(
            None, "确认框", "您确定要恢复出厂配置吗？", QMessageBox.Yes | QMessageBox.No
        )
        if result == QMessageBox.No:
            return

        source_file = 'config.json.bak'
        destination_file = 'config.json'

        try:
            with open(source_file, 'r', encoding="utf-8") as source:
                with open(destination_file, 'w', encoding="utf-8") as destination:
                    destination.write(source.read())
            logging.info("恢复出厂配置成功！")
        except Exception as e:
            logging.error(f"恢复出厂配置失败！\n{e}")
            self.show_message_box("错误", f"恢复出厂配置失败！\n{e}", QMessageBox.Critical)

        # 重载下配置
        self.init_config()


    # 运行
    def run(self):
        if self.running_flag == 1:
            self.show_message_box("提醒", "程序运行中，请勿重复运行，请耐心等待喵~如果卡死或者3分钟都没有运行日志，可以重启重新运行",
                QMessageBox.Information, 3000)
            return
        
        self.running_flag = 1

        self.show_message_box("提示", "3秒后开始运行，运行可能比较缓慢，请耐心等待，如果3分钟都没有运行日志输出，则可能是程序卡死，建议重启~",
            QMessageBox.Information, 3000)

        def delayed_run():
            # 判断当前位于的页面，如果是聊天页，则不跳转到运行页
            if self.stackedWidget_index != 3:
                # 切换到索引为 1 的页面 运行页
                self.ui.stackedWidget.setCurrentIndex(1)

            # 开冲！
            try:
                # self.run_external_command()
                # 连接信号与槽函数，用于接收输出并更新 UI
                # thread.output_ready.connect(self.ui.textBrowser.setText)

                # 连接 output_ready 信号和 update_textbrowser 槽函数
                # thread.output_ready.connect(self.update_textbrowser)

                # 创建线程对象
                self.platform_thread = ExternalCommandThread()
                self.platform_thread.platform = self.platform
                # 启动线程执行 run_external_command()
                self.platform_thread.start()

                # 设置定时器间隔为 300 毫秒
                self.timer.setInterval(300)
                # 每次定时器触发时调用 update_text_browser 函数
                self.timer.timeout.connect(self.update_text_browser)
                # 启动定时器
                self.timer.start()

                self.show_message_box("提示", "开始运行喵~\n不要忘记保存配置~", QMessageBox.Information, 3000)
            except Exception as e:
                logging.error("平台配置出错，程序自爆~\n{e}")
                self.show_message_box("错误", f"平台配置出错，程序自爆~\n{e}", QMessageBox.Critical)
                os._exit(0)

        # 启动定时器，延迟  秒后触发函数执行
        QTimer.singleShot(100, delayed_run)


    # 切换至index页面
    def change_page(self, index):
        self.stackedWidget_index = index
        self.ui.stackedWidget.setCurrentIndex(index)


    # 保存配置
    def on_pushButton_save_clicked(self):
        self.throttled_save()

    # 初始化配置
    def on_pushButton_factory_clicked(self):
        self.throttled_factory()

    # 运行
    def on_pushButton_run_clicked(self):
        self.throttled_run()

    # 切换页面
    def on_pushButton_change_page_clicked(self, index):
        self.throttled_change_page(index)


    # 根据文案索引添加文案
    def copywriting_config_index_add(self):
        try:
            index = int(self.ui.lineEdit_copywriting_config_index.text())

            tmp = {
                "file_path": "",
                "audio_path": "",
                "play_list": [],
                "continuous_play_num": 1,
                "max_play_time": 5.0
            }

            # 追加数据到成员变量
            self.copywriting_config["config"].append(tmp)

            data_json = []
            tmp_json = {
                "label_text": "文案存储路径" + str(index),
                "label_tip": "文案文件存储路径，默认不可编辑。不建议更改。",
                "data": tmp["file_path"],
                "widget_text": "",
                "click_func": "",
                "main_obj_name": "copywriting_config_file_path",
                "index": index
            }
            data_json.append(tmp_json)

            tmp_json = {
                "label_text": "音频存储路径" + str(index),
                "label_tip": "文案音频文件存储路径，默认不可编辑。不建议更改。",
                "data": tmp["audio_path"],
                "widget_text": "",
                "click_func": "",
                "main_obj_name": "copywriting_config_audio_path",
                "index": index
            }
            data_json.append(tmp_json)

            tmp_json = {
                "label_text": "文案列表" + str(index),
                "label_tip": "加载配置文件中配置的文案路径（data/copywriting/）下的所有文件，请勿放入其他非文案文件",
                "data": [],
                "widget_text": "",
                "click_func": "",
                "main_obj_name": "copywriting_config_copywriting_list",
                "index": index
            }
            data_json.append(tmp_json)

            tmp_json = {
                "label_text": "播放列表" + str(index),
                "label_tip": "此处填写需要播放的音频文件全名，填写完毕后点击 保存配置。文件全名从音频列表中复制，换行分隔，请勿随意填写",
                "data": tmp["play_list"],
                "widget_text": "",
                "click_func": "",
                "main_obj_name": "copywriting_config_play_list",
                "index": index
            }
            data_json.append(tmp_json)

            tmp_json = {
                "label_text": "已合成\n音频列表" + str(index),
                "label_tip": "加载配置文件中配置的音频路径（out/copywriting/）下的所有文件，请勿放入其他非音频文件",
                "data": [],
                "widget_text": "",
                "click_func": "",
                "main_obj_name": "copywriting_config_audio_list",
                "index": index
            }
            data_json.append(tmp_json)
            
            tmp_json = {
                "label_text": "连续播放数" + str(index),
                "label_tip": "文案播放列表中连续播放的音频文件个数，如果超过了这个个数就会切换下一个文案列表",
                "data": tmp["continuous_play_num"],
                "widget_text": "",
                "click_func": "",
                "main_obj_name": "copywriting_config_continuous_play_num",
                "index": index
            }
            data_json.append(tmp_json)

            tmp_json = {
                "label_text": "连续播放时间" + str(index),
                "label_tip": "文案播放列表中连续播放音频的时长，如果超过了这个时长就会切换下一个文案列表",
                "data": tmp["max_play_time"],
                "widget_text": "",
                "click_func": "",
                "main_obj_name": "copywriting_config_max_play_time",
                "index": index
            }
            data_json.append(tmp_json)
            widgets = self.create_widgets_from_json(data_json)

            # 动态添加widget到对应的gridLayout
            row = 0
            for i in range(0, len(widgets), 2):
                self.ui.gridLayout_copywriting_config.addWidget(widgets[i], row, 0)
                self.ui.gridLayout_copywriting_config.addWidget(widgets[i + 1], row, 1)
                row += 1
            
            self.copywriting_refresh_list()
        except Exception as e:
            logging.error(traceback.format_exc())


    # 根据文案索引删除文案
    def copywriting_config_index_del(self):
        try:
            index = int(self.ui.lineEdit_copywriting_config_index.text())

            # 删除指定索引的数据
            if 0 <= index < len(self.copywriting_config["config"]):
                del self.copywriting_config["config"][index]

            self.copywriting_refresh_list()
        except Exception as e:
            logging.error(traceback.format_exc())


    # 加载文案
    def copywriting_select(self):
        select_file_path = self.ui.lineEdit_copywriting_select.text()
        if "" == select_file_path:
            logging.warning(f"请输入 文案路径喵~")
            self.show_message_box("警告", "请输入 文案路径喵~", QMessageBox.Critical, 3000)
            return
        
        # 传入完整文件路径 绝对或相对
        logging.info(f"准备加载 文件：[{select_file_path}]")
        new_file_path = os.path.join(select_file_path)

        content = common.read_file_return_content(new_file_path)
        if content is None:
            logging.error(f"读取失败！请检测配置、文件路径、文件名")
            self.show_message_box("错误", "读取失败！请检测配置、文件路径、文件名", QMessageBox.Critical)
            return
        
        self.ui.textEdit_copywriting_edit.setText(content)

        logging.info(f"成功加载文案：{select_file_path}")
        self.show_message_box("提示", f"成功加载文案：{select_file_path}", QMessageBox.Information, 3000)

        self.copywriting_refresh_list()


    def on_pushButton_copywriting_config_index_add_clicked(self):
        self.throttled_copywriting_config_index_add()

    def on_pushButton_copywriting_config_index_del_clicked(self):
        self.throttled_copywriting_config_index_del()


    # 加载文案按钮
    def on_pushButton_copywriting_select_clicked(self):
        self.throttled_copywriting_select()
    

    # 刷新列表
    def copywriting_refresh_list(self):
        try:
            while self.ui.gridLayout_copywriting_config.count():
                item = self.ui.gridLayout_copywriting_config.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

            data_json = []
            for index, tmp in enumerate(self.copywriting_config["config"]):
                tmp_json = {
                    "label_text": "文案存储路径" + str(index),
                    "label_tip": "文案文件存储路径，默认不可编辑。不建议更改。",
                    "data": tmp["file_path"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_file_path",
                    "index": index
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "音频存储路径" + str(index),
                    "label_tip": "文案音频文件存储路径，默认不可编辑。不建议更改。",
                    "data": tmp["audio_path"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_audio_path",
                    "index": index
                }
                data_json.append(tmp_json)

                tmp_str = ""
                copywriting_file_names = self.get_dir_txt_filename(self.copywriting_config["config"][index]['file_path'])
                for tmp_copywriting_file_name in copywriting_file_names:
                    tmp_str = tmp_str + tmp_copywriting_file_name + "\n"
                tmp_json = {
                    "label_text": "文案列表" + str(index),
                    "label_tip": "加载配置文件中配置的文案路径（data/copywriting/）下的所有文件，请勿放入其他非文案文件",
                    "data": [tmp_str],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_copywriting_list",
                    "index": index
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "播放列表" + str(index),
                    "label_tip": "此处填写需要播放的音频文件全名，填写完毕后点击 保存配置。文件全名从音频列表中复制，换行分隔，请勿随意填写",
                    "data": tmp["play_list"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_play_list",
                    "index": index
                }
                data_json.append(tmp_json)

                tmp_str = ""
                copywriting_audio_file_names = self.get_dir_audio_filename(self.copywriting_config["config"][index]['audio_path'])
                for tmp_copywriting_audio_file_name in copywriting_audio_file_names:
                    tmp_str = tmp_str + tmp_copywriting_audio_file_name + "\n"
                tmp_json = {
                    "label_text": "已合成\n音频列表" + str(index),
                    "label_tip": "加载配置文件中配置的音频路径（out/copywriting/）下的所有文件，请勿放入其他非音频文件",
                    "data": [tmp_str],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_audio_list",
                    "index": index
                }
                data_json.append(tmp_json)
                
                tmp_json = {
                    "label_text": "连续播放数" + str(index),
                    "label_tip": "文案播放列表中连续播放的音频文件个数，如果超过了这个个数就会切换下一个文案列表",
                    "data": tmp["continuous_play_num"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_continuous_play_num",
                    "index": index
                }
                data_json.append(tmp_json)

                tmp_json = {
                    "label_text": "连续播放时间" + str(index),
                    "label_tip": "文案播放列表中连续播放音频的时长，如果超过了这个时长就会切换下一个文案列表",
                    "data": tmp["max_play_time"],
                    "widget_text": "",
                    "click_func": "",
                    "main_obj_name": "copywriting_config_max_play_time",
                    "index": index
                }
                data_json.append(tmp_json)
            widgets = self.create_widgets_from_json(data_json)

            # 动态添加widget到对应的gridLayout
            row = 0
            for i in range(0, len(widgets), 2):
                self.ui.gridLayout_copywriting_config.addWidget(widgets[i], row, 0)
                self.ui.gridLayout_copywriting_config.addWidget(widgets[i + 1], row, 1)
                row += 1

            logging.info("刷新文件列表")
        except Exception as e:
            logging.error(traceback.format_exc())
            self.show_message_box("错误", f"刷新失败！{e}", QMessageBox.Critical)


    # 刷新列表按钮
    def on_pushButton_copywriting_refresh_list_clicked(self):
        self.throttled_copywriting_refresh_list()


    # 保存文案
    def copywriting_save(self):
        content = self.ui.textEdit_copywriting_edit.toPlainText()
        select_file_path = self.ui.lineEdit_copywriting_select.text()
        if "" == select_file_path:
            logging.warning(f"请输入 文案路径喵~")
            return
        
        new_file_path = os.path.join(select_file_path)
        if True == common.write_content_to_file(new_file_path, content):
            self.show_message_box("提示", "保存成功~", QMessageBox.Information, 3000)
        else:
            self.show_message_box("错误", "保存失败！请查看日志排查问题", QMessageBox.Critical)


    # 保存文案按钮
    def on_pushButton_copywriting_save_clicked(self):
        self.throttled_copywriting_save()
    

    # 合成音频 正经版
    async def copywriting_synthetic_audio_main(self):
        select_file_path = self.ui.lineEdit_copywriting_select.text()

        # 将一个文件路径的字符串切分成路径和文件名
        folder_path, file_name = common.split_path_and_filename(select_file_path)

        flag = 0

        # 判断文件是哪个路径的
        for copywriting_config in config.get("copywriting", "config"):
            if folder_path == copywriting_config["file_path"]:
                folder_path = copywriting_config["audio_path"]
                flag = 1
                break

        if flag == 0:
            logging.error(f"文件路径与配置不匹配，将默认输出到同路径")
            self.show_message_box("提示", f"文件路径与配置不匹配，将默认输出到同路径", QMessageBox.Information, 3000)

        ret = await audio.copywriting_synthesis_audio(select_file_path, folder_path)
        if ret is None:
            logging.error(f"合成失败！请排查原因")
            self.show_message_box("错误", "合成失败！请排查原因", QMessageBox.Critical)
        else:
            logging.info(f"合成成功，文件输出到：{ret}")
            self.show_message_box("提示", f"合成成功，文件输出到：{ret}", QMessageBox.Information, 3000)

            # 刷新文案和音频列表
            self.copywriting_refresh_list()


    # 合成音频
    def copywriting_synthetic_audio(self):
        if self.running_flag != 1:
            self.show_message_box("提醒", "请先点击“运行”，然后再进行合成操作",
                QMessageBox.Information, 3000)
            return
        
        result = QMessageBox.question(
            None, "确认框", "开始合成后请勿做其他操作，耐心等待合成完成，您确定开始吗？", QMessageBox.Yes | QMessageBox.No
        )
        if result == QMessageBox.No:
            return
        
        asyncio.run(self.copywriting_synthetic_audio_main())


    
    # 合成音频按钮
    def on_pushButton_copywriting_synthetic_audio_clicked(self):
        self.throttled_copywriting_synthetic_audio()


    # 循环播放
    def copywriting_loop_play(self):
        if self.running_flag != 1:
            self.show_message_box("提醒", "请先点击“运行”，然后再进行播放",
                QMessageBox.Information, 3000)
            return
        
        self.show_message_box("提示", "3秒后开始循环播放文案~", QMessageBox.Information, 3000)
        audio.unpause_copywriting_play()


    # 循环播放按钮
    def on_pushButton_copywriting_loop_play_clicked(self):
        self.throttled_copywriting_loop_play()
    

    # 暂停播放
    def copywriting_pause_play(self):
        if self.running_flag != 1:
            self.show_message_box("提醒", "请先点击“运行”，然后再进行暂停",
                QMessageBox.Information, 3000)
            return
        
        audio.pause_copywriting_play()
        self.show_message_box("提示", "暂停文案完毕~", QMessageBox.Information, 3000)


    # 暂停播放按钮
    def on_pushButton_copywriting_pause_play_clicked(self):
        self.throttled_copywriting_pause_play()


    '''
        聊天页相关的函数
    '''

    # 发送 聊天框内容
    def talk_chat_box_send(self):
        global my_handle
        
        if self.running_flag != 1:
            self.show_message_box("提醒", "请先点击“运行”，然后再进行聊天",
                QMessageBox.Information, 3000)
            return
        
        if my_handle is None:
            from utils.my_handle import My_handle
        
            my_handle = My_handle(config_path)
            if my_handle is None:
                logging.error("程序初始化失败！")
                self.show_message_box("错误", "程序初始化失败！请排查原因", QMessageBox.Critical)
                os._exit(0)
        
        # 获取用户名和文本内容
        user_name = self.ui.lineEdit_talk_username.text()
        content = self.ui.textEdit_talk_chat_box.toPlainText()
        
        # 清空聊天框
        self.ui.textEdit_talk_chat_box.setText("")

        data = {
            "username": user_name,
            "content": content
        }
        
        # 正义执行
        my_handle.process_data(data, "comment")
    

    # 发送 聊天框内容 进行复读
    def talk_chat_box_reread(self):
        global my_handle
        
        if self.running_flag != 1:
            self.show_message_box("提醒", "请先点击“运行”，然后再进行复读",
                QMessageBox.Information, 3000)
            return
        
        if my_handle is None:
            from utils.my_handle import My_handle
        
            my_handle = My_handle(config_path)
            if my_handle is None:
                logging.error("程序初始化失败！")
                self.show_message_box("错误", "程序初始化失败！请排查原因", QMessageBox.Critical)
                os._exit(0)
        
        # 获取用户名和文本内容
        user_name = self.ui.lineEdit_talk_username.text()
        content = self.ui.textEdit_talk_chat_box.toPlainText()
        
        # 清空聊天框
        self.ui.textEdit_talk_chat_box.setText("")

        data = {
            "user_name": user_name,
            "content": content
        }
        
        # 正义执行 直接复读
        my_handle.reread_handle(data)


    # 事件过滤器会监听 QTextEdit 内的按键事件，当按下回车键时，会调用 eventFilter 方法，然后执行 talk_handleEnterKey 方法中的自定义处理代码。
    def eventFilter(self, source, event):
        # print(event.type())
        if (event.type() == QEvent.KeyPress and
            event.key() == Qt.Key_Return and
            source is self.ui.textEdit_talk_chat_box):
            # 在这里执行回车按键事件的处理代码
            self.talk_handleEnterKey()
            return True
        return super().eventFilter(source, event)


    def talk_handleEnterKey(self):
        # 发送 聊天框内容
        self.talk_chat_box_send()
 
    
    def on_pushButton_talk_chat_box_send_clicked(self):
        self.throttled_talk_chat_box_send()
    

    def on_pushButton_talk_chat_box_reread_clicked(self):
        self.throttled_talk_chat_box_reread()


    '''
        餐单栏相关的函数
    '''
    def openBrowser_github(self):
        url = QUrl("https://github.com/Ikaros-521/AI-Vtuber")  # 指定要打开的网页地址
        QDesktopServices.openUrl(url)

    def openBrowser_video(self):
        url = QUrl("https://space.bilibili.com/3709626/channel/collectiondetail?sid=1422512")  # 指定要打开的网页地址
        QDesktopServices.openUrl(url)

    def openBrowser_online_doc(self):
        url = QUrl("https://luna.docs.ie.cx")  # 指定要打开的网页地址
        QDesktopServices.openUrl(url)

    # 跳转到官方Q群
    def openBrowser_official_qq_group(self):
        url = QUrl("https://qm.qq.com/cgi-bin/qm/qr?k=sYTkGUFactreB4MJZx-aPeWvYtpWaJYG&jump_from=webapi&authKey=NVHJc5hDHOk0ynysKZ8BqIpnLxYfsJWnCb0vH02xBwE2BYP8UPSce7qJ4EPa6wGu")  # 指定要打开的网页地址
        QDesktopServices.openUrl(url)

    # 弹出关于窗口
    def alert_about(self):
        about_str = """
项目地址：https://github.com/Ikaros-521/AI-Vtuber
视频教程：https://space.bilibili.com/3709626/channel/collectiondetail?sid=1422512
在线文档：https://luna.docs.ie.cx

项目完全免费，如果您是在第三方平台购买了本项目，均为盗版，请及时止损（可怜的娃呀~）
        """
        self.show_message_box("关于", about_str, QMessageBox.Information, 180000)

    def exit_soft(self):
        os._exit(0)

    '''
        UI操作的函数
    '''
    # 自定义板块显隐
    def show_box_clicked(self, status, text):
        box_obj_name = "groupBox_" + text
        # 使用getattr()函数来从self.ui对象中获取属性。getattr()函数接收三个参数：对象，属性名（字符串），和默认值（可选）。
        # 如果属性存在，则返回对应的属性值（在这里是一个groupBox对象），否则返回默认值（在这里是None）。
        # 这样就可以根据字符串构造变量名，并获取对应的groupBox对象。
        box_widget = getattr(self.ui, box_obj_name, None)
        if box_widget is not None:
            box_widget.setVisible(status)


    # 聊天类型改变 加载显隐不同groupBox
    def oncomboBox_chat_type_IndexChanged(self, index):
        # 各index对应的groupbox的显隐值
        visibility_map = {
            0: (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            1: (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            2: (1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            3: (0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            4: (0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            5: (0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            6: (1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0),
            7: (0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0),
            8: (0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0),
            9: (0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
            10: (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0),
            11: (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0),
            12: (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0),
            13: (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0),
            14: (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1),
        }

        visibility_values = visibility_map.get(index, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))

        self.ui.groupBox_openai.setVisible(visibility_values[0])
        self.ui.groupBox_chatgpt.setVisible(visibility_values[1])
        self.ui.groupBox_header.setVisible(visibility_values[2])
        self.ui.groupBox_claude.setVisible(visibility_values[3])
        self.ui.groupBox_claude2.setVisible(visibility_values[4])
        self.ui.groupBox_chatglm.setVisible(visibility_values[5])
        self.ui.groupBox_chat_with_file.setVisible(visibility_values[6])
        self.ui.groupBox_chatterbot.setVisible(visibility_values[7])
        self.ui.groupBox_text_generation_webui.setVisible(visibility_values[8])
        self.ui.groupBox_sparkdesk.setVisible(visibility_values[9])
        self.ui.groupBox_langchain_chatglm.setVisible(visibility_values[10])
        self.ui.groupBox_zhipu.setVisible(visibility_values[11])
        self.ui.groupBox_bard.setVisible(visibility_values[12])
        self.ui.groupBox_yiyan.setVisible(visibility_values[13])
        self.ui.groupBox_tongyi.setVisible(visibility_values[14])

    
    # 语音合成类型改变 加载显隐不同groupBox
    # 当你新增TTS时，你需要同步修改此处的TTS配置的显隐
    def oncomboBox_audio_synthesis_type_IndexChanged(self, index):
        # 各index对应的groupbox的显隐值
        visibility_map = {
            0: (1, 0, 0, 0, 0, 0, 0, 0),
            1: (0, 1, 0, 0, 0, 0, 0, 0),
            2: (0, 0, 1, 0, 0, 0, 0, 0),
            3: (0, 0, 0, 1, 0, 0, 0, 0),
            4: (0, 0, 0, 0, 1, 0, 0, 0),
            5: (0, 0, 0, 0, 0, 1, 0, 0),
            6: (0, 0, 0, 0, 0, 0, 1, 0),
            7: (0, 0, 0, 0, 0, 0, 0, 1)
        }

        visibility_values = visibility_map.get(index, (0, 0, 0, 0, 0, 0, 0, 0))

        self.ui.groupBox_edge_tts.setVisible(visibility_values[0])
        self.ui.groupBox_vits.setVisible(visibility_values[1])
        self.ui.groupBox_vits_fast.setVisible(visibility_values[2])
        self.ui.groupBox_elevenlabs.setVisible(visibility_values[3])
        self.ui.groupBox_genshinvoice_top.setVisible(visibility_values[4])
        self.ui.groupBox_bark_gui.setVisible(visibility_values[5])
        self.ui.groupBox_vall_e_x.setVisible(visibility_values[6])
        self.ui.groupBox_openai_tts.setVisible(visibility_values[7])


    # 语音识别类型改变 加载显隐不同groupBox
    def oncomboBox_talk_type_IndexChanged(self, index):
        # 各index对应的groupbox的显隐值
        visibility_map = {
            0: (1, 0),
            1: (0, 1)
        }

        visibility_values = visibility_map.get(index, (0, 0))

        self.ui.groupBox_talk_baidu.setVisible(visibility_values[0])
        self.ui.groupBox_talk_google.setVisible(visibility_values[1])


    # 输出文本到运行页的textbrowser
    # def output_to_textbrowser(self, content):
    #     max_content_len = 10000

    #     text = self.ui.textBrowser.toPlainText() + content  # 将新内容添加到已有内容后面
    #     if len(text) > max_content_len:
    #         text = text[-max_content_len:]  # 保留最后一万个字符，截断超出部分
    #     self.ui.textBrowser.setText(text)

    
    # def update_textbrowser(self, output_text):
    #     cursor = self.ui.textBrowser.textCursor()
    #     cursor.movePosition(QTextCursor.End)
    #     cursor.insertText(output_text)
    #     self.ui.textBrowser.setTextCursor(cursor)
    #     self.ui.textBrowser.ensureCursorVisible()

    
    # 获取一个文件最后num_lines行数据
    def load_last_lines(self, file_path, num_lines=1000):
        lines = []
        with open(file_path, 'r', encoding="utf-8") as file:
            # 将文件内容逐行读取到列表中
            lines = file.readlines()

        # 只保留最后1000行文本
        last_lines = lines[-num_lines:]

        # 倒序排列文本行
        last_lines.reverse()

        return last_lines


    # 清空text_browser，显示文件内的数据
    def update_text_browser(self):
        global file_path

        # 记录当前的滚动位置
        scroll_position = self.ui.textBrowser.verticalScrollBar().value()
        scroll_position_talk_log = self.ui.textBrowser_talk_log.verticalScrollBar().value()

        # print(f"scroll_position={scroll_position}, scroll_position_talk_log={scroll_position_talk_log}")

        # 加载文件的最后1000行文本
        last_lines = self.load_last_lines(file_path)

        # 获取当前文本光标
        cursor = self.ui.textBrowser.textCursor()
        cursor_talk_log = self.ui.textBrowser_talk_log.textCursor()

        # 获取当前选中的文本
        selected_text = cursor.selectedText()
        selected_text_talk_log = cursor_talk_log.selectedText()

        # 判断是否有选中的文本
        has_selection = len(selected_text) > 0
        has_selection_talk_log = len(selected_text_talk_log) > 0

        # 清空 textBrowser
        self.ui.textBrowser.clear()
        self.ui.textBrowser_talk_log.clear()

        # 设置文本浏览器打开外部链接功能
        self.ui.textBrowser.setOpenExternalLinks(True)
        self.ui.textBrowser_talk_log.setOpenExternalLinks(True)

        # 将文本逐行添加到 textBrowser 中
        for line in last_lines:
            self.ui.textBrowser.insertPlainText(line)
            self.ui.textBrowser_talk_log.insertPlainText(line)

        # 恢复滚动位置
        if not has_selection:
            self.ui.textBrowser.verticalScrollBar().setValue(scroll_position)

        if not has_selection_talk_log:
            self.ui.textBrowser_talk_log.verticalScrollBar().setValue(scroll_position_talk_log)


    '''
        通用的函数
    '''
    # 获取本地音频文件夹内所有的txt文件名
    def get_dir_txt_filename(self, txt_path):
        try:
            # 使用 os.walk 遍历文件夹及其子文件夹
            txt_files = []
            for root, dirs, files in os.walk(txt_path):
                for file in files:
                    if file.endswith(('.txt')):
                        txt_files.append(os.path.join(root, file))

            # 提取文件名
            file_names = [os.path.basename(file) for file in txt_files]
            # 保留子文件夹路径
            # file_names = [os.path.relpath(file, txt_path) for file in txt_files]

            logging.debug("获取到文案文件名列表如下：")
            logging.debug(file_names)

            return file_names
        except Exception as e:
            logging.error(traceback.format_exc())
            return None
        

    # 获取本地音频文件夹内所有的音频文件名
    def get_dir_audio_filename(self, audio_path):
        try:
            # 使用 os.walk 遍历文件夹及其子文件夹
            audio_files = []
            for root, dirs, files in os.walk(audio_path):
                for file in files:
                    if file.endswith(('.MP3', '.mp3', '.WAV', '.wav', '.flac', '.aac', '.ogg', '.m4a')):
                        audio_files.append(os.path.join(root, file))

            # 提取文件名
            audio_file_names = [os.path.basename(file) for file in audio_files]
            # 保留子文件夹路径
            # file_names = [os.path.relpath(file, song_path) for file in audio_audio_files]

            logging.debug("获取到本地文案音频文件名列表如下：")
            logging.debug(audio_file_names)

            return audio_file_names
        except Exception as e:
            logging.error(traceback.format_exc())
            return None


    def restart_application(self):
        QApplication.exit()  # Exit the current application instance
        python = sys.executable
        os.execl(python, python, *sys.argv)  # Start a new instance of the application


    # 字符串是否只由字母或数字组成
    def is_alpha_numeric(self, string):
        pattern = r'^[a-zA-Z0-9]+$'
        return re.match(pattern, string) is not None


    # 显示提示弹窗框,自动关闭时间（单位：毫秒）
    def show_message_box(self, title, text, icon=QMessageBox.Information, timeout_ms=60 * 1000):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setIcon(icon)

        def close_message_box():
            msg_box.close()

        QTimer.singleShot(timeout_ms, close_message_box)

        msg_box.exec_()


    # 套娃运行喵（会卡死）
    def run_external_command(self):
        module = importlib.import_module(self.platform)
        platform_process = subprocess.Popen([sys.executable, '-c', 'import {}'.format(module.__name__)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                            args=(AI_VTB.terminate_event,))
        output, _ = platform_process.communicate()
        output_text = output.decode("utf-8")  # 将字节流解码为字符串
        self.output_to_textbrowser(output_text)

        # 调用 start_server() 并将输出追加到 textbrowser
        start_server_output = module.start_server()  # 调用 start_server() 函数并获取输出
        output_text += start_server_output
        

    # 节流函数，单位时间内只执行一次函数
    def throttle(self, func, delay):
        last_executed = 0

        def throttled(*args, **kwargs):
            nonlocal last_executed
            current_time = time.time()
            if current_time - last_executed > delay:
                last_executed = current_time
                func(*args, **kwargs)

        return throttled   
    

# 执行额外命令的线程
class ExternalCommandThread(QThread):
    output_ready = pyqtSignal(str)

    def __init__(self, platform=None):
        super().__init__()
        self.platform = platform

    def run(self):
        if self.platform is None:
            # 处理没有传递 platform 的情况
            self.output_ready.emit("没有传入platform，取名为寄！")
            return

        logging.debug(f"platform={self.platform}")

        module = importlib.import_module(self.platform)
        AI_VTB.platform_process = subprocess.Popen([sys.executable, '-c', 'import {}'.format(module.__name__)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, _ = AI_VTB.platform_process.communicate()
        # logging.debug(output)
        # output_text = output.decode("utf-8")  # 将字节流解码为字符串

        # 调用 start_server() 并将输出追加到 textbrowser
        start_server_output = module.start_server()  # 调用 start_server() 函数并获取输出
        # output_text += start_server_output


# web服务线程
class WebServerThread(QThread):
    def run(self):
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", web_server_port), Handler) as httpd:
            logging.info(f"Web运行在端口：{web_server_port}")
            logging.info(f"可以直接访问Live2D页， http://127.0.0.1:{web_server_port}/Live2D/")
            httpd.serve_forever()


# 退出程序
def exit_handler(signum, frame):
    print("收到信号:", signum)

    os._exit(0)


# 程序入口
if __name__ == '__main__':
    common = Common()
    my_handle = None

    if getattr(sys, 'frozen', False):
        # 当前是打包后的可执行文件
        bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
        file_relative_path = os.path.dirname(os.path.abspath(bundle_dir))
    else:
        # 当前是源代码
        file_relative_path = os.path.dirname(os.path.abspath(__file__))

    # logging.info(file_relative_path)

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

    web_server_port = 12345

    # 本地测试时候的日志设置
    '''
    # 日志格式
    log_format = '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
    # 日志文件路径
    file_path = os.path.join(file_relative_path, 'log/log.txt')

    # 自定义控制台输出类
    class ColoredStreamHandler(logging.StreamHandler):
        """
        自定义 StreamHandler 类，用于在控制台中为不同级别的日志信息设置不同的颜色
        """
        def __init__(self):
            super().__init__()
            self._colors = {
                logging.DEBUG: '\033[1;34m',    # 蓝色
                logging.INFO: '\033[1;37m',     # 白色
                logging.WARNING: '\033[1;33m',  # 黄色
                logging.ERROR: '\033[1;31m',    # 红色
                logging.CRITICAL: '\033[1;35m'  # 紫色
            }

        def emit(self, record):
            # 根据日志级别设置颜色
            color = self._colors.get(record.levelno, '\033[0m')  # 默认为关闭颜色设置
            # 设置日志输出格式和颜色
            self.stream.write(color)
            super().emit(record)
            self.stream.write('\033[0m')

    # 创建 logger 对象并设置日志级别
    logger = logging.getLogger(__name__)
    logging.setLevel(logging.DEBUG)

    # 创建 FileHandler 对象和 StreamHandler 对象并设置日志级别
    fh = logging.FileHandler(file_path, encoding='utf-8', mode='a+')
    fh.setLevel(logging.DEBUG)
    ch = ColoredStreamHandler()
    ch.setLevel(logging.DEBUG)

    # 创建 Formatter 对象并设置日志输出格式
    formatter = logging.Formatter(log_format)
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # 将 FileHandler 对象和 ColoredStreamHandler 对象添加到 logger 对象中
    logging.addHandler(fh)
    logging.addHandler(ch)
    '''


    logging.debug("配置文件路径=" + str(config_path))

    # 实例化配置类
    config = Config(config_path)

    try:
        if config.get("live2d", "enable"):
            web_server_port = int(config.get("live2d", "port"))
            # 创建 web服务线程
            web_server_thread = WebServerThread()
            # 运行 web服务线程
            web_server_thread.start()
    except Exception as e:
        logging.error(traceback.format_exc())
        os._exit(0)

    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)

    e = AI_VTB()

    sys.exit(e.app.exec())
    
