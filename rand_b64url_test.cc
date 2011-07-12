#include <ctype.h>
#include <gtest/gtest.h>

#include "rand_b64url.h"

class RandB64Test : public ::testing::Test {
 public:
  RandB64Test() {}
  virtual ~RandB64Test() {}

  // Return true if the string contains only valid characters for Base64URL
  // http://en.wikipedia.org/wiki/Base64#URL_applications
  bool IsValidB64Url(const std::string& str) {
    int len = str.length();
    for (int i = 0; i < len; ++i) {
      const int c = str[i];
      if (!(isalnum(c) || (c == '-') || (c == '_'))) {
        return false;
      }
    }
    return true;
  }
};

TEST_F(RandB64Test, TestUrlString) {
  // seeding the RNG with a different value each run is a mixed blessing.
  // If there _is_ a failure, re-running the test might pass.
  unsigned int seed = time(NULL);
  RandomBase64 rb64(seed);

  for (int i = 0; i < 100; ++i) {
    std::string randstr = rb64.GenerateRandomString(12);
    EXPECT_EQ(randstr.length(), 12) << "Seed value: " << seed;
    EXPECT_TRUE(IsValidB64Url(randstr))  << "Seed value: " << seed;
  }
}
