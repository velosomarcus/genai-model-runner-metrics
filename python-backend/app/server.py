"""
Server runner for the GenAI Model Runner Metrics API.

This module handles running both the main API server and the metrics server,
mirroring the Go implementation's two-server setup.
"""

import asyncio
import signal
import threading
import uvicorn
import structlog
from .main import app, create_metrics_server
from .config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class ServerRunner:
    """Manages running both main and metrics servers."""
    
    def __init__(self):
        self.main_server = None
        self.metrics_server = None
        self.shutdown_event = asyncio.Event()
    
    async def start_main_server(self):
        """Start the main API server."""
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=settings.port,
            log_config=None,  # Use our structured logging
            access_log=False  # Disable default access log
        )
        self.main_server = uvicorn.Server(config)
        logger.info("Starting main server", port=settings.port)
        await self.main_server.serve()
    
    async def start_metrics_server(self):
        """Start the metrics server."""
        metrics_app = create_metrics_server()
        config = uvicorn.Config(
            metrics_app,
            host="0.0.0.0",
            port=settings.metrics_port,
            log_config=None,  # Use our structured logging
            access_log=False  # Disable default access log
        )
        self.metrics_server = uvicorn.Server(config)
        logger.info("Starting metrics server", port=settings.metrics_port)
        await self.metrics_server.serve()
    
    async def shutdown(self):
        """Gracefully shutdown both servers."""
        logger.info("Shutting down servers...")
        
        if self.main_server:
            self.main_server.should_exit = True
        
        if self.metrics_server:
            self.metrics_server.should_exit = True
        
        # Wait a bit for graceful shutdown
        await asyncio.sleep(1)
        
        logger.info("Servers shut down successfully")
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal", signal=signum)
            asyncio.create_task(self.shutdown())
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Run both servers concurrently."""
        self.setup_signal_handlers()
        
        try:
            # Start both servers concurrently
            await asyncio.gather(
                self.start_main_server(),
                self.start_metrics_server(),
                return_exceptions=True
            )
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error("Server error", error=str(e))
        finally:
            await self.shutdown()


def main():
    """Main entry point."""
    runner = ServerRunner()
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()