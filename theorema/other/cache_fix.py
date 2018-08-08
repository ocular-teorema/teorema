from django.contrib import admin
from rest_framework import viewsets
from django.contrib.admin.actions import delete_selected

'''
В некоторых версиях джанги глючит кеширование queryset.
Поэтому создан этот файл.
Здесь есть 2 вещи для использования.
1) CacheFixViewSet. Используется как обычный ViewSet т.е. от него нужно
наследовать вьюхи. Не требует какой-любо настройки.
2) cache_fix_admin_register это декоратор класса.
Когда создаётся класс для админки, наследуемый от ModelAdmin,
следует поставить перед ним этот декоратор, а в параметрах передать
название соответствующей модели, например:
@cache_fix_admin_register(Question)                                             
class QuestionAdmin(ModelAdmin):
    ...
'''

def dirty_decorator(model):
    def real_dirty_decorator(method):
        def wrapper(*args, **kwargs):
            Marker.inst().mark_as_dirty(model)
            return method(*args, **kwargs)
        return wrapper
    return real_dirty_decorator


def get_actions_decorator(model):
    def real_decorator(method):
        def wrapper(*args, **kwargs):
            res = method(*args, **kwargs)
            if res['delete_selected']:
                l = list(res['delete_selected'])
                l[0] = dirty_decorator(model)(delete_selected)
                res['delete_selected'] = tuple(l)
            return res
        return wrapper
    return real_decorator

def cache_fix_admin_register(model):
    def real_decorator(admin_class):
        admin_class = admin.register(model)(admin_class)
        admin_class.save_model = dirty_decorator(model)(admin_class.save_model)
        admin_class.delete_model = dirty_decorator(model)(admin_class.delete_model)
        admin_class.get_actions = get_actions_decorator(model)(admin_class.get_actions)
        def wrapper(*args, **kwargs):
            admin_class(*args, **kwargs)
        return wrapper
    return real_decorator

class CacheFixViewSet(viewsets.ModelViewSet):
    def __init__(self, *args, **kwargs):
        Marker.inst().add(self.__class__)
        return super().__init__(*args, **kwargs)

    def create(self, *args, **kwargs):
        self.queryset.dirty = True
        return super().create(*args, **kwargs)

    def update(self, *args, **kwargs):
        self.queryset.dirty = True
        return super().update(*args, **kwargs)

    def partial_update(self, *args, **kwargs):
        self.queryset.dirty = True
        return super().partial_update(*args, **kwargs)

    def destroy(self, *args, **kwargs):
        self.queryset.dirty = True
        return super().destroy(*args, **kwargs)

    def list(self, *args, **kwargs):
        if hasattr(self.queryset, 'dirty') and self.queryset.dirty:
            self.queryset.update()
            self.queryset.dirty = False
        return super().list(*args, **kwargs)

class Marker:
    __instance = None
    @staticmethod
    def inst():
        if Marker.__instance is None:
            Marker.__instance = Marker()
        return Marker.__instance

    def __init__(self):
        self.querysets = {}

    def add(self, view):
        self.querysets[view.serializer_class.Meta.model] = view.queryset

    def mark_as_dirty(self, model):
        try:
            self.querysets[model].dirty = True
        except KeyError:
            pass


class CacheControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print('aaaab')
        response = self.get_response(request)
        response['Cache-Control'] = 'no-cache'
        return response