XSD_FILES = \
	cwmp-1-0.xsd \
	cwmp-1-1.xsd \
	cwmp-1-2.xsd \
	cwmp-datamodel-1-0.xsd \
	cwmp-datamodel-1-1.xsd \
	cwmp-datamodel-1-2.xsd \
	cwmp-datamodel-1-3.xsd \
	cwmp-datamodel-report.xsd \
	cwmp-devicetype-1-0.xsd \
	cwmp-devicetype-1-1.xsd \
	cwmp-devicetype-features.xsd

OBJDIR ?= ./

all:

# Must install Ubuntu package gsoap
gsoaptest:
	wsdl2h -o${OBJDIR}cwmp.h $(XSD_FILES)
	soapcpp2 -d${OBJDIR} -I/usr/include/gsoap/ ${OBJDIR}cwmp.h

# Must install Ubuntu package xsdcxx
xsdtest:
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
		$(XSD_FILES)

gsoapclean:
	rm -f ${OBJDIR}*.o ${OBJDIR}soapC.cpp ${OBJDIR}soapClient.cpp
	rm -f ${OBJDIR}soapClientLib.cpp ${OBJDIR}soapServer.cpp
	rm -f ${OBJDIR}soapServerLib.cpp ${OBJDIR}cwmp.h ${OBJDIR}soapH.h
	rm -f ${OBJDIR}soapStub.h ${OBJDIR}*.nsmap

xsdclean:
	rm -f $(patsubst %.xsd,${OBJDIR}%.cxx,$(XSD_FILES))
	rm -f $(patsubst %.xsd,${OBJDIR}%.hxx,$(XSD_FILES))

clean: gsoapclean xsdclean
