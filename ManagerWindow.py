
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

import resources
import postgis_utils

class ManagerWindow(QMainWindow):
	
	def __init__(self, use_qgis=False, parent=None):
		QMainWindow.__init__(self, parent)
		
		self.useQgis = use_qgis
		self.currentLayerId = None
		self.db = None
		
		self.setupUi()
		
		settings = QSettings()
		self.restoreGeometry(settings.value("/PostGIS_Manager/geometry").toByteArray())
		self.restoreState(settings.value("/PostGIS_Manager/windowState").toByteArray())
		
		
		self.dbModel = DatabaseModel(self)
		self.tree.setModel(self.dbModel)
		
		self.tableModel = None
		
		# setup signal-slot connections
		self.connect(self.tree, SIGNAL("clicked(const QModelIndex&)"), self.itemActivated)
		self.connect(self.tree, SIGNAL("doubleClicked(const QModelIndex&)"), self.editTable)
		self.connect(self.tree.model(), SIGNAL("dataChanged(const QModelIndex &, const QModelIndex &)"), self.refreshTable)
		# actions
		self.connect(self.actionCreateTable, SIGNAL("triggered(bool)"), self.createTable)
		self.connect(self.actionEditTable, SIGNAL("triggered(bool)"), self.editTable)
		self.connect(self.actionEmptyTable, SIGNAL("triggered(bool)"), self.emptyTable)
		self.connect(self.actionDeleteTableView, SIGNAL("triggered(bool)"), self.deleteTable)
		self.connect(self.actionCreateSchema, SIGNAL("triggered(bool)"), self.createSchema)
		self.connect(self.actionDeleteSchema, SIGNAL("triggered(bool)"), self.deleteSchema)
		self.connect(self.actionLoadData, SIGNAL("triggered(bool)"), self.loadData)
		self.connect(self.actionDumpData, SIGNAL("triggered(bool)"), self.dumpData)
		self.connect(self.actionDbInfo, SIGNAL("triggered(bool)"), self.dbInfo)
		self.connect(self.actionSqlWindow, SIGNAL("triggered(bool)"), self.sqlWindow)
		self.connect(self.actionDbDisconnect, SIGNAL("triggered(bool)"), self.dbDisconnect)
		self.connect(self.actionAbout, SIGNAL("triggered(bool)"), self.about)
		# text metadata
		self.connect(self.txtMetadata, SIGNAL("anchorClicked(const QUrl&)"), self.metadataLinkClicked)
		
		# connect to database selected last time
		# but first let the manager chance to show the window
		QTimer.singleShot(50, self.dbConnect)
		
	
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
			actionsDb[str(key)] = QAction(key, self)
			
		settings.endGroup()
		
		return actionsDb
	
		
	def dbConnectSlot(self):
		sel = str(self.sender().text())
		print "connect", sel
		self.dbConnect(sel)
		

	def dbConnect(self, selected=None):
		
		settings = QSettings()
		if selected == None:
			selected = str(settings.value("/PostgreSQL/connections/selected").toString())
		print "selected:" + selected
		
		# if there's open database already, get rid of it
		if self.db:
			self.dbDisconnect()
		
		# get connection details from QSettings
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
		
		self.updateWindowTitle()
		
		self.tree.expandAll()
		self.tree.resizeColumnToContents(0)
		
		self.dbInfo()
		
	
	def dbDisconnect(self):
		
		# uncheck previously selected DB
		for a in self.actionsDb.itervalues():
			if a.isChecked():
				a.setChecked(False)
		
		self.db = None
		self.refreshTable()
		
		self.actionDbDisconnect.setEnabled(False)
		
		self.loadTableMetadata(None)

		self.updateWindowTitle()

	
	def updateWindowTitle(self):
		if self.db:
			self.setWindowTitle("PostGIS Manager - %s - user %s at %s" % (self.db.dbname, self.db.user, self.db.host) )
		else:
			self.setWindowTitle("PostGIS Manager")


	def dbInfo(self):
		""" retrieve information about current server / database """
		info = self.db.get_info()
		
		html  = '<div style="background-color:#ccffcc"><h1>&nbsp;&nbsp;%s</h1></div>' % self.db.dbname
		html += '<div><h2>Connection details</h2><table>'
		html += '<tr><td width="100">Host:<td>%s<tr><td>User:<td>%s' % (self.db.host, self.db.user)
		html += '</table>'
		
		html += '<h2>PostGIS</h2>'
		if self.db.has_postgis:
			gis_info = self.db.get_postgis_info()
			html += '<table>'
			html += '<tr><td width="100">Library:<td>%s' % gis_info[0]
			html += '<tr><td>Scripts:<td>%s' % gis_info[1]
			html += '<tr><td>GEOS:<td>%s' % gis_info[3]
			html += '<tr><td>Proj:<td>%s' % gis_info[4]
			html += '<tr><td>Use stats:<td>%s' % gis_info[5]
			html += '</table>'
		else:
			html += '<p><img src=":/icons/warning-20px.png"> &nbsp; PostGIS support not enabled!</p>'
			
		priv = self.db.get_database_privileges()
		html += '<h2>Privileges</h2>'
		if priv[0] or priv[1]:
			html += "<div>User has privileges:<ul>"
			if priv[0]: html += "<li> create new schemas"
			if priv[1]: html += "<li> create temporary tables"
			html += "</ul></div>"
		else:
			html += "<div>User has no privileges :-(</div>"
		
		html += '<h2>Server version</h2>' + info
				
		self.txtMetadata.setHtml(html)
		
		self.unloadDbTable()

	
	def refreshTable(self):
		self.tree.model().loadFromDb(self.db)
		self.tree.model().reset()
		self.tree.expandAll()
		
	def itemActivated(self, index):
		item = index.internalPointer()
		
		if isinstance(item, SchemaItem):
			self.loadSchemaMetadata(item)
			self.unloadDbTable()
		elif isinstance(item, TableItem):
			self.loadTableMetadata(item)
			
	
	def loadSchemaMetadata(self, item):
		""" show metadata about schema """	
		html  = '<div style="background-color:#ffcccc"><h1>&nbsp;&nbsp;%s</h1></div>' % item.name
		html += "<p> (schema)<p>Tables: %d<br>Owner: %s" % (item.childCount(), item.owner)
		html += "<br><br>"
		priv = self.db.get_schema_privileges(item.name)
		if priv[0] or priv[1]:
			html += "<p>User has privileges:<ul>"
			if priv[0]: html += "<li>create new objects"
			if priv[1]: html += "<li>access objects"
			html += "</ul></p>"
		else:
			html += "<p>User has no privileges :-(</p>"
		self.txtMetadata.setHtml(html)
		
	
	def _field_by_number(self, num, fields):
		""" return field specified by its number or None if doesn't exist """
		for fld in fields:
			if fld.num == num:
				return fld
		return None
		
		
	def loadTableMetadata(self, item):
		""" show metadata about table """
		if not item:
			self.txtMetadata.setHtml(QString())
			return
		
		if item.is_view:
			reltype = "View"
		else:
			reltype = "Table"
			
		if not hasattr(item, 'row_count_real'):
			try:
				item.row_count_real = self.db.get_table_rows(item.name, item.schema().name)
			except postgis_utils.DbError, e:
				self.db.con.rollback()
				# possibly we don't have permission for this
				item.row_count_real = '(unknown)'
			
		html  = '<div style="background-color:#ccccff"><h1>&nbsp;&nbsp;%s</h1></div>' % item.name
		html += '<div style="margin-top:30px; margin-left:10px;"> <table>'
		html += '<tr><td width="150">Relation type:<td>%s' % reltype
		html += '<tr><td>Owner:<td>%s' % item.owner
		html += '<tr><td>Rows (estimation):<td>%d' % item.row_count
		html += '<tr><td>Rows (counted):<td>%s' % item.row_count_real
		html += '<tr><td>Pages:<td>%d' % item.page_count
		
		# permissions
		html += "<tr><td>Privileges:<td>"
		priv = self.db.get_table_privileges(item.name, item.schema().name)
		if priv[0] or priv[1] or priv[2] or priv[3]:
			if priv[0]: html += "select "
			if priv[1]: html += "insert "
			if priv[2]: html += "update "
			if priv[3]: html += "delete "
		else:
			html += "<i>none</i>"
		html += '</table></div>'
		
		html += '<div style="margin-top:30px; margin-left:10px;"><h2>PostGIS</h2>'
		if item.geom_type:
			html += '<table><tr><td>Column:<td>%s<tr><td>Geometry:<td>%s</table>' % (item.geom_column, item.geom_type)
		else:
			html += '<p>This is not a spatial table.</p>'
		html += '</div>'
		
		constraints = self.db.get_table_constraints(item.name, item.schema().name)
		
		# fields
		html += '<div style="margin-top:30px; margin-left:10px"><h2>Fields</h2>'
		html += '<table><tr bgcolor="#dddddd">'
		html += '<th width="30"># <th width="180">Name <th width="100">Type <th width="50">Length<th width="50">Null <th>Default '
		fields = self.db.get_table_fields(item.name, item.schema().name)
		for fld in fields:
			is_null_txt = "N" if fld.notnull else "Y"
			default = fld.default if fld.hasdefault else ""
			fldtype = fld.data_type if fld.modifier == -1 else "%s (%d)" % (fld.data_type, fld.modifier)
			
			# find out whether it's part of primary key
			pk_style = ''
			for con in constraints:
				if con.con_type == postgis_utils.TableConstraint.TypePrimaryKey and fld.num in con.keys:
					pk_style = ' style="text-decoration:underline;"'
					break
			html += '<tr><td align="center">%s<td%s>%s<td>%s<td align="center">%d<td align="center">%s<td>%s' % (fld.num, pk_style, fld.name, fldtype, fld.char_max_len, is_null_txt, default)
		html += "</table></div> "
		
		# constraints
		if len(constraints) != 0:
			html += '<div style=" margin-top:30px; margin-left:10px"><br><h2>Constraints</h2>'
			html += '<table><tr bgcolor="#dddddd"><th width="180">Name<th width="100">Type<th width="180">Column(s)'
			for con in constraints:
				if   con.con_type == postgis_utils.TableConstraint.TypeCheck:      con_type = "Check"
				elif con.con_type == postgis_utils.TableConstraint.TypePrimaryKey: con_type = "Primary key"
				elif con.con_type == postgis_utils.TableConstraint.TypeForeignKey: con_type = "Foreign key"
				elif con.con_type == postgis_utils.TableConstraint.TypeUnique:     con_type = "Unique"
				keys = ""
				for key in con.keys:
					if len(keys) != 0: keys += "<br>"
					keys += self._field_by_number(key, fields).name
				html += "<tr><td>%s<td>%s<td>%s" % (con.name, con_type, keys)
			html += "</table></div>"
		
		# indexes
		indexes = self.db.get_table_indexes(item.name, item.schema().name)
		if len(indexes) != 0:
			html += '<div style=" margin-top:30px; margin-left:10px"><h2>Indexes</h2>'
			html += '<table><tr bgcolor="#dddddd"><th width="180">Name<th width="180">Column(s)'
			for fld in indexes:
				keys = ""
				for key in fld.columns:
					if len(keys) != 0: keys += "<br>"
					keys += self._field_by_number(key, fields).name
				html += "<tr><td>%s<td>%s" % (fld.name, keys)
			html += "</table></div>"
			
		if item.is_view:
			html += '<div style=" margin-top:30px; margin-left:10px"><br><h2>View definition</h2>'
			html += '<p>%s</p>' % self.db.get_view_definition(item.name, item.schema().name)
			html += '</div>'
		
		self.txtMetadata.setHtml(html)
		
		self.loadDbTable(item)
		
		# load also map if qgis is enabled
		if self.useQgis:
			self.loadMapPreview(item)
			
	def metadataLinkClicked(self, url):
		print str(url.path())
		
	
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
		dlg.exec_()

	def dumpData(self):
		dlg = DlgDumpData(self, self.db)
		dlg.exec_()
		
		
	def about(self):
		""" show about box """
		dlg = DlgAbout(self)
		dlg.exec_()
		
	def sqlWindow(self):
		""" show sql window """
		dlg = DlgSqlWindow(self, self.db)
		dlg.exec_()
	
	
	def setupUi(self):
		
		self.setWindowTitle("PostGIS Manager")
		self.setWindowIcon(QIcon(":/icons/postgis_elephant.png"))
		self.resize(QSize(700,500).expandedTo(self.minimumSizeHint()))
		
		self.txtMetadata = QTextBrowser()
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
		self.tree.setRootIsDecorated(False)
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
		
		self.actionDbInfo = QAction("Show info", self)
		self.actionSqlWindow = QAction("SQL window", self)
		self.actionDbDisconnect = QAction("Disconnect", self)
		self.actionDbDisconnect.setEnabled(False)
		
		self.actionCreateSchema = QAction("Create schema", self)
		self.actionDeleteSchema = QAction("Delete (empty) schema", self)
		
		self.actionCreateTable = QAction("Create table", self)
		self.actionCreateView = QAction("Create view", self)
		self.actionEditTable = QAction("Edit table", self)
		self.actionDeleteTableView = QAction("Delete table/view", self)
		self.actionEmptyTable = QAction("Empty table", self)
		
		self.actionLoadData = QAction("Load data from shapefile", self)
		self.actionDumpData = QAction("Dump data to shapefile", self)
		
		self.actionAbout = QAction("About", self)
		
		self.menuDb     = QMenu("Database", self)
		self.menuSchema = QMenu("Schema", self)
		self.menuTable  = QMenu("Table", self)
		self.menuData   = QMenu("Data", self)
		self.menuHelp   = QMenu("Help", self)
		
		self.actionsDb = self.listDatabases()
		
		for k,a in self.actionsDb.iteritems():
			self.menuDb.addAction(a)
			a.setCheckable(True)
			self.connect(a, SIGNAL("triggered(bool)"), self.dbConnectSlot)
		self.menuDb.addSeparator()
		self.menuDb.addAction(self.actionDbInfo)
		self.menuDb.addAction(self.actionSqlWindow)
		self.menuDb.addSeparator()
		self.menuDb.addAction(self.actionDbDisconnect)
		
		for a in [self.actionCreateSchema, self.actionDeleteSchema]:
			self.menuSchema.addAction(a)
		for a in [self.actionCreateTable, self.actionCreateView, self.actionEditTable, self.actionEmptyTable, self.actionDeleteTableView]:
			self.menuTable.addAction(a)
		for a in [self.actionLoadData, self.actionDumpData]:
			self.menuData.addAction(a)
		
		self.menuHelp.addAction(self.actionAbout)
		
		self.menuBar = QMenuBar(self)
		self.menuBar.addMenu(self.menuDb)
		self.menuBar.addMenu(self.menuSchema)
		self.menuBar.addMenu(self.menuTable)
		self.menuBar.addMenu(self.menuData)
		self.menuBar.addMenu(self.menuHelp)
		self.setMenuBar(self.menuBar)
