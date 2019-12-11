from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.exceptions import ObjectDoesNotExist

from theorema.cameras.models import CameraSchedule

from queue_api.common import QueueEndpoint
from queue_api.messages import RequiredParamError, RequestParamValidationError, InvalidScheduleTypeError


class CameraScheduler:

    def start(self):
        scheduler = BackgroundScheduler()
        #scheduler.add_job(forecastApi.update_forecast, 'interval', minutes=5)
        scheduler.start()
        print('scheduler started', flush=True)


class ScheduleQueueEndpoint(QueueEndpoint):

    def __init__(self, scheduler):
        super().__init__()

        self.scheduler = scheduler

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
            if 'days' not in actual:
                message = RequiredParamError('days', self.uuid, self.response_message_type)
                print(message, flush=True)
                self.send_error_response(message)
                return True

        if schedule_type == 'timestamp':
            if 'start_timestamp' not in actual:
                message = RequiredParamError('start_timestamp', self.uuid, self.response_message_type)
                print(message, flush=True)
                self.send_error_response(message)
                return True
            if 'stop_timestamp' not in actual:
                message = RequiredParamError('stop_timestamp', self.uuid, self.response_message_type)
                print(message, flush=True)
                self.send_error_response(message)
                return True

        if schedule_type == 'time_period':
            if 'start_time' not in actual:
                message = RequiredParamError('start_time', self.uuid, self.response_message_type)
                print(message, flush=True)
                self.send_error_response(message)
            if 'stop_time' not in actual:
                message = RequiredParamError('stop_time', self.uuid, self.response_message_type)
                print(message, flush=True)
                self.send_error_response(message)
                return True


class ScheduleAddMessage(ScheduleQueueEndpoint):

    def handle_request(self, message):
        print('message received', flush=True)
        self.uuid = message['uuid']
        params = message['data']
        print('params', params, flush=True)

        if self.check_request_params(params):
            return

        schedule_type = params['schedule_type']
        days = str(params['days']) if 'days' in params else None
        start_timestamp = params['start_timestamp'] if 'start_timestamp' in params else None
        stop_itmestamp = params['stop_timestamp'] if 'stop_timestamp' in params else None
        start_time = params['start_time'] if 'start_time' in params else None
        stop_time = params['stop_time'] if 'stop_time' in params else None

        schedule = CameraSchedule(
            schedule_type=schedule_type,
            weekdays=days,
            start_timestamp=start_timestamp,
            stop_itmestamp=stop_itmestamp,
            start_time=start_time,
            stop_time=stop_time
        )

        schedule.save()
        self.send_success_response()


class ScheduleListMessage(ScheduleQueueEndpoint):

    def handle_request(self, params):
        print('message received', flush=True)
        self.send_response(params)

    def send_response(self, params):
        print('preparing response', flush=True)
        self.uuid = params['uuid']

        all_schedules = CameraSchedule.objects.all()

        schedule_weekdays_dict = {}
        schedules_weekdays = all_schedules.filter(schedule_type='weekdays')
        for schedule in schedules_weekdays:
            schedule_data = {
                'days': list(schedule.days)
            }
            schedule_weekdays_dict[schedule.id] = schedule_data

        schedule_timestamp_dict = {}
        schedules_timestamp = all_schedules.filter(schedule_type='timestamp')
        for schedule in schedules_timestamp:
            schedule_data = {
                'start_timestamp': schedule.start_timestamp,
                'stop_timestamp': schedule.stop_timestamp
            }
            schedule_timestamp_dict[schedule.id] = schedule_data

        schedule_time_dict = {}
        schedules_time = all_schedules.filter(schedule_type='time_period')
        for schedule in schedules_time:
            schedule_data = {
                'start_timestamp': schedule.start_timestamp,
                'stop_timestamp': schedule.stop_timestamp
            }
            schedule_time_dict[schedule.id] = schedule_data

        data = {
            'weekdays': schedule_weekdays_dict,
            'timestamp': schedule_timestamp_dict
            'time_period': schedule_time_dict
        }

        self.send_data_response(data)
        return


class SchedulesUpdateMessage(ScheduleQueueEndpoint):

    def handle_request(self, message):
        print('message received', flush=True)
        self.uuid = message['uuid']

        params = message['data']
        if self.check_request_params(params):
            return

        schedule_id = message['schedule_id']
        try:
            schedule = CameraSchedule.objects.get(uid=schedule_id)
        except ObjectDoesNotExist:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=schedule_id))
            print(error, flush=True)
            self.send_error_response(error)
            return

        schedule_type = params['schedule_type']
        schedule.schedule_type = schedule_type

        if schedule_type == 'weekdays'
            schedule.days = str(params['days']) if 'days' in params else schedule.days
        elif schedule_type == 'timestamp'
            schedule.start_timestamp = params['start_timestamp'] if 'start_time in params' else schedule.start_timestamp
            schedule.stop_timestamp = params['stop_timestamp'] if 'stop_timestamp' in params else schedule.stop_timestamp
        elif schedule_type == 'time_period'
            schedule.start_time = params['start_time'] if 'start_time' in params else schedule.start_time
            schedule.stop_time = params['stop_time'] if 'stop_time' in params else schedule.stop_time

        schedule.save()
        self.send_success_response()


class SchedulesDeleteMessage(ScheduleQueueEndpoint):

    def handle_request(self, params):
        print('message received', flush=True)
        self.uuid = params['uuid']

        schedule_id = params['schedule_id']
        try:
            schedule = CameraSchedule.objects.get(uid=schedule_id)
        except ObjectDoesNotExist:
            error = RequestParamValidationError('camera with id {id} not found'.format(id=schedule_id))
            print(error, flush=True)
            self.send_error_response(error)
            return

        schedule.delete()

        self.send_success_response()

