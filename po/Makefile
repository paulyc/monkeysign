# we strip the obsoleted entries from the template, otherwise they are naively copied in
*.po: messages.pot
	msgattrib --no-obsolete $< | msgmerge -U $@ -

messages.pot: ../monkeysign/cli.py ../monkeysign/gtkui.py ../monkeysign/ui.py ../monkeysign/gpg.py
	pygettext -k_ -kN_ -D -o $@ $^
	xgettext -k_ -kN_ -L Python -j -o $@ $^
