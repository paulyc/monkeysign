Monkeysign: OpenPGP key exchange for humans
===========================================

what is PGP
-----------

   * signs
   * encrypt
   * certifies

what is the monkeysphere
------------------------

   * get out of the CA cartel
   * supports SSH and HTTPS for now, more to come
   * usable right now!

why u no PGP???
---------------

 * key problem with PGP: the web of trust

critical monkeysign features
----------------------------

 * display and scan qrcode-encoded fingerprints - no more typing!
 * caff replacement:

  * signs in a separate keyring
  * mails the signatures to each email so that email is verified...
  * ... and the signed person gets to decide if certification is public

and more!
---------

   * SMTP support (TLS, user auth)
   * local signatures
   * unit tests
   * GUI and command line interface
   * modular python architecture instead of single perl script
   * packaged in Debian, install from git on other OS, packages welcome

help needed!
------------

 * wrote this from scratch
 * python-gnupg re-implementation, help needed for merge
 * translations
 * testing / bug reports / patches welcome!
