from django.contrib import admin

from .models import Community, Membership
from posts.models import PinnedPost


admin.site.register(Community)
admin.site.register(Membership)
admin.site.register(PinnedPost)