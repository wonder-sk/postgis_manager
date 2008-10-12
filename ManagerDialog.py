
from ManagerDialog_ui import Ui_ManagerDialog

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import sys

import postgis_utils


class MyTreeModel(QAbstractItemModel):
	
	def __init__(self, parent=None):
		QAbstractItemModel.__init__(self, parent)
		
	def data(self, index, role):
		if not index.isValid():
			return QVariant()
		if role != Qt.DisplayRole:
			return QVariant()
		
		return QVariant(1)
	
	def rowCount(self, index):
		return 1
	
	def columnCount(self, index):
		return 1
	
	def headerData(self, section, orientation, role):
		return QVariant()
	
	def flags(self, index):
		return Qt.ItemIsSelectable | Qt.ItemIsEnabled
	
	def index(self, row, col, parent):
		""" returns index of item specified by row, col and parent """
		return QModelIndex()
		
	
	def parent(self, index):
		""" return parent of the item specified by index """
		return QModelIndex()

class ManagerDialog(QDialog, Ui_ManagerDialog):
	
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
		
		self.m = MyTreeModel()
		self.tree.setModel(self.m)
		
		c = postgis_utils.connect_db('localhost','gis','gisak','g')
		self.db = postgis_utils.GeoDB(c)
		
		tbls = self.db.list_geotables()
		h = {}
		for tbl in tbls:
			tablename, schema = tbl[0], tbl[1]
			if not h.has_key(schema):
				h[schema] = []
			
			h[schema].append(tablename)
			
		print h



app = QApplication(sys.argv)

dlg = ManagerDialog()
dlg.show()

sys.exit(app.exec_())
