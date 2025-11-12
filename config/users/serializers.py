from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from users.models import Payment, User

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'password2', 'phone', 'city', 'avatar']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'city', 'avatar', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class UserDetailSerializer(UserSerializer):
    payments = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['payments']

    def get_payments(self, obj):
        from users.serializers import PaymentSerializer
        payments = obj.payments.all()[:5]
        return PaymentSerializer(payments, many=True).data

class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    course_name = serializers.CharField(source='paid_course.name', read_only=True)
    lesson_name = serializers.CharField(source='paid_lesson.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'payment_date',
            'paid_course', 'course_name', 'paid_lesson', 'lesson_name',
            'amount', 'payment_method'
        ]
