import json


class QueueMessage:

    data = None
    uuid = None
    response_type = None

    def __init__(self, uuid=None, response_type=None, data=None):
        if data is not None:
            self.data = data
        if uuid is not None:
            self.uuid = uuid
        if response_type is not None:
            self.response_type = uuid

    def __repr__(self):
        return json.dumps({
            'uuid': self.uuid,
            'type': self.response_type,
            'data': self.data
        })


class QueueSuccessMessage(QueueMessage):

    def __init__(self, uuid=None, response_type=None):
        self.data = {
            'success': True
        }

        super().__init__(uuid, response_type, self.data)


class QueueErrorMessage(QueueMessage):

    code = None
    error = None

    def __init__(self, uuid=None, response_type=None, code=None, error=None):
        if code is not None:
            self.code = code
        if error is not None:
            self.error = error

        self.data = {
            'success': False,
            'code': self.code,
            'error': self.error
        }

        super().__init__(uuid, response_type, self.data)


class RequiredParamError(QueueErrorMessage):
    code = 1
    message = "Required parameter not found: {param}"

    def __init__(self, param, uuid=None, response_type=None):
        super().__init__(
            uuid=uuid,
            response_type=response_type,
            error=self.message.format(param=param)
        )


class RequestParamValidationError(QueueErrorMessage):
    code = 2
    message = "Validation error: {info}"

    def __init__(self, info, uuid=None, response_type=None):
        print('info', info, flush=True)
        super().__init__(
            uuid=uuid,
            response_type=response_type,
            error=self.message.format(info=info)
        )
