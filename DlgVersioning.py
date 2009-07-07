
from ui.DlgVersioning_ui import Ui_DlgVersioning

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from DlgDbError import DlgDbError

import postgis_utils


class DlgVersioning(QDialog, Ui_DlgVersioning):

	def __init__(self, parent=None, db=None):
		QDialog.__init__(self, parent)
		
		self.db = db
		
		self.setupUi(self)

		self.connect(self.buttonBox, SIGNAL("accepted()"), self.onOK)
		self.connect(self.buttonBox, SIGNAL("helpRequested()"), self.showHelp)
		
		self.populateSchemas()
		self.populateTables()

		self.connect(self.cboSchema, SIGNAL("currentIndexChanged(int)"), self.populateTables)

		# updates of SQL window
		self.connect(self.cboSchema, SIGNAL("currentIndexChanged(int)"), self.updateSql)
		self.connect(self.cboTable, SIGNAL("currentIndexChanged(int)"), self.updateSql)
		self.connect(self.chkCreateCurrent, SIGNAL("stateChanged(int)"), self.updateSql)
		self.connect(self.editPkey, SIGNAL("textChanged(const QString &)"), self.updateSql)
		self.connect(self.editStart, SIGNAL("textChanged(const QString &)"), self.updateSql)
		self.connect(self.editEnd, SIGNAL("textChanged(const QString &)"), self.updateSql)

		self.updateSql()
		
	def updateSql(self):

		self.schema = unicode(self.cboSchema.currentText())
		self.table = unicode(self.cboTable.currentText())
		self.schtable = self.db._table_name(self.schema, self.table) # schema-qualified table

		self.current = self.chkCreateCurrent.isChecked()

		self.colPkey = unicode(self.editPkey.text())
		self.colStart = unicode(self.editStart.text())
		self.colEnd = unicode(self.editEnd.text())

		origPkey = None
		for constr in self.db.get_table_constraints(self.table, self.schema):
			if constr.con_type == postgis_utils.TableConstraint.TypePrimaryKey:
				origPkey = constr.keys
				self.origPkeyName = constr.name
				break
				
		if origPkey is None:
			self.txtSql.setPlainText("Table doesn't have a primary key!")
			self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
			return
		elif len(origPkey) != 1:
			self.txtSql.setPlainText("Table has multicolumn primary key!")
			self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
			return
		
		fields = self.db.get_table_fields(self.table, self.schema)
		self.columns = map(lambda x: x.name, fields)
		
		# take first (and only column of the pkey), find out its name
		for fld in fields:
			if fld.num == origPkey[0]:
				self.colOrigPkey = fld.name
				break
				
		sql = []
		
		# modify table: add serial column, start time, end time
		sql.append( self.sql_alterTable() )
		# add primary key to the table
		sql.append( self.sql_setPkey() )

		sql.append( self.sql_currentView() )
		# add X_at_time, X_update, X_delete functions
		sql.append( self.sql_functions() )
		# add insert, update trigger, delete rule
		sql.append( self.sql_triggers() )
		# add _current view + updatable
		#if self.current:
		sql.append( self.sql_updatesView() )

		self.txtSql.setPlainText( '\n\n'.join(sql) )
		self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
		
		return sql

	def showHelp(self):
		helpText = """In this dialog you can set up versioning support for a table. The table will be modified so that all changes will be recorded: there will be a column with start time and end time. Every row will have its start time, end time is assigned when the feature gets deleted. When a row is modified, the original data is marked with end time and new row is created. With this system, it's possible to get back to state of the table any time in history. When selecting rows from the table, you will always have to specify at what time do you want the rows."""
		QMessageBox.information(self, "Help", helpText)
		

	def populateSchemas(self):
		
		if not self.db:
			return
		
		schemas = self.db.list_schemas()
		self.cboSchema.clear()
		for schema in schemas:
			self.cboSchema.addItem(schema[1])


	def populateTables(self):
		
		if not self.db:
			return
		
		schema = unicode(self.cboSchema.currentText())
		tables = self.db.list_geotables(schema)
		self.cboTable.clear()
		for table in tables:
			if table[6]: # contains geometry column?
				self.cboTable.addItem(table[0])

	def sql_alterTable(self):
		return "ALTER TABLE %s ADD %s serial, ADD %s timestamp, ADD %s timestamp;" % (self.schtable, self.colPkey, self.colStart, self.colEnd)
		
	def sql_setPkey(self):
		return "ALTER TABLE %s DROP CONSTRAINT %s, ADD PRIMARY KEY (%s);" % (self.schtable, self.origPkeyName, self.colPkey)

	def sql_currentView(self):
		cols = ",".join(self.columns)
		return "CREATE VIEW %(schema)s.%(table)s_current AS SELECT %(cols)s FROM %(schtable)s WHERE %(end)s IS NULL;" % \
			{ 'schema' : self.schema, 'table' : self.table, 'cols' : cols, 'schtable' : self.schtable, 'end' : self.colEnd }


	def sql_functions(self):
		cols = ",".join(self.columns)
		old_cols = ",".join(map(lambda x: "OLD."+x, self.columns))
		sql = """
CREATE OR REPLACE FUNCTION %(schema)s.%(table)s_at_time(timestamp)
RETURNS SETOF %(schema)s.%(table)s_current AS
$$
SELECT %(cols)s FROM %(schtable)s WHERE
  ( SELECT CASE WHEN %(end)s IS NULL THEN (%(start)s <= $1) ELSE (%(start)s <= $1 AND %(end)s > $1) END );
$$
LANGUAGE 'SQL';

CREATE OR REPLACE FUNCTION %(schema)s.%(table)s_update()
RETURNS TRIGGER AS
$$
BEGIN
  IF OLD.%(end)s IS NOT NULL THEN
    RETURN NULL;
  END IF;
  IF NEW.%(end)s IS NULL THEN
    INSERT INTO %(schema)s.%(table)s (%(cols)s, %(start)s, %(end)s) VALUES (%(oldcols)s, OLD.%(start)s, current_timestamp);
    NEW.%(start)s = current_timestamp;
  END IF;
  RETURN NEW;
END;
$$
LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION %(schema)s.%(table)s_insert()
RETURNS trigger AS
$$
BEGIN
  if NEW.%(start)s IS NULL then
    NEW.%(start)s = now();
    NEW.%(end)s = null;
  end if;
  RETURN NEW;
END;
$$
LANGUAGE 'plpgsql';""" % { 'table' : self.table, 'schema' : self.schema, 'schtable': self.schtable, 'cols' : cols, 'oldcols' : old_cols, 'start' : self.colStart, 'end' : self.colEnd }
		return sql
	
	def sql_triggers(self):

		return """
CREATE RULE %(table)s_del AS ON DELETE TO %(schtable)s
DO INSTEAD UPDATE %(schtable)s SET %(end)s = current_timestamp WHERE %(pkey)s = OLD.%(pkey)s AND %(end)s IS NULL;

CREATE TRIGGER %(table)s_update BEFORE UPDATE ON %(schtable)s
FOR EACH ROW EXECUTE PROCEDURE %(schema)s.%(table)s_update();

CREATE TRIGGER %(table)s_insert BEFORE INSERT ON %(schtable)s
FOR EACH ROW EXECUTE PROCEDURE %(schema)s.%(table)s_insert();""" % \
		{ 'table' : self.table, 'schema' : self.schema, 'schtable' : self.schtable, 'pkey' : self.colPkey, 'end' : self.colEnd }

	def sql_updatesView(self):
		cols = ",".join(self.columns)
		new_cols = ",".join(map(lambda x: "NEW."+x, self.columns))
		schview = self.db._table_name(self.schema, self.table + "_current")
		assign_cols = ",".join(map(lambda x: "%s = NEW.%s" % (x,x), self.columns))
		return """
CREATE OR REPLACE RULE "_DELETE" AS ON DELETE TO %(schview)s DO INSTEAD
  DELETE FROM %(schtable)s WHERE %(origpkey)s = old.%(origpkey)s;
CREATE OR REPLACE RULE "_INSERT" AS ON INSERT TO %(schview)s DO INSTEAD
  INSERT INTO %(schtable)s (%(cols)s) VALUES (%(newcols)s);
CREATE OR REPLACE RULE "_UPDATE" AS ON UPDATE TO %(schview)s DO INSTEAD
  UPDATE %(schtable)s SET %(assign)s WHERE %(origpkey)s = new.%(origpkey)s;""" % { 'schview': schview, 'schtable':self.schtable, 'cols':cols, 'newcols':new_cols, 'assign':assign_cols, 'origpkey':self.colOrigPkey }
		

	def onOK(self):

		# execute and commit the code
		try:
			sql = "\n".join(self.updateSql())
			self.db._exec_sql_and_commit( sql )
			
			QMessageBox.information(self, "good!", "everything went fine!")
			self.accept()
			
		except postgis_utils.DbError, e:
			DlgDbError.showError(e, self)
		