import json


class QueueErrorMessage:

    code = None
    message = None
    request_uid = None

    def __init__(self, code=None, message=None, request_uid=None):
        if code is not None:
            self.code = code
        if message is not None:
            self.message = message
        if request_uid is not None:
            self.request_uid = request_uid

    def __repr__(self):
        return json.dumps({
            'success': False,
            'code': self.code,
            'error': self.message,
            'request_uid': self.request_uid
        })


class RequiredParamError(QueueErrorMessage):
    code = 1
    message = "Required parameter not found: {param}"

    def __init__(self, param, request_uid=None):
        super().__init__(
            message=self.message.format(param=param),
            request_uid=request_uid
        )


class RequestParamValidationError(QueueErrorMessage):
    code = 2
    message = "Validation error: {info}"

    def __init__(self, info, request_uid=None):
        super().__init__(
            message=self.message.format(info=info),
            request_uid=request_uid
        )

class ObjectDoesNotExistError(QueueErrorMessage):
    code = 3
    message = "Object does not exist: {object}"

    def __init__(self, object, request_uid=None):
        super().__init__(
            message=self.message.format(object=object),
            request_uid=request_uid
        )

