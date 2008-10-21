
from ManagerDialog_ui import Ui_ManagerDialog
from DlgCreateTable import DlgCreateTable
from DlgLoadData import DlgLoadData
from DlgDumpData import DlgDumpData
from DatabaseModel import TableItem, SchemaItem, DatabaseModel

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import postgis_utils
import resources



class ManagerDialog(QDialog, Ui_ManagerDialog):
	
	def __init__(self, db, parent=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
		
		self.db = db
		
		self.dbModel = DatabaseModel(self, self.db)
		self.tree.setModel(self.dbModel)
		
		self.tree.expandAll()
		self.tree.resizeColumnToContents(0)
		
		self.connect(self.tree, SIGNAL("clicked(const QModelIndex&)"), self.itemActivated)
		self.connect(self.tree.model(), SIGNAL("dataChanged(const QModelIndex &, const QModelIndex &)"), self.refreshTable)
		self.connect(self.btnCreateTable, SIGNAL("clicked()"), self.createTable)
		self.connect(self.btnDeleteTable, SIGNAL("clicked()"), self.deleteTable)
		self.connect(self.btnCreateSchema, SIGNAL("clicked()"), self.createSchema)
		self.connect(self.btnDeleteSchema, SIGNAL("clicked()"), self.deleteSchema)
		self.connect(self.btnLoadData, SIGNAL("clicked()"), self.loadData)
		self.connect(self.btnDumpData, SIGNAL("clicked()"), self.dumpData)
		
		
		
	def refreshTable(self):
		self.tree.model().loadFromDb()
		self.tree.model().reset()
		self.tree.expandAll()
		
	def itemActivated(self, index):
		
		item = index.internalPointer()
		
		if isinstance(item, SchemaItem):
			html = "<h1>%s</h1> (schema)<p>Tables: %d<br>Owner: %s" % (item.name, item.childCount(), item.owner)
		elif isinstance(item, TableItem):
			if item.is_view:
				reltype = "View"
			else:
				reltype = "Table"
			html = "<h1>%s</h1> (%s)<br>Owner: %s<br>Rows (estimation): %d<br>Pages: %d<p>Geometry: %s" % (item.name, reltype, item.owner, item.row_count, item.page_count, item.geom_type)
			html += "<table><tr><th>#<th>Name<th>Type<th>Null"
			for fld in self.db.get_table_fields(item.name):
				if fld.notnull: is_null_txt = "N"
				else: is_null_txt = "Y"
				html += "<tr><td>%s<td>%s<td>%s<td>%s" % (fld.num, fld.name, fld.data_type, is_null_txt)
			html += "</table>"
		else:
			html = "---"
		self.txtMetadata.setHtml(html)

	def createTable(self):
		dlg = DlgCreateTable(self, self.db)
		self.connect(dlg, SIGNAL("databaseChanged()"), self.refreshTable)
		dlg.exec_()
		
	def deleteTable(self):
		
		sel = self.tree.selectionModel()
		indexes = sel.selectedRows()
		if len(indexes) == 0:
			QMessageBox.information(self, "sorry", "select a table/view for deletion!")
			return
		if len(indexes) > 1:
			QMessageBox.information(self, "sorry", "select only one table/view")
			return
			
		index = indexes[0]
		ptr = index.internalPointer()
		if not isinstance(ptr, TableItem):
			QMessageBox.information(self, "sorry", "select a TABLE or VIEW for deletion")
			return
		
		res = QMessageBox.question(self, "hey!", "really delete table/view %s ?" % ptr.name, QMessageBox.Yes | QMessageBox.No)
		if res != QMessageBox.Yes:
			return
		
		try:
			if ptr.is_view:
				self.db.delete_view(ptr.name)
			else:
				self.db.delete_table(ptr.name)
			self.refreshTable()
			QMessageBox.information(self, "good", "table/view deleted.")
		except postgis_utils.DbError, e:
			QMessageBox.critical(self, "error", "Message:\n%s\nQuery:\n%s\n" % (e.message, e.query))
		
	
	def createSchema(self):
		
		(name, ok) = QInputDialog.getText(self, "Schema name", "Enter name for new schema")
		if not name.isEmpty():
			self.db.create_schema(name)
			self.refreshTable()
			QMessageBox.information(self, "good", "schema created.")

	
	def deleteSchema(self):
		sel = self.tree.selectionModel()
		indexes = sel.selectedRows()
		if len(indexes) == 0:
			QMessageBox.information(self, "sorry", "select a schema for deletion!")
			return
	
		index = indexes[0]
		ptr = index.internalPointer()
		if not isinstance(ptr, SchemaItem):
			QMessageBox.information(self, "sorry", "select a SCHEMA for deletion")
			return
		
		res = QMessageBox.question(self, "hey!", "really delete schema %s ?" % ptr.name, QMessageBox.Yes | QMessageBox.No)
		if res != QMessageBox.Yes:
			return
		
		self.db.delete_schema(ptr.name)
		self.refreshTable()
		QMessageBox.information(self, "good", "schema deleted.")
		
		
	def loadData(self):
		dlg = DlgLoadData(self, self.db)
		dlg.exec_()

	def dumpData(self):
		dlg = DlgDumpData(self, self.db)
		dlg.exec_()

