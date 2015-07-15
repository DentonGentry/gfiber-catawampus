default: all

# Note: super-init-not-called really should be enabled, but we had to
# disable it for now due to gpylint bug b/18440404.  Re-enable the warning
# if that bug gets fixed.
GPYLINT=$(shell \
    if which gpylint >/dev/null; then \
      echo gpylint \
          --disable=g-bad-import-order \
          --disable=g-unknown-interpreter \
          --disable=super-init-not-called \
          --disable=g-tzinfo-datetime; \
    else \
      echo 'echo "(gpylint-missing)" >&2'; \
    fi \
)
PYTHONPATH:=$(shell /bin/pwd):$(PYTHONPATH)

all: tr/all

SUBTESTS= \
    tr/test \
    dm/test \
    diagui/test \
    platform/fakecpe/test \
    platform/gfmedia/test \
    platform/gfonu/test \
    platform/tomato/test
$(SUBTESTS): all

# Use a submake here, only because otherwise GNU make (3.81) will not print
# an error about 'test' itself failing if one of the two sub-targets fails.
# Without such output, 'lint' could fail long before test_only fails, and
# the test_only output could scroll off the top of the screen, leaving the
# misleading impression that everything tested successfully.
test:
	$(MAKE) test_only lint

# Use this to skip the boring lint phase until you're almost done coding
test_only: all $(SUBTESTS)
	tr/vendor/wvtest/wvtestrun $(MAKE) runtests

runtests: all *_test.py
	set -e; \
	for d in $(filter %_test.py,$^); do \
		echo; \
		echo "Testing $$d"; \
		python $$d; \
	done

clean: tr/clean
	rm -f *~ .*~ *.pyc
	find . -name '*.pyc' -o -name '*~' | xargs rm -f


LINT_DIRS=$(shell \
	find . -name vendor -prune -o -name '*.py' -size +1c -printf '%h\n' | \
	sort -u \
)
LINT_TASKS?=12

# For maximum parallelism, we could just have a rule that depends on %.lint
# for all interesting files.  But gpylint takes a long time to start up, so
# let's try to batch several files together into each instance to minimize
# the runtime.  For added fun, gpylint has bugs if you specify files from
# more than one directory at once, so break it out by directory.
lint: \
    cwmp.lint \
    cwmpd.lint \
    $(patsubst %,%.dirlint,$(LINT_DIRS))

%.dirlint: all
	@find $* -maxdepth 1 -size +1c -name '*.py' -type f \
		-not -name google3.py | \
	sort | \
	xargs -P$(LINT_TASKS) -n25 --verbose $(GPYLINT)

%.lint: all
	@$(GPYLINT) $*


DSTDIR?=/tmp/catawampus/
INSTALL=install
PYTHON?=python

install: diagui/install tr/vendor/i2c/install
	$(INSTALL) -d $(DSTDIR) $(DSTDIR)/tr  $(DSTDIR)/tr/vendor \
		$(DSTDIR)/tr/vendor/bup/lib/bup $(DSTDIR)/tr/vendor/pynetlinux \
		$(DSTDIR)/tr/vendor/tornado $(DSTDIR)/tr/vendor/tornado/tornado \
		$(DSTDIR)/tr/vendor/tornado/tornado/platform \
                $(DSTDIR)/tr/vendor/i2c \
		$(DSTDIR)/tr/vendor/pbkdf2 $(DSTDIR)/tr/vendor/curtain \
		$(DSTDIR)/platform $(DSTDIR)/platform/gfmedia $(DSTDIR)/platform/gfonu \
		$(DSTDIR)/platform/fakecpe $(DSTDIR)/dm
	$(INSTALL) -D -m 0755 cwmp cwmpd $(DSTDIR)
	$(INSTALL) -D -m 0755 extras/set-acs $(DSTBINDIR)
	$(INSTALL) -D -m 0644 *.py $(DSTDIR)
	$(INSTALL) -D -m 0644 tr/*.py $(DSTDIR)/tr
	$(INSTALL) -D -m 0644 dm/*.py $(DSTDIR)/dm
	$(INSTALL) -D -m 0644 platform/*.py $(DSTDIR)/platform
	$(INSTALL) -D -m 0644 platform/gfmedia/*.py $(DSTDIR)/platform/gfmedia
	$(INSTALL) -D -m 0644 platform/gfonu/*.py $(DSTDIR)/platform/gfonu
	$(INSTALL) -D -m 0644 platform/fakecpe/*.py $(DSTDIR)/platform/fakecpe
	$(INSTALL) -D -m 0644 platform/fakecpe/version $(DSTDIR)/platform/fakecpe
	$(INSTALL) -D -m 0644 tr/vendor/README.third_party $(DSTDIR)/tr/vendor
	$(INSTALL) -m 0644 tr/vendor/bup/lib/bup/__init__.py $(DSTDIR)/tr/vendor/bup/lib/bup
	$(INSTALL) -m 0644 tr/vendor/bup/lib/bup/options.py $(DSTDIR)/tr/vendor/bup/lib/bup
	$(INSTALL) -m 0644 tr/vendor/bup/lib/bup/shquote.py $(DSTDIR)/tr/vendor/bup/lib/bup
	$(INSTALL) -D -m 0644 tr/vendor/curtain/* $(DSTDIR)/tr/vendor/curtain
	$(INSTALL) -D -m 0644 tr/vendor/pynetlinux/*.py $(DSTDIR)/tr/vendor/pynetlinux
	$(INSTALL) -D -m 0644 tr/vendor/pynetlinux/LICENSE.txt $(DSTDIR)/tr/vendor/pynetlinux
	$(INSTALL) -D -m 0644 tr/vendor/pynetlinux/README* $(DSTDIR)/tr/vendor/pynetlinux
	$(INSTALL) -D -m 0644 tr/vendor/tornado/README $(DSTDIR)/tr/vendor/tornado
	$(INSTALL) -D -m 0644 tr/vendor/tornado/tornado/*.py $(DSTDIR)/tr/vendor/tornado/tornado
	$(INSTALL) -D -m 0644 tr/vendor/tornado/tornado/platform/*.py $(DSTDIR)/tr/vendor/tornado/tornado/platform
	$(INSTALL) -D -m 0644 tr/vendor/xmlwitch.py $(DSTDIR)/tr/vendor
	$(INSTALL) -D -m 0644 tr/vendor/pbkdf2/* $(DSTDIR)/tr/vendor/pbkdf2
	$(PYTHON) -mcompileall $(DSTDIR)

# Subdir rules
%/all:; $(MAKE) -C $* all
%/test:; $(MAKE) -C $* test
%/clean:; $(MAKE) -C $* clean
%/install:; $(MAKE) -C $* install
