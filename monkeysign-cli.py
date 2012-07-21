#!/usr/bin/env python

"""Sign a key in a safe fashion.

This command should sign a key based on the fingerprint or user id
specified on the commandline, encrypt the result and mail it to the
user. This leave the choice of publishing the certification to that
person and makes sure that person owns the identity signed. This
script assumes you have gpg-agent configure to prompt for passwords.
"""
# see the optparse below for the remaining arguments

import sys
from optparse import OptionParser, TitledHelpFormatter
from gpg import Keyring, TempKeyring

def parse_args():
    """parse the commandline arguments"""
    parser = OptionParser(description=__doc__, usage='%prog [options] <keyid>', 
                          epilog='<keyid>: a GPG fingerprint or key id')
    parser.add_option('-d', '--debug', dest='debug', default=False, action='store_true',
                      help='request debugging information from GPG engine (lots of garbage)')
    parser.add_option('-v', '--verbose', dest='verbose', default=False, action='store_true',
                      help='explain what we do along the way')
    parser.add_option('-n', '--dry-run', dest='dryrun', default=False, action='store_true',
                      help='do not actually do anything')
    parser.add_option('-u', '--user', dest='user', help='user id to sign the key with')
    parser.add_option('-a', '--all', dest='alluids', default=False, action='store_true',
                      help='sign all uids on key')
    parser.add_option('-l', '--local', dest='local', default=False, action='store_true',
                      help='import in normal keyring a local certification')
    parser.add_option('-k', '--keyserver', dest='keyserver',
                      help='keyserver to fetch keys from')

    return parser.parse_args()

class MonkeysignCli():

    # the options that determine how we operate, from the parse_args()
    options = {}

    # the key we are signing, can be a keyid or a uid pattern
    pattern = None

    # the regular keyring we suck secrets and maybe the key to be signed from
    keyring = None

    # the temporary keyring we operate in
    tmpkeyring = None

    # the fingerprints that we actually signed
    signed_fprs = None

    def main(self,pattern, options = {}):
        """main code execution loop

        we expect to have the commandline parsed for us

        General process
        ===============

        1. fetch the key into a temporary keyring
        1.a) if allowed (@todo), from the keyservers
        1.b) from the local keyring (@todo try that first?)
        2. copy the signing key secrets into the keyring
        3. for every user id (or all, if -a is specified)
        3.1. sign the uid, using gpg-agent
        3.2. export and encrypt the signature
        3.3. mail the key to the user
        3.4. optionnally (-l), create a local signature and import in
        local keyring
        4. trash the temporary keyring
        """
        self.options = options
        self.pattern = pattern
        self.signed_fprs = []

        if options.user is None:
            raise NotImplementedError('no default key detection code, please provide a user to sign keys with -u')
        if options.local:
            raise NotImplementedError('local key signing not implemented yet')
        if not options.alluids:
            raise NotImplementedError('please use -a for now')

        # setup environment and options
        self.tmpkeyring = tmpkeyring = TempKeyring()
        self.keyring = Keyring() # the real keyring
        if options.debug:
            self.tmpkeyring.context.debug = sys.stderr
        if options.keyserver is not None: tmpkeyring.context.set_option('keyserver', options.keyserver)

        # 1. fetch the key into a temporary keyring
        self.find_key()

        # 2. copy the signing key secrets into the keyring
        self.copy_secrets()

        # 3. for every user id (or all, if -a is specified)
        # @todo select the uid
        # 3.1. sign the uid, using gpg-agent
        self.sign_key()

        # 3.2. export and encrypt the signature
        self.export_key()

        # 3.3. mail the key to the user
        self.mail_key()

        # 3.4. optionnally (-l), create a local signature and import in
        #local keyring
        # @todo

        # 4. trash the temporary keyring
        if options.verbose: print >>sys.stderr, 'deleting the temporary keyring ', tmpkeyring.tmphomedir
        # implicit

    def find_key(self):
        """find the key to be signed somewhere"""
        self.keyring.context.set_option('export-options', 'export-minimal')
        if self.options.keyserver:
            # 1.a) if allowed, from the keyservers
            if options.verbose: print >>sys.stderr, 'fetching key %s from keyservers' % self.pattern
            if self.options.dryrun: return True

            if not re.search('^[0-9A-F]*$', self.pattern): # this is not a keyid
                # the problem here is that we need to implement --search-keys, and it's a pain
                raise NotImplementedError('please provide a keyid or fingerprint, uids are not supported yet')

            if not self.tmpkeyring.fetch_keys(self.pattern) \
                    and not self.tmpkeyring.import_data(self.keyring.export_data(self.pattern, True)):
                print >>sys.stderr, 'failed to get key %s from keyservers or from your keyring, aborting' % pattern
                sys.exit(4)
        else:
            # 1.b) from the local keyring (@todo try that first?)
            if self.options.verbose: print >>sys.stderr, 'looking for key %s in your keyring' % self.pattern
            if self.options.dryrun: return True
            if not self.tmpkeyring.import_data(self.keyring.export_data(self.pattern)):
                print >>sys.stderr, 'could not find key %s in your keyring, and no keyserve defined' % self.pattern
                sys.exit(3)


    def copy_secrets(self):
        """import secret keys from your keyring"""
        if self.options.verbose: print >>sys.stderr, 'copying your private key to temporary keyring in', self.tmpkeyring.tmphomedir
        if not self.options.dryrun:
            if not self.tmpkeyring.import_data(self.keyring.export_data(options.user, True)):
                print >>sys.stderr, 'could not find private key material, do you have a GPG key?'
                sys.exit(5)

    def sign_key(self):
        """sign the key uids, as specified"""

        keys = self.tmpkeyring.get_keys(self.pattern)

        print "found", len(keys), "keys matching your request"

        for key in keys:
            print 'Signing the following key'
            print
            print str(keys[key])
            print

            print 'Sign key? [y/N] ',
            ans = sys.stdin.readline()
            while ans == "\n":
                print 'Sign key? [y/N] ',
                ans = sys.stdin.readline()

            if ans.lower() != "y\n":
                print >>sys.stderr, 'aborting keysigning as requested'
                continue

            if not self.options.dryrun:
                if not self.tmpkeyring.sign_key(keys[key].fpr, options.alluids):
                    print >>sys.stderr, 'key signing failed'
                else:
                    self.signed_fprs.append(key)

    def export_key(self):
        self.tmpkeyring.context.set_option('armor')
        for fpr in self.signed_fprs:
            data = self.tmpkeyring.export_data(fpr)
            encrypted = self.tmpkeyring.encrypt_data(data, self.pattern)

    def mail_key(self):
        raise NotImplementedError('key mailing not implemented')

if __name__ == '__main__':
    (options, args) = parse_args()
    try:
        MonkeysignCli().main(args[0], options)
    except IndexError:
        print >>sys.stderr, 'wrong number of arguments'
        sys.exit(1)
    except NotImplementedError as e:
        print >>sys.stderr, str(e)
        sys.exit(2)
