# GenAI Model Runner Metrics API - Python FastAPI Port

This is a complete Python FastAPI port of the Go GenAI Model Runner Metrics API, providing the same functionality with async support and comprehensive observability features.

## Features

- **Async FastAPI** application with streaming chat support
- **OpenAI API compatibility** for chat completions
- **Prometheus metrics** collection and exposition
- **OpenTelemetry tracing** with OTLP export
- **CORS support** for web frontend integration
- **Comprehensive error handling** and logging
- **Health checks** with model information
- **LlamaCpp specific metrics** for llama.cpp models
- **Token counting and latency tracking**
- **Graceful shutdown** handling

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (optional)

### Installation

1. **Install dependencies:**
```bash
cd python-backend
pip install -r requirements.txt
```

2. **Set environment variables:**
```bash
export BASE_URL="http://your-model-runner-url/v1"
export MODEL="your-model-name"
export API_KEY="your-api-key"
```

3. **Run the application:**
```bash
python -m app.server
```

The API will be available at:
- Main API: http://localhost:8080
- Metrics: http://localhost:9090
- Documentation: http://localhost:8080/docs

### Docker Deployment

1. **Build and run with Docker Compose:**
```bash
docker-compose up --build
```

This will start:
- Python backend on ports 8081 (API) and 9091 (metrics)
- Prometheus on port 9092
- Grafana on port 3001
- Jaeger on port 16686

## API Endpoints

### Core Endpoints

- `GET /health` - Health check with model information
- `POST /chat` - Streaming chat completions
- `OPTIONS /{path:path}` - CORS preflight handling

### Metrics Endpoints

- `GET /metrics` - Prometheus metrics (text format)
- `GET /metrics/summary` - JSON metrics summary for frontend
- `POST /metrics/log` - Log chat interaction metrics
- `POST /metrics/llamacpp` - Log LlamaCpp specific metrics
- `POST /metrics/error` - Log error metrics

## Configuration

The application is configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URL` | OpenAI API compatible base URL | Required |
| `MODEL` | Model name to use | Required |
| `API_KEY` | API key for authentication | Required |
| `TRACING_ENABLED` | Enable OpenTelemetry tracing | `false` |
| `OTLP_ENDPOINT` | OTLP endpoint for tracing | `jaeger:4318` |
| `PORT` | Main server port | `8080` |
| `METRICS_PORT` | Metrics server port | `9090` |

## Data Models

### ChatRequest
```python
{
    "message": "Your question here",
    "messages": [
        {"role": "user", "content": "Previous message"},
        {"role": "assistant", "content": "Previous response"}
    ],
    "format": "markdown"  # Optional
}
```

### MetricLog
```python
{
    "message_id": "unique-id",
    "tokens_in": 25,
    "tokens_out": 150,
    "response_time_ms": 2500.0,
    "first_token_ms": 800.0
}
```

### LlamaCppMetrics
```python
{
    "context_size": 4096,
    "prompt_eval_time": 1000.0,
    "tokens_per_second": 15.5,
    "memory_per_token": 512.0,
    "threads_used": 4,
    "batch_size": 32,
    "model_type": "llama.cpp"
}
```

## Metrics Collected

### HTTP Metrics
- `genai_app_http_requests_total` - Total HTTP requests
- `genai_app_http_request_duration_seconds` - Request duration
- `genai_app_active_requests` - Currently active requests

### Chat Metrics
- `genai_app_chat_tokens_total` - Total tokens processed
- `genai_app_model_latency_seconds` - Model response latency
- `genai_app_first_token_latency_seconds` - Time to first token

### Error Metrics
- `genai_app_errors_total` - Total errors by type

### LlamaCpp Metrics
- `genai_app_llamacpp_context_size` - Context window size
- `genai_app_llamacpp_prompt_eval_seconds` - Prompt evaluation time
- `genai_app_llamacpp_tokens_per_second` - Token generation rate
- `genai_app_llamacpp_memory_per_token_bytes` - Memory per token
- `genai_app_llamacpp_threads_used` - Inference threads
- `genai_app_llamacpp_batch_size` - Inference batch size

## Testing

### Run Unit Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html
```

### Test Coverage
The test suite covers:
- All API endpoints
- Data model validation
- Metrics collection
- Error handling
- Configuration management
- CORS functionality
- OpenAI client integration (mocked)

## Architecture

### Application Structure
```
app/
├── __init__.py          # Package initialization
├── main.py              # FastAPI application and endpoints
├── server.py            # Multi-server runner
├── config.py            # Configuration management
├── models.py            # Pydantic data models
├── metrics.py           # Prometheus metrics setup
└── tracing.py           # OpenTelemetry tracing setup
```

### Key Components

1. **FastAPI Application** (`main.py`)
   - All API endpoints
   - Middleware for metrics collection
   - CORS handling
   - Streaming response support

2. **Server Runner** (`server.py`)
   - Manages both main and metrics servers
   - Graceful shutdown handling
   - Signal handling

3. **Metrics System** (`metrics.py`)
   - Prometheus metrics definitions
   - Helper functions for metric collection
   - Custom registry for isolation

4. **Tracing System** (`tracing.py`)
   - OpenTelemetry setup
   - OTLP exporter configuration
   - Instrumentation for FastAPI and requests

## Development

### Code Quality
```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

### Adding New Endpoints

1. Define data models in `models.py`
2. Add endpoint to `main.py`
3. Add metrics collection if needed
4. Add tracing spans for observability
5. Write unit tests in `tests/`

### Monitoring and Observability

The application provides comprehensive observability:

1. **Metrics**: Prometheus metrics for performance monitoring
2. **Tracing**: OpenTelemetry traces for request flow analysis
3. **Logging**: Structured JSON logging with contextual information
4. **Health Checks**: Kubernetes-ready health and readiness probes

## Deployment

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: genai-python-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: genai-python-backend
  template:
    metadata:
      labels:
        app: genai-python-backend
    spec:
      containers:
      - name: backend
        image: genai-python-backend:latest
        ports:
        - containerPort: 8080
        - containerPort: 9090
        env:
        - name: BASE_URL
          value: "http://model-runner:11434/v1"
        - name: MODEL
          value: "llama3.2:1b"
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: genai-secrets
              key: api-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Production Considerations

1. **Security**
   - Use non-root user in containers
   - Implement proper authentication
   - Use secrets management for API keys
   - Enable HTTPS in production

2. **Performance**
   - Configure appropriate worker processes
   - Use Redis for caching if needed
   - Implement connection pooling
   - Monitor memory usage

3. **Reliability**
   - Implement circuit breakers
   - Add retry logic with exponential backoff
   - Configure proper timeouts
   - Use health checks for auto-recovery

## Comparison with Go Version

| Feature | Go Version | Python Version |
|---------|------------|----------------|
| Framework | Native HTTP | FastAPI |
| Concurrency | Goroutines | Asyncio |
| Metrics | Prometheus | Prometheus |
| Tracing | OpenTelemetry | OpenTelemetry |
| Streaming | Native | Server-Sent Events |
| Type Safety | Built-in | Pydantic |
| Performance | Higher | Good |
| Development Speed | Moderate | Faster |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure code quality checks pass
6. Submit a pull request

## License

This project is licensed under the same terms as the original Go implementation.

## Support

For issues and questions:
1. Check the existing issues in the repository
2. Create a new issue with detailed description
3. Include logs and configuration details
4. Provide steps to reproduce the problem