// Copyright 2011 Google Inc. All Rights Reserved.
// Author: dgentry@google.com (Denny Gentry)

#ifndef RAND_B64URL_H_
#define RAND_B64URL_H_

#include <string>

class RandomBase64 {
 public:
  explicit RandomBase64(unsigned int seed) : seed_(seed) {}
  virtual ~RandomBase64() {}

  virtual std::string GenerateRandomString(int length);

 private:
  static const int kNumBase64Chars = 64;
  static const char base64url_chars_[kNumBase64Chars + 1];

  unsigned int seed_;
};

#endif  // RAND_B64URL_H_
