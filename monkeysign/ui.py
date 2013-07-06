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

# gpg interface
from monkeysign.gpg import Keyring, TempKeyring

# mail functions
from email.mime.multipart import MIMEMultipart
from email.mime.message import MIMEMessage
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
import smtplib
import subprocess

# system libraries
from optparse import OptionParser, IndentedHelpFormatter
import sys
import re
import os
import shutil

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

    # the email subject
    # @todo make this translatable
    email_subject = "Your signed OpenPGP key"

    # the email body
    # @todo make this translatable
    email_body = """
Please find attached your signed PGP key. You can import the signed
key by running each through `gpg --import`.

Note that your key was not uploaded to any keyservers. If you want
this new signature to be available to others, please upload it
yourself.  With GnuPG this can be done using:

    gpg --keyserver pool.sks-keyservers.net --send-key <keyid>

Regards,
"""

    def parse_args(self, args):
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

        (self.options, self.pattern) = parser.parse_args(args=args)

        # XXX: a bit clunky because the cli expects this to be the
        # output of parse_args() while the GTK ui expects this to be
        # populated as a string, later
        if len(self.pattern) == 1:
            self.pattern = self.pattern[0]
        elif len(self.pattern) < 1:
            self.pattern = None
        else:
            sys.exit('wrong number of arguments')

    def __init__(self, args = None):
        # the options that determine how we operate, from the parse_args()
        self.options = {}

        # the key we are signing, can be a keyid or a uid pattern
        self.pattern = None

        # the regular keyring we suck secrets and maybe the key to be signed from
        self.keyring = Keyring()

        # the temporary keyring we operate in, actually initialized in prepare()
        # this is because we want the constructor to jsut initialise
        # data structures and not write any data
        self.tmpkeyring = None

        # the fingerprints that we actually signed
        self.signed_keys = {}

        # temporary, to keep track of the OpenPGPkey we are signing
        self.signing_key = None

        self.parse_args(args)

        # set a default logging mechanism
        self.logfile = sys.stderr
        self.log('Initializing UI')

        # create the temporary keyring
        # XXX: i would prefer this to be done outside the constructor
        self.prepare()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # this is implicit in the garbage collection, but tell the user anyways
        self.log('deleting the temporary keyring ' + self.tmpkeyring.tmphomedir)

        if type is NotImplementedError:
            ui.abort(str(exc_value))

    def prepare(self):
        # initialize the temporary keyring directory
        self.tmpkeyring = TempKeyring()

        if self.options.debug:
            self.tmpkeyring.context.debug = self.logfile
            self.keyring.context.debug = self.logfile
        if self.options.keyserver is not None:
            self.tmpkeyring.context.set_option('keyserver', self.options.keyserver)

        # copy the gpg.conf from the real keyring
        home = os.environ['HOME'] + '/.gnupg'
        if 'GNUPGHOME' in os.environ:
            home = os.environ['GNUPGHOME']
        try:
            shutil.copy(home + '/gpg.conf', self.tmpkeyring.tmphomedir)
            self.log("copied your gpg.conf in temporary keyring")
        except IOError as e:
            # no such file or directory is alright: it means the use
            # has no gpg.conf (because we are certain the tmphomedir
            # exists at this point)
            if e.errno != 2:
                pass

    def main(self):
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
        pass # we don't do anything because we allow for interactive process

    def abort(self, message):
        """show a message to the user and abort program"""
        sys.exit(message)

    def warn(self, message):
        """display an warning message

this should not interrupt the flow of the program, but must be visible to the user"""
        print message

    def log(self, message):
        """log an informational message if verbose"""
        if self.options.verbose: print >>self.logfile, message

    def yes_no(self, prompt, default = None):
        raise NotImplementedError('prompting not implemented in base class')

    def choose_uid(self, prompt, uids):
        raise NotImplementedError('prompting not implemented in base class')

    def find_key(self):
        """find the key to be signed somewhere"""
        self.keyring.context.set_option('export-options', 'export-minimal')

        # 1.b) from the local keyring
        self.log('looking for key %s in your keyring' % self.pattern)
        if not self.tmpkeyring.import_data(self.keyring.export_data(self.pattern)):
            self.log('key not in local keyring')

            # 1.a) if allowed, from the keyservers
            self.log('fetching key %s from keyservers' % self.pattern)

            if not re.search('^[0-9A-F]*$', self.pattern, re.IGNORECASE): # this is not a keyid
                # the problem here is that we need to implement --search-keys, and it's a pain
                raise NotImplementedError('please provide a keyid or fingerprint, uids are not supported yet')

            if not self.tmpkeyring.fetch_keys(self.pattern):
                self.abort('could not find key %s in your keyring or keyservers' % self.pattern)

    def copy_secrets(self):
        """import secret keys from your keyring"""
        self.log('copying your private key to temporary keyring in' + self.tmpkeyring.tmphomedir)
        if not self.tmpkeyring.import_data(self.keyring.export_data(self.options.user, True)):
            self.abort('could not find private key material, do you have a GPG key?')

        # detect the proper uid
        if self.options.user is None:
            keys = self.tmpkeyring.get_keys(None, True, False)
        else:
            keys = self.tmpkeyring.get_keys(self.options.user, True, False)

        for fpr, key in keys.iteritems():
            self.log('found secret key: %s' % key)
            if not key.invalid and not key.disabled and not key.expired and not key.revoked:
                self.signing_key = key
                break

        self.log('signing key chosen: %s' % key.fpr)

        if self.signing_key is None:
            self.abort('no default secret key found, abort!')

        # export public key material associated with the above
        if not self.tmpkeyring.import_data(self.keyring.export_data(self.signing_key.fpr)):
            self.abort('could not find public key material, do you have a GPG key?')

    def sign_key(self):
        """sign the key uids, as specified"""

        keys = self.tmpkeyring.get_keys(self.pattern)

        self.log("found %d keys matching your request" % len(keys))

        for key in keys:
            alluids = self.yes_no("""\
Signing the following key

%s

Sign all identities? [y/N] \
""" % str(keys[key]), False)

            if alluids:
                pattern = keys[key].fpr
            else:
                pattern = self.choose_uid('Specify the identity to sign: ', keys[key])
                if not pattern:
                    self.log("no identity chosen")
                    return False
                if not self.options.to:
                    self.options.to = pattern

            if not self.options.dryrun:
                if not self.yes_no('Really sign key? [y/N] ', False):
                    continue
                if not self.tmpkeyring.sign_key(pattern, alluids):
                    self.warn('key signing failed')
                else:
                    self.signed_keys[key] = keys[key]
                if self.options.local:
                    self.log("making a non-exportable signature")
                    self.tmpkeyring.context.set_option('export-options', 'export-minimal')

                    # this is inefficient - we could save a copy if we would fetch the key directly
                    if not self.keyring.import_data(self.tmpkeyring.export_data(self.pattern)):
                        self.abort('could not import public key back into public keyring, something is wrong')
                    if not self.keyring.sign_key(pattern, alluids, True):
                        self.warn('local key signing failed')

    def export_key(self):
        self.tmpkeyring.context.set_option('armor')
        self.tmpkeyring.context.set_option('always-trust')

        if self.options.user is not None and '@' in self.options.user:
            from_user = self.options.user
        else:
            from_user = self.signing_key.uidslist[0].uid

        if len(self.signed_keys) < 1: self.warn('no key signed, nothing to export')
        
        for fpr, key in self.signed_keys.items():
            data = self.tmpkeyring.export_data(fpr)

            # first layer, seen from within:
            # an encrypted MIME message, made of two parts: the
            # introduction and the signed key material
            text = MIMEText(self.email_body, 'plain', 'utf-8')
            filename = "yourkey.asc" # should be 0xkeyid.uididx.signed-by-0xkeyid.asc
            keypart = MIMEBase('application', 'pgp-keys', name=filename)
            keypart.add_header('Content-Disposition', 'attachment', filename=filename)
            keypart.add_header('Content-Transfer-Encoding', '7bit')
            keypart.add_header('Content-Description', 'PGP Key <keyid>, uid <uid> (<idx), signed by <keyid>')
            keypart.set_payload(data)
            message = MIMEMultipart('mixed', None, [text, keypart])
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
            msg['Subject'] = self.email_subject
            msg['From'] = from_user
            msg.preamble = 'This is a multi-part message in PGP/MIME format...'
            # take the first uid, not ideal
            msg['To'] = self.options.to or key.uids.values()[0].uid

            if self.options.smtpserver is not None:
                if self.options.dryrun: return True
                server = smtplib.SMTP(self.options.smtpserver)
                server.sendmail(from_user, msg['To'], msg.as_string())
                server.set_debuglevel(1)
                server.quit()
                self.warn('sent message through SMTP server %s to %s' % (self.options.smtpserver, msg['To']))
                return True
            elif not self.options.nomail:
                if self.options.dryrun: return True
                p = subprocess.Popen(['/usr/sbin/sendmail', '-t'], stdin=subprocess.PIPE)
                p.communicate(msg.as_string())
                self.warn('sent message through sendmail to ' + msg['To'])
            else:
                # okay, no mail, just dump the exported key then
                self.warn("""\
not sending email to %s, as requested, here's the signed key:

%s""" % (msg['To'], data))

class NowrapHelpFormatter(IndentedHelpFormatter):
    """A non-wrapping formatter for OptionParse."""

    def _format_text(self, text):
        return text