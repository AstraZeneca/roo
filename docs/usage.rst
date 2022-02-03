Usage
=====

The rproject.toml file
----------------------

All of the configuration of Roo happens in the rproject.toml file.
This file is in TOML format. It's an easy to read format very similar (but
not necessarily equal) to the INI format. Sections are defined with [], and
keys are assigned to values with the equal (=) sign.
Additionally, it's possible to define lists using double square brackets
sections [[]].

Create a basic rproject.toml
----------------------------

You can create a basic initial rproject.toml by issuing::

    $ roo init

This command will create a basic rproject file in the current directory::

    [tool.roo]
    name = "myproject"
    version = "0.1.0"

    [[tool.roo.source]]
    name = "CRAN"
    url = "https://cloud.r-project.org/"


All roo sections must start with the ``tool.roo`` prefix. The first section
defines basic meta information about the package.

The second section ``[[tool.roo.source]]`` contains the first (and for now
only) of many different sources for our packages. By default we use CRAN
mirror on r-project. The name is an arbitrary string, and the url must be
pointing at the CRAN or CRAN-like location.

Adding a new remote source: the tool.roo.source section
-------------------------------------------------------

To add a new source, add a new double-square bracket section, like this::

    [tool.roo]
    name = "myproject"
    version = "0.1.0"

    [[tool.roo.source]]
    name = "CRAN"
    url = "https://cloud.r-project.org/"

    [[tool.roo.source]]
    name = "Internal"
    url = "https://my.internal.address/"

Roo supports two types of remote sources:

- CRAN-like, such as those supported by CRAN itself, and miniCRAN
- Artifactory, which uses a different layout for the Archived packages
  compared to CRAN-like.

The support is transparent. Just use the appropriate URL and roo will detect
which layout the remote source is using.

Note that order is meaningful, but this topic will be discussed in the
priority section.

You can add as many sources as you want, as long as they have different
names.

Configuring a proxy for a source
''''''''''''''''''''''''''''''''

Roo allows to specify a proxy for each of the sources, using the keyword
``proxy``. For example, this configuration will use proxya to connect to CRAN
and proxyb to connect to Internal::

    [[tool.roo.source]]
    name = "CRAN"
    proxy = "http://proxya"
    url = "https://cloud.r-project.org/"

    [[tool.roo.source]]
    name = "Internal"
    proxy = "http://proxyb"
    url = "https://my.internal.address/"

Using priorities
''''''''''''''''

Priorities specify the order of resolutions of packages. It is quite important
to ensure not only reproducibility, but also to prevent potential security
issues.

By default, every source you define has priority zero. The way roo works is that it will
scan all sources, collect all the available packages (each with their own version),
put them into a common pool, and use this pool to look for packages. Of course,
if it is instructed to select the latest, it will pick the latest version that
is available throughout the pool, regardless of its origin.

Now imagine the following scenario: you have a package called ``mypackage``
with version 1.0.0 in your Internal repository. However, you also have CRAN
because many dependencies are there. You create a lock
(we'll examine locks later) to pin your environment today, your Internal version
is the latest, and therefore is selected.

However, you have no "rights" on the name ``mypackage``. It's only on your
internal repository, after all. Another user in the opensource community may
decide to create a package ``mypackage`` and push it on CRAN. As soon as this
user releases, say, version 2.0.0, if you create a lock again, the CRAN version,
rather than the Internal version, will be picked. This obviously bad, because
the two packages have nothing in common except the name.

Priorities are a way to "separate the pools". If a package is found in a higher
priority source, it will be picked regardless of its existence in other sources
with potentially higher version::

    [[tool.roo.source]]
    name = "Internal"
    priority = 1
    url = "https://my.internal.address/"

With this specification, you will keep using the Internal version. You are
effectively shadowing away any module from e.g. CRAN that happens to have a
name you are claiming on your Internal repository.

Defining your environment: tool.roo.dependencies and friends
------------------------------------------------------------

Your program requires dependencies to run. You specify these dependencies
in various sections, each related to a specific category of dependencies.
The ``main`` category is the dependencies that are required for your own
library or program to run, and it's specified like this in ``rproject.toml``::

    [tool.roo.dependencies]
    tibble = "*"

This statement says that you want an environment containing tibble of whatever
version is the latest (hence the "*") available on the sources.

You can specify restrictions. For example, this specification says that you
want tibble at least 3.1 or above::

    [tool.roo.dependencies]
    tibble = ">=3.1"

depending on what's available on the sources, it might be resolved to tibble
3.1.0, 3.1.1 and the like, 3.2.0. 3.2.1 and the like, and so on. Even 4.0.0, if
present, will satisfy the directive. In general, a change in the major number
(the first in the series) means that breaking changes are introduced, so you
want to protect yourself with a directive such as::

    [tool.roo.dependencies]
    tibble = ">=3.1,<4"

which can be expressed with the "compatible operator" tilde (~)::

    [tool.roo.dependencies]
    tibble = "~3.1"

which is read as "the most up-to-date that is compatible with the 3.x series
and is higher than 3.0.x

There are other two categories for dependencies: ``dev`` and ``doc``, each
having a specific section in the rproject.toml file.
These are dependencies that are required by developers and by
documentation writers to do their job (e.g. run test, build the documentation).
For example, you can put testthat in the dev-dependencies::

    [tool.roo.dev-dependencies]
    testthat = "*"

Or knitr or pkgdown in the doc-dependencies::

    [tool.roo.doc-dependencies]
    knitr = "*"

In some cases, this division could be useful, for example to speed up Continuous
Documentation building.

A digression: what about the DESCRIPTION dependencies?
''''''''''''''''''''''''''''''''''''''''''''''''''''''

A common question you might wonder at this point is: are we duplicating
information if we specify the dependencies both here and in the DESCRIPTION
file? The answer is No. While similar, the two specify very different
information.

- The DESCRIPTION file specifies a general description of what your library
  needs in order to run. It's kind of a "request for service" plea.
- The rproject specification specifies which _concrete_ package I want
  in order to actually run. It's a response to the plea above so that
  the library can actually run, for example while we develop.

In terms of object oriented programming, the DESCRIPTION file specifies
an abstract interface, and the rproject is a way to specify and obtain the
concrete implementation of that interface. They are related, but do not
mean the same.

Creating a lock file
--------------------

The rproject.toml specifies a set of version constraints to satisfy when we
download our package. To resolve these constraints, we issue the following
command::

    roo lock

Roo will contact the sources, select the packages satisfying the constraint,
fetch them, examine their DESCRIPTION files, verify their dependency and
constraints, resolve them, and so on until the whole tree is examined and
one specific version of each package has been picked. The chosen version
will be written near the selected package. If three dots (...) are shown, it
means that the package has already been found earlier and a version has
already been chosen.

This phase is where issues with your environment may be discovered.
See the motivation document for a clear explanation why this step may
fail to reveal an environment that might be broken.

The resulting tree will be written into a roo.lock file. This file file
should be committed to your VCS (e.g. git) repository.

Once you have a lock, you don't need to create it again unless you want
to upgrade your environment for whatever reason. New developers simply can
create the environment using ``roo install``, as we'll see in a moment.

Installing the lock
-------------------

Once the lock file is created, you can install its content with::

   roo install

The command will download and compile the packages in the correct order.


What to do if the compilation fails
-----------------------------------

Sometimes the compilation of a package may fail. There could be many reasons,
from an improperly setup R tools, to a missing library on your machine.
Compilation of the packages is outside Roo. Internally, all Roo does is
to invoke ``R CMD INSTALL`` on the package. You can get information about the
compilation process by performing::

   roo install --verbose-build

This may give you some information about the reasons behind the failure.
Note that Roo never downloads binary packages, so it will always need
compilation from sources. The reason is that binary packages are only
available for the latest version only, not for the archived ones.

Using the newly created environment
-----------------------------------

When you don't specify otherwise, Roo creates an environment called "default".
This environment contains all the compiled packages. You can see the currently
available environments by issuing::

    $ roo environment list
    * default (3.6.0)

Note that you _must_ be in the directory where you ran ``roo install``: Roo
creates a .Rprofile file in that directory that will be run by your R to
address you to the currently enabled environment. If you run ``R``, a message
will advertise the currently enabled environment::

    $ R

    R version 3.6.0 (2019-04-26) -- "Planting of a Tree"
    <...>

    Using environment default (R version: 3.6.0, platform: x86_64-apple-darwin15.6.0)
    >

You can create as many environments as you want, as long as they have different
names. Each environment may contain different versions of the library. This
is very useful in case you must maintain different versions of your application,
each needing a different environment, or if you want to test your application
with different versions of R.

Using multiple environments is an advanced topic and will be discussed later.

Other useful roo commands
-------------------------

Exporting the lock file
'''''''''''''''''''''''

You can export your lockfile to a different format. Currently supported formats
are csv and packrat::

    $ roo export lock csv myenv.csv

Searching for a package on the sources
''''''''''''''''''''''''''''''''''''''

You can search for the available versions of a package by issuing::

    $ roo package search testthat

This will provide a list of all the available versions of ``testthat`` on
the various sources you specified in the rproject file. The currently active
(most recent, not in archive) version will also be specified.
