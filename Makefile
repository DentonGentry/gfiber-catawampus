default: all

all: tr/all

test: all tr/test *_test.py
	set -e; \
	for d in $(filter %_test.py,$^); do \
		python $$d; \
	done

clean: tr/clean
	rm -f *~ .*~ *.pyc


# Subdir rules
%/all:; $(MAKE) -C $* all
%/test:; $(MAKE) -C $* test
%/clean:; $(MAKE) -C $* clean

