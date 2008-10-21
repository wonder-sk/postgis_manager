
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *


class PreviewTableModel(QAbstractTableModel):

	def __init__(self, layer, parent=None):
		QAbstractTableModel.__init__(self, parent)
		self.layer = layer

		self.lastRowId = -1
		self.lastRow = None

		self.featCount = self.layer.dataProvider().featureCount()
		print "features:", self.featCount

		self.attrs = self.layer.dataProvider().attributeIndexes()
		print "attrs:", self.attrs
	
	def rowCount(self, index):
		return self.featCount

	def columnCount(self, index):
		return self.layer.dataProvider().fieldCount()

	def data(self, index, role):
		if role == Qt.DisplayRole:
			#print "row %d col %d" % (index.row(), index.column())
			if self.lastRowId == index.row():
				# cached row
				return self.lastRow[index.column()]
			else:
				#print "fetching row ", index.row()
				f = QgsFeature()
				res = self.layer.dataProvider().featureAtId(index.row(),f, False, self.attrs)
				if res:
					self.lastRowId = index.row()
					self.lastRow = f.attributeMap()
					return self.lastRow[index.column()]
				else:
					return QVariant("error")
		else:
			return QVariant()

	def headerData(self, section, orientation, role):
		if role == Qt.DisplayRole:
			if orientation == Qt.Vertical:
				return QVariant(section) # riadok
			else:
				fld = self.layer.dataProvider().fields()[section] # stlpec
				return QVariant(fld.name())
		else:
			return QVariant()
