"""
PostGIS Manager

Copyright 2008 Martin Dobias
licensed under the terms of GNU GPL v2
"""

import psycopg2


class TableAttribute:
	def __init__(self, row):
		self.num, self.name, self.data_type, self.char_max_len, self.modifier, self.notnull, self.hasdefault = row

class DbError(Exception):
	def __init__(self, message, query=None):
		self.message = message
		self.query = query

class TableField:
	def __init__(self, name, data_type, is_null=None, default=None):
		self.name, self.data_type, self.is_null, self.default = name, data_type, is_null, default
		
	def is_null_txt(self):
		if self.is_null:
			return "NULL"
		else:
			return "NOT NULL"

class GeoDB:
	
	def __init__(self, host=None, port=None, dbname=None, user=None, passwd=None):
		con_str = ''
		if host:   con_str += "host='%s' " % host
		if port:   con_str += "port=%d " % port
		if dbname: con_str += "dbname='%s' " % dbname
		if user:   con_str += "user='%s' " % user
		if passwd: con_str += "password='%s' " % passwd
		
		self.con = psycopg2.connect(con_str)
		
		self.host = host
		self.port = port
		self.dbname = dbname
		self.user = user
		self.passwd = passwd
	
	def list_schemas(self):
		c = self.con.cursor()
		sql = "SELECT * FROM pg_namespace"
		self._exec_sql(c, sql)
		
		schemas = []
		
		row = c.fetchone()
		while row:
			schema = row[0]
			if schema[0:3] != 'pg_' and schema != 'information_schema':
				schemas.append(row)
			row = c.fetchone()
			
		return schemas
			
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
		# TODO: list empty schemas!
		
		# LEFT OUTER JOIN: zmena oproti LEFT JOIN ze ak moze spojit viackrat tak to urobi
		sql = "SELECT relname, nspname, relkind, geometry_columns.f_geometry_column, geometry_columns.type FROM pg_class " \
		      "  JOIN pg_namespace ON relnamespace=pg_namespace.oid " \
		      "  LEFT OUTER JOIN geometry_columns ON relname=f_table_name AND nspname=f_table_schema " \
		      "WHERE (relkind = 'r' or relkind='v') " + schema_where + \
		      "ORDER BY nspname, relname"
		self._exec_sql(c, sql)
		return c.fetchall()
			
	def get_table_metadata(self, table, schema='public'):
		"""
			get as much metadata as possible about the table:
			- fields and their types
			- row count
			- indices (spatial + classical)
			
			more (constraints, triggers, functions):
			http://www.alberton.info/postgresql_meta_info.html
		"""
		pass
		
	def get_table_fields(self, table, schema='public'):
		c = self.con.cursor()
		sql = """SELECT a.attnum AS ordinal_position,
				a.attname AS column_name,
				t.typname AS data_type,
				a.attlen AS char_max_len,
				a.atttypmod AS modifier,
				a.attnotnull AS notnull,
				a.atthasdef AS hasdefault
			FROM pg_class c, pg_attribute a, pg_type t
			WHERE c.relname = '%s' AND
				a.attnum > 0 AND
				a.attrelid = c.oid AND
				a.atttypid = t.oid
			ORDER BY a.attnum""" % table

		self._exec_sql(c, sql)
		attrs = []
		for row in c.fetchall():
			attrs.append(TableAttribute(row))
		return attrs
		
	"""
	def list_tables(self):
		c = self.con.cursor()
		c.execute("SELECT relname FROM pg_class WHERE relname !~ '^(pg_|sql_)' AND relkind = 'r'")
		return c.fetchall()
	"""
		
	def add_geometry_column(self, table, geom_type, schema='public', geom_column='the_geom', srid=-1, dim=2):
		c = self.con.cursor()
		
		sql = "SELECT AddGeometryColumn('%s', '%s', '%s', %d, '%s', %d)" % (schema, table, geom_column, srid, geom_type, dim)
		self._exec_sql(c, sql)
		self.con.commit()
		
	def create_table(self, table, fields, schema='public'):
		""" create ordinary table
				'fields' is array containing instances of TableField """
		# TODO: primary key?
				
		if len(fields) == 0:
			return False
		
		c = self.con.cursor()
		sql = "CREATE TABLE %s (%s %s %s" % (table, fields[0].name, fields[0].data_type, fields[0].is_null_txt())
		for field in fields[1:]:
			sql += ", %s %s %s" % (field.name, field.data_type, field.is_null_txt())
		sql += ")"
		self._exec_sql(c, sql)
		self.con.commit()
		return True
	
	def delete_table(self, table, schema='public'):
		""" delete table from the database """
		c = self.con.cursor()
		sql = "DROP TABLE %s" % table
		self._exec_sql(c, sql)
		self.con.commit()
		
	def rename_table(self, table, new_table, schema='public'):
		""" rename a table in database """
		sql = "ALTER TABLE %s.%s RENAME TO %s" % (schema, table, new_table)
		c = self.con.cursor()
		self._exec_sql(c, sql)
		self.con.commit()
		
	def create_schema(self, schema):
		""" create a new empty schema in database """
		sql = "CREATE SCHEMA %s" % schema
		c = self.con.cursor()
		self._exec_sql(c, sql)
		self.con.commit()
		
	def delete_schema(self, schema):
		""" drop (empty) schema from database """
		sql = "DROP SCHEMA %s" % schema
		c = self.con.cursor()
		self._exec_sql(c, sql)
		self.con.commit()
		
	def rename_schema(self, schema, new_schema):
		""" rename a schema in database """
		sql = "ALTER SCHEMA %s RENAME TO %s" % (schema, new_schema)
		c = self.con.cursor()
		self._exec_sql(c, sql)
		self.con.commit()
	
	def create_spatial_index(self, table, schema='public', geom_column='the_geom'):
		c = self.con.cursor()
		sql = "CREATE INDEX sidx_%s ON %s USING GIST(%s GIST_GEOMETRY_OPS)" % (table, table, geom_column)
		self._exec_sql(c, sql)
		self.con.commit()
		
	def _exec_sql(self, cursor, sql):
		try:
			cursor.execute(sql)
		except psycopg2.Error, e:
			raise DbError(e.message, e.cursor.query)
		

# for debugging / testing
if __name__ == '__main__':

	db = GeoDB(host='localhost',dbname='gis',user='gisak',passwd='g')
	
	print db.list_schemas()
	print '=========='
	
	for row in db.list_geotables():
		print row

	print '=========='

	#for fld in db.get_table_metadata('trencin'):
	#	print fld
	
	try:
		db.create_table('trrrr', [('id','serial'), ('test','text')])
	except DbError, e:
		print e.message, e.query
	