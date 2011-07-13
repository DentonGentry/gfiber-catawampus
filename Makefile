LOCAL_SRC_FILES:= \
	test_main.cc \
	rand_b64url.cc \
	rand_b64url_test.cc \
	cwmp_1_2_test.cc

all: test_main

CC = gcc
CPP = g++
LD = g++

# Directory where object files should be placed
OUTDIR ?= .

$(OUTDIR)/%.o: %.cc
	$(CPP) $(DEFINES) -I${OUTDIR} -c -o $@ $<

$(OUTDIR)/%.o: %.cxx
	$(CPP) $(DEFINES) -I${OUTDIR} -c -o $@ $<

OBJFILES = $(LOCAL_SRC_FILES:%.cc=%.o)

DEFINES := -g
LIBRARIES := -lxerces-c
TEST_LIBRARIES := -lgtest

XML_SCHEMAS := cwmp-1-2 soap-envelope soap-encoding
XSD_XMLFILES = $(XML_SCHEMAS:%=schema/%.xsd)
XSD_SOURCES = $(XML_SCHEMAS:%=$(OUTDIR)/%.cxx)
XSD_OBJFILES = $(XML_SCHEMAS:%=$(OUTDIR)/%.o)

$(XSD_OBJFILES) : $(XSD_SOURCES) soap-envelope.cxx

$(OBJFILES) : soap-envelope.cxx

# Need to install Ubuntu packages:
#    xsdcxx libxerces-c-dev libgtest-dev libexpat-dev
$(XSD_SOURCES) : $(XSD_XMLFILES)
	xsdcxx cxx-tree \
		--generate-serialization \
		--location-regex "%http://schemas.xmlsoap.org/soap/envelope/%soap-envelope.xsd%" \
		--location-regex "%http://schemas.xmlsoap.org/soap/encoding/%soap-encoding.xsd%" \
		--namespace-map urn:dslforum-org:cwmp-1-0=cwmp::cwmp_1_0 \
		--namespace-map urn:dslforum-org:cwmp-1-1=cwmp::cwmp_1_1 \
		--namespace-map urn:dslforum-org:cwmp-1-2=cwmp::cwmp_1_2 \
		--namespace-map urn:broadband-forum-org:cwmp:datamodel-1-0=cwmp::dm_1_0 \
		--namespace-map urn:broadband-forum-org:cwmp:datamodel-1-1=cwmp::dm_1_1 \
		--namespace-map urn:broadband-forum-org:cwmp:datamodel-1-2=cwmp::dm_1_2 \
		--namespace-map urn:broadband-forum-org:cwmp:datamodel-1-3=cwmp::dm_1_3 \
		--namespace-map urn:broadband-forum-org:cwmp:datamodel-report-0-1=cwmp::dm_r_0_1 \
		--namespace-map urn:broadband-forum-org:cwmp:devicetype-1-0=cwmp::dt_1_0 \
		--namespace-map urn:broadband-forum-org:cwmp:devicetype-1-1=cwmp::dt_1_1 \
		--namespace-map urn:broadband-forum-org:cwmp:devicetype-features=cwmp::dt_f \
		$^

test_main: $(OBJFILES) $(XSD_OBJFILES)
	$(LD) -o $(OUTDIR)/$@ $(DEFINES) \
		$(OBJFILES) $(XSD_OBJFILES) \
		$(LIBRARIES) ${TEST_LIBRARIES}

clean:
	rm -f $(OUTDIR)/*.o $(OUTDIR)/test_main *~ .*~ \
		cwmp-1-2.[ch]xx soap-encoding.[ch]xx soap-envelope.[ch]xx
