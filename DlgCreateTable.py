
from DlgCreateTable_ui import Ui_DlgCreateTable
from DlgFieldProperties import DlgFieldProperties

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import postgis_utils

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
		else:
			# use default
			QItemDelegate.setEditorData(self, editor, index)
		
	def setModelData(self, editor, model, index):
		""" save data from editor back to model """
		if index.column() == 0:
			model.setData(index, QVariant(editor.text()))
		elif index.column() == 1:
			model.setData(index, QVariant(editor.currentText()))
		else:
			# use default
			QItemDelegate.setModelData(self, editor, model, index)


class TableFieldsModel(QStandardItemModel):
	
	def __init__(self, parent):
		QStandardItemModel.__init__(self, 0,3, parent)
		self.header = ['Name', 'Type', 'Null']
		
	def headerData(self, section, orientation, role):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			return QVariant(self.header[section])
		return QVariant()


class DlgCreateTable(QDialog, Ui_DlgCreateTable):
	
	def __init__(self, parent=None, db=None):
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
		self.connect(self.btnFieldUp, SIGNAL("clicked()"), self.fieldUp)
		self.connect(self.btnFieldDown, SIGNAL("clicked()"), self.fieldDown)
		self.connect(b, SIGNAL("clicked()"), self.createTable)
		
		self.connect(self.chkGeomColumn, SIGNAL("clicked()"), self.updateUi)
		
		self.populateSchemas()
		
		self.updateUi()
		
		
	def populateSchemas(self):
		
		if not self.db:
			return
		
		schemas = self.db.list_schemas()
		self.cboSchema.clear()
		for schema in schemas:
			self.cboSchema.addItem(schema[1])
		
		
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
		indexNull = m.index(newRow,2,QModelIndex())
		
		m.setData(indexName, QVariant("new_field"))
		m.setData(indexType, QVariant("integer"))
		m.setData(indexNull, QVariant(False))
		
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
			
	def fieldUp(self):
		""" TODO: move selected field up """
		pass

	def fieldDown(self):
		""" TODO: move selected field down """
		pass
	
	def createTable(self):
		""" create table with chosen fields, optionally add a geometry column """
		
		schema = str(self.cboSchema.currentText())
		if len(schema) == 0:
			QMessageBox.information(self, "sorry", "select scheme!")
			return
		
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
			fldNull = m.data(m.index(row,2,QModelIndex())).toBool()
			
			flds.append( postgis_utils.TableField(fldName, fldType, fldNull) )
				
		if self.db:
			
			# commit to DB
			try:
				self.db.create_table(table, flds)
				if useGeomColumn:
					self.db.add_geometry_column(table, geomType, schema, geomColumn)
					# commit data definition changes, otherwise index can't be built
					self.db.con.commit()
					if useSpatialIndex:
						self.db.create_spatial_index(table, schema, geomColumn)
				self.emit(SIGNAL("databaseChanged()"))
			except postgis_utils.DbError, e:
				self.db.con.rollback()
				QMessageBox.critical(self, "DB error", e.message+"\nSQL query:\n"+e.query)
				return
					
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
