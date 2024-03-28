# -*- coding: UTF-8 -*-
"""
@Project : AI-Vtuber 
@File    : claude_model.py
@Author  : HildaM
@Email   : Hilda_quan@163.com
@Date    : 2023/06/17 下午 4:44 
@Description : 本地化向量数据库，实现langchain_pdf
"""
import logging
from langchain.document_loaders import PyPDFLoader

from utils.chat_with_file.chat_mode.chat_model import Chat_model

from utils.gpt_model.gpt import GPT_MODEL
from utils.my_handle import My_handle


# 由于similarity_search返回的数据不是标准的json格式，不能用过python格式化，所以只能用字符串操作获取数据
# 返回的数据很标准，可以很方便获取content信息
def get_content(data: str):
    prefix = "{'content': "
    suffix = ", 'chunk'"

    start = data.find(prefix)
    end = data.find(suffix)
    return data[start:end]


class Claude_mode(Chat_model):
    pdf_loader = PyPDFLoader
    local_db = None
    claude = None

    def __init__(self, data):
        super(Claude_mode, self).__init__(data)

        logging.info(f"本地数据文件路径：{self.data_path}")

        # 加载pdf并生成向量数据库
        self.load_zip_as_db(self.data_path, self.pdf_loader,
                            self.chunk_size,self.chunk_overlap)
        # 初始化claude客户端
        self.claude = GPT_MODEL.get("claude")

    def load_zip_as_db(self, zip_file_path,
                       pdf_loader,
                       chunk_size=300,
                       chunk_overlap=20):
        from utils.chat_with_file.vector_store.faiss import create_faiss_index_from_zip

        if chunk_overlap >= chunk_size:
            logging.error("输入的chunk_overlap大于chunk_size. 为了避免创建失败，将会修正chunk_overlap为chunk_size的十分之一")
            chunk_overlap = round(chunk_size / 10)
        if zip_file_path is None:
            logging.error("zip文件路径为空. 向量数据库构建失败.请重新启动")
            exit(-1)

        self.local_db = create_faiss_index_from_zip(
            zip_file_path=zip_file_path,
            embedding_model_name=self.local_vector_embedding_model,
            pdf_loader=pdf_loader,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        logging.info("成功创建向量知识库!")

    # 调用本地向量数据库，获取关联信息
    def get_local_database_data(self, message):
        logging.info(f"开始从本地向量数据库中查询有关”{message}“的信息........")

        contents = []
        docs = self.local_db.similarity_search(message, k=self.local_max_query)
        for i in range(self.local_max_query):
            # 预处理分块
            content = docs[i].page_content.replace('\n', ' ')
            logging.info(f"No.{i} 相关联信息: {content}")
            data = get_content(content)
            # 更新contents
            contents.append(data)

        logging.info("从本地向量数据库查询到的相关信息: {}".format(contents))
        if len(contents) == 0 or contents is None:
            return
        related_data = "\n---\n".join(contents) + "\n---\n"
        return related_data

    def get_model_resp(self, question=""):
        related_data = self.get_local_database_data(question)
        if related_data is None or len(related_data) <= 0:
            content = question
        else:
            content = related_data + "\n" + self.question_prompt + " question: " + question

        resp = self.claude.get_resp(content)
        return resp


if __name__ == '__main__':
    my_handle = My_handle("config.json")
    if my_handle is None:
        print("程序初始化失败！")
        exit(0)