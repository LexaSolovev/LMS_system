from django.urls import path
from materials.views import (
    LessonListAPIView,
    LessonCreateAPIView,
    LessonRetrieveAPIView,
    LessonUpdateAPIView,
    LessonDestroyAPIView,
)

urlpatterns = [
    path("", LessonListAPIView.as_view(), name="lesson-list"),
    path("create/", LessonCreateAPIView.as_view(), name="lesson-create"),
    path("<int:pk>/", LessonRetrieveAPIView.as_view(), name="lesson-detail"),
    path("<int:pk>/update/", LessonUpdateAPIView.as_view(), name="lesson-update"),
    path("<int:pk>/delete/", LessonDestroyAPIView.as_view(), name="lesson-delete"),
]
