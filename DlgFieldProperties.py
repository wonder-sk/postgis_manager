
from DlgFieldProperties_ui import Ui_DlgFieldProperties

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class DlgFieldProperties(QDialog, Ui_DlgFieldProperties):
	
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
