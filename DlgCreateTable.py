
from DlgCreateTable_ui import Ui_DlgCreateTable

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class NewTableModel(QStandardItemModel):
	
	def __init__(self):
		QStandardItemModel.__init__(self, 0,2)
		
	def headerData(self, section, orientation, role):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			if section==0:
				return QVariant("Name")
			elif section==1:
				return QVariant("Type")
		return QVariant()

	""" TODO: custom delegates """

class DlgCreateTable(QDialog, Ui_DlgCreateTable):
	
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
		
		self.m = NewTableModel()
		self.fields.setModel(self.m)

		self.connect(self.btnAddField, SIGNAL("clicked()"), self.addField)
		self.connect(self.btnDeleteField, SIGNAL("clicked()"), self.deleteField)
		
	def addField(self):
		""" add new field to the end of field table """
		newRow = self.m.rowCount()
		self.m.insertRows(newRow,1)
		self.m.setData(self.m.index(newRow,0,QModelIndex()), QVariant("name"))
		self.m.setData(self.m.index(newRow,1,QModelIndex()), QVariant("type"))
		
	
	def deleteField(self):
		""" delete selected field """
		sel = self.fields.selectionModel().selectedRows()
		if len(sel) < 1:
			QMessageBox.information(self, "sorry", "no field selected")
		else:
			self.m.removeRows(sel[0].row(),1)



if __name__ == '__main__':
	import sys
	a = QApplication(sys.argv)
	dlg = DlgCreateTable()
	dlg.show()
	sys.exit(a.exec_())
