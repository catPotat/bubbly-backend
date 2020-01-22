from django.contrib import admin
from django.contrib.auth.models import Group
from .models import User
from relationships.models import Relationship

admin.site.unregister(Group)
admin.site.register(User)
admin.site.register(Relationship)