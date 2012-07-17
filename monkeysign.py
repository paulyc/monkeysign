import os, tempfile, shutil

class Keyring():

        # secret keyring used to sign keys
        secret_keyring = os.environ['HOME'] + '/.gnupg/secring.gpg'

        # extra keyring to add, this should have the public key from the above keyring
        keyring = os.environ['HOME'] + '/.gnupg/pubring.gpg'

        # Create tempdir for gpg operations
        homedir = tempfile.mkdtemp(prefix="monkeysign-")

        def __init__(self):
                return

        def __del__(self):
                shutil.rmtree(self.homedir)                

        def sign_key_and_forget(self, fpr):
                # command from caff: gpg-sign --local-user $local_user --homedir=$GNUPGHOME --secret-keyring $secret_keyring --no-auto-check-trustdb --trust-model=always --edit sign
                command = ["/usr/bin/gpg", '--homedir', self.tmpkeyring.homedir, '--keyring', self.keyring, '--status-fd', "1", '--command-fd', '0', '--no-tty', '--use-agent', '--secret-keyring', self.secret_keyring, '--sign-key', fpr]
                proc = subprocess.Popen(command, 0, None, subprocess.PIPE)
                proc.stdin.write("y\n")

                command = ['gpg', '--homedir', self.tmpkeyring.homedir, '--export', '--armor', fpr]
                proc = subprocess.Popen(command)
                key = proc.stdout.read()
                return

