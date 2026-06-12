from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        custom_data = {
            'detail': response.data.get('detail', str(response.data)),
            'code': getattr(exc, 'default_code', 'error'),
        }
        if isinstance(response.data, dict):
            field_errors = {k: v for k, v in response.data.items() if k != 'detail'}
            if field_errors:
                custom_data['field_errors'] = field_errors
        response.data = custom_data
    return response
