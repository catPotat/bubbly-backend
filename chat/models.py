from django.db import models
from django.db.models import Q, Max

from accounts.models import User
from communities.models import Community, Membership

class RoomManager(models.Manager):
    def create_room(self, creator):
        new = self.create( )
        Roommate.objects.create(room=new, identity=creator, is_admin=True)
        Message.objects.create(
            thread = new,
            author = creator,
            msg_type = 8,
            content = "Say hi",
        )
        return new

    def create_direct(self, you, them):
        new_room = self.create_room(creator=you)
        Roommate.objects.create(room=new_room, identity=them, is_admin=True)
        Direct.objects.create(room=new_room, u1=you ,u2=them)
        return new_room

class Room(models.Model):
    # CUSTOMIZING
    name = models.CharField(max_length=120, null=True, blank=True)
    bg_img = models.CharField(max_length=255, null=True, blank=True)
    # END OF CUSTOMIZING

    objects = RoomManager()
    @property
    def channels_layer_name(self):
        return f"thread_{self.id}"

    def has_room_perm(self, user, basic_perms=False):
        if not user.is_anonymous:
            roommate = self.roommate_set.filter(identity=user)
            if basic_perms:
                if roommate.exists():
                    return True
                if hasattr(self, 'publicroom'):
                    return Membership.check_member(
                        self.publicroom.associated_with,
                        user
                    )
            else:
                try:
                    return roommate.first().is_admin
                except IndexError: pass
        return False

    @staticmethod
    def get_direct(you, them):
        direct = Direct.objects.filter(
            Q(u1 = you) | Q(u1 = them),
            Q(u2 = you) | Q(u2 = them),
        )
        return direct.first()


class PublicRoomManager(models.Manager):
    def create_public(self, **kwargs):
        new_room = Room.objects.create_room(creator=kwargs['creator'])
        community = kwargs['community']

        current_big = self.filter(associated_with=community).aggregate(Max('order'))['order__max']
        return self.create(
            room = new_room,
            description = kwargs.get('description', "This is a community chat room"),
            associated_with = community,
            order = current_big + 1 if current_big else 1
        )
        return new_room

class PublicRoom(models.Model):
    room = models.OneToOneField(Room, on_delete=models.CASCADE, primary_key=True)
    description = models.TextField()
    associated_with = models.ForeignKey(Community, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    
    objects = PublicRoomManager()
    # class Meta:
    #     unique_together = ('associated_with', 'order')


class Direct(models.Model):
    room = models.OneToOneField(Room, on_delete=models.CASCADE, primary_key=True)
    u1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='directs_as_u1')
    u2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='directs_as_u2')
    class Meta:
        unique_together = ('room', 'u1', 'u2')



class Roommate(models.Model):
    identity = models.ForeignKey(User, on_delete=models.CASCADE, related_name='joined_chats')
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False)
    enable_noti = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('room', 'identity')



class Message(models.Model):
    MESSAGE_TYPES = (
        (1, 'Text'),
        (2, 'Photo'),
        (3, 'Youtube Embed'),
        (4, 'Recording'),
        (5, 'Invited someone'),
        (6, 'Changed chat name'),
        (7, 'Changed chat background'),
        (8, 'Made the room'),
        (9, 'Left room'),
        (10, 'Msg Deleted'),
        (11, 'Emote'),
        (12, 'Hyperlink'),
    )
    
    id = models.BigAutoField(primary_key=True)
    thread = models.ForeignKey(Room, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    msg_type = models.SmallIntegerField(choices=MESSAGE_TYPES, default=1)
    content = models.TextField()
    
    class Meta:
        ordering = ('-timestamp',)