
from ManagerDialog_ui import Ui_ManagerDialog
from DlgCreateTable import DlgCreateTable
from DlgLoadData import DlgLoadData

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
	
	def columnCount(self):
		return len(self.itemData)
		
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



class GeneralItem(TreeItem):
	def __init__(self, items, parent):
		TreeItem.__init__(self, parent)
		self.items = items
		
	def data(self, column):
		if column < len(self.items):
			return self.items[column]
		else:
			return None
		
	
class SchemaItem(TreeItem):
	def __init__(self, name, parent):
		TreeItem.__init__(self, parent)
		self.name = name
	
	def data(self, column):
		if column == 0:
			return self.name
		else:
			return None
	
	def icon(self):
		# TODO: ineffective (instance for every item)
		return QIcon(":/icons/namespace.xpm")


class TableItem(TreeItem):
	
	def __init__(self, name, geom_type, parent):
		TreeItem.__init__(self, parent)
		self.name, self.geom_type = name, geom_type
		
	def data(self, column):
		if column == 0:
			return self.name
		elif column == 1:
			return self.geom_type
		else:
			return None
		
	def icon(self):
		# TODO: ineffective (instance for every item)
		return QIcon(":/icons/table.xpm")

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
		return Qt.ItemIsEnabled | Qt.ItemIsSelectable
	
	def headerData(self, section, orientation, role):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole and section < len(self.tree.items):
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
		
		self.refreshTable()
		
		self.connect(self.tree, SIGNAL("clicked(const QModelIndex&)"), self.itemActivated)
		self.connect(self.btnCreateTable, SIGNAL("clicked()"), self.createTable)
		self.connect(self.btnDeleteTable, SIGNAL("clicked()"), self.deleteTable)
		self.connect(self.btnLoadData, SIGNAL("clicked()"), self.loadData)
		self.connect(self.btnDumpData, SIGNAL("clicked()"), self.dumpData)
		
	def refreshTable(self):
		tbls = self.db.list_geotables()
		rootItem = GeneralItem(['Table','Geometry'], None)
		
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
		# TODO: after update treeview doesn't expand :-(
		self.tree.expandAll()
		
		self.tree.resizeColumnToContents(0)
		
	def itemActivated(self, index):
		
		item = index.internalPointer()
		
		if isinstance(item, SchemaItem):
			html = "<h1>%s</h1> (schema)<p>tables: %d" % (item.name, item.childCount())
		elif isinstance(item, TableItem):
			html = "<h1>%s</h1> (table)<p>geometry: %s" % (item.name, item.geom_type)
			html += "<table><tr><th>#<th>Name<th>Type"
			for fld in self.db.get_table_fields(item.name):
				html += "<tr><td>%s<td>%s<td>%s" % (fld.num, fld.name, fld.data_type)
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
			QMessageBox.information(self, "sorry", "select a table for deletion!")
			return
		if len(indexes) > 1:
			QMessageBox.information(self, "sorry", "select only one table")
			return
			
		index = indexes[0]
		ptr = index.internalPointer()
		if not isinstance(ptr, TableItem):
			QMessageBox.information(self, "sorry", "select a TABLE for deletion")
			return
		
		res = QMessageBox.question(self, "hey!", "really delete table %s ?" % ptr.name, QMessageBox.Yes | QMessageBox.No)
		if res != QMessageBox.Yes:
			return
		
		self.db.delete_table(ptr.name)
		self.refreshTable()
		QMessageBox.information(self, "good", "table deleted.")
		
	def loadData(self):
		dlg = DlgLoadData(self, self.db)
		dlg.exec_()

	def dumpData(self):
		# TODO: open dialog
		pass


app = QApplication(sys.argv)

dlg = ManagerDialog()
dlg.show()

retval = app.exec_()

sys.exit(retval)
