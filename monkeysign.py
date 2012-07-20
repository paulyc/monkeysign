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

        options = ['--status-fd', '1', '--command-fd', '0', '--no-tty', '--use-agent']

        def __init__(self, homedir=None):
                """f"""
                if homedir is None:
                        if 'GPG_HOME' in os.environ:
                                self.homedir = os.environ['GPG_HOME']
                else:
                        os.environ['GPG_HOME'] = homedir

        def add_option(self, option):
                """half-assed. we need an associative array of options and use get/setters"""
                self.options += option

        def build_command(self, command):
                """internal wrapper around gpg command

                this will add relevant arguments around the gpg binary"""
                return [self.gpg_binary] + self.options + command

        def call_command(self, command, data=None):
                """internal wrapper to call a GPG pipe"""
                proc = subprocess.Popen(self.build_command(command), 0, None, subprocess.PIPE, subprocess.PIPE, subprocess.PIPE)
                (self.stdout, self.stderr) = proc.communicate(data)
                self.returncode = proc.returncode
                return proc.returncode == 0

        def version(self, type='short'):
                self.call_command(['--version'])
                if type is not 'short': raise TypeError('invalid type')
                m = re.search('gpg \(GnuPG\) (\d+.\d+(?:.\d+)*)', self.stdout)
                return m.group(1)

        def import_data(self, data):
                return self.call_command(['--import'], data)

        def export_data(self, fpr):
                self.call_command(['--export', fpr])
                return self.stdout

        def fetch_keys(self, fpr, keyserver = None):
                """Get keys from a keyserver"""
                command = ['--recv-keys', fpr]
                if keyserver:
                        command[len(command):] = ['--keyserver', keyserver]
                proc = subprocess.Popen(self.build_command(command))
                # needs error handling
                
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

