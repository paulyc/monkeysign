*.po: messages.pot
	msgmerge -U $@ $<

messages.pot: ../monkeysign/cli.py ../monkeysign/gtkui.py ../monkeysign/ui.py ../monkeysign/gpg.py
	pygettext -k_ -kN_ -D -o $@ $^
	xgettext -k_ -kN_ -L Python -j -o $@ $^
