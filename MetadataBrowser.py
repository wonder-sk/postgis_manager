
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import postgis_utils

class MetadataBrowser(QTextBrowser):

	def __init__(self, parent=None):
		QTextBrowser.__init__(self, parent)
		
		self.db = None
		
	def setDatabase(self, db):
		""" called when connected / disconnected from db """
		self.db = db
		
	def showDbInfo(self):

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
			if not self.db.has_geometry_columns:
				html += '<p><img src=":/icons/warning-20px.png"> &nbsp; ' \
								'geometry_columns table doesn\'t exist!<br>' \
								'This table is essential for many GIS applications for enumeration of tables.</p>'
			if self.db.has_geometry_columns and not self.db.has_geometry_columns_access:
				html += '<p><img src=":/icons/warning-20px.png"> &nbsp; ' \
								'This user doesn\'t have privileges to read contents of geometry_columns table!<br>' \
								'This table is essential for many GIS applications for enumeration of tables.</p>'
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
				
		self.setHtml(html)
	
	
	
	def showSchemaInfo(self, item):
		
		if not item:
			self.setHtml('')
			return

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
			html += '<p><img src=":/icons/warning-20px.png"> &nbsp; This user has no privileges to access this schema!</p>'

		self.setHtml(html)


	def showTableInfo(self, item):

		if not item:
			self.setHtml('')
			return
		
		if item.is_view:
			reltype = "View"
		else:
			reltype = "Table"
			
		table_name, schema_name = item.name, item.schema().name

		# if the estimation is less than 100 rows, try to count them - it shouldn't take long time
		if item.row_count_real == -1 and item.row_count < 100:
			try:
				item.row_count_real = self.db.get_table_rows(table_name, schema_name)
			except postgis_utils.DbError, e:
				pass
			
		html  = '<div style="background-color:#ccccff"><h1>&nbsp;&nbsp;%s</h1></div>' % table_name
		html += '<div style="margin-top:30px; margin-left:10px;"> <table>'
		html += '<tr><td width="150">Relation type:<td>%s' % reltype
		html += '<tr><td>Owner:<td>%s' % item.owner
		html += '<tr><td>Rows (estimation):<td>%d' % item.row_count
		html += '<tr><td>Rows (counted):<td>'
		
		if item.row_count_real != -1:
			html += "%d" % item.row_count_real
		else:
			html += 'Unknown (<a href="action:rows">find out</a>)'
			
		html += '<tr><td>Pages:<td>%d' % item.page_count
		
		# has the user access to this schema?
		if not self.db.get_schema_privileges(schema_name)[1]:
			html += "</table></div> "
			html += '<p><img src=":/icons/warning-20px.png"> &nbsp; This user doesn\'t have usage privileges for this schema!</p>'
			self.setHtml(html)
			return False
			
		
		# permissions
		has_no_privileges = False
		has_read_only = False
		html += "<tr><td>Privileges:<td>"
		priv = self.db.get_table_privileges(table_name, schema_name)
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
		if item.row_count_real != -1 and (item.row_count > 2 * item.row_count_real or item.row_count * 2 < item.row_count_real):
			html += '<p><img src=":/icons/warning-20px.png"> &nbsp; There\'s a significant difference between estimated and real row count. ' \
			        'Consider running VACUUM ANALYZE.'
		html += '</div>'
		
		
		fields = self.db.get_table_fields(table_name, schema_name)
		constraints = self.db.get_table_constraints(table_name, schema_name)
		indexes = self.db.get_table_indexes(table_name, schema_name)
		triggers = self.db.get_table_triggers(table_name, schema_name)
		rules = self.db.get_table_rules(table_name, schema_name)
		
		has_pkey = False
		for con in constraints:
				if con.con_type == postgis_utils.TableConstraint.TypePrimaryKey:
					has_pkey = True
		if not has_pkey:
			html += '<div style="margin-top:10px; margin-left:10px;"><img src=":/icons/warning-20px.png"> &nbsp; No primary key defined for this table!</div>'
		
		html += '<div style="margin-top:30px; margin-left:10px;"><h2>PostGIS</h2>'
		if item.geom_type:
			html += '<table><tr><td width=150>Column:<td>%s<tr><td>Geometry:<td>%s' % (item.geom_column, item.geom_type)
			if item.geom_dim: # only if we have info from geometry_columns
				if item.geom_srid != -1:
					sr_info = self.db.sr_info_for_srid(item.geom_srid)
				else:
					sr_info = "Undefined"
				html += '<tr><td>Dimension:<td>%d<tr><td>Spatial ref:<td>%s (%d)' % (item.geom_dim, sr_info, item.geom_srid)
			# estimated extent
			html += '<tr><td>Extent:<td>'
			try:
				extent = self.db.get_table_estimated_extent(item.geom_column, table_name, schema_name)
				if extent[0] is not None:
					html += '%.5f, %.5f - %.5f, %.5f' % extent
				else:
					html += '(unknown)'
			except postgis_utils.DbError, e:
				html += '(unknown)'
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
			
		# triggers
		if len(triggers) != 0:
			html += '<div style=" margin-top:30px; margin-left:10px"><h2>Triggers</h2>'
			html += '<table><tr bgcolor="#dddddd"><th width="180">Name<th width="180">Function<th>Type<th>Enabled'
			for trig in triggers:
				trig_type = "Before " if trig.type & postgis_utils.TableTrigger.TypeBefore else "After "
				if trig.type & postgis_utils.TableTrigger.TypeInsert: trig_type += "INSERT "
				if trig.type & postgis_utils.TableTrigger.TypeUpdate: trig_type += "UPDATE "
				if trig.type & postgis_utils.TableTrigger.TypeDelete: trig_type += "DELETE "
				if trig.type & postgis_utils.TableTrigger.TypeTruncate: trig_type += "TRUNCATE "
				trig_type += "<br>for each "
				trig_type += "row" if trig.type & postgis_utils.TableTrigger.TypeRow else "statement"
				if trig.enabled:
					txt_enabled = 'Yes (<a href="action:trigger/%s/disable">disable</a>)' % trig.name
				else:
					txt_enabled = 'No (<a href="action:trigger/%s/enable">enable</a>)' % trig.name
				html += '<tr><td>%s (<a href="action:trigger/%s/delete">delete</a>)<td>%s<td>%s<td>%s' % (trig.name, trig.name, trig.function, trig_type, txt_enabled)
			html += "</table>"
			html += "<a href=\"action:triggers/enable\">Enable all triggers</a> / <a href=\"action:triggers/disable\">Disable all triggers</a>"
			html += "</div>"
			
		# rules
		if len(rules) != 0:
			html += '<div style=" margin-top:30px; margin-left:10px"><h2>Rules</h2>'
			html += '<table><tr bgcolor="#dddddd"><th width="180">Name<th>Definition'
			for rule in rules:
				html += '<tr><td>%s (<a href="action:rule/%s/delete">delete</a>)<td>%s' % (rule.name, rule.name, rule.definition)
			html += "</table></div>"
		
			
		if item.is_view:
			html += '<div style=" margin-top:30px; margin-left:10px"><br><h2>View definition</h2>'
			html += '<p>%s</p>' % self.db.get_view_definition(table_name, schema_name)
			html += '</div>'
		
		self.setHtml(html)
		
		if priv[0]: # ability to SELECT?
			return True
		else:
			return False


	def _field_by_number(self, num, fields):
		""" return field specified by its number or None if doesn't exist """
		for fld in fields:
			if fld.num == num:
				return fld
		return None
		
		
