# -*- coding: utf-8 -*-
#
#    Copyright (C) 2012 Antoine Beaupré <anarcat@orangeseeds.org>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Native Python / GPG API

This API was written to replace the GPGME bindings because the GPGME
API has a few problems:

 1. it is arcane and difficult to grasp
 2. it is very closely bound to the internal GPG data and commandline
    structures, which are quite confusing
 3. GPGME doesn't actually talk to a GPG library, but interacts with
    GPG through the commandline
 4. GPGME developers are not willing to extend GPGME to cover private
    key material management and consider this is outside the scope of
    the project.

The latter two points are especially problematic for this project, and
I have therefore started working on a replacement.

Operations are performed mostly through the Keyring or KeyringTmp
class (if you do not want to access your regular keyring but an empty
temporary one).

This is how you can access keys, which are represented by the
OpenPGPkey datastructure, but which will not look in your keyring or
on the keyservers itself without the Keyring class.
"""

import os, tempfile, shutil, subprocess, re

from StringIO import StringIO

class Context():
    """Python wrapper for GnuPG

    This wrapper allows for a simpler interface than GPGME or PyME to
    GPG, and bypasses completely GPGME to interoperate directly with
    GPG as a process.

    It uses the gpg-agent to prompt for passphrases and communicates
    with GPG over the stdin for commnads (--command-fd) and stdout for
    status (--status-fd).
    """

    # the gpg binary to call
    gpg_binary = 'gpg'

    # a list of key => value commandline options
    #
    # to pass a flag without options, use None as the value
    options = { 'status-fd': 2,
                'command-fd': 0,
                'no-tty': None,
                'quiet': None,
                'batch': None,
                'use-agent': None,
                'with-colons': None,
                'with-fingerprint': None,
                'fixed-list-mode': None,
                'list-options': 'show-sig-subpackets,show-uid-validity,show-unusable-uids,show-unusable-subkeys,show-keyring,show-sig-expire',
                }

    # whether to paste output here and there
    # if not false, needs to be a file descriptor
    debug = False

    def __init__(self):
        self.options = dict(Context.options) # copy

    def set_option(self, option, value = None):
        """set an option to pass to gpg

        this adds the given 'option' commandline argument with the
        value 'value'. to pass a flag without an argument, use 'None'
        for value
        """
        self.options[option] = value

    def unset_option(self, option):
        """remove an option from the gpg commandline"""
        if option in self.options:
            del self.options[option]
        else:
            return false

    def build_command(self, command):
        """internal helper to build a proper gpg commandline

        this will add relevant arguments around the gpg binary.

        like the options arguments, the command is expected to be a
        regular gpg command with the -- stripped. the -- are added
        before being called. this is to make the code more readable,
        and eventually support other backends that actually make more
        sense.

        this uses build_command to create a commandline out of the
        'options' dictionnary, and appends the provided command at the
        end. this is because order of certain options matter in gpg,
        where some options (like --recv-keys) are expected to be at
        the end.

        it is here that the options dictionnary is converted into a
        list. the command argument is expected to be a list of
        arguments that can be converted to strings. if it is not a
        list, it is cast into a list."""
        options = []
        for left, right in self.options.iteritems():
            options += ['--' + left]
            if right is not None:
                options += [str(right)]
        if type(command) is str:
            command = [command]
        if len(command) > 0 and command[0][0:2] != '--':
            command[0] = '--' + command[0]
        return [self.gpg_binary] + options + command

    def call_command(self, command, stdin=None):
        """internal wrapper to call a GPG commandline

        this will call the command generated by build_command() and
        setup a regular pipe to the subcommand.

        this assumes that we have the status-fd on stdout and
        command-fd on stdin, but could really be used in any other
        way.

        we pass the stdin argument in the standard input of gpg and we
        keep the output in the stdout and stderr array. the exit code
        is in the returncode variable.

        we can optionnally watch for a confirmation pattern on the
        statusfd.
        """
        proc = subprocess.Popen(self.build_command(command), 0, None, subprocess.PIPE, subprocess.PIPE, subprocess.PIPE)
        (self.stdout, self.stderr) = proc.communicate(stdin)
        self.returncode = proc.returncode
        if self.debug:
            print >>self.debug, 'command:', self.build_command(command)
            print >>self.debug, 'ret:', self.returncode, 'stdout:', self.stdout, 'stderr:', self.stderr
        return proc.returncode == 0

    def seek_pattern(self, fd, pattern):
        """iterate over file descriptor until certain pattern is found

        fd is a file descriptor
        pattern a string describing a regular expression to match

        this will skip lines not matching pattern until the pattern is
        found. it will raise an IOError if the pattern is not found
        and EOF is reached.

        this may hang for streams that do not send EOF or are waiting
        for input.
        """
        line = fd.readline()
        match = re.search(pattern, line)
        while line and not match:
            if self.debug: print >>self.debug, "skipped:", line,
            line = fd.readline()
            match = re.search(pattern, line)
        if match:
            if self.debug: print >>self.debug, "FOUND:", line,
            return match
        else:
            raise GpgProcotolError(self.returncode, "could not find pattern '%s' in input" % pattern)

    def seek(self, fd, pattern):
        """look for a specific GNUPG status line in the output

        this is a stub for seek_pattern()
        """
        return self.seek_pattern(fd, '^\[GNUPG:\] ' + pattern)

    def expect_pattern(self, fd, pattern):
        """make sure the next line matches the provided pattern

        in contrast with seek_pattern(), this will *not* skip
        non-matching lines and instead raise an exception if such a
        line is found.

        this therefore looks only at the next line, but may also hang
        like seek_pattern()
        """
        line = fd.readline()
        match = re.search(pattern, line)
        if match:
            if self.debug: print >>self.debug, "FOUND:", line,
            return match
        else:
            raise GpgProcotolError(self.returncode, "unexpected pattern: '%s', was expecting '%s'" % (line, pattern))

    def expect(self, fd, pattern):
        """look for a specific GNUPG status on the next line of output

        this is a stub for expect()
        """
        return self.expect_pattern(fd, '^\[GNUPG:\] ' + pattern)

    def version(self):
        """return the version of the GPG binary"""
        self.call_command(['version'])
        m = re.search('gpg \(GnuPG\) (\d+.\d+(?:.\d+)*)', self.stdout)
        return m.group(1)

class Keyring():
    """Keyring functionalities.

    This allows various operations (e.g. listing, signing, exporting
    data) on a keyring.

    Concretely, we talk about a "keyring", but we really mean a set of
    public and private keyrings and their trust databases. In
    practice, this is the equivalent of the GNUPGHOME or --homedir in
    GPG, and in fact this is implemented by setting a specific homedir
    to tell GPG to operate on a specific keyring.

    We actually use the --homedir parameter to gpg to set the keyring
    we operate upon.
    """

    # the context this keyring is associated with
    context = None

    def __init__(self, homedir=None):
        """constructor for the gpg context

        this mostly sets options, and allows passing in a different
        homedir, that will be added to the option right here and
        there.

        by default, we do not create or destroy the keyring, although
        later function calls on the object may modify the keyring (or
        other keyrings, if the homedir option is modified.
        """
        self.context = Context()
        if homedir is not None:
            self.context.set_option('homedir', homedir)

    def import_data(self, data):
        """Import OpenPGP data blocks into the keyring.

        This takes actual OpenPGP data, ascii-armored or not, gpg will
        gladly take it. This can be signatures, public, private keys,
        etc.

        You may need to set import-flags to import non-exportable
        signatures, however.
        """
        self.context.call_command(['import'], data)
        fd = StringIO(self.context.stderr)
        self.context.seek(fd, 'IMPORT_OK')
        self.context.seek(fd, 'IMPORT_RES')
        return self.context.returncode == 0

    def export_data(self, fpr = None, secret = False):
        """Export OpenPGP data blocks from the keyring.

        This exports actual OpenPGP data, by default in binary format,
        but can also be exported asci-armored by setting the 'armor'
        option."""
        if secret: command = ['export-secret-keys']
        else: command = ['export']
        if fpr: command += [fpr]
        self.context.call_command(command)
        return self.context.stdout

    def fetch_keys(self, fpr, keyserver = None):
        """Download keys from a keyserver into the local keyring

        This expects a fingerprint (or a at least a key id).

        Returns true if the command succeeded.
        """
        if keyserver:
            self.context.set_option('keyserver', keyserver)
        self.context.call_command(['recv-keys', fpr])
        return self.context.returncode == 0

    def get_keys(self, pattern = None, secret = False, public = True):
        """load keys matching a specific patterns

        this uses the (rather poor) list-keys API to load keys
        information
        """
        keys = {}
        if public:
            command = ['list-keys']
            if pattern: command += [pattern]
            self.context.call_command(command)
            if self.context.returncode == 0:
                key = OpenPGPkey(self.context.stdout)
                keys[key.fpr] = key
            elif self.context.returncode == 2:
                return None
            else:
                raise GpgProtocolError(self.context.returncode, "unexpected GPG exit code in list-keys: %d" % self.context.returncode)
        if secret:
            command = ['list-secret-keys']
            if pattern: command += [pattern]
            self.context.call_command(command)
            if self.context.returncode == 0:
                key = OpenPGPkey(self.context.stdout)
                # check if we already have that key, in which case we
                # add to it instead of adding a new key
                if key.fpr in keys:
                    keys[key.fpr].parse_gpg_list(self.context.stdout)
                    del key
                else:
                    keys[key.fpr] = key
            elif self.context.returncode == 2:
                return None
            else:
                raise GpgProcotolError(self.context.returncode, "unexpected GPG exit code in list-keys: %d" % self.context.returncode)
        return keys

    def sign_key(self, pattern, signall = False):
        """sign a OpenPGP public key

        By default it looks up and signs a specific uid, but it can
        also sign all uids in one shot thanks to GPG's optimization on
        that."""

        # we iterate over the keys matching the provided
        # keyid, but we should really load those uids from the
        # output of --sign-key
        if self.context.debug: print >>self.context.debug, 'command:', self.context.build_command(['sign-key', pattern])
        proc = subprocess.Popen(self.context.build_command(['sign-key', pattern]), 0, None, subprocess.PIPE, subprocess.PIPE, subprocess.PIPE)
        # don't sign all uids
        self.context.seek(proc.stderr, 'GET_BOOL keyedit.sign_all.okay')
        if signall: # special case, sign all keys
            print >>proc.stdin, "y"
            self.context.expect(proc.stderr, 'GOT_IT')
            # confirm signature
            self.context.seek(proc.stderr, 'GET_BOOL sign_uid.okay')
            print >>proc.stdin, 'y'
            self.context.expect(proc.stderr, 'GOT_IT')
            # expect the passphrase confirmation
            self.context.expect(proc.stderr, 'GOOD_PASSPHRASE')
            return proc.wait() == 0

        print >>proc.stdin, "n"
        self.context.expect(proc.stderr, 'GOT_IT')
        # select the uid
        self.context.expect(proc.stderr, 'GET_LINE keyedit.prompt')
        while True:
            m = self.context.seek_pattern(proc.stdout, '^uid:.::::::::([^:]*):::[^:]*:(\d+),[^:]*:')
            if m and m.group(1) == pattern:
                index = int(m.group(2)) + 1
                break
        print >>proc.stdin, str(index)
        self.context.expect(proc.stderr, 'GOT_IT')
        # sign the selected uid
        self.context.seek(proc.stderr, 'GET_LINE keyedit.prompt')
        print >>proc.stdin, "sign"
        self.context.expect(proc.stderr, 'GOT_IT')
        # confirm signature
        self.context.seek(proc.stderr, 'GET_BOOL sign_uid.okay')
        print >>proc.stdin, 'y'
        self.context.expect(proc.stderr, 'GOT_IT')
        # expect the passphrase confirmation
        self.context.expect(proc.stderr, 'GOOD_PASSPHRASE')
        # save the resulting key
        self.context.expect(proc.stderr, 'GET_LINE keyedit.prompt')
        print >>proc.stdin, "save"
        self.context.expect(proc.stderr, 'GOT_IT')
        return proc.wait() == 0

class TempKeyring(Keyring):
    def __init__(self):
        """Override the parent class to generate a temporary GPG home
        that gets destroyed at the end of operations."""
        self.tmphomedir = tempfile.mkdtemp(prefix="pygpg-")
        Keyring.__init__(self, self.tmphomedir)

    def __del__(self):
        shutil.rmtree(self.tmphomedir)

class OpenPGPkey():
    """An OpenPGP key.

    Some of this datastructure is taken verbatim from GPGME.
    """

    # the key has a revocation certificate
    # @todo - not implemented
    revoked = False

    # the expiry date is set and it is passed
    # @todo - not implemented
    expired = False

    # the key has been disabled
    # @todo - not implemented
    disabled = False

    # ?
    invalid = False

    # the various flags on this key
    purpose = {}

    # This is true if the subkey can be used for qualified
    # signatures according to local government regulations.
    # @todo - not implemented
    qualified = False

    # this key has also secret key material
    secret = False

    # This is the public key algorithm supported by this subkey.
    algo = -1

    # This is the length of the subkey (in bits).
    length = None

    # The key fingerprint (a string representation)
    fpr = None

    # The key id (a string representation), only if the fingerprint is unavailable
    # use keyid() instead of this field to find the keyid
    _keyid = None

    # This is the creation timestamp of the subkey.  This is -1 if
    # the timestamp is invalid, and 0 if it is not available.
    creation = 0

    # This is the expiration timestamp of the subkey, or 0 if the
    # subkey does not expire.
    expiry = 0

    # the list of OpenPGPuids associated with this key
    uids = {}

    # the list of subkeys associated with this key
    subkeys = {}

    def __init__(self, data=None):
        self.purpose = { 'encrypt': True, # if the public key part can be used to encrypt data
                         'sign': True,    # if the private key part can be used to sign data
                         'certify': True, # if the private key part can be used to sign other keys
                         'authenticate': True, # if this key can be used for authentication purposes
                         }
        self.uids = {}
        self.subkeys = {}
        if data is not None:
            self.parse_gpg_list(data)

    def keyid(self, l=8):
        if self.fpr is None:
            assert(self._keyid is not None)
            return self._keyid[-l:]
        return self.fpr[-l:]

    def parse_gpg_list(self, text):
        uidslist = []
        for block in text.split("\n"):
            record = block.split(":")
            #for block in record:
            #        print >>sys.stderr, block, "|\t",
            #print >>sys.stderr, "\n"
            rectype = record[0]
            if rectype == 'tru':
                (rectype, trust, selflen, algo, keyid, creation, expiry, serial) = record
            elif rectype == 'fpr':
                self.fpr = record[9]
            elif rectype == 'pub':
                (null, trust, self.length, self.algo, keyid, self.creation, self.expiry, serial, trust, uid, sigclass, purpose, smime) = record
                for p in self.purpose:
                    self.purpose[p] = p[0].lower() in purpose.lower()
            elif rectype == 'uid':
                (rectype, trust, null  , null, null, creation, expiry, uidhash, null, uid, null) = record
                uid = OpenPGPuid(uid, trust, creation, expiry, uidhash)
                self.uids[uidhash] = uid
                uidslist.append(uid)
            elif rectype == 'sub':
                subkey = OpenPGPkey()
                (rectype, trust, subkey.length, subkey.algo, subkey._keyid, subkey.creation, subkey.expiry, serial, trust, uid, sigclass, purpose, smime) = record
                for p in subkey.purpose:
                    subkey.purpose[p] = p[0].lower() in purpose.lower()
                self.subkeys[subkey._keyid] = subkey
            elif rectype == 'sec':
                (null, trust, self.length, self.algo, keyid, self.creation, self.expiry, serial, trust, uid, sigclass, purpose, smime, wtf, wtf, wtf) = record
                self.secret = True
            elif rectype == 'ssb':
                subkey = OpenPGPkey()
                (rectype, trust, subkey.length, subkey.algo, subkey._keyid, subkey.creation, subkey.expiry, serial, trust, uid, sigclass, purpose, smime, wtf, wtf, wtf) = record
                if subkey._keyid in self.subkeys:
                    # XXX: nothing else to add here?
                    self.subkeys[subkey._keyid].secret = True
                else:
                    self.subkeys[subkey._keyid] = subkey
            elif rectype == 'uat':
                pass # user attributes, ignore for now
            elif rectype == 'rvk':
                pass # revocation key, ignored for now
            elif rectype == '':
                pass
            else:
                raise NotImplementedError("record type '%s' not implemented" % rectype)
        if uidslist: self.uidslist = uidslist

    def __str__(self):
        ret = "pub    " + self.length + "R/" 
        ret += self.keyid(8) + " " + self.creation
        if self.expiry: ret += ' [expiry: ' + self.expiry + ']'
        ret += "\n"
        ret += '    Fingerprint = ' + self.fpr + "\n"
        for uid in self.uids.values():
            ret += "uid      [ " + uid.trust + " ] " + uid.uid + "\n"
        for subkey in self.subkeys.values():
            ret += "sub   " + subkey.length + "R/" + subkey.keyid(8) + " " + subkey.creation
            if subkey.expiry: ret += ' [expiry: ' + subkey.expiry + "]"
            ret += "\n"
        return ret

class OpenPGPuid():
    def __init__(self, uid, trust, creation = 0, expire = None, uidhash = ''):
        self.uid = uid
        self.trust = trust
        self.creation = creation
        self.expire = expire
        self.uidhash = uidhash

class GpgProcotolError(IOError):
    """simple exception raised when we have trouble talking with GPG

    we try to pass the subprocess.popen.returncode as an errorno and a
    significant description string
    """
    pass
