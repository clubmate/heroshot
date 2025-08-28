"""
Setup script for HeroShot
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="heroshot",
    version="0.1.0",
    author="HeroShot Team",
    author_email="",
    description="AI-powered video processing pipeline for hero shot extraction and style transformation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/clubmate/heroshot",
    packages=find_packages(),
    package_dir={"heroshot": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Content Creators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "pre-commit>=3.0.0",
        ],
        "gpu": [
            "torch[gpu]>=2.0.0",
            "xformers>=0.0.20",
        ],
    },
    entry_points={
        "console_scripts": [
            "heroshot=src.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "heroshot": ["configs/*.yaml"],
    },
    zip_safe=False,
    keywords="video processing, AI, computer vision, diffusion models, style transfer",
)