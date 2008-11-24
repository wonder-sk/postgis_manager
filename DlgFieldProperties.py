
from ui.DlgFieldProperties_ui import Ui_DlgFieldProperties

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class DlgFieldProperties(QDialog, Ui_DlgFieldProperties):
	
	def __init__(self, parent=None, column=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
		
		fieldTypes = ["integer", "bigint", "smallint", # integers
	              "serial", "bigserial", # auto-incrementing ints
								"real", "double precision", "numeric", # floats
								"varchar", "char", "text", # strings
								"date", "time", "timestamp"] # date/time
		for item in fieldTypes:
			self.cboType.addItem(item)
		
		#self.column = column
		if column:
			self.editName.setText(column.name)
			self.cboType.setEditText(column.data_type)
			if column.modifier >= 0:
				self.editLength.setText(str(column.modifier))
			self.chkNull.setChecked(not column.notnull)
			if column.default:
				self.editDefault.setText(column.default)
		
		self.connect(self.buttonBox, SIGNAL("accepted()"), self.onOK)


	def onOK(self):
		""" first check whether everything's fine """
		
		if self.editName.text().count() == 0:
			QMessageBox.critical(self, "sorry", "field name must not be empty")
			return
		if self.cboType.currentText().count() == 0:
			QMessageBox.critical(self, "sorry", "field type must not be empty")
			return
		
		self.accept()
