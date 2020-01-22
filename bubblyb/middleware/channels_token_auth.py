from channels.auth import AuthMiddlewareStack
from rest_framework_jwt.serializers import VerifyJSONWebTokenSerializer
from django.contrib.auth.models import AnonymousUser


class TokenAuthMiddleware:
    """
    Token authorization middleware for Django Channels 2
    """

    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        query_string = scope['query_string']
        #print(query_string)
        try:
            token = query_string[6:].decode()
            data = {'token': token}
            valid_data = VerifyJSONWebTokenSerializer().validate(data)
            # print(valid_data)
            user = valid_data['user']
            scope['user'] = user
        except:
            scope['user'] = AnonymousUser()
        return self.inner(scope)

TokenAuthMiddlewareStack = lambda inner: TokenAuthMiddleware(AuthMiddlewareStack(inner))