from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from materials.models import Course
from users.models import Subscription


@shared_task
def send_course_update_notification(course_id):
    """
    Асинхронная отправка уведомлений об обновлении курса
    """
    try:
        course = Course.objects.get(id=course_id)
        subscriptions = Subscription.objects.filter(course=course).select_related(
            "user"
        )

        emails = [sub.user.email for sub in subscriptions if sub.user.email]

        if emails:
            subject = f'Обновление курса "{course.name}"'
            message = f"""
            Здравствуйте!

            Курс "{course.name}" был обновлен. Проверьте новые материалы!

            Ссылка на курс: {settings.DOMAIN}/courses/{course.id}/

            С уважением,
            Команда LMS System
            """

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=emails,
                fail_silently=False,
            )

            return (
                f"Уведомления отправлены {len(emails)} подписчикам курса {course.name}"
            )
        return "Нет подписчиков для уведомления"

    except Course.DoesNotExist:
        return "Курс не найден"
    except Exception as e:
        return f"Ошибка отправки уведомлений: {str(e)}"
