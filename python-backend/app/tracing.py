"""
OpenTelemetry tracing setup and utilities.

This module provides tracing functionality using OpenTelemetry,
mirroring the Go implementation's tracing capabilities.
"""

import os
from typing import Optional, Callable
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
import structlog

logger = structlog.get_logger()


class TracingSetup:
    """Handles OpenTelemetry tracing setup and configuration."""
    
    def __init__(self):
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer = None
        
    def setup_tracing(self, service_name: str, otlp_endpoint: str) -> Optional[Callable]:
        """
        Initialize OpenTelemetry tracing.
        
        Args:
            service_name: Name of the service
            otlp_endpoint: OTLP endpoint URL
            
        Returns:
            Optional[Callable]: Cleanup function or None if setup failed
        """
        try:
            # Create resource with service information
            resource = Resource(attributes={
                ResourceAttributes.SERVICE_NAME: service_name,
            })
            
            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            
            # Set up OTLP exporter if endpoint provided
            if otlp_endpoint:
                otlp_exporter = OTLPSpanExporter(
                    endpoint=f"http://{otlp_endpoint}/v1/traces",
                    insecure=True,
                )
                
                # Add batch span processor
                span_processor = BatchSpanProcessor(otlp_exporter)
                self.tracer_provider.add_span_processor(span_processor)
            
            # Set global tracer provider
            trace.set_tracer_provider(self.tracer_provider)
            
            # Get tracer
            self.tracer = trace.get_tracer(service_name)
            
            # Instrument FastAPI and requests
            FastAPIInstrumentor.instrument()
            RequestsInstrumentor.instrument()
            
            logger.info("Tracing initialized successfully", endpoint=otlp_endpoint)
            
            # Return cleanup function
            return self.cleanup_tracing
            
        except Exception as e:
            logger.error("Failed to set up tracing", error=str(e))
            return None
    
    def cleanup_tracing(self):
        """Clean up tracing resources."""
        try:
            if self.tracer_provider:
                self.tracer_provider.force_flush(timeout_millis=5000)
                self.tracer_provider.shutdown()
            logger.info("Tracing cleaned up successfully")
        except Exception as e:
            logger.error("Error during tracing cleanup", error=str(e))
    
    def start_span(self, name: str, **kwargs):
        """
        Start a new span.
        
        Args:
            name: Span name
            **kwargs: Additional span attributes
            
        Returns:
            Span context manager
        """
        if self.tracer:
            return self.tracer.start_as_current_span(name, attributes=kwargs)
        else:
            # Return no-op context manager if tracing not initialized
            return NoOpSpan()
    
    def add_span_attribute(self, key: str, value):
        """
        Add attribute to current span.
        
        Args:
            key: Attribute key
            value: Attribute value
        """
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.set_attribute(key, value)
    
    def record_exception(self, exception: Exception, message: str = ""):
        """
        Record an exception in the current span.
        
        Args:
            exception: Exception to record
            message: Optional error message
        """
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.record_exception(exception)
            if message:
                current_span.set_attribute("error.message", message)
    
    def add_event(self, name: str, **attributes):
        """
        Add an event to the current span.
        
        Args:
            name: Event name
            **attributes: Event attributes
        """
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.add_event(name, attributes)


class NoOpSpan:
    """No-op span for when tracing is disabled."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def set_attribute(self, key: str, value):
        pass
    
    def add_event(self, name: str, **attributes):
        pass
    
    def record_exception(self, exception: Exception):
        pass


# Global tracing instance
tracing_setup = TracingSetup()