
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
from DatabaseModel import TableItem, SchemaItem, DatabaseModel
import resources
import postgis_utils

class ManagerWindow(QMainWindow):
	
	def __init__(self, use_qgis=False, parent=None):
		QMainWindow.__init__(self, parent)
		
		self.listDatabases()
		
		# connect to database selected last time
		settings = QSettings()
		sel = str(settings.value("/PostgreSQL/connections/selected").toString())
		self.dbConnect(sel)
		
		self.useQgis = use_qgis
		self.currentLayerId = None
		
		self.setupUi()
		
		self.dbModel = DatabaseModel(self, self.db)
		self.tree.setModel(self.dbModel)
		
		self.tree.expandAll()
		self.tree.resizeColumnToContents(0)
		
		# setup signal-slot connections
		self.connect(self.tree, SIGNAL("clicked(const QModelIndex&)"), self.itemActivated)
		self.connect(self.tree.model(), SIGNAL("dataChanged(const QModelIndex &, const QModelIndex &)"), self.refreshTable)
		# actions
		self.connect(self.actionCreateTable, SIGNAL("triggered(bool)"), self.createTable)
		self.connect(self.actionDeleteTableView, SIGNAL("triggered(bool)"), self.deleteTable)
		self.connect(self.actionCreateSchema, SIGNAL("triggered(bool)"), self.createSchema)
		self.connect(self.actionDeleteSchema, SIGNAL("triggered(bool)"), self.deleteSchema)
		self.connect(self.actionLoadData, SIGNAL("triggered(bool)"), self.loadData)
		self.connect(self.actionDumpData, SIGNAL("triggered(bool)"), self.dumpData)
		#self.connect(self.actionDbConnect, SIGNAL("triggered(bool)"), self.dbConnect)
		self.connect(self.actionDbDisconnect, SIGNAL("triggered(bool)"), self.dbDisconnect)
		
		
	def listDatabases(self):
		self.actionsDb = {}
		settings = QSettings()
		settings.beginGroup("/PostgreSQL/connections")
		keys = settings.childGroups()
		
		for key in keys:
			a = QAction(key, self)
			self.connect(a, SIGNAL("triggered(bool)"), self.dbConnectSlot)
			self.actionsDb[str(key)] = a
			
		settings.endGroup()
	
		
	def dbConnectSlot(self):
		sel = str(self.sender().text())
		print "connect", sel
		self.dbConnect(sel)
		

	def dbConnect(self, selected):
		settings = QSettings()
		print "selected:" + selected
		key = "/PostgreSQL/connections/" + selected
		get_value = lambda x: settings.value( key + "/" + x )
		get_value_str = lambda x: str(get_value(x).toString())
		host, database, username, password = map(get_value_str, ["host", "database", "username", "password"])
		port = get_value("port").toInt()[0]
		
		print host,port,database,username,password
		self.db = postgis_utils.GeoDB(host=host, port=port, dbname=database, user=username, passwd=password)
		
		settings.setValue("/PostgreSQL/connections/selected", QVariant(selected))
		
		# set action as checked
		# TODO: set other actions unchecked
		if self.actionsDb.has_key(selected):
			self.actionsDb[selected].setChecked(True)
	
	def dbDisconnect(self):
		
		#self.db = None
		# TODO: update UI
		pass

	
	def refreshTable(self):
		self.tree.model().loadFromDb()
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
		if item.is_view:
			reltype = "View"
		else:
			reltype = "Table"
		html = "<h1>%s</h1> (%s)<br>Owner: %s<br>Rows (estimation): %d<br>Pages: %d<p>Geometry: %s" % (item.name, reltype, item.owner, item.row_count, item.page_count, item.geom_type)
		html += "<table><tr><th>#<th>Name<th>Type<th>Null"
		for fld in self.db.get_table_fields(item.name):
			if fld.notnull: is_null_txt = "N"
			else: is_null_txt = "Y"
			html += "<tr><td>%s<td>%s<td>%s<td>%s" % (fld.num, fld.name, fld.data_type, is_null_txt)
		html += "</table>"
		self.txtMetadata.setHtml(html)
		
	def loadTablePreview(self, item):
		""" if has geometry column load to map canvas """
		if item.geom_type:
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
		
	def deleteTable(self):
		
		sel = self.tree.selectionModel()
		indexes = sel.selectedRows()
		if len(indexes) == 0:
			QMessageBox.information(self, "sorry", "select a table/view for deletion!")
			return
		if len(indexes) > 1:
			QMessageBox.information(self, "sorry", "select only one table/view")
			return
			
		index = indexes[0]
		ptr = index.internalPointer()
		if not isinstance(ptr, TableItem):
			QMessageBox.information(self, "sorry", "select a TABLE or VIEW for deletion")
			return
		
		res = QMessageBox.question(self, "hey!", "really delete table/view %s ?" % ptr.name, QMessageBox.Yes | QMessageBox.No)
		if res != QMessageBox.Yes:
			return
		
		try:
			if ptr.is_view:
				self.db.delete_view(ptr.name)
			else:
				self.db.delete_table(ptr.name)
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
			self.table = QTableView()
			
			self.preview = qgis.gui.QgsMapCanvas()
			self.preview.setCanvasColor(QColor(255,255,255))
		
		self.tabs = QTabWidget()
		self.tabs.addTab(self.txtMetadata, "Metadata")
		if self.useQgis:
			self.tabs.addTab(self.table, "Table")
			self.tabs.addTab(self.preview, "Preview")
		
		self.setCentralWidget(self.tabs)

		self.tree = QTreeView()
		self.tree.setRootIsDecorated(False)
		self.dock = QDockWidget("Database view", self)
		self.dock.setFeatures(QDockWidget.DockWidgetMovable)
		self.dock.setWidget(self.tree)
		
		self.statusBar = QStatusBar(self)
		self.setStatusBar(self.statusBar)
		
		self.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
		
		self.createMenu()
	
	def createMenu(self):
		
		#self.actionDbSelect = QAction("Select database", self)
		#self.actionDbConnect = QAction("Connect", self)
		self.actionDbDisconnect = QAction("Disconnect", self)
		
		self.actionCreateSchema = QAction("Create schema", self)
		self.actionDeleteSchema = QAction("Delete (empty) schema", self)
		
		self.actionCreateTable = QAction("Create table", self)
		self.actionCreateView = QAction("Create view", self)
		self.actionDeleteTableView = QAction("Delete table/view", self)
		
		self.actionLoadData = QAction("Load data from shapefile", self)
		self.actionDumpData = QAction("Dump data to shapefile", self)
		
		self.menuDb     = QMenu("Database", self)
		self.menuSchema = QMenu("Schema", self)
		self.menuTable  = QMenu("Table", self)
		self.menuData   = QMenu("Data", self)
		
		for a in self.actionsDb:
			self.menuDb.addAction(a)
		self.menuDb.addSeparator()
		self.menuDb.addAction(self.actionDbDisconnect)
		
		for a in [self.actionCreateSchema, self.actionDeleteSchema]:
			self.menuSchema.addAction(a)
		for a in [self.actionCreateTable, self.actionCreateView, self.actionDeleteTableView]:
			self.menuTable.addAction(a)
		for a in [self.actionLoadData, self.actionDumpData]:
			self.menuData.addAction(a)
		
		self.menuBar = QMenuBar(self)
		self.menuBar.addMenu(self.menuDb)
		self.menuBar.addMenu(self.menuSchema)
		self.menuBar.addMenu(self.menuTable)
		self.menuBar.addMenu(self.menuData)
		self.setMenuBar(self.menuBar)
