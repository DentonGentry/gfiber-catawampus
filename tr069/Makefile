default: all

all: std/parse-schema.stamp

SCHEMA_IN = $(wildcard ../schema/tr-*.xml)
std/parse-schema.stamp: parse-schema.py ${SCHEMA_IN}
	rm -f $@ $@.new
	rm -rf std
	./parse-schema.py ${SCHEMA_IN}
	touch $@
	
parse-validate.stamp: std/parse-schema.stamp
	rm -f $@ $@.new
	for d in $(patsubst std/%.py,%,$(wildcard std/tr*.py)); do \
		echo "import std.$$d"; \
	done >$@.new
	python $@.new
	mv $@.new $@

test: all parse-validate.stamp $(wildcard *_test.py)
	set -e; \
	for d in $(filter %_test.py,$^); do \
		python $$d; \
	done

clean:
	rm -f *~ *.pyc *.stamp
	rm -rf std
