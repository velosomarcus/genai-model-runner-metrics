"""Test the metrics functionality."""

import pytest
from unittest.mock import patch, MagicMock
from app.metrics import MetricsHelper, request_counter, active_requests, llamacpp_context_size


class TestMetricsHelper:
    """Test MetricsHelper functionality."""
    
    def test_calculate_error_rate_no_requests(self):
        """Test error rate calculation with no requests."""
        # Mock the counter values
        with patch.object(MetricsHelper, 'get_counter_value') as mock_get:
            mock_get.side_effect = [0, 0]  # errors, requests
            
            error_rate = MetricsHelper.calculate_error_rate()
            assert error_rate == 0.0
    
    def test_calculate_error_rate_with_errors(self):
        """Test error rate calculation with errors."""
        with patch.object(MetricsHelper, 'get_counter_value') as mock_get:
            mock_get.side_effect = [2, 10]  # 2 errors out of 10 requests
            
            error_rate = MetricsHelper.calculate_error_rate()
            assert error_rate == 0.2
    
    def test_get_llama_cpp_metrics_no_data(self):
        """Test getting LlamaCpp metrics when no data available."""
        with patch.object(MetricsHelper, 'get_gauge_value') as mock_gauge:
            mock_gauge.return_value = 0  # No context size
            
            metrics = MetricsHelper.get_llama_cpp_metrics("test-model")
            assert metrics is None
    
    def test_get_llama_cpp_metrics_with_data(self):
        """Test getting LlamaCpp metrics with data."""
        with patch.object(MetricsHelper, 'get_gauge_value') as mock_gauge, \
             patch.object(MetricsHelper, 'get_histogram_average') as mock_hist:
            
            # Mock the gauge values
            mock_gauge.side_effect = [4096, 15.5, 512.0, 4, 32]  # context, tps, memory, threads, batch
            mock_hist.return_value = 0.5  # prompt eval time
            
            metrics = MetricsHelper.get_llama_cpp_metrics("test-model")
            
            assert metrics is not None
            assert metrics["context_size"] == 4096
            assert metrics["tokens_per_second"] == 15.5
            assert metrics["model_type"] == "llama.cpp"
    
    def test_get_histogram_average_mock(self):
        """Test getting histogram average with mock."""
        mock_histogram = MagicMock()
        
        with patch.object(MetricsHelper, 'get_histogram_average') as mock_method:
            mock_method.return_value = 10.0
            
            avg = MetricsHelper.get_histogram_average(mock_histogram)
            assert avg == 10.0