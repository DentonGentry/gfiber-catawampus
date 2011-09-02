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


# Subdir rules
%/all:; $(MAKE) -C $* all
%/test:; $(MAKE) -C $* test
%/clean:; $(MAKE) -C $* clean

