# scripts/setup.sh
#!/bin/bash

# Setup script for VRP Optimizer
set -e  # Exit on any error

echo "🚀 Setting up VRP Optimizer..."

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$python_version < 3.10" | bc -l) )); then
    echo "❌ Error: Python 3.10 or higher is required"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "🔄 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Install development dependencies if in dev mode
if [ "$1" == "--dev" ]; then
    echo "🛠️ Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p data/cache data/uploads logs config

# Copy example configuration
echo "⚙️ Setting up configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from template"
fi

# Setup pre-commit hooks if in dev mode
if [ "$1" == "--dev" ]; then
    echo "🔧 Setting up pre-commit hooks..."
    pre-commit install
fi

echo "✅ Setup complete!"
echo "To activate the environment: source venv/bin/activate"
