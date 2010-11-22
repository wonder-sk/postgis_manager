# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

import resources


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
		try:
			self.iface.addPluginToDatabaseMenu("&PostGIS Manager", self.action)
		except AttributeError:
			self.iface.addPluginToMenu("&PostGIS Manager", self.action)
		
	
	def unload(self):
		# Remove the plugin menu item and icon
		try:
			self.iface.removePluginDatabaseMenu("&PostGIS Manager", self.action)
		except AttributeError:
			self.iface.removePluginMenu("&PostGIS Manager",self.action)
		self.iface.removeToolBarIcon(self.action)
	
	def run(self):

		try:
			import psycopg2
		except ImportError, e:
			QMessageBox.information(self.iface.mainWindow(), "hey", "Couldn't import Python module 'psycopg2' for communication with PostgreSQL database. Without it you won't be able to run PostGIS manager.")
			return
		
		from ManagerWindow import ManagerWindow
		self.dlg = ManagerWindow(True)
		self.dlg.show()
