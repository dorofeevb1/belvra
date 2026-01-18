import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.tests.factories import AdminUserFactory, UserFactory

from .factories import CategoryFactory, MasterServiceFactory, ServiceFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def admin_user(db):
    return AdminUserFactory()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.mark.django_db
class TestCategoryAPI:
    def test_list_categories(self, api_client):
        CategoryFactory.create_batch(3)
        url = reverse("category-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 3

    def test_list_categories_excludes_inactive(self, api_client):
        CategoryFactory(is_active=True, name="Active")
        CategoryFactory(is_active=False, name="Inactive")

        url = reverse("category-list")
        response = api_client.get(url)

        # Handle both paginated and non-paginated responses
        data = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        names = [cat["name"] for cat in data]
        assert "Active" in names
        assert "Inactive" not in names

    def test_get_category_detail(self, api_client):
        category = CategoryFactory()
        url = reverse("category-detail", kwargs={"slug": category.slug})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == category.name

    def test_get_category_services(self, api_client):
        category = CategoryFactory()
        ServiceFactory.create_batch(3, category=category)

        url = reverse("category-services", kwargs={"slug": category.slug})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_create_category_requires_admin(self, authenticated_client):
        url = reverse("category-list")
        data = {"name": "Новая категория", "slug": "new-category"}
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_category_as_admin(self, admin_client):
        url = reverse("category-list")
        data = {"name": "Новая категория", "slug": "new-category"}
        response = admin_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestServiceAPI:
    def test_list_services(self, api_client):
        ServiceFactory.create_batch(5)
        url = reverse("service-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 5

    def test_list_services_filter_by_category(self, api_client):
        category = CategoryFactory()
        ServiceFactory.create_batch(3, category=category)
        ServiceFactory.create_batch(2)  # Другая категория

        url = reverse("service-list")
        response = api_client.get(url, {"category": str(category.pk)})

        assert response.status_code == status.HTTP_200_OK
        for service in response.data["results"]:
            assert str(service["category"]) == str(category.pk)

    def test_list_popular_services(self, api_client):
        ServiceFactory.create_batch(3, is_popular=True)
        ServiceFactory.create_batch(2, is_popular=False)

        url = reverse("service-popular")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        for service in response.data:
            assert service["is_popular"] is True

    def test_get_service_detail(self, api_client):
        service = ServiceFactory()
        url = reverse("service-detail", kwargs={"slug": service.slug})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == service.name
        assert "masters" in response.data

    def test_get_service_with_masters(self, api_client):
        service = ServiceFactory()
        MasterServiceFactory.create_batch(2, service=service)

        url = reverse("service-detail", kwargs={"slug": service.slug})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["masters"]) == 2

    def test_search_services(self, api_client):
        ServiceFactory(name="Стрижка мужская", slug="strizhka-muzhskaya")
        ServiceFactory(name="Стрижка женская", slug="strizhka-zhenskaya")
        ServiceFactory(name="Маникюр", slug="manikur")

        url = reverse("service-list")
        response = api_client.get(url, {"search": "Стрижка"})

        assert response.status_code == status.HTTP_200_OK
        # Search might be case-sensitive depending on DB
        assert len(response.data["results"]) >= 1

    def test_create_service_requires_admin(self, authenticated_client):
        category = CategoryFactory()
        url = reverse("service-list")
        data = {
            "category": category.pk,
            "name": "Новая услуга",
            "slug": "new-service",
            "price": "1500.00",
            "duration": 60
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestMasterServiceAPI:
    def test_list_master_services(self, api_client):
        MasterServiceFactory.create_batch(3)
        url = reverse("master-service-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 3

    def test_filter_by_master(self, api_client):
        ms1 = MasterServiceFactory()
        MasterServiceFactory.create_batch(2, master=ms1.master)
        MasterServiceFactory.create_batch(3)  # Другие мастера

        url = reverse("master-service-list")
        response = api_client.get(url, {"master": ms1.master.pk})

        assert response.status_code == status.HTTP_200_OK
        for item in response.data["results"]:
            assert item["master"]["id"] == str(ms1.master.pk)

    def test_filter_by_service(self, api_client):
        ms1 = MasterServiceFactory()
        MasterServiceFactory.create_batch(2, service=ms1.service)
        MasterServiceFactory.create_batch(3)  # Другие услуги

        url = reverse("master-service-list")
        response = api_client.get(url, {"service": ms1.service.pk})

        assert response.status_code == status.HTTP_200_OK
        for item in response.data["results"]:
            assert item["service"]["id"] == str(ms1.service.pk)
