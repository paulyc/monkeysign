import os, tempfile, shutil, subprocess, re

class KeyNotFound(Exception):
        def __init__(self, msg=None):
                self.msg = msg
        def __repr__(self):
                return self.msg

class Gpg():
        """Python wrapper for GnuPG

        This wrapper allows for a simpler interface than GPGME or PyME
        to GPG, and bypasses completely GPGME to interoperate directly
        with GPG as a process.

        It uses the gpg-agent to prompt for passphrases and
        communicates with GPG over the stdin for commnads
        (--command-fd) and stdout for status (--status-fd).
        """

        # the gpg binary to call
        gpg_binary = 'gpg'

        # a list of key => value commandline options
        #
        # to pass a flag without options, use None as the value
        options = { 'status-fd': 1,
                    'command-fd': 0,
                    'no-tty': None,
                    'use-agent': None,
                    'with-colons': None,
                    'with-fingerprint': None,
                    'fixed-list-mode': None,
                    'list-options': 'show-sig-subpackets,show-uid-validity,show-unusable-uids,show-unusable-subkeys,show-keyring,show-sig-expire',
                    }

        def __init__(self, homedir=None):
                """f"""
                if homedir is None:
                        if 'GPG_HOME' in os.environ:
                                self.homedir = os.environ['GPG_HOME']
                else:
                        os.environ['GPG_HOME'] = homedir

        def set_option(self, option, value = None):
                """set an option to pass to gpg

                this adds the given 'option' commandline argument with
                the value 'value'. to pass a flag without an argument,
                use 'None' for value"""
                self.options[option] = value

        def unset_option(self, option):
                """remove an option from the gpg commandline"""
                if option in self.options:
                        del self.options[option]
                else:
                        return false

        def build_command(self, command):
                """internal helper to build a proper gpg commandline

                this will add relevant arguments around the gpg
                binary.

                like the options arguments, the command is expected to
                be a regular gpg command with the -- stripped. the --
                are added before being called. this is to make the
                code more readable, and eventually support other
                backends that actually make more sense.

                this uses build_command to create a commandline out of
                the 'options' dictionnary, and appends the provided
                command at the end. this is because order of certain
                options matter in gpg, where some options (like
                --recv-keys) are expected to be at the end.

                it is here that the options dictionnary is converted
                into a list. the command argument is expected to be a
                list of arguments that can be converted to strings. if
                it is not a list, it is cast into a list."""
                options = []
                for left, right in self.options.iteritems():
                        options += ['--' + left]
                        if right is not None:
                                options += [str(right)]
                if type(command) is str:
                        command = [command]
                if len(command) > 0:
                        command[0] = '--' + command[0]
                return [self.gpg_binary] + options + command

        def call_command(self, command, stdin=None):
                """internal wrapper to call a GPG commandline

                this will call the command generated by
                build_command() and setup a regular pipe to the
                subcommand.

                this assumes that we have the status-fd on stdout and
                command-fd on stdin, but could really be used in any
                other way.

                we pass the stdin argument in the standard input of
                gpg and we keep the output in the stdout and stderr
                array. the exit code is in the returncode variable.
                """
                proc = subprocess.Popen(self.build_command(command), 0, None, subprocess.PIPE, subprocess.PIPE, subprocess.PIPE)
                (self.stdout, self.stderr) = proc.communicate(stdin)
                self.returncode = proc.returncode
                return proc.returncode == 0

        def version(self, type='short'):
                self.call_command(['version'])
                if type is not 'short': raise TypeError('invalid type')
                m = re.search('gpg \(GnuPG\) (\d+.\d+(?:.\d+)*)', self.stdout)
                return m.group(1)

        def import_data(self, data):
                """Import OpenPGP data blocks into the keyring.

                This takes actual OpenPGP data, ascii-armored or not,
                gpg will gladly take it. This can be signatures,
                public, private keys, etc.

                You may need to set import-flags to import
                non-exportable signatures, however.
                """
                self.call_command(['import'], data)
                return self.returncode == 0

        def export_data(self, fpr):
                """Export OpenPGP data blocks from the keyring.

                This exports actual OpenPGP data, by default in binary
                format, but can also be exported asci-armored by
                setting the 'armor' option."""
                self.call_command(['export', fpr])
                return self.stdout

        def fetch_keys(self, fpr, keyserver = None):
                """Download keys from a keyserver into the local keyring

                This expects a fingerprint (or a at least a key id).

                Returns true if the command succeeded.
                """
                if keyserver:
                        self.set_option('keyserver', keyserver)
                self.call_command(['recv-keys', fpr])
                return self.returncode == 0
                
        def sign_key_and_forget(self, fpr, sign_key, local = False):
                "Sign key using sign_key. Signature is exportable if local is False"
                # Values copied from <gpg-error.h>
                GPG_ERR_CONFLICT = 70
                GPG_ERR_UNUSABLE_PUBKEY = 53
                val_dict = self.common_dict.copy()
                val_dict.update({
                                "start keyedit.prompt": ("sign", (local and "lsign") or "sign"),
                                "sign keyedit.sign_all.okay": ("sign", "Y"),
                                "sign sign_uid.expire": ("sign", "Y"),
                                "sign sign_uid.class": ("sign", "0"),
                                "sign sign_uid.okay": ("okay", "Y"),
                                "okay keyedit.prompt": ("quit", "quit"),
                                "error ALREADY_SIGNED": GPG_ERR_CONFLICT,
                                "error sign keyedit.prompt": GPG_ERR_UNUSABLE_PUBKEY
                                })
                out = Data()
                #self.context.signers_clear()
                #self.context.signers_add(sign_key)
                key = self.context.get_key(fpr, 0)
                # XXX: bug: this will yield a pyme.errors.GPGMEError: Unspecified source: General error (0,1) if the key is already signed
                self.context.op_edit(key, self.editor_func, val_dict, out)

        def sign_key_and_forget_manual(self, fpr):
                """sign a key already present in the temporary keyring"""
                # command from caff: gpg-sign --local-user $local_user --homedir=$GNUPGHOME --secret-keyring $secret_keyring --no-auto-check-trustdb --trust-model=always --edit sign
                command = ['--keyring', self.keyring, '--secret-keyring', self.secret_keyring, '--sign-key', fpr]
                proc = subprocess.Popen(command, 0, None, subprocess.PIPE)
                proc.stdin.write("y\n")

                command = ['gpg', '--homedir', self.homedir, '--export', '--armor', fpr]
                proc = subprocess.Popen(command)
                key = proc.stdout.read()
                return


class GpgTemp(Gpg):
        def __init__(self):
                """Override the parent class to generate a temporary
                GPG home that gets destroyed at the end of
                operations."""

                # Create tempdir for gpg operations
                Gpg.__init__(self, tempfile.mkdtemp(prefix="monkeysign-"))

        def __del__(self):
                shutil.rmtree(os.environ['GPG_HOME'])

