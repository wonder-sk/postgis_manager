
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
from DlgAbout import DlgAbout
from DlgSqlWindow import DlgSqlWindow
from DlgTableProperties import DlgTableProperties
from DatabaseModel import TableItem, SchemaItem, DatabaseModel
from DbTableModel import DbTableModel
from DlgDbError import DlgDbError
from WizardImport import WizardImport
from DlgGeomProcessing import DlgGeomProcessing
from MetadataBrowser import MetadataBrowser

import resources
import postgis_utils

class ManagerWindow(QMainWindow):
	
	def __init__(self, use_qgis=False, parent=None):
		QMainWindow.__init__(self, parent)
		
		self.useQgis = use_qgis
		self.currentLayerId = None
		self.db = None
		
		self.setupUi()
		self.enableGui(False)
		
		settings = QSettings()
		self.restoreGeometry(settings.value("/PostGIS_Manager/geometry").toByteArray())
		self.restoreState(settings.value("/PostGIS_Manager/windowState").toByteArray())
		
		
		self.dbModel = DatabaseModel(self)
		self.tree.setModel(self.dbModel)
		self.currentItem = (None, None)
		
		self.tableModel = None
		
		# setup signal-slot connections
		self.connect(self.tree.selectionModel(), SIGNAL("currentChanged(const QModelIndex&, const QModelIndex&)"), self.itemChanged)
		self.connect(self.tree, SIGNAL("doubleClicked(const QModelIndex&)"), self.editTable)
		self.connect(self.tree.model(), SIGNAL("dataChanged(const QModelIndex &, const QModelIndex &)"), self.refreshTable)
		# text metadata
		self.connect(self.txtMetadata, SIGNAL("anchorClicked(const QUrl&)"), self.metadataLinkClicked)
		
		# connect to database selected last time
		# but first let the manager chance to show the window
		QTimer.singleShot(50, self.dbConnectInit)
		
	
	def closeEvent(self, e):
		""" save window state """
		settings = QSettings()
		settings.setValue("/PostGIS_Manager/windowState", QVariant(self.saveState()))
		settings.setValue("/PostGIS_Manager/geometry", QVariant(self.saveGeometry()))
		
		QMainWindow.closeEvent(self, e)
		
	def listDatabases(self):
		
		actionsDb = {}
		settings = QSettings()
		settings.beginGroup("/PostgreSQL/connections")
		keys = settings.childGroups()
		
		for key in keys:
			actionsDb[unicode(key)] = QAction(key, self)
			
		settings.endGroup()
		
		return actionsDb
	
		
	def dbConnectSlot(self):
		sel = unicode(self.sender().text())
		#print "connect", sel.encode('utf-8')
		self.dbConnect(sel)
		
	def dbConnectInit(self):

		if len(self.actionsDb) == 0:
			QMessageBox.information(self, "No connections", "You apparently haven't defined any database connections yet.\nYou can do so in Quantum GIS by opening Add PostGIS layer dialog.\n\nWithout database connections you won't be able to use this plugin.")
			return

		settings = QSettings()
		selected = unicode(settings.value("/PostgreSQL/connections/selected").toString())
		self.dbConnect(selected)

	def dbConnect(self, selected):
		
		settings = QSettings()
		
		# if there's open database already, get rid of it
		if self.db:
			self.dbDisconnect()
		
		# get connection details from QSettings
		settings.beginGroup( u"/PostgreSQL/connections/" + selected )
		if not settings.contains("database"): # non-existent entry?
			QMessageBox.critical(self, "Error", "Unable to connect: there is no defined database connection \"%s\"." % selected)
			return
		
		get_value_str = lambda x: unicode(settings.value(x).toString())
		host, database, username, password = map(get_value_str, ["host", "database", "username", "password"])
		port = settings.value("port").toInt()[0]
		if not settings.value("save").toBool():
			(password, ok) = QInputDialog.getText(self, "Enter password", "Enter password for connection \"%s\":" % selected, QLineEdit.Password)
			if not ok: return
		settings.endGroup()
		
		self.statusBar.showMessage("Connecting to database (%s) ..." % selected)
		QApplication.processEvents() # give the user chance to see the message :)
		
		# connect to DB
		try:
			self.db = postgis_utils.GeoDB(host=host, port=port, dbname=database, user=username, passwd=password)
		except postgis_utils.DbError, e:
			self.statusBar.clearMessage()
			QMessageBox.critical(self, "error", "Couldn't connect to database:\n"+e.msg)
			return
			
		self.txtMetadata.setDatabase(self.db)
		
		# set as default in QSettings
		settings.setValue("/PostgreSQL/connections/selected", QVariant(selected))
		
		# set action as checked
		if self.actionsDb.has_key(selected):
			self.actionsDb[selected].setChecked(True)
	
		self.actionDbDisconnect.setEnabled(True)
		
		self.statusBar.showMessage("Querying database structure ...")
		
		self.enableGui(True)
		
		self.refreshTable()
		
		self.updateWindowTitle()
		
		self.tree.expandAll()
		self.tree.resizeColumnToContents(0)
		
		self.dbInfo()
		
		self.statusBar.clearMessage()
	
	def dbDisconnect(self):
		
		# uncheck previously selected DB
		for a in self.actionsDb.itervalues():
			if a.isChecked():
				a.setChecked(False)
		
		self.db = None
		self.txtMetadata.setDatabase(None)
		self.refreshTable()
		
		self.actionDbDisconnect.setEnabled(False)
		self.enableGui(False)
		
		self.loadTableMetadata(None)

		self.updateWindowTitle()

	
	def updateWindowTitle(self):
		if self.db:
			self.setWindowTitle("PostGIS Manager - %s - user %s at %s" % (self.db.dbname, self.db.user, self.db.host) )
		else:
			self.setWindowTitle("PostGIS Manager")


	def dbInfo(self):
		""" retrieve information about current server / database """
		
		self.txtMetadata.showDbInfo()
		
		self.unloadDbTable()
		if self.useQgis: self.clearMapPreview()

	
	def refreshTable(self):
		self.tree.model().loadFromDb(self.db)
		self.tree.model().reset()
		self.tree.expandAll()

	def itemChanged(self, index, indexOld):
		""" update information - current database item has been changed """
		item = index.internalPointer()
		
		if isinstance(item, SchemaItem):
			if self.currentItem == (item.name, None):
				return
			self.currentItem = (item.name, None)
			self.loadSchemaMetadata(item)
			self.unloadDbTable()
		elif isinstance(item, TableItem):
			if self.currentItem == (item.schema().name, item.name):
				return
			self.currentItem = (item.schema().name, item.name)
			self.loadTableMetadata(item)
	
	
	def loadSchemaMetadata(self, item):
		""" show metadata about schema """	
		self.txtMetadata.showSchemaInfo(item)

		if self.useQgis: self.clearMapPreview()

	
	def loadTableMetadata(self, item):
		""" show metadata about table """
		if not item:
			self.txtMetadata.setHtml(QString())
			return
		
		if self.txtMetadata.showTableInfo(item):
			self.loadDbTable(item)
			# load also map if qgis is enabled
			if self.useQgis: self.loadMapPreview(item)
		else:
			self.unloadDbTable()
			if self.useQgis: self.clearMapPreview()

			
	def metadataLinkClicked(self, url):
		print unicode(url.path()).encode('utf-8')
		
		action = unicode(url.path())

		if action == 'triggers/enable' or action == 'triggers/disable':
			enable = (action == 'triggers/enable')
			item = self.currentDatabaseItem()
			msg = "Do you want to %s all triggers?" % ("enable" if enable else "disable")
			if QMessageBox.question(self, "Table triggers", msg, QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
				try:
					self.unloadDbTable()
					self.db.table_enable_triggers(item.name, item.schema().name, enable)
					self.loadTableMetadata(item)
				except postgis_utils.DbError, e:
					DlgDbError.showError(e, self)
		
	
	def unloadDbTable(self):
		
		self.table.setModel(None)
		self.tableModel = None

		
	def loadDbTable(self, item):
		
		# the same table?
		if self.table.model() and self.table.model().table == item.name and self.table.model().schema == item.schema().name:
			return
		
		newModel = DbTableModel(self.db, item.schema().name, item.name, item.row_count_real)
		self.table.setModel(newModel)
		del self.tableModel # ensure that old model gets deleted
		self.tableModel = newModel

		
	def loadMapPreview(self, item):
		""" if has geometry column load to map canvas """
		if item and item.geom_type:
			uri = qgis.core.QgsDataSourceURI()
			uri.setConnection(self.db.host, str(self.db.port), self.db.dbname, self.db.user, self.db.passwd)
			uri.setDataSource(item.schema().name, item.name, item.geom_column, "")
			#con = self.db.con_info() + " table=%s (%s) sql=" % (item.name, item.geom_column)
			vl = qgis.core.QgsVectorLayer(uri.uri(), item.name, "postgres")
			if not vl.isValid():
				newLayerId = None
				self.preview.setLayerSet( [] )
			else:
				newLayerId = vl.getLayerID()
				qgis.core.QgsMapLayerRegistry.instance().addMapLayer(vl, False)
				self.preview.setLayerSet( [ qgis.gui.QgsMapCanvasLayer(vl, True, False) ] )
				self.preview.zoomToFullExtent()
				
		else:
			newLayerId = None
			self.preview.setLayerSet( [] )
			
		# remove old layer (if any) and set new
		if self.currentLayerId:
			qgis.core.QgsMapLayerRegistry.instance().removeMapLayer(self.currentLayerId, False)
		self.currentLayerId = newLayerId
			
	def clearMapPreview(self):
		""" remove any layers from preview canvas """
		self.preview.setLayerSet( [] )

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
		self.connect(dlg, SIGNAL("aboutToChangeTable()"), self.aboutToChangeTable)
		dlg.exec_()
		
		# update info
		self.loadTableMetadata(ptr)
	
	def aboutToChangeTable(self):
		""" table is going to be changed, we must close currently opened cursor """
		self.unloadDbTable()
		
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
	
	
	def emptyTable(self):
		""" deletes all items from current table """
		
		ptr = self.currentDatabaseItem()
		if not ptr:
			return
		
		if not isinstance(ptr, TableItem) or ptr.is_view:
			QMessageBox.information(self, "sorry", "select a TABLE to empty it")
			return
		
		res = QMessageBox.question(self, "hey!", "really delete all items frm table %s ?" % ptr.name, QMessageBox.Yes | QMessageBox.No)
		if res != QMessageBox.Yes:
			return
		
		try:
			self.db.empty_table(ptr.name, ptr.schema().name)
			self.loadTableMetadata(ptr)
			QMessageBox.information(self, "good", "table has been emptied.")
		except postgis_utils.DbError, e:
			DlgDbError.showError(e, self)
		

	def deleteTable(self):
		""" deletes current table from database """
		
		ptr = self.currentDatabaseItem()
		if not ptr:
			return
		
		if not isinstance(ptr, TableItem):
			QMessageBox.information(self, "sorry", "select a TABLE or VIEW for deletion")
			return
		
		res = QMessageBox.question(self, "hey!", "really delete table/view %s ?" % ptr.name, QMessageBox.Yes | QMessageBox.No)
		if res != QMessageBox.Yes:
			return
		
		# necessary to close cursor, otherwise deletion fails
		self.unloadDbTable()
		self.dbInfo()
		
		try:
			if ptr.is_view:
				self.db.delete_view(ptr.name, ptr.schema().name)
			else:
				if ptr.geom_column:
					self.db.delete_geometry_table(ptr.name, ptr.schema().name)
				else:
					self.db.delete_table(ptr.name, ptr.schema().name)
			self.refreshTable()
			QMessageBox.information(self, "good", "table/view deleted.")
		except postgis_utils.DbError, e:
			DlgDbError.showError(e, self)
		
	
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
		if not dlg.exec_():
			return
		
		self.refreshTable()

	def dumpData(self):
		dlg = DlgDumpData(self, self.db)
		dlg.exec_()
		
	def importData(self):
		wizard = WizardImport(self, self.db)
		if not wizard.exec_():
			return
	
		self.refreshTable()
		
	def geomProcessing(self):
		dlg = DlgGeomProcessing(self, self.db)
		if not dlg.exec_():
			return
			
		self.refreshTable()
	
	def exportData(self):
		QMessageBox.information(self, "sorry", "wizard not implemented yet.")
		
	def vacuumAnalyze(self):
		""" run VACUUM ANALYZE on this table """
		ptr = self.currentDatabaseItem()
		if not ptr: return
		if not isinstance(ptr, TableItem): #or ptr.is_view:
			QMessageBox.information(self, "sorry", "select a TABLE for vacuum analyze")
			return
		
		self.db.vacuum_analyze(ptr.name, ptr.schema().name)
	
		# update info
		self.loadTableMetadata(ptr)
	
	def prepareMenuMoveToSchema(self):
		""" populate menu with schemas """
		self.menuMoveToSchema.clear()
		for schema in self.db.list_schemas():
			self.menuMoveToSchema.addAction(schema[1], self.moveToSchemaSlot)
		
	def moveToSchemaSlot(self):
		""" find out what item called this slot """
		self.moveToSchema(unicode(self.sender().text()))
		
	def moveToSchema(self, new_schema):
		ptr = self.currentDatabaseItem()
		if not ptr: return
		if not isinstance(ptr, TableItem):
			QMessageBox.information(self, "sorry", "select a table or schema")
			return
		
		self.db.table_move_to_schema(ptr.name, new_schema, ptr.schema().name)
		
		self.refreshTable()
		
	def about(self):
		""" show about box """
		dlg = DlgAbout(self)
		dlg.exec_()
		
	def sqlWindow(self):
		""" show sql window """
		dlg = DlgSqlWindow(self, self.db)
		dlg.exec_()
	
	def enableGui(self, connected):
		""" enable / disable various actions depending whether we're connected or not """
		for a in self.dbActions:
			a.setEnabled(connected)
	
	def setupUi(self):
		
		self.setWindowTitle("PostGIS Manager")
		self.setWindowIcon(QIcon(":/icons/postgis_elephant.png"))
		self.resize(QSize(700,500).expandedTo(self.minimumSizeHint()))
		
		self.txtMetadata = MetadataBrowser()
		self.txtMetadata.setOpenLinks(False)
		self.table = QTableView(self)
		self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
		
		if self.useQgis:
			self.preview = qgis.gui.QgsMapCanvas(self)
			self.preview.setCanvasColor(QColor(255,255,255))
		
		self.tabs = QTabWidget()
		self.tabs.addTab(self.txtMetadata, "Metadata")
		self.tabs.addTab(self.table, "Table")
		if self.useQgis:
			self.tabs.addTab(self.preview, "Preview")
		
		self.setCentralWidget(self.tabs)

		self.tree = QTreeView()
		#self.tree.setRootIsDecorated(False)
		self.tree.setEditTriggers( QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed )
		self.dock = QDockWidget("Database view", self)
		self.dock.setObjectName("DbView")
		self.dock.setFeatures(QDockWidget.DockWidgetMovable)
		self.dock.setWidget(self.tree)
		
		self.statusBar = QStatusBar(self)
		self.setStatusBar(self.statusBar)
		
		self.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
		
		self.createMenu()
	
	def createMenu(self):
		
		self.menuDb     = QMenu("&Database", self)
		self.menuSchema = QMenu("&Schema", self)
		self.menuTable  = QMenu("&Table", self)
		self.menuData   = QMenu("D&ata", self)
		self.menuHelp   = QMenu("&Help", self)
		
		## MENU Database
		self.actionsDb = self.listDatabases()
		for k,a in self.actionsDb.iteritems():
			self.menuDb.addAction(a)
			a.setCheckable(True)
			self.connect(a, SIGNAL("triggered(bool)"), self.dbConnectSlot)
		self.menuDb.addSeparator()
		actionDbInfo = self.menuDb.addAction("Show &info", self.dbInfo)
		actionSqlWindow = self.menuDb.addAction("&SQL window", self.sqlWindow)
		self.menuDb.addSeparator()
		self.actionDbDisconnect = self.menuDb.addAction("&Disconnect", self.dbDisconnect)
		self.actionDbDisconnect.setEnabled(False)
		
		## MENU Schema
		actionCreateSchema = self.menuSchema.addAction("&Create schema", self.createSchema)
		actionDeleteSchema = self.menuSchema.addAction("&Delete (empty) schema", self.deleteSchema)
		
		## MENU Table
		actionCreateTable = self.menuTable.addAction(QIcon(":/icons/toolbar/action_new_table.png"), "Create &table", self.createTable)
		self.menuTable.addSeparator()
		actionEditTable = self.menuTable.addAction(QIcon(":/icons/toolbar/action_edit_table.png"),"&Edit table", self.editTable)
		actionVacuumAnalyze = self.menuTable.addAction("Run VACUUM &ANALYZE", self.vacuumAnalyze)
		self.menuMoveToSchema = self.menuTable.addMenu("Move to &schema")
		self.connect(self.menuMoveToSchema, SIGNAL("aboutToShow()"), self.prepareMenuMoveToSchema)
		self.menuTable.addSeparator()
		actionEmptyTable = self.menuTable.addAction("E&mpty table", self.emptyTable)
		actionDeleteTable = self.menuTable.addAction(QIcon(":/icons/toolbar/action_del_table.png"),"&Delete table/view", self.deleteTable)
		
		## MENU Data
		actionLoadData = self.menuData.addAction("&Load data from shapefile", self.loadData)
		actionDumpData = self.menuData.addAction("&Dump data to shapefile", self.dumpData)
		actionImportData = self.menuData.addAction(QIcon(":/icons/toolbar/action_import.png"), "&Import data", self.importData)
		actionExportData = self.menuData.addAction(QIcon(":/icons/toolbar/action_export.png"), "&Export data", self.exportData)
		self.menuData.addSeparator()
		actionGeomProcessing = self.menuData.addAction("&Geometry processing...", self.geomProcessing)
		
		## MENU About
		self.menuHelp.addAction("&About", self.about)
		
		## menu bar
		self.menuBar = QMenuBar(self)
		self.menuBar.addMenu(self.menuDb)
		self.menuBar.addMenu(self.menuSchema)
		self.menuBar.addMenu(self.menuTable)
		self.menuBar.addMenu(self.menuData)
		self.menuBar.addMenu(self.menuHelp)
		self.setMenuBar(self.menuBar)
		
		# toolbar
		self.toolBar = QToolBar(self)
		self.toolBar.setObjectName("PostGIS_Manager_ToolBar")
		self.toolBar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
		self.toolBar.addAction(actionCreateTable)
		self.toolBar.addAction(actionEditTable)
		self.toolBar.addAction(actionDeleteTable)
		self.toolBar.addSeparator()
		self.toolBar.addAction(actionImportData)
		self.toolBar.addAction(actionExportData)
		self.addToolBar(self.toolBar)

		# database actions - enabled only when we're not connected
		# (menu "move to schema" actually isn't an action... we're abusing python's duck typing :-)
		self.dbActions = [ actionDbInfo, actionSqlWindow, actionCreateSchema, actionDeleteSchema,
			actionCreateTable, actionEditTable, actionVacuumAnalyze, actionEmptyTable, actionDeleteTable,
			actionLoadData, actionDumpData, actionImportData, actionExportData, actionGeomProcessing,
			self.menuMoveToSchema ]
		