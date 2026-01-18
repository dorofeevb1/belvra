import pytest

from apps.users.models import MasterProfile, User

from .factories import MasterProfileFactory, MasterUserFactory, UserFactory


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = UserFactory()
        assert user.pk is not None
        assert user.email is not None
        assert user.is_active is True
        assert user.is_staff is False

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="admin@test.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User"
        )
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.role == User.Role.ADMIN

    def test_user_full_name(self):
        user = UserFactory(first_name="Иван", last_name="Петров")
        assert user.full_name == "Иван Петров"

    def test_user_str(self):
        user = UserFactory(email="test@example.com")
        assert str(user) == "test@example.com"

    def test_user_is_master_property(self):
        client = UserFactory(role=User.Role.CLIENT)
        master = UserFactory(role=User.Role.MASTER)

        assert client.is_master is False
        assert master.is_master is True

    def test_user_is_client_property(self):
        client = UserFactory(role=User.Role.CLIENT)
        master = UserFactory(role=User.Role.MASTER)

        assert client.is_client is True
        assert master.is_client is False

    def test_user_password_is_hashed(self):
        user = UserFactory(password="mypassword123")
        assert user.password != "mypassword123"
        assert user.check_password("mypassword123")


@pytest.mark.django_db
class TestMasterProfileModel:
    def test_create_master_profile(self):
        profile = MasterProfileFactory()
        assert profile.pk is not None
        assert profile.user.role == User.Role.MASTER

    def test_master_profile_str(self):
        profile = MasterProfileFactory()
        assert profile.user.full_name in str(profile)

    def test_master_profile_auto_created_on_master_user(self):
        """Тест что профиль мастера создаётся автоматически при создании пользователя-мастера"""
        user = MasterUserFactory()
        # Профиль создаётся сигналом
        assert MasterProfile.objects.filter(user=user).exists()

    def test_master_profile_default_values(self):
        profile = MasterProfileFactory(rating=0, reviews_count=0)
        assert profile.rating == 0
        assert profile.reviews_count == 0
        assert profile.is_available is True
