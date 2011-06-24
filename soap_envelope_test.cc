#include <gtest/gtest.h>
#include <libxml/parser.h>
#include <libxml/tree.h>

#include "soap_envelope.h"

const char XML_SOAP_Envelope[] =
  "<soap-env:Envelope"
  "    xmlns:soap-enc=\"http://schemas.xmlsoap.org/soap/encoding/\""
  "    xmlns:soap-env=\"http://schemas.xmlsoap.org/soap/envelope/\""
  "    xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\""
  "    xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\""
  "    xmlns:cwmp=\"urn:dslforum-org:cwmp-1-0\">"
  "  <soap-env:Header>"
  "    <cwmp:ID soap-env:mustUnderstand=\"1\">0</cwmp:ID>"
  "  </soap-env:Header>"
  "  <soap-env:Body>"
  "    <cwmp:GetParameterNames>"
  "      <ParameterPath>Object.</ParameterPath>"
  "      <NextLevel>0</NextLevel>"
  "    </cwmp:GetParameterNames>"
  "  </soap-env:Body>"
  "</soap-env:Envelope>";

TEST(ExtractTgzTest, TestExtract) {
  tr69_message_t msg;
  init_tr69_message(&msg);

  int len = sizeof(XML_SOAP_Envelope) - 1;  // exclude trailing NUL
  xmlDocPtr doc = xmlReadMemory(XML_SOAP_Envelope, len, "test.xml", NULL, 0);

  xmlFreeDoc(doc);
  xmlCleanupParser();
  xmlMemoryDump();
}
