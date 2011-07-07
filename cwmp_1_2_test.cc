#include <gtest/gtest.h>
#include <sstream>
#include "cwmp-1-2.hxx"

class Cwmp_1_2_Test : public ::testing::Test {
 public:
  Cwmp_1_2_Test() {}
  virtual ~Cwmp_1_2_Test() {}
};

TEST_F(Cwmp_1_2_Test, GenerateInform) {
  const cwmp::cwmp_1_2::Manufacturer manufacturer("manufacturer_string");
  const cwmp::cwmp_1_2::OUI oui("oui_string");
  const cwmp::cwmp_1_2::ProductClass product_class("product_class_string");
  const cwmp::cwmp_1_2::SerialNumber serial_number("serial_number_string");

  const cwmp::cwmp_1_2::DeviceIdStruct device_id(
      manufacturer, oui, product_class, serial_number);

  const cwmp::cwmp_1_2::EventList event_list;

  const xml_schema::unsigned_int envelopes = 200;

  // 12:30:01.02 on June 4, 1970.
  const cwmp::cwmp_1_2::Inform::CurrentTime_type date_time(
      1970, 6, 4, 12, 30, 1.02);

  const xml_schema::unsigned_int retry_count = 201;

  const cwmp::cwmp_1_2::Inform::ParameterList_type parameter_list;

  cwmp::cwmp_1_2::Inform inform(device_id, event_list, envelopes, date_time,
                                retry_count, parameter_list);

  std::stringstream sstream;
  ::xml_schema::namespace_infomap m;
  cwmp::cwmp_1_2::Inform_(sstream, inform, m, "UTF-8",
                          xml_schema::flags::no_xml_declaration);

  const std::string expected_xml(
    "\n"  // http://www.codesynthesis.com/pipermail/xsd-users/2009-December/002625.html
    "<p1:Inform xmlns:p1=\"urn:dslforum-org:cwmp-1-2\">\n"
    "\n"
    "  <DeviceId>\n"
    "    <Manufacturer>manufacturer_string</Manufacturer>\n"
    "    <OUI>oui_string</OUI>\n"
    "    <ProductClass>product_class_string</ProductClass>\n"
    "    <SerialNumber>serial_number_string</SerialNumber>\n"
    "  </DeviceId>\n"
    "\n"
    "  <Event/>\n"
    "\n"
    "  <MaxEnvelopes>200</MaxEnvelopes>\n"
    "\n"
    "  <CurrentTime>1970-06-04T12:30:01.02</CurrentTime>\n"
    "\n"
    "  <RetryCount>201</RetryCount>\n"
    "\n"
    "  <ParameterList/>\n"
    "\n"
    "</p1:Inform>\n");
  EXPECT_EQ(sstream.str(), expected_xml);
}
