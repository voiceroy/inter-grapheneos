LOCAL_PATH := $(call my-dir)

PRODUCT_SOONG_NAMESPACES += \
    vendor/extras

include $(call all-subdir-makefiles,$(LOCAL_PATH))

# Overlay directory inclusion
PRODUCT_PACKAGE_OVERLAYS += vendor/extras/overlay/common

# Fonts
PRODUCT_PACKAGES += \
    fonts_customization.xml

PRODUCT_COPY_FILES += \
    $(call find-copy-subdir-files,*,vendor/extras/prebuilt/fonts,$(TARGET_COPY_OUT_PRODUCT)/fonts)
