#!/usr/bin/env python3
"""
Setup configuration for asm8085-lsp Language Server.
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = (
    readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""
)

setup(
    name="asm8085-lsp",
    version="0.2.1",
    description="Language Server Protocol implementation for Intel 8085 assembly language",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Resty",
    author_email="morganischkalt@gmail.com",
    url="https://github.com/Restythecake/asm8085-lsp",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies - uses only Python standard library
    ],
    entry_points={
        "console_scripts": [
            "asm8085-lsp=asm8085_lsp:main",
        ],
    },
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
        "Topic :: Software Development :: Assemblers",
        "Topic :: Software Development :: Compilers",
        "Topic :: Text Editors :: Integrated Development Environments (IDE)",
    ],
    keywords="8085 assembly lsp language-server intel microprocessor ide",
    project_urls={
        "Bug Reports": "https://github.com/Restythecake/asm8085-lsp/issues",
        "Source": "https://github.com/Restythecake/asm8085-lsp",
        "Documentation": "https://github.com/Restythecake/asm8085-lsp#readme",
    },
)
