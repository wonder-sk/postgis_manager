
from ui.DlgAddGeometryColumn_ui import Ui_DlgAddGeometryColumn

from PyQt4.QtCore import *
from PyQt4.QtGui import *

class DlgAddGeometryColumn(QDialog, Ui_DlgAddGeometryColumn):

	def __init__(self, parent=None, db=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)

		self.connect(self.buttonBox, SIGNAL("accepted()"), self.onOK)

	def onOK(self):
		""" first check whether everything's fine """
		
		if self.editName.text().count() == 0:
			QMessageBox.critical(self, "sorry", "field name must not be empty")
			return

		self.accept()
