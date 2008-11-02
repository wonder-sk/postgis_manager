
from DlgAbout_ui import Ui_DlgAbout

from PyQt4.QtCore import *
from PyQt4.QtGui import *

class DlgAbout(QDialog, Ui_DlgAbout):

	def __init__(self, parent=None, db=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
