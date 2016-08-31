Bug reports
===========

We want you to report bugs you find in Monkeysign. It's an important
part of contributing to a project, and all bug reports will be read
and replied to politely and professionnally.

Bugs used to be tracked with the [bugs-everywhere][] package, but this
has proven to be too difficult to use and not transparent enough to
most users, so we are now using [Gitlab][], where new bug reports
should be sent.

 [bugs-everywhere]: http://bugseverywhere.org/
 [Gitlab]: https://0xacab.org/monkeysphere/monkeysign/issues

You can also report bugs by email over the [Debian BTS][], even if you
are not using Debian. Use the `reportbug` package to report a bug if
you run Debian (or Ubuntu), otherwise send an email to
`submit@bugs.debian.org`, with content like this:

    To: submit@bugs.debian.org
    From: you@example.com
    Subject: fails to frobnicate
    
    Package: monkeysign
    Version: 1.0
      
    Monkeysign fails to frobnicate.
    
    I tried to do...
    
    I was expecting...
    
    And instead I had this backtrace...
    
    I am running Arch Linux 2013.07.01, Python 2.7.5-1 under a amd64
    architecture.

See also the [complete instructions][] for more information on how to
use the Debian bugtracker. You can also
[browse the existing bug reports][] there.

 [Debian BTS]: http://bugs.debian.org/
 [complete instructions]: http://www.debian.org/Bugs/Reporting
 [browse the existing bug reports]: http://bugs.debian.org/monkeysign

Patches
=======

Patches can be submitted through [merge requests][] on the
[Gitlab site][].

[Gitlab site]: https://0xacab.org/monkeysphere/monkeysign/
[merge requests]: https://0xacab.org/monkeysphere/monkeysign/merge_requests

If you prefer old school, offline email systems, you can also use the
Debian BTS, as described above, or send patches to the mailing list
for discussion.

Unit tests
==========

Unit tests should be ran before sending patches. They can be ran with
`./test.py`.

It is possible that some keys used in the tests expire. The built-in
keys do not have specific expiry dates, but some keys are provided to
test some corner cases and *those* keys may have new expiration dates.

To renew the keys, try:

    mkdir ~/.gpg-tmp
    chmod 700 ~/.gpg-tmp
    gpg --homedir ~/.gpg-tmp --import 7B75921E.asc
    gpg --homedir ~/.gpg-tmp --refresh-keys 8DC901CE64146C048AD50FBB792152527B75921E
    gpg --homedir ~/.gpg-tmp --export-options export-minimal --armor --export 8DC901CE64146C048AD50FBB792152527B75921E > 7B75921E.asc

It is also possible the key is just expired and there is no
replacement. In this case the solution is to try and find a similar
test case and replace the key, or simply disable that test.

Release process
===============

 * make sure tests pass (`./test.py`)
 * update version in `monkeysign/__init__.py` and run `dch -i -D unstable`
 * signed and annotated tag (`git tag -s -u keyid x.y`)
 * build Debian package (`git-buildpackage`)
 * install and test Debian package (`dpkg -i ../build-area/monkeysign_*.deb`)
 * upload Debian package
 * push commits and tags to the git repository
 * add announcement on website and mailing list <monkeysphere@lists.riseup.net>

Support schedule
================

The 2.0.x branch will be featured in Debian Jessie and will therefore
be maintained for security fixes for the lifetime of that release. New
development will then happen on the 3.0 branch, and some features may
be backported in 2.x point releases.
