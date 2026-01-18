import pytest
from decimal import Decimal

from apps.services.models import Category, MasterService, Service

from .factories import CategoryFactory, MasterServiceFactory, ServiceFactory


@pytest.mark.django_db
class TestCategoryModel:
    def test_create_category(self):
        category = CategoryFactory()
        assert category.pk is not None
        assert category.is_active is True

    def test_category_str(self):
        category = CategoryFactory(name="Стрижки")
        assert str(category) == "Стрижки"

    def test_category_ordering(self):
        cat1 = CategoryFactory(order=2)
        cat2 = CategoryFactory(order=1)
        cat3 = CategoryFactory(order=3)

        categories = list(Category.objects.all())
        assert categories[0].order <= categories[1].order <= categories[2].order


@pytest.mark.django_db
class TestServiceModel:
    def test_create_service(self):
        service = ServiceFactory()
        assert service.pk is not None
        assert service.category is not None
        assert service.price > 0
        assert service.duration > 0

    def test_service_str(self):
        service = ServiceFactory(name="Маникюр классический")
        assert str(service) == "Маникюр классический"

    def test_service_belongs_to_category(self):
        category = CategoryFactory()
        service = ServiceFactory(category=category)

        assert service.category == category
        assert service in category.services.all()


@pytest.mark.django_db
class TestMasterServiceModel:
    def test_create_master_service(self):
        master_service = MasterServiceFactory()
        assert master_service.pk is not None
        assert master_service.master is not None
        assert master_service.service is not None

    def test_master_service_str(self):
        master_service = MasterServiceFactory()
        assert master_service.master.user.full_name in str(master_service)
        assert master_service.service.name in str(master_service)

    def test_actual_price_default(self):
        """Если цена не указана, используется цена услуги"""
        service = ServiceFactory(price=Decimal("1500.00"))
        master_service = MasterServiceFactory(service=service, price=None)

        assert master_service.actual_price == Decimal("1500.00")

    def test_actual_price_custom(self):
        """Если указана кастомная цена, используется она"""
        service = ServiceFactory(price=Decimal("1500.00"))
        master_service = MasterServiceFactory(service=service, price=Decimal("2000.00"))

        assert master_service.actual_price == Decimal("2000.00")

    def test_actual_duration_default(self):
        """Если длительность не указана, используется длительность услуги"""
        service = ServiceFactory(duration=60)
        master_service = MasterServiceFactory(service=service, duration=None)

        assert master_service.actual_duration == 60

    def test_actual_duration_custom(self):
        """Если указана кастомная длительность, используется она"""
        service = ServiceFactory(duration=60)
        master_service = MasterServiceFactory(service=service, duration=90)

        assert master_service.actual_duration == 90

    def test_unique_together_constraint(self):
        """Один мастер не может иметь дублирующую услугу"""
        master_service = MasterServiceFactory()

        with pytest.raises(Exception):
            MasterServiceFactory(
                master=master_service.master,
                service=master_service.service
            )
