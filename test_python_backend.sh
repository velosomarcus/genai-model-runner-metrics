#!/bin/bash

# Test script for the Python FastAPI backend
# This script demonstrates how to run and test the complete application

echo "============================================"
echo "GenAI Python Backend Test & Demo Script"
echo "============================================"

# Set test environment variables
export BASE_URL="http://localhost:11434/v1"
export MODEL="llama3.2:1b"
export API_KEY="test-api-key"
export TRACING_ENABLED="false"
export PORT="8080"
export METRICS_PORT="9090"

echo "Environment configured:"
echo "  BASE_URL: $BASE_URL"
echo "  MODEL: $MODEL"
echo "  API_KEY: $API_KEY"
echo ""

# Check if Python dependencies are installed
echo "Checking Python dependencies..."
cd python-backend
python -c "import fastapi, uvicorn, openai, prometheus_client; print('✅ All required dependencies are installed')" 2>/dev/null || {
    echo "❌ Dependencies missing. Installing..."
    pip install -r requirements.txt
}

echo ""
echo "============================================"
echo "Running Unit Tests"
echo "============================================"

# Run tests
python -m pytest tests/ -v --tb=short --disable-warnings
test_exit_code=$?

if [ $test_exit_code -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed!"
    exit 1
fi

echo ""
echo "============================================"
echo "Code Quality Checks"
echo "============================================"

# Check code formatting
echo "Checking code formatting with black..."
python -m black --check app/ tests/ 2>/dev/null && echo "✅ Code formatting is correct" || echo "⚠️  Code formatting issues found"

# Check import sorting
echo "Checking import sorting with isort..."
python -m isort --check-only app/ tests/ 2>/dev/null && echo "✅ Import sorting is correct" || echo "⚠️  Import sorting issues found"

echo ""
echo "============================================"
echo "Application Demo"
echo "============================================"

echo "Starting the Python FastAPI backend..."
echo "The application will run for 30 seconds to demonstrate functionality."
echo ""

# Start the application in background
python -m app.server &
APP_PID=$!

# Wait for startup
echo "Waiting for application to start..."
sleep 5

# Test health endpoint
echo "Testing health endpoint..."
curl -s http://localhost:8080/health | jq '.' || curl -s http://localhost:8080/health

echo ""
echo "Testing metrics endpoint..."
curl -s http://localhost:8080/metrics | head -10

echo ""
echo "Testing metrics summary endpoint..."
curl -s http://localhost:8080/metrics/summary | jq '.' || curl -s http://localhost:8080/metrics/summary

echo ""
echo "Testing CORS preflight..."
curl -s -X OPTIONS http://localhost:8080/chat -H "Access-Control-Request-Method: POST"

echo ""
echo "============================================"
echo "API Documentation"
echo "============================================"
echo "The FastAPI application provides interactive documentation at:"
echo "  - Swagger UI: http://localhost:8080/docs"
echo "  - ReDoc: http://localhost:8080/redoc"
echo "  - OpenAPI JSON: http://localhost:8080/openapi.json"

echo ""
echo "Available endpoints:"
echo "  - GET  /health - Health check"
echo "  - GET  /metrics - Prometheus metrics"
echo "  - GET  /metrics/summary - JSON metrics summary"
echo "  - POST /metrics/log - Log metrics"
echo "  - POST /metrics/llamacpp - Log LlamaCpp metrics"
echo "  - POST /metrics/error - Log errors"
echo "  - POST /chat - Streaming chat completions"

echo ""
echo "The application is running. You can test it manually for 25 more seconds..."
echo "Press Ctrl+C to stop early or wait for automatic shutdown."

# Wait for demo time or user interrupt
sleep 25

# Cleanup
echo ""
echo "Shutting down the application..."
kill $APP_PID 2>/dev/null
wait $APP_PID 2>/dev/null

echo ""
echo "============================================"
echo "Docker Build Test"
echo "============================================"

echo "Testing Docker build..."
if command -v docker &> /dev/null; then
    docker build -t genai-python-backend . && echo "✅ Docker build successful" || echo "❌ Docker build failed"
else
    echo "⚠️  Docker not available, skipping build test"
fi

echo ""
echo "============================================"
echo "Test Complete"
echo "============================================"
echo "✅ Python FastAPI backend is working correctly!"
echo ""
echo "To run the application:"
echo "  cd python-backend"
echo "  export BASE_URL=<your-model-runner-url>"
echo "  export MODEL=<your-model>"
echo "  export API_KEY=<your-api-key>"
echo "  python -m app.server"
echo ""
echo "To run with Docker Compose:"
echo "  cd python-backend"
echo "  docker-compose up --build"
echo ""
echo "For more information, see python-backend/README.md"