default: all

all:
	@echo "Nothing to build."

# Called from cwmpd test Makefile
test: $(wildcard *_test.py)
	set -e; \
	for d in $(filter %_test.py,$^); do \
		echo; \
		echo "Testing $$d"; \
		python $$d; \
	done
