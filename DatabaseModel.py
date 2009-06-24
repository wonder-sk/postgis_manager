
from DlgDbError import DlgDbError

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import postgis_utils


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

	def constructTreeFromDb(self, db):
		""" creates a tree of schemas and tables from current DB connection """
		
		if not db:
			return
		
		try:
			list_schemas = db.list_schemas()
		except postgis_utils.DbError, e:
			DlgDbError.showError(e, None)
			return
		
		schemas = {} # name : item
		
		# add all schemas
		for schema in list_schemas:
			schema_oid, schema_name, schema_owner, schema_perms = schema
			schemas[schema_name] = SchemaItem(schema_name, schema_owner, self)
			
		try:
			list_tables = db.list_geotables()
		except postgis_utils.DbError, e:
			DlgDbError.showError(e, None)
			return
		
		# add all tables
		for tbl in list_tables:
			tablename, schema, reltype, relowner, row_count, page_count, geom_col, geom_type, geom_dim, geom_srid = tbl
			is_view = (reltype == 'v')
			tableItem = TableItem(tablename, relowner, row_count, page_count, is_view, geom_type, geom_col, geom_dim, geom_srid, schemas[schema])
			
		self.tableCount = len(list_tables)

	
class SchemaItem(TreeItem):
	def __init__(self, name, owner, parent):
		TreeItem.__init__(self, parent)
		self.name = name
		self.owner = owner
		
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
	
	def __init__(self, name, owner, row_count, page_count, is_view, geom_type, geom_column, geom_dim, geom_srid, parent):
		TreeItem.__init__(self, parent)
		self.name, self.owner, self.row_count, self.page_count, self.is_view = name, owner, row_count, page_count, is_view
		self.geom_type, self.geom_column, self.geom_dim, self.geom_srid = geom_type, geom_column, geom_dim, geom_srid
		self.row_count_real = -1 # not known (expensive to find out)
		
		# load (shared) icon with first instance of table item
		if not hasattr(TableItem, 'tableIcon'):
			TableItem.tableIcon = QIcon(":/icons/table.xpm")
			TableItem.viewIcon = QIcon(":/icons/view.xpm")
			
	def schema(self):
		return self.parent()
		
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
	
	rootItem = DatabaseItem()
	sPublic = SchemaItem('public', 'ozefo', rootItem)
	sG = SchemaItem('gis', 'ozefo', rootItem)
	t1 = TableItem('roads', 'ozefo', 123, 4, 'LINESTRING', False, sPublic)
	t2 = TableItem('sidla', 'ozefo', 66, 2, 'POINT', False, sG)
	return rootItem



class DatabaseModel(QAbstractItemModel):
	
	def __init__(self, parent=None):
		QAbstractItemModel.__init__(self, parent)
		self.header = ['Table', 'Geometry']
		
		self.tree = DatabaseItem()
		
	def loadFromDb(self, db):
		self.db = db
		self.tree = DatabaseItem()
		self.tree.constructTreeFromDb(self.db)

		
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
		new_name = unicode(value.toString())
		if new_name == item.name:
			return False
		
		if isinstance(item, TableItem):
			# rename table or view
			try:
				schema = item.parentItem.name
				self.db.rename_table(item.name, new_name, schema)
				self.emit(SIGNAL('dataChanged(const QModelIndex &, const QModelIndex &)'), index, index)
				return True
			except postgis_utils.DbError, e:
				DlgDbError.showError(e, None)
				return False
			
		elif isinstance(item, SchemaItem):
			# rename schema
			try:
				self.db.rename_schema(item.name, new_name)
				self.emit(SIGNAL('dataChanged(const QModelIndex &, const QModelIndex &)'), index, index)
				return True
			except postgis_utils.DbError, e:
				DlgDbError.showError(e, None)
				return False
			
		else:
			print "set", unicode(value.toString()), role
			return False

