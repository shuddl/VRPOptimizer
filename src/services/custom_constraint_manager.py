from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from ortools.constraint_solver import pywrapcp
from src.core.exceptions import OptimizationError
from src.core.models import Shipment


@dataclass
class ConstraintConfig:
    """Configuration for custom constraints."""

    enabled: bool = True
    weight: int = 1
    penalty: int = 1000


class CustomConstraintManager:
    """Manages custom constraints for the VRP optimization."""

    def __init__(self):
        """Initialize the constraint manager."""
        self.configs = {
            "lifo": ConstraintConfig(enabled=True, weight=2, penalty=1000),
            "time_windows": ConstraintConfig(enabled=True, weight=1, penalty=500),
            "capacity": ConstraintConfig(enabled=True, weight=3, penalty=2000),
            "distance": ConstraintConfig(enabled=True, weight=1, penalty=800),
        }

    def add_lifo_constraints(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        data: Dict,
    ) -> None:
        """
        Add Last-In-First-Out (LIFO) constraints to the routing model.

        Args:
            routing: The routing model
            manager: The routing index manager
            data: The problem data containing shipment information
        """
        if not self.configs["lifo"].enabled:
            return

        try:
            # Create LIFO dimension
            routing.AddDimension(
                routing.RegisterUnaryTransitCallback(lambda index: 1),
                0,  # null capacity slack
                data["num_vehicles"],  # maximum number of active shipments
                True,  # start cumul to zero
                "LIFO",
            )
            lifo_dimension = routing.GetDimensionOrDie("LIFO")

            # Add LIFO constraints for each pair of pickup and delivery
            for request in range(data["num_locations"] // 2):
                pickup_index = manager.NodeToIndex(request)
                delivery_index = manager.NodeToIndex(
                    request + data["num_locations"] // 2
                )

                # Ensure pickup happens before delivery
                routing.AddPickupAndDelivery(pickup_index, delivery_index)

                # Add LIFO constraint
                routing.solver().Add(
                    lifo_dimension.CumulVar(pickup_index)
                    < lifo_dimension.CumulVar(delivery_index)
                )

        except Exception as e:
            raise OptimizationError(f"Failed to add LIFO constraints: {str(e)}")

    def add_capacity_constraints(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        data: Dict,
        vehicle_capacity: int,
    ) -> None:
        """
        Add vehicle capacity constraints to the routing model.

        Args:
            routing: The routing model
            manager: The routing index manager
            data: The problem data containing shipment information
            vehicle_capacity: Maximum vehicle capacity
        """
        if not self.configs["capacity"].enabled:
            return

        try:
            # Register capacity callback
            def demand_callback(from_index: int) -> int:
                """Returns the demand of the node."""
                from_node = manager.IndexToNode(from_index)
                return data["demands"][from_node]

            demand_callback_index = routing.RegisterUnaryTransitCallback(
                demand_callback
            )

            # Add capacity dimension
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,  # null capacity slack
                [vehicle_capacity] * data["num_vehicles"],  # vehicle maximum capacities
                True,  # start cumul to zero
                "Capacity",
            )

        except Exception as e:
            raise OptimizationError(f"Failed to add capacity constraints: {str(e)}")

    def add_time_window_constraints(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        data: Dict,
    ) -> None:
        """
        Add time window constraints to the routing model.

        Args:
            routing: The routing model
            manager: The routing index manager
            data: The problem data containing time windows
        """
        if not self.configs["time_windows"].enabled:
            return

        try:
            # Register time callback
            def time_callback(from_index: int, to_index: int) -> int:
                """Returns the travel time between two nodes."""
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return data["time_matrix"][from_node][to_node]

            transit_callback_index = routing.RegisterTransitCallback(time_callback)

            # Add time dimension
            routing.AddDimension(
                transit_callback_index,
                30,  # allow waiting time
                data["max_route_time"],  # maximum time per vehicle
                False,  # don't force start cumul to zero
                "Time",
            )

            time_dimension = routing.GetDimensionOrDie("Time")

            # Add time window constraints
            for location_idx, time_window in enumerate(data["time_windows"]):
                index = manager.NodeToIndex(location_idx)
                time_dimension.CumulVar(index).SetRange(
                    time_window[0], time_window[1]  # start time  # end time
                )

        except Exception as e:
            raise OptimizationError(f"Failed to add time window constraints: {str(e)}")

    def validate_solution(
        self, solution: List[List[Shipment]]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that all constraints are satisfied in the solution.

        Args:
            solution: List of routes, where each route is a list of shipments

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Validate LIFO constraints
            if self.configs["lifo"].enabled:
                for route in solution:
                    active_shipments = []
                    for shipment in route:
                        if shipment.is_pickup:
                            active_shipments.append(shipment.id)
                        else:
                            if (
                                not active_shipments
                                or active_shipments[-1] != shipment.id
                            ):
                                return False, "LIFO constraint violation"
                            active_shipments.pop()

            # Add other validation logic as needed
            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def update_config(
        self,
        constraint_type: str,
        enabled: bool = True,
        weight: Optional[int] = None,
        penalty: Optional[int] = None,
    ) -> None:
        """
        Update the configuration for a specific constraint type.

        Args:
            constraint_type: Type of constraint to update
            enabled: Whether the constraint should be enabled
            weight: New weight for the constraint
            penalty: New penalty for violating the constraint
        """
        if constraint_type not in self.configs:
            raise ValueError(f"Unknown constraint type: {constraint_type}")

        config = self.configs[constraint_type]
        config.enabled = enabled
        if weight is not None:
            config.weight = weight
        if penalty is not None:
            config.penalty = penalty
