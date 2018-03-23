import os
from celery import Celery
import datetime
import subprocess
import re
import pytz
from django.core.mail import send_mail
import time

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
    current_timezone=pytz.timezone('Europe/Moscow')
#    print(datetime.datetime.now(current_timezone).time())
    active_notifications=NotificationCamera.objects.filter(notify_time_start__lte = datetime.datetime.now(current_timezone).time(), notify_time_stop__gte = datetime.datetime.now(current_timezone).time())
    print(active_notifications)
    all_notifications=NotificationCamera.objects.all()
    notifications={}
    if all_notifications:
        for notification in all_notifications:
            for camera in notification.camera:
                print(camera)
                cam = Camera.objects.get(id=int(camera))
                if cam.id not in notifications.keys() and cam.analysis>1:
                    pid = subprocess.getoutput('lsof -i | grep {}'.format(cam.port)).split()[1]
                    stdout = subprocess.getoutput('timeout 2 cat /proc/{}/fd/1'.format(pid))
                    if stdout:
                        stdout = [el for el in stdout.split('\n') if 'Event started' in el and 'CamInfoEventMessage' in el]
                        events=''
                        for el in stdout:
                            str = 'Время события {}, '.format(re.search(r'(?<=time:)\S{8}', el).group(0))
                            str += 'Имя камеры: {}, '.format(cam.name)
                            str += 'Тип события: {}, '.format(ACTIVITY_TYPE[re.search(r'(?<=type = )\w+', el).group(0)])
                            str += 'Уровень события: {}, '.format(re.search(r'(?<=confidence = )\w+', el).group(0))
                            str += 'Ссылка на ролик: {}\n'.format(re.search(r'(?<=link:http://127.0.0.1:)\S+.mp4', el).group(0))
                            #str += 'Имя камеры: {} \n'.format(cam.name)
                            events += str
                            print(events)
                        print('end')
                        notifications[cam.id] = events
        print(notifications)
        if active_notifications:
            func = lambda obj : 'Высокий' if int(obj.group(0)) > 80 else ('Средний' if 80 > int(obj.group(0)) > 50 else 'Низкий')
            for notification in active_notifications:
                for user in notification.users.all():
                    message=''
                    message_list=''.join([value for key,value in notifications.items() if key in notification.camera and value and int(re.search(r"(?<=Уровень события: )\w+", value).group(0)) > notification.notify_alert_level])
                    #print(message_list)
                    #message_list=message_list.split('\n')
                    #message_list.remove('')
                    #print(message_list)
                    message=re.sub(r'(?<=Уровень события: )\w+', func, message_list)
                    if message_list:
                        #for el in message_list:
                        #    level=re.search(r"(?<=Уровень события: )\w+", el).group(0)
                        #    print(level)
                        #    message += el.replace(level, 'Высокий' if int(level) > 80 else ('Средний' if 80 > int(level) > 50  else 'Низкий')) + '\n'
                        #    level = re.search(r"(?<=Уровень события: )\w+", message).group(0)
                        #message=(
                        #message= message.replace(level, 'Высокий' if int(level) > 80 else ('Средний' if 80 > int(level) > 50  else 'Низкий'))
                        #message_list=[value for key,value in notifications.items() if key in notification.camera and value and int(re.search(r"(?<=Уровень события: )\w+", value).group(0)) > notification.notify_alert_level]
                        #for line in message_list:
                        #    level=re.search(r"(?<=Уровень события: )\w+", line).group(0)
                        #    print(level)
                        #    message += line.replace(level, 'Высокий' if int(level) > 80 else ('Средний' if 80 > int(level) > 50  else 'Низкий'))
                        #    print(line)
                        try:
                            send_mail('Новые уведомления', message, 'analitika@teorema.info', [user.email, ], fail_silently=False)
                            time.sleep(2)
                        except:
                            raise Exception('send message fail')
