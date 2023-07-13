# Advanced usage

## Working with multiple, independent environments

Roo supports multiple environment within the context of the same project.

Imagine the following scenario: you are developing a library version 2.0, and this
library has a set of dependencies. You are using this environment to develop.

Suddenly, a support request comes in for version 1.0. You need to reproduce the bug
in 1.0 to verify it, and hopefully find a solution. Obviously. version 1.0 used a
different set of dependencies (or even a different version of R), and you also
don't want to throw away the environment for 2.0.

With roo, you can switch and manage the two (or more) environments easily. First, create
a new environment

    $ roo environment init v1
    Initialised and enabled environment v1

This will create a new environment named "v1". You can see your environments with:

    $ roo environment list
    * v1 (4.0.4)
    default (4.0.4)

Note how we now have two environments. The default, which is the one you created when
you did your first initialisation, and the new one, called "v1". This new environment
currently contains no packages. Also note how one environment uses

The asterisk in front of the "v1" name means that the environment is currently activated.
This means that `roo install` will install packages in this environment from now on.

You can now check out your previous git branch for version 1.0, and install the dependencies
from the lock at that point in time

    $ roo install

The packages will be downloaded, compiled, and installed in this environment.

When you are done fixing the bug, you can switch back to the previous environment using

    $ roo environment enable default
    Environment default enabled

if you want, you can also cleanup the "v1" environment:

    $ roo environment remove v1

## Using environments associated to different versions of R

If you specify an R version at `roo environment init`, the environment will be
bound to that version of R. This means that `roo install` will use that version of R
for its compilation and installation process. Of course, you must have that version
of R installed on your machine.

    $ roo environment init --r-version 3.6.0 oldenv

You can see which R versions are available on your machine using `roo environment options`

    $ roo environment options
      3.6.0 /Library/Frameworks/R.framework/Versions/3.6
    * 4.0.4 /Library/Frameworks/R.framework/Versions/4.0

Some caveats need to be explained about this functionality::

- The requested version of R will only be used if you use `roo install` or `roo run`.
  If you just invoke R from the command line, you will still get the one that your
  command line interface believes to be the "current one".
- On macOS, it's not possible to have multiple version of R *active* at the same time.
  You can only have one. See the macOS-only command `roo rswitch` for details.


## Query packages information from the sources

You can query the sources defined on your rproject file using the `roo package search`:

    $ roo package search dplyr
    🌍 CRAN (https://cloud.r-project.org/)
      🌟 dplyr 1.1.1 (Active)
      📦 dplyr 0.1.1
      📦 dplyr 0.1.2


## Exporting roo lock file to renv or packrat format

You can export your lockfile to a different format. Currently supported formats
are csv, renv and packrat::

    $ roo export lock csv myenv.csv

## Using git to retrieve a dependency instead of a source

You can specify a dependency using git, instead of the sources, in your rproject.toml file. Example:

    [tool.roo.dependencies]
    qscheck = { git = "https://github.com/AstraZeneca/qscheck.git" }

Note that there is no way to rely on the version of the package at `roo lock` time.
The version can only be determined at `roo install`. The reason is that the content
of the repository can change between the time the lock is created and the time
the lock is installed.

## Using roo on github actions and other CI

The `roo install` command is designed to help the user imn recreating
the lock if it is desynchronized with the current rproject specification.
This is convenient for the user, but for CI machines that need to create the
environment this may be problematic. Imagine the scenario where a developer
commits the rproject.toml but not the roo.lock. Using `roo install`, the CI
machine will recreate the lock and install the packages, but in reality the
correct course of action would be to let the user know something is odd.

The command `roo ci` does precisely this task. It is exactly like `roo install`,
except that it will fail if a desynchronization is detected between the two files.
