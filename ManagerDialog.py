
from ManagerDialog_ui import Ui_ManagerDialog
from DlgCreateTable import DlgCreateTable
from DlgLoadData import DlgLoadData
from DlgDumpData import DlgDumpData

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import sys

import postgis_utils
import resources

class TreeItem:
	
	def __init__(self, parent):
		self.parentItem = parent
		self.childItems = []
		
		if parent:
			parent.appendChild(self)
			
	def appendChild(self, child):
		self.childItems.append(child)
	
	def child(self, row):
		return self.childItems[row]
	
	def childCount(self):
		return len(self.childItems)
	
	def row(self):
		
		if self.parentItem:
			items = self.parentItem.childItems
			for (row,item) in enumerate(items):
				if item is self:
					return row
			print "CHYBAA", self, items
			
		return 0
	
	def parent(self):
		return self.parentItem
	
	def icon(self):
		return None



class DatabaseItem(TreeItem):
	def __init__(self, parent=None):
		TreeItem.__init__(self, parent)
	
	def data(self, column):
		return None

	
class SchemaItem(TreeItem):
	def __init__(self, name, parent):
		TreeItem.__init__(self, parent)
		self.name = name
		
		# load (shared) icon with first instance of schema item
		if not hasattr(SchemaItem, 'schemaIcon'):
			SchemaItem.schemaIcon = QIcon(":/icons/namespace.xpm")
	
	def data(self, column):
		if column == 0:
			return self.name
		else:
			return None
	
	def icon(self):
		return self.schemaIcon


class TableItem(TreeItem):
	
	def __init__(self, name, geom_type, is_view, parent):
		TreeItem.__init__(self, parent)
		self.name, self.geom_type, self.is_view = name, geom_type, is_view
		
		# load (shared) icon with first instance of table item
		if not hasattr(TableItem, 'tableIcon'):
			TableItem.tableIcon = QIcon(":/icons/table.xpm")
			TableItem.viewIcon = QIcon(":/icons/view.xpm")
		
	def data(self, column):
		if column == 0:
			return self.name
		elif column == 1:
			return self.geom_type
		else:
			return None
		
	def icon(self):
		if self.is_view:
			return self.viewIcon
		else:
			return self.tableIcon

def new_tree():
	
	rootItem = TreeItem(['tables'], None)
	sPublic = SchemaItem('public', rootItem)
	sG = SchemaItem('gis', rootItem)
	t1 = TableItem('roads', 'LINESTRING', False, sPublic)
	t2 = TableItem('sidla', 'POINT', False, sG)
	return rootItem



class TreeModel(QAbstractItemModel):
	
	def __init__(self, tree, parent=None, db=None):
		QAbstractItemModel.__init__(self, parent)
		self.tree = tree
		self.db = db
		self.header = ['Table', 'Geometry']
		
	def columnCount(self, parent):
		return 2
		
	def data(self, index, role):
		if not index.isValid():
			return QVariant()
		
		if role == Qt.DecorationRole and index.column() == 0:
			icon = index.internalPointer().icon()
			if icon: return QVariant(icon)
			
		if role != Qt.DisplayRole and role != Qt.EditRole:
			return QVariant()
		
		retval = index.internalPointer().data(index.column())
		if retval:
			return QVariant(retval)
		else:
			return QVariant()
	
	def flags(self, index):
		if not index.isValid():
			return 0
		
		flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable 
		if index.column() == 0:
			flags |= Qt.ItemIsEditable
		return flags
	
	def headerData(self, section, orientation, role):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole and section < len(self.header):
			return QVariant(self.header[section])
		return QVariant()

	def index(self, row, column, parent):
		if not self.hasIndex(row, column, parent):
			return QModelIndex()
		
		if not parent.isValid():
			parentItem = self.tree
		else:
			parentItem = parent.internalPointer()
		
		childItem = parentItem.child(row)
		if childItem:
			return self.createIndex(row, column, childItem)
		else:
			return QModelIndex()

	def parent(self, index):
		if not index.isValid():
			return QModelIndex()
		
		childItem = index.internalPointer()
		parentItem = childItem.parent()
		
		if parentItem == self.tree:
			return QModelIndex()
		
		return self.createIndex(parentItem.row(), 0, parentItem)

	def rowCount(self, parent):
		if parent.column() > 0:
			return 0
		
		if not parent.isValid():
			parentItem = self.tree
		else:
			parentItem = parent.internalPointer()
			
		return parentItem.childCount()

	def setData(self, index, value, role):
		if role != Qt.EditRole or index.column() != 0:
			return False
			
		item = index.internalPointer()
		new_name = str(value.toString())
		if isinstance(item, TableItem):
			# rename table or view
			try:
				schema = item.parentItem.name
				self.db.rename_table(item.name, new_name, schema)
				self.emit(SIGNAL('dataChanged(const QModelIndex &, const QModelIndex &)'), index, index)
				return True
			except postgis_utils.DbError, e:
				QMessageBox.critical(None, "error", "Couldn't rename:\nMessage: %s\nQuery: %s" % (e.message, e.query) )
				return False
			
		elif isinstance(item, SchemaItem):
			# rename schema
			try:
				self.db.rename_schema(item.name, new_name)
				self.emit(SIGNAL('dataChanged(const QModelIndex &, const QModelIndex &)'), index, index)
				return True
			except postgis_utils.DbError, e:
				QMessageBox.critical(None, "error", "Couldn't rename schema:\nMessage: %s\nQuery: %s" % (e.message, e.query) )
				return False
			
		else:
			print "set", str(value.toString()), role
			return False



class ManagerDialog(QDialog, Ui_ManagerDialog):
	
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
		
		self.db = postgis_utils.GeoDB(host='localhost',dbname='gis',user='gisak',passwd='g')
		
		rootItem = self.loadTreeItems()
		self.treeModel = TreeModel(rootItem, self, self.db)
		self.tree.setModel(self.treeModel)
		
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
		
		
	def loadTreeItems(self):
		tbls = self.db.list_geotables()
		rootItem = DatabaseItem()
		
		schemas = {} # name : item
		
		# add all schemas
		for schema in self.db.list_schemas():
			schema_name = schema[0]
			schemas[schema_name] = SchemaItem(schema_name, rootItem)
		
		for tbl in tbls:
			tablename, schema, reltype, geom_col, geom_type = tbl
			is_view = (reltype == 'v')
			
			# add schema if doesn't exist
			if not schemas.has_key(schema):
				print "AAAA!!"
				continue
			
			tableItem = TableItem(tablename, geom_type, is_view, schemas[schema])
		return rootItem
		
	def refreshTable(self):
		self.tree.model().tree = self.loadTreeItems()
		self.tree.model().reset()
		self.tree.expandAll()
		
	def itemActivated(self, index):
		
		item = index.internalPointer()
		
		if isinstance(item, SchemaItem):
			html = "<h1>%s</h1> (schema)<p>tables: %d" % (item.name, item.childCount())
		elif isinstance(item, TableItem):
			if item.is_view:
				reltype = "View"
			else:
				reltype = "Table"
			html = "<h1>%s</h1> (%s)<p>geometry: %s" % (item.name, reltype, item.geom_type)
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


app = QApplication(sys.argv)

dlg = ManagerDialog()
dlg.show()

retval = app.exec_()

sys.exit(retval)
