import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import *

# 加载参数
load_dotenv()
api_key = os.getenv("API_KEY_CHAT")
base_url = os.getenv("BASE_URL")
print('*'*50)
print("api_key:",api_key)
print("base_url:",base_url) #https://ds.baocloud.cn/xin3plat/api/v1
print('*'*50)

# 记忆
msg = [
    SystemMessage(content='你是优秀的低代码平台助理，名字叫做低代码助手小丁，需要根据提供的知识库信息友好准确地回答用户的提问。\n请围绕知识库所示的低代码平台功能进行回答，不要回答不相关的问题。\n请以标准的markdown语法回复，切记不要回复图片。'),
    HumanMessage(content='你叫什么名字？')
]

# 非流式传输调用
llm = ChatOpenAI(api_key=api_key, base_url=base_url)
response = llm.invoke(msg)
print(response)



