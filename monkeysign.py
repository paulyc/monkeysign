import os, tempfile, shutil, subprocess

from pyme.core import Context, Data

class KeyNotFound(Exception):
        def __init__(self, msg=None):
                self.msg = msg
        def __repr__(self):
                return self.msg

class Keyring():
        # secret keyring used to sign keys
        secret_keyring = os.environ['HOME'] + '/.gnupg/secring.gpg'

        # extra keyring to add, this should have the public key from the above keyring
        keyring = os.environ['HOME'] + '/.gnupg/pubring.gpg'

        # the GPG_HOME we are operating on, initialized to a temporary
        # directory if not provided in the constructor
        homedir = None

        # if homedir is set to a temporary directory, this is a copy
        # of homedir, so that we can safely delete it on destruction
        tmpdir = None

        # the default GPGME context we operate with, set to use the homedir defined above
        context = Context()

        # default settings to communicate with GPG --edit-key
        # taken from /usr/share/doc/python-pyme-doc/examples/pygpa.py
        common_dict = {
                "state": "start",
                "quit keyedit.save.okay": ("save", "Y"),
                "ignore NEED_PASSPHRASE": None,
                "ignore NEED_PASSPHRASE_SYM": None,
                "ignore BAD_PASSPHRASE": None,
                "ignore USERID_HINT": None
        }  

        def __init__(self, homedir=None):
                """Initialize the keyring object. This will yield undefined results if homedir is set to your regular GPG_HOME, so be careful."""
                self.homedir = homedir
                if self.homedir is None:
                        # Create tempdir for gpg operations
                        self.tmpdir = tempfile.mkdtemp(prefix="monkeysign-")
                        self.homedir = self.tmpdir
                # initialize the context to use the provided GPG_HOME
                self.context.set_engine_info(0, None, self.homedir)
                return

        def __del__(self):
                if self.tmpdir:
                        shutil.rmtree(self.tmpdir)

        # editing function, action depends on the val_dict
        # taken from /usr/share/doc/python-pyme-doc/examples/pygpa.py
        def editor_func(status, args, val_dict):
                prompt = "%s %s" % (val_dict["state"], args)
                if val_dict.has_key(prompt):
                        val_dict["state"] = val_dict[prompt][0]
                        return val_dict[prompt][1]
                elif args and not val_dict.has_key("ignore %s" % status2str[status]):
                        for error in ["error %s" % status2str[status], "error %s" % prompt]:
                                if val_dict.has_key(error):
                                        raise errors.GPGMEError(val_dict[error])
                        sys.stderr.write(_("Unexpected status and prompt in editor_func: " +
                                           "%s %s\n") % (status2str[status], prompt))
                        raise EOFError()
                return ""

        def fetch_key_from_keyring(self, fpr):
                """try to get the key from the user's keyring"""
                # temporary context that will actually look in the normal keyring
                c = Context()
                export_keys = Data()
                c.op_export(fpr, 0, export_keys)
                export_keys.seek(0,0)

                status = self.context.op_import(export_keys)
                if status:
                        # need better error reporting here - exception?
                        raise KeyNotFound(status)
                else:
                        result = self.context.op_import_result()
                        if result.considered == 0:
                                raise KeyNotFound("no keys found")

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
                command = ["/usr/bin/gpg", '--homedir', self.homedir, '--keyring', self.keyring, '--status-fd', "1", '--command-fd', '0', '--no-tty', '--use-agent', '--secret-keyring', self.secret_keyring, '--sign-key', fpr]
                proc = subprocess.Popen(command, 0, None, subprocess.PIPE)
                proc.stdin.write("y\n")

                command = ['gpg', '--homedir', self.homedir, '--export', '--armor', fpr]
                proc = subprocess.Popen(command)
                key = proc.stdout.read()
                return

