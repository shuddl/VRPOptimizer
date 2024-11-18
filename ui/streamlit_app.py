import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

import streamlit as st
import asyncio
import logging
import base64
import pandas as pd
from src.core.settings import Settings
from src.database.database import DatabaseConnection
from src.services.data_service import DataService
from src.services.geocoding_service import GeocodingService
from src.services.optimization_service import OptimizationService
from src.services.visualization_service import VisualizationService
from src.services.business_intelligence_service import BusinessIntelligenceService
from src.monitoring.monitoring import MonitoringSystem
from ui.components import RouteMap, ShipmentTable, MetricsPanel, Sidebar
from datetime import datetime, timedelta
from src.core.async_utils import AsyncLoopManager
import tracemalloc

tracemalloc.start()


class VRPOptimizerApp:
    def __init__(self):
        """Initialize the application."""
        self.logger = logging.getLogger(__name__)
        self.route_map = RouteMap()
        self.metrics_panel = MetricsPanel()
        self.shipment_table = ShipmentTable()
        self.page_size = 10

    async def async_initialize(self):
        """Asynchronously initialize the application."""
        try:
            # Initialize settings
            settings = Settings()
            settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            self.logger.info("Settings loaded successfully")

            # Initialize database
            database = await DatabaseConnection.get_instance(settings)
            self.logger.info("Database initialized successfully")

            # Initialize services
            services = {
                "data_service": DataService(settings, database),
                "geocoding_service": GeocodingService(settings, database),
                "optimization_service": OptimizationService(settings, database),
                "visualization_service": VisualizationService(settings, database),
                "monitoring": MonitoringSystem(settings),
                "bi_service": BusinessIntelligenceService(
                    settings=settings, database=database
                ),
            }

            # Initialize each service
            for name, service in services.items():
                if hasattr(service, "initialize"):
                    await service.initialize()
                self.logger.info(f"{name} initialized successfully")

            return settings, database, services

        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}")
            raise

    def initialize_session_state(self):
        """Initialize the session state."""
        if "initialized" not in st.session_state:
            try:
                self.logger.info("Initializing session state")

                # Run async initialization synchronously
                settings, database, services = asyncio.run(self.async_initialize())

                # Update session state
                st.session_state.update(
                    {
                        "settings": settings,
                        "database": database,
                        "data_service": services["data_service"],
                        "geocoding_service": services["geocoding_service"],
                        "optimization_service": services["optimization_service"],
                        "visualization_service": services["visualization_service"],
                        "monitoring": services["monitoring"],
                        "bi_service": services["bi_service"],
                        "initialized": True,
                        # ...other session state variables...
                    }
                )

                self.logger.info("Session state initialized successfully")
                return True
            except Exception as e:
                self.logger.error(f"Failed to initialize application: {str(e)}")
                st.error(f"Failed to initialize application: {str(e)}")
                return False
        return True

    async def cleanup(self):
        """Cleanup resources before exit."""
        if hasattr(st.session_state, "database"):
            await st.session_state.database.cleanup()

    def run(self):
        """Run the Streamlit application."""
        try:
            if not self.initialize_session_state():
                return

            st.title("🚚 VRP Optimizer")
            st.markdown(
                """
            Optimize your vehicle routes with LIFO (Last-In-First-Out) constraints.
            Upload your shipment data and get optimized routes instantly.
            """
            )
            # Render sidebar
            self._render_sidebar()

            # Main content tabs
            tabs = st.tabs(
                [
                    "Upload & Optimize",
                    "Route Visualization",
                    "Analysis",
                    "History",
                    "Settings",
                ]
            )

            with tabs[0]:
                self._render_upload_tab()
            with tabs[1]:
                self._render_visualization_tab()
            with tabs[2]:
                self._render_analysis_tab()
            with tabs[3]:
                self._render_history_tab()
            with tabs[4]:
                self._render_settings_tab()

        except Exception as e:
            st.error(f"Application error: {str(e)}")
            self.logger.error(f"Application error: {str(e)}", exc_info=True)

    def _render_sidebar(self):
        """Render the application sidebar."""
        Sidebar.render(st.session_state.get("monitoring"))

    def _render_upload_tab(self):
        """Render the data upload and optimization tab."""
        st.header("Upload Data & Optimize")

        # Provide download link for local template
        def get_table_download_link():
            """Generates a link to download the sample Excel template."""
            with open("templates/shipment_template.xlsx", "rb") as f:
                bytes_data = f.read()
            b64 = base64.b64encode(bytes_data).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="shipment_template.xlsx">Download Sample Excel Template</a>'
            return href

        st.markdown(
            f"""
        **Need a template?** {get_table_download_link()}
        
        **Required Columns:**
        - **Shipment ID**: Unique identifier for each shipment.
        - **Origin ZIP Code**: ZIP code of the shipment origin.
        - **Destination ZIP Code**: ZIP code of the shipment destination.
        - **Pallets**: Number of pallets for the shipment.
        - **Delivery Window Start**: Earliest delivery time (optional).
        - **Delivery Window End**: Latest delivery time (optional).
        """,
            unsafe_allow_html=True,
        )

        # File uploader for shipment data
        uploaded_file = st.file_uploader(
            "Upload Shipment Data",
            type=["xlsx", "xls", "csv"],
            help="Upload an Excel or CSV file containing shipment data",
        )

        # Upload settings in columns
        col1, col2 = st.columns(2)
        with col1:
            validate_data = st.checkbox("Validate Data", value=True)
        with col2:
            auto_optimize = st.checkbox("Auto-Optimize", value=True)

        # Process uploaded file
        if uploaded_file is not None:
            try:
                with st.spinner("Processing file..."):
                    # Process the file using the data service
                    success = AsyncLoopManager.run_async(
                        self._process_file(uploaded_file)
                    )

                    if success:
                        st.success("File processed successfully!")

                        # Show optimization button if not auto-optimizing
                        if not auto_optimize:
                            if st.button("Optimize Routes"):
                                with st.spinner("Optimizing routes..."):
                                    solution = (
                                        st.session_state.optimization_service.optimize(
                                            st.session_state.current_shipments
                                        )
                                    )
                                    st.session_state.current_solution = solution

                        # Display solution if available
                        if hasattr(st.session_state, "current_solution"):
                            self._display_solution_summary(
                                st.session_state.current_solution
                            )

                            # Export buttons
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Export to Excel"):
                                    self._export_solution(
                                        st.session_state.current_solution,
                                        format="excel",
                                    )
                            with col2:
                                if st.button("Export to CSV"):
                                    self._export_solution(
                                        st.session_state.current_solution, format="csv"
                                    )

            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                self.logger.error(f"File processing error: {str(e)}", exc_info=True)

    def _render_visualization_tab(self):
        """Render the route visualization tab."""
        st.header("Route Visualization")

        # Check if there's a current solution to visualize
        if not hasattr(st.session_state, "current_solution"):
            st.info("No routes to visualize. Please optimize routes first.")
            return

        # Get the current solution
        solution = st.session_state.current_solution

        # Visualization options
        col1, col2 = st.columns(2)
        with col1:
            show_markers = st.checkbox("Show Location Markers", value=True)
        with col2:
            show_routes = st.checkbox("Show Route Lines", value=True)

        # Route selection
        if solution.routes:
            selected_route = st.selectbox(
                "Select Route to Visualize",
                options=range(len(solution.routes)),
                format_func=lambda x: f"Route {x + 1}",
            )

            # Get selected route
            route = solution.routes[selected_route]

            # Display route details
            st.subheader(f"Route {selected_route + 1} Details")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Distance", f"{route.total_distance:.1f} miles")
            with col2:
                st.metric("Total Time", f"{route.total_time:.1f} hours")
            with col3:
                st.metric("Load", f"{route.current_load}/{route.capacity} pallets")

            # Display route map
            try:
                # Get route coordinates from visualization service
                route_coords = (
                    st.session_state.visualization_service.get_route_coordinates(route)
                )

                # Create and display map
                self.route_map.plot_route(
                    route_coords,
                    show_markers=show_markers,
                    show_routes=show_routes,
                    route_color=st.session_state.visualization_service.get_route_color(
                        selected_route
                    ),
                )

                # Display shipment sequence
                st.subheader("Delivery Sequence")
                sequence_df = pd.DataFrame(
                    [
                        {
                            "Stop": i + 1,
                            "Location": f"{stop.city}, {stop.state}",
                            "Arrival Time": stop.arrival_time.strftime("%H:%M"),
                            "Pallets": stop.load_change,
                        }
                        for i, stop in enumerate(route.stops)
                    ]
                )
                st.dataframe(sequence_df, use_container_width=True)

            except Exception as e:
                st.error(f"Error visualizing route: {str(e)}")
                self.logger.error(f"Visualization error: {str(e)}", exc_info=True)
        else:
            st.info("No routes available in the current solution.")

        # Advanced visualization options
        with st.expander("Advanced Visualization Options"):
            st.color_picker("Route Color", value="#FF4B4B")
            st.slider("Line Thickness", min_value=1, max_value=10, value=3)
            st.checkbox("Show Time Windows", value=False)
            st.checkbox("Show Load Changes", value=False)

    def _render_analysis_tab(self):
        """Render the analytics dashboard."""
        st.header("Analytics Dashboard")

        try:
            # Check if we have any data to analyze
            with st.spinner("Loading analytics data..."):
                metrics = AsyncLoopManager.run_async(
                    st.session_state.bi_service.get_optimization_metrics()
                )

                if metrics.get("total_optimizations", 0) == 0:
                    st.info(
                        "No optimization data available for analysis. Please run some optimizations first."
                    )
                    return

                # Display summary metrics in columns
                st.metric("Avg Vehicles", f"{metrics['average_vehicles']:.1f}")

            # Get historical data
            historical = AsyncLoopManager.run_async(
                st.session_state.bi_service.get_historical_metrics()
            )

            if not historical:
                st.info("No historical data available.")
                return

            st.subheader("Historical Trends")
            # ...existing code to create and display charts...

        except Exception as e:
            st.error(f"Error loading analytics: {str(e)}")
            self.logger.error(f"Analytics error: {str(e)}", exc_info=True)

    def _render_history_tab(self):
        """Render the optimization history tab."""
        # ...existing code...

    def _render_settings_tab(self):
        """Render the application settings tab."""
        st.header("Application Settings")

        # Display current settings
        st.subheader("Current Configuration")
        st.json(
            {
                "App Name": st.session_state.settings.APP_NAME,
                "Environment": st.session_state.settings.ENVIRONMENT,
                "Debug Mode": st.session_state.settings.DEBUG,
                "Max Vehicles": st.session_state.settings.MAX_VEHICLES,
                "Max Distance": st.session_state.settings.MAX_DISTANCE,
                "Max Computation Time": st.session_state.settings.MAX_COMPUTATION_TIME,
                "Geocoding Provider": st.session_state.settings.GEOCODING_API_KEY
                or "Not Set",
            }
        )

        # Allow updates to settings
        st.subheader("Update Settings")
        new_max_vehicles = st.number_input(
            "Max Vehicles",
            min_value=1,
            max_value=100,
            value=st.session_state.settings.MAX_VEHICLES,
        )
        new_max_distance = st.number_input(
            "Max Distance (miles)",
            min_value=100,
            max_value=5000,
            value=st.session_state.settings.MAX_DISTANCE,
        )

        if st.button("Update Settings"):
            try:
                st.session_state.settings.MAX_VEHICLES = new_max_vehicles
                st.session_state.settings.MAX_DISTANCE = new_max_distance
                st.success("Settings updated successfully!")
            except Exception as e:
                st.error(f"Error updating settings: {str(e)}")
                self.logger.error(f"Settings update error: {str(e)}", exc_info=True)

    async def _process_file(self, uploaded_file):
        """Process the uploaded file."""
        # Implement the method to process the uploaded file
        pass

    def _export_solution(self, solution, format):
        """Export the solution in the specified format."""
        # Implement the method to export the solution
        pass

    def _display_solution_summary(self, solution):
        """Display a summary of the optimization solution."""
        # Implement the method to display the solution summary
        pass


def main():
    """Initialize and run the Streamlit application."""
    app = VRPOptimizerApp()
    app.run()


if __name__ == "__main__":
    main()
