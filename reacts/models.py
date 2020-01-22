from django.db import models
from accounts.models import User
from communities.models import Community
from posts.models import Content

'''
#################
# CUSTOM FIELDS #
class PositiveBigIntegerField(models.BigIntegerField):
    empty_strings_allowed = False
    description = ("Big (8 byte) positive integer")

    def db_type(self, connection):
        """
        Returns MySQL-specific column data type. Make additional checks
        to support other backends.
        """
        return 'bigint UNSIGNED'

    def formfield(self, **kwargs):
        defaults = {'min_value': 0,
                    'max_value': BigIntegerField.MAX_BIGINT * 2 - 1}
        defaults.update(kwargs)
        return super(PositiveBigIntegerField, self).formfield(**defaults)
# END OF CUSTOM FIELDS #
########################
'''


class Icon(models.Model):
    uploader = models.ForeignKey(User, on_delete=models.PROTECT)
    belongs_to = models.ForeignKey(Community, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=16)
    img_src = models.TextField()
    active = models.BooleanField(default=True)
    uploaded_on = models.DateTimeField(auto_now=True)
    # class Meta:
    #     unique_together = ('belongs_to', 'name')

class Reaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    icon = models.ForeignKey(Icon, on_delete=models.PROTECT, default=1)
    to = models.ForeignKey(Content, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'to')
