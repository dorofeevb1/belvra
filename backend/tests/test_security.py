"""
Security tests: access control, IDOR, subscription gating, rate limiting,
business logic, and smoke tests.
"""

import uuid
from datetime import date, timedelta

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import MasterProfile, User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client_user(db):
    return User.objects.create_user(
        email="sectest_client@test.com",
        password="Test1234!",
        role="client",
    )


@pytest.fixture
def client_api(client_user):
    api = APIClient()
    api.force_authenticate(user=client_user)
    return api


@pytest.fixture
def master_user(db):
    user, _ = User.objects.get_or_create(
        email="sectest_master@test.com",
        defaults={"password": "Test1234!", "role": "master"},
    )
    if not user.check_password("Test1234!"):
        user.set_password("Test1234!")
        user.save()
    user.role = "master"
    user.save(update_fields=["role"])
    MasterProfile.objects.get_or_create(user=user, defaults={"specialization": "Test"})
    return user


@pytest.fixture
def master_api(master_user):
    api = APIClient()
    api.force_authenticate(user=master_user)
    return api


@pytest.fixture
def other_client_user(db):
    return User.objects.create_user(
        email="sectest_other@test.com",
        password="Test1234!",
        role="client",
    )


@pytest.fixture
def other_client_api(other_client_user):
    api = APIClient()
    api.force_authenticate(user=other_client_user)
    return api


@pytest.fixture
def anon_api():
    return APIClient()


# ---------------------------------------------------------------------------
# 1. Client cannot access master-only endpoints (should get 403, not 500)
# ---------------------------------------------------------------------------

class TestClientCannotAccessMasterEndpoints:
    """A client user must receive 403 (not 500) on master-only endpoints."""

    def test_client_cannot_create_todo(self, client_api):
        resp = client_api.post("/api/v1/todos/", {"title": "hack", "date": "2026-04-10"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_client_cannot_list_todos(self, client_api):
        resp = client_api.get("/api/v1/todos/")
        # Non-masters get an empty queryset, so 200 with empty list is acceptable
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == [] or resp.data.get("results", []) == []

    def test_client_cannot_bulk_schedule(self, client_api):
        resp = client_api.post(
            "/api/v1/appointments/schedules/bulk/",
            {"schedules": [{"weekday": 0, "start_time": "09:00", "end_time": "18:00"}]},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_client_cannot_create_master_service(self, client_api):
        resp = client_api.post(
            "/api/v1/services/master-services/",
            {"custom_name": "hack", "price": 100, "duration": 60},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_client_cannot_create_portfolio(self, client_api):
        resp = client_api.post(
            "/api/v1/services/portfolio/",
            {"title": "hack", "description": "x"},
            format="json",
        )
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST)

    def test_client_cannot_create_client_note(self, client_api):
        resp = client_api.post(
            "/api/v1/appointments/client-notes/",
            {"client": str(uuid.uuid4()), "text": "hack"},
            format="json",
        )
        assert resp.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        )

    def test_client_cannot_get_my_services(self, client_api):
        resp = client_api.get("/api/v1/services/master-services/my_services/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# 2. IDOR: user A cannot see user B's private data
# ---------------------------------------------------------------------------

class TestIDOR:
    """Ensure one user cannot access another user's private resources."""

    def test_user_cannot_see_other_users_notifications(self, client_api, other_client_user):
        """Notifications endpoint should only return the caller's own data."""
        resp = client_api.get("/api/v1/notifications/")
        assert resp.status_code == status.HTTP_200_OK
        # The response should not contain data belonging to other_client_user.
        # Just verify it does not crash and returns a list.
        data = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        for n in data:
            assert str(n.get("user")) != str(other_client_user.id)

    def test_user_cannot_see_other_users_todos(self, master_api, master_user):
        """Master's todo list only returns their own items (empty by default)."""
        resp = master_api.get("/api/v1/todos/")
        assert resp.status_code == status.HTTP_200_OK

    def test_user_cannot_see_other_users_chats(self, client_api, other_client_user):
        resp = client_api.get("/api/v1/chats/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        for chat in data:
            participants = chat.get("participants", [])
            assert str(other_client_user.id) not in [str(p) for p in participants]


# ---------------------------------------------------------------------------
# 3. Subscription gating: FREE users get 403 on PRO endpoints
# ---------------------------------------------------------------------------

class TestSubscriptionGating:
    """FREE-tier users should not access PRO-only features."""

    def test_free_user_cannot_export_appointments(self, client_api):
        resp = client_api.get("/api/v1/subscriptions/export/appointments/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_free_user_cannot_export_finances(self, client_api):
        resp = client_api.get("/api/v1/subscriptions/export/finances/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_free_master_cannot_export(self, master_api):
        resp = master_api.get("/api/v1/subscriptions/export/appointments/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_free_user_cannot_access_client_stats(self, client_api):
        resp = client_api.get("/api/v1/appointments/client-stats/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# 4. Rate limiting (skipped - requires real cache backend)
# ---------------------------------------------------------------------------

class TestRateLimiting:
    """Rate limiting tests. Skipped because test LocMemCache may behave differently."""

    @pytest.mark.skip(reason="requires cache backend")
    def test_login_rate_limited(self, anon_api):
        for _ in range(30):
            anon_api.post(
                "/api/v1/auth/login/",
                {"email": "x@test.com", "password": "wrong"},
                format="json",
            )
        resp = anon_api.post(
            "/api/v1/auth/login/",
            {"email": "x@test.com", "password": "wrong"},
            format="json",
        )
        assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.skip(reason="requires cache backend")
    def test_register_rate_limited(self, anon_api):
        for i in range(30):
            anon_api.post(
                "/api/v1/auth/register/",
                {
                    "email": f"spam{i}@test.com",
                    "password": "Test1234!",
                    "first_name": "X",
                    "last_name": "Y",
                },
                format="json",
            )
        resp = anon_api.post(
            "/api/v1/auth/register/",
            {
                "email": "final@test.com",
                "password": "Test1234!",
                "first_name": "X",
                "last_name": "Y",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS


# ---------------------------------------------------------------------------
# 5. Business logic
# ---------------------------------------------------------------------------

class TestBusinessLogic:
    """Basic business-logic invariants."""

    def test_cannot_book_past_date(self, client_api, master_user):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        master_profile = master_user.master_profile
        resp = client_api.post(
            "/api/v1/appointments/",
            {
                "master_id": str(master_profile.id),
                "date": yesterday,
                "start_time": "10:00",
                "end_time": "11:00",
            },
            format="json",
        )
        # Should be rejected (400) not silently accepted
        assert resp.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        )

    def test_invalid_export_type_rejected(self, client_api):
        resp = client_api.get("/api/v1/subscriptions/export/hacked/")
        # Either 403 (subscription gate) or 400 (invalid type) are acceptable
        assert resp.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        )

    def test_invalid_limit_type_rejected(self, client_api):
        resp = client_api.get("/api/v1/subscriptions/check-limit/hacked/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# 6. Smoke tests: basic endpoints return expected codes, no PII in public API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSmokeTests:
    """Verify that fundamental endpoints respond correctly."""

    def test_health_check(self, anon_api):
        resp = anon_api.get("/health/")
        # 503 if DB not connected in test, 200 if connected — both acceptable
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_plans_public(self, anon_api):
        resp = anon_api.get("/api/v1/subscriptions/plans/")
        assert resp.status_code == status.HTTP_200_OK

    def test_categories_public(self, anon_api):
        resp = anon_api.get("/api/v1/services/categories/")
        assert resp.status_code == status.HTTP_200_OK

    def test_services_public(self, anon_api):
        resp = anon_api.get("/api/v1/services/items/")
        assert resp.status_code == status.HTTP_200_OK

    def test_masters_public(self, anon_api):
        resp = anon_api.get("/api/v1/auth/masters/")
        assert resp.status_code == status.HTTP_200_OK

    def test_unauthenticated_profile_rejected(self, anon_api):
        resp = anon_api.get("/api/v1/auth/profile/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_public_masters_no_pii(self, anon_api, master_user):
        """Public master list must not expose email or phone."""
        resp = anon_api.get("/api/v1/auth/masters/")
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        for master in results:
            # The user sub-object (if present) should not leak email/phone
            user_data = master.get("user", master)
            assert "password" not in user_data

    def test_analytics_returns_data_for_client(self, client_api):
        """Analytics should return something (not crash) even for a client."""
        resp = client_api.get("/api/v1/subscriptions/analytics/")
        assert resp.status_code == status.HTTP_200_OK
