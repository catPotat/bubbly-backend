from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Notification
from relationships.models import Relationship
from reacts.models import Reaction
from posts.models import Comment

@receiver([post_save, post_delete], sender=Relationship)
def hi_bye(sender, **kwargs):
    obj = kwargs['instance']
    me = obj.to_user
    them = obj.from_user
    if kwargs.get('created'):
        Notification.objects.create(
            actor = them,
            verb = Notification.FOLLOW,
            receiver = me,
        )
    else:
        Notification.objects.filter(
            actor = them,
            verb = Notification.FOLLOW,
            receiver = me
        ).delete()

@receiver([post_save, post_delete], sender=Reaction)
def reacted(sender, **kwargs):
    obj = kwargs['instance']
    if kwargs.get('created'):
        content = obj.to
        if obj.user != content.author:
            post_or_cmt = content.post if hasattr(content, 'post') else \
                content.comment if hasattr(content, 'comment') else content
            Notification.objects.create(
                actor = obj.user,
                verb = Notification.REACT,
                action_object = obj,
                target = post_or_cmt,
                receiver = content.author,
            )
    else:
        Notification.objects.filter(
            actor = obj.user,
            target_object_id = obj.to_id
        ).delete()

@receiver([post_save, post_delete], sender=Comment)
def commented_on_post(sender, **kwargs):
    obj = kwargs['instance']
    commented_on = obj.reply_to if obj.reply_to else obj.on
    if kwargs.get('created') and obj.content.author!=commented_on.content.author:
        Notification.objects.create(
            actor = obj.content.author,
            verb = Notification.COMMENT,
            action_object = obj,
            target = commented_on,
            receiver = commented_on.content.author,
        )
    else:
        Notification.objects.generic_filter(
            actor = obj.content.author,
            action_object = obj,
        ).delete()

# post_save.connect(