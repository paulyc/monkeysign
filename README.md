Monkeysign: OpenPGP Key Exchange for Humans
===========================================

monkeysign is a tool to overhaul the OpenPGP keysigning experience and
bring it closer to something that most primates can understand.

The project makes use of cheap digital cameras and the type of bar
code known as a QRcode to provide a human-friendly yet still-secure
keysigning experience.

No more reciting tedious strings of hexadecimal characters.  And, you
can build a little rogue's gallery of the people that you have met and
exchanged keys with! (Well, not yet, but it's part of the plan.)

Monkeysign was written by Jerome Charaoui and Antoine Beaupré and is
licensed under GPLv3.

Features
---------

 * commandline and GUI interface
 * GUI supports exchanging fingerprints with qrcodes
 * print your OpenPGP fingerprint on a QRcode
 * key signature done on a separate keyring
 * signature sent in a crypted email to ensure:
   1. the signee controls the signed email
   2. the signee really controls the key
 * local ("non-exportable") signatures
 * send through local email server or SMTP

Installing
----------

Monkeysign should be available in Debian and Ubuntu, but can also
easily be installed from source.

### Requirements

The following Python packages are required for the GUI to work.

    python-qrencode python-gtk2 python-zbar python-zbarpygtk

If they are not available, the commandline signing tool should still
work but doesn't recognize QR codes.

Of course, all this depends on the GnuPG program.

### In Debian / Ubuntu

Monkeysign is now in Debian, since Jessie (and backported to Wheezy)
and Ubuntu (since Trusty 14.04LTS). To install it, just run:

    apt-get install monkeysign

### From git

You can fetch monkeysign with git:

    git clone git://git.monkeysphere.info/monkeysign

### From source

The source tarball is also available directly from the Debian mirrors
here:

    http://cdn.debian.net/debian/pool/main/m/monkeysign/

The `.tar.gz` file has a checksum, cryptographically signed, in the
`.dsc` file.

### Installing from source

To install monkeysign, run:

    sudo ./setup.py install --record=install.log

Running
-------

The graphical interface should be self-explanatory, it should be in
your menus or call it with:

    monkeyscan

The commandline interface should provide you with a complete help file
when called with `--help`:

    monkeysign --help

For example, to sign a given fingerprint:

    monkeysign 90ABCDEF1234567890ABCDEF1234567890ABCDEF

This will fetch the key from your keyring (or a keyserver) and sign it
in a temporary keyring, then encrypt the signature and send it in an
email to the owner of the key.

Caveats
-------

 * There are numerous bugs with odd keys and GnuPG corner cases. Most
   of them should be documented on the Debian BTS here:
   https://bugs.debian.org/monkeysign

 * Running monkeysign in `--debug` mode and sending the output to a
   public forum may leak public or even private key material in some
   circumstances. Special efforts have been made so that private key
   material is never output to the screen, but you can never be too
   careful: look at the output before you send it.

 * The graphical interface isn't as complete as the commandline. A few
   features are missing and it is mostly a proof of concept at this
   point which works, but has a few rough edges. In particular, if you
   have a high resolution camera, the camera window may fill your
   screen completely, in which case you may want to change the
   resolution beforehand using the following commands:

        sudo apt-get install v4l-utils
        v4l2-ctl --set-fmt-video=width=640,height=480,pixelformat=1

   See https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=723154 for
   more information about this specific problem.

 * Both the graphical and commandline interface assume you are fairly
   familiar with SMTP configuration or had an administrator setup a
   mailserver on your machine for email delivery.

Support
-------

Discussions, questions and issues can be brought up on the mailing
list, <monkeysphere@lists.riseup.net>. See the [CONTRIBUTING.md][]
file for more information about how to file bugs.

[CONTRIBUTING.md]: CONTRIBUTING.md

Similar projects
----------------

 * [GPG for Android][] (of the [Guardian project][]) will import
   public keys in your device's keyring when they are found in
   QRcodes, so it should be able to talk with Monkeysign, but this
   remains to be tested. ([Github project][])
 
 [GPG for Android]: https://guardianproject.info/code/gnupg/
 [Guardian project]: https://guardianproject.info/
 [Github project]: https://github.com/guardianproject/gnupg-for-android

 * [OpenPGP keychain][], a fork of [APG][], has support for exporting
   and importing fingerprints in QRcode and NFC. Interoperability also
   needs to be tested. ([Github project][2])

 [OpenPGP keychain]: http://sufficientlysecure.org/index.php/openpgp-keychain/
 [APG]: http://www.thialfihar.org/projects/apg/
 [2]: https://github.com/dschuermann/openpgp-keychain

 * [Gibberbot][] (also of the [Guardian project][]) can exchange OTR
   fingerprints using QRcodes. ([Github project][3])

 [Gibberbot]: https://guardianproject.info/apps/gibber/
 [3]: https://github.com/guardianproject/Gibberbot
