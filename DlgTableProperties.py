
from DlgTableProperties_ui import Ui_DlgTableProperties

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class DlgTableProperties(QDialog, Ui_DlgTableProperties):
	
	def __init__(self, parent=None, db=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
