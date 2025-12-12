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