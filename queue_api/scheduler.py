from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.exceptions import ObjectDoesNotExist

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from theorema.cameras.models import CameraSchedule

from queue_api.common import QueueEndpoint
from queue_api.messages import RequiredParamError, RequestParamValidationError, InvalidScheduleTypeError
from queue_api.cameras import enable_camera, disable_camera

class CameraScheduler:

    def __init__(self):
        self.scheduler = BackgroundScheduler({
            'apscheduler.jobstores.default': {
                'type': 'sqlalchemy',
                'url': 'postgresql://postgres:Blizzard@localhost/theorema_schedules'
            },
            'apscheduler.executors.default': {
                'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
                'max_workers': '20'
            },
            'apscheduler.executors.processpool': {
                'type': 'processpool',
                'max_workers': '5'
            },
            'apscheduler.job_defaults.coalesce': 'false',
            'apscheduler.job_defaults.max_instances': '3',
            'apscheduler.timezone': 'UTC',
        })

    def start(self):
        #scheduler.add_job(forecastApi.update_forecast, 'interval', minutes=5)
        self.scheduler.start()
        print('scheduler started', flush=True)

    def add_weekdays_schedule(self, camera, days):
        days_to_zero = []
        for el in days:
            el -= 1
            days_to_zero.append(el)

        converted_days = str(days_to_zero)[1:-1]
        enable_job = self.scheduler.add_job(enable_camera, 'cron', [camera], day_of_week=converted_days, hour=0, minute=0, second=1)
        disable_job = self.scheduler.add_job(disable_camera, 'cron', [camera], day_of_week=converted_days, hour=23, minute=59, second=59)
        return enable_job, disable_job

    def add_timestamp_schedule(self, camera, start_timestamp, stop_timestamp):
        start_datetime = datetime.fromtimestamp(int(start_timestamp))
        stop_datetime = datetime.fromtimestamp(int(stop_timestamp))

        enable_job = self.scheduler.add_job(enable_camera, 'date', [camera], run_date=start_datetime)
        disable_job = self.scheduler.add_job(disable_camera, 'date', [camera], run_date=stop_datetime)
        return enable_job, disable_job

    def add_time_schedule(self, camera, start_time, stop_time):
        start_times = [int(value) for value in start_time.split('-')]
        stop_times = [int(value) for value in stop_time.split('-')]

        enable_job = self.scheduler.add_job(enable_camera(camera), 'cron', [camera],
                                            hour=start_times[0], minute=start_times[1], second=start_times[2])
        disable_job = self.scheduler.add_job(disable_camera(camera), 'cron', [camera],
                                             hour=stop_times[0], minute=stop_times[1], second=stop_times[2])
        return enable_job, disable_job

    def delete_schedule(self, start_job_id, stop_job_id):
        self.scheduler.remove_job(start_job_id)
        self.scheduler.remove_job(stop_job_id)
        return True


class ScheduleQueueEndpoint(QueueEndpoint):

    def check_request_params(self, actual):
        actual_keys = actual.keys()

        if 'schedule_type' not in actual_keys:
            message = RequiredParamError('schedule_type', self.uuid, self.response_message_type)
            print(message, flush=True)
            self.send_error_response(message)
            return True

        schedule_type = actual['schedule_type']
        if schedule_type not in ['weekdays', 'timestamp', 'time_period']:
            message = InvalidScheduleTypeError(type=schedule_type, uuid=self.uuid)
            print(message, flush=True)
            self.send_error_response(message)
            return True

        if schedule_type == 'weekdays':
            if 'days' not in actual or not actual['days']:
                message = RequiredParamError('days', self.uuid, self.response_message_type)
                print(message, flush=True)
                self.send_error_response(message)
                return True

        if schedule_type == 'timestamp':
            if 'start_timestamp' not in actual or not actual['start_timestamp']:
                message = RequiredParamError('start_timestamp', self.uuid, self.response_message_type)
                print(message, flush=True)
                self.send_error_response(message)
                return True
            if 'stop_timestamp' not in actual or not actual['stop_timestamp']:
                message = RequiredParamError('stop_timestamp', self.uuid, self.response_message_type)
                print(message, flush=True)
                self.send_error_response(message)
                return True

        if schedule_type == 'time_period':
            if 'start_time' not in actual or not actual['start_time']:
                message = RequiredParamError('start_time', self.uuid, self.response_message_type)
                print(message, flush=True)
                self.send_error_response(message)
            if 'stop_time' not in actual or not actual['stop_time']:
                message = RequiredParamError('stop_time', self.uuid, self.response_message_type)
                print(message, flush=True)
                self.send_error_response(message)
                return True


class SchedulesAddMessage(ScheduleQueueEndpoint):

    response_message_type = 'schedules_add_response'

    def handle_request(self, message):
        print('message received', flush=True)
        self.uuid = message['uuid']
        params = message['data']
        print('params', params, flush=True)

        if self.check_request_params(params):
            return

        schedule_type = params['schedule_type']
        days = start_timestamp = stop_timestamp = start_time = stop_time = None
        if schedule_type == 'weekdays':
            days = str(params['days'])[1:-1] if 'days' in params else None
        elif schedule_type == 'timestamp':
            start_timestamp = params['start_timestamp'] if 'start_timestamp' in params else None
            stop_timestamp = params['stop_timestamp'] if 'stop_timestamp' in params else None
        elif schedule_type == 'time_period':
            start_time = params['start_time'] if 'start_time' in params else None
            stop_time = params['stop_time'] if 'stop_time' in params else None

        schedule = CameraSchedule(
            schedule_type=schedule_type,
            weekdays=days,
            start_timestamp=start_timestamp,
            stop_timestamp=stop_timestamp,
            start_daytime=start_time,
            stop_daytime=stop_time
        )

        schedule.save()
        self.send_data_response({'schedule_id': schedule.id, 'success': True})


class ScheduleListMessage(ScheduleQueueEndpoint):

    response_message_type = 'schedules_list_response'

    def handle_request(self, params):
        print('message received', flush=True)
        self.send_response(params)

    def send_response(self, params):
        print('preparing response', flush=True)
        self.uuid = params['uuid']

        all_schedules = CameraSchedule.objects.all()

        schedule_weekdays_list = []
        schedules_weekdays = all_schedules.filter(schedule_type='weekdays')
        for schedule in schedules_weekdays:
            schedule_data = {
                'id': schedule.id,
                'days': [int(day) for day in schedule.weekdays.split(', ')]
            }
            schedule_weekdays_list.append(schedule_data)

        schedule_timestamp_list = []
        schedules_timestamp = all_schedules.filter(schedule_type='timestamp')
        for schedule in schedules_timestamp:
            schedule_data = {
                'id': schedule.id,
                'start_timestamp': schedule.start_timestamp,
                'stop_timestamp': schedule.stop_timestamp
            }
            schedule_timestamp_list.append(schedule_data)

        schedule_time_list = []
        schedules_time = all_schedules.filter(schedule_type='time_period')
        for schedule in schedules_time:
            schedule_data = {
                'id': schedule.id,
                'start_time': schedule.start_daytime,
                'stop_time': schedule.stop_daytime
            }
            schedule_time_list.append(schedule_data)

        data = {
            'weekdays': schedule_weekdays_list,
            'timestamp': schedule_timestamp_list,
            'time_period': schedule_time_list
        }

        self.send_data_response(data)
        return


class SchedulesUpdateMessage(ScheduleQueueEndpoint):

    response_message_type = 'schedules_update_response'

    def handle_request(self, message):
        print('message received', flush=True)
        self.uuid = message['uuid']

        params = message['data']
        if self.check_request_params(params):
            return

        schedule_id = message['schedule_id']
        try:
            schedule = CameraSchedule.objects.get(id=schedule_id)
        except ObjectDoesNotExist:
            error = RequestParamValidationError('schedule with id {id} not found'.format(id=schedule_id))
            print(error, flush=True)
            self.send_error_response(error)
            return

        schedule_type = params['schedule_type']
        schedule.schedule_type = schedule_type

        if schedule_type == 'weekdays':
            schedule.weekdays = str(params['days']) if 'days' in params else schedule.days
            schedule.start_timestamp = None
            schedule.stop_timestamp = None
            schedule.start_daytime = None
            schedule.stop_timestamp = None
        elif schedule_type == 'timestamp':
            schedule.start_timestamp = params['start_timestamp'] if 'start_time in params' else schedule.start_timestamp
            schedule.stop_timestamp = params['stop_timestamp'] if 'stop_timestamp' in params else schedule.stop_timestamp
            schedule.weekdays = None
            schedule.start_daytime =None
            schedule.stop_daytime = None
        elif schedule_type == 'time_period':
            schedule.start_daytime = params['start_time'] if 'start_time' in params else schedule.start_daytime
            schedule.stop_daytime = params['stop_time'] if 'stop_time' in params else schedule.stop_daytime
            schedule.weekdays = None
            schedule.start_timestamp = None
            schedule.stop_timestamp = None

        schedule.save()
        self.send_success_response()


class SchedulesDeleteMessage(ScheduleQueueEndpoint):

    response_message_type = 'schedules_delete_response'
    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']

        schedule_id = params['schedule_id']
        try:
            schedule = CameraSchedule.objects.get(id=schedule_id)
        except ObjectDoesNotExist:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=schedule_id))
            print(error, flush=True)
            self.send_error_response(error)
            return

        schedule.delete()

        self.send_success_response()

