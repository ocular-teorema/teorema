import json


class QueueMessage:

    data = None
    request_uid = None
    response_type = None

    def __init__(self, request_uid=None, response_type=None, data=None):
        if data is not None:
            self.data = data
        if request_uid is not None:
            self.request_uid = request_uid
        if response_type is not None:
            self.response_type = request_uid

    def __repr__(self):
        return json.dumps({
            'request_uid': self.request_uid,
            'type': self.response_type,
            'data': self.data
        })


class QueueSuccessMessage(QueueMessage):

    def __init__(self, request_uid=None, response_type=None):
        self.data = {
            'success': True
        }

        super().__init__(request_uid, response_type, self.data)


class QueueErrorMessage(QueueMessage):

    code = None
    error = None

    def __init__(self, request_uid=None, response_type=None, code=None, error=None):
        if code is not None:
            self.code = code
        if error is not None:
            self.error = error

        self.data = {
            'success': False,
            'code': self.code,
            'error': self.error
        }

        super().__init__(request_uid, response_type, self.data)


class RequiredParamError(QueueErrorMessage):
    code = 1
    message = "Required parameter not found: {param}"

    def __init__(self, param, request_uid=None, response_type=None):
        super().__init__(
            request_uid=request_uid,
            response_type=response_type,
            error=self.message.format(param=param)
        )


class RequestParamValidationError(QueueErrorMessage):
    code = 2
    message = "Validation error: {info}"

    def __init__(self, info, request_uid=None, response_type=None):
        print('info', info, flush=True)
        super().__init__(
            request_uid=request_uid,
            response_type=response_type,
            error=self.message.format(info=info)
        )
