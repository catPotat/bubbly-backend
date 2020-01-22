from django.contrib import admin

from .models import Content, Attachment, Post, Comment

admin.site.register(Content)
admin.site.register(Attachment)
admin.site.register(Post)
admin.site.register(Comment)