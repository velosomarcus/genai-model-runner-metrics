"""
Prometheus metrics setup and helper functions.

This module provides Prometheus metrics collection functionality,
mirroring the Go implementation's metrics.
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from typing import Dict, Optional
import time


# Create custom registry for metrics
registry = CollectorRegistry()

# HTTP request metrics
request_counter = Counter(
    'genai_app_http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

request_duration = Histogram(
    'genai_app_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

# Chat token metrics
chat_tokens_counter = Counter(
    'genai_app_chat_tokens_total',
    'Total number of tokens processed in chat',
    ['direction', 'model'],
    registry=registry
)

# Model latency metrics
model_latency = Histogram(
    'genai_app_model_latency_seconds',
    'Model response time in seconds',
    ['model', 'operation'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 20, 30, 60],
    registry=registry
)

# Active requests gauge
active_requests = Gauge(
    'genai_app_active_requests',
    'Number of currently active requests',
    registry=registry
)

# Error counter
error_counter = Counter(
    'genai_app_errors_total',
    'Total number of errors',
    ['type'],
    registry=registry
)

# First token latency
first_token_latency = Histogram(
    'genai_app_first_token_latency_seconds',
    'Time to first token in seconds',
    ['model'],
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2, 5],
    registry=registry
)

# LlamaCpp specific metrics
llamacpp_context_size = Gauge(
    'genai_app_llamacpp_context_size',
    'Context window size in tokens for llama.cpp models',
    ['model'],
    registry=registry
)

llamacpp_prompt_eval_time = Histogram(
    'genai_app_llamacpp_prompt_eval_seconds',
    'Time spent evaluating the prompt in seconds',
    ['model'],
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10],
    registry=registry
)

llamacpp_tokens_per_second = Gauge(
    'genai_app_llamacpp_tokens_per_second',
    'Tokens generated per second',
    ['model'],
    registry=registry
)

llamacpp_memory_per_token = Gauge(
    'genai_app_llamacpp_memory_per_token_bytes',
    'Memory usage per token in bytes',
    ['model'],
    registry=registry
)

llamacpp_threads_used = Gauge(
    'genai_app_llamacpp_threads_used',
    'Number of threads used for inference',
    ['model'],
    registry=registry
)

llamacpp_batch_size = Gauge(
    'genai_app_llamacpp_batch_size',
    'Batch size used for inference',
    ['model'],
    registry=registry
)


class MetricsHelper:
    """Helper class for working with Prometheus metrics."""
    
    @staticmethod
    def get_counter_value(counter: Counter, label_values: Optional[Dict[str, str]] = None) -> float:
        """
        Get the current value of a counter metric.
        
        Args:
            counter: The Counter metric
            label_values: Optional label values to filter by
            
        Returns:
            float: Current counter value
        """
        try:
            if label_values:
                return counter.labels(**label_values)._value._value
            else:
                # Sum all values across labels
                total = 0.0
                for sample in counter.collect()[0].samples:
                    total += sample.value
                return total
        except:
            return 0.0
    
    @staticmethod
    def get_gauge_value(gauge: Gauge, label_values: Optional[Dict[str, str]] = None) -> float:
        """
        Get the current value of a gauge metric.
        
        Args:
            gauge: The Gauge metric
            label_values: Optional label values to filter by
            
        Returns:
            float: Current gauge value
        """
        try:
            if label_values:
                return gauge.labels(**label_values)._value._value
            else:
                # Get first available value
                for sample in gauge.collect()[0].samples:
                    return sample.value
                return 0.0
        except:
            return 0.0
    
    @staticmethod
    def get_histogram_average(histogram: Histogram, label_values: Optional[Dict[str, str]] = None) -> float:
        """
        Get the average value from a histogram metric.
        
        Args:
            histogram: The Histogram metric
            label_values: Optional label values to filter by
            
        Returns:
            float: Average value
        """
        try:
            samples = histogram.collect()[0].samples
            total_sum = 0.0
            total_count = 0.0
            
            for sample in samples:
                if sample.name.endswith('_sum'):
                    total_sum = sample.value
                elif sample.name.endswith('_count'):
                    total_count = sample.value
            
            return total_sum / total_count if total_count > 0 else 0.0
        except:
            return 0.0
    
    @staticmethod
    def calculate_error_rate() -> float:
        """
        Calculate the current error rate.
        
        Returns:
            float: Error rate as a percentage
        """
        total_errors = MetricsHelper.get_counter_value(error_counter)
        total_requests = MetricsHelper.get_counter_value(request_counter)
        
        if total_requests == 0:
            return 0.0
        
        return total_errors / total_requests
    
    @staticmethod
    def get_llama_cpp_metrics(model: str) -> Optional[Dict]:
        """
        Get LlamaCpp specific metrics for a model.
        
        Args:
            model: Model name
            
        Returns:
            Optional[Dict]: LlamaCpp metrics or None if not available
        """
        context_size = MetricsHelper.get_gauge_value(
            llamacpp_context_size, 
            {"model": model}
        )
        
        if context_size == 0:
            return None
        
        return {
            "context_size": int(context_size),
            "prompt_eval_time": MetricsHelper.get_histogram_average(
                llamacpp_prompt_eval_time, 
                {"model": model}
            ) * 1000,  # Convert to ms
            "tokens_per_second": MetricsHelper.get_gauge_value(
                llamacpp_tokens_per_second, 
                {"model": model}
            ),
            "memory_per_token": MetricsHelper.get_gauge_value(
                llamacpp_memory_per_token, 
                {"model": model}
            ),
            "threads_used": int(MetricsHelper.get_gauge_value(
                llamacpp_threads_used, 
                {"model": model}
            )),
            "batch_size": int(MetricsHelper.get_gauge_value(
                llamacpp_batch_size, 
                {"model": model}
            )),
            "model_type": "llama.cpp"
        }


def get_metrics_text() -> str:
    """
    Get Prometheus metrics in text format.
    
    Returns:
        str: Prometheus metrics text
    """
    return generate_latest(registry).decode('utf-8')