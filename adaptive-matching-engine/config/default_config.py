"""
Default configuration for the adaptive matching engine
"""

DEFAULT_CONFIG = {
    "regime_detection": {
        "window_size": 50,
        "volatility_threshold": 0.05,
        "spread_threshold": 0.02,
        "imbalance_threshold": 0.8,
        "cancellation_threshold": 0.4,
        "detection_interval": 100,
    },
    # Matching Engine Parameters
    "matching_engine": {
        "max_order_book_levels": 1000,
        "enable_adaptive_logic": True,
        "default_regime": "NORMAL",
        "regime_transition_delay": 0.001,  # 1ms delay during transition
    },
    # Performance Monitoring
    "performance": {
        "enable_monitoring": True,
        "sample_interval": 100,  # Sample every 100 orders
        "latency_warning_threshold": 0.01,  # 10ms warning threshold
        "throughput_target": 10000,  # Target throughput (orders/sec)
    },
    # Order Validation
    "validation": {
        "min_order_price": 0.01,
        "max_order_price": 1000000.0,
        "min_order_quantity": 1,
        "max_order_quantity": 1000000,
        "allow_market_orders": True,
        "allow_ioc_orders": True,
    },
    # Logging Configuration
    "logging": {
        "level": "INFO",
        "enable_file_logging": False,
        "log_file": "matching_engine.log",
        "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
}

# Regime-specific matching policies
REGIME_POLICIES = {
    "NORMAL": {
        "priority_rule": "PRICE_TIME",
        "description": "Standard Price-Time priority",
        "matching_algorithm": "FIFO",
        "liquidity_incentive": False,
    },
    "HIGH_VOLATILITY": {
        "priority_rule": "PRICE_SIZE_TIME",
        "description": "Price-Size-Time priority to encourage liquidity",
        "matching_algorithm": "SIZE_PRIORITY",
        "liquidity_incentive": True,
    },
    "ILLIQUID": {
        "priority_rule": "PRICE_SIZE_TIME",
        "description": "Price-Size-Time priority for illiquid markets",
        "matching_algorithm": "SIZE_PRIORITY",
        "liquidity_incentive": True,
    },
    "DIRECTIONAL": {
        "priority_rule": "PRICE_TIME_VOLUME",
        "description": "Price-Time with volume consideration",
        "matching_algorithm": "HYBRID",
        "liquidity_incentive": True,
    },
    "HIGH_FREQUENCY": {
        "priority_rule": "PRICE_TIME",
        "description": "Standard priority with pro-rata for large orders",
        "matching_algorithm": "PRO_RATA",
        "liquidity_incentive": False,
    },
}


def get_config():
    """Get the default configuration"""
    return DEFAULT_CONFIG.copy()


def get_regime_policy(regime: str):
    """Get the policy for a specific regime"""
    return REGIME_POLICIES.get(regime, REGIME_POLICIES["NORMAL"])
