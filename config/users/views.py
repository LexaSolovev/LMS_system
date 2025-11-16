from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework.filters import OrderingFilter
from rest_framework.views import APIView
from users.models import Payment, User, Subscription
from users.serializers import (
    UserSerializer, UserDetailSerializer,
    UserRegistrationSerializer, PaymentSerializer
)
from users.permissions import IsOwner, IsModerator, IsOwnerOrModerator

from materials.models import Course, Lesson

from materials.paginators import LessonCoursePagination
from users.services import StripeService

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
    pagination_class = LessonCoursePagination

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

    @action(detail=False, methods=['post'])
    def create_stripe_payment(self, request):
        """
        Создание платежа через Stripe
        """
        course_id = request.data.get('course_id')
        lesson_id = request.data.get('lesson_id')

        if not course_id and not lesson_id:
            return Response(
                {"error": "Необходимо указать course_id или lesson_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if course_id and lesson_id:
            return Response(
                {"error": "Можно указать только курс ИЛИ урок"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Получаем курс или урок
        if course_id:
            item = get_object_or_404(Course, id=course_id)
            amount = item.price
        else:
            item = get_object_or_404(Lesson, id=lesson_id)
            amount = item.price

        # Создаем платеж
        payment_data = {
            'user': request.user.id,
            'amount': amount,
            'payment_method': 'stripe'
        }

        if course_id:
            payment_data['paid_course'] = course_id
        else:
            payment_data['paid_lesson'] = lesson_id

        serializer = self.get_serializer(data=payment_data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PaymentSuccessView(APIView):
    """
    Обработка успешной оплаты
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        session_id = request.GET.get('session_id')

        if not session_id:
            return Response(
                {"error": "Не указан session_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Получаем информацию о сессии из Stripe
            session = StripeService.retrieve_session(session_id)

            # Находим соответствующий платеж
            payment = Payment.objects.get(stripe_session_id=session_id)

            # Проверяем, что платеж принадлежит текущему пользователю
            if payment.user != request.user:
                return Response(
                    {"error": "Доступ запрещен"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Обновляем статус платежа
            if session.payment_status == 'paid':
                payment.status = 'succeeded'
                payment.stripe_payment_intent_id = session.payment_intent
                payment.save()

                return Response({
                    "message": "Оплата прошла успешно",
                    "payment_id": payment.id,
                    "item": payment.paid_course.name if payment.paid_course else payment.paid_lesson.name
                })
            else:
                return Response({
                    "message": "Статус оплаты неизвестен",
                    "payment_status": session.payment_status
                })

        except Payment.DoesNotExist:
            return Response(
                {"error": "Платеж не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Ошибка при обработке платежа: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentCancelView(APIView):
    """
    Обработка отмены оплаты
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "message": "Оплата была отменена. Вы можете попробовать снова."
        })


class PaymentStatusView(APIView):  # NEW
    """
    Проверка статуса платежа
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)

        # Проверяем права доступа
        if payment.user != request.user and not request.user.is_staff:
            return Response(
                {"error": "Доступ запрещен"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Если платеж через Stripe, обновляем статус
        if payment.stripe_session_id and payment.status == 'pending':
            try:
                session = StripeService.retrieve_session(payment.stripe_session_id)
                if session.payment_status == 'paid' and payment.status != 'succeeded':
                    payment.status = 'succeeded'
                    payment.stripe_payment_intent_id = session.payment_intent
                    payment.save()
            except Exception:
                # Если не удалось получить статус, оставляем текущий
                pass

        serializer = PaymentSerializer(payment)
        return Response(serializer.data)


class SubscriptionAPIView(APIView):
    """
    APIView для управления подпиской на курс
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        course_id = request.data.get('course_id')

        if not course_id:
            return Response(
                {"error": "course_id обязателен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        course = get_object_or_404(Course, id=course_id)
        subscription = Subscription.objects.filter(user=user, course=course)

        if subscription.exists():
            # Если подписка есть - удаляем ее
            subscription.delete()
            message = 'Подписка удалена'
        else:
            # Если подписки нет - создаем ее
            Subscription.objects.create(user=user, course=course)
            message = 'Подписка добавлена'

        return Response({"message": message})