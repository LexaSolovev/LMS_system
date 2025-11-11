from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.exceptions import ValidationError


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(
        max_length=15, blank=True, null=True, verbose_name="Телефон"
    )
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Город")
    avatar = models.ImageField(
        upload_to="users/avatars/", blank=True, null=True, verbose_name="Аватарка"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Наличные'),
        ('transfer', 'Перевод на счет'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
        related_name="payments"
    )

    payment_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата оплаты"
    )

    paid_course = models.ForeignKey(
        'materials.Course',
        on_delete=models.CASCADE,
        verbose_name="Оплаченный курс",
        null=True,
        blank=True,
        related_name="payments"
    )

    paid_lesson = models.ForeignKey(
        'materials.Lesson',
        on_delete=models.CASCADE,
        verbose_name="Оплаченный урок",
        null=True,
        blank=True,
        related_name="payments"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Сумма оплаты"
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name="Способ оплаты"
    )

    def __str__(self):
        if self.paid_course:
            return f"Оплата курса {self.paid_course.name} - {self.user.email}"
        elif self.paid_lesson:
            return f"Оплата урока {self.paid_lesson.name} - {self.user.email}"
        return f"Оплата #{self.id} - {self.user.email}"

    def clean(self):
        if not self.paid_course and not self.paid_lesson:
            raise ValidationError("Должен быть указан либо курс, либо урок")
        if self.paid_course and self.paid_lesson:
            raise ValidationError("Можно указать только курс ИЛИ урок, но не оба одновременно")

    class Meta:
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"
        ordering = ['-payment_date']
