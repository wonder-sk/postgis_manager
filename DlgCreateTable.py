
from DlgCreateTable_ui import Ui_DlgCreateTable

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class TableFieldsDelegate(QItemDelegate):
	""" delegate with some special item editors """
	
	fieldTypes = ["integer", "bigint", "smallint", # integers
	              "serial", "bigserial", # auto-incrementing ints
								"real", "double precision", "numeric", # floats
								"varchar(n)", "char(n)", "text", # strings
								"date", "time", "timestamp"] # date/time
	
	def __init__(self, parent=None):
		QItemDelegate.__init__(self, parent)
		
	def createEditor(self, parent, option, index):
		# special combobox for field type
		if index.column() == 0:
			return QLineEdit(parent)
		elif index.column() == 1:
			cbo = QComboBox(parent)
			cbo.setEditable(True)
			cbo.setAutoCompletion(True)
			cbo.setFrame(False)
			for item in self.fieldTypes:
				cbo.addItem(item)
			return cbo
		return QItemDelegate.createEditor(self, parent, option, index)
		
	def setEditorData(self, editor, index):
		""" load data from model to editor """
		m = index.model()
		if index.column() == 0:
			txt = m.data(index, Qt.DisplayRole).toString()
			editor.setText(txt)
		elif index.column() == 1:
			txt = m.data(index, Qt.DisplayRole).toString()
			editor.setEditText(txt)
		
	def setModelData(self, editor, model, index):
		""" save data from editor back to model """
		if index.column() == 0:
			model.setData(index, QVariant(editor.text()))
		elif index.column() == 1:
			model.setData(index, QVariant(editor.currentText()))


class TableFieldsModel(QStandardItemModel):
	
	def __init__(self, parent):
		QStandardItemModel.__init__(self, 0,2, parent)
		
	def headerData(self, section, orientation, role):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			if section==0:
				return QVariant("Name")
			elif section==1:
				return QVariant("Type")
		return QVariant()


class DlgCreateTable(QDialog, Ui_DlgCreateTable):
	
	def __init__(self, db=None, parent=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
		
		self.db = db
		
		m = TableFieldsModel(self)
		self.fields.setModel(m)
		
		d = TableFieldsDelegate(self)
		self.fields.setItemDelegate(d)
		
		b = QPushButton("&Create")
		self.buttonBox.addButton(b, QDialogButtonBox.ActionRole)

		self.connect(self.btnAddField, SIGNAL("clicked()"), self.addField)
		self.connect(self.btnDeleteField, SIGNAL("clicked()"), self.deleteField)
		self.connect(b, SIGNAL("clicked()"), self.createTable)
		
		self.connect(self.chkGeomColumn, SIGNAL("clicked()"), self.updateUi)
		
		self.updateUi()
		
	def updateUi(self):
		useGeom = self.chkGeomColumn.isChecked()
		self.cboGeomType.setEnabled(useGeom)
		self.editGeomColumn.setEnabled(useGeom)
		self.chkSpatialIndex.setEnabled(useGeom)
		
	def addField(self):
		""" add new field to the end of field table """
		m = self.fields.model()
		newRow = m.rowCount()
		m.insertRows(newRow,1)
		
		indexName = m.index(newRow,0,QModelIndex())
		indexType = m.index(newRow,1,QModelIndex())
		
		m.setData(indexName, QVariant("new field"))
		m.setData(indexType, QVariant("integer"))
		
		# selects the new row
		sel = self.fields.selectionModel()
		sel.select(indexName, QItemSelectionModel.Rows | QItemSelectionModel.ClearAndSelect)
		
		# starts editing
		self.fields.edit(indexName)
		
	
	def deleteField(self):
		""" delete selected field """
		sel = self.fields.selectionModel().selectedRows()
		if len(sel) < 1:
			QMessageBox.information(self, "sorry", "no field selected")
		else:
			self.fields.model().removeRows(sel[0].row(),1)

	def createTable(self):
		""" create table with chosen fields, optionally add a geometry column """
		
		# TODO: schema
		schema = 'public'
		
		table = str(self.editName.text())
		if len(table) == 0:
			QMessageBox.information(self, "sorry", "enter table name!")
			return
		
		m = self.fields.model()
		if m.rowCount() == 0:
			QMessageBox.information(self, "sorry", "add some fields!")
			return
		
		# TODO: SRID, dimension
		useGeomColumn = self.chkGeomColumn.isChecked()
		if useGeomColumn:
			geomColumn = str(self.editGeomColumn.text())
			geomType = str(self.cboGeomType.currentText())
			useSpatialIndex = self.chkSpatialIndex.isChecked()
			if len(geomColumn) == 0:
				QMessageBox.information(self, "sorry", "set geometry column name")
				return
		
		flds = []
		for row in xrange(m.rowCount()):
			fldName = str(m.data(m.index(row,0,QModelIndex())).toString())
			fldType = str(m.data(m.index(row,1,QModelIndex())).toString())
			flds.append( (fldName, fldType) )
				
		# commit to DB
		if self.db:
			self.db.createTable(table, flds)
			if useGeomColumn:
				self.db.add_geometry_column(table, geomType, schema, geomColumn)
				if useSpatialIndex:
					self.db.create_spatial_index(table, schema, geomColumn)
		else:
			print table, flds, useGeomColumn
			if useGeomColumn:
				print geomType, geomColumn


		QMessageBox.information(self, "Good", "everything went fine")


if __name__ == '__main__':
	import sys
	a = QApplication(sys.argv)
	dlg = DlgCreateTable()
	dlg.show()
	sys.exit(a.exec_())
