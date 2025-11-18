from setuptools import setup, find_packages

setup(
    name="adaptive-matching-engine",
    version="0.1.0",
    description="Adaptive heap-based order matching engine for dynamic market regimes",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-benchmark>=3.4.0",
            "matplotlib>=3.5.0",
        ]
    },
)
