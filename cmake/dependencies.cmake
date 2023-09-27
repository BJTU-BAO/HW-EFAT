# Copyright 2020 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

# Ascend mode
if(DEFINED ENV{ASCEND_CUSTOM_PATH})
  set(ASCEND_DIR $ENV{ASCEND_CUSTOM_PATH})
else()
  set(ASCEND_DIR /usr/local/Ascend/latest)
endif()
message("Search libs under install path ${ASCEND_DIR}")

set(ASCEND_ATC_DIR ${ASCEND_DIR}/compiler/lib64)
set(ASCEND_OPENSDK_LIB ${ASCEND_DIR}/opensdk/opensdk/lib)
set(CMAKE_PREFIX_PATH ${ASCEND_DIR}/opensdk/opensdk/cmake)

if (BUILD_OPEN_PROJECT)
  list(APPEND CMAKE_PREFIX_PATH ${ASCEND_DIR}/opensdk/opensdk/jpeg)
  set(CMAKE_MODULE_PATH ${ASCEND_DIR}/opensdk/opensdk/cmake/modules)
  find_package(jpeg MODULE)
endif()

find_package(slog CONFIG REQUIRED)
find_package(metadef CONFIG REQUIRED)
find_module(ascend_protobuf libascend_protobuf.so.3.13.0.0 ${ASCEND_ATC_DIR})
find_package(mmpa CONFIG REQUIRED)
find_package(parser CONFIG REQUIRED)
find_package(opcompiler CONFIG REQUIRED)
find_package(platform CONFIG REQUIRED)
find_package(ascend_hal CONFIG REQUIRED)
find_package(runtime CONFIG REQUIRED)
find_package(air CONFIG REQUIRED)
find_file(tbe_whl te-0.4.0-py3-none-any.whl ${ASCEND_ATC_DIR})
