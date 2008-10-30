
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import sys

try:
	import qgis.gui
	import qgis.core
except ImportError, e:
	print "no qgis"


from DlgCreateTable import DlgCreateTable
from DlgLoadData import DlgLoadData
from DlgDumpData import DlgDumpData
from DlgTableProperties import DlgTableProperties
from DatabaseModel import TableItem, SchemaItem, DatabaseModel
import resources
import postgis_utils

class ManagerWindow(QMainWindow):
	
	def __init__(self, use_qgis=False, parent=None):
		QMainWindow.__init__(self, parent)
		
		self.useQgis = use_qgis
		self.currentLayerId = None
		self.db = None
		
		self.setupUi()
		
		self.dbModel = DatabaseModel(self)
		self.tree.setModel(self.dbModel)
		
		# connect to database selected last time
		settings = QSettings()
		sel = str(settings.value("/PostgreSQL/connections/selected").toString())
		self.dbConnect(sel)
		
		
		self.tree.expandAll()
		self.tree.resizeColumnToContents(0)
		
		# setup signal-slot connections
		self.connect(self.tree, SIGNAL("clicked(const QModelIndex&)"), self.itemActivated)
		self.connect(self.tree, SIGNAL("doubleClicked(const QModelIndex&)"), self.editTable)
		self.connect(self.tree.model(), SIGNAL("dataChanged(const QModelIndex &, const QModelIndex &)"), self.refreshTable)
		# actions
		self.connect(self.actionCreateTable, SIGNAL("triggered(bool)"), self.createTable)
		self.connect(self.actionEditTable, SIGNAL("triggered(bool)"), self.editTable)
		self.connect(self.actionDeleteTableView, SIGNAL("triggered(bool)"), self.deleteTable)
		self.connect(self.actionCreateSchema, SIGNAL("triggered(bool)"), self.createSchema)
		self.connect(self.actionDeleteSchema, SIGNAL("triggered(bool)"), self.deleteSchema)
		self.connect(self.actionLoadData, SIGNAL("triggered(bool)"), self.loadData)
		self.connect(self.actionDumpData, SIGNAL("triggered(bool)"), self.dumpData)
		#self.connect(self.actionDbConnect, SIGNAL("triggered(bool)"), self.dbConnect)
		self.connect(self.actionDbDisconnect, SIGNAL("triggered(bool)"), self.dbDisconnect)
		
		
	def listDatabases(self):
		
		actionsDb = {}
		settings = QSettings()
		settings.beginGroup("/PostgreSQL/connections")
		keys = settings.childGroups()
		
		for key in keys:
			actionsDb[str(key)] = QAction(key, self)
			
		settings.endGroup()
		
		return actionsDb
	
		
	def dbConnectSlot(self):
		sel = str(self.sender().text())
		print "connect", sel
		self.dbConnect(sel)
		

	def dbConnect(self, selected):
		
		# if there's open database already, get rid of it
		if self.db:
			self.dbDisconnect()
		
		# get connection details from QSettings
		settings = QSettings()
		print "selected:" + selected
		key = "/PostgreSQL/connections/" + selected
		get_value = lambda x: settings.value( key + "/" + x )
		get_value_str = lambda x: str(get_value(x).toString())
		host, database, username, password = map(get_value_str, ["host", "database", "username", "password"])
		port = get_value("port").toInt()[0]
		
		# connect to DB
		#print host,port,database,username,password
		try:
			self.db = postgis_utils.GeoDB(host=host, port=port, dbname=database, user=username, passwd=password)
		except postgis_utils.DbError, e:
			QMessageBox.critical(self, "error", "Couldn't connect to database:\n"+e.message)
			return
		
		# set as default in QSettings
		settings.setValue("/PostgreSQL/connections/selected", QVariant(selected))
		
		# set action as checked
		if self.actionsDb.has_key(selected):
			self.actionsDb[selected].setChecked(True)
	
		self.actionDbDisconnect.setEnabled(True)
		
		self.refreshTable()
	
	
	def dbDisconnect(self):
		
		# uncheck previously selected DB
		for a in self.actionsDb.itervalues():
			if a.isChecked():
				a.setChecked(False)
		
		self.db = None
		self.refreshTable()
		
		self.actionDbDisconnect.setEnabled(False)
		
		self.loadTableMetadata(None)
		if self.useQgis:
			self.loadTablePreview(None)

	
	def refreshTable(self):
		self.tree.model().loadFromDb(self.db)
		self.tree.model().reset()
		self.tree.expandAll()
		
	def itemActivated(self, index):
		item = index.internalPointer()
		
		if isinstance(item, SchemaItem):
			self.loadSchemaMetadata(item)
		elif isinstance(item, TableItem):
			self.loadTableMetadata(item)
			if self.useQgis:
				self.loadTablePreview(item)
	
	def loadSchemaMetadata(self, item):
		""" show metadata about schema """	
		html = "<h1>%s</h1> (schema)<p>Tables: %d<br>Owner: %s" % (item.name, item.childCount(), item.owner)
		self.txtMetadata.setHtml(html)
		
	def loadTableMetadata(self, item):
		""" show metadata about table """
		if not item:
			self.txtMetadata.setHtml(QString())
			return
		
		if item.is_view:
			reltype = "View"
		else:
			reltype = "Table"
		html = "<h1>%s</h1> (%s)<br>Owner: %s<br>Rows (estimation): %d<br>Pages: %d<p>Geometry: %s" % (item.name, reltype, item.owner, item.row_count, item.page_count, item.geom_type)
		
		# fields
		html += "<h3>Fields</h3><table><tr><th>#<th>Name<th>Type<th>Null"
		for fld in self.db.get_table_fields(item.name):
			if fld.notnull: is_null_txt = "N"
			else: is_null_txt = "Y"
			html += "<tr><td>%s<td>%s<td>%s<td>%s" % (fld.num, fld.name, fld.data_type, is_null_txt)
		html += "</table>"
		
		# constraints
		constraints = self.db.get_table_constraints(item.name)
		if len(constraints) != 0:
			html += "<h3>Constraints</h3>"
			html += "<table><tr><th>Name<th>Type<th>Attributes"		
			for con in constraints:
				if   con.con_type == postgis_utils.TableConstraint.TypeCheck:      con_type = "Check"
				elif con.con_type == postgis_utils.TableConstraint.TypePrimaryKey: con_type = "Primary key"
				elif con.con_type == postgis_utils.TableConstraint.TypeForeignKey: con_type = "Foreign key"
				elif con.con_type == postgis_utils.TableConstraint.TypeUnique:     con_type = "Unique"
				html += "<tr><td>%s<td>%s<td>%s" % (con.name, con_type, con.keys)
			html += "</table>"
		
		# indexes
		indexes = self.db.get_table_indexes(item.name)
		if len(indexes) != 0:
			html += "<h3>Indexes</h3>"
			html += "<table><tr><th>Name<th>Attributes"
			for fld in indexes:
				html += "<tr><td>%s<td>%s" % (fld[0], fld[1])
			html += "</table>"
		
		self.txtMetadata.setHtml(html)
		
		
	def loadTablePreview(self, item):
		""" if has geometry column load to map canvas """
		if item and item.geom_type:
			con = self.db.con_info() + " table=%s (%s) sql=" % (item.name, item.geom_column)
			vl = qgis.core.QgsVectorLayer(con, "test", "postgres")
			if not vl.isValid():
				newLayerId = None
				self.preview.setLayerSet( [] )
			else:
				newLayerId = vl.getLayerID()
				qgis.core.QgsMapLayerRegistry.instance().addMapLayer(vl, False)
				self.preview.setLayerSet( [ qgis.gui.QgsMapCanvasLayer(vl, True, False) ] )
				self.preview.zoomToFullExtent()
				
				from PreviewTableModel import PreviewTableModel
				tableModel = PreviewTableModel(vl, self)
				self.table.setModel(tableModel)
				
		else:
			newLayerId = None
			self.preview.setLayerSet( [] )
			
		# remove old layer (if any) and set new
		if self.currentLayerId:
			qgis.core.QgsMapLayerRegistry.instance().removeMapLayer(self.currentLayerId, False)
		self.currentLayerId = newLayerId
			


	def createTable(self):
		dlg = DlgCreateTable(self, self.db)
		self.connect(dlg, SIGNAL("databaseChanged()"), self.refreshTable)
		dlg.exec_()
		
		
	def editTable(self):
		
		ptr = self.currentDatabaseItem()
		if not ptr:
			return
		if not isinstance(ptr, TableItem) or ptr.is_view:
			QMessageBox.information(self, "sorry", "select a TABLE for editation")
			return
		
		dlg = DlgTableProperties(self.db, ptr.schema().name, ptr.name)
		dlg.exec_()
		
		# update info
		self.loadTableMetadata(ptr)
		if self.useQgis:
			self.loadTablePreview(ptr)
		
		
	def currentDatabaseItem(self):
		""" returns reference to item currently selected or displays an error """
		
		sel = self.tree.selectionModel()
		indexes = sel.selectedRows()
		if len(indexes) == 0:
			QMessageBox.information(self, "sorry", "nothing selected")
			return None
		if len(indexes) > 1:
			QMessageBox.information(self, "sorry", "select only one item")
			return None
		
		# we have exactly one selected item
		index = indexes[0]
		return index.internalPointer()
		
		
	def deleteTable(self):
		
		ptr = self.currentDatabaseItem()
		if not ptr:
			return
		
		if not isinstance(ptr, TableItem):
			QMessageBox.information(self, "sorry", "select a TABLE or VIEW for deletion")
			return
		
		res = QMessageBox.question(self, "hey!", "really delete table/view %s ?" % ptr.name, QMessageBox.Yes | QMessageBox.No)
		if res != QMessageBox.Yes:
			return
		
		try:
			if ptr.is_view:
				self.db.delete_view(ptr.name, ptr.schema().name)
			else:
				if len(ptr.geom_column) > 0:
					self.db.delete_geometry_table(ptr.name, ptr.schema().name)
				else:
					self.db.delete_table(ptr.name, ptr.schema().name)
			self.refreshTable()
			QMessageBox.information(self, "good", "table/view deleted.")
		except postgis_utils.DbError, e:
			QMessageBox.critical(self, "error", "Message:\n%s\nQuery:\n%s\n" % (e.message, e.query))
		
	
	def createSchema(self):
		
		(name, ok) = QInputDialog.getText(self, "Schema name", "Enter name for new schema")
		if not name.isEmpty():
			self.db.create_schema(name)
			self.refreshTable()
			QMessageBox.information(self, "good", "schema created.")

	
	def deleteSchema(self):
		sel = self.tree.selectionModel()
		indexes = sel.selectedRows()
		if len(indexes) == 0:
			QMessageBox.information(self, "sorry", "select a schema for deletion!")
			return
	
		index = indexes[0]
		ptr = index.internalPointer()
		if not isinstance(ptr, SchemaItem):
			QMessageBox.information(self, "sorry", "select a SCHEMA for deletion")
			return
		
		res = QMessageBox.question(self, "hey!", "really delete schema %s ?" % ptr.name, QMessageBox.Yes | QMessageBox.No)
		if res != QMessageBox.Yes:
			return
		
		self.db.delete_schema(ptr.name)
		self.refreshTable()
		QMessageBox.information(self, "good", "schema deleted.")
		
		
	def loadData(self):
		dlg = DlgLoadData(self, self.db)
		dlg.exec_()

	def dumpData(self):
		dlg = DlgDumpData(self, self.db)
		dlg.exec_()
		
		
	def setupUi(self):
		
		self.setWindowTitle("PostGIS Manager")
		self.setWindowIcon(QIcon(":/icons/postgis_elephant.png"))
		self.resize(QSize(700,500).expandedTo(self.minimumSizeHint()))
		
		self.txtMetadata = QTextBrowser()
		
		if self.useQgis:
			self.table = QTableView(self)
			
			self.preview = qgis.gui.QgsMapCanvas(self)
			self.preview.setCanvasColor(QColor(255,255,255))
		
		self.tabs = QTabWidget()
		self.tabs.addTab(self.txtMetadata, "Metadata")
		if self.useQgis:
			self.tabs.addTab(self.table, "Table")
			self.tabs.addTab(self.preview, "Preview")
		
		self.setCentralWidget(self.tabs)

		self.tree = QTreeView()
		self.tree.setRootIsDecorated(False)
		self.tree.setEditTriggers( QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed )
		self.dock = QDockWidget("Database view", self)
		self.dock.setFeatures(QDockWidget.DockWidgetMovable)
		self.dock.setWidget(self.tree)
		
		self.statusBar = QStatusBar(self)
		self.setStatusBar(self.statusBar)
		
		self.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
		
		self.createMenu()
	
	def createMenu(self):
		
		self.actionDbDisconnect = QAction("Disconnect", self)
		self.actionDbDisconnect.setEnabled(False)
		
		self.actionCreateSchema = QAction("Create schema", self)
		self.actionDeleteSchema = QAction("Delete (empty) schema", self)
		
		self.actionCreateTable = QAction("Create table", self)
		self.actionCreateView = QAction("Create view", self)
		self.actionEditTable = QAction("Edit table", self)
		self.actionDeleteTableView = QAction("Delete table/view", self)
		
		self.actionLoadData = QAction("Load data from shapefile", self)
		self.actionDumpData = QAction("Dump data to shapefile", self)
		
		self.menuDb     = QMenu("Database", self)
		self.menuSchema = QMenu("Schema", self)
		self.menuTable  = QMenu("Table", self)
		self.menuData   = QMenu("Data", self)
		
		self.actionsDb = self.listDatabases()
		
		for k,a in self.actionsDb.iteritems():
			self.menuDb.addAction(a)
			a.setCheckable(True)
			self.connect(a, SIGNAL("triggered(bool)"), self.dbConnectSlot)
		self.menuDb.addSeparator()
		self.menuDb.addAction(self.actionDbDisconnect)
		
		for a in [self.actionCreateSchema, self.actionDeleteSchema]:
			self.menuSchema.addAction(a)
		for a in [self.actionCreateTable, self.actionCreateView, self.actionEditTable, self.actionDeleteTableView]:
			self.menuTable.addAction(a)
		for a in [self.actionLoadData, self.actionDumpData]:
			self.menuData.addAction(a)
		
		self.menuBar = QMenuBar(self)
		self.menuBar.addMenu(self.menuDb)
		self.menuBar.addMenu(self.menuSchema)
		self.menuBar.addMenu(self.menuTable)
		self.menuBar.addMenu(self.menuData)
		self.setMenuBar(self.menuBar)
