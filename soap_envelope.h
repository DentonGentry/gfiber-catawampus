// Copyright 2011 Google Inc. All Rights Reserved.
// Author: dgentry@google.com (Denton Gentry)

#include <libxml/parser.h>
#include <libxml/tree.h>

#ifndef SOAP_ENVELOPE_H_
#define SOAP_ENVELOPE_H_

typedef struct tr69_message_s {
  int tr69_version_;
} tr69_message_t;

extern void init_tr69_message(tr69_message_t* msg);

#endif  // SOAP_ENVELOPE_H_
