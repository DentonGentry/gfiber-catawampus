default: all

all:

DSTDIR?=/tmp/catawampus/
PYTHON?=python
INSTALL?=install

install:
	$(INSTALL) -d $(DSTDIR) $(DSTDIR)/diagui $(DSTDIR)/diagui/static  $(DSTDIR)/diagui/Testdata $(DSTDIR)/diagui/techui_static $(DSTDIR)/diagui/license_static
	$(INSTALL) -D -m 0644 *.html $(DSTDIR)/diagui
	$(INSTALL) -D -m 0644 static/*.css static/*.js  static/*.png static/*.ico static/*.ttf $(DSTDIR)/diagui/static
	$(INSTALL) -D -m 0644 techui_static/* $(DSTDIR)/diagui/techui_static
	$(INSTALL) -D -m 0644 license_static/* $(DSTDIR)/diagui/license_static
	$(INSTALL) -D -m 0644 Testdata/testdata $(DSTDIR)/diagui/Testdata
	$(INSTALL) -D -m 0644 *.py $(DSTDIR)/diagui

test: all
	../tr/vendor/wvtest/wvtestrun $(MAKE) runtests

runtests: all $(wildcard *_test.py)
	set -e; \
	for d in $(filter %_test.py,$^); do \
		echo; \
		echo "Testing $$d"; \
		python $$d; \
	done

deviceList_test: techui_static/deviceList_test.js techui_static/deviceList.js techui_static/wvtest.js ../tr/vendor/wvtest/javascript/jsshell
	../tr/vendor/wvtest/javascript/jsshell techui_static/wvtest.js techui_static/deviceList.js techui_static/deviceList_test.js

tech_test: techui_static/tech_test.js techui_static/tech.js techui_static/deviceList.js
	../tr/vendor/wvtest/javascript/jsshell techui_static/wvtest.js techui_static/deviceList.js techui_static/tech.js techui_static/tech_test.js

jstest: ../tr/vendor/wvtest/wvtestrun
	../tr/vendor/wvtest/wvtestrun $(MAKE) jsruntests

jsruntests: deviceList_test tech_test

jslint: techui_static/deviceList.js techui_static/deviceList_test.js techui_static/tech.js techui_static/tech_test.js techui_static/tech_static.js
	gjslint techui_static/deviceList.js techui_static/deviceList_test.js techui_static/tech.js techui_static/tech_test.js techui_static/tech_static.js

clean:
	rm -f *~ *.pyc .*~
