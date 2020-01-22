import json
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
import channels.exceptions as excpt

from .models import Room, Message
from reacts.models import Icon
from communities.models import Membership

from .serializers import MessageSerializer
from accounts.serializers import UserPeakSerializer


class ChatConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        print("Whenever problem arises, be sure to check Redis first")
        self.me = self.scope['user']
        self.thread_obj = await self.get_room(self.scope['url_route']['kwargs']['thread_id'])
        self.t_name = self.thread_obj.channels_layer_name

        if self.thread_obj.has_room_perm(self.me, basic_perms=True):
            await self.channel_layer.group_add(self.t_name, self.channel_name)
            await self.send({
                "type": "websocket.accept",
            })
          
    async def websocket_receive(self, event):
        received = event.get("text")
        if received == "tpng":
            # Someone is typing
            response = {
                "type": "tpng",
                "user": UserPeakSerializer(
                    self.me, context={'profile_flds': ('profile_pic',)}
                ).data,
            }
            await self.channel_layer.group_send(self.t_name, {
                "type": "chat_message",
                "text": json.dumps(response)
            })
        elif received is not None:
            loaded_dict = json.loads(received)
            new_msg_obj = await self.save_chat_msg(loaded_dict)
            response = {
                # "type": "msg",
                "nonce": loaded_dict["nonce"],
                "msg_data": MessageSerializer(
                    new_msg_obj,
                    context = {'profile_flds': ('profile_pic', 'fave_color')}
                ).data,
            }
            await self.channel_layer.group_send(self.t_name, {
                "type": "chat_message",
                "text": json.dumps(response)
            })

    async def chat_message(self, event):
        await self.send({
            "type": "websocket.send",
            "text": event["text"]
        })
        
    async def websocket_disconnect(self, event):
        print("---------------disconnected", event)

    # async def respondWithErr(self):
    #     await self.channel_layer.group_send(self.t_name, {
    #         "type": "chat_message",
    #         "text": json.dumps({
    #             "nonce": loaded_dict["nonce"],
    #             "type": 'error'
    #         })
    #     })

    @database_sync_to_async
    def get_room(self, id):
        try:
            return Room.objects.get(id = id)
        except:
            raise excpt.DenyConnection

    @database_sync_to_async
    def save_chat_msg(self, received):
        msg_content = received["c__content"]
        msg_type = received["c__msg_type"]
        if msg_type == 11:
            try:
                emote = Icon.objects.get(id = msg_content)
            except Icon.DoesNotExist:
                raise excpt.RequestAborted
            if not Membership.check_member(emote.belongs_to, self.me):
                raise excpt.RequestAborted
            msg_content = emote.img_src

        return Message.objects.create(
            thread = self.thread_obj,
            author = self.me,
            content = msg_content,
            msg_type = msg_type,
        )
