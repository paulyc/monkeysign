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

def main(pattern, options = {}):
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
    if options.user is None:
        raise NotImplementedError('no default key detection code, please provide a user to sign keys with -u')
    if options.local:
        raise NotImplementedError('local key signing not implemented yet')

    # setup environment and options
    tmpkeyring = TempKeyring()
    if options.debug:
        tmpkeyring.context.debug = sys.stderr
    if options.keyserver is not None: tmpkeyring.context.set_option('keyserver', options.keyserver)

    # 1. fetch the key into a temporary keyring
    # 1.a) if allowed (@todo), from the keyservers
    if options.verbose: print >>sys.stderr, 'fetching key %s from keyservers' % pattern
    if not options.dryrun:
        if not tmpkeyring.fetch_keys(pattern):
            # 1.b) @todo from the local keyring (@todo try that first?)
            print >>sys.stderr, 'failed to get key %s from keyservers, aborting' % pattern
            sys.exit(3)

    # 2. copy the signing key secrets into the keyring
    if options.verbose: print >>sys.stderr, 'copying your private key to temporary keyring in', tmpkeyring.tmphomedir
    if not options.dryrun:
        keyring = Keyring() # the real keyring
        if not tmpkeyring.import_data(keyring.export_data(options.user, True)):
            print >>sys.stderr, 'could not find private key material, do you have a GPG key?'
            sys.exit(4)

    # 3. for every user id (or all, if -a is specified)
    # 3.1. sign the uid, using gpg-agent
    # 3.2. export and encrypt the signature
    # 3.3. mail the key to the user
    # 3.4. optionnally (-l), create a local signature and import in
    #local keyring

    # 4. trash the temporary keyring
    if options.verbose: print >>sys.stderr, 'deleting the temporary keyring ', tmpkeyring.tmphomedir
    # implicit

if __name__ == '__main__':
    (options, args) = parse_args()
    try:
        main(args[0], options)
    except IndexError:
        print >>sys.stderr, 'wrong number of arguments'
        sys.exit(1)
    except NotImplementedError as e:
        print >>sys.stderr, str(e)
        sys.exit(2)