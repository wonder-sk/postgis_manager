
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import postgis_utils

from types import StringType, NoneType

class DbTableModel(QAbstractTableModel):

	def __init__(self, db, schema, table, row_count_real, parent=None):
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
		
		self.row_count = row_count_real #self.db.get_table_rows(self.table, self.schema)
		self.col_count = len(self.fields)
		
		# create named cursor and run query
		self.cur = self.db.con.cursor("db_table_"+self.table)
		self.cur.execute("SELECT %s FROM %s.%s" % (fields_txt, self.schema, self.table))
		
		self.fetched_count = 100
		self.fetchMoreData(0)
		
		
	def __del__(self):
		# close cursor and save memory
		self.cur.close()
		
	def fetchMoreData(self, row_start):
		
		#print "fetching from",row_start
		self.cur.scroll(row_start, mode='absolute')
		self.fetched_rows = self.cur.fetchmany(self.fetched_count)
		self.fetched_from = row_start


	def rowCount(self, index):
		return self.row_count

	def columnCount(self, index):
		return self.col_count

	def data(self, index, role):
		if role != Qt.DisplayRole and role != Qt.FontRole:
			return QVariant()
		
		# if we have run out of fetched values, let's fetch some more
		row = index.row()
		if row < self.fetched_from or row >= self.fetched_from+self.fetched_count:
			self.fetchMoreData(row)
		
		val = self.fetched_rows[row-self.fetched_from][index.column()]
		
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
