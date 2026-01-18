import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User

from .factories import MasterProfileFactory, UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory(password="testpass123")


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
class TestRegistration:
    def test_register_success(self, api_client):
        url = reverse("register")
        data = {
            "email": "newuser@example.com",
            "password": "strongpass123",
            "password_confirm": "strongpass123",
            "first_name": "Тест",
            "last_name": "Пользователь",
            "phone": "+79001234567"
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data
        assert User.objects.filter(email="newuser@example.com").exists()

    def test_register_password_mismatch(self, api_client):
        url = reverse("register")
        data = {
            "email": "newuser@example.com",
            "password": "strongpass123",
            "password_confirm": "differentpass",
            "first_name": "Тест",
            "last_name": "Пользователь"
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password_confirm" in response.data

    def test_register_duplicate_email(self, api_client, user):
        url = reverse("register")
        data = {
            "email": user.email,
            "password": "strongpass123",
            "password_confirm": "strongpass123",
            "first_name": "Тест",
            "last_name": "Пользователь"
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client):
        url = reverse("register")
        data = {
            "email": "newuser@example.com",
            "password": "123",
            "password_confirm": "123",
            "first_name": "Тест",
            "last_name": "Пользователь"
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, api_client, user):
        url = reverse("login")
        data = {
            "email": user.email,
            "password": "testpass123"
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password(self, api_client, user):
        url = reverse("login")
        data = {
            "email": user.email,
            "password": "wrongpassword"
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_nonexistent_user(self, api_client):
        url = reverse("login")
        data = {
            "email": "nonexistent@example.com",
            "password": "somepassword"
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_user(self, api_client):
        user = UserFactory(is_active=False, password="testpass123")
        url = reverse("login")
        data = {
            "email": user.email,
            "password": "testpass123"
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogout:
    def test_logout_success(self, authenticated_client):
        url = reverse("logout")
        response = authenticated_client.post(url, {})

        assert response.status_code == status.HTTP_200_OK

    def test_logout_unauthenticated(self, api_client):
        url = reverse("logout")
        response = api_client.post(url, {})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestProfile:
    def test_get_profile(self, authenticated_client, user):
        url = reverse("profile")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert response.data["first_name"] == user.first_name

    def test_update_profile(self, authenticated_client, user):
        url = reverse("profile")
        data = {
            "first_name": "Новое Имя",
            "last_name": "Новая Фамилия",
            "phone": "+79009999999"
        }
        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == "Новое Имя"

    def test_get_profile_unauthenticated(self, api_client):
        url = reverse("profile")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestChangePassword:
    def test_change_password_success(self, authenticated_client, user):
        url = reverse("change-password")
        data = {
            "old_password": "testpass123",
            "new_password": "newstrongpass123"
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password("newstrongpass123")

    def test_change_password_wrong_old(self, authenticated_client):
        url = reverse("change-password")
        data = {
            "old_password": "wrongpassword",
            "new_password": "newstrongpass123"
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestMasterList:
    def test_list_masters(self, api_client):
        MasterProfileFactory.create_batch(3)
        url = reverse("master-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 3

    def test_list_masters_excludes_unavailable(self, api_client):
        MasterProfileFactory(is_available=True)
        MasterProfileFactory(is_available=False)

        url = reverse("master-list")
        response = api_client.get(url)

        # Handle both paginated and non-paginated responses
        data = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        # Только доступные мастера
        for master in data:
            assert master["is_available"] is True

    def test_get_master_detail(self, api_client):
        profile = MasterProfileFactory()
        url = reverse("master-detail", kwargs={"pk": profile.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(profile.pk)
