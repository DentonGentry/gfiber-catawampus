default: all

all: parse-schema.stamp

parse-schema.stamp: parse-schema.py $(wildcard ../schema/tr-*.xml)
	rm -f $@ $@.new
	./parse-schema.py $(filter %.xml,$^) >$@.new
	mv $@.new $@

clean:
	rm -f *~ *.pyc *.stamp
