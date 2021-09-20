# Roo - manages environments and dependencies in R

![Build](https://github.com/AstraZeneca/roo/actions/workflows/python.yml/badge.svg)
![Flake8](https://github.com/AstraZeneca/roo/actions/workflows/lint.yml/badge.svg)
[![Maturity Level](https://img.shields.io/badge/Maturity%20Level-Under%20Development-orange)](https://img.shields.io/badge/Maturity%20Level-Under%20Development-orange)

# Description

Roo is a python program that handles R dependencies and R environments, ensuring environment reproducibility
that satisfy dependency constraints. If you are familiar with python poetry or pip it aims at being the same.

## Motivation

Roo was born out of frustration at the current R environment handling tools
that are not up to expected needs when it's time to ensure a reproducible
environment that is guaranteed to have dependencies satisfied. Utilities such
as packrat and renv, and the general status of CRAN, do not favour such
reliability. 

Most R programmers always use the most recent code available on CRAN, but this
is not going to work for validated applications that need a specified environment
that is unchanged even if a reinstallation happens at a later date. While you could
argue that packrat or renv freezes the packages in the current environment,
unfortunately the mechanism with which those packages are discovered to begin
with has potential issues.

### Subdependency conflicts, and why it's a problem

Say for example that you want to install two packages, `A` and `B`. Both depend on
package `C`.  However, `A` depends on `C >= 2`, and `B` depends on `C < 2`. 

It is obvious that there is no version of `C` that satisfies the constraints,
therefore the environment cannot be created. This is an important point that
one wants to be aware of, because validation depends on a reliable and
consistent environment.

There are effective techniques to deal with this so called "dependency hell".
Roo is not as performant as tools such as conda and poetry for python, but it
satisfies the basic need I currently have to ensure the environment is stable,
reproducible, and consistent (of course, assuming that the annotations in the
packages are correct!)

Roo does a lot more than this, and it's basically a work in progress. As a data
scientist you are unlikely to need Roo in your daily work, because Roo is
mostly focused on production-level rather than exploratory coding. However, if time
allows, an R interface will be written to at least install from a roo lock file.

# Requirements and Installation

Roo is written in python and requires python 3.8 or above. 
It runs on any platform, and it can be installed from pypi with:

    pip install roo

Dependencies will be installed automatically.
