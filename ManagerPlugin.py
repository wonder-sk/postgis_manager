
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

import resources

import postgis_utils
from ManagerWindow import ManagerWindow

class ManagerPlugin:

	def __init__(self, iface):
		# Save reference to the QGIS interface
		self.iface = iface
	
	def initGui(self):
		# Create action that will start plugin configuration
		self.action = QAction(QIcon(":/icons/postgis_elephant.png"), "PostGIS Manager", self.iface.mainWindow())
		QObject.connect(self.action, SIGNAL("triggered()"), self.run)
	
		# Add toolbar button and menu item
		self.iface.addToolBarIcon(self.action)
		self.iface.addPluginToMenu("&PostGIS Manager", self.action)
	
	def unload(self):
		# Remove the plugin menu item and icon
		self.iface.removePluginMenu("&PostGIS Manager",self.action)
		self.iface.removeToolBarIcon(self.action)
	
	def run(self): 
		
		db = postgis_utils.GeoDB(host='localhost',dbname='gis',user='gisak',passwd='g')
		
		self.dlg = ManagerWindow(db, True)
		self.dlg.show()
