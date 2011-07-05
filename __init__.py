# -*- coding: utf-8 -*-


def name():
	return "PostGIS manager"

def description():
	return "Manage your PostGIS database"

def version():
	return "Version 0.5.15"

def icon():
	return "icons/postgis_elephant.png"

def qgisMinimumVersion():
	return "1.0.0"

def classFactory(iface):
	from ManagerPlugin import ManagerPlugin
	return ManagerPlugin(iface)
