from fastapi import status
from fastapi.responses import JSONResponse
import json
from datetime import datetime


class DateTimeEncoder(json.JSONEncoder):
    """支持datetime序列化的JSON编码器"""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            # 将datetime转换为ISO 8601格式字符串
            return obj.isoformat()
        # 其他类型的对象使用默认的序列化方法
        return super().default(obj)


def datetime_handler(obj):
    """处理datetime对象的函数"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def success_response(data=None, message=None, status_code=status.HTTP_200_OK):
    """
    统一的成功响应格式
    
    Args:
        data: 返回的数据内容
        message: 成功描述信息
        status_code: HTTP状态码
        
    Returns:
        JSONResponse: FastAPI响应对象
    """
    # 手动序列化带有datetime的数据
    content = {
        'success': True,
        'message': message,
        'results': data
    }
    
    # 使用自定义编码器进行序列化
    content_json = json.dumps(content, default=datetime_handler)
    
    return JSONResponse(
        status_code=status_code,
        content=json.loads(content_json)  # 将JSON字符串转回Python对象
    )


def error_response(message, status_code=status.HTTP_400_BAD_REQUEST):
    """
    统一的错误响应格式
    
    Args:
        message: 错误描述信息
        status_code: HTTP状态码
        
    Returns:
        JSONResponse: FastAPI响应对象
    """
    # 手动序列化内容
    content = {
        'success': False,
        'message': message
    }
    
    # 使用自定义编码器进行序列化
    content_json = json.dumps(content, default=datetime_handler)
    
    return JSONResponse(
        status_code=status_code,
        content=json.loads(content_json)  # 将JSON字符串转回Python对象
    ) 