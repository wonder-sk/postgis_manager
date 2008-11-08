
from ui.DlgCreateConstraint_ui import Ui_DlgCreateConstraint

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import postgis_utils

class DlgCreateConstraint(QDialog, Ui_DlgCreateConstraint):
	
	def __init__(self, parent=None, db=None, table=None, schema=None):
		QDialog.__init__(self, parent)
		
		self.db = db
		self.table = table
		self.schema = schema
		
		self.setupUi(self)

		self.populateColumns()
		
	def populateColumns(self):
		
		self.cboColumn.clear()
		for field in self.db.get_table_fields(self.table, self.schema):
			self.cboColumn.addItem(field.name)
			
