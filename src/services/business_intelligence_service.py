from src.services.base_service import BaseService
from src.core.settings import Settings
from src.database.database import DatabaseConnection
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime, timedelta
class BusinessIntelligenceService(BaseService):
    """Service for business intelligence and analytics."""

    def __init__(self, settings: Settings, database: DatabaseConnection):
        """Initialize the BusinessIntelligenceService."""
        super().__init__(settings, database)
        self.logger = logging.getLogger(__name__)
    async def initialize(self):
        """Initialize required resources."""
        await super().ensure_initialized()
        self.logger.info("BusinessIntelligenceService initialized")

    async def get_optimization_metrics(self) -> Dict[str, Any]:
        """Get metrics from optimization results."""
        try:
            async with self.database.async_session() as session:
                results = await session.execute(
                    """SELECT total_distance, total_cost, vehicle_count 
                       FROM optimization_results"""
                )
                data = results.fetchall()
                
                if not data:
                    return {
                        "total_optimizations": 0,
                        "average_distance": 0,
                        "average_cost": 0,
                        "average_vehicles": 0
                    }

                df = pd.DataFrame(data, columns=["total_distance", "total_cost", "vehicle_count"])
                
                return {
                    "total_optimizations": len(df),
                    "average_distance": float(df["total_distance"].mean()),
                    "average_cost": float(df["total_cost"].mean()),
                    "average_vehicles": float(df["vehicle_count"].mean())
                }
        except Exception as e:
            self.logger.error(f"Error getting optimization metrics: {str(e)}")
            return {
                "error": str(e),
                "total_optimizations": 0,
                "average_distance": 0,
                "average_cost": 0,
                "average_vehicles": 0
            }

    async def get_historical_metrics(self) -> Optional[Dict[str, Any]]:
        """Get historical optimization metrics."""
        try:
            async with self.database.async_session() as session:
                # Get optimization results for the last 30 days
                thirty_days_ago = datetime.now() - timedelta(days=30)
                
                query = """
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as total_runs,
                        AVG(total_distance) as avg_distance,
                        AVG(total_cost) as avg_cost,
                        AVG(vehicle_count) as avg_vehicles
                    FROM optimization_results
                    WHERE created_at >= :start_date
                    GROUP BY DATE(created_at)
                    ORDER BY date ASC
                """
                
                result = await session.execute(
                    query,
                    {"start_date": thirty_days_ago}
                )
                data = await result.fetchall()  # Make sure to await the fetch
                
                if not data:
                    return None

                # Convert data to dictionary format
                return {
                    "dates": [row[0].strftime("%Y-%m-%d") if isinstance(row[0], datetime) else row[0] for row in data],
                    "total_runs": [int(row[1]) for row in data],
                    "avg_distance": [float(row[2]) for row in data],
                    "avg_cost": [float(row[3]) for row in data],
                    "avg_vehicles": [float(row[4]) for row in data]
                }

        except Exception as e:
            self.logger.error(f"Error getting historical metrics: {str(e)}")
            return None

    async def cleanup(self):
        """Cleanup resources."""
        await super().cleanup()
        self.logger.info("BusinessIntelligenceService cleaned up")
