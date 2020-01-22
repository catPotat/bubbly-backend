from django.contrib import admin

# Register your models here.
from .models import Room, Roommate, Message, Direct, PublicRoom

admin.site.register(Room)
admin.site.register(Roommate)
admin.site.register(Message)
admin.site.register(Direct)
admin.site.register(PublicRoom)