from django.db import transaction
from django.db.models.fields.related import ManyToManyField
from rest_framework import serializers

class M2MHelperSerializer(serializers.ModelSerializer):
    _m2mhm_field_classes = (ManyToManyField, )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._m2mhm_fields = [x for x in self.Meta.model._meta.get_fields() if isinstance(x, self._m2mhm_field_classes)]
    
    @property
    def fields(self):
        if not hasattr(self, '_fields'):
# https://github.com/encode/django-rest-framework/blob/master/rest_framework/serializers.py#L354
            super().fields 
            new_fields = {x.name: serializers.JSONField(write_only=True) for x in self._m2mhm_fields}
            self._fields.update(new_fields)
        return self._fields

    def _m2mhm_do_transaction(self, methods, **kwargs):
        transaction.set_autocommit(False)
        try:
            for method in methods:
                kwargs = method(**kwargs)
        except:
            transaction.rollback()
            raise
        else:
            transaction.commit()
        finally:
            transaction.set_autocommit(True)
        return kwargs
    
    def _m2mhm_create_obj(self, **kwargs):
        kwargs['obj'] = super().create(kwargs['validated_data'])
        return kwargs

    def _m2mhm_create_through(self, **kwargs):
        for field, data in kwargs['for_process'].items():
            if data is not None:
                through_model = field.rel.through
                name_fk_to_this = field.m2m_field_name()
                name_fk_to_another = field.m2m_reverse_field_name()
                for_create = []
                through_model_fields = [x.name for x in through_model._meta.get_fields()]
                for chunk in data:
                    another_id = chunk.pop('id')
                    arguments = {k: v for k, v in chunk.items() if k in through_model_fields}
                    arguments[name_fk_to_this+'_id'] = kwargs['obj'].id
                    arguments[name_fk_to_another+'_id'] = another_id
                    for_create.append(through_model(**arguments))
                through_model.objects.bulk_create(for_create)
        return kwargs

    def _m2mhm_update_obj(self, **kwargs):
        kwargs['obj'] = super().update(kwargs['obj'], kwargs['validated_data'])
        return kwargs

    def _m2mhm_delete_through(self, **kwargs):
        for field, data in kwargs['for_process'].items():
            if data:
                through_model = field.rel.through
                name_fk_to_this = field.m2m_field_name()
                through_model.objects.filter(**{name_fk_to_this: kwargs['obj']}).delete()
        return kwargs

    def create(self, validated_data):
        for_process = {x: validated_data.pop(x.name, None) for x in self._m2mhm_fields}
        return self._m2mhm_do_transaction(
                (self._m2mhm_create_obj, self._m2mhm_create_through),
                validated_data=validated_data,
                for_process=for_process,
        )['obj']

    def update(self, obj, validated_data):
        for_process = {x: validated_data.pop(x.name, None) for x in self._m2mhm_fields}
        return self._m2mhm_do_transaction(
                    (self._m2mhm_update_obj, self._m2mhm_delete_through, self._m2mhm_create_through),
                    validated_data=validated_data,
                    for_process = for_process,
                    obj = obj,
        )['obj']

    def to_representation(self, obj):
        result = super().to_representation(obj)
        for field in self._m2mhm_fields:
            result[field.name] = []
            through_model = field.rel.through
            name_related = field.rel.name
            name_fk_to_this = field.m2m_field_name()
            name_fk_to_another = field.m2m_reverse_field_name()
            serializer = [x for x in object.__class__.__subclasses__(serializers.ModelSerializer) if getattr(getattr(x, 'Meta', None), 'model', None) == field.rel.model][0]()
            for through_object in list(getattr(obj, through_model.__name__.lower()+'_set').all()):
                through_object_fields = [x.name for x in through_object.__class__._meta.get_fields() if x.name not in ('id', name_fk_to_this, name_fk_to_another)]
                sub_result = {x: getattr(through_object, x) for x in through_object_fields}
                another_object = getattr(through_object, name_fk_to_another)
                sub_result.update(serializer.to_representation(another_object))
                result[field.name].append(sub_result)
        return result
