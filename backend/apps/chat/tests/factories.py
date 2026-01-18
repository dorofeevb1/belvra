import factory
from faker import Faker

from apps.chat.models import Chat, ChatMessage
from apps.users.tests.factories import MasterProfileFactory, UserFactory

fake = Faker("ru_RU")


class ChatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Chat

    master = factory.SubFactory(MasterProfileFactory)
    client = factory.SubFactory(UserFactory)
    is_active = True


class ChatMessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChatMessage

    chat = factory.SubFactory(ChatFactory)
    sender = factory.LazyAttribute(lambda obj: obj.chat.client)
    sender_role = ChatMessage.SenderRole.CLIENT
    content = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    is_read = False


class MasterMessageFactory(ChatMessageFactory):
    """Message from master."""
    sender = factory.LazyAttribute(lambda obj: obj.chat.master.user)
    sender_role = ChatMessage.SenderRole.MASTER


class ClientMessageFactory(ChatMessageFactory):
    """Message from client."""
    sender = factory.LazyAttribute(lambda obj: obj.chat.client)
    sender_role = ChatMessage.SenderRole.CLIENT
