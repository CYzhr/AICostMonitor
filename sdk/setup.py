"""
AICostMonitor SDK Setup
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="aicostmonitor",
    version="1.0.0",
    author="AICostMonitor Team",
    author_email="support@aicostmonitor.com",
    description="Zero-intrusion AI API cost tracking SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/CYzhr/AICostMonitor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "openai": ["openai>=1.0.0"],
        "anthropic": ["anthropic>=0.18.0"],
        "langchain": ["langchain-core>=0.1.0"],
        "all": ["openai>=1.0.0", "anthropic>=0.18.0", "langchain-core>=0.1.0"],
    },
    entry_points={
        "console_scripts": [
            "aicm=aicostmonitor.cli:main",
        ],
    },
)
