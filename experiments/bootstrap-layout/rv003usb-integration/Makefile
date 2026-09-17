ifndef RV003USB_DIR
$(error RV003USB_DIR must point to an rv003usb checkout)
endif
ifndef CH32FUN
$(error CH32FUN must point to the ch32fun source directory)
endif
TARGET_MCU := CH32V003
TARGET ?= bootstrap_rv003usb

ADDITIONAL_C_FILES += $(RV003USB_DIR)/rv003usb/rv003usb.S
ADDITIONAL_C_FILES += $(RV003USB_DIR)/rv003usb/rv003usb.c
EXTRA_CFLAGS += -I$(RV003USB_DIR)/lib -I$(RV003USB_DIR)/rv003usb
EXTRA_CFLAGS += -I../src $(LAYOUT_DEFINE)
ADDITIONAL_C_FILES += ../src/hid_feature_lifecycle.c

ifeq ($(LAYOUT_DEFINE),-DOEP_BOOTSTRAP_LAYOUT_B)
ADDITIONAL_C_FILES += ../src/bootstrap_candidate_b.c
ADDITIONAL_C_FILES += ../src/bootstrap_candidate_b_core.c
else ifeq ($(LAYOUT_DEFINE),-DOEP_BOOTSTRAP_LAYOUT_C)
ADDITIONAL_C_FILES += ../src/bootstrap_candidate_c.c
endif

.PHONY: compare
compare:
	$(MAKE) cv_clean TARGET=bootstrap_rv003usb
	$(MAKE) build TARGET=bootstrap_rv003usb \
		LAYOUT_DEFINE=-DOEP_BOOTSTRAP_LAYOUT_B
	cp bootstrap_rv003usb.elf build-layout-b.elf
	$(MAKE) cv_clean TARGET=bootstrap_rv003usb
	$(MAKE) build TARGET=bootstrap_rv003usb \
		LAYOUT_DEFINE=-DOEP_BOOTSTRAP_LAYOUT_C
	cp bootstrap_rv003usb.elf build-layout-c.elf
	$(PREFIX)-size -A build-layout-b.elf
	$(PREFIX)-size -A build-layout-c.elf

include $(CH32FUN)/ch32fun.mk
