# Changelog

## 0.17.0

- #84 Change DESCRIPTION parser to be more robust against real DESCRIPTION files
- #81 Update documentation so that it's in markdown format

## 0.16.0

- #79 Fixed incorrect checkmark with VCS installation
- #78 Add "--fix-changed-hash" to roo lock

## 0.15.0

- #70 Added cache remove and cache list. These commands may not work unless you recreate the cache.
- #74 ensure that a package is considered present only if the DESCRIPTION file is present.

## 0.14.0

- #70 Improved error message in case of incorrect environment
- #69 Ensure that the conservative flag is taken from the old lock if not s…
- #68 Improved roo package search ui visual style
- #67 Added run command
- #66 Add Switch command to change R version on mac

## 0.13.2

- PR #64 Added base as core dependency

## 0.13.1

- PR #56 Ensure that discovery of R versions on linux is done invoking the command, rather than Rcmd

## 0.13.0

- #52 Added roo environment options to see the available R versions to use when generating an environment
- #50 Added --r-version to environment init to specify the R version to use for the environment


## 0.12.1

- #45 Fixed restrictive detection of R path on linux machines

## 0.12.0

- #43 Added Documentation on usage
- #42 Add local source to use CRAN-like entries on our local disk
- #40 Allow to specify priority in sources
- #38, #39 Improve concurrency issues
- #37 Removed user notifier in favor of full rich console
- #35 Improved logic for automatic detection of R path
- #36 Handle dependencies with R of different versions (support R 4)
- #33 Verify the version of R in the init file, and use the environment data for version info
- #30 Fixed: roo install installs on default environment
- #28 environment init with no value will raise confusing exceptions

## 0.11.0

- First public release
