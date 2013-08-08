default: all

all:

DSTDIR?=/tmp/catawampus/
PYTHON?=python
INSTALL?=install

install:
	$(INSTALL) -d $(DSTDIR) $(DSTDIR)/diagui $(DSTDIR)/diagui/static  $(DSTDIR)/diagui/Testdata 
	$(INSTALL) -D -m 0755 diaguid $(DSTDIR)/diagui
	$(INSTALL) -D -m 0644 *.html $(DSTDIR)/diagui
	$(INSTALL) -D -m 0644 static/*.css static/*.js  static/*.png $(DSTDIR)/diagui/static
	$(INSTALL) -D -m 0644 Testdata/testdata $(DSTDIR)/diagui/Testdata
	$(INSTALL) -D -m 0644 *.py $(DSTDIR)/diagui

test: all $(wildcard *_test.py)
	set -e; \
	for d in $(filter %_test.py,$^); do \
		echo; \
		echo "Testing $$d"; \
		python $$d; \
	done

clean:
	rm -f *~ *.pyc .*~