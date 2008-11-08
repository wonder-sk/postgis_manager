
from ui.DlgTableProperties_ui import Ui_DlgTableProperties
from DlgFieldProperties import DlgFieldProperties
from DlgCreateConstraint import DlgCreateConstraint
from DlgCreateIndex import DlgCreateIndex
from DlgDbError import DlgDbError

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import postgis_utils


class SimpleTableModel(QStandardItemModel):
	def __init__(self, parent, header):
		QStandardItemModel.__init__(self, 0, len(header), parent)
		self.header = header
		
	def headerData(self, section, orientation, role):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			return QVariant(self.header[section])
		return QVariant()

class TableFieldsModel(SimpleTableModel):
	
	def __init__(self, parent):
		SimpleTableModel.__init__(self, parent, ['#', 'Name', 'Type', 'Null', 'Default'])

class TableConstraintsModel(SimpleTableModel):
	
	def __init__(self, parent):
		SimpleTableModel.__init__(self, parent, ['Name', 'Type', 'Column(s)'])

class TableIndexesModel(SimpleTableModel):
	
	def __init__(self, parent):
		SimpleTableModel.__init__(self, parent, ['Name', 'Column(s)'])
		
	


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
		
		m = TableConstraintsModel(self)
		self.viewConstraints.setModel(m)
		self.populateConstraints()
		
		m = TableIndexesModel(self)
		self.viewIndexes.setModel(m)
		self.populateIndexes()
		
		self.connect(self.btnAddColumn, SIGNAL("clicked()"), self.addColumn)
		self.connect(self.btnEditColumn, SIGNAL("clicked()"), self.editColumn)
		self.connect(self.btnDeleteColumn, SIGNAL("clicked()"), self.deleteColumn)
		
		self.connect(self.btnAddConstraint, SIGNAL("clicked()"), self.addConstraint)
		self.connect(self.btnDeleteConstraint, SIGNAL("clicked()"), self.deleteConstraint)
		
		self.connect(self.btnAddIndex, SIGNAL("clicked()"), self.createIndex)
		self.connect(self.btnAddSpatialIndex, SIGNAL("clicked()"), self.createSpatialIndex)
		self.connect(self.btnDeleteIndex, SIGNAL("clicked()"), self.deleteIndex)
		

		
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
			DlgDbError.showError(e, self)
	
	
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
				self.db.table_delete_geometry_column(self.table, column, self.schema)
			else:
				self.db.table_delete_column(self.table, column, self.schema)
				
			self.populateFields()
		except postgis_utils.DbError, e:
			DlgDbError.showError(e, self)

	def _field_by_number(self, num):
		""" return field specified by its number or None if doesn't exist """
		for fld in self.fields:
			if fld.num == num:
				return fld
		return None
		
	
	def populateConstraints(self):
		m = self.viewConstraints.model()
		m.clear()
		
		self.constraints = self.db.get_table_constraints(self.table, self.schema)
		
		for con in self.constraints:
			# name
			item_name = QStandardItem(con.name)
			# type
			if   con.con_type == con.TypeCheck: con_type = "Check"
			elif con.con_type == con.TypeForeignKey: con_type = "Foreign key"
			elif con.con_type == con.TypePrimaryKey: con_type = "Primary key"
			elif con.con_type ==  con.TypeUnique: con_type = "Unique"
			item_type = QStandardItem(con_type)
			# key(s)
			cols = ""
			for col in con.keys:
				if len(cols) != 0: cols += ", "
				cols += self._field_by_number(col).name
			item_columns = QStandardItem(cols)
			m.appendRow( [ item_name, item_type, item_columns ] )


	def addConstraint(self):
		""" add primary key or unique constraint """
		
		dlg = DlgCreateConstraint(self, self.db, self.table, self.schema)
		if not dlg.exec_():
			return
		
		column = str(dlg.cboColumn.currentText())
		
		try:
			if dlg.radPrimaryKey.isChecked():
				self.db.table_add_primary_key(self.table, column, self.schema)
			else:
				self.db.table_add_unique_constraint(self.table, column, self.schema)
		except postgis_utils.DbError, e:
			DlgDbError.showError(e, self)
			return
	
		# refresh constraints
		self.populateConstraints()
	
	
	def deleteConstraint(self):
		""" delete a constraint """
		
		num = self.currentConstraint()
		if num == -1:
			return

		m = self.viewConstraints.model()
		con_name = m.item(num, 0).text()

		res = QMessageBox.question(self, "are you sure", "really delete constraint '%s' ?" % con_name, QMessageBox.Yes | QMessageBox.No)
		if res != QMessageBox.Yes:
			return
		
		try:
			self.db.table_delete_constraint(self.table, con_name, self.schema)
		except postgis_utils.DbError, e:
			DlgDbError.showError(e, self)
			return
		
		# refresh constraints
		self.populateConstraints()

	
	def currentConstraint(self):
		""" returns row index of selected index """
		sel = self.viewConstraints.selectionModel()
		indexes = sel.selectedRows()
		if len(indexes) == 0:
			QMessageBox.information(self, "sorry", "nothing selected")
			return -1
		return indexes[0].row()


	def populateIndexes(self):
		m = self.viewIndexes.model()
		m.clear()
		
		self.indexes = self.db.get_table_indexes(self.table, self.schema)
		
		for idx in self.indexes:
			item_name = QStandardItem(idx.name)
			cols = ""
			for col in idx.columns:
				if len(cols) != 0: cols += ", "
				cols += self._field_by_number(col).name
			item_columns = QStandardItem(cols)
			m.appendRow( [ item_name, item_columns ] )


	def createIndex(self):
		""" create an index """
		
		dlg = DlgCreateIndex(self, self.db, self.table, self.schema)
		if not dlg.exec_():
			return
		
		# refresh indexes
		self.populateIndexes()
		
		
	def createSpatialIndex(self):
		""" asks for every geometry column whether it should create an index for it """
		
		# TODO: first check whether the index doesn't exist already
		try:
			for fld in self.fields:
				if fld.data_type == 'geometry':
					res = QMessageBox.question(self, "create?", "create spatial index for field "+fld.name+"?", QMessageBox.Yes | QMessageBox.No)
					if res == QMessageBox.Yes:
						self.db.create_spatial_index(self.table, self.schema, fld.name)
		except postgis_utils.DbError, e:
			DlgDbError.showError(e, self)
			return
	
		# refresh indexes
		self.populateIndexes()
	
	
	def currentIndex(self):
		""" returns row index of selected index """
		sel = self.viewIndexes.selectionModel()
		indexes = sel.selectedRows()
		if len(indexes) == 0:
			QMessageBox.information(self, "sorry", "nothing selected")
			return -1
		return indexes[0].row()
	
	
	def deleteIndex(self):
		""" delete currently selected index """
		
		num = self.currentIndex()
		if num == -1:
			return

		m = self.viewIndexes.model()
		idx_name = m.item(num, 0).text()

		res = QMessageBox.question(self, "are you sure", "really delete index '%s' ?" % idx_name, QMessageBox.Yes | QMessageBox.No)
		if res != QMessageBox.Yes:
			return
		
		try:
			self.db.delete_index(idx_name, self.schema)
		except postgis_utils.DbError, e:
			DlgDbError.showError(e, self)
			return
		
		# refresh indexes
		self.populateIndexes()
