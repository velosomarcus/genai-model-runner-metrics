"""
Main FastAPI application for GenAI Model Runner Metrics.

This module contains the main FastAPI application with all endpoints,
mirroring the Go implementation's functionality.
"""

import asyncio
import time
import structlog
from datetime import datetime
from typing import AsyncGenerator, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, PlainTextResponse
from openai import AsyncOpenAI
import uvicorn

from .config import get_settings
from .models import (
    ChatRequest, MetricLog, ErrorLog, LlamaCppMetrics, 
    MetricsSummary, HealthResponse
)
from .metrics import (
    request_counter, request_duration, active_requests, error_counter,
    chat_tokens_counter, model_latency, first_token_latency,
    llamacpp_context_size, llamacpp_prompt_eval_time, llamacpp_tokens_per_second,
    llamacpp_memory_per_token, llamacpp_threads_used, llamacpp_batch_size,
    MetricsHelper, get_metrics_text, registry
)
from .tracing import tracing_setup

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Get application settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title="GenAI Model Runner Metrics API",
    description="FastAPI port of the Go GenAI application with observability features",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
openai_client: Optional[AsyncOpenAI] = None
tracing_cleanup: Optional[callable] = None


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    global openai_client, tracing_cleanup
    
    logger.info("Starting GenAI App with observability")
    
    # Initialize OpenAI client
    if settings.base_url and settings.api_key:
        openai_client = AsyncOpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key
        )
        logger.info("OpenAI client initialized", base_url=settings.base_url)
    else:
        logger.warning("OpenAI client not initialized - missing BASE_URL or API_KEY")
    
    # Initialize tracing if enabled
    if settings.tracing_enabled:
        logger.info("Setting up tracing", endpoint=settings.otlp_endpoint)
        tracing_cleanup = tracing_setup.setup_tracing("genai-app", settings.otlp_endpoint)
        if tracing_cleanup:
            logger.info("Tracing initialized successfully")
        else:
            logger.error("Failed to initialize tracing")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down GenAI App")
    
    # Cleanup tracing
    if tracing_cleanup:
        tracing_cleanup()
    
    # Close OpenAI client
    if openai_client:
        await openai_client.close()


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect metrics for all requests."""
    start_time = time.time()
    active_requests.inc()
    
    try:
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        request_counter.labels(
            method=request.method,
            endpoint=request.url.path,
            status=str(response.status_code)
        ).inc()
        
        return response
    
    except Exception as e:
        # Record error
        error_counter.labels(type=type(e).__name__).inc()
        logger.error("Request failed", error=str(e), path=request.url.path)
        raise
    
    finally:
        active_requests.dec()


def estimate_tokens(text: str) -> int:
    """
    Rough estimation of token count (divide by 4).
    
    Args:
        text: Input text
        
    Returns:
        int: Estimated token count
    """
    return len(text) // 4


def is_llama_model(model: str, base_url: str) -> bool:
    """
    Check if the model is a llama.cpp model.
    
    Args:
        model: Model name
        base_url: Base URL
        
    Returns:
        bool: True if it's a llama model
    """
    return "llama" in model.lower() or "llama.cpp" in base_url.lower()


def get_context_window_size(model: str) -> int:
    """
    Get default context window size based on model name.
    
    Args:
        model: Model name
        
    Returns:
        int: Context window size
    """
    if "1B" in model:
        return 2048
    elif "7B" in model:
        return 4096
    elif "13B" in model:
        return 4096
    elif "70B" in model:
        return 8192
    else:
        return 4096  # Default


@app.options("/{path:path}")
async def options_handler(request: Request):
    """Handle CORS preflight requests."""
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns application health status and model information.
    """
    model_info = {
        "model": settings.model
    }
    
    # Add model type and context window for llama models
    if is_llama_model(settings.model, settings.base_url):
        model_info["modelType"] = "llama.cpp"
        
        # Try to get context size from metrics, otherwise use default
        context_size = MetricsHelper.get_gauge_value(
            llamacpp_context_size, 
            {"model": settings.model}
        )
        
        if context_size > 0:
            model_info["contextWindow"] = int(context_size)
        else:
            model_info["contextWindow"] = get_context_window_size(settings.model)
    
    return HealthResponse(
        status="ok",
        model_info=model_info
    )


@app.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format.
    """
    return get_metrics_text()


@app.get("/metrics/summary", response_model=MetricsSummary)
async def get_metrics_summary():
    """
    Get metrics summary for the frontend.
    
    Returns aggregated metrics in a frontend-friendly format.
    """
    # Get llama.cpp metrics if applicable
    llama_cpp_metrics = None
    if is_llama_model(settings.model, settings.base_url):
        llama_metrics_data = MetricsHelper.get_llama_cpp_metrics(settings.model)
        if llama_metrics_data:
            llama_cpp_metrics = LlamaCppMetrics(**llama_metrics_data)
    
    # Create metrics summary
    summary = MetricsSummary(
        total_requests=MetricsHelper.get_counter_value(request_counter),
        average_response_time=MetricsHelper.get_histogram_average(request_duration),
        tokens_generated=MetricsHelper.get_counter_value(
            chat_tokens_counter, 
            {"direction": "output", "model": settings.model}
        ),
        tokens_processed=MetricsHelper.get_counter_value(
            chat_tokens_counter, 
            {"direction": "input", "model": settings.model}
        ),
        active_users=MetricsHelper.get_gauge_value(active_requests),
        error_rate=MetricsHelper.calculate_error_rate(),
        llama_cpp_metrics=llama_cpp_metrics
    )
    
    return summary


@app.post("/metrics/log")
async def log_metrics(metric_log: MetricLog):
    """
    Log chat metrics.
    
    Args:
        metric_log: Metrics to log
    """
    # Log first token latency if available
    if metric_log.first_token_ms > 0:
        first_token_latency.labels(model=settings.model).observe(
            metric_log.first_token_ms / 1000.0
        )
    
    return {"status": "ok"}


@app.post("/metrics/llamacpp")
async def log_llamacpp_metrics(llamacpp_log: LlamaCppMetrics):
    """
    Log LlamaCpp specific metrics.
    
    Args:
        llamacpp_log: LlamaCpp metrics to log
    """
    model = settings.model
    
    # Record all llama.cpp metrics
    llamacpp_context_size.labels(model=model).set(llamacpp_log.context_size)
    llamacpp_prompt_eval_time.labels(model=model).observe(
        llamacpp_log.prompt_eval_time / 1000.0  # Convert ms to seconds
    )
    llamacpp_tokens_per_second.labels(model=model).set(llamacpp_log.tokens_per_second)
    llamacpp_memory_per_token.labels(model=model).set(llamacpp_log.memory_per_token)
    llamacpp_threads_used.labels(model=model).set(llamacpp_log.threads_used)
    llamacpp_batch_size.labels(model=model).set(llamacpp_log.batch_size)
    
    return {"status": "ok"}


@app.post("/metrics/error")
async def log_error(error_log: ErrorLog):
    """
    Log error metrics.
    
    Args:
        error_log: Error information to log
    """
    error_counter.labels(type=error_log.error_type).inc()
    return {"status": "ok"}


@app.post("/chat")
async def chat_endpoint(chat_request: ChatRequest, request: Request):
    """
    Main chat endpoint with streaming support.
    
    Args:
        chat_request: Chat request data
        request: FastAPI request object
        
    Returns:
        StreamingResponse: Streaming chat response
    """
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")
    
    # Start tracing span
    with tracing_setup.start_span("chat_request") as span:
        tracing_setup.add_span_attribute("model", settings.model)
        tracing_setup.add_span_attribute("message_length", len(chat_request.message))
        
        # Count input tokens
        input_tokens = estimate_tokens(chat_request.message)
        for msg in chat_request.messages:
            input_tokens += estimate_tokens(msg.content)
        
        # Track input tokens
        chat_tokens_counter.labels(direction="input", model=settings.model).inc(input_tokens)
        
        # Build messages for OpenAI
        messages = []
        for msg in chat_request.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Check for markdown formatting request
        use_markdown = (
            chat_request.format == "markdown" or
            "in markdown" in chat_request.message.lower() or
            "using markdown" in chat_request.message.lower()
        )
        
        # Add system message for markdown if requested
        if use_markdown:
            system_msg = {
                "role": "system",
                "content": "Please format your response using markdown. Use proper headings, bullet points, numbered lists, code blocks with syntax highlighting, and tables where appropriate."
            }
            messages.insert(0, system_msg)
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": chat_request.message
        })
        
        async def generate_response() -> AsyncGenerator[str, None]:
            """Generate streaming response from OpenAI."""
            start_time = time.time()
            model_start_time = time.time()
            prompt_eval_start_time = time.time()
            first_token_time = None
            output_tokens = 0
            
            try:
                # Create chat completion stream
                stream = await openai_client.chat.completions.create(
                    model=settings.model,
                    messages=messages,
                    stream=True,
                    timeout=90.0
                )
                
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        
                        # Record first token time
                        if first_token_time is None:
                            first_token_time = time.time()
                            
                            # Record prompt evaluation time for llama models
                            if is_llama_model(settings.model, settings.base_url):
                                prompt_eval_time = first_token_time - prompt_eval_start_time
                                llamacpp_prompt_eval_time.labels(model=settings.model).observe(prompt_eval_time)
                        
                        output_tokens += 1
                        yield content
                
                # Calculate final metrics
                total_duration = time.time() - start_time
                model_duration = time.time() - model_start_time
                
                # Record metrics
                request_duration.labels(
                    method="POST",
                    endpoint="/chat"
                ).observe(total_duration)
                
                chat_tokens_counter.labels(
                    direction="output",
                    model=settings.model
                ).inc(output_tokens)
                
                model_latency.labels(
                    model=settings.model,
                    operation="inference"
                ).observe(model_duration)
                
                # Record first token latency
                if first_token_time:
                    ttft = first_token_time - model_start_time
                    first_token_latency.labels(model=settings.model).observe(ttft)
                    logger.info("Time to first token", ttft_seconds=ttft)
                
                # Calculate tokens per second for llama models
                if is_llama_model(settings.model, settings.base_url) and first_token_time:
                    total_time = time.time() - first_token_time
                    if total_time > 0 and output_tokens > 0:
                        tokens_per_second = output_tokens / total_time
                        llamacpp_tokens_per_second.labels(model=settings.model).set(tokens_per_second)
                
                tracing_setup.add_span_attribute("output_tokens", output_tokens)
                tracing_setup.add_span_attribute("total_duration", total_duration)
                
            except Exception as e:
                error_counter.labels(type=type(e).__name__).inc()
                tracing_setup.record_exception(e, "Chat request failed")
                logger.error("Chat request failed", error=str(e))
                yield f"Error: {str(e)}"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        )


# Create metrics server app
metrics_app = FastAPI(title="Metrics Server")

@metrics_app.get("/")
async def metrics_root():
    """Metrics server root endpoint."""
    return get_metrics_text()


def create_metrics_server():
    """Create and configure the metrics server."""
    return metrics_app


if __name__ == "__main__":
    # Run the main application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
        log_config=None  # Use our structured logging
    )