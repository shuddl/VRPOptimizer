docs/setup.md
VRP Optimizer Setup Guide
Prerequisites
System Requirements

Python 3.10 or higher
4GB RAM minimum (8GB recommended)
10GB free disk space
Internet connection for geocoding

Optional Requirements

PostgreSQL 12+ (for production)
Redis (for caching)
Docker and Docker Compose (for containerization)

Installation
1. Basic Setup
bashCopy# Clone repository
git clone https://github.com/your-repo/vrp-optimizer.git
cd vrp-optimizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
2. Configuration
bashCopy# Copy example configuration
cp .env.example .env

# Edit .env file with your settings
nano .env
Required environment variables:
envCopyENV=development
DEBUG=true
SECRET_KEY=your_secret_key
GEOCODING_API_KEY=your_api_key
3. Database Setup
bashCopy# For SQLite (default)
# No additional setup required

# For PostgreSQL
createdb vrp_optimizer
python manage.py migrate
4. Start Services
Development
bashCopy# Start API server
./scripts/start_api.sh

# Start UI server (in new terminal)
./scripts/start_ui.sh
Production
bashCopy# Using Docker
docker-compose up -d
Testing
bashCopy# Run all tests
./scripts/run_tests.sh

# Run specific tests
pytest tests/test_services/test_optimization.py
Upgrading
bashCopy# Pull latest changes
git pull

# Update dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate
