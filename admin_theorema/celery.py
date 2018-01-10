from celery import Celery
import shutil

from admin_theorema.listener import stop_cam, all_cams_info

app=Celery('admin_theorema', broker="amqp://guest:guest@127.0.0.1:5672//")


@app.task(bind=True)
def delete_cam(self, cam_path, cam_id):
    stop_cam(cam_id)
    all_cams_info.pop('cam'+str(cam_id))
    shutil.rmtree(cam_path)