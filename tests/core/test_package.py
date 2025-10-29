"""Tests for Package data structure."""

from core.packages.package import Package
from core.types import (
    DeliveryUrgency,
    PackageID,
    PackageStatus,
    Priority,
    SiteID,
)


class TestPackage:
    """Test Package data structure."""

    def test_package_creation(self) -> None:
        """Test package creation with all parameters."""
        package = Package(
            id=PackageID("pkg-123"),
            origin_site=SiteID("site-1"),
            destination_site=SiteID("site-2"),
            size_kg=25.5,
            value_currency=1500.0,
            priority=Priority.HIGH,
            urgency=DeliveryUrgency.EXPRESS,
            spawn_tick=1000,
            pickup_deadline_tick=4600,
            delivery_deadline_tick=8200,
        )

        assert package.id == PackageID("pkg-123")
        assert package.origin_site == SiteID("site-1")
        assert package.destination_site == SiteID("site-2")
        assert package.size_kg == 25.5
        assert package.value_currency == 1500.0
        assert package.priority == Priority.HIGH
        assert package.urgency == DeliveryUrgency.EXPRESS
        assert package.spawn_tick == 1000
        assert package.pickup_deadline_tick == 4600
        assert package.delivery_deadline_tick == 8200
        assert package.status == PackageStatus.WAITING_PICKUP

    def test_package_default_status(self) -> None:
        """Test that package defaults to WAITING_PICKUP status."""
        package = Package(
            id=PackageID("pkg-123"),
            origin_site=SiteID("site-1"),
            destination_site=SiteID("site-2"),
            size_kg=10.0,
            value_currency=100.0,
            priority=Priority.MEDIUM,
            urgency=DeliveryUrgency.STANDARD,
            spawn_tick=0,
            pickup_deadline_tick=3600,
            delivery_deadline_tick=7200,
        )

        assert package.status == PackageStatus.WAITING_PICKUP

    def test_package_serialization(self) -> None:
        """Test package serialization and deserialization."""
        original_package = Package(
            id=PackageID("pkg-123"),
            origin_site=SiteID("site-1"),
            destination_site=SiteID("site-2"),
            size_kg=25.5,
            value_currency=1500.0,
            priority=Priority.HIGH,
            urgency=DeliveryUrgency.EXPRESS,
            spawn_tick=1000,
            pickup_deadline_tick=4600,
            delivery_deadline_tick=8200,
            status=PackageStatus.IN_TRANSIT,
        )

        # Serialize to dict
        package_dict = original_package.to_dict()
        assert isinstance(package_dict, dict)
        assert package_dict["id"] == "pkg-123"
        assert package_dict["priority"] == "HIGH"
        assert package_dict["urgency"] == "EXPRESS"
        assert package_dict["status"] == "IN_TRANSIT"

        # Deserialize from dict
        restored_package = Package.from_dict(package_dict)
        assert restored_package.id == original_package.id
        assert restored_package.origin_site == original_package.origin_site
        assert restored_package.destination_site == original_package.destination_site
        assert restored_package.size_kg == original_package.size_kg
        assert restored_package.value_currency == original_package.value_currency
        assert restored_package.priority == original_package.priority
        assert restored_package.urgency == original_package.urgency
        assert restored_package.spawn_tick == original_package.spawn_tick
        assert restored_package.pickup_deadline_tick == original_package.pickup_deadline_tick
        assert restored_package.delivery_deadline_tick == original_package.delivery_deadline_tick
        assert restored_package.status == original_package.status

    def test_package_expiry_check(self) -> None:
        """Test package expiry checking."""
        package = Package(
            id=PackageID("pkg-123"),
            origin_site=SiteID("site-1"),
            destination_site=SiteID("site-2"),
            size_kg=10.0,
            value_currency=100.0,
            priority=Priority.MEDIUM,
            urgency=DeliveryUrgency.STANDARD,
            spawn_tick=0,
            pickup_deadline_tick=3600,  # 1 hour
            delivery_deadline_tick=7200,  # 2 hours
        )

        # Before expiry
        assert not package.is_expired(1800)  # 30 minutes
        assert not package.is_expired(3599)  # just before deadline

        # At and after expiry
        assert package.is_expired(3600)  # exactly at deadline
        assert package.is_expired(3601)  # 1 tick after deadline
        assert package.is_expired(7200)  # 2 hours

    def test_package_delivery_overdue_check(self) -> None:
        """Test package delivery overdue checking."""
        package = Package(
            id=PackageID("pkg-123"),
            origin_site=SiteID("site-1"),
            destination_site=SiteID("site-2"),
            size_kg=10.0,
            value_currency=100.0,
            priority=Priority.MEDIUM,
            urgency=DeliveryUrgency.STANDARD,
            spawn_tick=0,
            pickup_deadline_tick=3600,  # 1 hour
            delivery_deadline_tick=7200,  # 2 hours
        )

        # Before delivery deadline
        assert not package.is_delivery_overdue(3600)  # 1 hour
        assert not package.is_delivery_overdue(7199)  # just before deadline

        # At and after delivery deadline
        assert not package.is_delivery_overdue(7200)  # exactly at deadline (not overdue yet)
        assert package.is_delivery_overdue(7201)  # 1 tick after deadline
        assert package.is_delivery_overdue(14400)  # 4 hours

    def test_package_remaining_time_calculations(self) -> None:
        """Test remaining time calculations."""
        package = Package(
            id=PackageID("pkg-123"),
            origin_site=SiteID("site-1"),
            destination_site=SiteID("site-2"),
            size_kg=10.0,
            value_currency=100.0,
            priority=Priority.MEDIUM,
            urgency=DeliveryUrgency.STANDARD,
            spawn_tick=0,
            pickup_deadline_tick=3600,  # 1 hour
            delivery_deadline_tick=7200,  # 2 hours
        )

        # Test remaining pickup time
        assert package.get_remaining_pickup_time_ticks(0) == 3600
        assert package.get_remaining_pickup_time_ticks(1800) == 1800
        assert package.get_remaining_pickup_time_ticks(3600) == 0
        assert package.get_remaining_pickup_time_ticks(7200) == 0  # Should not go negative

        # Test remaining delivery time
        assert package.get_remaining_delivery_time_ticks(0) == 7200
        assert package.get_remaining_delivery_time_ticks(3600) == 3600
        assert package.get_remaining_delivery_time_ticks(7200) == 0
        assert package.get_remaining_delivery_time_ticks(14400) == 0  # Should not go negative
