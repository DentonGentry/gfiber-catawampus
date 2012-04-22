#!/bin/bash

CWMP="./cwmpd --platform=fakecpe"
DELAY=2

$CWMP "$@"
code=$?
DNLD=download.tgz
if [ $code -eq 32 ] && [ -f $DNLD ]; then
  tar xzf $DNLD
  rm $DNLD
  echo "cwmpd exited deliberately.  Respawning in $DELAY seconds." >&2
  sleep $DELAY
  exec ./fakecpe.sh "$@"
fi

exit 1
