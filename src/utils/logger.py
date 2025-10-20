"""
Logging utilities for the matching engine
"""

import logging
import sys
from typing import Optional
import os


class EngineLogger:
    """Custom logger for the matching engine"""

    def __init__(
        self,
        name: str = "matching_engine",
        level: str = "INFO",
        log_file: Optional[str] = None,
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler (if specified)
        if log_file:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(self._format_message(message, kwargs))

    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(self._format_message(message, kwargs))

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(self._format_message(message, kwargs))

    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(self._format_message(message, kwargs))

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(self._format_message(message, kwargs))

    def log_regime_change(self, from_regime: str, to_regime: str, reason: str = ""):
        """Log regime change with details"""
        message = f"Regime change: {from_regime} -> {to_regime}"
        if reason:
            message += f" | Reason: {reason}"
        self.info(message, from_regime=from_regime, to_regime=to_regime, reason=reason)

    def log_order_processing(
        self,
        order_id: str,
        side: str,
        quantity: int,
        price: float,
        trades_generated: int,
        processing_time: float,
    ):
        """Log order processing details"""
        self.debug(
            f"Order processed: {order_id} | {side} {quantity} @ {price} | "
            f"Trades: {trades_generated} | Time: {processing_time:.6f}s",
            order_id=order_id,
            side=side,
            quantity=quantity,
            price=price,
            trades_generated=trades_generated,
            processing_time=processing_time,
        )

    def log_performance_metrics(
        self, throughput: float, avg_latency: float, p95_latency: float, regime: str
    ):
        """Log performance metrics"""
        self.info(
            f"Performance | Throughput: {throughput:.2f} ops/sec | "
            f"Avg Latency: {avg_latency:.4f}ms | P95: {p95_latency:.4f}ms | "
            f"Regime: {regime}",
            throughput=throughput,
            avg_latency=avg_latency,
            p95_latency=p95_latency,
            regime=regime,
        )

    def _format_message(self, message: str, kwargs: dict) -> str:
        """Format message with additional context"""
        if kwargs:
            context = " | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())
            return message + context
        return message


# Global logger instance
_global_logger: Optional[EngineLogger] = None


def get_logger(name: str = "matching_engine", **kwargs) -> EngineLogger:
    """Get or create global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = EngineLogger(name, **kwargs)
    return _global_logger


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Setup global logging configuration"""
    global _global_logger
    _global_logger = EngineLogger("matching_engine", level, log_file)
