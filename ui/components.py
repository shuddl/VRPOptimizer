# ui/components.py

import streamlit as st
import folium
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Optional, Any
import pandas as pd
from src.core.models import Solution, Route, Shipment
import asyncio
import threading


class RouteMap:
    def __init__(self):
        pass  # Add your implementation here


class MetricsPanel:
    def __init__(self):
        pass  # Add your implementation here

    def create_trend_charts(self, historical_data: Dict[str, List[Any]]) -> go.Figure:
        """Create trend charts for performance metrics."""
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Total Runs",
                "Average Distance",
                "Average Cost",
                "Average Vehicles",
            ),
        )

        # Add total runs trend
        fig.add_trace(
            go.Scatter(
                x=historical_data["dates"],
                y=historical_data["total_runs"],
                mode="lines+markers",
                name="Total Runs",
            ),
            row=1,
            col=1,
        )

        # Add average distance trend
        fig.add_trace(
            go.Scatter(
                x=historical_data["dates"],
                y=historical_data["avg_distance"],
                mode="lines+markers",
                name="Avg Distance",
            ),
            row=1,
            col=2,
        )

        # Add average cost trend
        fig.add_trace(
            go.Scatter(
                x=historical_data["dates"],
                y=historical_data["avg_cost"],
                mode="lines+markers",
                name="Avg Cost",
            ),
            row=2,
            col=1,
        )

        # Add average vehicles trend
        fig.add_trace(
            go.Scatter(
                x=historical_data["dates"],
                y=historical_data["avg_vehicles"],
                mode="lines+markers",
                name="Avg Vehicles",
            ),
            row=2,
            col=2,
        )

        fig.update_layout(
            height=800, showlegend=False, title_text="Performance Trends Over Time"
        )

        return fig


class ShipmentTable:
    def __init__(self):
        pass  # Add your implementation here


class OptimizationControls:
    def __init__(self):
        pass  # Add your implementation here


class SystemStatus:
    @staticmethod
    async def get_status(monitoring) -> Dict[str, Any]:
        """Get system health status."""
        try:
            metrics = await monitoring.get_system_health()
            healthy = (
                metrics.get("memory_percent", 100) < 90
                and metrics.get("cpu_percent", 100) < 80
            )
            return {"healthy": healthy, "metrics": metrics}
        except Exception as e:
            return {"healthy": False, "error": str(e)}


class Sidebar:
    @staticmethod
    def fetch_and_display_status(
        status_placeholder: st.delta_generator.DeltaGenerator, monitoring
    ):
        """Fetch and display system status synchronously."""
        try:
            # Fetch status using asyncio event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            status = loop.run_until_complete(SystemStatus.get_status(monitoring))
            loop.close()

            # Update the sidebar with fetched status
            status_text = (
                "🟢 Healthy" if status.get("healthy", False) else "🔴 Issues Detected"
            )
            status_placeholder.write(f"Status: {status_text}")

            if "metrics" in status:
                metrics = status["metrics"]
                st.metric("Memory Usage", f"{metrics.get('memory_percent', 0)}%")
                st.metric("CPU Usage", f"{metrics.get('cpu_percent', 0)}%")
                st.metric(
                    "Active Optimizations", metrics.get("active_optimizations", 0)
                )
                st.metric("Total Optimizations", metrics.get("total_optimizations", 0))

            if "error" in status:
                st.error(f"Error: {status['error']}")

        except Exception as e:
            st.error(f"Error fetching system status: {str(e)}")

    @staticmethod
    def render(monitoring):
        """Render the sidebar with system status."""
        with st.sidebar:
            st.header("System Status")

            # Initialize a placeholder for system status
            status_placeholder = st.empty()

            if monitoring:
                Sidebar.fetch_and_display_status(status_placeholder, monitoring)
            else:
                status_placeholder.error("Monitoring system not initialized")


class HistoryPanel:
    @staticmethod
    def render_empty_state():
        """Render empty state message."""
        st.info(
            """
        No optimization history available yet.

        To get started:
        1. Upload your shipment data in the 'Upload & Optimize' tab.
        2. Run an optimization.
        3. Your results will appear here automatically.
        """
        )

    @staticmethod
    def render_history_table(history_df):
        """Render the optimization history table."""
        st.dataframe(
            history_df,
            use_container_width=True,
            column_config={
                "Date": st.column_config.DatetimeColumn(
                    "Date", format="YYYY-MM-DD HH:mm"
                ),
                "Routes": st.column_config.NumberColumn(
                    "Routes", help="Number of routes in the solution"
                ),
                "Total Distance": st.column_config.TextColumn(
                    "Total Distance", help="Total distance across all routes"
                ),
                "Total Cost": st.column_config.TextColumn(
                    "Total Cost", help="Total cost of all routes"
                ),
                "Status": st.column_config.TextColumn(
                    "Status", help="Optimization status"
                ),
            },
        )
