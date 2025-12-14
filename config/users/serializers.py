from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from users.models import Payment, User

from users.models import Subscription

from materials.serializers import CourseSerializer

from users.services import StripeService


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["email", "password", "password2", "phone", "city", "avatar"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "phone", "city", "avatar", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class UserDetailSerializer(UserSerializer):
    payments = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["payments"]

    def get_payments(self, obj):
        from users.serializers import PaymentSerializer

        payments = obj.payments.all()[:5]
        return PaymentSerializer(payments, many=True).data


class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    course_name = serializers.CharField(source="paid_course.name", read_only=True)
    lesson_name = serializers.CharField(source="paid_lesson.name", read_only=True)
    checkout_url = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "user",
            "user_email",
            "payment_date",
            "paid_course",
            "course_name",
            "paid_lesson",
            "lesson_name",
            "amount",
            "payment_method",
            "status",
            "stripe_session_id",
            "checkout_url",
        ]
        read_only_fields = ["status", "stripe_session_id"]

    def get_checkout_url(self, obj):
        """
        Возвращает URL для оплаты через Stripe
        """
        if obj.stripe_session_id and obj.status == "pending":
            try:
                session = StripeService.retrieve_session(obj.stripe_session_id)
                return session.url
            except Exception:
                return None
        return None

    def create(self, validated_data):
        """
        Переопределяем создание платежа для интеграции со Stripe
        """
        # Создаем платеж
        payment = super().create(validated_data)

        # Если это оплата через Stripe, создаем сессию
        if payment.payment_method == "stripe":
            try:
                session = StripeService.create_payment_for_course_or_lesson(payment)
                payment.stripe_session_id = session.id
                payment.save()
                # URL для оплаты будет доступен через get_checkout_url
            except Exception as e:
                # Если ошибка при создании сессии, обновляем статус
                payment.status = "failed"
                payment.save()
                raise serializers.ValidationError(
                    f"Ошибка создания платежа в Stripe: {str(e)}"
                )

        return payment


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ["id", "user", "course", "subscribed_at"]
        read_only_fields = ["user", "subscribed_at"]


class CourseWithSubscriptionSerializer(CourseSerializer):
    """
    Расширенный сериализатор курса с информацией о подписке текущего пользователя
    """

    is_subscribed = serializers.SerializerMethodField()

    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + ["is_subscribed"]

    def get_is_subscribed(self, obj):
        """
        Проверяем, подписан ли текущий пользователь на этот курс
        """
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(user=request.user, course=obj).exists()
        return False
