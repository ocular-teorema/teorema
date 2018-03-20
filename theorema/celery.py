import os
from celery import Celery
import datetime
import subprocess
import re 
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'theorema.settings')
app = Celery('theorema')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # send messages
    sender.add_periodic_task(
            60.0,
            send_message,
    )


@app.task(bind=True)
def send_message(self):
    ACTIVITY_TYPE= {
    'AREA': 'Движение в зоне',
    'STATIC_OBJECT': 'Оставленный предмет',
    'VELOCITY': 'Скорость движения',
    'MOTION': 'Вектор движение',
    'CALIBRATION': 'Ошибка калибровки',
    'PEOPLE_COUNT': 'Толпа',
  }
    from theorema.cameras.models import NotificationCamera, Camera
    from theorema.users.models import User
    active_notifications=NotificationCamera.objects.filter(notify_time_start__lt = datetime.datetime.now().time(), notify_time_stop__gt = datetime.datetime.now().time())
    notifications={}
    if active_notifications:
        for notification in active_notifications:
            for camera in notification.camera:
                cam = Camera.objects.get(id=int(camera))
                if cam.id not in notifications.keys() and cam.analysis>1:
                    pid = subprocess.getoutput('lsof -i | grep {}'.format(cam.port)).split()[1]
                    stdout = subprocess.getoutput('timeout 2 cat /proc/{}/fd/1'.format(pid))
                    if stdout:
                        #notifications[cam.id] = [el for el in stdout.split('\n') if 'Event started' in el and 'CamInfoEventMessage' in el]
                        #for notify in notifications[cam.id]
                        stdout = [el for el in stdout.split('\n') if 'Event started' in el and 'CamInfoEventMessage' in el]
                        events=''
                        for el in stdout:
                            str = 'Тип события: {}, '.format(ACTIVITY_TYPE[re.search(r'(?<=type = )\w+', el).group(0)])
                            str += 'Время события: {}, '.format(re.search(r'(?<=time:)\S{8}', el).group(0))
                            str += 'Ссылка на ролик: {}, '.format(re.search(r'(?<=link:http://127.0.0.1:)\S+.mp4', el).group(0))
                            str += 'Уровень события: {}, '.format(re.search(r'(?<=confidence = )\w+', el).group(0))
                            str += 'Имя камеры: {} \n'.format(cam.name)
                            events += str
                        print('end')
                        notifications[cam.id] = events
            for user in notification.users.all():
                message=''.join([value for key,value in notifications.items() if key in notification.camera and value and int(re.search(r"(?<=Уровень события: )\w+", value).group(0)) > notification.notify_alert_level])
                print(user.username, message)
        print(notifications)
