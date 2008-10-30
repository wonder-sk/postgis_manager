
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import postgis_utils

from types import StringType, NoneType

class DbTableModel(QAbstractTableModel):

	def __init__(self, db, schema, table, parent=None):
		QAbstractTableModel.__init__(self, parent)
		
		self.db = db
		self.schema = schema
		self.table = table
		
		# get fields, ignore geometry columns
		self.fields = []
		for fld in self.db.get_table_fields(self.table, self.schema):
			if fld.data_type != "geometry":
				self.fields.append(fld.name)
		
		fields_txt = ", ".join(self.fields)
		print fields_txt
		
		self.cur = self.db.con.cursor("db_table_"+self.table)
		self.cur.execute("SELECT %s FROM %s.%s" % (fields_txt, self.schema, self.table))
		self.rows = self.cur.fetchall()
		#self.cur.close()
		
		self.row_count = len(self.rows)
		self.col_count = len(self.fields)
		
	def __del__(self):
		#print "db table model del:",self.schema,self.table
		self.cur.close()

	def rowCount(self, index):
		return self.row_count

	def columnCount(self, index):
		return self.col_count

	def data(self, index, role):
		if role != Qt.DisplayRole and role != Qt.FontRole:
			return QVariant()
		
		val = self.rows[index.row()][index.column()]
		
		# draw NULL in italic
		if role == Qt.FontRole:
			if val != None:
				return QVariant()
			f = QFont()
			f.setItalic(True)
			return QVariant(f)
		
		if type(val) == StringType:
			return QVariant(QString.fromUtf8(val))
		elif type(val) == NoneType:
			return QVariant("NULL")
		else:
			return QVariant(val)
		
	def headerData(self, section, orientation, role):
		if role != Qt.DisplayRole:
			return QVariant()
		
		if orientation == Qt.Vertical:
			# header for a row
			return QVariant(section+1)
		else:
			# header for a column
			return QVariant(self.fields[section])
