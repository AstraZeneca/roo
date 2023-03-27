## Why roo?

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
