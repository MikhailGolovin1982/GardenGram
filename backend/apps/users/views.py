from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse  # ← добавили
from .serializers import RegisterSerializer


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(                              # ← добавили
        request=RegisterSerializer,              # тело запроса берётся из сериализатора
        responses={201: OpenApiResponse(response=None, description="User created"),
                   400: OpenApiResponse(response=None, description="Validation error")},
        description="Register a new user (username, email, password).",
        tags=["auth"]
    )
    def post(self, request):
        s = RegisterSerializer(data=request.data)
        if s.is_valid():
            user = s.save()
            return Response(
                {"id": user.id, "username": user.username, "email": user.email},
                status=status.HTTP_201_CREATED
            )
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)