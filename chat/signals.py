import json
import asyncio

from django.db.models.signals import post_save
from django.dispatch import receiver

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Message
from .serializers import MessageSerializer


@receiver(post_save, sender=Message, weak=True, dispatch_uid=None)
def new_message(sender, instance, **kwargs):
    response = {
        "msg_data": MessageSerializer(
            instance,
            context = {'profile_flds': ('profile_pic', 'fave_color')}
        ).data,
    }
    async_to_sync(get_channel_layer().group_send)(
        instance.thread.channels_layer_name,
        {
            "type": "chat_message",
            "text": json.dumps(response)
        }
    )
