# -*- coding: utf-8 -*-

from ui.DlgLoadData_ui import Ui_DlgLoadData
from DlgDbError import DlgDbError

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import subprocess
import re
import sys

from postgis_utils import DbError


class DlgLoadData(QDialog, Ui_DlgLoadData):

	def __init__(self, parent=None, db=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
		
		self.db = db
		
		b = QPushButton("&Load")
		self.buttonBox.addButton(b, QDialogButtonBox.ActionRole)

		self.connect(self.btnSelectShapefile, SIGNAL("clicked()"), self.onSelectShapefile)
		self.connect(self.btnSelectOutputFile, SIGNAL("clicked()"), self.onSelectOutputFile)
		self.connect(b, SIGNAL("clicked()"), self.onLoad)
		
		# updates of UI
		for widget in [self.radCreate, self.radAppend, self.radCreateOnly, self.chkSrid,
		               self.chkGeomColumn, self.chkEncoding, self.radExec, self.radSave]:
			self.connect(widget, SIGNAL("clicked()"), self.updateUi)
			
		self.connect(self.cboSchema, SIGNAL("currentIndexChanged(int)"), self.populateTables)
		
		self.populateSchemas()
		self.populateTables()
		self.populateEncodings()
		self.updateUi()
		
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
		
		currentText = self.cboTable.currentText()
		schema = unicode(self.cboSchema.currentText())
		tables = self.db.list_geotables(schema)
		self.cboTable.clear()
		for table in tables:
			self.cboTable.addItem(table[0])
		self.cboTable.setEditText(currentText)
	
	def populateEncodings(self):
		encodings = ['ISO-8859-1', 'ISO-8859-2', 'UTF-8', 'CP1250']
		for enc in encodings:
			self.cboEncoding.addItem(enc)
	
	def updateUi(self):
		allowDropTable = self.radCreate.isChecked()
		self.chkDropTable.setEnabled(allowDropTable)
		
		allowSetSrid = self.chkSrid.isChecked()
		self.editSrid.setEnabled(allowSetSrid)
		
		allowSetGeomColumn = self.chkGeomColumn.isChecked()
		self.editGeomColumn.setEnabled(allowSetGeomColumn)
		
		allowSetEncoding = self.chkEncoding.isChecked()
		self.cboEncoding.setEnabled(allowSetEncoding)
		
		allowSetOutputFile = self.radSave.isChecked()
		self.editOutputFile.setEnabled(allowSetOutputFile)
		self.btnSelectOutputFile.setEnabled(allowSetOutputFile)

		
	def onLoad(self):
		
		# sanity checks
		if self.editShapefile.text().isEmpty():
			QMessageBox.information(self, "error", "No shapefile for import!")
			return
		if self.cboTable.currentText().isEmpty():
			QMessageBox.information(self, "error", "Table name is empty!")
			return
		if self.radSave.isChecked() and self.editOutputFile.text().isEmpty():
			QMessageBox.information(self, "error", "Output file not set!")
			return
		
		args = ["shp2pgsql"]
		
		# set action
		if self.radCreate.isChecked():
			if self.chkDropTable.isChecked():
				args.append("-d")
			else:
				args.append("-c")
		elif self.radAppend.isChecked():
			args.append("-a")
		else: # only create table
			args.append("-p")
		
		# more options
		if self.chkSrid.isChecked():
			args += ['-s', str(self.editSrid.text())]
		if self.chkGeomColumn.isChecked():
			args += ['-g', unicode(self.editGeomColumn.text())]
		if self.chkEncoding.isChecked():
			args += ['-W', str(self.cboEncoding.currentText())]
		if self.chkSinglePart.isChecked():
			args.append('-S')
		if self.chkSpatialIndex.isChecked():
			args.append('-I')
		if self.chkDumpFormat.isChecked():
			args.append('-D')
			
		# shapefile
		shpfile = unicode(self.editShapefile.text())
		args.append(shpfile) 
		
		# table name
		if self.cboSchema.currentText().isEmpty():
			table = unicode(self.cboTable.currentText())
		else:
			table = unicode(self.cboSchema.currentText())+"."+unicode(self.cboTable.currentText())
		args.append(table)
		
		print args

		QApplication.setOverrideCursor(Qt.WaitCursor)
		
		if self.radExec.isChecked():
			out = subprocess.PIPE
			#execAtOnce = self.chkDumpFormat.isChecked()
		else:
			out = open(self.editOutputFile.text(), 'w')
			
		try:
			if sys.platform == 'win32':
				res, err = self.load_data_win(out, args)
			else:
				res, err = self.load_data_posix(out, args)
			
		except OSError, e:
			QApplication.restoreOverrideCursor()
			QMessageBox.critical(self, "OSError", "Message: %s\nFilename: %s" % (e.message, e.filename))
			return
		except DbError, e:
			QApplication.restoreOverrideCursor()
			DlgDbError.showError(e, self)
			return
		except UnicodeDecodeError, e:
			QApplication.restoreOverrideCursor()
			QMessageBox.critical(self, "Encoding error", "Encoding mismatch. Please choose correct encoding of the data.")
			return

		QApplication.restoreOverrideCursor()
		
		# check whether it has run without errors
		if res == False:
			QMessageBox.critical(self, "Returned error", "Something's wrong:\n" + str(err))
			return

		QMessageBox.information(self, "Good", "Everything went fine")

		# repopulate the table list (and preserve current table name)
		self.populateTables()


	def onSelectShapefile(self):
		settings = QSettings()
		shpPath = settings.value("/PostGIS_Manager/shp_path").toString()

		fileName = QFileDialog.getOpenFileName(self, "Open Shapefile", shpPath, "Shapefiles (*.shp)")
		if fileName.isNull():
			return
		self.editShapefile.setText(fileName)
		# use default name for table
		fi = QFileInfo(fileName)
		self.cboTable.setEditText(fi.baseName())

		# save shapefile path
		shpPath = QFileInfo(fileName).absolutePath()
		settings.setValue("/PostGIS_Manager/shp_path", QVariant(shpPath))
	
	def onSelectOutputFile(self):
		settings = QSettings()
		sqlPath = settings.value("/PostGIS_Manager/sql_path").toString()

		fileName = QFileDialog.getSaveFileName(self, "Save SQL as", sqlPath, "SQL files (*.sql);;All files (*.*)")
		if fileName.isNull():
			return
		self.editOutputFile.setText(fileName)
		
		# save sql path
		sqlPath = QFileInfo(fileName).absolutePath()
		settings.setValue("/PostGIS_Manager/sql_path", QVariant(sqlPath))


	def load_data_win(self, out, args):
		""" special windows handling """
		import os
		cmdline = subprocess.list2cmdline(args)
		data = None

		# subprocess.Popen() doesn't work here on windows
		# it just throws "Bad file decriptor" exception
		# I think that might be due different C runtime libraries
		# because it works in python from command line

		# with os.popen3 it's impossible to get error code
		# and os.Popen3 object isn't present on windows
		# STUPID!
		p = os.popen3(cmdline)
		data = p[1].read()
		
		if out == subprocess.PIPE:
		
			cursor = self.db.con.cursor()
			newcommand = re.compile(";$", re.MULTILINE)

			# split the commands
			cmds = newcommand.split(data)
			for cmd in cmds[:-1]:
				# run SQL commands within current DB connection
				self.db._exec_sql(cursor, cmd)
			data = cmds[-1]
			
			self.db.con.commit()

			self.emit(SIGNAL("dbChanged()"))
		else:
			out.write(data)
			out.close()

		if data is None or len(data) == 0:
			return (False, p[2].readlines())
		else:
			return (True, None)


	def load_data_posix(self, out, args):

		# start shp2pgsql as subprocess
		p = subprocess.Popen(args=args, stdout=out, stderr=subprocess.PIPE)
		
		if out == subprocess.PIPE:
			# read the output while the process is running
			data = ''
			cursor = self.db.con.cursor()
			newcommand = re.compile(";$", re.MULTILINE)
			while p.poll() == None:
				data += p.stdout.read()
				
				# split the commands
				cmds = newcommand.split(data)
				for cmd in cmds[:-1]:
					# run SQL commands within current DB connection
					self.db._exec_sql(cursor, cmd)
				data = cmds[-1]
				
			# commit!
			self.db.con.commit()

			self.emit(SIGNAL("dbChanged()"))
		else:
			# just wait until it finishes
			p.wait()
			# close the output file
			out.close()
			
		if p.returncode == 0:
			return (True, None)
		else:
			return (False, p.stderr.readlines())



if __name__ == '__main__':
	import sys
	a = QApplication(sys.argv)
	dlg = DlgLoadData()
	dlg.show()
	sys.exit(a.exec_())
