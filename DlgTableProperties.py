
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
		
		self.fields = self.db.get_table_fields(self.table, self.schema)
		
		for fld in self.fields:
			item_num = QStandardItem(str(fld.num))
			item_name = QStandardItem(fld.name)
			item_type = QStandardItem(fld.data_type)
			item_null = QStandardItem(str(not fld.notnull))
			if fld.hasdefault:
				item_default = QStandardItem(fld.default)
			else:
				item_default = QStandardItem()
			m.appendRow( [ item_num, item_name, item_type, item_null, item_default ] )
		
		
	def currentColumn(self):
		""" returns row index of selected column """
		sel = self.viewFields.selectionModel()
		indexes = sel.selectedRows()
		if len(indexes) == 0:
			QMessageBox.information(self, "sorry", "nothing selected")
			return -1
		return indexes[0].row()


	def addColumn(self):
		""" open dialog to set column info and add column to table """
		
		dlg = DlgFieldProperties(self)
		if not dlg.exec_():
			return
		
		name = str(dlg.editName.text())
		data_type = str(dlg.cboType.currentText())
		is_null = dlg.chkNull.isChecked()
		default = str(dlg.editDefault.text())
		
		new_field = postgis_utils.TableField(name, data_type, is_null, default)
	
		try:
			# add column to table
			self.db.table_add_column(self.table, new_field, self.schema)
			self.populateFields()
		except postgis_utils.DbError, e:
			QMessageBox.information(self, "sorry", "couldn't add column:\n"+e.message)
	
	
	def editColumn(self):
		""" open dialog to change column info and alter table appropriately """

		num = self.currentColumn()
		if num == -1:
			return
		
		m = self.viewFields.model()
		# get column in table
		# (there can be missing number if someone deleted a column)
		column = str(m.item(num, 1).text())
		for col in self.fields:
			if col.name == column:
				break
		print col.num, col.name
		
		dlg = DlgFieldProperties(self, col)
		if not dlg.exec_():
			return
		
		new_name = str(dlg.editName.text())
		new_data_type = str(dlg.cboType.currentText())
		new_is_null = dlg.chkNull.isChecked()
		new_default = str(dlg.editDefault.text())
		
		try:
			if new_name != col.name:
				self.db.table_column_rename(self.table, col.name, new_name, self.schema)
			if new_data_type != col.data_type:
				self.db.table_column_set_type(self.table, new_name, new_data_type, self.schema)
			if new_is_null == col.notnull:
				self.db.table_column_set_null(self.table, new_name, new_is_null, self.schema)
			if len(new_default) > 0 and new_default != col.default:
				self.db.table_column_set_default(self.table, new_name, new_default, self.schema)
			if len(new_default) == 0 and col.hasdefault:
				self.db.table_column_set_default(self.table, new_name, None, self.schema)
				
			self.populateFields()
		except postgis_utils.DbError, e:
			QMessageBox.critical(self, "sorry", "couln't alter column:\n%s\nQUERY:\n%s" % (e.message, e.query))
	
	
	def deleteColumn(self):
		""" delete currently selected column """
		
		num = self.currentColumn()
		if num == -1:
			return
		
		m = self.viewFields.model()
		column = m.item(num, 1).text()
		data_type = m.item(num, 2).text()
		
		res = QMessageBox.question(self, "are you sure", "really delete column '%s' ?" % column, QMessageBox.Yes | QMessageBox.No)
		if res != QMessageBox.Yes:
			return
		
		try:
			if data_type == "geometry":
				self.db.table_delete_geometry_column(table, column, schema)
			else:
				self.db.table_delete_column(table, column, schema)
				
			self.populateFields()
		except postgis_utils.DbError, e:
			QMessageBox.information(self, "sorry", "couldn't delete column:\n"+e.message)

