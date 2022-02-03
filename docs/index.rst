.. Roo documentation master file, created by
   sphinx-quickstart on Wed Feb  2 14:25:22 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Roo - manages environments and dependencies in R
================================================

Description
-----------

Roo is a python program that handles R dependencies and R environments,
ensuring environment reproducibility that satisfy dependency constraints.
If you are familiar with python poetry or pip it aims at being the same.

While apparently similar to packrat or renv, Roo is way more powerful.
As a data scientist using e.g. RStudio you are unlikely to benefit from Roo,
but if you need to create production R code, it's a much safer choice to
define a consistent and reliable environment of dependencies.

Welcome to Roo's documentation!
===============================

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   rationale.rst
   installation.rst
   usage.rst
   advanced.rst
   troubleshooting.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
