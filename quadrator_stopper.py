import os
import sys
import time
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'theorema.settings')
import django
django.setup()

from theorema.cameras.models import Quadrator

def stopper():
    for quad in Quadrator.objects.all():
        if quad.is_active and datetime.datetime.now().timestamp() - quad.last_ping_time > 60:
            not_stopped = os.system('supervisorctl stop quad' + str(quad.id))
            if not_stopped:
                print(not_stopped, flush=True)
                print('quad' + str(quad.id), 'did not stop', flush=True)
            else:
                quad.is_active = False
                quad.save()
                print('quad' + str(quad.id), 'stopped', flush=True)

if __name__ == '__main__':
    while True:
        stopper()
        time.sleep(60)
