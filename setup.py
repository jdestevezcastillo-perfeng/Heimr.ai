from setuptools import setup, find_packages

setup(
    name="heimr",
    version="0.1.0",
    description="AI-Powered Load Test Analysis Tool",
    author="Heimr.ai",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "pyod",
        "scikit-learn",
        "requests",
        "openai",
        "anthropic"
    ],
    entry_points={
        "console_scripts": [
            "heimr=heimr.cli:main",
        ],
    },
    python_requires=">=3.8",
)
