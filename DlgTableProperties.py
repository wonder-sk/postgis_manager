
from DlgTableProperties_ui import Ui_DlgTableProperties
from DlgFieldProperties import DlgFieldProperties

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import postgis_utils


class TableFieldsModel(QStandardItemModel):
	
	def __init__(self, parent):
		QStandardItemModel.__init__(self, 0,4, parent)
		self.header = ['#', 'Name', 'Type', 'Null', 'Default']
		
	def headerData(self, section, orientation, role):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			return QVariant(self.header[section])
		return QVariant()



class DlgTableProperties(QDialog, Ui_DlgTableProperties):
	
	def __init__(self, db, schema, table, parent=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
		
		self.db = db
		self.schema = schema
		self.table = table
		
		m = TableFieldsModel(self)
		self.viewFields.setModel(m)
		self.populateFields()
		
		self.connect(self.btnAddColumn, SIGNAL("clicked()"), self.addColumn)
		self.connect(self.btnEditColumn, SIGNAL("clicked()"), self.editColumn)
		self.connect(self.btnDeleteColumn, SIGNAL("clicked()"), self.deleteColumn)
		
		
	def populateFields(self):
		""" load field information from database """
		
		m = self.viewFields.model()
		m.clear()
		
		flds = self.db.get_table_fields(self.table, self.schema)
		for fld in flds:
			item_num = QStandardItem(str(fld.num))
			item_name = QStandardItem(fld.name)
			item_type = QStandardItem(fld.data_type)
			item_null = QStandardItem(str(not fld.notnull))
			item_default = QStandardItem(str(fld.hasdefault))
			m.appendRow( [ item_num, item_name, item_type, item_null, item_default ] )
		
		
	def currentColumn(self):
		""" returns selected column """
		sel = self.viewFields.selectionModel()
		indexes = sel.selectedRows()
		if len(indexes) == 0:
			QMessageBox.information(self, "sorry", "nothing selected")
			return None
		return indexes[0]


	def addColumn(self):
		dlg = DlgFieldProperties(self)
		if not dlg.exec_():
			return
		
		name = dlg.editName.text()
		data_type = dlg.cboType.currentText()
		is_null = dlg.chkNull.isChecked()
		default = dlg.editDefault.text()
		
		new_field = postgis_utils.TableField(name, data_type, is_null, default)
	
		try:
			# add column to table
			self.db.table_add_column(self.table, new_field, self.schema)
			self.populateFields()
		except postgis_utils.DbError, e:
			QMessageBox.information(self, "sorry", "couldn't add column:\n"+e.message)
	
	
	def editColumn(self):

		col = self.currentColumn()
		if not col:
			return
		
		dlg = DlgFieldProperties(self, col)
		if not dlg.exec_():
			return
		
		# TODO: edit column
		
	
	def deleteColumn(self):
		
		col = self.currentColumn()
		if not col:
			return
		
		m = self.viewFields.model()
		row = col.row()
		column = m.item(row, 1).text()
		data_type = m.item(row, 2).text()
		
		res = QMessageBox.question(self, "are you sure", "really delete column '%s' ?" % column, QMessageBox.Yes | QMessageBox.No)
		if res != QMessageBox.Yes:
			return
		
		try:
			if data_type == "geometry":
				self.db.table_delete_geometry_column(table, column, schema)
			else:
				self.db.table_delete_column(table, column, schema)
		except postgis_utils.DbError, e:
			QMessageBox.information(self, "sorry", "couldn't delete column:\n"+e.message)

