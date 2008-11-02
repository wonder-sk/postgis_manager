"""
PostGIS Manager

Copyright 2008 Martin Dobias
licensed under the terms of GNU GPL v2


Good resource for metadata extraction:
http://www.alberton.info/postgresql_meta_info.html
System information functions:
http://www.postgresql.org/docs/8.0/static/functions-info.html
"""

import psycopg2


class TableAttribute:
	def __init__(self, row):
		self.num, self.name, self.data_type, self.char_max_len, self.modifier, self.notnull, self.hasdefault, self.default = row


class TableConstraint:
	""" class that represents a constraint of a table (relation) """
	
	TypeCheck, TypeForeignKey, TypePrimaryKey, TypeUnique = range(4)
	types = { "c" : TypeCheck, "f" : TypeForeignKey, "p" : TypePrimaryKey, "u" : TypeUnique }
	
	on_action = { "a" : "NO ACTION", "r" : "RESTRICT", "c" : "CASCADE", "n" : "SET NULL", "d" : "SET DEFAULT" }
	match_types = { "u" : "UNSPECIFIED", "f" : "FULL", "p" : "PARTIAL" }
	
	def __init__(self, row):
		self.name, con_type, self.is_defferable, self.is_deffered, self.keys = row[:5]
		
		self.con_type = TableConstraint.types[con_type]   # convert to enum
		if self.con_type == TableConstraint.TypeCheck:
			self.check_src = row[5]
		elif self.con_type == TableConstraint.TypeForeignKey:
			self.foreign_table = row[6]
			self.foreign_on_update = TableConstraint.on_action[row[7]]
			self.foreign_on_delete = TableConstraint.on_action[row[8]]
			self.foreign_match_type = TableConstraint.match_types[row[9]]
			self.foreign_keys = row[10]



class DbError(Exception):
	def __init__(self, message, query=None):
		self.message = message
		self.query = query
	def __str__(self):
		return "MESSAGE: %s\nQUERY: %s" % (self.message, self.query)

class TableField:
	def __init__(self, name, data_type, is_null=None, default=None):
		self.name, self.data_type, self.is_null, self.default = name, data_type, is_null, default
		
	def is_null_txt(self):
		if self.is_null:
			return "NULL"
		else:
			return "NOT NULL"
		
	def field_def(self):
		""" return field definition as used for CREATE TABLE or ALTER TABLE command """
		txt = "%s %s %s" % (self.name, self.data_type, self.is_null_txt())
		if self.default and len(self.default) > 0:
			txt += " DEFAULT %s" % self.default
		return txt
		

class GeoDB:
	
	def __init__(self, host=None, port=None, dbname=None, user=None, passwd=None):
		
		self.host = host
		self.port = port
		self.dbname = dbname
		self.user = user
		self.passwd = passwd
		
		try:
			self.con = psycopg2.connect(self.con_info())
		except psycopg2.OperationalError, e:
			raise DbError(e.message)
		
	def con_info(self):
		con_str = ''
		if self.host:   con_str += "host='%s' "     % self.host
		if self.port:   con_str += "port=%d "       % self.port
		if self.dbname: con_str += "dbname='%s' "   % self.dbname
		if self.user:   con_str += "user='%s' "     % self.user
		if self.passwd: con_str += "password='%s' " % self.passwd
		return con_str
		
	def get_info(self):
		c = self.con.cursor()
		self._exec_sql(c, "SELECT version()")
		return c.fetchone()[0]
	
	def get_postgis_info(self):
		""" returns tuple about postgis support:
			- lib version
			- installed scripts version
			- released scripts version
			- geos version
			- proj version
			- whether uses stats
		"""
		c = self.con.cursor()
		self._exec_sql(c, "SELECT postgis_lib_version(), postgis_scripts_installed(), postgis_scripts_released(), postgis_geos_version(), postgis_proj_version(), postgis_uses_stats()")
		return c.fetchone()
	
	def list_schemas(self):
		"""
			get list of schemas in tuples: (oid, name, owner, perms)
		"""
		c = self.con.cursor()
		sql = "SELECT oid, nspname, pg_get_userbyid(nspowner), nspacl FROM pg_namespace WHERE nspname !~ '^pg_' AND nspname != 'information_schema'"
		self._exec_sql(c, sql)
		return c.fetchall()
			
	def list_geotables(self, schema=None):
		"""
			get list of tables with schemas, whether user has privileges, whether table has geometry column(s) etc.
			
			pg_class:
			- relname = nazov relacie (tabulka / view / index / ....)
			- relnamespace = oid schemy
			- reltype = oid typu relacie
			- relowner = oid vlastnika
			- relpages = kolko stranok zabera (stranka = 8kb)
			- reltuples = odhad planovaca kolko ma riadkov
			- relkind = r = ordinary table, i = index, S = sequence, v = view, c = composite type, s = special, t = TOAST table 
			
			- relnatts = pocet stlpcov tabulky (vid pg_attribute)
			- relchecks = pocet constraintov (vid pg_constraint)
			- reltriggers = pocet triggerov (vid pg_trigger)
			- relacl = privilegia
			
			pg_namespace:
			- nspname = nazov schemy
			- nspowner = oid vlastnika
			- nspacl = privilegia
			
			funkcia - pg_get_userbyid(relowner)
			
			geometry_columns:
			- f_table_schema
			- f_table_name
			- f_geometry_column
			- coord_dimension
			- srid
			- type
			
			checking privileges:
			- has_schema_privilege(pg_namespace.nspname,'usage')
			- has_table_privilege('\"'||pg_namespace.nspname||'\".\"'||pg_class.relname||'\"','select')
		"""
		c = self.con.cursor()
		
		if schema:
			schema_where = " AND nspname = '%s' " % schema
		else:
			schema_where = " AND nspname NOT IN ('information_schema','pg_catalog') "
			
		# TODO: geometry_columns relation may not exist!
		
		# LEFT OUTER JOIN: zmena oproti LEFT JOIN ze ak moze spojit viackrat tak to urobi
		sql = "SELECT relname, nspname, relkind, pg_get_userbyid(relowner), reltuples, relpages, geometry_columns.f_geometry_column, geometry_columns.type FROM pg_class " \
		      "  JOIN pg_namespace ON relnamespace=pg_namespace.oid " \
		      "  LEFT OUTER JOIN geometry_columns ON relname=f_table_name AND nspname=f_table_schema " \
		      "WHERE (relkind = 'r' or relkind='v') " + schema_where + \
		      "ORDER BY nspname, relname"
		self._exec_sql(c, sql)
		return c.fetchall()
			
	
	def get_table_rows(self, table, schema='public'):
		c = self.con.cursor()
		self._exec_sql(c, "SELECT COUNT(*) FROM %s" % self._table_name(schema, table))
		return c.fetchone()[0]
		
		
	def get_table_fields(self, table, schema='public'):
		""" return list of columns in table """
		c = self.con.cursor()
		sql = """SELECT a.attnum AS ordinal_position,
				a.attname AS column_name,
				t.typname AS data_type,
				a.attlen AS char_max_len,
				a.atttypmod AS modifier,
				a.attnotnull AS notnull,
				a.atthasdef AS hasdefault,
				adef.adsrc AS default_value
			FROM pg_class c
			JOIN pg_attribute a ON a.attrelid = c.oid
			JOIN pg_type t ON a.atttypid = t.oid
			JOIN pg_namespace nsp ON c.relnamespace = nsp.oid
			LEFT JOIN pg_attrdef adef ON adef.adrelid = a.attrelid AND adef.adnum = a.attnum
			WHERE
				nsp.nspname = '%s' AND
			  c.relname = '%s' AND
				a.attnum > 0
			ORDER BY a.attnum""" % (schema, table)

		self._exec_sql(c, sql)
		attrs = []
		for row in c.fetchall():
			attrs.append(TableAttribute(row))
		return attrs
		
		
	def get_table_indexes(self, table, schema='public'):
		""" get info about table's indexes. ignore primary key and unique index, they get listed in constaints """
		# TODO: schema
		c = self.con.cursor()
		sql = """SELECT relname, indkey FROM pg_class, pg_index WHERE pg_class.oid = pg_index.indexrelid AND pg_class.oid IN ( SELECT indexrelid FROM pg_index, pg_class WHERE pg_class.relname='%s' AND pg_class.oid=pg_index.indrelid AND indisunique != 't' AND indisprimary != 't' )""" % table
		self._exec_sql(c, sql)
		return c.fetchall()
	
	
	def get_table_constraints(self, table, schema='public'):
		# TODO: schema
		c = self.con.cursor()
		
		sql = """SELECT c.conname, c.contype, c.condeferrable, c.condeferred, array_to_string(c.conkey, ' '), c.consrc,
		         t2.relname, c.confupdtype, c.confdeltype, c.confmatchtype, array_to_string(c.confkey, ' ') FROM pg_constraint c
		  LEFT JOIN pg_class t ON c.conrelid = t.oid
			LEFT JOIN pg_class t2 ON c.confrelid = t2.oid
			WHERE t.relname = '%s'""" % table
		
		self._exec_sql(c, sql)
		
		constrs = []
		for row in c.fetchall():
			constrs.append(TableConstraint(row))
		return constrs
		
	
	def get_view_definition(self, view, schema=None):
		""" returns definition of the view """
		# TODO: schema
		sql = "SELECT pg_get_viewdef(oid) FROM pg_class WHERE relname='%s' AND relkind='v'" % view
		c = self.con.cursor()
		self._exec_sql(c, sql)
		return c.fetchone()[0]
		
	"""
	def list_tables(self):
		c = self.con.cursor()
		c.execute("SELECT relname FROM pg_class WHERE relname !~ '^(pg_|sql_)' AND relkind = 'r'")
		return c.fetchall()
	"""
		
	def add_geometry_column(self, table, geom_type, schema=None, geom_column='the_geom', srid=-1, dim=2):
		
		# use schema if explicitly specified
		if schema:
			schema_part = "'%s', " % schema
		else:
			schema_part = ""
		sql = "SELECT AddGeometryColumn(%s'%s', '%s', %d, '%s', %d)" % (schema_part, table, geom_column, srid, geom_type, dim)
		self._exec_sql_and_commit(sql)
		
	def delete_geometry_column(self, table, geom_column, schema=None):
		""" use postgis function to delete geometry column correctly """
		if schema:
			schema_part = "'%s', " % schema
		else:
			schema_part = ""
		sql = "SELECT DropGeometryColumn(%s'%s', '%s')" % (schema_part, table, geom_column)
		self._exec_sql_and_commit(sql)
		
	def delete_geometry_table(self, table, schema=None):
		""" delete table with one or more geometries using postgis function """
		if schema:
			schema_part = "'%s', " % schema
		else:
			schema_part = ""
		sql = "SELECT DropGeometryTable(%s'%s')" % (schema_part, table)
		self._exec_sql_and_commit(sql)
		
	def create_table(self, table, fields, schema=None):
		""" create ordinary table
				'fields' is array containing instances of TableField """
		# TODO: primary key?
				
		if len(fields) == 0:
			return False
		
		table_name = self._table_name(schema, table)
		
		sql = "CREATE TABLE %s (%s" % (table_name, fields[0].field_def())
		for field in fields[1:]:
			sql += ", %s" % field.field_def()
		sql += ")"
		self._exec_sql_and_commit(sql)
		return True
	
	def delete_table(self, table, schema=None):
		""" delete table from the database """
		table_name = self._table_name(schema, table)
		sql = "DROP TABLE %s" % table_name
		self._exec_sql_and_commit(sql)
		
	def empty_table(self, table, schema=None):
		""" delete all rows from table """
		table_name = self._table_name(schema, table)
		sql = "DELETE FROM %s" % table_name
		self._exec_sql_and_commit(sql)
		
	def rename_table(self, table, new_table, schema=None):
		""" rename a table in database """
		table_name = self._table_name(schema, table)
		sql = "ALTER TABLE %s RENAME TO %s" % (table_name, new_table)
		self._exec_sql_and_commit(sql)
		
	def create_view(self, name, query, schema=None):
		view_name = self._table_name(schema, name)
		sql = "CREATE VIEW %s AS %s" % (view_name, query)
		self._exec_sql_and_commit(sql)
	
	def delete_view(self, name, schema=None):
		view_name = self._table_name(schema, name)
		sql = "DROP VIEW %s" % view_name
		self._exec_sql_and_commit(sql)
	
	def rename_view(self, name, new_name, schema=None):
		""" rename view in database """
		self.rename_table(name, new_name, schema)
		
	def create_schema(self, schema):
		""" create a new empty schema in database """
		sql = "CREATE SCHEMA %s" % schema
		self._exec_sql_and_commit(sql)
		
	def delete_schema(self, schema):
		""" drop (empty) schema from database """
		sql = "DROP SCHEMA %s" % schema
		self._exec_sql_and_commit(sql)
		
	def rename_schema(self, schema, new_schema):
		""" rename a schema in database """
		sql = "ALTER SCHEMA %s RENAME TO %s" % (schema, new_schema)
		self._exec_sql_and_commit(sql)
		
	def table_add_column(self, table, field, schema=None):
		""" add a column to table (passed as TableField instance) """
		table_name = self._table_name(schema, table)
		sql = "ALTER TABLE %s ADD %s" % (table_name, field.field_def())
		self._exec_sql_and_commit(sql)
		
	def table_delete_column(self, table, field, schema=None):
		""" delete column from a table """
		table_name = self._table_name(schema, table)
		sql = "ALTER TABLE %s DROP %s" % (table_name, field)
		self._exec_sql_and_commit(sql)
		
	def table_column_rename(self, table, name, new_name, schema=None):
		""" rename column in a table """
		table_name = self._table_name(schema, table)
		sql = "ALTER TABLE %s RENAME %s TO %s" % (table_name, name, new_name)
		self._exec_sql_and_commit(sql)
		
	def table_column_set_type(self, table, column, data_type, schema=None):
		""" change column type """
		table_name = self._table_name(schema, table)
		sql = "ALTER TABLE %s ALTER %s TYPE %s" % (table_name, column, data_type)
		self._exec_sql_and_commit(sql)
		
	def table_column_set_default(self, table, column, default, schema=None):
		""" change column's default value. If default=None drop default value """
		table_name = self._table_name(schema, table)
		if default:
			sql = "ALTER TABLE %s ALTER %s SET DEFAULT %s" % (table_name, column, default)
		else:
			sql = "ALTER TABLE %s ALTER %s DROP DEFAULT" % (table_name, column)
		self._exec_sql_and_commit(sql)
		
	def table_column_set_null(self, table, column, is_null, schema=None):
		""" change whether column can contain null values """
		table_name = self._table_name(schema, table)
		sql = "ALTER TABLE %s ALTER %s " % (table_name, column)
		if is_null:
			sql += "DROP NOT NULL"
		else:
			sql += "SET NOT NULL"
		self._exec_sql_and_commit(sql)
	
	def create_spatial_index(self, table, schema=None, geom_column='the_geom'):
		table_name = self._table_name(schema, table)
		sql = "CREATE INDEX sidx_%s ON %s USING GIST(%s GIST_GEOMETRY_OPS)" % (table, table_name, geom_column)
		self._exec_sql_and_commit(sql)
		
		
	def get_database_privileges(self):
		""" db privileges: (can create schemas, can create temp. tables) """
		sql = "SELECT has_database_privilege('%s', 'CREATE'), has_database_privilege('%s', 'TEMP')" % (self.dbname, self.dbname)
		c = self.con.cursor()
		self._exec_sql(c, sql)
		return c.fetchone()
		
	def get_schema_privileges(self, schema):
		""" schema privileges: (can create new objects, can access objects in schema) """
		sql = "SELECT has_schema_privilege('%s', 'CREATE'), has_schema_privilege('%s', 'USAGE')" % (schema, schema)
		c = self.con.cursor()
		self._exec_sql(c, sql)
		return c.fetchone()
	
	def get_table_privileges(self, table, schema=None):
		""" table privileges: (select, insert, update, delete) """
		t = self._table_name(schema, table)
		sql = """SELECT has_table_privilege('%s', 'SELECT'), has_table_privilege('%s', 'INSERT'),
		                has_table_privilege('%s', 'UPDATE'), has_table_privilege('%s', 'DELETE')""" % (t,t,t,t)
		c = self.con.cursor()
		self._exec_sql(c, sql)
		return c.fetchone()
		
	def _exec_sql(self, cursor, sql):
		try:
			cursor.execute(sql)
		except psycopg2.Error, e:
			raise DbError(e.message, e.cursor.query)
		
	def _exec_sql_and_commit(self, sql):
		""" tries to execute and commit some action, on error it rolls back the change """
		try:
			c = self.con.cursor()
			self._exec_sql(c, sql)
			self.con.commit()
		except DbError, e:
			self.con.rollback()
			raise
		
	def _table_name(self, schema, table):
		if not schema:
			return table
		else:
			return "%s.%s" % (schema, table)
		

# for debugging / testing
if __name__ == '__main__':

	db = GeoDB(host='localhost',dbname='gis',user='gisak',passwd='g')
	
	print db.list_schemas()
	print '=========='
	
	for row in db.list_geotables():
		print row

	print '=========='
	
	for row in db.get_table_indexes('trencin'):
		print row

	print '=========='
	
	for row in db.get_table_constraints('trencin'):
		print row
	
	print '=========='
	
	print db.get_table_rows('trencin')
	
	#for fld in db.get_table_metadata('trencin'):
	#	print fld
	
	#try:
	#	db.create_table('trrrr', [('id','serial'), ('test','text')])
	#except DbError, e:
	#	print e.message, e.query
	