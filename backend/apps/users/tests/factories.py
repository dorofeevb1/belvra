import factory
from faker import Faker

from apps.users.models import MasterProfile, User

fake = Faker("ru_RU")


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.LazyAttribute(lambda _: fake.unique.email())
    first_name = factory.LazyAttribute(lambda _: fake.first_name())
    last_name = factory.LazyAttribute(lambda _: fake.last_name())
    phone = factory.LazyAttribute(lambda _: fake.phone_number())
    role = User.Role.CLIENT
    is_active = True
    is_verified = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or "testpass123"
        self.set_password(password)
        if create:
            self.save()


class MasterUserFactory(UserFactory):
    """Factory for master users. Note: MasterProfile is created automatically by signal."""
    role = User.Role.MASTER


class AdminUserFactory(UserFactory):
    role = User.Role.ADMIN
    is_staff = True
    is_superuser = True


class MasterProfileFactory(factory.django.DjangoModelFactory):
    """Factory for MasterProfile - uses existing profile created by signal."""

    class Meta:
        model = MasterProfile

    user = factory.SubFactory(MasterUserFactory)
    bio = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    experience_years = factory.LazyAttribute(lambda _: fake.random_int(min=1, max=20))
    specialization = factory.LazyAttribute(
        lambda _: fake.random_element(["Парикмахер", "Визажист", "Маникюр", "Массаж"])
    )
    rating = 0
    reviews_count = 0
    is_available = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override to get or update existing profile instead of creating new."""
        user = kwargs.pop("user", None)

        if user is None:
            user = MasterUserFactory()

        # Profile is auto-created by signal, so get it and update
        try:
            profile = MasterProfile.objects.get(user=user)
            for key, value in kwargs.items():
                setattr(profile, key, value)
            profile.save()
            return profile
        except MasterProfile.DoesNotExist:
            kwargs["user"] = user
            return super()._create(model_class, *args, **kwargs)
