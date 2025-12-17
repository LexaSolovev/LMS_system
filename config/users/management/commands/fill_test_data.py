from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.hashers import make_password
from users.models import User, Payment
from materials.models import Course, Lesson
from decimal import Decimal
import random
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = "Заполняет базу данных тестовыми данными для LMS системы"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Очистить существующие данные перед заполнением",
        )

    def handle(self, *args, **options):
        clear_data = options.get("clear", False)

        if clear_data:
            self.clear_existing_data()

        self.create_groups()
        self.create_users()
        self.create_courses()
        self.create_lessons()
        self.create_payments()

        self.stdout.write(self.style.SUCCESS("✅ Тестовые данные успешно созданы!"))

    def clear_existing_data(self):
        """Очистка существующих данных"""
        self.stdout.write("Очистка существующих данных...")

        Payment.objects.all().delete()
        Lesson.objects.all().delete()
        Course.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        Group.objects.filter(name="moderators").delete()

        self.stdout.write("✅ Существующие данные очищены")

    def create_groups(self):
        """Создание группы модераторов с правами"""
        self.stdout.write("Создание группы модераторов...")

        moderators_group, created = Group.objects.get_or_create(name="moderators")

        # Получаем разрешения для моделей
        course_content_type = ContentType.objects.get_for_model(Course)
        lesson_content_type = ContentType.objects.get_for_model(Lesson)
        payment_content_type = ContentType.objects.get_for_model(Payment)

        # Разрешения для модераторов (просмотр и изменение, но не создание и удаление)
        course_permissions = Permission.objects.filter(
            content_type=course_content_type,
            codename__in=["view_course", "change_course"],
        )
        lesson_permissions = Permission.objects.filter(
            content_type=lesson_content_type,
            codename__in=["view_lesson", "change_lesson"],
        )
        payment_permissions = Permission.objects.filter(
            content_type=payment_content_type, codename__in=["view_payment"]
        )

        # Добавляем разрешения в группу
        all_permissions = (
            list(course_permissions)
            + list(lesson_permissions)
            + list(payment_permissions)
        )
        moderators_group.permissions.set(all_permissions)

        self.stdout.write("✅ Группа модераторов создана")

    def create_users(self):
        """Создание тестовых пользователей"""
        self.stdout.write("Создание тестовых пользователей...")

        users_data = [
            {
                "email": "user1@example.com",
                "password": "password123",
                "first_name": "Иван",
                "last_name": "Петров",
                "phone": "+79161234567",
                "city": "Москва",
                "is_superuser": False,
                "is_staff": False,
                "is_moderator": False,
            },
            {
                "email": "user2@example.com",
                "password": "password123",
                "first_name": "Мария",
                "last_name": "Сидорова",
                "phone": "+79167654321",
                "city": "Санкт-Петербург",
                "is_superuser": False,
                "is_staff": False,
                "is_moderator": False,
            },
            {
                "email": "admin@example.com",
                "password": "admin123",
                "first_name": "Админ",
                "last_name": "Админов",
                "phone": "+79031112233",
                "city": "Москва",
                "is_superuser": True,
                "is_staff": True,
                "is_moderator": False,
            },
            {
                "email": "moderator@example.com",
                "password": "moderator123",
                "first_name": "Модератор",
                "last_name": "Модераторов",
                "phone": "+79032223344",
                "city": "Казань",
                "is_superuser": False,
                "is_staff": False,
                "is_moderator": True,
            },
        ]

        created_users = {}

        for user_data in users_data:
            user, created = User.objects.get_or_create(
                email=user_data["email"],
                defaults={
                    "password": make_password(user_data["password"]),
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                    "phone": user_data["phone"],
                    "city": user_data["city"],
                    "is_superuser": user_data["is_superuser"],
                    "is_staff": user_data["is_staff"],
                    "is_active": True,
                },
            )

            if user_data["is_moderator"]:
                moderators_group = Group.objects.get(name="moderators")
                user.groups.add(moderators_group)

            created_users[user_data["email"]] = user

            if created:
                self.stdout.write(f"   ✅ Создан пользователь: {user.email}")
            else:
                self.stdout.write(f"   ⚠️  Пользователь уже существует: {user.email}")

        self.stdout.write("✅ Тестовые пользователи созданы")
        return created_users

    def create_courses(self):
        """Создание тестовых курсов"""
        self.stdout.write("Создание тестовых курсов...")

        users = User.objects.filter(
            email__in=["user1@example.com", "user2@example.com"]
        )
        user1 = users.get(email="user1@example.com")
        user2 = users.get(email="user2@example.com")

        courses_data = [
            {
                "name": "Python для начинающих",
                "description": "Базовый курс по программированию на Python. Изучите основы языка и создайте свои первые проекты.",
                "owner": user1,
            },
            {
                "name": "Django Framework",
                "description": "Полный курс по веб-разработке на Django. Создавайте мощные веб-приложения с ORM, шаблонами и формами.",
                "owner": user2,
            },
            {
                "name": "JavaScript современный",
                "description": "Изучение JavaScript и современных фреймворков. От основ до продвинутых тем включая ES6+, React и Node.js.",
                "owner": user1,
            },
            {
                "name": "Базы данных и SQL",
                "description": "Полное руководство по работе с базами данных, SQL запросами и оптимизации.",
                "owner": user2,
            },
        ]

        created_courses = []

        for course_data in courses_data:
            course, created = Course.objects.get_or_create(
                name=course_data["name"], defaults=course_data
            )
            created_courses.append(course)

            if created:
                self.stdout.write(f"   ✅ Создан курс: {course.name}")
            else:
                self.stdout.write(f"   ⚠️  Курс уже существует: {course.name}")

        self.stdout.write("✅ Тестовые курсы созданы")
        return created_courses

    def create_lessons(self):
        """Создание тестовых уроков"""
        self.stdout.write("Создание тестовых уроков...")

        courses = Course.objects.all()
        users = User.objects.filter(
            email__in=["user1@example.com", "user2@example.com"]
        )
        user1 = users.get(email="user1@example.com")
        user2 = users.get(email="user2@example.com")

        lessons_data = [
            # Курс 1: Python для начинающих
            {
                "name": "Введение в Python",
                "description": "Основы синтаксиса Python, переменные, типы данных и первые программы.",
                "video_link": "https://youtube.com/watch?v=python_intro",
                "course": courses.get(name="Python для начинающих"),
                "owner": user1,
            },
            {
                "name": "Функции в Python",
                "description": "Создание и использование функций, параметры, возвращаемые значения и области видимости.",
                "video_link": "https://youtube.com/watch?v=python_functions",
                "course": courses.get(name="Python для начинающих"),
                "owner": user1,
            },
            {
                "name": "Классы и ООП",
                "description": "Объектно-ориентированное программирование в Python: классы, наследование, полиморфизм.",
                "video_link": "https://youtube.com/watch?v=python_oop",
                "course": courses.get(name="Python для начинающих"),
                "owner": user1,
            },
            # Курс 2: Django Framework
            {
                "name": "Основы Django",
                "description": "Знакомство с фреймворком Django, создание первого приложения и настройка проекта.",
                "video_link": "https://youtube.com/watch?v=django_basics",
                "course": courses.get(name="Django Framework"),
                "owner": user2,
            },
            {
                "name": "Модели в Django",
                "description": "Работа с моделями и базой данных в Django, миграции и ORM.",
                "video_link": "https://youtube.com/watch?v=django_models",
                "course": courses.get(name="Django Framework"),
                "owner": user2,
            },
            {
                "name": "Django REST Framework",
                "description": "Создание API с помощью Django REST Framework, сериализаторы и ViewSets.",
                "video_link": "https://youtube.com/watch?v=django_rest",
                "course": courses.get(name="Django Framework"),
                "owner": user2,
            },
            # Курс 3: JavaScript современный
            {
                "name": "JavaScript основы",
                "description": "Синтаксис и основные конструкции JavaScript: переменные, функции, циклы.",
                "video_link": "https://youtube.com/watch?v=javascript_basics",
                "course": courses.get(name="JavaScript современный"),
                "owner": user1,
            },
            {
                "name": "ES6+ Нововведения",
                "description": "Современный JavaScript: стрелочные функции, деструктуризация, шаблонные строки.",
                "video_link": "https://youtube.com/watch?v=javascript_es6",
                "course": courses.get(name="JavaScript современный"),
                "owner": user1,
            },
            # Курс 4: Базы данных и SQL
            {
                "name": "Введение в SQL",
                "description": "Основы SQL: SELECT, INSERT, UPDATE, DELETE запросы и работа с таблицами.",
                "video_link": "https://youtube.com/watch?v=sql_intro",
                "course": courses.get(name="Базы данных и SQL"),
                "owner": user2,
            },
            {
                "name": "JOIN и агрегатные функции",
                "description": "Сложные SQL запросы: JOIN, GROUP BY, агрегатные функции и подзапросы.",
                "video_link": "https://youtube.com/watch?v=sql_advanced",
                "course": courses.get(name="Базы данных и SQL"),
                "owner": user2,
            },
        ]

        for lesson_data in lessons_data:
            lesson, created = Lesson.objects.get_or_create(
                name=lesson_data["name"],
                course=lesson_data["course"],
                defaults=lesson_data,
            )

            if created:
                self.stdout.write(
                    f"   ✅ Создан урок: {lesson.name} ({lesson.course.name})"
                )
            else:
                self.stdout.write(f"   ⚠️  Урок уже существует: {lesson.name}")

        self.stdout.write("✅ Тестовые уроки созданы")

    def create_payments(self):
        """Создание тестовых платежей"""
        self.stdout.write("Создание тестовых платежей...")

        users = User.objects.all()
        courses = Course.objects.all()
        lessons = Lesson.objects.all()

        payment_methods = ["cash", "transfer"]
        amounts = [
            Decimal("1000.00"),
            Decimal("2500.00"),
            Decimal("5000.00"),
            Decimal("7500.00"),
        ]

        payments_data = [
            # Платежи user1
            {
                "user": users.get(email="user1@example.com"),
                "paid_course": courses.get(name="Python для начинающих"),
                "paid_lesson": None,
                "amount": Decimal("5000.00"),
                "payment_method": "transfer",
            },
            {
                "user": users.get(email="user1@example.com"),
                "paid_course": None,
                "paid_lesson": lessons.get(name="Основы Django"),
                "amount": Decimal("1000.00"),
                "payment_method": "cash",
            },
            {
                "user": users.get(email="user1@example.com"),
                "paid_course": courses.get(name="JavaScript современный"),
                "paid_lesson": None,
                "amount": Decimal("6000.00"),
                "payment_method": "transfer",
            },
            # Платежи user2
            {
                "user": users.get(email="user2@example.com"),
                "paid_course": courses.get(name="Django Framework"),
                "paid_lesson": None,
                "amount": Decimal("7500.00"),
                "payment_method": "transfer",
            },
            {
                "user": users.get(email="user2@example.com"),
                "paid_course": None,
                "paid_lesson": lessons.get(name="JavaScript основы"),
                "amount": Decimal("1500.00"),
                "payment_method": "cash",
            },
            # Платежи moderator
            {
                "user": users.get(email="moderator@example.com"),
                "paid_course": courses.get(name="Python для начинающих"),
                "paid_lesson": None,
                "amount": Decimal("5000.00"),
                "payment_method": "transfer",
            },
            # Платежи admin
            {
                "user": users.get(email="admin@example.com"),
                "paid_course": courses.get(name="Базы данных и SQL"),
                "paid_lesson": None,
                "amount": Decimal("4500.00"),
                "payment_method": "transfer",
            },
        ]

        # Случайные платежи для разнообразия
        for i in range(10):
            user = random.choice(list(users))
            payment_method = random.choice(payment_methods)
            amount = random.choice(amounts)

            # Случайно выбираем оплату курса или урока
            paid_course = None
            paid_lesson = None

            if random.choice([True, False]):
                paid_course = random.choice(list(courses))
            else:
                paid_lesson = random.choice(list(lessons))

            # Случайная дата в последние 30 дней
            random_days = random.randint(0, 30)
            payment_date = datetime.now() - timedelta(days=random_days)

            payments_data.append(
                {
                    "user": user,
                    "paid_course": paid_course,
                    "paid_lesson": paid_lesson,
                    "amount": amount,
                    "payment_method": payment_method,
                    "payment_date": payment_date
                }
            )

        for payment_data in payments_data:
            payment = Payment.objects.create(**payment_data)
            self.stdout.write(
                f"   ✅ Создан платеж: {payment.amount} руб. - {payment.user.email}"
            )

        self.stdout.write("✅ Тестовые платежи созданы")
