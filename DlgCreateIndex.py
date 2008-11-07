
from DlgCreateIndex_ui import Ui_DlgCreateIndex

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import postgis_utils

class DlgCreateIndex(QDialog, Ui_DlgCreateIndex):
	
	def __init__(self, parent=None, db=None, table=None, schema=None):
		QDialog.__init__(self, parent)
		
		self.db = db
		self.table = table
		self.schema = schema
		
		self.setupUi(self)
		
		b = QPushButton("&Create")
		self.buttonBox.addButton(b, QDialogButtonBox.ActionRole)
		self.connect(b, SIGNAL("clicked()"), self.createIndex)
		
		self.connect(self.cboColumn, SIGNAL("currentIndexChanged(int)"), self.columnChanged)
		
		self.populateColumns()
		
	def populateColumns(self):
		
		self.cboColumn.clear()
		for field in self.db.get_table_fields(self.table, self.schema):
			self.cboColumn.addItem(field.name)
			
	def columnChanged(self):
		self.editName.setText("idx_%s_%s" % (self.table, self.cboColumn.currentText()))
			
			
	def createIndex(self):

		column = str(self.cboColumn.currentText())
		name = str(self.editName.text())
		if not name:
			QMessageBox.critical(self, "error", "Please enter some name for the index")
			return
		
		# now create the index
		try:
			self.db.create_index(self.table, name, column, self.schema)
		except postgis_utils.DbError, e:
			QMessageBox.critical(self, "error", "Message:\n%s\nQuery:\n%s\n" % (e.message, e.query))
			return

		self.accept()
