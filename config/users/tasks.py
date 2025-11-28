from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()


@shared_task
def block_inactive_users():
    """
    Блокировка пользователей, не заходивших более месяца
    """
    try:
        one_month_ago = timezone.now() - timedelta(days=30)

        # Находим активных пользователей, которые не заходили более месяца
        inactive_users = User.objects.filter(
            last_login__lt=one_month_ago, is_active=True
        )

        count = inactive_users.count()

        # Блокируем пользователей
        inactive_users.update(is_active=False)

        return f"Заблокировано {count} неактивных пользователей"

    except Exception as e:
        return f"Ошибка при блокировке пользователей: {str(e)}"
