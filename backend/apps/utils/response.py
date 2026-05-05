"""
统一响应格式工具
响应格式: {code: 200, msg: "", data: {}}
"""
from rest_framework.response import Response
from rest_framework import status


class APIResponse:
    """统一API响应"""
    
    # 成功状态码
    SUCCESS = 200
    CREATED = 201
    NO_CONTENT = 204
    
    # 错误状态码
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    SERVER_ERROR = 500
    
    @staticmethod
    def success(data=None, msg='操作成功', code=200):
        """成功响应"""
        return Response({
            'code': code,
            'msg': msg,
            'data': data if data is not None else {}
        }, status=status.HTTP_200_OK)
    
    @staticmethod
    def created(data=None, msg='创建成功', code=201):
        """创建成功响应"""
        return Response({
            'code': code,
            'msg': msg,
            'data': data if data is not None else {}
        }, status=status.HTTP_201_CREATED)
    
    @staticmethod
    def error(msg='操作失败', code=400, data=None):
        """错误响应"""
        return Response({
            'code': code,
            'msg': msg,
            'data': data
        }, status=min(code, 500))
    
    @staticmethod
    def paginated(data, total, page, page_size, msg='操作成功'):
        """分页响应"""
        return Response({
            'code': 200,
            'msg': msg,
            'data': {
                'results': data,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        }, status=status.HTTP_200_OK)


def success_response(data=None, msg='操作成功'):
    """快捷成功响应"""
    return APIResponse.success(data, msg)


def error_response(msg='操作失败', code=400):
    """快捷错误响应"""
    return APIResponse.error(msg, code)
