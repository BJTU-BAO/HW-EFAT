#!/bin/bash
# Copyright 2019-2020 Huawei Technologies Co., Ltd
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

set -e
param_usage()
{
  echo "-h|--help                        show user parameter"
  echo "--opp_install_path               opp pack install path"
  echo "--file_backup_dir                file backup directory"
}

all_param="$@"
echo "all_param:$all_param"
SCRIPT_PATH=$(cd "$(dirname $0)"; pwd)
echo "script path: $SCRIPT_PATH"
BASE_PATH=${SCRIPT_PATH%/*}
echo "base path: $BASE_PATH"
while true
do
  case "$1" in
    -h | --help)
    param_usage
    exit 0
    ;;
    --opp_install_path=*)
    opp_path=$(echo "$1" | cut -d"=" -f2-)
    opp_temp_path=$opp_path
    opp_first_char=${opp_path:0:1}
    if [[ "x$opp_first_char" == "x~" ]];then
      opp_path=$HOME/${opp_temp_path:2}
    fi
    opp_last_char=${opp_path: -1}
    if [ "$opp_last_char" == "/" ];then
      ASCEND_OPP_INSTALL_PATH=${opp_path%/*}
    else
      ASCEND_OPP_INSTALL_PATH=$opp_path
    fi
    shift
    ;;
    --file_backup_dir=*)
    file_back_path=$(echo "$1" | cut -d"=" -f2-)
    temp_path=$file_back_path
    first_char=${file_back_path:0:1}
    if [[ "x$first_char" == "x~" ]];then
      file_back_path=$HOME/${temp_path:2}
    fi
    last_char=${file_back_path: -1}
    if [ "$last_char" == "/" ];then
      FILE_BACKUP_PATH=${file_back_path%/*}
    else
      FILE_BACKUP_PATH=$file_back_path
    fi
    shift
    ;;
    -*)
    echo "Unsupported parameters : $1"
    param_usage
    exit 1
    ;;
    *)
    break
    ;;
  esac
done

if [[ "x$ASCEND_OPP_INSTALL_PATH" = "x" ]]; then
  ASCEND_OPP_INSTALL_PATH="/usr/local/Ascend/latest"
fi

if [[ ! -d "$ASCEND_OPP_INSTALL_PATH/opp/" ]]; then
  echo "directory $ASCEND_OPP_INSTALL_PATH/opp/ is not exist"
  exit 1;
fi

# create backup_dir for copy existing file
if [[ "x$FILE_BACKUP_PATH" = "x" ]]; then
  FILE_BACKUP_PATH="$BASE_PATH"
else
  if [[ ! -d "$FILE_BACKUP_PATH" ]]; then
    echo "$FILE_BACKUP_PATH is not exist"
    exit 1
  fi
fi
mkdir -p $FILE_BACKUP_PATH/backup_dir > /dev/null 2>&1
if [[ ! -d "$FILE_BACKUP_PATH/backup_dir" ]]; then
  echo "create directory $FILE_BACKUP_PATH/backup_dir failed"
  exit 1
fi

# install libcpu_kernels_v*.so on the device
install_kernel()
{
    AICPU_KERNEL_INSTALL_PATH="$1/opp/built-in/op_impl/aicpu/aicpu_kernel/lib/Ascend910"
    AICPU_KERNEL_PATH="$2/build/install/aicpu"
    if [[ -d  "$AICPU_KERNEL_PATH" ]]; then
      chmod 750 $AICPU_KERNEL_INSTALL_PATH
      chmod 640 $AICPU_KERNEL_INSTALL_PATH/libcpu_kernels_v*.so
      cp -f $AICPU_KERNEL_INSTALL_PATH/libcpu_kernels_v*.so $FILE_BACKUP_PATH/backup_dir
      if [[ $? -ne 0 ]]; then
        echo "copy libcpu_kernels_v*.so to $FILE_BACKUP_PATH/backup_dir failed"
        chmod 440 $AICPU_KERNEL_INSTALL_PATH/libcpu_kernels_v*.so
        chmod 550 $AICPU_KERNEL_INSTALL_PATH
        return 1
      fi

      cp -f $AICPU_KERNEL_PATH/libcpu_kernels_v*.so $AICPU_KERNEL_INSTALL_PATH
      if [[ $? -ne 0 ]]; then
        echo "copy libcpu_kernels_v*.so to $AICPU_KERNEL_INSTALL_PATH failed"
        chmod 440 $AICPU_KERNEL_INSTALL_PATH/libcpu_kernels_v*.so
        chmod 550 $AICPU_KERNEL_INSTALL_PATH
        return 1
      fi
      echo "copy libcpu_kernels_v*.so to $AICPU_KERNEL_INSTALL_PATH success"
    else
      echo "directory $AICPU_KERNEL_PATH is not exist"
      return 1
    fi
    return 0
}

# install aicpu_kernel.json on the device
install_json()
{
    AICPU_JSON_INSTALL_PATH="$1/opp/built-in/op_impl/aicpu/aicpu_kernel/config"
    AICPU_JSON_PATH="$2/build/install/opp/built-in/op_impl/aicpu/aicpu_kernel/config"
    if [[ -d  "$AICPU_JSON_PATH" ]]; then
      chmod 750 $AICPU_JSON_INSTALL_PATH
      chmod 640 $AICPU_JSON_INSTALL_PATH/aicpu_kernel.json
      cp -f $AICPU_JSON_INSTALL_PATH/aicpu_kernel.json $FILE_BACKUP_PATH/backup_dir
      if [[ $? -ne 0 ]]; then
        echo "copy aicpu_kernel.json to $FILE_BACKUP_PATH/backup_dir failed"
        chmod 550 $AICPU_JSON_INSTALL_PATH/aicpu_kernel.json
        chmod 550 $AICPU_JSON_INSTALL_PATH
        return 1
      fi

      cp -f $AICPU_JSON_PATH/aicpu_kernel.json $AICPU_JSON_INSTALL_PATH
      if [[ $? -ne 0 ]]; then
        echo "copy aicpu_kernel.json to $AICPU_JSON_INSTALL_PATH failed"
        chmod 550 $AICPU_JSON_INSTALL_PATH/aicpu_kernel.json
        chmod 550 $AICPU_JSON_INSTALL_PATH
        return 1
      fi
      echo "copy aicpu_kernel.json to $AICPU_JSON_INSTALL_PATH success"
    else
      echo "directory $AICPU_JSON_PATH is not exist"
      return 1
    fi
    return 0
}

modify_init_conf_file()
{
  INIT_CONF_PATH="$1/fwkacllib/lib64/plugin/opskernel/config"
  if [[ ! -f "$INIT_CONF_PATH/init.conf" ]]; then
    echo "can not find init.conf in $INIT_CONF_PATH, install failed"
    return 1
  fi
  chmod 750 $INIT_CONF_PATH
  chmod 640 $INIT_CONF_PATH/init.conf
  sed -i "/LoadCpuKernelsInModel/s/0/1/g" $INIT_CONF_PATH/init.conf
  if [[ $? -ne 0 ]]; then
    echo "modify $INIT_CONF_PATH/init.conf failed"
    chmod 440 $INIT_CONF_PATH/init.conf
    chmod 550 $INIT_CONF_PATH
    return 1
  fi
  chmod 440 $INIT_CONF_PATH/init.conf
  chmod 550 $INIT_CONF_PATH
  return 0
}

recover_kernel_and_json_mode()
{
  chmod 440 $AICPU_KERNEL_INSTALL_PATH/libcpu_kernels_v*.so
  chmod 550 $AICPU_KERNEL_INSTALL_PATH
  chmod 550 $AICPU_JSON_INSTALL_PATH/aicpu_kernel.json
  chmod 550 $AICPU_JSON_INSTALL_PATH
}

install_kernel $ASCEND_OPP_INSTALL_PATH $BASE_PATH
if [[ $? -ne 0 ]]; then
  echo "install cpu_kernels failed!"
  exit 1
fi

install_json $ASCEND_OPP_INSTALL_PATH $BASE_PATH
if [[ $? -ne 0 ]]; then
  echo "install aicpu_kernel.json failed!"
  cp -f $FILE_BACKUP_PATH/backup_dir/libcpu_kernels_v*.so $AICPU_KERNEL_INSTALL_PATH
  chmod 440 $AICPU_KERNEL_INSTALL_PATH/libcpu_kernels_v*.so
  chmod 550 $AICPU_KERNEL_INSTALL_PATH
  exit 1
fi

modify_init_conf_file $ASCEND_OPP_INSTALL_PATH
if [[ ! -f "$INIT_CONF_PATH/init.conf" ]]; then
  echo "can not find init.conf in $INIT_CONF_PATH, install failed"
  cp -f $FILE_BACKUP_PATH/backup_dir/libcpu_kernels_v*.so $AICPU_KERNEL_INSTALL_PATH
  cp -f $FILE_BACKUP_PATH/backup_dir/aicpu_kernel.json $AICPU_JSON_INSTALL_PATH
  recover_kernel_and_json_mode
  exit 1
fi

recover_kernel_and_json_mode
exit 0
