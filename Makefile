LOCAL_SRC_FILES:= \
	test_main.cc \
	soap_envelope.cc \
	soap_envelope_test.cc

all: test_main

CC = gcc
CPP = g++
LD = g++

# Directory where object files should be placed
TARGET_OUT ?= .

$(TARGET_OUT)/%.o: %.cc
	$(CPP) $(DEFINES) -I${TARGET_OUT} -c -o $@ $<

OBJFILES = $(LOCAL_SRC_FILES:%.cc=%.o)

DEFINES := -g -I/usr/include/libxml2
LIBRARIES := -lxml2
TEST_LIBRARIES := -lgtest

test_main: $(OBJFILES)
	$(LD) -o $(TARGET_OUT)/$@ $(DEFINES) $(OBJFILES) $(LIBRARIES) ${TEST_LIBRARIES}

clean:
	rm -f $(TARGET_OUT)/*.o $(TARGET_OUT)/test_main
