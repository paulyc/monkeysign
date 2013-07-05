# -*- coding: utf-8 -*-

import sys

from monkeysign.ui import MonkeysignUi

class MonkeysignCli(MonkeysignUi):
    """Sign a key in a safe fashion.

This command should sign a key based on the fingerprint or user id
specified on the commandline, encrypt the result and mail it to the
user. This leave the choice of publishing the certification to that
person and makes sure that person owns the identity signed. This
script assumes you have gpg-agent configure to prompt for passwords."""

    # override default options to allow passing a keyid
    usage = usage='%prog [options] <keyid>'
    epilog='<keyid>: a GPG fingerprint or key id'

    def main(self):
        """main code execution loop

        we expect to have the commandline parsed for us
        """

        if self.pattern is None:
            sys.exit('wrong number of arguments')

        # 1. fetch the key into a temporary keyring
        self.find_key()

        # 2. copy the signing key secrets into the keyring
        self.copy_secrets()

        self.warn("Preparing to sign with this key\n\n%s" % self.signing_key)

        # 3. for every user id (or all, if -a is specified)
        # 3.1. sign the uid, using gpg-agent
        self.sign_key()

        # 3.2. export and encrypt the signature
        # 3.3. mail the key to the user
        # 3.4. optionnally (-l), create a local signature and import in
        #local keyring
        self.export_key()

        # 4. trash the temporary keyring
        # implicit

    def yes_no(self, prompt, default = None):
        ans = raw_input(prompt)
        while default is None and ans.lower() not in ["y", "n"]:
            ans = raw_input(prompt)
        if default: return default
        else: return ans.lower() == 'y'

    def choose_uid(self, prompt, key):
        """present the user with a list of UIDs and let him choose one"""
        allowed_uids = []
        for uid in key.uidslist:
            allowed_uids.append(uid.uid)

        pattern = raw_input(prompt)
        while pattern not in allowed_uids and not pattern.isdigit() and int(pattern)-1 not in range(0,len(allowed_uids)):
            print "invalid uid"
            pattern = raw_input(prompt)
        if pattern.isdigit():
            pattern = allowed_uids[int(pattern)-1]
        return pattern
