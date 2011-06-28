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

gsoaptest:
	wsdl2h -o${OBJDIR}cwmp.h $(XSD_FILES)
	soapcpp2 -d${OBJDIR} -I/usr/include/gsoap/ ${OBJDIR}cwmp.h

clean:
	rm -f ${OBJDIR}*.o ${OBJDIR}soapC.cpp ${OBJDIR}soapClient.cpp
	rm -f ${OBJDIR}soapClientLib.cpp ${OBJDIR}soapServer.cpp
	rm -f ${OBJDIR}soapServerLib.cpp ${OBJDIR}cwmp.h ${OBJDIR}soapH.h
	rm -f ${OBJDIR}soapStub.h ${OBJDIR}*.nsmap
