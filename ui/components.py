# ui/components.py

import streamlit as st
import folium
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Optional
import pandas as pd
from ..src.core.models import Solution, Route, Shipment

class RouteMap:
    """Interactive route map component."""
    def __init__(self):
        self.colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        self._load_custom_js()

    def _load_custom_js(self):
        with open('ui/assets/js/map_utils.js', 'r') as f:
            st.components.v1.html(f"<script>{f.read()}</script>", height=0)

    def render(self, solution: Solution, center: Optional[Dict[str, float]] = None):
        """Render interactive route map."""
        if not solution or not solution.routes:
            st.warning("No routes to display")
            return

        # Create base map
        m = folium.Map(
            location=center or self._calculate_center(solution),
            zoom_start=6,
            tiles='cartodbpositron'
        )

        # Add routes
        for idx, route in enumerate(solution.routes):
            color = self.colors[idx % len(self.colors)]
            self._add_route_to_map(m, route, color)

        # Add custom controls
        self._add_map_controls(m)

        # Display map
        st.components.v1.html(m._repr_html_(), height=600)

    def _calculate_center(self, solution: Solution) -> List[float]:
        """Calculate map center point."""
        lats, lngs = [], []
        for route in solution.routes:
            for stop_type, shipment in route.stops:
                loc = shipment.origin if stop_type == 'pickup' else shipment.destination
                lats.append(loc.lat)
                lngs.append(loc.lng)
        return [sum(lats)/len(lats), sum(lngs)/len(lngs)]

    def _add_route_to_map(self, m: folium.Map, route: Route, color: str):
        """Add a single route to the map."""
        # Create route coordinates
        coords = []
        for stop_type, shipment in route.stops:
            loc = shipment.origin if stop_type == 'pickup' else shipment.destination
            coords.append([loc.lat, loc.lng])
            
            # Add marker
            folium.CircleMarker(
                location=[loc.lat, loc.lng],
                radius=8,
                color=color,
                fill=True,
                fillOpacity=0.7,
                popup=self._create_popup_content(route, stop_type, shipment)
            ).add_to(m)

        # Add route line
        folium.PolyLine(
            coords,
            weight=3,
            color=color,
            opacity=0.7,
            popup=f"Route {route.id}: {route.total_distance:.1f} miles"
        ).add_to(m)

    def _create_popup_content(self, route: Route, stop_type: str, shipment: Shipment) -> str:
        """Create HTML content for marker popups."""
        return f"""
        <div class="popup-content">
            <h4>Route {route.id}</h4>
            <p><b>{stop_type.title()}</b></p>
            <p>Shipment: {shipment.id}</p>
            <p>Location: {shipment.origin.city}, {shipment.origin.state}</p>
            <p>Pallets: {shipment.pallet_count}</p>
        </div>
        """

    def _add_map_controls(self, m: folium.Map):
        """Add custom map controls."""
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Add custom controls
        m.get_root().html.add_child(folium.Element("""
            <div class='map-controls'>
                <button onclick="zoomToFit()">Zoom to Fit</button>
                <button onclick="toggleAllRoutes()">Toggle All Routes</button>
            </div>
        """))

class MetricsPanel:
    """Analytics and metrics visualization."""
    def render(self, solution: Solution):
        """Render metrics dashboard."""
        if not solution:
            st.warning("No data to display")
            return

        # Create metrics layout
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Distance",
                f"{solution.total_distance:.1f} mi",
                delta=None
            )
        
        with col2:
            st.metric(
                "Total Cost",
                f"${solution.total_cost:.2f}",
                delta=None
            )
            
        with col3:
            utilization = self._calculate_utilization(solution)
            st.metric(
                "Avg Utilization",
                f"{utilization:.1f}%",
                delta=None
            )
            
        with col4:
            st.metric(
                "Routes",
                len(solution.routes),
                delta=None
            )

        # Add detailed charts
        self._render_utilization_chart(solution)
        self._render_distance_chart(solution)

    def _calculate_utilization(self, solution: Solution) -> float:
        """Calculate average route utilization."""
        if not solution.routes:
            return 0.0
        utilizations = [
            (route.total_pallets / 26) * 100
            for route in solution.routes
        ]
        return sum(utilizations) / len(utilizations)

    def _render_utilization_chart(self, solution: Solution):
        """Render route utilization chart."""
        data = []
        for route in solution.routes:
            data.append({
                'Route': f"Route {route.id}",
                'Utilization': (route.total_pallets / 26) * 100
            })
            
        fig = px.bar(
            data,
            x='Route',
            y='Utilization',
            title='Route Utilization (%)',
            color='Utilization',
            color_continuous_scale='RdYlBu'
        )
        st.plotly_chart(fig, use_container_width=True)

    def _render_distance_chart(self, solution: Solution):
        """Render route distance chart."""
        data = []
        for route in solution.routes:
            data.append({
                'Route': f"Route {route.id}",
                'Distance': route.total_distance
            })
            
        fig = px.bar(
            data,
            x='Route',
            y='Distance',
            title='Route Distances (miles)',
            color='Distance',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig, use_container_width=True)

class ShipmentTable:
    """Interactive shipment data table."""
    def render(self, solution: Solution):
        """Render shipment details table."""
        if not solution:
            st.warning("No data to display")
            return

        # Prepare data
        data = []
        for route in solution.routes:
            for stop_type, shipment in route.stops:
                data.append({
                    'Route': route.id,
                    'Stop Type': stop_type.title(),
                    'Shipment ID': shipment.id,
                    'Origin': f"{shipment.origin.city}, {shipment.origin.state}",
                    'Destination': f"{shipment.destination.city}, {shipment.destination.state}",
                    'Pallets': shipment.pallet_count
                })

        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Add filters
        col1, col2 = st.columns(2)
        with col1:
            route_filter = st.multiselect(
                "Filter by Route",
                options=df['Route'].unique()
            )
        with col2:
            type_filter = st.multiselect(
                "Filter by Stop Type",
                options=df['Stop Type'].unique()
            )

        # Apply filters
        if route_filter:
            df = df[df['Route'].isin(route_filter)]
        if type_filter:
            df = df[df['Stop Type'].isin(type_filter)]

        # Display table
        st.dataframe(
            df,
            column_config={
                "Route": st.column_config.TextColumn(
                    "Route",
                    help="Route identifier"
                ),
                "Pallets": st.column_config.NumberColumn(
                    "Pallets",
                    help="Number of pallets",
                    format="%d"
                )
            }
        )
