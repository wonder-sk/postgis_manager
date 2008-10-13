
from ManagerDialog_ui import Ui_ManagerDialog

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import sys

import postgis_utils

class TreeItem:
	
	def __init__(self, data, parent):
		self.parentItem = parent
		self.itemData = data
		self.childItems = []
		
		if parent:
			parent.appendChild(self)
			
	def appendChild(self, child):
		self.childItems.append(child)
	
	def child(self, row):
		return self.childItems[row]
	
	def childCount(self):
		return len(self.childItems)
	
	def columnCount(self):
		return len(self.itemData)
		
	def data(self, column):
		return self.itemData[column]
	
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
	
class SchemaItem(TreeItem):
	def __init__(self, name, parent):
		TreeItem.__init__(self, [name], parent)
	
class TableItem(TreeItem):
	def __init__(self, name, geom_type, parent):
		TreeItem.__init__(self, [name, geom_type], parent)

def new_tree():
	
	rootItem = TreeItem(['tables'], None)
	sPublic = SchemaItem('public', rootItem)
	sG = SchemaItem('gis', rootItem)
	t1 = TableItem('roads', 'LINESTRING', sPublic)
	t2 = TableItem('sidla', 'POINT', sG)
	return rootItem


def create_tree():
	rootItem = TreeItem(['title','summary'], None)
	
	item_gs = TreeItem(['Getting Started','How to familiarize yourself with Qt Designer'], rootItem)
	item_gs1 = TreeItem(['Launching Designer', 'Running the Qt Designer application'], item_gs)
	item_gs2 = TreeItem(['The User Interface', 'How to interact with Qt Designer'], item_gs)
	
	item_dc = TreeItem(['Designing a Component', 'Creating a GUI for your application'], rootItem)
	item_dc1 = TreeItem(['Creating a Dialog', 'How to create a dialog'], item_dc)
	item_dc2 = TreeItem(['Composing the Dialog', 'Putting widgets into the dialog example'], item_dc)
	item_dc3 = TreeItem(['Creating a Layout', 'Arranging widgets on a form'], item_dc)
	
	item_uc = TreeItem(['Using a Component in Your Application', 'Generating code from forms'], rootItem)
	item_uc1 = TreeItem(['The Direct Approach', 'Using a form without any adjustments'], item_uc)
	item_uc11 = TreeItem(['The Single Inheritance Approach', 'Subclassing a form\'s base class'], item_uc1)
	
	return rootItem
	


class TreeModel(QAbstractItemModel):
	
	def __init__(self, tree, parent=None):
		QAbstractItemModel.__init__(self, parent)
		self.tree = tree
		
	def columnCount(self, parent):
		if parent.isValid():
			return parent.internalPointer().columnCount()
		else:
			return self.tree.columnCount()
		
	def data(self, index, role):
		if not index.isValid():
			return QVariant()
		if role != Qt.DisplayRole:
			return QVariant()
		
		item = index.internalPointer()
		return QVariant(item.data(index.column()))
	
	def flags(self, index):
		if not index.isValid():
			return 0
		return Qt.ItemIsEnabled | Qt.ItemIsSelectable
	
	def headerData(self, section, orientation, role):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			return QVariant(self.tree.data(section))
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




class ManagerDialog(QDialog, Ui_ManagerDialog):
	
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
		
		c = postgis_utils.connect_db('localhost','gis','gisak','g')
		self.db = postgis_utils.GeoDB(c)
		
		tbls = self.db.list_geotables()
		rootItem = TreeItem(['hello','world'], None)
		
		schemas = {} # name : item
		for tbl in tbls:
			tablename, schema, reltype, geom_col, geom_type = tbl
			
			# add schema if doesn't exist
			if not schemas.has_key(schema):
				schemaItem = SchemaItem(schema, rootItem)
				schemas[schema] = schemaItem
			
			tableItem = TableItem(tablename, geom_type, schemas[schema])
			
		self.treeModel = TreeModel(rootItem)
		self.tree.setModel(self.treeModel)



app = QApplication(sys.argv)

dlg = ManagerDialog()
dlg.show()

retval = app.exec_()

sys.exit(retval)
