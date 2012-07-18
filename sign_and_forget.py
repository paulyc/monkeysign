#!/usr/bin/python
#
# This simple script aims to test the 'monkeysign' library which is
# used in the monkeysign-scan and monkeysign-gen programs.
#
# It is particularly testing the "caff"-like functionality. This
# should do the following steps:
#
# 1. create a temporary keyring (works, in the Keyring class thru GPGME)
# 2. import the key to be signed (the "key"):
#  a) from keyservers or (works, in the monkeysign-scan code through gpg subproc)
#  b) from the regular keyring (works, in fetch_key_from_keyring() thru GPGME)
# 3. import the private key (the "signing key")
#  a) from the regular keyring or (FAIL: GPGME can't export secret keys)
#  b) be able to access the regular keyring as well as the temporary one (works in the monkeysign-scan code, thru gpg subproc)
# 4. sign one or many identities in the temporary keyring, as a local or exportable signature (almost works, both in subproc and GPGME, although the latter gives almost no debugging info)
# 5. (optional) mail those signatures to the relevant identity, encrypted (TODO)

import monkeysign

keyring = monkeysign.Keyring('/tmp/m')

fpr = '73CF7A82A1138982B64FE3DAD1CF7387343CA353'
sign_key = '8DC901CE64146C048AD50FBB792152527B75921E'

keyring.fetch_key_from_keyring(fpr)
keyring.fetch_key_from_keyring(sign_key)
keyring.sign_key_and_forget(fpr, sign_key)
