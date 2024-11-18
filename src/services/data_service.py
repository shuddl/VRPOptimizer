# services/data_service.py
import io
from fastapi import UploadFile
import pandas as pd
import numpy as np
from typing import Callable, Tuple, List, Dict, Optional, Any
from datetime import datetime
import logging
from pathlib import Path
import json
from io import BytesIO
import hashlib
from pydantic import BaseModel, validator
import asyncio
import aiofiles

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.core.models import Shipment, Location
from src.core.models import Solution
from src.core.config import SecurityConfig
from src.database.database import DatabaseConnection
from src.services.base_service import BaseService
from src.core.settings import Settings
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from src.services.cache_manager import CacheManager
from src.services.business_intelligence_service import BusinessIntelligenceService


class ShipmentData(BaseModel):
    """Data validation model for shipments."""

    shipment_id: str
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    pallet_count: int
    volume: Optional[float]
    weight: Optional[float]
    pickup_time: Optional[datetime]
    delivery_time: Optional[datetime]

    @validator("pallet_count")
    def validate_pallet_count(cls, v):
        if not 0 < v <= 26:
            raise ValueError("Pallet count must be between 1 and 26")
        return v

    @validator("origin_state", "destination_state")
    def validate_state(cls, v):
        if len(v) != 2:
            raise ValueError("State must be a 2-letter abbreviation")
        return v


class DataService(BaseService):
    """Production-ready data handling service with validation and caching."""

    def __init__(self, settings: Settings, database: DatabaseConnection):
        super().__init__(settings, database)
        self.cache_dir = settings.CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        self.demand_model = LinearRegression()
        self.route_pattern_model = KMeans(n_clusters=5)
        self.scaler = StandardScaler()
        self.cache_manager = CacheManager(settings.REDIS_URL)
        # Pass the settings and database to BusinessIntelligenceService
        self.bi_service = BusinessIntelligenceService(
            settings=settings, database=database
        )

    async def process_excel(
        self, file_content: bytes
    ) -> Tuple[bool, List[str], Optional[List[Shipment]]]:
        """Process Excel file with validation and error handling."""
        try:
            # Check file size
            if len(file_content) > self.settings.MAX_FILE_SIZE:
                return (
                    False,
                    [
                        f"File size exceeds maximum allowed ({self.settings.MAX_FILE_SIZE} bytes)"
                    ],
                    None,
                )

            # Calculate file hash for caching
            file_hash = hashlib.md5(file_content).hexdigest()
            cache_file = self.cache_dir / f"{file_hash}.json"

            # Check cache
            if cache_file.exists():
                try:
                    async with aiofiles.open(cache_file, "r") as f:
                        cached_data = json.loads(await f.read())
                        return True, [], [Shipment.from_dict(s) for s in cached_data]
                except Exception as e:
                    self.logger.warning(f"Cache read failed: {str(e)}")

            # Process Excel file
            df = pd.read_excel(BytesIO(file_content))

            # Validate data structure
            required_columns = {
                "Shipment ID": str,
                "Origin City": str,
                "Origin State": str,
                "Destination City": str,
                "Destination State": str,
                "Pallet Count": int,
            }

            missing_columns = set(required_columns.keys()) - set(df.columns)
            if missing_columns:
                return (
                    False,
                    [f"Missing required columns: {', '.join(missing_columns)}"],
                    None,
                )

            # Convert to structured data
            shipments = []
            errors = []

            for idx, row in df.iterrows():
                try:
                    # Validate row data
                    shipment_data = ShipmentData(
                        shipment_id=str(row["Shipment ID"]),
                        origin_city=str(row["Origin City"]),
                        origin_state=str(row["Origin State"]),
                        destination_city=str(row["Destination City"]),
                        destination_state=str(row["Destination State"]),
                        pallet_count=int(row["Pallet Count"]),
                        volume=float(row["Volume"]) if "Volume" in df.columns else None,
                        weight=float(row["Weight"]) if "Weight" in df.columns else None,
                        pickup_time=pd.to_datetime(row["Pickup Time"])
                        if "Pickup Time" in df.columns
                        else None,
                        delivery_time=pd.to_datetime(row["Delivery Time"])
                        if "Delivery Time" in df.columns
                        else None,
                    )

                    # Create shipment object
                    origin = Location(
                        city=shipment_data.origin_city, state=shipment_data.origin_state
                    )
                    destination = Location(
                        city=shipment_data.destination_city,
                        state=shipment_data.destination_state,
                    )

                    shipment = Shipment(
                        id=shipment_data.shipment_id,
                        origin=origin,
                        destination=destination,
                        pallet_count=shipment_data.pallet_count,
                        volume=shipment_data.volume,
                        weight=shipment_data.weight,
                        pickup_time=shipment_data.pickup_time,
                        delivery_time=shipment_data.delivery_time,
                    )

                    shipments.append(shipment)

                except Exception as e:
                    errors.append(f"Error in row {idx + 2}: {str(e)}")

            if errors:
                return False, errors, None

            # Cache valid results
            try:
                async with aiofiles.open(cache_file, "w") as f:
                    await f.write(json.dumps([s.to_dict() for s in shipments]))
            except Exception as e:
                self.logger.warning(f"Cache write failed: {str(e)}")

            return True, [], shipments

        except Exception as e:
            self.logger.error(f"File processing error: {str(e)}")
            return False, [f"File processing error: {str(e)}"], None

    async def process_json(
        self, file_content: bytes
    ) -> Tuple[bool, List[str], Optional[List[Shipment]]]:
        """Process JSON file with validation and error handling."""
        try:
            data = json.loads(file_content)
            shipments = []
            errors = []

            for idx, item in enumerate(data):
                try:
                    shipment_data = ShipmentData(**item)
                    origin = Location(
                        city=shipment_data.origin_city, state=shipment_data.origin_state
                    )
                    destination = Location(
                        city=shipment_data.destination_city,
                        state=shipment_data.destination_state,
                    )
                    shipment = Shipment(
                        id=shipment_data.shipment_id,
                        origin=origin,
                        destination=destination,
                        pallet_count=shipment_data.pallet_count,
                        volume=shipment_data.volume,
                        weight=shipment_data.weight,
                        pickup_time=shipment_data.pickup_time,
                        delivery_time=shipment_data.delivery_time,
                    )
                    shipments.append(shipment)
                except Exception as e:
                    errors.append(f"Error in item {idx + 1}: {str(e)}")

            if errors:
                return False, errors, None

            return True, [], shipments

        except Exception as e:
            self.logger.error(f"JSON processing error: {str(e)}")
            return False, [f"JSON processing error: {str(e)}"], None

    async def process_csv(
        self, file_content: bytes
    ) -> Tuple[bool, List[str], Optional[List[Shipment]]]:
        """Process CSV file with validation and error handling."""
        try:
            df = pd.read_csv(BytesIO(file_content))
            shipments = []
            errors = []

            for idx, row in df.iterrows():
                try:
                    shipment_data = ShipmentData(
                        shipment_id=str(row["Shipment ID"]),
                        origin_city=str(row["Origin City"]),
                        origin_state=str(row["Origin State"]),
                        destination_city=str(row["Destination City"]),
                        destination_state=str(row["Destination State"]),
                        pallet_count=int(row["Pallet Count"]),
                        volume=float(row["Volume"]) if "Volume" in df.columns else None,
                        weight=float(row["Weight"]) if "Weight" in df.columns else None,
                        pickup_time=pd.to_datetime(row["Pickup Time"])
                        if "Pickup Time" in df.columns
                        else None,
                        delivery_time=pd.to_datetime(row["Delivery Time"])
                        if "Delivery Time" in df.columns
                        else None,
                    )
                    origin = Location(
                        city=shipment_data.origin_city, state=shipment_data.origin_state
                    )
                    destination = Location(
                        city=shipment_data.destination_city,
                        state=shipment_data.destination_state,
                    )
                    shipment = Shipment(
                        id=shipment_data.shipment_id,
                        origin=origin,
                        destination=destination,
                        pallet_count=shipment_data.pallet_count,
                        volume=shipment_data.volume,
                        weight=shipment_data.weight,
                        pickup_time=shipment_data.pickup_time,
                        delivery_time=shipment_data.delivery_time,
                    )
                    shipments.append(shipment)
                except Exception as e:
                    errors.append(f"Error in row {idx + 2}: {str(e)}")

            if errors:
                return False, errors, None

            return True, [], shipments

        except Exception as e:
            self.logger.error(f"CSV processing error: {str(e)}")
            return False, [f"CSV processing error: {str(e)}"], None

    async def validate_data(self, shipments: List[Shipment]) -> Tuple[bool, List[str]]:
        """Validate shipment data for optimization."""
        errors = []

        try:
            # Check total number of shipments
            if len(shipments) > self.settings.MAX_SHIPMENTS:
                errors.append(
                    f"Number of shipments ({len(shipments)}) exceeds maximum allowed "
                    f"({self.settings.MAX_SHIPMENTS})"
                )

            # Validate individual shipments
            total_pallets = 0
            shipment_ids = set()

            for shipment in shipments:
                # Check for duplicate shipment IDs
                if shipment.id in shipment_ids:
                    errors.append(f"Duplicate shipment ID: {shipment.id}")
                shipment_ids.add(shipment.id)

                # Validate pallet count
                if not 0 < shipment.pallet_count <= self.settings.MAX_PALLETS:
                    errors.append(
                        f"Invalid pallet count for shipment {shipment.id}: "
                        f"{shipment.pallet_count}"
                    )
                total_pallets += shipment.pallet_count

                # Validate locations
                if not shipment.origin.state or len(shipment.origin.state) != 2:
                    errors.append(
                        f"Invalid origin state for shipment {shipment.id}: "
                        f"{shipment.origin.state}"
                    )
                if (
                    not shipment.destination.state
                    or len(shipment.destination.state) != 2
                ):
                    errors.append(
                        f"Invalid destination state for shipment {shipment.id}: "
                        f"{shipment.destination.state}"
                    )

                # Validate timing if provided
                if shipment.pickup_time and shipment.delivery_time:
                    if shipment.pickup_time >= shipment.delivery_time:
                        errors.append(
                            f"Invalid timing for shipment {shipment.id}: pickup time must "
                            f"be before delivery time"
                        )

            # Check total capacity
            min_vehicles = (
                total_pallets + self.settings.MAX_PALLETS - 1
            ) // self.settings.MAX_PALLETS
            if min_vehicles > self.settings.MAX_VEHICLES:
                errors.append(
                    f"Total pallet count ({total_pallets}) requires more vehicles than "
                    f"available ({min_vehicles} > {self.settings.MAX_VEHICLES})"
                )

            return len(errors) == 0, errors

        except Exception as e:
            self.logger.error(f"Data validation error: {str(e)}")
            return False, [f"Data validation error: {str(e)}"]

    async def export_solution(
        self, solution: "Solution", format: str = "excel"
    ) -> Tuple[bool, str, Optional[bytes]]:
        """Export solution to specified format."""
        try:
            if format == "excel":
                return await self._export_to_excel(solution)
            elif format == "json":
                return await self._export_to_json(solution)
            else:
                return False, f"Unsupported format: {format}", None

        except Exception as e:
            self.logger.error(f"Export error: {str(e)}")
            return False, f"Export error: {str(e)}", None

    async def _export_to_excel(
        self, solution: "Solution"
    ) -> Tuple[bool, str, Optional[bytes]]:
        """Export solution to Excel format."""
        try:
            # Create Excel file in memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                # Export routes
                routes_data = []
                for route in solution.routes:
                    for i, stop in enumerate(route.stops):
                        routes_data.append(
                            {
                                "Route ID": route.id,
                                "Stop Number": i + 1,
                                "Stop Type": stop[0].capitalize(),
                                "Shipment ID": stop[1].id,
                                "Location": f"{stop[1].origin.city}, {stop[1].origin.state}",
                                "Pallets": stop[1].pallet_count,
                            }
                        )

                pd.DataFrame(routes_data).to_excel(
                    writer, sheet_name="Routes", index=False
                )

                # Export summary
                summary_data = {
                    "Metric": ["Total Distance", "Total Cost", "Total Routes"],
                    "Value": [
                        f"{solution.total_distance:.1f} miles",
                        f"${solution.total_cost:.2f}",
                        len(solution.routes),
                    ],
                }
                pd.DataFrame(summary_data).to_excel(
                    writer, sheet_name="Summary", index=False
                )

            return True, "Success", output.getvalue()

        except Exception as e:
            self.logger.error(f"Excel export error: {str(e)}")
            return False, f"Excel export error: {str(e)}", None

    async def _export_to_json(
        self, solution: "Solution"
    ) -> Tuple[bool, str, Optional[bytes]]:
        """Export solution to JSON format."""
        try:
            json_data = solution.to_dict()
            return True, "Success", json.dumps(json_data, indent=2).encode("utf-8")

        except Exception as e:
            self.logger.error(f"JSON export error: {str(e)}")
            return False, f"JSON export error: {str(e)}", None

    async def predict_demand(self, historical_data: pd.DataFrame) -> pd.DataFrame:
        """Predict future demand based on historical data."""
        try:
            features = historical_data[["pallet_count", "volume", "weight"]]
            targets = historical_data["demand"]

            # Scale features
            scaled_features = self.scaler.fit_transform(features)

            # Train model
            self.demand_model.fit(scaled_features, targets)

            # Predict future demand
            future_demand = self.demand_model.predict(scaled_features)
            historical_data["predicted_demand"] = future_demand

            return historical_data

        except Exception as e:
            self.logger.error(f"Demand prediction error: {str(e)}")
            raise

    async def analyze_route_patterns(self, shipment_data: pd.DataFrame) -> pd.DataFrame:
        """Analyze route patterns using clustering."""
        try:
            features = shipment_data[
                ["origin_lat", "origin_lng", "destination_lat", "destination_lng"]
            ]

            # Scale features
            scaled_features = self.scaler.fit_transform(features)

            # Train clustering model
            self.route_pattern_model.fit(scaled_features)

            # Predict clusters
            clusters = self.route_pattern_model.predict(scaled_features)
            shipment_data["route_cluster"] = clusters

            return shipment_data

        except Exception as e:
            self.logger.error(f"Route pattern analysis error: {str(e)}")
            raise

    async def calculate_dynamic_pricing(
        self, shipment_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Calculate dynamic pricing based on historical data."""
        if not self.settings.FEATURE_DYNAMIC_PRICING:
            self.logger.info("Dynamic pricing feature is disabled")
            return shipment_data

        try:
            # Example pricing model: base price + demand factor + route complexity factor
            base_price = 100
            demand_factor = shipment_data["predicted_demand"] * 0.1
            route_complexity_factor = shipment_data["route_cluster"] * 5

            shipment_data["dynamic_price"] = (
                base_price + demand_factor + route_complexity_factor
            )

            return shipment_data

        except Exception as e:
            self.logger.error(f"Dynamic pricing calculation error: {str(e)}")
            raise

    async def process_batch(
        self, files: List[UploadFile]
    ) -> List[Tuple[bool, List[str], Optional[List[Shipment]]]]:
        """Process multiple optimization requests in batch."""
        results = []
        async with asyncio.TaskGroup() as group:
            for file in files:
                task = group.create_task(self._process_single_file(file))
                results.append(task)
        return [await result for result in results]

    async def _process_single_file(
        self, file: UploadFile
    ) -> Tuple[bool, List[str], Optional[List[Shipment]]]:
        """Process a single file."""
        content = await file.read()
        return await self.process_excel(content)

    def export_solution(self, solution, format: str):
        """Export the solution to the specified format."""
        try:
            if format == "excel":
                # Example: Convert solution to Excel bytes
                excel_bytes = self._convert_to_excel(solution)
                return excel_bytes
            elif format == "json":
                return json.dumps(solution).encode("utf-8")
            else:
                raise ValueError(f"Unsupported export format: {format}")
        except Exception as e:
            print(f"Error exporting solution: {str(e)}")
            raise

    def _convert_to_excel(self, solution):
        """Convert solution data to Excel format."""
        df = pd.DataFrame(solution)  # Adjust based on solution structure
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()

    async def generate_bi_reports(self, timeframe: str) -> Dict[str, Any]:
        """Generate business intelligence reports."""
        if not self.settings.FEATURE_BI_REPORTS:
            self.logger.info("Business intelligence reports feature is disabled")
            return {}

        return await self.bi_service.generate_reports(timeframe)


class DataValidationService(BaseService):
    """Service for comprehensive input validation."""

    async def validate_input(self, data: Dict) -> Tuple[bool, List[str]]:
        """Comprehensive input validation."""
        validators = {
            "address_validation": self._validate_addresses,
            "capacity_validation": self._validate_capacity_constraints,
            "time_window_validation": self._validate_time_windows,
        }
        return await self._run_validators(data, validators)

    async def _run_validators(
        self, data: Dict, validators: Dict[str, Callable]
    ) -> Tuple[bool, List[str]]:
        """Run all validators and collect errors."""
        errors = []
        for name, validator in validators.items():
            valid, validation_errors = await validator(data)
            if not valid:
                errors.extend(validation_errors)
        return len(errors) == 0, errors

    async def _validate_addresses(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate addresses in the input data."""
        errors = []
        # Implement address validation logic
        # ...
        return len(errors) == 0, errors

    async def _validate_capacity_constraints(
        self, data: Dict
    ) -> Tuple[bool, List[str]]:
        """Validate capacity constraints in the input data."""
        errors = []
        # Implement capacity validation logic
        # ...
        return len(errors) == 0, errors

    async def _validate_time_windows(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate time windows in the input data."""
        errors = []
        # Implement time window validation logic
        # ...
        return len(errors) == 0, errors
