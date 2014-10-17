# -*- coding: utf-8 -*-
#
#    Copyright (C) 2012-2013 Antoine Beaupré <anarcat@orangeseeds.org>
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

from monkeysign import __version__
# gpg interface
from monkeysign.gpg import Keyring, TempKeyring, GpgRuntimeError
import monkeysign.translation

# mail functions
from email.mime.multipart import MIMEMultipart
from email.mime.message import MIMEMessage
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.header import Header
from email.utils import parseaddr, formataddr
from email import Charset
import smtplib
import subprocess

# system libraries
import optparse
import sys
import re
import os
import shutil
import socket

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

    @classmethod
    def parser(self):
        """parse the commandline arguments"""
        parser = optparse.OptionParser(description=self.__doc__, usage=self.usage, epilog=self.epilog, formatter=NowrapHelpFormatter())
        parser.add_option('--version', dest='version', default=False, action='store_true',
                          help=_('show version information and quit'))
        parser.add_option('-d', '--debug', dest='debug', default=False, action='store_true',
                          help=_('request debugging information from GPG engine (lots of garbage)'))
        parser.add_option('-v', '--verbose', dest='verbose', default=False, action='store_true',
                          help=_('explain what we do along the way'))
        parser.add_option('-n', '--dry-run', dest='dryrun', default=False, action='store_true',
                          help=_('do not actually do anything'))
        parser.add_option('-u', '--user', dest='user', help=_('user id to sign the key with'))
        parser.add_option('--cert-level', dest='certlevel', help=_('certification level to sign the key with'))
        parser.add_option('-l', '--local', dest='local', default=False, action='store_true',
                          help=_('import in normal keyring a local certification'))
        parser.add_option('-k', '--keyserver', dest='keyserver',
                          help=_('keyserver to fetch keys from'))
        parser.add_option('-s', '--smtp', dest='smtpserver', help=_('SMTP server to use, use a colon to specify the port number if non-standard'))
        parser.add_option('--smtpuser', dest='smtpuser', help=_('username for the SMTP server (default: no user)'))
        parser.add_option('--smtppass', dest='smtppass', help=_('password for the SMTP server (default: prompted, if --smtpuser is specified)'))
        parser.add_option('--no-mail', dest='nomail', default=False, action='store_true',
                          help=_('do not send email at all (default: use sendmail)'))
        parser.add_option('-t', '--to', dest='to', 
                          help=_('override destination email for testing (default: use the first uid on the key or send email to each uid chosen)'))
        return parser

    def parse_args(self, args):
        parser = self.parser()
        (self.options, self.pattern) = parser.parse_args(args=args)

        # XXX: a bit clunky because the cli expects this to be the
        # output of parse_args() while the GTK ui expects this to be
        # populated as a string, later
        if len(self.pattern) < 1:
            self.pattern = None
        else:
            # accept space-separated fingerprints
            self.pattern = "".join(self.pattern)
        # make sure parser can be accessed outside of this function
        return parser

    def __init__(self, args = None):
        # the options that determine how we operate, from the parse_args()
        self.options = {}

        # the key we are signing, can be a keyid or a uid pattern
        self.pattern = None

        # the regular keyring we suck secrets and maybe the key to be signed from
        self.keyring = Keyring()

        # the temporary keyring we operate in, actually initialized in prepare()
        # this is because we want the constructor to just initialise
        # data structures and not write any data
        self.tmpkeyring = None

        # the fingerprints that we actually signed
        self.signed_keys = {}

        # temporary, to keep track of the OpenPGPkey we are signing
        self.signing_key = None

        self.parse_args(args)

        # set a default logging mechanism
        self.logfile = sys.stderr
        self.log(_('Initializing UI'))

        # create the temporary keyring
        # XXX: i would prefer this to be done outside the constructor
        self.prepare()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # this is implicit in the garbage collection, but tell the user anyways
        self.log(_('deleting the temporary keyring %s') % self.tmpkeyring.homedir)

        if exc_type is NotImplementedError:
            self.abort(str(exc_value))

    def prepare(self):
        # initialize the temporary keyring directory
        self.tmpkeyring = TempKeyring()

        if self.options.version:
            self.abort(monkeysign.__version__)
        if self.options.debug:
            self.tmpkeyring.context.debug = self.logfile
            self.keyring.context.debug = self.logfile
        if self.options.keyserver is not None:
            self.tmpkeyring.context.set_option('keyserver', self.options.keyserver)
        if self.options.user is not None:
            self.tmpkeyring.context.set_option('local-user', self.options.user)
        if self.options.certlevel is not None:
            self.tmpkeyring.context.set_option('default-cert-level', self.options.certlevel)
        self.tmpkeyring.context.set_option('secret-keyring', self.keyring.homedir + '/secring.gpg')

        # copy the gpg.conf from the real keyring
        try:
            self.log(_('copying your gpg.conf in temporary keyring'))
            shutil.copy(self.keyring.homedir + '/gpg.conf', self.tmpkeyring.homedir)
        except IOError as e:
            # no such file or directory is alright: it means the use
            # has no gpg.conf (because we are certain the temp homedir
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
        print message.encode('utf-8')

    def log(self, message):
        """log an informational message if verbose"""
        if self.options.verbose: print >>self.logfile, message

    def yes_no(self, prompt, default = True):
        """default UI is not interactive, so we assume yes all the time"""
        return True

    def choose_uid(self, prompt, uids):
        raise NotImplementedError('choosing not implemented in base class')

    def prompt_line(self, prompt):
        raise NotImplementedError('prompting for a line not implemented in base class')

    def prompt_pass(self, prompt):
        raise NotImplementedError('prompting for a password not implemented in base class')

    def find_key(self):
        """find the key to be signed somewhere"""
        # 1.b) from the local keyring
        self.log(_('looking for key %s in your keyring') % self.pattern)
        if not self.tmpkeyring.import_data(self.keyring.export_data(self.pattern)):
            self.log(_('key not in local keyring'))

            # 1.a) if allowed, from the keyservers
            self.log(_('fetching key %s from keyserver') % self.pattern)

            if not re.search('^[0-9A-F]*$', self.pattern, re.IGNORECASE): # this is not a keyid
                # the problem here is that we need to implement --search-keys, and it's a pain
                raise NotImplementedError(_('please provide a keyid or fingerprint, uids are not supported yet'))

            if not self.tmpkeyring.fetch_keys(self.pattern):
                self.abort(_('could not find key %s in your keyring or keyservers') % self.pattern)

    def copy_secrets(self):
        """import secret keys (but only the public part) from your keyring

we use --secret-keyring instead of copying the secret key material,
but we still need the public part in the temporary keyring for this to
work.
"""
        self.log(_('copying your private key to temporary keyring in %s') % self.tmpkeyring.homedir)
        # detect the proper uid
        if self.options.user is None:
            keys = self.keyring.get_keys(None, True, False)
        else:
            keys = self.keyring.get_keys(self.options.user, True, False)

        for fpr, key in keys.iteritems():
            self.log(_('found secret key: %s') % key)
            if not key.invalid and not key.disabled and not key.expired and not key.revoked:
                self.signing_key = key
                break

        if self.signing_key is None:
            self.abort(_('no default secret key found, abort!'))
        self.log(_('signing key chosen: %s') % self.signing_key.fpr)

        # export public key material associated with detected private
        if not self.tmpkeyring.import_data(self.keyring.export_data(self.signing_key.fpr)):
            self.abort(_('could not find public key material, do you have a GPG key?'))

    def sign_key(self):
        """sign the key uids, as specified"""

        keys = self.tmpkeyring.get_keys(self.pattern)

        self.log(_('found %d keys matching your request') % len(keys))

        for key in keys:
            alluids = self.yes_no(_("""\
Signing the following key

%s

Sign all identities? [y/N] \
""") % keys[key], False)

            self.chosen_uid = None
            if alluids:
                pattern = keys[key].fpr
            else:
                pattern = self.choose_uid(_('Choose the identity to sign'), keys[key])
                if not pattern:
                    self.log(_('no identity chosen'))
                    return False
                if not self.options.to:
                    self.options.to = pattern
                self.chosen_uid = pattern

            if not self.options.dryrun:
                if not self.yes_no(_('Really sign key? [y/N] '), False):
                    continue
                if not self.tmpkeyring.sign_key(pattern, alluids):
                    self.warn(_('key signing failed'))
                else:
                    self.signed_keys[key] = keys[key]
                if self.options.local:
                    self.log(_('making a non-exportable signature'))
                    self.tmpkeyring.context.set_option('export-options', 'export-minimal')

                    # this is inefficient - we could save a copy if we would fetch the key directly
                    if not self.keyring.import_data(self.tmpkeyring.export_data(self.pattern)):
                        self.abort(_('could not import public key back into public keyring, something is wrong'))
                    if not self.keyring.sign_key(pattern, alluids, True):
                        self.warn(_('local key signing failed'))

    def export_key(self):
        if self.options.user is not None and '@' in self.options.user:
            from_user = self.options.user
        else:
            from_user = self.signing_key.uidslist[0].uid

        if len(self.signed_keys) < 1: self.warn(_('no key signed, nothing to export'))
        
        for fpr, key in self.signed_keys.items():
            if self.chosen_uid is None:
                for uid in key.uids.values():
                    try:
                        msg = EmailFactory(self.tmpkeyring.export_data(fpr), fpr, uid.uid, from_user, self.options.to)
                    except GpgRuntimeError as e:
                        self.warn(_('failed to create email: %s') % e)
                        break
                    self.sendmail(msg)
            else:
                try:
                    msg = EmailFactory(self.tmpkeyring.export_data(fpr), fpr, self.chosen_uid, from_user, self.options.to)
                except GpgRuntimeError as e:
                    self.warn(_('failed to create email: %s') % e)
                    break
                self.sendmail(msg)

    def sendmail(self, msg):
            """actually send the email

expects an EmailFactory email, but will not mail if nomail is set"""
            if self.options.smtpserver is not None and not self.options.nomail:
                if self.options.dryrun: return True
                server = smtplib.SMTP()
                server.set_debuglevel(self.options.debug)
                # to be nicer to users, we could catch socket.error exceptions from
                # server.connect() here and display a meaningful message to stderr.
                try:
                    (code, srvmsg) = server.connect(self.options.smtpserver)
                except (socket.error, socket.timeout) as e:
                    self.abort(_('Error connecting to SMTP server %s: %s') % (self.options.smtpserver, e))
                if code != 220:
                    self.abort(_('Unexpected SMTP server error while talking to %s, code: %s (%s)') % (self.options.smtpserver, code, srvmsg))
                try:
                    server.starttls()
                except SMTPException:
                    self.warn(_('SMTP server does not support STARTTLS'))
                    if self.options.smtpuser: self.warn(_('authentication credentials will be sent in clear text'))
                if self.options.smtpuser:
                    if not self.options.smtppass:
                        self.options.smtppass = self.prompt_pass(_('enter SMTP password for server %s: ') % self.options.smtpserver)
                    server.login(self.options.smtpuser, self.options.smtppass)
                server.sendmail(msg.mailfrom.encode('utf-8'), msg.mailto.encode('utf-8'), msg.as_string().encode('utf-8'))
                server.quit()
                self.warn(_('sent message through SMTP server %s to %s') % (self.options.smtpserver, msg.mailto))
                return True
            elif not self.options.nomail:
                if self.options.dryrun: return True
                p = subprocess.Popen(['/usr/sbin/sendmail', '-t'], stdin=subprocess.PIPE)
                p.communicate(msg.as_string().encode('utf-8'))
                self.warn(_('sent message through sendmail to %s') % msg.mailto)
            else:
                # okay, no mail, just dump the exported key then
                self.warn(_("""\
not sending email to %s, as requested, here's the email message:

%s""") % (msg.mailto, msg.create_mail_from_block()))


class EmailFactory:
    """email generator

this is a factory, ie. a class generating an object that represents
the email and when turned into a string, is the actual
mail.
"""

    # the email subject
    subject = _("Your signed OpenPGP key")

    # the email body
    body = _("""
Please find attached your signed PGP key. You can import the signed
key by running each through `gpg --import`.

If you have multiple user ids, each signature was sent in a separate
email to each user id.

Note that your key was not uploaded to any keyservers. If you want
this new signature to be available to others, please upload it
yourself.  With GnuPG this can be done using:

    gpg --keyserver pool.sks-keyservers.net --send-key <keyid>

Regards,
""")

    def __init__(self, keydata, keyfpr, recipient, mailfrom, mailto):
        """email constructor

we expect to find the following arguments:

keydata: the signed public key material
keyfpr: the fingerprint of that public key
recipient: the recipient to encrypt the mail to
mailfrom: who the mail originates from
mailto: who to send the mail to (usually similar to recipient, but can be used to specify specific keyids"""
        (self.keyfpr, self.recipient, self.mailfrom, self.mailto) = (keyfpr, recipient, mailfrom.decode('utf-8'), mailto or recipient)
        self.mailto = self.mailto.decode('utf-8')
        # operate over our own keyring, this allows us to remove UIDs freely
        self.tmpkeyring = TempKeyring()
        # copy data over from the UI keyring
        self.tmpkeyring.import_data(keydata)
        # prepare for email transport
        self.tmpkeyring.context.set_option('armor')
        # this is necessary because we reimport keys from outside our
        # keyring, so gpg doesn't trust them anymore
        # but we know we do, so we ignore the trustdb
        self.tmpkeyring.context.set_option('trust-model', 'always')
        # remove UIDs we don't want to send
        self.cleanup_uids()
        # cleanup email addresses
        self.cleanup_emails()

    def cleanup_emails(self):
        # wrap real name in quotes
        self.mailfrom = re.sub(r'^(.*) <', r'"\1" <',
                               # trim comment from uid
                               re.sub(r' \([^)]*\)', r'',
                                      self.mailfrom))
        # same with mailto
        self.mailto = re.sub(r'^(.*) <', r'"\1" <',
                             re.sub(r' \([^)]*\)', r'',
                                    self.mailto))

    def cleanup_uids(self):
        """this will remove any UID not matching the 'recipient' set in the class"""
        for fpr, key in self.tmpkeyring.get_keys().iteritems():
            todelete = []
            for uid in key.uids.values():
                if self.recipient != uid.uid:
                    todelete.append(uid.uid)
            for uid in todelete:
                self.tmpkeyring.del_uid(fpr, uid)

    def get_message(self):
        # first layer, seen from within:
        # an encrypted MIME message, made of two parts: the
        # introduction and the signed key material
        message = self.create_mail_from_block()
        encrypted = self.tmpkeyring.encrypt_data(message.as_string(), self.keyfpr)

        # the second layer up, made of two parts: a version number
        # and the first layer, encrypted
        return self.wrap_crypted_mail(encrypted)

    def __str__(self):
        return self.get_message().as_string().decode('utf-8')

    def as_string(self):
        return self.__str__()

    def create_mail_from_block(self):
        """
        a multipart/mixed message containing a plain-text message
        explaining what this is, and a second part containing PGP data
        """

        # Override python's weird assumption that utf-8 text should be encoded with
        # base64, and instead use quoted-printable (for both subject and body).  I
        # can't figure out a way to specify QP (quoted-printable) instead of base64 in
        # a way that doesn't modify global state. :-(
        # (taken from http://radix.twistedmatrix.com/2010/07/how-to-send-good-unicode-email-with.html)
        Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')

        text = MIMEText(self.body, 'plain', 'utf-8')
        filename = 'signed-%s.asc' % self.keyfpr # should be 0xkeyid.uididx.signed-by-0xkeyid.asc
        keypart = MIMEBase('application', 'pgp-keys', name=filename)
        keypart.add_header('Content-Disposition', 'attachment', filename=filename)
        keypart.add_header('Content-Transfer-Encoding', '7bit')
        keypart.add_header('Content-Description', (_('signed PGP Key %s, uid %s') % (self.keyfpr, self.recipient.decode('utf-8'))))
        keypart.set_payload(self.tmpkeyring.export_data(self.keyfpr))
        return MIMEMultipart('mixed', None, [text, keypart])

    def wrap_crypted_mail(self, encrypted):
        p1 = MIMEBase('application', 'pgp-encrypted', filename='signedkey.msg')
        p1.add_header('Content-Disposition','attachment', filename='signedkey.msg')
        p1.set_payload('Version: 1')
        p2 = MIMEBase('application', 'octet-stream', filename='msg.asc')
        p2.add_header('Content-Disposition', 'inline', filename='msg.asc')
        p2.add_header('Content-Transfer-Encoding', '7bit')
        p2.set_payload(encrypted)
        msg = MIMEMultipart('encrypted', None, [p1, p2], protocol="application/pgp-encrypted")
        msg.preamble = _('This is a multi-part message in PGP/MIME format...')
        msg['Subject'] = Header(self.subject.encode('utf-8'), 'UTF-8').encode()
        name, address = parseaddr(self.mailfrom)
        msg['From'] = formataddr((Header(name.encode('utf-8'), 'UTF-8').encode(), address))
        name, address = parseaddr(self.mailto)
        msg['To'] = formataddr((Header(name.encode('utf-8'), 'UTF-8').encode(), address))
        return msg

class NowrapHelpFormatter(optparse.IndentedHelpFormatter):
    """A non-wrapping formatter for OptionParse."""

    def _format_text(self, text):
        return text
