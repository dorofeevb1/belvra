"""
Tests for MasterGeoSearchView (nearby masters search).
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .factories import MasterProfileFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestMasterGeoSearch:
    """Tests for geo-search endpoint."""

    # Moscow coordinates for testing
    MOSCOW_CENTER_LAT = 55.7558
    MOSCOW_CENTER_LNG = 37.6173

    def test_find_nearby_masters(self, api_client):
        """Should find masters within the specified radius."""
        # Create a master near Moscow center (about 1 km away)
        near_master = MasterProfileFactory(
            latitude=Decimal("55.7600"),
            longitude=Decimal("37.6200"),
            is_available=True
        )

        # Create a master far from Moscow (about 500 km away - St. Petersburg)
        far_master = MasterProfileFactory(
            latitude=Decimal("59.9343"),
            longitude=Decimal("30.3351"),
            is_available=True
        )

        url = reverse("master-nearby")
        response = api_client.get(url, {
            "lat": self.MOSCOW_CENTER_LAT,
            "lng": self.MOSCOW_CENTER_LNG,
            "radius_km": 10
        })

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)

        # Only near_master should be in results
        master_ids = [str(m["id"]) for m in results]
        assert str(near_master.id) in master_ids
        assert str(far_master.id) not in master_ids

    def test_distance_km_in_response(self, api_client):
        """Response should include distance_km field."""
        master = MasterProfileFactory(
            latitude=Decimal("55.7600"),
            longitude=Decimal("37.6200"),
            is_available=True
        )

        url = reverse("master-nearby")
        response = api_client.get(url, {
            "lat": self.MOSCOW_CENTER_LAT,
            "lng": self.MOSCOW_CENTER_LNG,
            "radius_km": 10
        })

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)

        assert len(results) > 0
        assert "distance_km" in results[0]
        # Distance should be approximately 0.5-1 km
        assert 0 < results[0]["distance_km"] < 2

    def test_sorted_by_distance(self, api_client):
        """Results should be sorted by distance (nearest first)."""
        # Create masters at different distances
        near_master = MasterProfileFactory(
            latitude=Decimal("55.7560"),
            longitude=Decimal("37.6180"),
            is_available=True
        )
        medium_master = MasterProfileFactory(
            latitude=Decimal("55.7700"),
            longitude=Decimal("37.6300"),
            is_available=True
        )
        far_master = MasterProfileFactory(
            latitude=Decimal("55.8000"),
            longitude=Decimal("37.7000"),
            is_available=True
        )

        url = reverse("master-nearby")
        response = api_client.get(url, {
            "lat": self.MOSCOW_CENTER_LAT,
            "lng": self.MOSCOW_CENTER_LNG,
            "radius_km": 50
        })

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)

        # Verify sorted by distance
        distances = [r["distance_km"] for r in results]
        assert distances == sorted(distances)

    def test_exclude_unavailable_masters(self, api_client):
        """Unavailable masters should be excluded."""
        available_master = MasterProfileFactory(
            latitude=Decimal("55.7560"),
            longitude=Decimal("37.6180"),
            is_available=True
        )
        unavailable_master = MasterProfileFactory(
            latitude=Decimal("55.7565"),
            longitude=Decimal("37.6185"),
            is_available=False
        )

        url = reverse("master-nearby")
        response = api_client.get(url, {
            "lat": self.MOSCOW_CENTER_LAT,
            "lng": self.MOSCOW_CENTER_LNG,
            "radius_km": 10
        })

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)

        master_ids = [str(m["id"]) for m in results]
        assert str(available_master.id) in master_ids
        assert str(unavailable_master.id) not in master_ids

    def test_exclude_masters_without_coordinates(self, api_client):
        """Masters without coordinates should be excluded."""
        with_coords = MasterProfileFactory(
            latitude=Decimal("55.7560"),
            longitude=Decimal("37.6180"),
            is_available=True
        )
        without_coords = MasterProfileFactory(
            latitude=None,
            longitude=None,
            is_available=True
        )

        url = reverse("master-nearby")
        response = api_client.get(url, {
            "lat": self.MOSCOW_CENTER_LAT,
            "lng": self.MOSCOW_CENTER_LNG,
            "radius_km": 10
        })

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)

        master_ids = [str(m["id"]) for m in results]
        assert str(with_coords.id) in master_ids
        assert str(without_coords.id) not in master_ids

    def test_default_radius(self, api_client):
        """Default radius should be 10 km if not specified."""
        # Master at about 5 km should be included
        near_master = MasterProfileFactory(
            latitude=Decimal("55.7800"),
            longitude=Decimal("37.6500"),
            is_available=True
        )
        # Master at about 50 km should be excluded
        far_master = MasterProfileFactory(
            latitude=Decimal("56.2000"),
            longitude=Decimal("38.0000"),
            is_available=True
        )

        url = reverse("master-nearby")
        response = api_client.get(url, {
            "lat": self.MOSCOW_CENTER_LAT,
            "lng": self.MOSCOW_CENTER_LNG,
            # No radius_km - should use default 10 km
        })

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)

        master_ids = [str(m["id"]) for m in results]
        assert str(near_master.id) in master_ids
        assert str(far_master.id) not in master_ids

    def test_missing_lat_lng_returns_empty(self, api_client):
        """Missing lat/lng should return empty results."""
        MasterProfileFactory(
            latitude=Decimal("55.7560"),
            longitude=Decimal("37.6180"),
            is_available=True
        )

        url = reverse("master-nearby")

        # No parameters
        response = api_client.get(url)
        results = response.data.get("results", response.data)
        assert len(results) == 0

        # Only lat
        response = api_client.get(url, {"lat": self.MOSCOW_CENTER_LAT})
        results = response.data.get("results", response.data)
        assert len(results) == 0

        # Only lng
        response = api_client.get(url, {"lng": self.MOSCOW_CENTER_LNG})
        results = response.data.get("results", response.data)
        assert len(results) == 0

    def test_invalid_lat_lng_returns_empty(self, api_client):
        """Invalid lat/lng values should return empty results."""
        MasterProfileFactory(
            latitude=Decimal("55.7560"),
            longitude=Decimal("37.6180"),
            is_available=True
        )

        url = reverse("master-nearby")
        response = api_client.get(url, {
            "lat": "invalid",
            "lng": "invalid",
            "radius_km": 10
        })

        results = response.data.get("results", response.data)
        assert len(results) == 0

    def test_custom_radius(self, api_client):
        """Custom radius should be respected."""
        # Master at about 15 km
        medium_master = MasterProfileFactory(
            latitude=Decimal("55.8500"),
            longitude=Decimal("37.7500"),
            is_available=True
        )

        url = reverse("master-nearby")

        # With 10 km radius - should not find
        response = api_client.get(url, {
            "lat": self.MOSCOW_CENTER_LAT,
            "lng": self.MOSCOW_CENTER_LNG,
            "radius_km": 10
        })
        results = response.data.get("results", response.data)
        master_ids = [str(m["id"]) for m in results]
        assert str(medium_master.id) not in master_ids

        # With 20 km radius - should find
        response = api_client.get(url, {
            "lat": self.MOSCOW_CENTER_LAT,
            "lng": self.MOSCOW_CENTER_LNG,
            "radius_km": 20
        })
        results = response.data.get("results", response.data)
        master_ids = [str(m["id"]) for m in results]
        assert str(medium_master.id) in master_ids

    def test_returns_master_data(self, api_client):
        """Response should include all master profile fields."""
        master = MasterProfileFactory(
            latitude=Decimal("55.7560"),
            longitude=Decimal("37.6180"),
            is_available=True,
            specialization="Парикмахер",
            bio="Test bio"
        )

        url = reverse("master-nearby")
        response = api_client.get(url, {
            "lat": self.MOSCOW_CENTER_LAT,
            "lng": self.MOSCOW_CENTER_LNG,
            "radius_km": 10
        })

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)

        assert len(results) == 1
        result = results[0]

        # Check expected fields
        assert "id" in result
        assert "user" in result
        assert "bio" in result
        assert "specialization" in result
        assert "rating" in result
        assert "distance_km" in result
        assert "latitude" in result
        assert "longitude" in result
