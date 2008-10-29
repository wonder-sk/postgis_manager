
def name():
	return "PostGIS manager"

def description():
	return "Manage your PostGIS tables"

def version():
	return "Version 0.1.1"

def classFactory(iface):
	from ManagerPlugin import ManagerPlugin
	return ManagerPlugin(iface)
