
GEN_FILES = ManagerDialog_ui.py DlgCreateTable_ui.py DlgLoadData_ui.py

all: $(GEN_FILES)

DlgCreateTable_ui.py: DlgCreateTable.ui
	pyuic4 -o DlgCreateTable_ui.py DlgCreateTable.ui

ManagerDialog_ui.py: ManagerDialog.ui
	pyuic4 -o ManagerDialog_ui.py ManagerDialog.ui

DlgLoadData_ui.py: DlgLoadData.ui
	pyuic4 -o DlgLoadData_ui.py DlgLoadData.ui


clean:
	rm -f $(GEN_FILES) *.pyc
