import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.models import Chat, ChatMessage
from apps.users.tests.factories import MasterProfileFactory, MasterUserFactory, UserFactory

from .factories import ChatFactory, ClientMessageFactory, MasterMessageFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def master_user(db):
    return MasterUserFactory()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def master_client(api_client, master_user):
    api_client.force_authenticate(user=master_user)
    return api_client


@pytest.mark.django_db
class TestChatListAPI:
    def test_list_chats_authenticated(self, authenticated_client, user):
        # Chats where user is client
        ChatFactory.create_batch(2, client=user)
        # Chats of other users
        ChatFactory.create_batch(3)

        url = reverse("chat-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Handle both paginated and non-paginated responses
        data = response.data.get("results", response.data) if isinstance(response.data, dict) and "results" in response.data else response.data
        assert len(data) == 2

    def test_list_chats_as_master(self, master_client, master_user):
        master_profile = master_user.master_profile
        # Chats where user is master
        ChatFactory.create_batch(3, master=master_profile)
        # Chats of other masters
        ChatFactory.create_batch(2)

        url = reverse("chat-list")
        response = master_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Handle both paginated and non-paginated responses
        data = response.data.get("results", response.data) if isinstance(response.data, dict) and "results" in response.data else response.data
        assert len(data) == 3

    def test_list_chats_unauthenticated(self, api_client):
        url = reverse("chat-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestChatCreateAPI:
    def test_create_chat(self, authenticated_client, user):
        master_profile = MasterProfileFactory()

        url = reverse("chat-list")
        data = {"master_id": str(master_profile.pk)}
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Chat.objects.filter(client=user, master=master_profile).exists()

    def test_create_chat_duplicate_returns_existing(self, authenticated_client, user):
        """Creating a chat that already exists should return the existing chat (get_or_create behavior)."""
        master_profile = MasterProfileFactory()
        existing_chat = ChatFactory(client=user, master=master_profile)

        url = reverse("chat-list")
        data = {"master_id": str(master_profile.pk)}
        response = authenticated_client.post(url, data)

        # get_or_create returns existing chat instead of error
        assert response.status_code == status.HTTP_201_CREATED
        # Ensure no duplicate was created
        assert Chat.objects.filter(client=user, master=master_profile).count() == 1


@pytest.mark.django_db
class TestChatDetailAPI:
    def test_get_chat_detail(self, authenticated_client, user):
        chat = ChatFactory(client=user)
        ClientMessageFactory.create_batch(3, chat=chat)

        url = reverse("chat-detail", kwargs={"pk": chat.pk})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(chat.pk)

    def test_get_chat_detail_not_participant(self, authenticated_client):
        chat = ChatFactory()  # Other user's chat

        url = reverse("chat-detail", kwargs={"pk": chat.pk})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestSendMessageAPI:
    def test_send_message_as_client(self, authenticated_client, user):
        chat = ChatFactory(client=user)

        url = reverse("chat-send-message", kwargs={"pk": chat.pk})
        data = {"content": "Hello master!"}
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["content"] == "Hello master!"
        assert response.data["sender_role"] == "client"

    def test_send_message_as_master(self, master_client, master_user):
        master_profile = master_user.master_profile
        chat = ChatFactory(master=master_profile)

        url = reverse("chat-send-message", kwargs={"pk": chat.pk})
        data = {"content": "Hello client!"}
        response = master_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["content"] == "Hello client!"
        assert response.data["sender_role"] == "master"

    def test_send_message_not_participant(self, authenticated_client):
        chat = ChatFactory()  # Other user's chat

        url = reverse("chat-send-message", kwargs={"pk": chat.pk})
        data = {"content": "Hello!"}
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_send_empty_message(self, authenticated_client, user):
        chat = ChatFactory(client=user)

        url = reverse("chat-send-message", kwargs={"pk": chat.pk})
        data = {"content": ""}
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestGetMessagesAPI:
    def test_get_messages(self, authenticated_client, user):
        chat = ChatFactory(client=user)
        ClientMessageFactory.create_batch(5, chat=chat)
        MasterMessageFactory.create_batch(3, chat=chat)

        url = reverse("chat-messages", kwargs={"pk": chat.pk})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Paginated response
        results = response.data.get("results", response.data)
        assert len(results) == 8

    def test_get_messages_not_participant(self, authenticated_client):
        chat = ChatFactory()  # Other user's chat

        url = reverse("chat-messages", kwargs={"pk": chat.pk})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestMarkReadAPI:
    def test_mark_read_as_client(self, authenticated_client, user):
        chat = ChatFactory(client=user)
        MasterMessageFactory.create_batch(5, chat=chat, is_read=False)
        ClientMessageFactory.create_batch(2, chat=chat, is_read=False)

        url = reverse("chat-mark-read", kwargs={"pk": chat.pk})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["marked_read"] == 5

        # Verify messages are marked as read
        assert chat.messages.filter(
            sender_role=ChatMessage.SenderRole.MASTER,
            is_read=True
        ).count() == 5

    def test_mark_read_as_master(self, master_client, master_user):
        master_profile = master_user.master_profile
        chat = ChatFactory(master=master_profile)
        ClientMessageFactory.create_batch(4, chat=chat, is_read=False)
        MasterMessageFactory.create_batch(2, chat=chat, is_read=False)

        url = reverse("chat-mark-read", kwargs={"pk": chat.pk})
        response = master_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["marked_read"] == 4


@pytest.mark.django_db
class TestWithMasterAPI:
    def test_get_or_create_chat_with_master_new(self, authenticated_client, user):
        master_profile = MasterProfileFactory()

        url = reverse("chat-with-master", kwargs={"master_id": master_profile.pk})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_201_CREATED
        assert Chat.objects.filter(client=user, master=master_profile).exists()

    def test_get_or_create_chat_with_master_existing(self, authenticated_client, user):
        master_profile = MasterProfileFactory()
        existing_chat = ChatFactory(client=user, master=master_profile)

        url = reverse("chat-with-master", kwargs={"master_id": master_profile.pk})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(existing_chat.pk)

    def test_get_chat_with_nonexistent_master(self, authenticated_client):
        import uuid
        fake_master_id = uuid.uuid4()

        url = reverse("chat-with-master", kwargs={"master_id": fake_master_id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
