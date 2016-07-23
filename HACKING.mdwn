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

Bug tracking
============

Bug tracking happens in this git repository using `be`
([bugs-everywhere][]). [Full documentation][] is available online, but
here's a short overview:

    # list bugs
    be list
    # new bug
    be new "here's a summary"
    # describe / comment on a bug
    be comment 618/d0d0
    # register all changes in git
    be commit

A more convenient HTML view can be served using:

    be html

Use the `--port` option if port 8000 is busy with icecast.

 [bugs-everywhere]: http://bugseverywhere.org/
 [Full documentation]: http://docs.bugseverywhere.org/

There are also bugs reported by email over the [Debian BTS][]. See the
[website][] for more information.

 [Debian BTS]: http://bugs.debian.org/monkeysign
 [website]: http://web.monkeysphere.info/monkeysign/#index4h2
