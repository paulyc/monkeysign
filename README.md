Monkeysign: OpenPGP Key Exchange for Humans
===========================================

monkeysign is a tool to overhaul the OpenPGP keysigning experience and
bring it closer to something that most primates can understand.

The project makes use of cheap digital cameras and the type of bar
code known as a QRcode to provide a human-friendly yet still-secure
keysigning experience.

No more reciting tedious strings of hexadecimal characters.  And, you
can build a little rogue's gallery of the people that you have met and
exchanged keys with!

Monkeysign was written by Jerome Charaoui and Antoine Beaupré and is
licensed under GPLv3.

Requirements
------------

The following Python packages are required for the GUI to work.

 * python-qrencode
 * python-gtk2
 * python-zbar
 * python-zbarpygtk

If they are not available, the commandline signing tool should still
work but doesn't recognize QR codes.

Of course, all this depends on the GnuPG program.

Installing
----------

To install monkeysign, run:

    setup.py install

There is also a Debian package available.

Caveats
-------

 * There are numerous bugs with odd keys and GnuPG corner cases. Most
   of them should be documented on the Debian BTS here:
   https://bugs.debian.org/monkeysign

 * Running monkeysign in `--debug` mode and sending the output to a
   public forum may leak public or even private key material in some
   circumstances. Special efforts have been made so that private key
   material is never output to the screen, but you can never be too
   careful.

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
