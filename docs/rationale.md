# Rationale

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

## Subdependency conflicts, and why it's a problem

Say for example that you want to install two packages, ``A`` and ``B``.
Both depend on package ``C``.  However, ``A`` depends on ``C >= 2``, and ``B``
depends on ``C < 2``.

It is obvious that there is no version of ``C`` that satisfies the constraints,
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

### Isn't CRAN supposed to handle this issue?

CRAN has a build process to check submitted packages. In the R world,
the approach to dependency management is generally to target a "freeze" of
CRAN at a given date. This approach cannot work for many reasons:

- As the number of packages increases, it's impossible to guarantee any sort
  of consistency, even if it were achievable in the first place. I am highly
  skeptical of a system that requires all constraints in a set of more than
  9000 (and counting) packages to be all satisfied, and kept satisfied.
- When developing complex applications, you will be forced to mix and match
  different libraries, possibly from different sources, or add new libraries
  on demand. Some of these libraries may not work in the newest version, and
  you might have to use older versions.
- It cannot support simultaneously two or more version of the language.
  For example, if you upgrade your package to use R 4, you must discontinue
  development for R 3 as a result.

No other language uses the CRAN approach. In fact, tools like Pipenv, npm,
Poetry, cargo, all follow a very liberal approach to dependency management,
and just ensure that the environment you create is satisfied by checking the
constraints for being all satisfied by the selected packages.

### Why Roo isn't as good as other package managers

Roo at the moment is unable to find a possible solution that satisfies all
constraints, all by itself. This is the so called "SAT problem" or satisfiability
problem: ensure that a set of conditions are all True.

Imagine that Roo starts scouting the dependency tree, and downloads a package A
that requires a version of B that is not the one we already picked and installed.
There are three approaches to solve this issue:

1. uninstall B and install a compatible version.
2. backtrack, pick a different version of A, consider all the various options,
   and pick a version of both A and B that are optimal
3. Stop and cry.

The first option is what traditional R tools like ``install.packages`` would do.
This is wrong, because by uninstalling and upgrading B, we might ensure we
satisfy A, but also silently break the other dependency that was the reason
why we picked B in the first place.

The second option is (more or less) what tools like conda, pipenv, poetry etc
do. They are very smart and do whatever it takes to "thread the needle" and
pick the right combination of versions that are all compatible, or die trying.
I say more or less, because they don't really backtrack. They just look at the
whole set of constraints and available versions, pick a combination of versions
that satisfies the whole lot, then proceed with it.

The third option is what Roo does. It will require assistance, and you will
basically be forced to find the right combination by hand, but at least it
won't give you a silently broken environment. Why isn't Roo smart to find the
right solution? Because it requires an algorithm called "SAT solver" and I am
not smart enough to implement it or use an external library for it.
I'll get there though.
