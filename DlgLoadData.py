
from DlgLoadData_ui import Ui_DlgLoadData

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import subprocess


class DlgLoadData(QDialog, Ui_DlgLoadData):

	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		
		self.setupUi(self)
		
		b = QPushButton("&Load")
		self.buttonBox.addButton(b, QDialogButtonBox.ActionRole)

		self.connect(self.btnSelectShapefile, SIGNAL("clicked()"), self.onSelectShapefile)
		self.connect(self.btnSelectOutputFile, SIGNAL("clicked()"), self.onSelectOutputFile)
		self.connect(b, SIGNAL("clicked()"), self.onLoad)
		
		# updates of UI
		for widget in [self.radCreate, self.radAppend, self.radCreateOnly, self.chkSrid,
		               self.chkGeomColumn, self.chkEncoding, self.radExec, self.radSave]:
			self.connect(widget, SIGNAL("clicked()"), self.updateUi)
		
		self.populateSchemasTables()
		self.populateEncodings()
		self.updateUi()
		
	def populateSchemasTables(self):
		# TODO: populate with data from database
		pass
	
	def populateEncodings(self):
		encodings = ['ASCII', 'CP1250', 'ISO-8859-2', 'UTF-8']
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
			args += ['-g', str(self.editGeomColumn.text())]
		if self.chkEncoding.isChecked():
			args += ['-W', str(self.cboEncoding.currentText())]
		if self.chkSpatialIndex.isChecked():
			args.append('-I')
			
		# shapefile
		shpfile = str(self.editShapefile.text())
		args.append(shpfile) 
		
		# table name
		if self.cboSchema.currentText().isEmpty():
			table = str(self.cboTable.currentText())
		else:
			table = str(self.cboSchema.currentText())+"."+str(self.cboTable.currentText())
		args.append(table)
		
		print args
		
		if self.radExec.isChecked():
			out = subprocess.PIPE
		else:
			out = open(self.editOutputFile.text(), 'w')
		
		try:
			# start shp2pgsql as subprocess
			p = subprocess.Popen(args=args, stdout=out, stderr=subprocess.PIPE)
			
			if out == subprocess.PIPE:
				# read the output while the process is running
				# TODO: run SQL commands within current DB connection
				while p.poll() == None:
					print p.stdout.read()
				# read the rest ... is this necessary?
				print p.stdout.read()
			else:
				# just wait until it finishes
				p.wait()
				# close the output file
				out.close()
			
		except OSError, e:
			QMessageBox.critical(self, "OSError", "Message: %s\nFilename: %s" % (e.filename, e.message))
			return
		
		# check whether it has run without errors
		if p.returncode != 0:
			err = p.stderr.readlines()
			QMessageBox.critical(self, "Returned error", "Something's wrong:\n" + str(err))
			return
		
		QMessageBox.information(self, "Good", "Everything went fine")


	def onSelectShapefile(self):
		fileName = QFileDialog.getOpenFileName(self, "Open Shapefile", QString(), "Shapefiles (*.shp)")
		if fileName.isNull():
			return
		self.editShapefile.setText(fileName)
	
	def onSelectOutputFile(self):
		fileName = QFileDialog.getSaveFileName(self, "Save SQL as", QString(), "SQL files (*.sql);;All files (*.*)")
		if fileName.isNull():
			return
		self.editOutputFile.setText(fileName)
		


if __name__ == '__main__':
	import sys
	a = QApplication(sys.argv)
	dlg = DlgLoadData()
	dlg.show()
	sys.exit(a.exec_())
