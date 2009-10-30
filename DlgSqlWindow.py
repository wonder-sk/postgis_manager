# -*- coding: utf-8 -*-

from ui.DlgSqlWindow_ui import Ui_DlgSqlWindow
from DlgDbError import DlgDbError

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import postgis_utils
import psycopg2

from types import NoneType


class SqlTableModel(QAbstractTableModel):
	
	def __init__(self, cursor, parent=None):
		QAbstractTableModel.__init__(self, parent)
		
		try:
			self.resdata = cursor.fetchall()
			self.header = map(lambda x: x[0], cursor.description)
		except psycopg2.Error, e:
			# nothing to fetch!
			self.resdata = [ ]
			self.header = [ ]
		
		
		
	def rowCount(self, parent):
		return len(self.resdata)
	
	def columnCount(self, parent):
		return len(self.header)
	
	def data(self, index, role):
		if role != Qt.DisplayRole:
			return QVariant()
		
		val = self.resdata[ index.row() ][ index.column() ]
		if type(val) == NoneType:
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
			return QVariant(self.header[section])


class DlgSqlWindow(QDialog, Ui_DlgSqlWindow):

	def __init__(self, parent=None, db=None):
		QDialog.__init__(self, parent)
		
		self.db = db
		
		self.setupUi(self)

		settings = QSettings()
		self.restoreGeometry(settings.value("/PostGIS_Manager/sql_geometry").toByteArray())
		
		self.connect(self.btnExecute, SIGNAL("clicked()"), self.executeSql)
		self.connect(self.btnClear, SIGNAL("clicked()"), self.clearSql)
		self.connect(self.buttonBox.button(QDialogButtonBox.Close), SIGNAL("clicked()"), self.close)
		
		
	def closeEvent(self, e):
		""" save window state """
		settings = QSettings()
		settings.setValue("/PostGIS_Manager/sql_geometry", QVariant(self.saveGeometry()))
		
		QDialog.closeEvent(self, e)
		
	def clearSql(self):
		self.editSql.setPlainText(QString())

	def executeSql(self):
		
		if self.editSql.toPlainText().isEmpty():
			return

		txt = unicode(self.editSql.toPlainText())
		
		QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

		try:
			c = self.db.con.cursor()
			t = QTime()
			t.start()
			self.db._exec_sql(c, txt)
			secs = t.elapsed() / 1000.0
			
			self.viewResult.setModel( SqlTableModel(c, self.viewResult) )
			
			# commit before closing the cursor to make sure that the changes are stored
			self.db.con.commit()
			c.close()
			
			self.lblResult.setText("%d rows, %.1f seconds" % (c.rowcount, secs))
			
			QApplication.restoreOverrideCursor()
		
		except postgis_utils.DbError, e:
			QApplication.restoreOverrideCursor()
			
			DlgDbError.showError(e, self)
		