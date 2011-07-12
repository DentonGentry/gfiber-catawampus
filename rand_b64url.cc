// Copyright 2011 Google Inc. All Rights Reserved.
// Author: dgentry@google.com (Denny Gentry)

#include <assert.h>
#include <stdint.h>
#include <stdlib.h>

#include <string>

#include "rand_b64url.h"

const char RandomBase64::base64url_chars_[kNumBase64Chars + 1] =
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

std::string RandomBase64::GenerateRandomString(int length) {
  std::string outurl;

  for (int i = 0; i < length; ++i) {
    int r = rand_r(&seed_) & (kNumBase64Chars - 1);
    outurl.append(1, base64url_chars_[r]);
  }

  return outurl;
}
