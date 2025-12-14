from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from materials.models import Course, Lesson

User = get_user_model()


class LessonCRUDTestCase(APITestCase):
    """
    Тестирование CRUD операций для уроков с разными правами доступа
    """

    def setUp(self):
        """Заполнение базы данных тестовыми данными"""
        # Создаем пользователей с разными ролями
        self.owner_user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            first_name="Owner",
            last_name="User",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
            first_name="Other",
            last_name="User",
        )

        self.moderator_user = User.objects.create_user(
            email="moderator@example.com",
            password="testpass123",
            first_name="Moderator",
            last_name="User",
        )

        # Создаем группу модераторов и добавляем пользователя
        from django.contrib.auth.models import Group

        moderators_group, created = Group.objects.get_or_create(name="moderators")
        self.moderator_user.groups.add(moderators_group)

        # Создаем курс
        self.course = Course.objects.create(
            name="Test Course",
            description="Test Course Description",
            owner=self.owner_user,
        )

        # Создаем урок
        self.lesson = Lesson.objects.create(
            name="Test Lesson",
            description="Test Lesson Description",
            course=self.course,
            owner=self.owner_user,
            video_link="https://youtube.com/watch?v=test123",
        )

        # URL для тестирования
        self.lessons_list_url = "/api/materials/lessons/"
        self.lesson_detail_url = f"/api/materials/lessons/{self.lesson.id}/"

        # Клиент для запросов
        self.client = APIClient()

    def test_lesson_list_authenticated(self):
        """Тест получения списка уроков аутентифицированным пользователем"""
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.get(self.lessons_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Test Lesson")

    def test_lesson_list_unauthenticated(self):
        """Тест получения списка уроков неаутентифицированным пользователем"""
        response = self.client.get(self.lessons_list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_lesson_create_authenticated(self):
        """Тест создания урока аутентифицированным пользователем"""
        self.client.force_authenticate(user=self.owner_user)

        lesson_data = {
            "name": "New Lesson",
            "description": "New Lesson Description",
            "course": self.course.id,
            "video_link": "https://youtube.com/watch?v=new123",
        }

        response = self.client.post(self.lessons_list_url, lesson_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lesson.objects.count(), 2)
        self.assertEqual(response.data["name"], "New Lesson")
        self.assertEqual(response.data["owner"], self.owner_user.id)

    def test_lesson_create_moderator_forbidden(self):
        """Тест запрета создания урока модератором"""
        self.client.force_authenticate(user=self.moderator_user)

        lesson_data = {
            "name": "Moderator Lesson",
            "description": "Moderator Lesson Description",
            "course": self.course.id,
            "video_link": "https://youtube.com/watch?v=mod123",
        }

        response = self.client.post(self.lessons_list_url, lesson_data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Lesson.objects.count(), 1)

    def test_lesson_retrieve_owner(self):
        """Тест получения деталей урока владельцем"""
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.get(self.lesson_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Lesson")
        self.assertEqual(response.data["owner"], self.owner_user.id)

    def test_lesson_retrieve_moderator(self):
        """Тест получения деталей урока модератором"""
        self.client.force_authenticate(user=self.moderator_user)
        response = self.client.get(self.lesson_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Lesson")

    def test_lesson_retrieve_other_user_forbidden(self):
        """Тест запрета получения деталей урока другим пользователем"""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.lesson_detail_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_lesson_update_owner(self):
        """Тест обновления урока владельцем"""
        self.client.force_authenticate(user=self.owner_user)

        update_data = {"name": "Updated Lesson", "description": "Updated Description"}

        response = self.client.patch(self.lesson_detail_url, update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.name, "Updated Lesson")

    def test_lesson_update_moderator(self):
        """Тест обновления урока модератором"""
        self.client.force_authenticate(user=self.moderator_user)

        update_data = {
            "name": "Moderator Updated Lesson",
            "description": "Moderator Updated Description",
        }

        response = self.client.patch(self.lesson_detail_url, update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.name, "Moderator Updated Lesson")

    def test_lesson_update_other_user_forbidden(self):
        """Тест запрета обновления урока другим пользователем"""
        self.client.force_authenticate(user=self.other_user)

        update_data = {"name": "Unauthorized Update"}

        response = self.client.patch(self.lesson_detail_url, update_data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_lesson_delete_owner(self):
        """Тест удаления урока владельцем"""
        self.client.force_authenticate(user=self.owner_user)
        response = self.client.delete(self.lesson_detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Lesson.objects.count(), 0)

    def test_lesson_delete_moderator_forbidden(self):
        """Тест запрета удаления урока модератором"""
        self.client.force_authenticate(user=self.moderator_user)
        response = self.client.delete(self.lesson_detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Lesson.objects.count(), 1)

    def test_lesson_delete_other_user_forbidden(self):
        """Тест запрета удаления урока другим пользователем"""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(self.lesson_detail_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Lesson.objects.count(), 1)

    def test_lesson_create_invalid_video_link(self):
        """Тест создания урока с некорректной видео-ссылкой"""
        self.client.force_authenticate(user=self.owner_user)

        lesson_data = {
            "name": "Invalid Video Lesson",
            "description": "Lesson with invalid video link",
            "course": self.course.id,
            "video_link": "https://vimeo.com/invalid123",  # Не YouTube!
        }

        response = self.client.post(self.lessons_list_url, lesson_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("video_link", response.data)
        self.assertEqual(Lesson.objects.count(), 1)

    def test_lesson_create_with_external_links_in_description(self):
        """Тест создания урока с внешними ссылками в описании"""
        self.client.force_authenticate(user=self.owner_user)

        lesson_data = {
            "name": "Lesson with External Links",
            "description": "Check this out: https://vimeo.com/external",
            "course": self.course.id,
            "video_link": "https://youtube.com/watch?v=valid123",
        }

        response = self.client.post(self.lessons_list_url, lesson_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("description", response.data)
        self.assertEqual(Lesson.objects.count(), 1)
