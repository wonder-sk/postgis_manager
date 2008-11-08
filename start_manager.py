
import sys

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import postgis_utils

def start_qgis(qgis_path):

	# FIXME
	#qgis_path = '/home/wonder/qgis/inst'
	sys.path.insert(0, qgis_path+'/share/qgis/python')
	
	try:
		import qgis.core
		import qgis.gui
	except ImportError, e:
		print "Import error:", e.message
		return False
	
	qgis.core.QgsApplication.setPrefixPath(qgis_path, True)
	qgis.core.QgsApplication.initQgis()
	return True


def main():
	
	# defaults
	use_qgis = False
	qgis_path = None
	
	# check whether to use QGIS
	for arg in sys.argv:
		if arg[:7] == '--qgis=':
			use_qgis = True
			qgis_path = arg[7:]
			print qgis_path

	# try to use QGIS
	if use_qgis and not start_qgis(qgis_path):
		print "Can't load PyQGIS. Possible reasons:"
		print "- QGIS or its Python support is not installed"
		print "- QGIS is installed in non-standard folder"
		print "  (setting PYTHONPATH and/or LD_LIBRARY_PATH might help)"
		sys.exit(1)
	
	# add testing entry
	settings = QSettings()
	
	key = "/PostgreSQL/connections/test DB"
	settings.setValue(key + "/host", QVariant("localhost"))
	settings.setValue(key + "/port", QVariant(5432))
	settings.setValue(key + "/database", QVariant("gis"))
	settings.setValue(key + "/username", QVariant("gisak"))
	settings.setValue(key + "/password", QVariant("g"))
	
	key = "/PostgreSQL/connections/urtax"
	settings.setValue(key + "/host", QVariant("localhost"))
	settings.setValue(key + "/port", QVariant(5431))
	settings.setValue(key + "/database", QVariant("qgismapper"))
	settings.setValue(key + "/username", QVariant("qgismapper"))
	settings.setValue(key + "/password", QVariant("g"))
	
	settings.setValue("/PostgreSQL/connections/selected", QVariant("test DB"))
	
	app = QApplication(sys.argv)
	
	from ManagerWindow import ManagerWindow
	dlg = ManagerWindow(use_qgis)
	dlg.show()
	
	retval = app.exec_()
	
	sys.exit(retval)


if __name__ == '__main__':
	main()