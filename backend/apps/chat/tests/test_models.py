import pytest

from apps.chat.models import Chat, ChatMessage

from .factories import ChatFactory, ClientMessageFactory, MasterMessageFactory


@pytest.mark.django_db
class TestChatModel:
    def test_create_chat(self):
        chat = ChatFactory()
        assert chat.pk is not None
        assert chat.is_active is True

    def test_chat_str(self):
        chat = ChatFactory()
        assert chat.master.user.full_name in str(chat)
        assert chat.client.full_name in str(chat)

    def test_chat_unique_together(self):
        chat = ChatFactory()
        with pytest.raises(Exception):
            ChatFactory(master=chat.master, client=chat.client)

    def test_last_message_property(self):
        chat = ChatFactory()
        msg1 = ClientMessageFactory(chat=chat)
        msg2 = MasterMessageFactory(chat=chat)

        # Messages are ordered by -created_at, so last created is first
        assert chat.last_message == msg2

    def test_last_message_property_empty(self):
        chat = ChatFactory()
        assert chat.last_message is None

    def test_unread_count_for_master(self):
        chat = ChatFactory()
        ClientMessageFactory.create_batch(3, chat=chat, is_read=False)
        ClientMessageFactory(chat=chat, is_read=True)
        MasterMessageFactory.create_batch(2, chat=chat, is_read=False)

        assert chat.unread_count_for_master == 3

    def test_unread_count_for_client(self):
        chat = ChatFactory()
        MasterMessageFactory.create_batch(4, chat=chat, is_read=False)
        MasterMessageFactory(chat=chat, is_read=True)
        ClientMessageFactory.create_batch(2, chat=chat, is_read=False)

        assert chat.unread_count_for_client == 4


@pytest.mark.django_db
class TestChatMessageModel:
    def test_create_message(self):
        msg = ClientMessageFactory()
        assert msg.pk is not None
        assert msg.is_read is False
        assert msg.read_at is None

    def test_message_str(self):
        msg = ClientMessageFactory(content="Test message content")
        assert msg.sender.full_name in str(msg)
        assert "Test message" in str(msg)

    def test_mark_as_read(self):
        msg = ClientMessageFactory(is_read=False)
        assert msg.is_read is False
        assert msg.read_at is None

        msg.mark_as_read()

        assert msg.is_read is True
        assert msg.read_at is not None

    def test_mark_as_read_idempotent(self):
        msg = ClientMessageFactory(is_read=False)
        msg.mark_as_read()
        first_read_at = msg.read_at

        msg.mark_as_read()
        assert msg.read_at == first_read_at
