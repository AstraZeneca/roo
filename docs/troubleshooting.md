# Troubleshooting

In this section, we'll address the commonly occurring issues we have found
while using Roo.

## On Windows, roo fails when trying to uninstall a package

This problem arises from the fact that RStudio is running. On Windows, files
that are used by one process cannot be deleted. If RStudio is using that file,
Roo will not be able to delete it. To solve, close RStudio and try again.
If you still can't delete the package, another process may be using it
(possibly a background process), and it might require some investigation.

As a very last resort, try rebooting your machine.
