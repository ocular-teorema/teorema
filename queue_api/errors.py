import json


class QueueErrorMessage:

    code = None
    message = None
    request_uid = None
    response_type = None

    def __init__(self, code=None, message=None, request_uid=None, response_type=None):
        if code is not None:
            self.code = code
        if message is not None:
            self.message = message
        if request_uid is not None:
            self.request_uid = request_uid
        if response_type is not None:
            self.response_type = request_uid

    def __repr__(self):
        return json.dumps({
            'request_uid': self.request_uid,
            'type': self.response_type,
            'data': {
                'success': False,
                'code': self.code,
                'error': self.message,
            }
        })


class RequiredParamError(QueueErrorMessage):
    code = 1
    message = "Required parameter not found: {param}"

    def __init__(self, param, request_uid=None, response_type=None):
        super().__init__(
            message=self.message.format(param=param),
            request_uid=request_uid,
            response_type=response_type
        )


class RequestParamValidationError(QueueErrorMessage):
    code = 2
    message = "Validation error: {info}"

    def __init__(self, info, request_uid=None, response_type=None):
        super().__init__(
            message=self.message.format(info=info),
            request_uid=request_uid,
            response_type=response_type
        )
