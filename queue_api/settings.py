
RABBITMQ_HOST = '10.10.110.1'
RABBITMQ_PORT = 5672
RABBITMQ_VHOST = '/svideo2'
RABBITMQ_EXCHANGE_TYPE_OCULAR = "direct"
RABBITMQ_EXCHANGE_TYPE_DRIVER = "direct"
RABBITMQ_RESPONSE_EXCHANGE = "driver"

RABBITMQ_CREDENTIALS = {
    'user': 'svideo2',
    'password': 'mC2QX0J7sx7i'
}


try:
    from queue_api.settings_local import *
except ImportError as exc:
    __import__('warnings').warn("Can't load local settings: {}".format(str(exc)))

