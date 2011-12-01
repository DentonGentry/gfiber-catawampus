default: all

all: tr/all

test: all tr/test *_test.py
	set -e; \
	for d in $(filter %_test.py,$^); do \
		python $$d; \
	done

clean: tr/clean
	rm -f *~ .*~ *.pyc

lint: all
	set -e; \
	for dir in . tr; do \
		( \
			cd $$dir; \
			files=$$(ls *.py | \
				 egrep -v xmlwitch.py); \
			gpylint $$files; \
		); \
	done

DSTDIR?=/tmp/catawampus/
INSTALL=install

install:
	$(INSTALL) -d $(DSTDIR) $(DSTDIR)/tr  $(DSTDIR)/tr/vendor \
		$(DSTDIR)/tr/vendor/bup/lib/bup $(DSTDIR)/tr/vendor/pynetlinux \
		$(DSTDIR)/tr/vendor/tornado $(DSTDIR)/tr/vendor/tornado/tornado
	$(INSTALL) -D -m 0644 *.py $(DSTDIR)
	ln -s tr/vendor/pynetlinux $(DSTDIR)/pynetlinux
	$(INSTALL) -D -m 0644 tr/*.py $(DSTDIR)/tr
	ln -s vendor/bup/lib/bup $(DSTDIR)/tr/bup
	ln -s vendor/tornado/tornado $(DSTDIR)/tr/tornado
	$(INSTALL) -D -m 0644 tr/vendor/README.third_party $(DSTDIR)/tr/vendor
	$(INSTALL) -m 0644 tr/vendor/bup/lib/bup/__init__.py $(DSTDIR)/tr/vendor/bup/lib/bup
	$(INSTALL) -m 0644 tr/vendor/bup/lib/bup/options.py $(DSTDIR)/tr/vendor/bup/lib/bup
	$(INSTALL) -m 0644 tr/vendor/bup/lib/bup/shquote.py $(DSTDIR)/tr/vendor/bup/lib/bup
	$(INSTALL) -D -m 0644 tr/vendor/pynetlinux/*.py $(DSTDIR)/tr/vendor/pynetlinux
	$(INSTALL) -D -m 0644 tr/vendor/pynetlinux/LICENSE.txt $(DSTDIR)/tr/vendor/pynetlinux
	$(INSTALL) -D -m 0644 tr/vendor/pynetlinux/README* $(DSTDIR)/tr/vendor/pynetlinux
	$(INSTALL) -D -m 0644 tr/vendor/tornado/README $(DSTDIR)/tr/vendor/tornado
	$(INSTALL) -D -m 0644 tr/vendor/tornado/tornado/*.py $(DSTDIR)/tr/vendor/tornado/tornado
	$(INSTALL) -D -m 0644 tr/vendor/tornado/tornado/*.crt $(DSTDIR)/tr/vendor/tornado/tornado

# Subdir rules
%/all:; $(MAKE) -C $* all
%/test:; $(MAKE) -C $* test
%/clean:; $(MAKE) -C $* clean
