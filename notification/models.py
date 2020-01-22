from django.db import models

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from accounts.models import User

class NotificationManager(models.Manager):
    def generic_filter(self, **kwargs):
        qs = self
        target = kwargs.pop('target', None)
        if target:
            qs = qs.filter(
                target_content_type = ContentType.objects.get_for_model(type(target)),
                target_object_id = target.id
            )
        act_obj = kwargs.pop('action_object', None)
        if target:
            qs = qs.filter(
                action_object_content_type = ContentType.objects.get_for_model(type(act_obj)),
                action_object_object_id = act_obj.id
            )
        qs = qs.filter(**kwargs)
        return qs

    # def create(self, *args, **kwargs):
        # TODO loop.run_in_executor(None, lambda: super().create(*args, **kwargs))

class Notification(models.Model):
    '''
    https://github.com/django-notifications/django-notifications
    TODO revamp notification
    '''
    timestamp = models.DateTimeField(auto_now=True, db_index=True)    
    receiver = models.ForeignKey(User, related_name='noti_receiver', on_delete=models.CASCADE)

    actor = models.ForeignKey(User, related_name='noti_actor', on_delete=models.CASCADE)

    FOLLOW = 'FL'
    REACT = 'RC'
    COMMENT = 'CM'
    MENTION = 'MT'
    ANNOUNCEMENT = 'AN'
    FLAGGED = 'FG'
    VERBS_CHOICES = (
        (FOLLOW, 'followed you'),
        (REACT, 'reacted'),
        (COMMENT, 'commented'),
        (MENTION, 'mentioned you'),
        (ANNOUNCEMENT, 'announced'),
        (FLAGGED, 'flagged'),
    )
    verb = models.CharField(max_length=2, choices=VERBS_CHOICES)
    
    action_object_content_type = models.ForeignKey(ContentType,
        related_name='action_object_content_type', on_delete=models.CASCADE,
        blank=True, null=True, default=None
    )
    action_object_object_id = models.CharField(max_length=255, blank=True, null=True, default=None)
    action_object = GenericForeignKey('action_object_content_type', 'action_object_object_id')
    
    target_content_type = models.ForeignKey(ContentType,
        related_name='target_content_type', on_delete=models.CASCADE,
        blank=True, null=True, default=None
    )
    target_object_id = models.CharField(max_length=255, blank=True, null=True, default=None)
    target = GenericForeignKey('target_content_type', 'target_object_id')
    
    objects = NotificationManager()

    class Meta:
        ordering = ('-timestamp',)