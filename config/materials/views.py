from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework.filters import SearchFilter, OrderingFilter
from materials.models import Course, Lesson
from materials.serializers import CourseSerializer, LessonSerializer
from users.permissions import IsOwner, IsModerator, IsOwnerOrModerator, IsOwnerOrModeratorForCreate, \
    IsOwnerOrModeratorForList

from django.utils import timezone
from datetime import timedelta

from users.serializers import CourseWithSubscriptionSerializer

from materials.paginators import LessonCoursePagination

from materials.tasks import send_course_update_notification

class LessonFilter(FilterSet):
    class Meta:
        model = Lesson
        fields = {
            'course': ['exact'],
            'name': ['icontains'],
        }


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'id', 'created_at']
    pagination_class = LessonCoursePagination

    def get_serializer_class(self):
        # Используем расширенный сериализатор с информацией о подписке
        if self.action == 'retrieve':
            return CourseWithSubscriptionSerializer
        return CourseSerializer

    def get_permissions(self):
        """
        Настройка прав доступа:
        - Создание: только аутентифицированные пользователи, которые НЕ модераторы
        - Список: аутентифицированные пользователи (модераторы видят все, обычные - только свои)
        - Детали, обновление: владелец или модератор
        - Удаление: только владелец (модераторы не могут удалять)
        """
        if self.action == 'create':
            self.permission_classes = [IsOwnerOrModeratorForCreate]
        elif self.action == 'list':
            self.permission_classes = [IsOwnerOrModeratorForList]
        elif self.action in ['retrieve', 'update', 'partial_update']:
            self.permission_classes = [IsOwnerOrModerator]
        elif self.action == 'destroy':
            self.permission_classes = [IsOwner]  # Только владелец может удалять
        else:
            self.permission_classes = [permissions.IsAuthenticated]

        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        """
        Фильтрация объектов:
        - Модераторы видят все курсы
        - Обычные пользователи видят только свои курсы
        """
        user = self.request.user

        if not user.is_authenticated:
            return Course.objects.none()

        # Модераторы видят все
        if user.groups.filter(name='moderators').exists():
            return Course.objects.prefetch_related('lessons').all()

        # Обычные пользователи видят только свои курсы
        return Course.objects.prefetch_related('lessons').filter(owner=user)

    def perform_create(self, serializer):
        """Автоматически назначаем владельца при создании курса"""
        serializer.save(owner=self.request.user)


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LessonFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'id', 'created_at']
    pagination_class = LessonCoursePagination

    def get_permissions(self):
        """
        Настройка прав доступа:
        - Создание: только аутентифицированные пользователи, которые НЕ модераторы
        - Список: аутентифицированные пользователи (модераторы видят все, обычные - только свои)
        - Детали, обновление: владелец или модератор
        - Удаление: только владелец (модераторы не могут удалять)
        """
        if self.action == 'create':
            self.permission_classes = [IsOwnerOrModeratorForCreate]
        elif self.action == 'list':
            self.permission_classes = [IsOwnerOrModeratorForList]
        elif self.action in ['retrieve', 'update', 'partial_update']:
            self.permission_classes = [IsOwnerOrModerator]
        elif self.action == 'destroy':
            self.permission_classes = [IsOwner]  # Только владелец может удалять
        else:
            self.permission_classes = [permissions.IsAuthenticated]

        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        """
        Фильтрация объектов:
        - Модераторы видят все уроки
        - Обычные пользователи видят только свои уроки
        """
        user = self.request.user

        if not user.is_authenticated:
            return Lesson.objects.none()

        # Модераторы видят все
        if user.groups.filter(name='moderators').exists():
            return Lesson.objects.select_related('course', 'owner').all()

        # Обычные пользователи видят только свои уроки
        return Lesson.objects.select_related('course', 'owner').filter(owner=user)

    def perform_create(self, serializer):
        """Автоматически назначаем владельца при создании урока"""
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        """
        Переопределяем обновление для отправки уведомлений
        """
        instance = self.get_object()
        old_updated_at = instance.updated_at

        # Сохраняем обновления
        super().perform_update(serializer)

        # Проверяем, что курс не обновлялся более 4 часов
        current_time = timezone.now()
        time_diff = current_time - old_updated_at

        if time_diff > timedelta(hours=4):
            # Отправляем уведомления асинхронно
            send_course_update_notification.delay(instance.id)