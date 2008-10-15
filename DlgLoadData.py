
from DlgLoadData_ui import Ui_DlgLoadData

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class DlgLoadData(QDialog, Ui_DlgLoadData):

	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)

		self.connect(self.btnSelectShapefile, SIGNAL("clicked()"), self.onSelectShapefile)
		self.connect(self.btnSelectOutputFile, SIGNAL("clicked()"), self.onSelectOutputFile)
		self.connect(self.buttonBox.button(QDialogButtonBox.Ok), SIGNAL("clicked()"), self.onOk)
		
		# updates of UI
		for widget in [self.radCreate, self.radAppend, self.radCreateOnly, self.chkSrid, self.chkGeomColumn, self.chkEncoding]:
			self.connect(widget, SIGNAL("clicked()"), self.updateUi)
		
		self.populateSchemasTables()
		self.populateEncodings()
		self.updateUi()
		
	def populateSchemasTables(self):
		# TODO: populate with data from database
		pass
	
	def populateEncodings(self):
		# TODO: populate with some commonly used encodings
		pass
	
	def updateUi(self):
		allowDropTable = self.radCreate.isChecked()
		self.chkDropTable.setEnabled(allowDropTable)
		
		allowSetSrid = self.chkSrid.isChecked()
		self.editSrid.setEnabled(allowSetSrid)
		
		allowSetGeomColumn = self.chkGeomColumn.isChecked()
		self.editGeomColumn.setEnabled(allowSetGeomColumn)
		
		allowSetEncoding = self.chkEncoding.isChecked()
		self.cboEncoding.setEnabled(allowSetEncoding)

		
	def onOk(self):
		# TODO: do the ska, call shp2pg
		pass
		
	def onSelectShapefile(self):
		fileName = QFileDialog.getOpenFileName(self, "Open Shapefile", QString(), "Shapefiles (*.shp)")
		if fileName.isNull():
			return
		self.editShapefile.setText(fileName)
	
	def onSelectOutputFile(self):
		fileName = QFileDialog.getSaveFileName(self, "Save SQL as", QString(), "SQL files (*.sql);;All files (*.*)")
		if fileName.isNull():
			return
		self.editOutputFile.setText(fileName)
		


if __name__ == '__main__':
	import sys
	a = QApplication(sys.argv)
	dlg = DlgLoadData()
	dlg.show()
	sys.exit(a.exec_())