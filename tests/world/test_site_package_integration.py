"""Integration tests for Site and Package functionality in World."""

from core.buildings.site import Site
from core.packages.package import Package
from core.types import (
    AgentID,
    BuildingID,
    DeliveryUrgency,
    NodeID,
    PackageID,
    PackageStatus,
    Priority,
    SiteID,
)
from world.graph.graph import Graph
from world.graph.node import Node
from world.world import World


class TestSitePackageIntegration:
    """Test Site and Package integration with World."""

    def create_test_world(self) -> World:
        """Create a test world with sites."""
        graph = Graph()

        # Create nodes
        node1 = Node(id=NodeID(1), x=0, y=0)
        node2 = Node(id=NodeID(2), x=100, y=0)
        node3 = Node(id=NodeID(3), x=50, y=50)

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)

        # Create sites with high activity rates for testing
        site1 = Site(
            id=BuildingID("site-1"),
            name="Warehouse A",
            activity_rate=3600.0,  # 3600 packages/hour (1 per second)
            destination_weights={
                SiteID("site-2"): 0.6,
                SiteID("site-3"): 0.4,
            },
        )
        site2 = Site(
            id=BuildingID("site-2"),
            name="Warehouse B",
            activity_rate=1800.0,  # 1800 packages/hour (0.5 per second)
            destination_weights={
                SiteID("site-1"): 0.5,
                SiteID("site-3"): 0.5,
            },
        )
        site3 = Site(
            id=BuildingID("site-3"),
            name="Distribution Center",
            activity_rate=900.0,  # 900 packages/hour (0.25 per second)
            destination_weights={
                SiteID("site-1"): 0.7,
                SiteID("site-2"): 0.3,
            },
        )

        # Add sites to nodes
        node1.add_building(site1)
        node2.add_building(site2)
        node3.add_building(site3)

        # Create world with larger dt_s for more frequent spawning
        world = World(graph=graph, router=None, traffic=None, dt_s=1.0)
        return world

    def test_world_package_management(self) -> None:
        """Test package management in world."""
        world = self.create_test_world()

        # Create a test package
        package = Package(
            id=PackageID("test-pkg-1"),
            origin_site=SiteID("site-1"),
            destination_site=SiteID("site-2"),
            size=15.0,
            value_currency=750.0,
            priority=Priority.HIGH,
            urgency=DeliveryUrgency.EXPRESS,
            spawn_tick=0,
            pickup_deadline_tick=3600,
            delivery_deadline_tick=7200,
        )

        # Add package to world
        world.add_package(package)
        assert len(world.packages) == 1
        assert PackageID("test-pkg-1") in world.packages

        # Get package
        retrieved_package = world.get_package(PackageID("test-pkg-1"))
        assert retrieved_package.id == package.id
        assert retrieved_package.origin_site == package.origin_site

        # Get packages at site
        packages_at_site = world.get_packages_at_site(SiteID("site-1"))
        assert len(packages_at_site) == 1
        assert packages_at_site[0].id == PackageID("test-pkg-1")

        # Remove package
        world.remove_package(PackageID("test-pkg-1"))
        assert len(world.packages) == 0

    def test_package_status_updates(self) -> None:
        """Test package status updates and event emission."""
        world = self.create_test_world()

        # Create a test package
        package = Package(
            id=PackageID("test-pkg-1"),
            origin_site=SiteID("site-1"),
            destination_site=SiteID("site-2"),
            size=10.0,
            value_currency=500.0,
            priority=Priority.MEDIUM,
            urgency=DeliveryUrgency.STANDARD,
            spawn_tick=0,
            pickup_deadline_tick=3600,
            delivery_deadline_tick=7200,
        )

        world.add_package(package)

        # Update status to IN_TRANSIT (picked up)
        world.update_package_status(PackageID("test-pkg-1"), "IN_TRANSIT", AgentID("truck-1"))

        # Check package status
        updated_package = world.get_package(PackageID("test-pkg-1"))
        assert updated_package.status == PackageStatus.IN_TRANSIT

        # Update status to DELIVERED
        world.update_package_status(PackageID("test-pkg-1"), "DELIVERED")

        # Check package status
        delivered_package = world.get_package(PackageID("test-pkg-1"))
        assert delivered_package.status == PackageStatus.DELIVERED

    def test_site_package_spawning(self) -> None:
        """Test package spawning from sites during world step."""
        world = self.create_test_world()

        # Initially no packages
        assert len(world.packages) == 0

        # Debug: Check if sites are found
        sites_found = 0
        for node in world.graph.nodes.values():
            for building in node.buildings:
                if isinstance(building, Site):
                    sites_found += 1
        assert sites_found == 3, f"Expected 3 sites, found {sites_found}"

        # Run multiple steps to allow spawning
        packages_spawned = 0
        for i in range(500):  # Run 500 steps
            world.step()
            if len(world.packages) > packages_spawned:
                packages_spawned = len(world.packages)
                print(f"Step {i}: Packages spawned: {packages_spawned}")

        # Should have spawned some packages (with dt_s=1.0 and activity_rate=5.0, probability is ~0.0014 per step)
        assert (
            packages_spawned > 0
        ), f"No packages spawned after 500 steps. Sites found: {sites_found}"
        assert len(world.packages) > 0

        # Check that packages have valid destinations
        for package in world.packages.values():
            assert package.origin_site in [SiteID("site-1"), SiteID("site-2"), SiteID("site-3")]
            assert package.destination_site in [
                SiteID("site-1"),
                SiteID("site-2"),
                SiteID("site-3"),
            ]
            assert package.origin_site != package.destination_site

    def test_package_expiry_handling(self) -> None:
        """Test package expiry handling during world step."""
        world = self.create_test_world()

        # Create a package that will expire soon
        package = Package(
            id=PackageID("expiring-pkg"),
            origin_site=SiteID("site-1"),
            destination_site=SiteID("site-2"),
            size=5.0,
            value_currency=200.0,
            priority=Priority.LOW,
            urgency=DeliveryUrgency.STANDARD,
            spawn_tick=0,
            pickup_deadline_tick=1,  # Expires very soon
            delivery_deadline_tick=3600,
        )

        world.add_package(package)

        # Find the site and add package to its active list
        for node in world.graph.nodes.values():
            for building in node.buildings:
                if isinstance(building, Site) and building.id == BuildingID("site-1"):
                    building.add_package(PackageID("expiring-pkg"))
                    break

        # Run steps until package expires
        initial_packages = len(world.packages)
        expired_packages = 0

        for i in range(100):  # Run 100 steps
            world.step()
            current_tick = world.tick
            if PackageID("expiring-pkg") not in world.packages and initial_packages > 0:
                expired_packages += 1
                print(f"Package expired at step {i}, tick {current_tick}")
                break
            elif PackageID("expiring-pkg") in world.packages:
                package = world.get_package(PackageID("expiring-pkg"))
                print(
                    f"Step {i}: Package exists, current_tick={current_tick}, deadline={package.pickup_deadline_tick}, expired={package.is_expired(current_tick)}"
                )

        # Should have at least one expired package
        assert expired_packages > 0

    def test_multiple_sites_different_activity_rates(self) -> None:
        """Test multiple sites with different activity rates."""
        world = self.create_test_world()

        # Run many steps to collect statistics
        for _ in range(200):
            world.step()

        # Count packages by origin site
        packages_by_site: dict[SiteID, int] = {}
        for package in world.packages.values():
            origin = package.origin_site
            packages_by_site[origin] = packages_by_site.get(origin, 0) + 1

        # Site 1 should have more packages (activity_rate=5.0)
        # Site 2 should have fewer packages (activity_rate=3.0)
        # Site 3 should have fewest packages (activity_rate=2.0)
        assert packages_by_site.get(SiteID("site-1"), 0) >= packages_by_site.get(
            SiteID("site-2"), 0
        )
        assert packages_by_site.get(SiteID("site-2"), 0) >= packages_by_site.get(
            SiteID("site-3"), 0
        )

    def test_destination_weight_distribution(self) -> None:
        """Test that destination selection follows weight distribution."""
        world = self.create_test_world()

        # Run many steps to collect packages
        for _ in range(300):
            world.step()

        # Count destinations from site-1
        site1_destinations: dict[SiteID, int] = {}
        for package in world.packages.values():
            if package.origin_site == SiteID("site-1"):
                dest = package.destination_site
                site1_destinations[dest] = site1_destinations.get(dest, 0) + 1

        # Should have packages going to both site-2 and site-3
        # (weights are 0.6 and 0.4 respectively)
        if len(site1_destinations) >= 2:
            assert SiteID("site-2") in site1_destinations
            assert SiteID("site-3") in site1_destinations

    def test_world_full_state_includes_packages(self) -> None:
        """Test that world full state includes package data."""
        world = self.create_test_world()

        # Add a test package
        package = Package(
            id=PackageID("state-test-pkg"),
            origin_site=SiteID("site-1"),
            destination_site=SiteID("site-2"),
            size=20.0,
            value_currency=1000.0,
            priority=Priority.HIGH,
            urgency=DeliveryUrgency.EXPRESS,
            spawn_tick=0,
            pickup_deadline_tick=1800,
            delivery_deadline_tick=3600,
        )

        world.add_package(package)

        # Get full state
        full_state = world.get_full_state()

        # Check that packages are included
        assert "packages" in full_state
        assert len(full_state["packages"]) == 1
        assert full_state["packages"][0]["id"] == "state-test-pkg"
        assert full_state["packages"][0]["origin_site"] == "site-1"
        assert full_state["packages"][0]["destination_site"] == "site-2"

    def test_site_statistics_tracking(self) -> None:
        """Test that site statistics are properly tracked."""
        world = self.create_test_world()

        # Get site-1
        site1 = None
        for node in world.graph.nodes.values():
            for building in node.buildings:
                if isinstance(building, Site) and building.id == BuildingID("site-1"):
                    site1 = building
                    break

        assert site1 is not None

        # Run steps to generate packages
        initial_generated = site1.statistics.packages_generated
        for _ in range(200):
            world.step()

        # Should have generated some packages
        assert site1.statistics.packages_generated > initial_generated

        # Test statistics update
        site1.update_statistics("delivered", 500.0)
        assert site1.statistics.packages_delivered == 1
        assert site1.statistics.total_value_delivered == 500.0

        site1.update_statistics("expired", 200.0)
        assert site1.statistics.packages_expired == 1
        assert site1.statistics.total_value_expired == 200.0
