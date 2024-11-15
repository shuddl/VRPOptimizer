README.md
VRP Optimizer
An enterprise-grade Vehicle Route Planning system with LIFO constraints optimization.
Features

🚛 Route optimization with LIFO (Last-In-First-Out) constraints
📦 Support for up to 26 pallets per vehicle
🗺️ Interactive route visualization
📊 Real-time performance analytics
🔄 API and web interface access
📈 System monitoring and logging

Quick Start
bashCopy# Clone repository
git clone https://github.com/your-org/vrp-optimizer.git
cd vrp-optimizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt




# Start the application
./scripts/start_api.sh  # Start API server
./scripts/start_ui.sh   # Start UI server (new terminal)
System Requirements

Python 3.11.5
4GB RAM (8GB recommended)
Internet connection for geocoding

Documentation

API Documentation
Setup Guide
User Guide

Development
bashCopy# Install development dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run tests
./scripts/run_tests.sh

# Format code
black src/ tests/

# Type checking
mypy src/
Project Structure
Copyvrp_optimizer/
├── src/           # Main source code
├── tests/         # Test suite
├── ui/            # User interface
├── scripts/       # Utility scripts
└── docs/          # Documentation
Configuration
Configuration is managed through:

Environment variables
.env file
config/settings.yml

License
MIT License - see LICENSE file for details.
Contributing

Fork the repository
Create a feature branch
Make your changes
Run tests
Submit a pull request

Support
For support:

Check documentation
Open an issue
Contact support team

Acknowledgments

OR-Tools by Google
FastAPI framework
Streamlit team