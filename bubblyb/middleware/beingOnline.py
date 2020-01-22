from django.utils.timezone import now
from django.core.cache import cache

class ActiveUserMiddleware:
    def process_request(self, request):
        current_user = request.user
        if request.user.is_authenticated():
            cache.set(
                'seen_%s' % (current_user.username),
                now(),
                60 * 60 * 24 * 7
                    # Number of seconds that we will keep track of inactive users for before 
                    # their last seen is removed from the cache
            )