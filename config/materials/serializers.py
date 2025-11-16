from rest_framework import serializers
from materials.models import Course, Lesson

from materials.validators import validate_no_external_links


class LessonSerializer(serializers.ModelSerializer):
    video_link = serializers.URLField(
        validators=[validate_no_external_links],
        required=False,
        allow_null=True,
        allow_blank=True
    )
    description = serializers.CharField(
        validators=[validate_no_external_links],
        required=False,
        allow_blank=True
    )

    class Meta:
        model = Lesson
        fields = '__all__'
        read_only_fields = ['owner']


class CourseSerializer(serializers.ModelSerializer):
    lessons_count = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)

    description = serializers.CharField(
        validators=[validate_no_external_links],
        required=False,
        allow_blank=True
    )

    class Meta:
        model = Course
        fields = ['id', 'name', 'preview', 'description', 'lessons_count', 'lessons', 'owner']
        read_only_fields = ['owner']

    def get_lessons_count(self, obj):
        return obj.lessons.count()