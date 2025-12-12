# LCAI+项目上手使用说明

## 1. 安装依赖
```pip install -r requirements.txt```

## 2. 启动服务
```python app/main.py```

## 3. 接口测试（Swagger 文档）
服务启动后访问：<http://localhost:8000/docs>，可直接调试以下接口：
- GET /health：健康检查
- POST /api/v1/lcai/invoke：同步调用 LCAI
- POST /api/v1/lcai/stream：流式调用 LCAI

或访问下述网址：
- 健康检查： <http://localhost:8000/health>

## 4.示例请求
***POST:*** <http://localhost:8000/api/v1/lcai/invoke>
```json
{
    "user_input": "低代码平台有哪些功能？",
    "meta": {
        "chatId": "123",
        "userId": "563504",
        "lcUserName": "丁仁杰",
        "origin":"https://eplatdev.baocloud.cn"
    },
    "stream": false
}
```
