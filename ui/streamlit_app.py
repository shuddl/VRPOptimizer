# ui/streamlit_app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import io
import asyncio
from typing import Optional, Dict, List
import base64
import time
import sys
from pathlib import Path
import sys
import os

print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Environment variables: {os.environ}")
# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import our services and models
from src.core.config import Settings
from src.database import Database
from src.services import (
    DataService,
    GeocodingService,
    OptimizationService,
    VisualizationService
)
from src.monitoring import MonitoringSystem
from src.core.exceptions import VRPOptimizerError
from ui.components import RouteMap, MetricsPanel, ShipmentTable

async def initialize_services():
    """Initialize all required services with database connection."""
    try:
        # Initialize settings
        settings = Settings()
        
        # Initialize database
        database = Database(settings)
        await database.initialize()
        
        # Initialize services
        data_service = DataService(settings, database)
        geocoding_service = GeocodingService(settings, database)
        optimization_service = OptimizationService(settings, database)
        visualization_service = VisualizationService(settings)
        monitoring = MonitoringSystem(settings)
        
        return (
            settings,
            database,
            data_service,
            geocoding_service,
            optimization_service,
            visualization_service,
            monitoring
        )
    except Exception as e:
        st.error(f"Failed to initialize services: {str(e)}")
        raise

class VRPOptimizerUI:
    """Streamlit web interface for VRP Optimizer."""
    
    def __init__(self):
        """Initialize the UI and components."""
        self.route_map = RouteMap()
        self.metrics_panel = MetricsPanel()
        self.shipment_table = ShipmentTable()
        
    def initialize_session_state(self):
        """Initialize or get session state variables."""
        if 'initialized' not in st.session_state:
            services = asyncio.run(initialize_services())
            
            st.session_state.settings = services[0]
            st.session_state.database = services[1]
            st.session_state.data_service = services[2]
            st.session_state.geocoding_service = services[3]
            st.session_state.optimization_service = services[4]
            st.session_state.visualization_service = services[5]
            st.session_state.monitoring = services[6]
            
            # Initialize solution states
            st.session_state.current_solution = None
            st.session_state.optimization_history = []
            
            st.session_state.initialized = True

    def run(self):
        """Run the Streamlit application."""
        try:
            self._setup_page()
            self.initialize_session_state()
            
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
            if st.session_state.get('monitoring'):
                asyncio.run(
                    st.session_state.monitoring.log_error(e)
                )

    def _setup_page(self):
        """Configure page settings."""
        st.set_page_config(
            page_title="VRP Optimizer",
            page_icon="🚚",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.title("🚚 VRP Optimizer")
        st.markdown("""
        Optimize your vehicle routes with LIFO (Last-In-First-Out) constraints.
        Upload your shipment data and get optimized routes instantly.
        """)

    def _render_sidebar(self):
        """Render sidebar with controls and metrics."""
        st.sidebar.header("Configuration")
        
        # Optimization parameters
        st.sidebar.subheader("Parameters")
        max_vehicles = st.sidebar.number_input(
            "Maximum Vehicles",
            min_value=1,
            max_value=20,
            value=st.session_state.settings.MAX_VEHICLES
        )
        
        max_distance = st.sidebar.number_input(
            "Maximum Route Distance (miles)",
            min_value=100,
            max_value=1000,
            value=st.session_state.settings.MAX_DISTANCE
        )
        
        # System metrics
        st.sidebar.subheader("System Metrics")
        metrics = asyncio.run(
            st.session_state.monitoring.get_system_health()
        )
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric(
                "Active Optimizations",
                metrics.get('active_optimizations', 0)
            )
        with col2:
            st.metric(
                "Total Optimizations",
                metrics.get('total_optimizations', 0)
            )
        
        # Memory usage
        memory_usage = metrics.get('memory_percent', 0)
        st.sidebar.progress(
            memory_usage / 100,
            f"Memory Usage: {memory_usage:.1f}%"
        )

    async def _process_file(self, file) -> bool:
        """Process uploaded file with error handling."""
        try:
            # Start monitoring
            await st.session_state.monitoring.log_optimization_start(0)
            start_time = time.time()
            
            # Read file
            content = await file.read()
            
            # Process data
            shipments = await st.session_state.data_service.process_excel(content)
            if not shipments:
                st.error("No valid shipments found in file")
                return False
            
            # Update monitoring count
            await st.session_state.monitoring.log_optimization_start(
                len(shipments)
            )
            
            # Geocode locations
            shipments = await st.session_state.geocoding_service.geocode_shipments(
                shipments
            )
            
            # Optimize routes
            solution = await st.session_state.optimization_service.optimize(
                shipments
            )
            
            if solution:
                # Store solution
                st.session_state.current_solution = solution
                st.session_state.optimization_history.append({
                    'timestamp': datetime.now(),
                    'solution': solution
                })
                
                # Cache solution in database
                await st.session_state.database.save_solution(
                    solution.to_dict(),
                    {'processing_time': time.time() - start_time}
                )
                
                # Log success
                await st.session_state.monitoring.log_optimization_end(
                    time.time() - start_time,
                    True
                )
                
                return True
            else:
                st.error("No feasible solution found")
                await st.session_state.monitoring.log_optimization_end(
                    time.time() - start_time,
                    False,
                    "No feasible solution"
                )
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            await st.session_state.monitoring.log_optimization_end(
                duration,
                False,
                str(e)
            )
            raise

    def _render_upload_tab(self):
        """Render the data upload and optimization tab."""
        st.header("Upload Data & Optimize")
        
        uploaded_file = st.file_uploader(
            "Upload Shipment Data (Excel)",
            type=['xlsx', 'xls'],
            help="Upload an Excel file containing shipment data"
        )
        
        if uploaded_file:
            try:
                with st.spinner("Processing file..."):
                    success = asyncio.run(self._process_file(uploaded_file))
                    
                if success:
                    st.success("Routes optimized successfully!")
                    self._display_solution_summary(
                        st.session_state.current_solution
                    )
                    
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")

    def _render_visualization_tab(self):
        """Render the visualization tab."""
        if not st.session_state.current_solution:
            st.info("Please optimize routes first")
            return
            
        self.route_map.render(st.session_state.current_solution)
        self.metrics_panel.render(st.session_state.current_solution)

    def _render_analysis_tab(self):
        """Render the analysis tab."""
        if not st.session_state.current_solution:
            st.info("Please optimize routes first")
            return
            
        solution = st.session_state.current_solution
        
        # Summary metrics
        self.metrics_panel.render(solution)
        
        # Route details
        st.subheader("Route Details")
        self.shipment_table.render(solution)

    def _render_history_tab(self):
        """Render the optimization history tab."""
        st.header("Optimization History")
        
        # Get recent solutions from database
        solutions = asyncio.run(
            st.session_state.database.get_recent_solutions()
        )
        
        if not solutions:
            st.info("No optimization history available")
            return
            
        for solution in solutions:
            with st.expander(
                f"Solution from {solution['created_at']}"
            ):
                self._display_solution_summary(solution['solution'])
                if solution['metrics']:
                    st.metric(
                        "Processing Time",
                        f"{solution['metrics']['processing_time']:.2f}s"
                    )

    def _render_settings_tab(self):
        """Render the settings tab."""
        st.header("Settings")
        
        # General settings
        st.subheader("General Settings")
        max_vehicles = st.number_input(
            "Maximum Vehicles",
            min_value=1,
            max_value=20,
            value=st.session_state.settings.MAX_VEHICLES
        )
        
        max_pallets = st.number_input(
            "Maximum Pallets per Vehicle",
            min_value=1,
            max_value=50,
            value=st.session_state.settings.MAX_PALLETS
        )
        
        # Export settings
        st.subheader("Export Settings")
        if st.button("Export Current Solution"):
            if st.session_state.current_solution:
                self._export_solution(st.session_state.current_solution)
            else:
                st.warning("No solution to export")

    def _display_solution_summary(self, solution):
        """Display a summary of the optimization solution."""
        self.metrics_panel.render(solution)
        self.shipment_table.render(solution)

    async def _export_solution(self, solution):
        """Export the solution to Excel with error handling."""
        try:
            excel_data = await st.session_state.data_service.export_solution(
                solution,
                'excel'
            )
            
            if excel_data:
                b64 = base64.b64encode(excel_data).decode()
                href = f'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}'
                st.markdown(
                    f'<a href="{href}" download="route_solution.xlsx">'
                    f'Download Solution (Excel)</a>',
                    unsafe_allow_html=True
                )
            else:
                st.error("Failed to export solution")
                
        except Exception as e:
            st.error(f"Error exporting solution: {str(e)}")
            await st.session_state.monitoring.log_error(e)

def main():
    app = VRPOptimizerUI()
    app.run()

if __name__ == "__main__":
    main()