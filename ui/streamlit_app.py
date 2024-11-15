import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
import asyncio
import logging
import os
import base64
import psutil
from src.core.settings import Settings
from src.database.database import DatabaseConnection
from src.services.data_service import DataService
from src.services.geocoding_service import GeocodingService
from src.services.optimization_service import OptimizationService
from src.services.visualization_service import VisualizationService
from src.services.business_intelligence_service import BusinessIntelligenceService
from src.monitoring.monitoring import MonitoringSystem
from ui.components import RouteMap, ShipmentTable, MetricsPanel
from datetime import datetime, timedelta
import pandas as pd
from src.core.async_utils import AsyncLoopManager


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
                'data_service': DataService(settings, database),
                'geocoding_service': GeocodingService(settings, database),
                'optimization_service': OptimizationService(settings, database),
                'visualization_service': VisualizationService(settings, database),
                'monitoring': MonitoringSystem(settings),
                'bi_service': BusinessIntelligenceService(settings=settings, database=database)
            }

            # Initialize each service
            for name, service in services.items():
                if hasattr(service, 'initialize'):
                    await service.initialize()
                self.logger.info(f"{name} initialized successfully")

            return settings, database, services

        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}")
            raise

    def initialize_session_state(self):
        """Initialize the session state."""
        if 'initialized' not in st.session_state:
            try:
                self.logger.info("Initializing session state")

                # Run async initialization
                settings, database, services = asyncio.run(self.async_initialize())

                # Update session state
                st.session_state.update({
                    'settings': settings,
                    'database': database,
                    'data_service': services['data_service'],
                    'geocoding_service': services['geocoding_service'],
                    'optimization_service': services['optimization_service'],
                    'visualization_service': services['visualization_service'],
                    'monitoring': services['monitoring'],
                    'bi_service': services['bi_service'],
                    'initialized': True
                })

                self.logger.info("Session state initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize application: {str(e)}")
                raise

    async def cleanup(self):
        """Cleanup resources before exit."""
        if hasattr(st.session_state, 'database'):
            await st.session_state.database.cleanup()

    def run(self):
        """Run the Streamlit application."""
        try:
            self.initialize_session_state()
            
            if not st.session_state.get('initialized'):
                st.error("Application failed to initialize properly")
                return

            st.title("🚚 VRP Optimizer")
            st.markdown("""
            Optimize your vehicle routes with LIFO (Last-In-First-Out) constraints.
            Upload your shipment data and get optimized routes instantly.
            """)
            # Render sidebar
            self._render_sidebar()
            
            # Main content tabs
            tabs = st.tabs([
                "Upload & Optimize",
                "Route Visualization",
                "Analysis",
                "History",
                "Settings"
            ])
            
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
        with st.sidebar:
            st.header("⚙️ Controls")
            
            # Optimization Settings
            st.subheader("Optimization Settings")
            st.number_input(
                "Max Vehicles",
                min_value=1,
                max_value=st.session_state.settings.MAX_VEHICLES,
                value=5,
                key="max_vehicles"
            )
            
            st.number_input(
                "Max Pallets per Vehicle",
                min_value=1,
                max_value=26,  # Maximum pallets per vehicle
                value=20,
                key="max_pallets"
            )
            
            # Advanced Settings Expander
            with st.expander("Advanced Settings"):
                st.number_input(
                    "Computation Time Limit (seconds)",
                    min_value=10,
                    max_value=st.session_state.settings.MAX_COMPUTATION_TIME,
                    value=300,
                    key="computation_time"
                )
                
                max_distance = st.number_input(
                    "Maximum Route Distance (miles)",
                    min_value=100,
                    max_value=5000,  # Updated to 5,000 miles
                    value=st.session_state.settings.MAX_DISTANCE
                )
            
            # System Status
            st.subheader("System Status")
            if st.session_state.get('monitoring'):
                status = asyncio.run(st.session_state.monitoring.get_system_health())
                st.write(f"Status: {'🟢 Healthy' if status.get('healthy', False) else '🔴 Issues Detected'}")
                st.write(f"CPU Usage: {status.get('cpu_usage', 0)}%")
                st.write(f"Memory Usage: {status.get('memory_usage', 0)}%")
            else:
                st.warning("Monitoring not initialized")
            
            # Help & Documentation
            st.markdown("---")
            st.markdown("[📚 Documentation](https://github.com/your-org/vrp-optimizer)")
            st.markdown("[🐛 Report Issues](https://github.com/your-org/vrp-optimizer/issues)")

    def _render_upload_tab(self):
        """Render the data upload and optimization tab."""
        st.header("Upload Data & Optimize")
        
        # File uploader for shipment data
        uploaded_file = st.file_uploader(
            "Upload Shipment Data",
            type=['xlsx', 'xls', 'csv'],
            help="Upload an Excel or CSV file containing shipment data"
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
                                    solution = st.session_state.optimization_service.optimize(
                                        st.session_state.current_shipments
                                    )
                                    st.session_state.current_solution = solution
                        
                        # Display solution if available
                        if hasattr(st.session_state, 'current_solution'):
                            self._display_solution_summary(st.session_state.current_solution)
                            
                            # Export buttons
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Export to Excel"):
                                    self._export_solution(
                                        st.session_state.current_solution,
                                        format='excel'
                                    )
                            with col2:
                                if st.button("Export to CSV"):
                                    self._export_solution(
                                        st.session_state.current_solution,
                                        format='csv'
                                    )

            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                self.logger.error(f"File processing error: {str(e)}", exc_info=True)

    def _render_visualization_tab(self):
        """Render the route visualization tab."""
        st.header("Route Visualization")

        # Check if there's a current solution to visualize
        if not hasattr(st.session_state, 'current_solution'):
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
                format_func=lambda x: f"Route {x + 1}"
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
                route_coords = st.session_state.visualization_service.get_route_coordinates(route)
                
                # Create and display map
                self.route_map.plot_route(
                    route_coords,
                    show_markers=show_markers,
                    show_routes=show_routes,
                    route_color=st.session_state.visualization_service.get_route_color(selected_route)
                )
                
                # Display shipment sequence
                st.subheader("Delivery Sequence")
                sequence_df = pd.DataFrame([
                    {
                        "Stop": i + 1,
                        "Location": f"{stop.city}, {stop.state}",
                        "Arrival Time": stop.arrival_time.strftime("%H:%M"),
                        "Pallets": stop.load_change
                    }
                    for i, stop in enumerate(route.stops)
                ])
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
        """Render the analytics and reporting tab."""
        st.header("Analytics & Insights")

        try:
            # Get metrics from BI service using AsyncLoopManager
            with st.spinner("Loading analytics..."):
                metrics = AsyncLoopManager.run_async(
                    st.session_state.bi_service.get_optimization_metrics()
                )
                historical_data = AsyncLoopManager.run_async(
                    st.session_state.bi_service.get_historical_metrics()
                )

            # Display high-level metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Total Optimizations",
                    metrics["total_optimizations"],
                    help="Total number of route optimizations performed"
                )
            with col2:
                st.metric(
                    "Avg Distance (miles)",
                    f"{metrics['average_distance']:.1f}",
                    help="Average route distance across all optimizations"
                )
            with col3:
                st.metric(
                    "Avg Cost ($)",
                    f"{metrics['average_cost']:.2f}",
                    help="Average cost per route"
                )
            with col4:
                st.metric(
                    "Avg Vehicles Used",
                    f"{metrics['average_vehicles']:.1f}",
                    help="Average number of vehicles required"
                )

            # Performance trends
            st.subheader("Performance Trends")
            if historical_data is not None:
                # Create trend charts
                fig = self.metrics_panel.create_trend_charts(historical_data)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No historical data available for trend analysis.")

            # Resource utilization
            st.subheader("Resource Utilization")
            
            # Get current system metrics
            system_metrics = AsyncLoopManager.run_async(
                st.session_state.monitoring.get_system_health()
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "CPU Usage",
                    f"{system_metrics.get('cpu_usage', 0):.1f}%"
                )
            with col2:
                st.metric(
                    "Memory Usage",
                    f"{system_metrics.get('memory_usage', 0)::.1f}%"
                )

            # Export options
            st.subheader("Export Analytics")
            if st.button("Export Analytics"):
                try:
                    export_data = {
                        "metrics": metrics,
                        "historical_data": historical_data,
                        "system_metrics": system_metrics
                    }
                    # Use DataService to handle the export
                    success = AsyncLoopManager.run_async(
                        st.session_state.data_service.export_analytics(export_data)
                    )
                    if success:
                        st.success("Analytics exported successfully!")
                    else:
                        st.error("Failed to export analytics.")
                except Exception as e:
                    st.error(f"Error exporting analytics: {str(e)}")

        except Exception as e:
            st.error(f"Error loading analytics: {str(e)}")
            self.logger.error(
                f"Error in analysis tab: {str(e)}",
                exc_info=True
            )

    def _render_history_tab(self):
        """Render the optimization history tab."""
        st.header("Optimization History")
        
        try:
            # Get recent optimizations from database
            with st.spinner("Loading optimization history..."):
                history = asyncio.run(
                    st.session_state.database.get_recent_solutions(limit=10)
                )
            
            if not history:
                st.info("No optimization history available.")
                return

            # Display history in a table
            history_df = pd.DataFrame([
                {
                    "Date": h["created_at"].strftime("%Y-%m-%d %H:%M"),
                    "Routes": len(h["solution"]["routes"]),
                    "Total Distance": f"{h['solution']['total_distance']:.1f} miles",
                    "Total Cost": f"${h['solution']['total_cost']:.2f}",
                    "Status": "✅ Success" if h["solution"].get("success", False) else "❌ Failed"
                }
                for h in history
            ])
            
            st.dataframe(history_df, use_container_width=True)

            # Allow viewing detailed solution
            if st.button("View Selected Solution Details"):
                if "selected_solution" in st.session_state:
                    self._display_solution_summary(st.session_state.selected_solution)
                else:
                    st.warning("Please select a solution to view details")

        except Exception as e:
            st.error(f"Error loading history: {str(e)}")
            self.logger.error(f"History tab error: {str(e)}", exc_info=True)

    def _render_settings_tab(self):
        """Render the application settings tab."""
        st.header("Application Settings")
        
        # Display current settings
        st.subheader("Current Configuration")
        st.json({
            "App Name": st.session_state.settings.APP_NAME,
            "Environment": st.session_state.settings.ENVIRONMENT,
            "Debug Mode": st.session_state.settings.DEBUG,
            "Max Vehicles": st.session_state.settings.MAX_VEHICLES,
            "Max Distance": st.session_state.settings.MAX_DISTANCE,
            "Max Computation Time": st.session_state.settings.MAX_COMPUTATION_TIME,
            "Geocoding Provider": st.session_state.settings.GEOCODING_API_KEY or "Not Set"
        })

        # Allow updates to settings
        st.subheader("Update Settings")
        new_max_vehicles = st.number_input(
            "Max Vehicles",
            min_value=1,
            max_value=100,
            value=st.session_state.settings.MAX_VEHICLES
        )
        new_max_distance = st.number_input(
            "Max Distance (miles)",
            min_value=100,
            max_value=5000,
            value=st.session_state.settings.MAX_DISTANCE
        )
        
        if st.button("Update Settings"):
            st.session_state.settings.MAX_VEHICLES = new_max_vehicles
            st.session_state.settings.MAX_DISTANCE = new_max_distance
            st.success("Settings updated successfully!")

def main():
    """Initialize and run the Streamlit application."""
    app = VRPOptimizerApp()
    app.run()
if __name__ == "__main__":
    main()

