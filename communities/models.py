from django.db import models
from django.core.cache import cache 
from django.utils.functional import cached_property

from accounts.models import User

from random import choice
from string import ascii_lowercase

class Community(models.Model):
    id = models.CharField(max_length=30, primary_key=True)
    name = models.CharField(max_length=100)
    date_created = models.DateTimeField(auto_now_add=True)
    is_secret = models.BooleanField(default=False)
    invite_code = models.CharField(max_length=16, blank=True, null=True, default=None)
    @property
    def visibility(self):
        s = self.is_secret
        c = self.invite_code
        if not s and not c : return "public"
        if not s and c     : return "closed"
        if s and c         : return "secret"
        return "secret closed"
    @cached_property
    def member_count(self):
        return self.membership_set.count()

    # CUSTOMIZATION
    moto = models.CharField(max_length=255, blank=True, null=True)
    icon_img = models.CharField(max_length=255, default="")
    theme_color = models.CharField(max_length=6, default="0000ff")
    cover_img = models.CharField(max_length=255, default="")
    background_img = models.CharField(max_length=255, default="")
    # language = 
    # END OF CUSTOMIZATION

    def save(self, *args, **kwargs):
        def _get_unique_id():
            return ''.join(choice(ascii_lowercase) for i in range(8))
        if not self.id:
            self.id = _get_unique_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def has_cmty_perm(self, user, read_only=False):
        try: # maybe handle anon more gracefully?
            if read_only:
                if self.visibility in ('public', 'closed'):
                    return True
                return Membership.check_member(self, user)
            else:
                if self.visibility == 'public':
                    return Membership.check_member(self, user, Membership.VISITANT)
                return Membership.check_member(self, user) # can implement reputation check if desire
        except: pass
        return False


    class Meta:
        pass
        # referencing purpose
        # queryset = Photo.objects.all().order_by('-postTime')
        # resource_name = 'following'
        # fields = ['id', 'title', 'url', 'likes','postTime','photographer', 'location_id', 'location_name']
        # authentication = BasicAuthentication()
        # authorization = DjangoAuthorization()
        # serializer = Serializer(formats=['json'])
        # include_resource_uri = False
        # filtering = {
        #         'postTime': ALL,
        #         'photographer' : ALL_WITH_RELATIONS,
        # }



class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community= models.ForeignKey(Community, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(auto_now_add=True, db_index=True)
    reputation_point = models.PositiveIntegerField(default=1)

    BANNED = -100
    VISITANT = -10
    MEMBER = 10
    MODERATOR = 100
    ADMINISTRATOR = 200
    ROLE_LIST = (
        (BANNED, 'banned'),
        (VISITANT, 'visitant'),
        (MEMBER, 'member'),
        (MODERATOR, 'moderator'),
        (ADMINISTRATOR, 'administrator'),
    )
    role = models.SmallIntegerField(choices=ROLE_LIST, default=MEMBER)

    @staticmethod
    def get_joined_communities(user, role=MEMBER):
        qs = Community.objects.all()
        qs = qs.filter(membership__user=user, membership__role__gte=role)
        return qs
    @staticmethod
    def get_mutual_communities(you, them, role=MEMBER):
        qs = Community.objects.all()
        qs = qs.filter(membership__role__gte=role)
        qs = qs.filter(membership__user=you) & qs.filter(membership__user=them)
        return qs

    @classmethod
    def check_member(cls, community, user, checkRole=MEMBER):
        try:
            ship = cls.objects.get(community=community, user=user)
            if ship.role >= checkRole:
                return True
        except cls.DoesNotExist:
            if checkRole == cls.VISITANT:
                cls.objects.create(
                    community = community,
                    user = user,
                    role = checkRole
                )
                return True
        except: return False
        return False

# def raise_reputation(sender, **kwargs):
#     if kwargs['created']:
#         print(kwargs)
#         print("HEYY!!!!")

    class Meta:
        unique_together = ('user', 'community')



'''
class Flair(models.Model):
    for_member = models.ForeignKey(Membership, on_delete=models.CASCADE)
'''