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


class InvalidMessageStructureError(QueueErrorMessage):
    code = 1
    message = "Message structure is not valid"

    def __init__(self, uuid=None):
        super().__init__(
            uuid=uuid,
            response_type='error',
            error=self.message
        )


class InvalidMessageTypeError(QueueErrorMessage):
    code = 2
    message = "Declared type is not supported: {type}"

    def __init__(self, request_type, uuid=None):
        super().__init__(
            uuid=uuid,
            response_type='error',
            error=self.message.format(type=request_type)
        )


class RequiredParamError(QueueErrorMessage):
    code = 3
    message = "Required parameter not found: {param}"

    def __init__(self, param, uuid=None, response_type=None):
        super().__init__(
            uuid=uuid,
            response_type=response_type,
            error=self.message.format(param=param)
        )


class RequestParamValidationError(QueueErrorMessage):
    code = 4
    message = "Validation error: {info}"

    def __init__(self, info, uuid=None, response_type=None):
        print('info', info, flush=True)
        super().__init__(
            uuid=uuid,
            response_type=response_type,
            error=self.message.format(info=info)
        )
