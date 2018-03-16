import os
from celery import Celery
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'theorema.settings')
app = Celery('theorema')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # send messages
    sender.add_periodic_task(
            3.0,
            send_message,
    )


@app.task(bind=True)
def send_message(self):
    notifications={}
    from theorema.cameras.models import NotificationCamera, Camera
    from theorema.users.models import User
    for camera in Camera.objects.all():
        if camera.analysis > 1
            pid = subprocess.getoutput('lsof -i | grep {}'.format(camera.port)).split()[1]
            stdout = subprocess.getoutput('timeout 2 cat /proc/{}/fd/1'.format(pid))
            if stdout:
           	 notifications[camera.id] = [el for el in stdout.split('\n') if 'Event started' in el] 
    for notification in NotificationCamera.objects.all():
        if notification.notify_time_start < datetime.datetime.now().time() < notification.notify_time_end:
            
