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
***POST:*** <http://localhost:8000/api/v1/lcai/stream>
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
***POST:*** <http://localhost:8000/api/v1/lcai/confirm>
```json
{
    "user_input": "2",
    "session_id":"a0-123"
}
```

## 5.代表性提示词
### 5.1 复合需求
    "user_input": "请搭建一个会议预定应用，其中需要两个表单：1.会议室信息，需要有会议室名称，楼层，房间号，最大容纳人数等字段；2.会议室预订信息，需要有预订时间段等字段"
### 5.2 应用搭建（模板搜索）
    "user_input": "请搭建一个会议预定应用"