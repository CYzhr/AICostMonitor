#!/usr/bin/env python3
"""AICostMonitor SDK - AI API成本追踪工具"""

from setuptools import setup, find_packages

setup(
    name="aicostmonitor",
    version="1.0.0",
    description="Track AI API costs automatically - OpenAI, Anthropic, Google, and more",
    author="AICostMonitor",
    author_email="support@aicostmonitor.com",
    url="https://github.com/CYzhr/AICostMonitor",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.28.0"
    ],
    extras_require={
        "openai": ["openai>=1.0.0"],
        "anthropic": ["anthropic>=0.3.0"],
        "all": ["openai>=1.0.0", "anthropic>=0.3.0"]
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="ai, openai, anthropic, cost, monitoring, api, tracking",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
)
