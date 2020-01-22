from rest_framework import serializers

from .models import Notification

from accounts.serializers import UserPeakSerializer

def truncate(str_):
    return (str_[:75] + '...') if len(str_) > 75 else str_

class NotificationListSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()
    verb = serializers.CharField(source='get_verb_display')
    action_object = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    class Meta:
        model = Notification
        fields = (
            'id',
            'timestamp',
            # 'unread',
            'actor',
            'verb',
            'action_object',
            'target',
        )
    def get_actor(self, obj):
        return UserPeakSerializer(obj.actor, context=self.context).data

    def get_action_object(self, obj):
        act_obj = obj.action_object
        type_ = type(act_obj).__name__
        if type_ == 'Reaction':
            return {
                "name": act_obj.icon.name,
                "img_src": act_obj.icon.img_src
            }
        elif type_ == 'Comment':
            return {
                "id": act_obj.content_id,
                "preview": truncate(act_obj.content.text)
            }

    def get_target(self, obj):
        target = obj.target
        type_ = type(target).__name__
        if type_ == 'Content':
            return {
                "id": target.id,
                "preview": truncate(target.text)
            }
        elif type_ == 'Post':
            return {
                "type": "post",
                "id": target.content_id,
                "title": target.title,
                "text": truncate(target.content.text)
            }
        elif type_ == 'Comment':
            return {
                "type": "comment",
                "id": target.content_id,
                "preview": truncate(target.content.text)
            }