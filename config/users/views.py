from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework.filters import OrderingFilter
from users.models import Payment, User
from users.serializers import (
    UserSerializer, UserDetailSerializer,
    UserRegistrationSerializer, PaymentSerializer
)
from users.permissions import IsOwner, IsModerator, IsOwnerOrModerator


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления пользователями.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserDetailSerializer
        return UserSerializer

    def get_permissions(self):
        """
        Настройка прав доступа для пользователей:
        - Создание (регистрация): доступно всем (AllowAny)
        - Список: только для админов
        - Детали, обновление, удаление: только сам пользователь или админ
        """
        if self.action == 'create':
            return [permissions.AllowAny()]
        elif self.action == 'list':
            return [permissions.IsAdminUser()]
        elif self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return [IsOwnerOrModerator | permissions.IsAdminUser]
        else:
            return [permissions.IsAuthenticated]

    def get_queryset(self):
        # Админы видят всех пользователей
        if self.request.user.is_staff:
            return User.objects.all()

        # Модераторы видят всех пользователей
        if self.request.user.groups.filter(name='moderators').exists():
            return User.objects.all()

        # Обычные пользователи видят только себя
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Получение профиля текущего пользователя"""
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Обновление профиля текущего пользователя"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRegistrationAPIView(generics.CreateAPIView):
    """
    Эндпоинт для регистрации новых пользователей.
    Доступен без авторизации.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class PaymentFilter(FilterSet):
    class Meta:
        model = Payment
        fields = {
            'paid_course': ['exact'],
            'paid_lesson': ['exact'],
            'payment_method': ['exact'],
            'payment_date': ['gte', 'lte', 'exact'],
            'amount': ['gte', 'lte', 'exact'],
        }


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для платежей с расширенной фильтрацией.
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ['payment_date', 'amount']
    ordering = ['-payment_date']

    def get_permissions(self):
        """
        Настройка прав доступа для платежей:
        - Создание: только аутентифицированные пользователи
        - Список, детали: владелец или модератор
        - Обновление, удаление: только владелец
        """
        if self.action == 'create':
            self.permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['list', 'retrieve']:
            self.permission_classes = [IsOwnerOrModerator]
        elif self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsOwner]
        else:
            self.permission_classes = [permissions.IsAuthenticated]

        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Payment.objects.none()

        # Модераторы видят все платежи
        if user.groups.filter(name='moderators').exists():
            return Payment.objects.select_related('user', 'paid_course', 'paid_lesson').all()

        # Обычные пользователи видят только свои платежи
        return Payment.objects.filter(user=user).select_related('user', 'paid_course', 'paid_lesson')

    def perform_create(self, serializer):
        """Автоматически привязываем пользователя при создании платежа"""
        serializer.save(user=self.request.user)