default: all

all: stamp.parsed

SCHEMA_IN = $(wildcard schema/tr-*.xml)
stamp.parsed: parse-schema.py ${SCHEMA_IN}
	rm -f $@ $@.new tr???_*.py*
	rm -rf std
	./parse-schema.py ${SCHEMA_IN}
	touch $@
	
stamp.validated: stamp.parsed *.py
	rm -f $@ $@.new
	( \
		for d in $(patsubst %.py,%,$(wildcard tr???_*.py)); do \
			echo "import $$d"; \
		done; \
	) >$@.new
	python $@.new
	mv $@.new $@

test: all stamp.validated $(wildcard *_test.py)
	set -e; \
	for d in $(filter %_test.py,$^); do \
		python $$d; \
	done

clean:
	rm -f *~ .*~ *.pyc *.stamp tr???_*.py* stamp.*
	rm -rf std
