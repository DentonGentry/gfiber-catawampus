default: all

all: parse-schema.stamp

parse-schema.stamp: parse-schema.py $(wildcard ../schema/tr-*.xml)
	rm -f $@ $@.new
	./parse-schema.py $(filter %.xml,$^) >$@.new
	mv $@.new $@
	
test: all $(wildcard *_test.py)
	set -e; \
	for d in $(filter %_test.py,$^); do \
		python $$d; \
	done

clean:
	rm -f *~ *.pyc *.stamp
