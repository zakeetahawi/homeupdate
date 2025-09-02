from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings
from rest_framework.authentication import CSRFCheck
from rest_framework import exceptions

class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        try:
            header = self.get_header(request)
            if header is None:
                # Try to get token from cookies
                raw_token = request.COOKIES.get(settings.SIMPLE_JWT.get('AUTH_COOKIE'))
                if raw_token is None:
                    return None
            else:
                raw_token = self.get_raw_token(header)
                if raw_token is None:
                    return None

            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            self._enforce_csrf(request)
            
            return user, validated_token
            
        except (InvalidToken, TokenError) as e:
            raise exceptions.AuthenticationFailed(str(e))
        except Exception as e:
            return None

    def _enforce_csrf(self, request):
        """
        Enforce CSRF validation for session based authentication.
        """
        def dummy_get_response(request):
            return None
        check = CSRFCheck(dummy_get_response)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied('CSRF Failed: %s' % reason)
