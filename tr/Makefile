default: all

all: stamp.parsed

SCHEMA_IN = \
    $(wildcard schema/tr-*.xml) \
    $(wildcard schema/x-*.xml) \
    $(wildcard ../platform/*/schema/x-*.xml) \
    $(wildcard $(CWMPD_EXT_DIR)/x-*.xml) \
    $(wildcard $(CWMPD_EXT_DIR)/*/x-*.xml)
stamp.parsed: parse-schema.py ${SCHEMA_IN}
	@echo "CWMPD_EXT_DIR is '$(CWMPD_EXT_DIR)'"
	rm -f $@ $@.new tr???_*.py* ../platform/*/schema/x_*.py*
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

runtests: all stamp.validated \
    core_test.py \
    api_test.py \
    api_soap_test.py \
    http_test.py \
    $(wildcard *_test.py)
	set -e; \
	for d in $(filter %_test.py,$^); do \
		echo; \
		echo "Testing $$d"; \
		python $$d; \
	done

test:
	vendor/wvtest/wvtestrun $(MAKE) runtests

clean:
	rm -f *~ .*~ *.pyc *.stamp tr???_*.py* x_*.py* stamp.* *.tmp
	rm -rf std
