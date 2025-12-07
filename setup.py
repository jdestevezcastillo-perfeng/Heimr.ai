# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="heimr-ai",
    version="0.1.0",
    author="Juan Estevez Castillo",
    author_email="jd.estevezcastillo@gmail.com",
    description="AI-Powered Load Test Analysis & Root Cause Explanation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://heimr.ai",
    project_urls={
        "Bug Tracker": "https://github.com/jdestevezcastillo-perfeng/Heimr.ai/issues",
        "Documentation": "https://github.com/jdestevezcastillo-perfeng/Heimr.ai/blob/main/docs/WIKI.md",
        "Source Code": "https://github.com/jdestevezcastillo-perfeng/Heimr.ai",
    },
    packages=find_packages(exclude=[
        "tests", "tests.*",
        "scripts", "scripts.*",
        "website", "website.*",
        "demos", "demos.*",
        "load-tests", "load-tests.*",
        "LOCAL", "LOCAL.*"
    ]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Software Development :: Testing",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        # Core data processing
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        # HTTP client for observability integrations (Prometheus, Loki, Tempo)
        "requests>=2.28.0",
        # YAML config file support
        "pyyaml>=6.0",
    ],
    extras_require={
        # LLM providers - install only what you need
        # Note: "openai" package also works for local Ollama (OpenAI-compatible API)
        "openai": ["openai>=1.0.0"],
        "anthropic": ["anthropic>=0.18.0"],
        "llm": [
            "openai>=1.0.0",
            "anthropic>=0.18.0",
        ],
        "all": [
            "openai>=1.0.0",
            "anthropic>=0.18.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",

            "mkdocs-material>=9.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "heimr=heimr.cli:main",
        ],
    },
    keywords=[
        "load-testing",
        "performance",
        "jmeter",
        "k6",
        "gatling",
        "locust",
        "anomaly-detection",
        "root-cause-analysis",
        "llm",
        "prometheus",
        "observability",
    ],
    include_package_data=True,
)
