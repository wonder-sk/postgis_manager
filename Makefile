
UI_SOURCES=$(wildcard ui/*.ui)
UI_FILES=$(patsubst %.ui,%_ui.py,$(UI_SOURCES))

GEN_FILES = resources.py ${UI_FILES}

all: $(GEN_FILES)


$(UI_FILES): %_ui.py: %.ui
	pyuic4 -o $@ $<
	
resources.py: resources.qrc
	pyrcc4 -o resources.py resources.qrc


clean:
	rm -f $(GEN_FILES) *.pyc

package:
	cd .. && rm -f postgis_manager.zip && zip -r postgis_manager.zip postgis_manager -x \*.svn-base -x \*.pyc -x \*entries\*
