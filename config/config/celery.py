import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Периодические задачи
app.conf.beat_schedule = {
    'check-inactive-users-monthly': {
        'task': 'users.tasks.block_inactive_users',
        'schedule': crontab(day_of_month='1', hour=0, minute=0),  # Первое число каждого месяца
    },
}

app.conf.timezone = 'UTC'