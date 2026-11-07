# pewpew's line-in capture node: `idf.py build`, or `just firmware` in the
# pinned ESP-IDF image (docs/audio.md).
cmake_minimum_required(VERSION 3.16)

set(PROJECT_VER "0.1.0")
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(pewpew-audio-node)

# The node's key image, made by `python -m pewpew audio key MAC`:
# `idf.py -DNODE_KEY=PATH.csv flash` writes it to the nodekey partition with
# the firmware. Without it, the build has no key image and a flash leaves
# the partition as it was.
if(NODE_KEY)
    nvs_create_partition_image(nodekey "${NODE_KEY}" FLASH_IN_PROJECT)
endif()
