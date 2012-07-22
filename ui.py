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

from optparse import OptionParser, IndentedHelpFormatter

from gpg import Keyring, TempKeyring

from email.mime.multipart import MIMEMultipart
from email.mime.message import MIMEMessage
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
import smtplib
import subprocess

import sys

class MonkeysignUi(object):
    """User interface abstraction for monkeysign.

    This aims to factor out a common pattern to sign keys that is used
    regardless of the UI used.

    This is mostly geared at console/text-based and X11 interfaces,
    but could also be ported to other interfaces (touch-screen/phone
    interfaces would be interesting).

    The actual process is in main(), which outlines what the
    subclasses of this should be doing.

    You should have a docstring in derived classes, as it will be
    added to the 'usage' output.

    You should also set the usage and epilog parameters, see
    parse_args().
    """

    # what gets presented to the user in the usage (first and last lines)
    # default is to use the OptionParser's defaults
    # the 'docstring' above is the long description
    usage=None
    epilog=None

    # the options that determine how we operate, from the parse_args()
    options = {}

    # the key we are signing, can be a keyid or a uid pattern
    pattern = None

    # the regular keyring we suck secrets and maybe the key to be signed from
    keyring = None

    # the temporary keyring we operate in
    tmpkeyring = None

    # the fingerprints that we actually signed
    signed_keys = None

    # temporary, to keep track of the OpenPGPkey we are signing
    signing_key = None

    @classmethod
    def parse_args(self):
        """parse the commandline arguments"""
        parser = OptionParser(description=self.__doc__, usage=self.usage, epilog=self.epilog, formatter=NowrapHelpFormatter())
        parser.add_option('-d', '--debug', dest='debug', default=False, action='store_true',
                          help='request debugging information from GPG engine (lots of garbage)')
        parser.add_option('-v', '--verbose', dest='verbose', default=False, action='store_true',
                          help='explain what we do along the way')
        parser.add_option('-n', '--dry-run', dest='dryrun', default=False, action='store_true',
                          help='do not actually do anything')
        parser.add_option('-u', '--user', dest='user', help='user id to sign the key with')
        parser.add_option('-l', '--local', dest='local', default=False, action='store_true',
                          help='import in normal keyring a local certification')
        parser.add_option('-k', '--keyserver', dest='keyserver',
                          help='keyserver to fetch keys from')
        parser.add_option('-s', '--smtp', dest='smtpserver', help='SMTP server to use')
        parser.add_option('--no-mail', dest='nomail', default=False, action='store_true',
                          help='Do not send email at all. (Default is to use sendmail.)')
        parser.add_option('-t', '--to', dest='to', 
                          help='Override destination email for testing (default is to use the first uid on the key or send email to each uid chosen)')

        return parser.parse_args()

    def __init__(self, pattern, options = {}):
        self.options = options
        try:
            self.log('Initializing UI')
        except AttributeError:
            # set a default logging mechanism
            self.options.log = sys.stderr
            self.log('Initializing UI')

        self.pattern = pattern
        self.signed_keys = {}

        if options.local:
            self.abort('local key signing not implemented yet')

        # setup environment and options
        self.tmpkeyring = tmpkeyring = TempKeyring()
        self.keyring = Keyring() # the real keyring
        if options.debug:
            self.tmpkeyring.context.debug = sys.stderr
        if options.keyserver is not None: tmpkeyring.context.set_option('keyserver', options.keyserver)

        try:
            self.main(pattern, options)
        except NotImplementedError as e:
            self.abort(str(e))
        # this is implicit in the garbage collection, but tell the user anyways
        self.log('deleting the temporary keyring ' + self.tmpkeyring.tmphomedir)

    def main(self, pattern, options = {}):
        """
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
        pass # we allow for interactive process

    def abort(self, message):
        """show a message to the user and abort program"""
        self.warn(message)
        sys.exit(1)

    def warn(self, message):
        """display an error message"""
        print message

    def log(self, message):
        """log an informational message if verbose"""
        if self.options.verbose and self.options.log: print >>self.options.log, message

    def yes_no(self, prompt, default = None):
        raise NotImplementedError('prompting not implemented in base class')

    def choose_uid(self, prompt, uids):
        raise NotImplementedError('prompting not implemented in base class')

    def find_key(self):
        """find the key to be signed somewhere"""
        self.keyring.context.set_option('export-options', 'export-minimal')
        if self.options.keyserver:
            # 1.a) if allowed, from the keyservers
            self.log('fetching key %s from keyservers' % self.pattern)

            if not re.search('^[0-9A-F]*$', self.pattern): # this is not a keyid
                # the problem here is that we need to implement --search-keys, and it's a pain
                raise NotImplementedError('please provide a keyid or fingerprint, uids are not supported yet')

            if not self.tmpkeyring.fetch_keys(self.pattern) \
                    and not self.tmpkeyring.import_data(self.keyring.export_data(self.pattern, True)):
                self.abort('failed to get key %s from keyservers or from your keyring, aborting' % pattern)
        else:
            # 1.b) from the local keyring (@todo try that first?)
            self.log('looking for key %s in your keyring' % self.pattern)
            if not self.tmpkeyring.import_data(self.keyring.export_data(self.pattern)):
                self.abort('could not find key %s in your keyring, and no keyserver defined' % self.pattern)


    def copy_secrets(self):
        """import secret keys from your keyring"""
        self.log('copying your private key to temporary keyring in' + self.tmpkeyring.tmphomedir)
        if not self.options.dryrun:
            if not self.tmpkeyring.import_data(self.keyring.export_data(self.options.user, True)):
                self.abort('could not find private key material, do you have a GPG key?')

        # detect the proper uid
        if self.options.user is None:
            keys = self.tmpkeyring.get_keys(None, True)
        else:
            keys = self.tmpkeyring.get_keys(self.options.user, True)

        for fpr, key in keys.iteritems():
            if not key.invalid and not key.disabled and not key.expired and not key.revoked:
                self.signing_key = key
                break

        if self.signing_key is None:
            self.abort('no default secret key found, abort!')

        if not self.tmpkeyring.import_data(self.keyring.export_data(self.signing_key.fpr)):
            self.abort('could not find public key material, do you have a GPG key?')

    def sign_key(self):
        raise NotImplementedError('signing is too UI-dependent to have a good default, implement one')

    def export_key(self):
        self.tmpkeyring.context.set_option('armor')
        self.tmpkeyring.context.set_option('always-trust')

        if self.options.user is not None and '@' in self.options.user:
            from_user = self.options.user
        else:
            from_user = self.signing_key.uidslist[0].uid

        if len(self.signed_keys) < 1: self.warn('no key signed, nothing to export')
        for fpr in self.signed_keys:
            data = self.tmpkeyring.export_data(fpr)

            # first layer, seen from within:
            # an encrypted MIME message, made of two parts: the
            # introduction and the signed key material
            text = MIMEText('your pgp key, yay', 'plain', 'utf-8')
            filename = "yourkey.asc" # should be 0xkeyid.uididx.signed-by-0xkeyid.asc
            key = MIMEBase('application', 'php-keys', name=filename)
            key.add_header('Content-Disposition', 'attachment', filename=filename)
            key.add_header('Content-Transfer-Encoding', '7bit')
            key.add_header('Content-Description', 'PGP Key <keyid>, uid <uid> (<idx), signed by <keyid>')
            message = MIMEMultipart('mixed', [text, data])
            encrypted = self.tmpkeyring.encrypt_data(message.as_string(), self.pattern)

            # the second layer up, made of two parts: a version number
            # and the first layer, encrypted
            p1 = MIMEBase('application', 'pgp-encrypted', filename='signedkey.msg')
            p1.add_header('Content-Disposition','attachment', filename='signedkey.msg')
            p1.set_payload('Version: 1')
            p2 = MIMEBase('application', 'octet-stream', filename='msg.asc')
            p2.add_header('Content-Disposition', 'inline', filename='msg.asc')
            p2.add_header('Content-Transfer-Encoding', '7bit')
            p2.set_payload(encrypted)
            msg = MIMEMultipart('encrypted', None, [p1, p2], protocol="application/pgp-encrypted")
            msg['Subject'] = 'Your signed OpenPGP key'
            msg['From'] = from_user
            msg.preamble = 'This is a multi-part message in PGP/MIME format...'
            # take the first uid, not ideal
            msg['To'] = self.options.to

            if self.options.smtpserver is not None:
                self.warn('sending message through SMTP server %s to %s' % (self.options.smtpserver, self.options.to))
                if self.options.dryrun: return True
                server = smtplib.SMTP(self.options.smtpserver)
                server.sendmail(from_user, self.options.to, msg.as_string())
                server.set_debuglevel(1)
                server.quit()
                return True
            elif not self.options.nomail:
                self.warn('sending message through sendmail to ' + self.options.to)
                if self.options.dryrun: return True
                p = subprocess.Popen(['/usr/sbin/sendmail', '-t'], stdin=subprocess.PIPE)
                p.communicate(msg.as_string())
            else:
                # okay, no mail, just dump the exported key then
                self.warn("""\
not sending email, as requested, here's the signed key:

%s""" % data)

    def sign_key(self):
        """sign the key uids, as specified"""

        keys = self.tmpkeyring.get_keys(self.pattern)

        print "found", len(keys), "keys matching your request"

        for key in keys:
            alluids = self.yes_no("""\
Signing the following key

%s

Sign all identities? [y/N] \
""" % str(keys[key]), False)

            if alluids:
                pattern = keys[key].fpr
                if not self.options.to:
                    self.options.to = keys[key].uids.values()[0].uid
            else:
                pattern = self.choose_uid('Specify the identity to sign: ', keys[key])
                if not self.options.to:
                    self.options.to = pattern

            if not self.options.dryrun:
                if not self.yes_no('Really sign key? [y/N] ', False):
                    continue
                if not self.tmpkeyring.sign_key(pattern, alluids):
                    self.warn('key signing failed')
                else:
                    self.signed_keys[key] = keys[key]

class NowrapHelpFormatter(IndentedHelpFormatter):
    """A non-wrapping formatter for OptionParse."""

    def _format_text(self, text):
        return text

class MonkeysignCli(MonkeysignUi):
    """Sign a key in a safe fashion.

This command should sign a key based on the fingerprint or user id
specified on the commandline, encrypt the result and mail it to the
user. This leave the choice of publishing the certification to that
person and makes sure that person owns the identity signed. This
script assumes you have gpg-agent configure to prompt for passwords.
"""

    # override default options to allow passing a keyid
    usage = usage='%prog [options] <keyid>'
    epilog='<keyid>: a GPG fingerprint or key id'

    def main(self, pattern, options = {}):
        """main code execution loop

        we expect to have the commandline parsed for us
        """
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
        self.export_key()

        # 3.4. optionnally (-l), create a local signature and import in
        #local keyring
        # @todo

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

