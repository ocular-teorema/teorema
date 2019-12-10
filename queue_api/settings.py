
RABBITMQ_HOST = '10.10.110.1'
RABBITMQ_PORT = 5672
RABBITMQ_VHOST = '/ocular'

RABBITMQ_CREDENTIALS = {
    'user': 'ocular',
    'password': 'mC2QX0J7sx7i'
}


try:
    from queue_api.settings_local import *
except ImportError as exc:
    __import__('warnings').warn("Can't load local settings: {}".format(str(exc)))

