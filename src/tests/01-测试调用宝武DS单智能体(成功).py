import os
from dotenv import load_dotenv
from langchain_openai import *

# 加载参数
load_dotenv()
api_key = os.getenv("API_KEY_CHAT")
base_url = os.getenv("BASE_URL")
print('*'*50)
print("api_key:",api_key)
print("base_url:",base_url) #https://ds.baocloud.cn/xin3plat/api/v1
print('*'*50)

# 非流式传输调用
llm = ChatOpenAI(api_key=api_key, base_url=base_url)
response = llm.invoke('低代码有哪些功能？')
print(response)



