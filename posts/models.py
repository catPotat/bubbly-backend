from django.db import models
from django.utils.functional import cached_property

from accounts.models import User
from communities.models import Community

from django.utils.text import slugify
import random, string
from bubblyb.utils import tiengVietKhongDau


class ContentManager(models.Manager):
    def create_attachments(self, content, attachments_data):
        for attachment_data in attachments_data:
            Attachment.objects.create(to=content, **attachment_data)

class Content(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    edited = models.DateTimeField(blank=True, null=True, default=None)
    text = models.TextField(default="")
    @cached_property
    def allocated_to(self): # bruh?
        p = self.post if hasattr(self, 'post') else \
            self.comment if hasattr(self, 'comment') else \
            self.pinnedpost if hasattr(self, 'pinnedpost') else Post.objects.get(content_id=1)
        return p.allocated_to

    objects = ContentManager()

class Attachment(models.Model):
    ATCH_TYPE = (
        (1, 'Text'),
        (2, 'Photo'),
        (3, 'Youtube_embed'),
        (4, 'Emote'),
        (5, 'Twitter_embed'),
    )
    type = models.PositiveSmallIntegerField(choices=ATCH_TYPE)
    content = models.TextField()
    to = models.ForeignKey(Content, on_delete=models.CASCADE)
    order = models.SmallIntegerField()

    class Meta:
        ordering = ('order',)


class Post(models.Model):
    slug = models.CharField(max_length=20, unique=True, blank=True)
    title = models.CharField(max_length=120, blank=True, default="")
    allocated_to = models.ForeignKey(Community, on_delete=models.CASCADE)
    content = models.OneToOneField(Content, on_delete=models.CASCADE, primary_key=True)
    is_nsfw = models.BooleanField(default=False)
    # background_image decor or something
    # tags = models.ManyToManyField(Tag)
    @property
    def author(self):
        return self.content.author

    hot_score = models.IntegerField(default=0)

    def _get_unique_slug(self):
        if self.title:
            unique_slug = slugify( tiengVietKhongDau(self.title) )
        else:
            unique_slug = \
            f'{slugify(tiengVietKhongDau(self.content.author.alias))}-{self.pk}'
            
        if Post.objects.filter(slug=unique_slug).exists():
            unique_slug = f'{unique_slug}-{self.pk}'
        return unique_slug

    def save(self, *args, **kwargs):
        self.slug = self._get_unique_slug()
        super().save(*args, **kwargs)


class Comment(models.Model):
    on = models.ForeignKey(Post, on_delete=models.CASCADE)
    reply_to = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, default=None)
    content = models.OneToOneField(Content, on_delete=models.CASCADE, primary_key=True)
    @property
    def allocated_to(self):
        return self.on.allocated_to
    @property
    def author(self):
        return self.content.author



class PinnedPost(models.Model):
    '''For communities. Act as anouncements, info, etc'''
    content = models.OneToOneField(Content, on_delete=models.CASCADE, primary_key=True)
    allocated_to = models.ForeignKey(Community, on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField()
    
    class Meta:
        ordering = ('order',)
        # unique_together = ('allocated_to', 'order')
