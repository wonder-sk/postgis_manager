
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import QgsVectorLayer, QgsRectangle, QgsFeature
import postgis_utils



class IntroPage(QWizardPage):
	
	Encodings = ["UTF-8","ISO8859-1","ISO8859-2","CP1250"]
	
	def __init__(self, parent=None):
		QWizardPage.__init__(self, parent)

		self.setTitle("Open file")
		#self.setSubTitle("This wizard will help you to import data to the database.")
	
		label = QLabel("This wizard will help you to import data to the database.")
		label.setWordWrap(True)
		
		# TODO: select import type: shapefile / csv / dbf
		
		label2 = QLabel("Enter file name of inpurt DBF file:")
		self.editFilename = QLineEdit()
		button = QPushButton("Browse...")
		self.connect(button, SIGNAL("clicked()"), self.browseFile)
		
		l2 = QHBoxLayout()
		l2.addWidget(button)
		l2.addStretch()
		
		self.cboEncoding = QComboBox()
		self.cboEncoding.setEditable(True)
		for enc in IntroPage.Encodings:
			self.cboEncoding.addItem(enc)
		
		l3 = QHBoxLayout()
		l3.addWidget(self.cboEncoding)
		l3.addStretch()
	
		layout = QVBoxLayout()
		layout.addWidget(label)
		layout.addWidget(label2)
		layout.addWidget(self.editFilename)
		layout.addLayout(l2)
		layout.addWidget(QLabel("Encoding:"))
		layout.addLayout(l3)
		#layout.addWidget(button)
		self.setLayout(layout)
		
		self.registerField("filename*", self.editFilename)
		
	
	def nextId(self):
		return WizardImport.Page_Details
	
	def browseFile(self):
		
		filename = QFileDialog.getOpenFileName(self, "Open DBF", QString(), "DBF files (*.dbf)")
		if filename.isEmpty():
			return
		self.editFilename.setText(filename)
		
	def validatePage(self):
		
		filename = self.field("filename").toString()
		
		encoding = self.cboEncoding.currentText()
		#self.setField("encoding", QVariant(encoding))
		
		if not self.wizard().load_dbf(filename, encoding):
			QMessageBox.warning(self, "error", "couldn't open file with OGR provider")
			return False
		
		
		return True



class DetailsPage(QWizardPage):
	
	def __init__(self, parent=None):
		QWizardPage.__init__(self, parent)

		self.setTitle("Table definition")
		self.setSubTitle("Details about the table to be created")
		
		self.editTablename = QLineEdit()
		self.cboPrimaryKey = QComboBox()
		
		self.listFields = QListWidget()
		
		
		layout = QVBoxLayout()
		layout.addWidget(QLabel("Table name:"))
		layout.addWidget(self.editTablename)
		layout.addWidget(QLabel("Fields:"))
		layout.addWidget(self.listFields)
		layout.addWidget(QLabel("Primary key (optional):"))
		layout.addWidget(self.cboPrimaryKey)
		
		self.setLayout(layout)
		
		self.registerField("tablename*", self.editTablename)
		self.registerField("pkey", self.cboPrimaryKey, "currentText", SIGNAL("currentIndexChanged(int)"))
		
	def initializePage(self):
		
		self.cboPrimaryKey.clear()
		self.cboPrimaryKey.addItem("(none)")
		
		tablename = QFileInfo(self.field("filename").toString()).baseName()
		
		self.editTablename.setText(tablename)
		
		# show columns
		self.listFields.clear()
		for fld in self.wizard().dbf_fields:
			self.listFields.addItem(fld.field_def())
			self.cboPrimaryKey.addItem(fld.name)
		
	
	def validatePage(self):
		
		# TODO: check whether the table doesn't exist already
		
		return True
	
	

class WizardImport(QWizard):
	
	Page_Intro, Page_Details = range(2)
	
	def __init__(self, parent=None, db=None):
		QWizard.__init__(self, parent)
		self.db = db
		
		self.setWindowTitle("Import wizard")
		
		self.setPage(self.Page_Intro, IntroPage())
		self.setPage(self.Page_Details, DetailsPage())

		self.setStartId(self.Page_Intro)
		
	def accept(self):
		
		QApplication.instance().setOverrideCursor(QCursor(Qt.WaitCursor))
		self.do_dbf_import()
		QApplication.instance().restoreOverrideCursor()
		
		QDialog.accept(self)
		

			
	def load_dbf(self, filename, encoding):
		""" try to load DBF file """
		v = QgsVectorLayer(filename, "x", "ogr")
		if not v.isValid():
			self.vlayer = None
			return False
			
		self.vlayer = v
		pr = v.dataProvider()
		pr.setEncoding(encoding)
		
		# now find out what fields are in the dbf file
		self.dbf_fields = []
		flds = pr.fields()
		for (i,fld) in flds.iteritems():
			
			name = unicode(fld.name())
			modifier = None
			if fld.type() == QVariant.Int:
				data_type = "int"
			elif fld.type() == QVariant.Double:
				data_type = "double precision"
			elif fld.type() == QVariant.String:
				data_type = "varchar"
				modifier = fld.length()
			else:
				# unsupported type
				data_type = "varchar"
				modifier = fld.length()
				
			self.dbf_fields.append(postgis_utils.TableField(name, data_type, True, None, modifier))
		
		return True
			
				

	def do_dbf_import(self):
		""" last step: create table and import data """
		
		tablename = unicode(self.field("tablename").toString())
		pkey = unicode(self.field("pkey").toString())
		if pkey == "(none)": pkey = None
		
		# create the table
		self.db.create_table(tablename, self.dbf_fields, pkey)
		
		cursor = self.db.con.cursor()
			
		# now let's get the features and import them to database
		pr = self.vlayer.dataProvider()
		flds = pr.fields()
		pr.enableGeometrylessFeatures(True)
		pr.select(pr.attributeIndexes(), QgsRectangle(), False) # all attrs, no geometry
		f = QgsFeature()
		while pr.nextFeature(f):
			attrs = f.attributeMap()
			values = []
			for (i,val) in attrs.iteritems():
				vartype = flds[i].type()
				if val.isNull():
					values.append("NULL")
				elif vartype == QVariant.Int:
					values.append(str(val.toInt()[0]))
				elif vartype == QVariant.Double:
					values.append(str(val.toDouble()[0]))
				else: # string or something else
					values.append("'%s'" % str(val.toString().toUtf8()).replace("'","''").replace("\\", "\\\\"))
			self.db.insert_table_row(tablename, values, None, cursor)
			
		# commit changes to DB
		self.db.con.commit()
