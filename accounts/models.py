from django.db import models
#from django.conf import settings #settings.AUTH_USER_MODEL

from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin,
)

from django.core.cache import cache
from django.utils.timezone import now
import random, string

class UserManager(BaseUserManager):
    def create_user(self, **fields):
        user = self.model(
            email = self.normalize_email(fields.pop('email')),
            alias = fields.pop('alias', fields['username']),
            **fields
        )
        user.set_password(fields['password'])
        user.save()
        return user

    def create_superuser(self, **fields):
        user = self.create_user(**fields)
        user.is_staff = True
        user.save()
        return user

    def get_by_username(self, username):
        try:
            return self.get(username=username)
        except User.DoesNotExist:
            return None


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=40, unique=True, primary_key=True)
    email = models.EmailField(max_length=120, unique=True) #get_email_field_name()
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # PROFILE FIELDS
    alias = models.CharField(max_length=40)
    fave_color = models.CharField(max_length=24, default="#0000ff")
    profile_pic = models.CharField(max_length=255,
        default="https://bubblyatch.s3.ap-east-1.amazonaws.com/dp.jpg")
    cover_photo = models.CharField(max_length=255, default="")
    bio = models.TextField(blank=True, default="")
    location = models.CharField(max_length=120, blank=True, default="")
    # END OF PROFILE FIELDS

    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    objects = UserManager()

    REQUIRED_FIELDS = []
    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'

    def __str__(self):
        return f"@{self.username}"

    def generate_reset_code(self):
        code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
        cache.set(
            'reqester_%s' % (self.username),
            code,
            60 * 15
        )
        return code
    @property
    def pw_reset_code(self):
        return cache.get('reqester_%s' % (self.username))
        
        
    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        return self.is_staff
    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        return self.is_staff

    # def last_seen(self):
    #     return cache.get('seen_%s' % self.username)
    # def online(self):
    #     if self.last_seen():
    #         now = datetime.datetime.now()
    #         if now > self.last_seen() + datetime.timedelta(
    #                     seconds=60*5):
    #             return False
    #         else:
    #             return True
    #     else:
    #         return False

# from django.contrib.auth.backends import ModelBackend
# class EmailBackend(ModelBackend):
#     def authenticate(self, username=None, password=None, **kwargs):
#         try:
#             user = User.objects.get(email=username) 
#         except User.DoesNotExist:
#             return None
#         else:
#             if user.check_password(password):
#                 return user
#         return None
