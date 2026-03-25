from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


def _set_auth_cookies(response, refresh_token, remember_me: bool = True):
    jwt_settings = settings.SIMPLE_JWT
    secure = jwt_settings.get("AUTH_COOKIE_SECURE", False)
    http_only = jwt_settings.get("AUTH_COOKIE_HTTP_ONLY", True)
    samesite = jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax")

    access_lifetime = jwt_settings["ACCESS_TOKEN_LIFETIME"]
    refresh_lifetime = jwt_settings["REFRESH_TOKEN_LIFETIME"]
    refresh_max_age = int(refresh_lifetime.total_seconds()) if remember_me else None

    response.set_cookie(
        jwt_settings.get("AUTH_COOKIE", "access_token"),
        str(refresh_token.access_token),
        max_age=int(access_lifetime.total_seconds()),
        secure=secure,
        httponly=http_only,
        samesite=samesite,
    )
    response.set_cookie(
        jwt_settings.get("AUTH_COOKIE_REFRESH", "refresh_token"),
        str(refresh_token),
        max_age=refresh_max_age,  # None = session cookie (expires on browser close)
        secure=secure,
        httponly=http_only,
        samesite=samesite,
    )
    # Non-sensitive preference cookie so RefreshView can preserve the setting
    response.set_cookie(
        "remember_me",
        "1" if remember_me else "0",
        max_age=refresh_max_age,
        secure=secure,
        httponly=False,
        samesite=samesite,
    )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        response = Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        _set_auth_cookies(response, refresh)
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        remember_me = bool(request.data.get("remember_me", False))
        response = Response(UserSerializer(user).data)
        _set_auth_cookies(response, refresh, remember_me=remember_me)
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response({"detail": "Logged out"})
        jwt_settings = settings.SIMPLE_JWT
        response.delete_cookie(jwt_settings.get("AUTH_COOKIE", "access_token"))
        response.delete_cookie(jwt_settings.get("AUTH_COOKIE_REFRESH", "refresh_token"))
        response.delete_cookie("remember_me")
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        jwt_settings = settings.SIMPLE_JWT
        refresh_cookie = jwt_settings.get("AUTH_COOKIE_REFRESH", "refresh_token")
        raw_refresh = request.COOKIES.get(refresh_cookie)
        if not raw_refresh:
            return Response(
                {"detail": "No refresh token"}, status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            refresh = RefreshToken(raw_refresh)
            remember_me = request.COOKIES.get("remember_me", "1") == "1"
            response = Response({"detail": "Token refreshed"})
            _set_auth_cookies(response, refresh, remember_me=remember_me)
            return response
        except Exception:
            return Response(
                {"detail": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED
            )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
