
.. include:: include/links.rst

.. _developer_install:

======================
Developer Installation
======================

The following provides guidance on installing the code from source for
development purposes.

Setup a clean python environment
================================

This is the same as described for a user installation; see :ref:`environment`.

Fork the code
=============

Except for a few maintainers, code development should be done in forks of the
code base.  To fork the code, go to `GitHub
<https://github.com/pypeit/PypeIt>`__ and click the "Fork" button at the upper
right.  You should keep the name of the repository (``PypeIt``) the same.

When you fork the code, you will be asked if you want to only copy the
``release`` branch (default).  If you uncheck this box, you will get *all* of
the current branches, which is almost certainly not something you want to do.
See below for one way to add the ``develop`` branch to your repo.

Finally, you are **strongly** encouraged to add branch protection rules for both
the ``release`` and ``develop`` branches in your fork (these rules are *not*
inherited from the main repository).

Local Install
=============

To install from source, first create a local clone of your fork:

.. code-block:: console

    git clone https://github.com/{github_handle}/PypeIt.git

This will create a ``PypeIt`` directory at the location the command above was
executed.  Then install the code, including the development dependencies, using
``pip`` (even if you're in a conda environment):

.. code-block:: console

    cd PypeIt
    pip install -e ".[dev]"

This (specifically the ``-e`` option) creates an "editable" installation, which
means that any changes you make in the repository directory tree will become
immediately available the next time the code is imported. Including the
``[dev]`` set of optional dependencies ensures that all of the tools you need to
test and build PypeIt are installed. (Again, note that you may or may not need
the quotes above depending on your shell, and that you should avoid cutting and
pasting these commands into a terminal window.)

Connect your fork to the main repository
========================================

To ensure you are up-to-date with the main repository, you should add it as a
remote:

.. code-block:: console

    % git remote -v
    origin	https://github.com/{github_handle}/PypeIt.git (fetch)
    origin	https://github.com/{github_handle}/PypeIt.git (push)
    % git remote add upstream https://github.com/pypeit/PypeIt.git
    % git remote -v
    origin	https://github.com/{github_handle}/PypeIt.git (fetch)
    origin	https://github.com/{github_handle}/PypeIt.git (push)
    upstream	https://github.com/pypeit/PypeIt.git (fetch)
    upstream	https://github.com/pypeit/PypeIt.git (push)

Updating your fork
==================

To update your fork so that it will recognize changes in the main repository,
run:

.. code-block:: console

    % git fetch upstream

Do this often!

Checkout a remote branch and add it to your fork
================================================

The most obvious application of this is for your first checkout of the
``develop`` branch.  But you can do this with any branch.  The steps are (1)
update your repo, (2) checkout the upstream branch, (3) push it to your fork
(and change its tracking):

.. code-block:: console

    % git fetch upstream
    % git checkout -b develop upstream/develop
    % git push -u origin develop




Merging changes to an upstream branch
=====================================

To update your release


Merging changes to an upstream branch
=====================================



