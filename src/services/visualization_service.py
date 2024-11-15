# services/visualization.py
import folium
from folium import plugins
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import asyncio
import io
import base64
from datetime import datetime
import numpy as np
from src.database.database import DatabaseConnection
from src.core.models import Solution, Route, Shipment
import tempfile
import shutil
import resource
from src.services.base_service import BaseService
from src.core.settings import Settings
import pandas as pd



class VisualizationService(BaseService):
    """Production-ready visualization service with resource management."""

    def __init__(self, settings: Settings, database: DatabaseConnection):
        super().__init__(settings, database)
        self.temp_dir = Path(tempfile.mkdtemp())
        self._setup_resource_limits()

    def __del__(self):
        """Cleanup temporary files on service destruction."""
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            self.logger.error(f"Cleanup error: {str(e)}")

    def _setup_resource_limits(self):
        """Set resource limits for visualization processes."""
        try:
            memory_limit = (
                self.settings.MEMORY_LIMIT_MB * 1024 * 1024
            )  # Convert MB to bytes
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, -1))
        except Exception as e:
            self.logger.warning(f"Could not set resource limits: {str(e)}")

    async def create_route_map(
        self, solution: Solution
    ) -> Tuple[bool, str, Optional[str]]:
        """Create interactive route map with error handling."""
        try:
            # Validate input
            if not solution or not solution.routes:
                return False, "No routes to visualize", None

            # Create base map
            center_lat, center_lon = self._calculate_map_center(solution)
            m = folium.Map(
                location=[center_lat, center_lon], zoom_start=5, tiles="cartodbpositron"
            )

            # Add routes with distinct colors
            colors = self._generate_colors(len(solution.routes))

            for route_idx, route in enumerate(solution.routes):
                route_color = colors[route_idx]
                self._add_route_to_map(m, route, route_color)

            # Add unassigned shipments if any
            if solution.unassigned_shipments:
                self._add_unassigned_shipments(m, solution.unassigned_shipments)

            # Add legend
            self._add_map_legend(m)

            # Save map to temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            map_file = self.temp_dir / f"route_map_{timestamp}.html"
            m.save(str(map_file))

            return True, "Success", str(map_file)

        except Exception as e:
            self.logger.error(f"Map creation error: {str(e)}")
            return False, f"Map creation error: {str(e)}", None

    async def create_timeline(
        self, solution: Solution
    ) -> Tuple[bool, str, Optional[str]]:
        """Create route timeline visualization."""
        try:
            if not solution or not solution.routes:
                return False, "No routes to visualize", None

            # Prepare timeline data
            timeline_data = []

            for route in solution.routes:
                route_data = self._prepare_route_timeline_data(route)
                timeline_data.extend(route_data)

            # Create Gantt chart
            fig = px.timeline(
                timeline_data,
                x_start="Start",
                x_end="End",
                y="Route",
                color="Type",
                hover_data=["Location", "Shipment ID"],
                title="Route Schedule Timeline",
            )

            # Customize layout
            self._customize_timeline_layout(fig)

            # Save to temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            timeline_file = self.temp_dir / f"timeline_{timestamp}.html"
            fig.write_html(str(timeline_file))

            return True, "Success", str(timeline_file)

        except Exception as e:
            self.logger.error(f"Timeline creation error: {str(e)}")
            return False, f"Timeline creation error: {str(e)}", None

    async def create_analytics_dashboard(
        self, solution: Solution
    ) -> Tuple[bool, str, Optional[str]]:
        """Create comprehensive analytics dashboard."""
        try:
            if not solution or not solution.routes:
                return False, "No data to analyze", None

            # Create dashboard with multiple visualizations
            dashboard_data = self._prepare_dashboard_data(solution)

            # Create dashboard figure
            fig = go.Figure()

            # Add route statistics
            self._add_route_statistics(fig, dashboard_data)

            # Add utilization chart
            self._add_utilization_chart(fig, dashboard_data)

            # Add distance distribution
            self._add_distance_distribution(fig, dashboard_data)

            # Save dashboard
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dashboard_file = self.temp_dir / f"dashboard_{timestamp}.html"
            fig.write_html(str(dashboard_file))

            return True, "Success", str(dashboard_file)

        except Exception as e:
            self.logger.error(f"Dashboard creation error: {str(e)}")
            return False, f"Dashboard creation error: {str(e)}", None

    async def create_advanced_analytics(
        self, solution: Solution
    ) -> Tuple[bool, str, Optional[str]]:
        """Generate advanced analytics dashboard."""
        try:
            if not solution or not solution.routes:
                return False, "No data to analyze", None

            # Calculate advanced metrics
            metrics = {
                "cost_per_mile": solution.total_cost / solution.total_distance,
                "vehicle_utilization": self._calculate_utilization(solution),
                "delivery_density": self._calculate_delivery_density(solution),
                "route_efficiency": self._calculate_route_efficiency(solution),
            }

            # Create dashboard figure
            fig = go.Figure()

            # Add advanced metrics
            self._add_advanced_metrics(fig, metrics)

            # Save dashboard
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dashboard_file = self.temp_dir / f"advanced_dashboard_{timestamp}.html"
            fig.write_html(str(dashboard_file))

            return True, "Success", str(dashboard_file)

        except Exception as e:
            self.logger.error(f"Advanced analytics creation error: {str(e)}")
            return False, f"Advanced analytics creation error: {str(e)}", None

    async def create_demand_prediction_chart(
        self, demand_data: pd.DataFrame
    ) -> Tuple[bool, str, Optional[str]]:
        """Create demand prediction chart."""
        try:
            fig = px.line(
                demand_data, x="date", y="predicted_demand", title="Demand Prediction"
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_file = self.temp_dir / f"demand_prediction_{timestamp}.html"
            fig.write_html(str(chart_file))
            return True, "Success", str(chart_file)
        except Exception as e:
            self.logger.error(f"Demand prediction chart creation error: {str(e)}")
            return False, f"Demand prediction chart creation error: {str(e)}", None

    async def create_route_pattern_chart(
        self, shipment_data: pd.DataFrame
    ) -> Tuple[bool, str, Optional[str]]:
        """Create route pattern analysis chart."""
        try:
            fig = px.scatter_mapbox(
                shipment_data,
                lat="origin_lat",
                lon="origin_lng",
                color="route_cluster",
                title="Route Pattern Analysis",
                mapbox_style="carto-positron",
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_file = self.temp_dir / f"route_pattern_{timestamp}.html"
            fig.write_html(str(chart_file))
            return True, "Success", str(chart_file)
        except Exception as e:
            self.logger.error(f"Route pattern chart creation error: {str(e)}")
            return False, f"Route pattern chart creation error: {str(e)}", None

    async def create_dynamic_pricing_chart(
        self, shipment_data: pd.DataFrame
    ) -> Tuple[bool, str, Optional[str]]:
        """Create dynamic pricing chart."""
        try:
            fig = px.bar(
                shipment_data,
                x="shipment_id",
                y="dynamic_price",
                title="Dynamic Pricing",
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_file = self.temp_dir / f"dynamic_pricing_{timestamp}.html"
            fig.write_html(str(chart_file))
            return True, "Success", str(chart_file)
        except Exception as e:
            self.logger.error(f"Dynamic pricing chart creation error: {str(e)}")
            return False, f"Dynamic pricing chart creation error: {str(e)}", None

    def _calculate_utilization(self, solution: Solution) -> float:
        """Calculate vehicle utilization."""
        total_pallets = sum(route.total_pallets for route in solution.routes)
        max_capacity = self.settings.MAX_PALLETS * len(solution.routes)
        return (total_pallets / max_capacity) * 100

    def _calculate_delivery_density(self, solution: Solution) -> float:
        """Calculate delivery density."""
        total_deliveries = sum(len(route.stops) for route in solution.routes)
        total_distance = solution.total_distance
        return total_deliveries / total_distance

    def _calculate_route_efficiency(self, solution: Solution) -> float:
        """Calculate route efficiency."""
        total_distance = solution.total_distance
        total_stops = sum(len(route.stops) for route in solution.routes)
        return total_stops / total_distance

    def _add_advanced_metrics(self, fig: go.Figure, metrics: Dict[str, float]):
        """Add advanced metrics to dashboard."""
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=metrics["cost_per_mile"],
                title="Cost per Mile",
                domain={"row": 0, "column": 0},
            )
        )

        fig.add_trace(
            go.Indicator(
                mode="number",
                value=metrics["vehicle_utilization"],
                title="Vehicle Utilization (%)",
                domain={"row": 0, "column": 1},
            )
        )

        fig.add_trace(
            go.Indicator(
                mode="number",
                value=metrics["delivery_density"],
                title="Delivery Density",
                domain={"row": 1, "column": 0},
            )
        )

        fig.add_trace(
            go.Indicator(
                mode="number",
                value=metrics["route_efficiency"],
                title="Route Efficiency",
                domain={"row": 1, "column": 1},
            )
        )

    def _calculate_map_center(self, solution: Solution) -> Tuple[float, float]:
        """Calculate center point for map."""
        all_lats = []
        all_lons = []

        for route in solution.routes:
            for stop_type, shipment in route.stops:
                location = (
                    shipment.origin if stop_type == "pickup" else shipment.destination
                )
                all_lats.append(location.lat)
                all_lons.append(location.lng)

        return np.mean(all_lats), np.mean(all_lons)

    def _generate_colors(self, n: int) -> List[str]:
        """Generate visually distinct colors."""
        colors = []
        for i in range(n):
            hue = i / n
            saturation = 0.7
            value = 0.9
            rgb = tuple(int(x * 255) for x in self._hsv_to_rgb(hue, saturation, value))
            colors.append(f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}")
        return colors

    def _hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[float, float, float]:
        """Convert HSV to RGB color."""
        if s == 0.0:
            return (v, v, v)

        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6

        if i == 0:
            return (v, t, p)
        if i == 1:
            return (q, v, p)
        if i == 2:
            return (p, v, t)
        if i == 3:
            return (p, q, v)
        if i == 4:
            return (t, p, v)
        return (v, p, q)

    def _add_route_to_map(self, m: folium.Map, route: Route, color: str):
        """Add route to map with styling."""
        coordinates = []

        for stop_idx, (stop_type, shipment) in enumerate(route.stops):
            location = (
                shipment.origin if stop_type == "pickup" else shipment.destination
            )
            coordinates.append([location.lat, location.lng])

            # Create marker
            icon_color = "green" if stop_type == "pickup" else "red"
            popup_html = self._create_stop_popup(route, stop_idx, stop_type, shipment)

            folium.CircleMarker(
                location=[location.lat, location.lng],
                radius=8,
                color=color,
                fill=True,
                fillColor=icon_color,
                fillOpacity=0.7,
                popup=folium.Popup(popup_html, max_width=300),
            ).add_to(m)

        # Add route line
        folium.PolyLine(
            coordinates, weight=2, color=color, opacity=0.8, popup=f"Route {route.id}"
        ).add_to(m)

    def _create_stop_popup(
        self, route: Route, stop_idx: int, stop_type: str, shipment: Shipment
    ) -> str:
        """Create HTML popup content for map markers."""
        return f"""
        <div style="font-family: Arial, sans-serif;">
            <h4>Route {route.id}</h4>
            <p><b>Stop:</b> {stop_idx + 1}</p>
            <p><b>Type:</b> {stop_type.capitalize()}</p>
            <p><b>Shipment:</b> {shipment.id}</p>
            <p><b>Pallets:</b> {shipment.pallet_count}</p>
            <p><b>Location:</b> {shipment.origin.city}, {shipment.origin.state}</p>
        </div>
        """

    def _add_map_legend(self, m: folium.Map):
        """Add legend to map."""
        legend_html = """
        <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; 
                    background-color: white; padding: 10px; border-radius: 5px;">
            <h4>Legend</h4>
            <p><i style="background: green; border-radius: 50%; width: 10px; 
                        height: 10px; display: inline-block;"></i> Pickup</p>
            <p><i style="background: red; border-radius: 50%; width: 10px; 
                        height: 10px; display: inline-block;"></i> Delivery</p>
            <p><i style="background: gray; border-radius: 50%; width: 10px; 
                        height: 10px; display: inline-block;"></i> Unassigned</p>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

    def _prepare_route_timeline_data(self, route: Route) -> List[Dict]:
        """Prepare data for timeline visualization."""
        timeline_data = []
        cumulative_time = 0

        for stop_idx, (stop_type, shipment) in enumerate(route.stops):
            duration = 0.5  # 30 minutes for loading/unloading

            timeline_data.append(
                {
                    "Route": f"Route {route.id}",
                    "Start": cumulative_time,
                    "End": cumulative_time + duration,
                    "Type": stop_type.capitalize(),
                    "Location": f"{shipment.origin.city}, {shipment.origin.state}",
                    "Shipment ID": shipment.id,
                }
            )

            cumulative_time += duration + 0.25  # Add 15 minutes travel time

        return timeline_data

    def _customize_timeline_layout(self, fig: go.Figure):
        """Customize timeline visualization layout."""
        fig.update_layout(
            title_font_size=16,
            showlegend=True,
            height=400,
            xaxis_title="Hours from Start",
            yaxis_title="Route",
            template="plotly_white",
        )

    def _prepare_dashboard_data(self, solution: Solution) -> Dict:
        """Prepare data for analytics dashboard."""
        return {
            "route_statistics": {
                "total_distance": solution.total_distance,
                "total_cost": solution.total_cost,
                "total_routes": len(solution.routes),
                "total_stops": sum(len(r.stops) for r in solution.routes),
                "average_route_length": solution.total_distance / len(solution.routes),
            },
            "utilization": [
                {
                    "route_id": route.id,
                    "utilization": (route.total_pallets / self.settings.MAX_PALLETS)
                    * 100,
                }
                for route in solution.routes
            ],
            "distances": [route.total_distance for route in solution.routes],
        }

    def _add_route_statistics(self, fig: go.Figure, data: Dict):
        """Add route statistics to dashboard."""
        stats = data["route_statistics"]

        fig.add_trace(
            go.Indicator(
                mode="number",
                value=stats["total_routes"],
                title="Total Routes",
                domain={"row": 0, "column": 0},
            )
        )

        fig.add_trace(
            go.Indicator(
                mode="number",
                value=stats["total_distance"],
                title="Total Distance (mi)",
                domain={"row": 0, "column": 1},
            )
        )

    def _add_utilization_chart(self, fig: go.Figure, data: Dict):
        """Add utilization chart to dashboard."""
        utilization_data = data["utilization"]

        fig.add_trace(
            go.Bar(
                name="Utilization",
                x=[u["route_id"] for u in utilization_data],
                y=[u["utilization"] for u in utilization_data],
                text=[f"{u['utilization']:.1f}%" for u in utilization_data],
                textposition="auto",
            )
        )

    def _add_distance_distribution(self, fig: go.Figure, data: Dict):
        """Add distance distribution to dashboard."""
        fig.add_trace(
            go.Histogram(
                x=data["distances"], name="Route Distances", nbinsx=10, showlegend=False
            )
        )
