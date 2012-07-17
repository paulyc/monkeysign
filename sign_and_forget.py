import monkeysign

keyring = monkeysign.Keyring('/tmp/m')

fpr = '73CF7A82A1138982B64FE3DAD1CF7387343CA353'
sign_key = '8DC901CE64146C048AD50FBB792152527B75921E'

keyring.fetch_key_from_keyring(fpr)
keyring.fetch_key_from_keyring(sign_key)
keyring.sign_key_and_forget(fpr, sign_key)
