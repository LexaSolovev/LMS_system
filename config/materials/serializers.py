from rest_framework import serializers
from materials.models import Course, Lesson


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'name', 'description', 'preview', 'video_link', 'course']


class LessonShortSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для вложенного отображения уроков в курсе"""

    class Meta:
        model = Lesson
        fields = ['id', 'name', 'description', 'preview', 'video_link']


class CourseSerializer(serializers.ModelSerializer):
    lessons_count = serializers.SerializerMethodField()
    lessons = LessonShortSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'name', 'preview', 'description', 'lessons_count', 'lessons']

    def get_lessons_count(self, obj):
        return obj.lessons.count()