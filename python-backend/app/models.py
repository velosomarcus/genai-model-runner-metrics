"""
Data models for the GenAI Model Runner Metrics API.

This module defines all the Pydantic models used throughout the application,
mirroring the Go structs from the original implementation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Message(BaseModel):
    """
    Represents a single message in a chat conversation.
    
    Attributes:
        role: The role of the message sender ("user", "assistant", "system")
        content: The actual message content
    """
    role: str = Field(..., description="The role of the message sender")
    content: str = Field(..., description="The message content")


class ChatRequest(BaseModel):
    """
    Request model for the chat endpoint.
    
    Attributes:
        messages: List of previous messages in the conversation
        message: The current user message
        format: Optional format parameter (e.g., "markdown")
    """
    messages: List[Message] = Field(default_factory=list, description="Previous conversation messages")
    message: str = Field(..., description="Current user message")
    format: Optional[str] = Field(None, description="Optional response format")


class MetricLog(BaseModel):
    """
    Model for logging chat interaction metrics.
    
    Attributes:
        message_id: Unique identifier for the message
        tokens_in: Number of input tokens
        tokens_out: Number of output tokens
        response_time_ms: Total response time in milliseconds
        first_token_ms: Time to first token in milliseconds
    """
    message_id: str = Field(..., description="Unique message identifier")
    tokens_in: int = Field(..., description="Input token count")
    tokens_out: int = Field(..., description="Output token count")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    first_token_ms: float = Field(..., description="Time to first token in milliseconds")


class ErrorLog(BaseModel):
    """
    Model for logging errors.
    
    Attributes:
        error_type: Type/category of the error
        status_code: HTTP status code
        input_length: Length of the input that caused the error
        timestamp: When the error occurred
    """
    error_type: str = Field(..., description="Error type or category")
    status_code: int = Field(..., description="HTTP status code")
    input_length: int = Field(..., description="Input length")
    timestamp: str = Field(..., description="Error timestamp")


class LlamaCppMetrics(BaseModel):
    """
    Metrics specific to llama.cpp models.
    
    Attributes:
        context_size: Context window size in tokens
        prompt_eval_time: Time spent evaluating prompt in milliseconds
        tokens_per_second: Token generation rate
        memory_per_token: Memory usage per token in bytes
        threads_used: Number of threads used for inference
        batch_size: Batch size used for inference
        model_type: Type of model (always "llama.cpp")
    """
    context_size: int = Field(..., description="Context window size in tokens")
    prompt_eval_time: float = Field(..., description="Prompt evaluation time in milliseconds")
    tokens_per_second: float = Field(..., description="Token generation rate")
    memory_per_token: float = Field(..., description="Memory per token in bytes")
    threads_used: int = Field(..., description="Number of inference threads")
    batch_size: int = Field(..., description="Inference batch size")
    model_type: str = Field(default="llama.cpp", description="Model type")


class MetricsSummary(BaseModel):
    """
    Summary of all metrics for the frontend.
    
    Attributes:
        total_requests: Total number of requests processed
        average_response_time: Average response time across all requests
        tokens_generated: Total tokens generated
        tokens_processed: Total tokens processed
        active_users: Number of currently active users
        error_rate: Error rate as a percentage
        llama_cpp_metrics: LlamaCpp-specific metrics if applicable
    """
    total_requests: float = Field(..., description="Total requests processed")
    average_response_time: float = Field(..., description="Average response time")
    tokens_generated: float = Field(..., description="Total tokens generated")
    tokens_processed: float = Field(..., description="Total tokens processed")
    active_users: float = Field(..., description="Active users count")
    error_rate: float = Field(..., description="Error rate percentage")
    llama_cpp_metrics: Optional[LlamaCppMetrics] = Field(None, description="LlamaCpp metrics")


class HealthResponse(BaseModel):
    """
    Health check response model.
    
    Attributes:
        status: Health status ("ok" or "error")
        model_info: Information about the configured model
    """
    status: str = Field(..., description="Health status")
    model_info: Dict[str, Any] = Field(..., description="Model information")


class ConfigSettings(BaseModel):
    """
    Application configuration settings.
    
    Attributes:
        base_url: Base URL for the OpenAI-compatible API
        model: Model name to use
        api_key: API key for authentication
        tracing_enabled: Whether OpenTelemetry tracing is enabled
        otlp_endpoint: OTLP endpoint for tracing
        port: Port to run the main server on
        metrics_port: Port to run the metrics server on
    """
    base_url: str = Field(..., description="OpenAI API base URL")
    model: str = Field(..., description="Model name")
    api_key: str = Field(..., description="API key")
    tracing_enabled: bool = Field(default=False, description="Enable tracing")
    otlp_endpoint: str = Field(default="jaeger:4318", description="OTLP endpoint")
    port: int = Field(default=8080, description="Main server port")
    metrics_port: int = Field(default=9090, description="Metrics server port")