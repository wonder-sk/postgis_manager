
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
			actionsDb[unicode(key)] = QAction(key, self)
			
		settings.endGroup()
		
		return actionsDb
	
		
	def dbConnectSlot(self):
		sel = unicode(self.sender().text())
		print "connect", sel
		self.dbConnect(sel)
		

	def dbConnect(self, selected=None):
		
		settings = QSettings()
		if selected == None:
			selected = unicode(settings.value("/PostgreSQL/connections/selected").toString())
		print "selected:", selected
		
		# if there's open database already, get rid of it
		if self.db:
			self.dbDisconnect()
		
		# get connection details from QSettings
		key = u"/PostgreSQL/connections/" + selected
		get_value = lambda x: settings.value( key + "/" + x )
		get_value_str = lambda x: unicode(get_value(x).toString())
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
			if gis_info[1] != gis_info[2]:
				html += '<p><img src=":/icons/warning-20px.png"> &nbsp; ' \
				        'Version of installed scripts doesn\'t match version of released scripts!<br>' \
								'This is probably a result of incorrect PostGIS upgrade.</p>'
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
		has_no_privileges = False
		has_read_only = False
		html += "<tr><td>Privileges:<td>"
		priv = self.db.get_table_privileges(item.name, item.schema().name)
		if priv[0] or priv[1] or priv[2] or priv[3]:
			if priv[0]: html += "select "
			if priv[1]: html += "insert "
			if priv[2]: html += "update "
			if priv[3]: html += "delete "
			if not priv[1] and not priv[2] and not priv[3]:
				has_read_only = True
		else:
			html += "<i>none</i>"
			has_no_privileges = True
		html += '</table>'
		if has_no_privileges:
			html += '<p><img src=":/icons/warning-20px.png"> &nbsp; This user has no privileges!</p>'
		elif has_read_only:
			html += '<p><img src=":/icons/warning-20px.png"> &nbsp; This user has read-only privileges.</p>'
		if item.row_count > 2 * item.row_count_real or item.row_count * 2 < item.row_count_real:
			html += '<p><img src=":/icons/warning-20px.png"> &nbsp; There\'s a significant difference between estimated and real row count. ' \
			        'Consider running VACUUM ANALYZE.'
		html += '</div>'
		
		fields = self.db.get_table_fields(item.name, item.schema().name)
		constraints = self.db.get_table_constraints(item.name, item.schema().name)
		indexes = self.db.get_table_indexes(item.name, item.schema().name)
		
		has_pkey = False
		for con in constraints:
				if con.con_type == postgis_utils.TableConstraint.TypePrimaryKey:
					has_pkey = True
		if not has_pkey:
			html += '<div style="margin-top:10px; margin-left:10px;"><img src=":/icons/warning-20px.png"> &nbsp; No primary key defined for this table!</div>'
		
		html += '<div style="margin-top:30px; margin-left:10px;"><h2>PostGIS</h2>'
		if item.geom_type:
			html += '<table><tr><td>Column:<td>%s<tr><td>Geometry:<td>%s' % (item.geom_column, item.geom_type)
			if item.geom_dim: # only if we have info from geometry_columns
				html += '<tr><td>Dimension:<td>%d<tr><td>SRID:<td>%d' % (item.geom_dim, item.geom_srid)
			html += '</table>'
			if item.geom_type == 'geometry':
				html += '<p><img src=":/icons/warning-20px.png"> &nbsp; There isn\'t entry in geometry_columns!</p>'
			# find out geometry's column number
			for fld in fields:
				if fld.name == item.geom_column:
					geom_col_num = fld.num
			# find out whether it has spatial index on it
			has_spatial_index = False
			for idx in indexes:
				if geom_col_num in idx.columns:
					has_spatial_index = True
			if not has_spatial_index:
				html += '<p><img src=":/icons/warning-20px.png"> &nbsp; No spatial index defined.</p>'
		else:
			html += '<p>This is not a spatial table.</p>'
		html += '</div>'
		
		# fields
		html += '<div style="margin-top:30px; margin-left:10px"><h2>Fields</h2>'
		html += '<table><tr bgcolor="#dddddd">'
		html += '<th width="30"># <th width="180">Name <th width="100">Type <th width="50">Length<th width="50">Null <th>Default '
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
		print unicode(url.path())
		
	
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
		self.menuDb.addAction("Show &info", self.dbInfo)
		self.menuDb.addAction("&SQL window", self.sqlWindow)
		self.menuDb.addSeparator()
		self.actionDbDisconnect = self.menuDb.addAction("&Disconnect", self.dbDisconnect)
		self.actionDbDisconnect.setEnabled(False)
		
		## MENU Schema
		self.menuSchema.addAction("&Create schema", self.createSchema)
		self.menuSchema.addAction("&Delete (empty) schema", self.deleteSchema)
		
		## MENU Table
		actionCreateTable = self.menuTable.addAction(QIcon(":/icons/toolbar/action_new_table.png"), "Create &table", self.createTable)
		self.menuTable.addSeparator()
		actionEditTable = self.menuTable.addAction(QIcon(":/icons/toolbar/action_edit_table.png"),"&Edit table", self.editTable)
		self.menuTable.addAction("Run VACUUM &ANALYZE", self.vacuumAnalyze)
		self.menuMoveToSchema = self.menuTable.addMenu("Move to &schema")
		self.connect(self.menuMoveToSchema, SIGNAL("aboutToShow()"), self.prepareMenuMoveToSchema)
		self.menuTable.addSeparator()
		self.menuTable.addAction("E&mpty table", self.emptyTable)
		actionDeleteTable = self.menuTable.addAction(QIcon(":/icons/toolbar/action_del_table.png"),"&Delete table/view", self.deleteTable)
		
		## MENU Data
		self.menuData.addAction("&Load data from shapefile", self.loadData)
		self.menuData.addAction("&Dump data to shapefile", self.dumpData)
		actionImportData = self.menuData.addAction(QIcon(":/icons/toolbar/action_import.png"), "&Import data", self.importData)
		actionExportData = self.menuData.addAction(QIcon(":/icons/toolbar/action_export.png"), "&Export data", self.exportData)
		
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
