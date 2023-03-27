# Roo - manages environments and dependencies in R

[![Maturity Level](https://img.shields.io/badge/Maturity%20Level-Under%20Development-orange)](https://img.shields.io/badge/Maturity%20Level-Under%20Development-orange)

# Description

Roo is a python program that handles R dependencies and R environments,
ensuring environment reproducibility that satisfy dependency constraints.
If you are familiar with python poetry or pip it aims at being the same.
While apparently similar to packrat or renv, Roo is way more powerful.

As a data scientist using e.g. RStudio you are unlikely to benefit from Roo,
but if you need to create production R code, it's a much safer choice to
define a consistent and reliable environment of dependencies. It also provides
functionalities that helps in maintaining different environments at the same time.

# Installation

Roo is written in python and requires python 3.8 or above.
It runs on any platform, and it can be installed from pypi with:

    pip install roo

Dependencies will be installed automatically.

# Documentation

- [Rationale](docs/rationale.md)
- [Basic Usage](docs/usage.md)
- [Advanced Usage](docs/advanced.md)
- [Troubleshooting](docs/troubleshooting.md)
