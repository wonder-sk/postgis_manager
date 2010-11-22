# -*- coding: utf-8 -*-


def name():
	return "PostGIS manager"

def description():
	return "Manage your PostGIS database"

def version():
	return "Version 0.5.12"

def qgisMinimumVersion():
	return "1.0.0"

def classFactory(iface):
	from ManagerPlugin import ManagerPlugin
	return ManagerPlugin(iface)
