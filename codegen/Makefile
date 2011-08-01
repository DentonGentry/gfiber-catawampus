all: test_main

# Directory where object files should be placed
OUTDIR ?= .

XML_SCHEMAS := cwmp-1-2
XML_SCHEMAS += cwmp-datamodel-1-3
#XML_SCHEMAS += cwmp-datamodel-report
XML_SCHEMAS += cwmp-devicetype-1-1
#XML_SCHEMAS += cwmp-devicetype-features

XSD_SOURCES = $(XML_SCHEMAS:%=schema/%.xsd)
XSD_PYFILES = $(XML_SCHEMAS:%=$(OUTDIR)/%.py)

$(XSD_PYFILES) : ${OUTDIR}/%.py: ../schema/%.xsd
	generateDS.py --silence --no-questions -o $@ $^

test_main: $(XSD_PYFILES)
	echo Done

clean:
	rm -f ${XSD_PYFILES}
