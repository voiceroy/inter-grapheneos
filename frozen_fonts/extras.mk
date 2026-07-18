LOCAL_PATH := $(call my-dir)

PRODUCT_SOONG_NAMESPACES += \
    vendor/extras

include $(call all-subdir-makefiles,$(LOCAL_PATH))

# Overlay directory inclusion
PRODUCT_PACKAGE_OVERLAYS += vendor/extras/overlay/common

# Font configuration
PRODUCT_PACKAGES += \
    fonts_customization.xml
