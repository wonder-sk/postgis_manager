from DlgDbError_ui import Ui_DlgDbError

from PyQt4.QtCore import *
from PyQt4.QtGui import *

#import postgis_utils

class DlgDbError(QDialog, Ui_DlgDbError):
	
	def __init__(self, e, parent=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)

		msg = "<pre>" + e.message.replace('<','&lt;') + "</pre>"
		query = "<pre>" + e.query.replace('<','&lt;') + "</pre>"
		self.txtMessage.setHtml(msg)
		self.txtQuery.setHtml(query)

	@staticmethod
	def showError(e, parent=None):
		dlg = DlgDbError(e, parent)
		dlg.exec_()
