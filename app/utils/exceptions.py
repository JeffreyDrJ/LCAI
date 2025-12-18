class BaseLCAIException(Exception):
    """LCAI项目基础异常类（所有自定义异常的父类）"""
    def __init__(self, message: str, original_exception: Exception = None):
        self.message = message
        self.original_exception = original_exception  # 保留原始异常（便于排查）
        super().__init__(self.message)

    def __str__(self):
        if self.original_exception:
            return f"{self.message} | 原始异常：{str(self.original_exception)}"
        return self.message

class DSPlatformError(Exception):
    """宝武DS平台调用异常"""
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(self.message)

class FormStorageError(Exception):
    """表单保存API调用异常"""
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(self.message)

class IntentRecognitionError(Exception):
    """意图识别异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class AppnameRecognitionError(Exception):
    """意图识别异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class AppTemplateApiError(BaseLCAIException):
    """应用模板查询API异常（S_BE_LA_18接口调用专用）"""

    # 可扩展：添加API相关的自定义属性（如状态码、请求ID）
    def __init__(self, message: str, api_code: int = None, request_id: str = None,
                 original_exception: Exception = None):
        self.api_code = api_code  # API返回的错误码
        self.request_id = request_id  # API请求ID（便于第三方排查）
        super().__init__(message, original_exception)

    def __str__(self):
        base_str = super().__str__()
        if self.api_code:
            base_str += f" | API错误码：{self.api_code}"
        if self.request_id:
            base_str += f" | 请求ID：{self.request_id}"
        return base_str

class AppGenerateError(Exception):
    """应用生成异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
