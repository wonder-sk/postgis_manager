"""
PostGIS Manager

Copyright 2008 Martin Dobias
licensed under the terms of GNU GPL v2
"""

import psycopg2

def connect_db(host, dbname, user, passwd):
	return psycopg2.connect("host='%s' dbname='%s' user='%s' password='%s'" % (host, dbname, user, passwd))

class GeoDB:
	
	def __init__(self, con):
		self.con = con
	
	def list_schemas(self):
		c = self.con.cursor()
		c.execute("SELECT * FROM pg_namespace")
		
		schemas = []
		
		row = c.fetchone()
		while row:
			schema = row[0]
			if schema[0:3] != 'pg_' and schema != 'information_schema':
				schemas.append(row)
			row = c.fetchone()
			
		return schemas
			
	def list_geotables(self):
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
		
		# LEFT OUTER JOIN: zmena oproti LEFT JOIN ze ak moze spojit viackrat tak to urobi

		sql = "SELECT relname, nspname, relkind, geometry_columns.f_geometry_column, geometry_columns.type FROM pg_class " \
		      "  JOIN pg_namespace ON relnamespace=pg_namespace.oid " \
		      "  LEFT OUTER JOIN geometry_columns ON relname=f_table_name AND nspname=f_table_schema " \
		      "WHERE (relkind = 'r' or relkind='v') " \
		      "  AND nspname NOT IN ('information_schema','pg_catalog') " \
		      "ORDER BY nspname, relname"
		c.execute(sql)
		return c.fetchall()
			
	def get_table_metadata(self, table, schema='public'):
		"""
			get as much metadata as possible about the table:
			- fields and their types
			- row count
			- indices (spatial + classical)
			
			how to get field info:
			
			SELECT a.attnum AS ordinal_position,
				a.attname AS column_name,
				t.typname AS data_type,
				a.attlen AS character_maximum_length,
				a.atttypmod AS modifier,
				a.attnotnull AS notnull,
				a.atthasdef AS hasdefault
			FROM pg_class c, pg_attribute a, pg_type t
			WHERE c.relname = 'test2' AND
				a.attnum > 0 AND
				a.attrelid = c.oid AND
				a.atttypid = t.oid
			ORDER BY a.attnum;
			 
			more (constraints, triggers, functions):
			http://www.alberton.info/postgresql_meta_info.html
		"""
		pass
		
	"""
	def list_tables(self):
		c = self.con.cursor()
		c.execute("SELECT relname FROM pg_class WHERE relname !~ '^(pg_|sql_)' AND relkind = 'r'")
		return c.fetchall()
	"""
		
	def add_geometry_column(self, table, geom_type, schema='public', geom_column='the_geom', srid=-1, dim=2):
		c = self.con.cursor()
		
		sql = "SELECT AddGeometryColumn('%s', '%s', '%s', %d, '%s', %d)" % (schema, table, geom_column, srid, geom_type, dim)
		c.execute(sql)
		
	def create_table(self, table, fields, schema='public'):
		""" create ordinary table """
		c = self.con.cursor()
		# TODO: fields
		sql = "CREATE TABLE %s (id int4 primary key)" % table
		c.execute(sql)
	
	def delete_table(self, table, schema='public'):
		""" delete table from the database """
		c = self.con.cursor()
		sql = "DROP TABLE %s" % table
		c.execute(sql)
	
	def create_spatial_index(self, table, schema='public', geom_column='the_geom'):
		c = self.con.cursor()
		sql = "CREATE INDEX sidx_%s ON %s USING GIST(%s GIST_GEOMETRY_OPS)" % (table, table, geom_column)
		c.execute(sql)

# for debugging / testing
if __name__ == '__main__':

	con = connect_db('localhost', 'gis', 'gisak', 'g')
	db = GeoDB(con)
	
	print db.list_schemas()
	print '=========='
	
	for row in db.list_geotables():
		print row

