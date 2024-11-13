# scripts/run_tests.sh
#!/bin/bash

# Test runner script
set -e

# Activate virtual environment
source venv/bin/activate

# Set environment to test
export ENVIRONMENT=test

echo "🧪 Running tests..."

# Run pre-test cleanup
echo "🧹 Cleaning up test cache..."
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Run tests with coverage
echo "🔍 Running tests with coverage..."
python -m pytest \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html:coverage_report \
    tests/ \
    -v

# Run type checking
echo "📝 Running type checking..."
mypy src/

# Run linting
echo "🔍 Running linting..."
flake8 src/ tests/

# Check for security issues
echo "🔒 Running security checks..."
bandit -r src/

echo "✅ All tests completed!"
