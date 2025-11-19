"""Tests for Site building serialization and type system."""

from core.buildings.base import Building
from core.buildings.site import Site, SiteStatistics
from core.types import BuildingID, SiteID


def test_site_has_correct_type() -> None:
    """Test that Site has the correct TYPE attribute."""
    site = Site(id=SiteID("site-1"), name="Test Site", activity_rate=10.0)
    assert site.TYPE == "site"
    assert Site.TYPE == "site"


def test_site_serialization_includes_type() -> None:
    """Test that Site serialization includes type field."""
    site = Site(
        id=SiteID("site-1"),
        name="Test Site",
        activity_rate=15.0,
        destination_weights={SiteID("site-2"): 0.7, SiteID("site-3"): 0.3},
    )

    data = site.to_dict()
    assert data["type"] == "site"
    assert data["id"] == "site-1"
    assert data["name"] == "Test Site"
    assert data["activity_rate"] == 15.0


def test_site_deserialization_from_dict() -> None:
    """Test that Site can be deserialized from dictionary."""
    data = {
        "type": "site",
        "id": "site-1",
        "name": "Test Site",
        "activity_rate": 10.0,
        "destination_weights": {"site-2": 0.5, "site-3": 0.5},
        "package_config": {},
        "active_packages": [],
        "statistics": {
            "packages_generated": 5,
            "packages_picked_up": 3,
            "packages_delivered": 2,
            "packages_expired": 0,
            "total_value_delivered": 100.0,
            "total_value_expired": 0.0,
        },
    }

    # Deserialize via Building.from_dict (polymorphic)
    building = Building.from_dict(data)
    assert isinstance(building, Site)
    assert building.id == BuildingID("site-1")
    assert building.name == "Test Site"
    assert building.activity_rate == 10.0
    assert isinstance(building.statistics, SiteStatistics)
    assert building.statistics.packages_generated == 5


def test_site_deserialization_via_site_class() -> None:
    """Test that Site can be deserialized directly via Site.from_dict."""
    data = {
        "type": "site",
        "id": "site-1",
        "name": "Direct Site",
        "activity_rate": 20.0,
        "destination_weights": {},
        "package_config": {},
        "active_packages": ["pkg-1", "pkg-2"],
        "statistics": {
            "packages_generated": 10,
            "packages_picked_up": 8,
            "packages_delivered": 7,
            "packages_expired": 1,
            "total_value_delivered": 500.0,
            "total_value_expired": 50.0,
        },
    }

    site = Site.from_dict(data)
    assert isinstance(site, Site)
    assert site.id == BuildingID("site-1")
    assert site.name == "Direct Site"
    assert site.activity_rate == 20.0
    assert len(site.active_packages) == 2
    assert site.statistics.packages_delivered == 7


def test_site_roundtrip_serialization() -> None:
    """Test that Site can be serialized and deserialized without data loss."""
    original_site = Site(
        id=SiteID("site-roundtrip"),
        name="Roundtrip Test Site",
        activity_rate=25.0,
        destination_weights={SiteID("dest-1"): 0.6, SiteID("dest-2"): 0.4},
    )

    # Update statistics
    original_site.statistics.packages_generated = 15
    original_site.statistics.packages_delivered = 10
    original_site.statistics.total_value_delivered = 750.0

    # Serialize
    data = original_site.to_dict()

    # Deserialize
    restored_site = Site.from_dict(data)

    # Verify
    assert isinstance(restored_site, Site)
    assert restored_site.id == original_site.id
    assert restored_site.name == original_site.name
    assert restored_site.activity_rate == original_site.activity_rate
    assert restored_site.statistics.packages_generated == 15
    assert restored_site.statistics.packages_delivered == 10
    assert restored_site.statistics.total_value_delivered == 750.0


def test_site_type_distinguishes_from_other_buildings() -> None:
    """Test that Site type is distinct from other building types."""
    from core.buildings.parking import Parking

    site = Site(id=SiteID("site-1"), name="Test Site", activity_rate=10.0)
    parking = Parking(id=BuildingID("parking-1"), capacity=5)

    assert site.TYPE != parking.TYPE
    assert site.TYPE == "site"
    assert parking.TYPE == "parking"
