import requests
import json
import asyncio
from bubblyb.env_vars import (
    ONESIGNAL_AUTH_KEY,
    ONESIGNAL_APP_ID
)

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Notification
from chat.models import Message


header = {
    "Content-Type": "application/json; charset=utf-8",
    "Authorization": "Basic "+ONESIGNAL_AUTH_KEY
}
def do_req(data):
    req = requests.post("https://onesignal.com/api/v1/notifications", headers=header, data=data)
    # print(req.status_code, req.reason)
loop = asyncio.get_event_loop()
def sendPush(to=("long",), message="You have a notification!", click_to="http://localhost:3000/notifications", title="", imageUrl=""):
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "include_external_user_ids": to,
        "headings": {
            "en": title
        },
        "contents": {
            "en": message
        },
        "url": click_to,
        "chrome_web_icon": imageUrl
    }
    # do_req(data=json.dumps(payload)) # throttling test
    loop.run_in_executor( None, lambda: do_req(data=json.dumps(payload)) )


@receiver(post_save, sender=Notification)
def new_notification(sender, **kwargs):
    obj = kwargs['instance']
    if kwargs.get('created'):
        sendPush(
            (obj.receiver.username,),
            obj.actor.alias+" "+obj.get_verb_display(),
            imageUrl = obj.actor.profile_pic
        )
        
@receiver(post_save, sender=Message)
def new_message(sender, **kwargs):
    obj = kwargs['instance']
    if kwargs.get('created'):
        to_send = obj.thread.roommate_set.exclude(identity=obj.author).filter(enable_noti=True) \
            .values_list('identity', flat=True)
        if obj.msg_type == 1:
            content = ": "+obj.content
        else:
            content = " sent a message"
        sendPush(
            tuple(to_send),
            obj.author.alias + content,
            "http://localhost:3000/chat/t/"+str(obj.thread.id),
            obj.thread.name or "Chat message",
            obj.author.profile_pic,
        )