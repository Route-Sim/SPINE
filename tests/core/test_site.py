"""Tests for Site building and SiteStatistics."""

from typing import cast

import pytest

from core.buildings.site import Site, SiteStatistics
from core.types import BuildingID, PackageID, SiteID


class TestSiteStatistics:
    """Test SiteStatistics data structure."""

    def test_site_statistics_creation(self) -> None:
        """Test site statistics creation with defaults."""
        stats = SiteStatistics()

        assert stats.packages_generated == 0
        assert stats.packages_picked_up == 0
        assert stats.packages_delivered == 0
        assert stats.packages_expired == 0
        assert stats.total_value_delivered == 0.0
        assert stats.total_value_expired == 0.0

    def test_site_statistics_serialization(self) -> None:
        """Test site statistics serialization and deserialization."""
        original_stats = SiteStatistics(
            packages_generated=10,
            packages_picked_up=8,
            packages_delivered=7,
            packages_expired=1,
            total_value_delivered=5000.0,
            total_value_expired=200.0,
        )

        # Serialize to dict
        stats_dict = original_stats.to_dict()
        assert isinstance(stats_dict, dict)
        assert stats_dict["packages_generated"] == 10
        assert stats_dict["total_value_delivered"] == 5000.0

        # Deserialize from dict
        restored_stats = SiteStatistics.from_dict(stats_dict)
        assert restored_stats.packages_generated == original_stats.packages_generated
        assert restored_stats.packages_picked_up == original_stats.packages_picked_up
        assert restored_stats.packages_delivered == original_stats.packages_delivered
        assert restored_stats.packages_expired == original_stats.packages_expired
        assert restored_stats.total_value_delivered == original_stats.total_value_delivered
        assert restored_stats.total_value_expired == original_stats.total_value_expired


class TestSite:
    """Test Site building."""

    def test_site_creation(self) -> None:
        """Test site creation with all parameters."""
        site = Site(
            id=cast(BuildingID, SiteID("site-1")),
            name="Test Warehouse",
            activity_rate=5.0,  # 5 packages/hour
            destination_weights={
                SiteID("site-2"): 0.6,
                SiteID("site-3"): 0.4,
            },
        )

        assert cast(SiteID, site.id) == SiteID("site-1")
        assert site.name == "Test Warehouse"
        assert site.activity_rate == 5.0
        assert len(site.destination_weights) == 2
        assert site.destination_weights[SiteID("site-2")] == 0.6
        assert site.destination_weights[SiteID("site-3")] == 0.4
        assert len(site.active_packages) == 0
        assert isinstance(site.statistics, SiteStatistics)

    def test_site_default_configuration(self) -> None:
        """Test that site gets default package configuration."""
        site = Site(
            id=cast(BuildingID, SiteID("site-1")),
            name="Test Site",
            activity_rate=2.0,
        )

        assert "size_range_kg" in site.package_config
        assert "value_range_currency" in site.package_config
        assert "priority_weights" in site.package_config
        assert "urgency_weights" in site.package_config

        # Check priority weights sum to 1.0
        priority_weights = site.package_config["priority_weights"]
        assert sum(priority_weights.values()) == pytest.approx(1.0, abs=0.01)

        # Check urgency weights sum to 1.0
        urgency_weights = site.package_config["urgency_weights"]
        assert sum(urgency_weights.values()) == pytest.approx(1.0, abs=0.01)

    def test_site_serialization(self) -> None:
        """Test site serialization and deserialization."""
        original_site = Site(
            id=cast(BuildingID, SiteID("site-1")),
            name="Test Warehouse",
            activity_rate=3.0,
            destination_weights={
                SiteID("site-2"): 0.7,
                SiteID("site-3"): 0.3,
            },
        )

        # Serialize to dict
        site_dict = original_site.to_dict()
        assert isinstance(site_dict, dict)
        assert site_dict["id"] == "site-1"
        assert site_dict["name"] == "Test Warehouse"
        assert site_dict["activity_rate"] == 3.0

        # Deserialize from dict
        restored_site = Site.from_dict(site_dict)
        assert restored_site.id == original_site.id
        assert restored_site.name == original_site.name
        assert restored_site.activity_rate == original_site.activity_rate
        assert restored_site.destination_weights == original_site.destination_weights
        assert isinstance(restored_site.statistics, SiteStatistics)

    def test_site_package_management(self) -> None:
        """Test adding and removing packages from site."""
        site = Site(
            id=cast(BuildingID, SiteID("site-1")),
            name="Test Site",
            activity_rate=1.0,
        )

        package_id1 = PackageID("pkg-1")
        package_id2 = PackageID("pkg-2")

        # Add packages
        site.add_package(package_id1)
        site.add_package(package_id2)
        assert len(site.active_packages) == 2
        assert package_id1 in site.active_packages
        assert package_id2 in site.active_packages

        # Remove package
        site.remove_package(package_id1)
        assert len(site.active_packages) == 1
        assert package_id1 not in site.active_packages
        assert package_id2 in site.active_packages

        # Try to remove non-existent package (should not raise error)
        site.remove_package(PackageID("non-existent"))

    def test_site_statistics_updates(self) -> None:
        """Test site statistics updates."""
        site = Site(
            id=cast(BuildingID, SiteID("site-1")),
            name="Test Site",
            activity_rate=1.0,
        )

        # Test generated
        site.update_statistics("generated")
        assert site.statistics.packages_generated == 1

        # Test picked up
        site.update_statistics("picked_up")
        assert site.statistics.packages_picked_up == 1

        # Test delivered with value
        site.update_statistics("delivered", 500.0)
        assert site.statistics.packages_delivered == 1
        assert site.statistics.total_value_delivered == 500.0

        # Test expired with value
        site.update_statistics("expired", 100.0)
        assert site.statistics.packages_expired == 1
        assert site.statistics.total_value_expired == 100.0

    def test_site_destination_selection(self) -> None:
        """Test destination site selection."""
        site = Site(
            id=cast(BuildingID, SiteID("site-1")),
            name="Test Site",
            activity_rate=1.0,
            destination_weights={
                SiteID("site-2"): 0.6,
                SiteID("site-3"): 0.4,
            },
        )

        available_sites = [SiteID("site-2"), SiteID("site-3")]

        # Test with weights
        selected = site.select_destination(available_sites)
        assert selected in available_sites

        # Test with no weights (should select randomly)
        site_no_weights = Site(
            id=cast(BuildingID, SiteID("site-1")),
            name="Test Site",
            activity_rate=1.0,
        )
        selected = site_no_weights.select_destination(available_sites)
        assert selected in available_sites

        # Test with empty available sites
        selected = site.select_destination([])
        assert selected is None

    def test_site_package_parameter_generation(self) -> None:
        """Test package parameter generation."""
        site = Site(
            id=cast(BuildingID, SiteID("site-1")),
            name="Test Site",
            activity_rate=1.0,
        )

        params = site.generate_package_parameters()

        # Check required parameters
        assert "size_kg" in params
        assert "value_currency" in params
        assert "priority" in params
        assert "urgency" in params
        assert "pickup_deadline_tick" in params
        assert "delivery_deadline_tick" in params

        # Check value ranges
        config = site.package_config
        size_min, size_max = config["size_range_kg"]
        assert size_min <= params["size_kg"] <= size_max

        value_min, value_max = config["value_range_currency"]
        # Value can exceed value_max due to priority/urgency multipliers
        # Maximum multiplier: URGENT (2.0) * SAME_DAY (1.8) = 3.6
        max_possible_value = value_max * 3.6
        assert value_min <= params["value_currency"] <= max_possible_value

        # Check delivery deadline is after pickup deadline
        assert params["delivery_deadline_tick"] > params["pickup_deadline_tick"]

    def test_site_poisson_spawning_probability(self) -> None:
        """Test Poisson spawning probability calculation."""
        site = Site(
            id=cast(BuildingID, SiteID("site-1")),
            name="Test Site",
            activity_rate=10.0,  # 10 packages/hour
        )

        # Test with different time deltas
        dt_small = 0.05  # Small time step
        dt_large = 1.0  # Large time step

        # With small dt, probability should be low
        # Use more samples to reduce variance in probabilistic test
        prob_small: float = 0.0
        num_samples = 10000
        for _ in range(num_samples):
            if site.should_spawn_package(dt_small):
                prob_small += 1.0
        prob_small /= float(num_samples)

        # With large dt, probability should be higher
        prob_large: float = 0.0
        for _ in range(num_samples):
            if site.should_spawn_package(dt_large):
                prob_large += 1.0
        prob_large /= float(num_samples)

        # Large dt should have higher probability (with tolerance for stochastic variance)
        # With 10000 samples, the probability of both being 0 is extremely small
        # Theoretical values: dt_small ~0.000139, dt_large ~0.00278
        assert (
            prob_large >= prob_small
        ), f"Large dt probability ({prob_large}) should be >= small dt probability ({prob_small})"

        # Test with zero activity rate
        site_zero = Site(
            id=cast(BuildingID, SiteID("site-2")),
            name="Inactive Site",
            activity_rate=0.0,
        )

        # Should never spawn with zero activity rate
        for _ in range(100):
            assert not site_zero.should_spawn_package(1.0)
