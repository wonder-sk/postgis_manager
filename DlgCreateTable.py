
from DlgCreateTable_ui import Ui_DlgCreateTable

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class DlgCreateTable(QDialog, Ui_DlgCreateTable):
	
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
