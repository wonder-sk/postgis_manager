
GEN_FILES = DlgCreateTable_ui.py DlgLoadData_ui.py resources.py DlgDumpData_ui.py DlgFieldProperties_ui.py DlgTableProperties_ui.py DlgAbout_ui.py DlgSqlWindow_ui.py DlgCreateIndex_ui.py DlgCreateConstraint_ui.py

all: $(GEN_FILES)

DlgCreateTable_ui.py: DlgCreateTable.ui
	pyuic4 -o DlgCreateTable_ui.py DlgCreateTable.ui

DlgCreateConstraint_ui.py: DlgCreateConstraint.ui
	pyuic4 -o DlgCreateConstraint_ui.py DlgCreateConstraint.ui

DlgCreateIndex_ui.py: DlgCreateIndex.ui
	pyuic4 -o DlgCreateIndex_ui.py DlgCreateIndex.ui

DlgFieldProperties_ui.py: DlgFieldProperties.ui
	pyuic4 -o DlgFieldProperties_ui.py DlgFieldProperties.ui

DlgTableProperties_ui.py: DlgTableProperties.ui
	pyuic4 -o DlgTableProperties_ui.py DlgTableProperties.ui

DlgLoadData_ui.py: DlgLoadData.ui
	pyuic4 -o DlgLoadData_ui.py DlgLoadData.ui

DlgDumpData_ui.py: DlgDumpData.ui
	pyuic4 -o DlgDumpData_ui.py DlgDumpData.ui

DlgAbout_ui.py: DlgAbout.ui
	pyuic4 -o DlgAbout_ui.py DlgAbout.ui

DlgSqlWindow_ui.py: DlgSqlWindow.ui
	pyuic4 -o DlgSqlWindow_ui.py DlgSqlWindow.ui

resources.py: resources.qrc
	pyrcc4 -o resources.py resources.qrc


clean:
	rm -f $(GEN_FILES) *.pyc

package:
	cd .. && rm -f postgis_manager.zip && zip -r postgis_manager.zip postgis_manager -x \*.svn-base -x \*.pyc
