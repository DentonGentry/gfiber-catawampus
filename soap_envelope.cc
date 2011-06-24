#include <expat.h>
#include <stdio.h>
#include <string.h>

#include "soap_envelope.h"

void
init_tr69_message(tr69_message_t* msg) {
  memset(msg, 0, sizeof(*msg));
}
