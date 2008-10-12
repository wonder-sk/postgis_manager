
ManagerDialog_ui.py: ManagerDialog.ui
	pyuic4 -o ManagerDialog_ui.py ManagerDialog.ui

all: ManagerDialog_ui.py

clean:
	rm -f ManagerDialog_ui.py *.pyc