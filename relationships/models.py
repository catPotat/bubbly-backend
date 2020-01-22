from django.db import models

from accounts.models import User


class Relationship(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='from_user')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follows')
    timestamp = models.DateTimeField(auto_now=True, db_index=True)
    # friendship_level = models.IntegerField
    
        
class Block(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks')
    got_blokt = models.ForeignKey(User, on_delete=models.CASCADE, related_name='got_blokt')
    timestamp = models.DateTimeField(auto_now=True)

    @classmethod
    def blocked(cls, blocker, to_user):
        return cls.objects.filter(
            blocker = blocker,
            got_blokt = to_user
        ).exists()

    class Meta:
        unique_together = ('blocker', 'got_blokt')