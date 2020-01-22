from rest_framework.serializers import SerializerMethodField

class DynamicFieldsMixin(object):
    dyna_fld_kwarg = ''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = kwargs.get('context', {}).get(self.dyna_fld_kwarg, ())
        for field in fields:
            self.fields[field] = SerializerMethodField()

class LoggedInExclsvFldsMixin(object):
    logged_in_flds = ('',)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ctx = kwargs.get('context', {})
        if ctx.get('request') and not ctx['request'].user.is_anonymous:
            for field in self.logged_in_flds:
                self.fields[field] = SerializerMethodField()

class NestedFlattenerMixin(object):
    """ Flattens output json """
    to_flatten = ''
    def to_representation(self, obj):
        to_re = super().to_representation(obj)
        nested = to_re.pop(self.to_flatten, [])
        for key in nested:
            to_re[key] = nested[key]
        return to_re
