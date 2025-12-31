# 2. 工具函数：推送中间消息（更新状态）
from app.config.settings import settings


def get_app_run_url(origin: str, workspace_id: str, app_id: str) -> str:
    if "localhost" in origin:
        return f"{settings.CODE_DISPLAY_ORIGIN}/#/list?workspaceid={workspace_id}&id={app_id}"
    else:
        return f"{origin}/code-display/#/list?workspaceid={workspace_id}&id={app_id}"
