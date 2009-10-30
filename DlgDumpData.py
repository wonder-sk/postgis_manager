# -*- coding: utf-8 -*-

from ui.DlgDumpData_ui import Ui_DlgDumpData

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import subprocess
import re


class DlgDumpData(QDialog, Ui_DlgDumpData):

	def __init__(self, parent=None, db=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
		
		self.db = db

		btnDump = QPushButton("&Dump")
		self.buttonBox.addButton(btnDump, QDialogButtonBox.ActionRole)

		self.connect(self.btnSelectShapefile, SIGNAL("clicked()"), self.onSelectShapefile)
		self.connect(btnDump, SIGNAL("clicked()"), self.onDump)

		self.connect(self.cboSchema, SIGNAL("currentIndexChanged(int)"), self.populateTables)
		
		self.populateSchemas()
		self.populateTables()

	def populateSchemas(self):
		
		if not self.db:
			return
		
		schemas = self.db.list_schemas()
		self.cboSchema.clear()
		for schema in schemas:
			self.cboSchema.addItem(schema[1])
			
	def populateTables(self):
		
		if not self.db:
			return
		
		schema = unicode(self.cboSchema.currentText())
		tables = self.db.list_geotables(schema)
		self.cboTable.clear()
		for table in tables:
			self.cboTable.addItem(table[0])


	def onSelectShapefile(self):
		settings = QSettings()
		shpPath = settings.value("/PostGIS_Manager/shp_path").toString()

		fileName = QFileDialog.getSaveFileName(self, "Save as", shpPath, "Shapefiles (*.shp)")
		if fileName.isNull():
			return
		self.editShapefile.setText(fileName)
	
		# save shapefile path
		shpPath = QFileInfo(fileName).absolutePath()
		settings.setValue("/PostGIS_Manager/shp_path", QVariant(shpPath))

	def onDump(self):
		
		# sanity checks
		if self.cboTable.currentText().isEmpty():
			QMessageBox.information(self, "error", "Table name is empty!")
			return
		if self.editShapefile.text().isEmpty():
			QMessageBox.information(self, "error", "Set output shapefile name!")
			return
	
		args = ["pgsql2shp"]
		
		# output shapefilename
		output = unicode(self.editShapefile.text())
		args += [ '-f', output ]
		
		# connection options
		if self.db.host:
			args += ['-h', self.db.host ]
		if self.db.port:
			args += ['-p', str(self.db.port) ]
		if self.db.user:
			args += [ '-u', self.db.user ]
		if self.db.passwd:
			args += [ '-P', self.db.passwd ]
		
		# other options
		if self.chkBinaryCursor.isChecked():
			args.append('-b')
		
		# database and table
		table = unicode(self.cboSchema.currentText()) + '.' + unicode(self.cboTable.currentText())
		args += [ self.db.dbname, table ]
		
		print args

		try:
			# start shp2pgsql as subprocess
			p = subprocess.Popen(args=args, stderr=subprocess.PIPE)
			
			# TODO: visualize somehow what's going on

			# just wait until it finishes
			p.wait()

		except OSError, e:
			QMessageBox.critical(self, "OSError", "Message: %s\nFilename: %s" % (e.message, e.filename))
			return

		QMessageBox.information(self, "good", "data dumped!")
