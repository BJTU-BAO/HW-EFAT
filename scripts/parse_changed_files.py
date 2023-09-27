#!/bin/bash
# Copyright 2021 Huawei Technologies Co., Ltd
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

import os
import sys

CPU_UT = "CPU_UT"
PASS_UT = "PASS_UT"
OM_UT = "OM_UT"
TILING_UT = "TILING_UT"
PROTO_UT = "PROTO_UT"
PLUGIN_UT = "PLUGIN_UT"
ONNX_PLUGIN_UT = "ONNX_PLUGIN_UT"
OTHER_FILE="OTHER_FILE"

class FileChangeInfo:
    def __init__(self, proto_changed_files=None, tiling_changed_files=None, pass_changed_files=None,
                 om_changed_files=None, aicpu_changed_files=None,
                 plugin_changed_files=None, onnx_plugin_changed_files=None, other_changed_files=None):
        self.proto_changed_files = [] if proto_changed_files is None else proto_changed_files
        self.tiling_changed_files = [] if tiling_changed_files is None else tiling_changed_files
        self.pass_changed_files = [] if pass_changed_files is None else pass_changed_files
        self.om_changed_files = [] if om_changed_files is None else om_changed_files
        self.aicpu_changed_files = [] if aicpu_changed_files is None else aicpu_changed_files
        self.plugin_changed_files = [] if plugin_changed_files is None else plugin_changed_files
        self.onnx_plugin_changed_files = [] if onnx_plugin_changed_files is None else onnx_plugin_changed_files
        self.other_changed_files = [] if other_changed_files is None else other_changed_files

    def print_change_info(self):
        print("=========================================================================\n")
        print("changed file info\n")
        print("-------------------------------------------------------------------------\n")
        print("infershape proto changed files: \n%s" % "\n".join(self.proto_changed_files))
        print("-------------------------------------------------------------------------\n")
        print("tiling changed files: \n%s" % "\n".join(self.tiling_changed_files))
        print("-------------------------------------------------------------------------\n")
        print("fusion changed files: \n%s" % "\n".join(self.pass_changed_files))
        print("-------------------------------------------------------------------------\n")
        print("bianry om changed files: \n%s" % "\n".join(self.om_changed_files))
        print("-------------------------------------------------------------------------\n")
        print("aicpu changed files: \n%s" % "\n".join(self.aicpu_changed_files))
        print("-------------------------------------------------------------------------\n")
        print("plugin changed files: \n%s" % "\n".join(self.plugin_changed_files))
        print("-------------------------------------------------------------------------\n")
        print("onnx plugin changed files: \n%s" % "\n".join(self.onnx_plugin_changed_files))
        print("-------------------------------------------------------------------------\n")
        print("other changed files: \n%s" % "\n".join(self.other_changed_files))
        print("=========================================================================\n")


def get_file_change_info_from_ci(changed_file_info_from_ci):
    """
      get file change info from ci, ci will write `git diff > /or_filelist.txt`
      :param changed_file_info_from_ci: git diff result file from ci
      :return: None or FileChangeInf
      """
    or_file_path = os.path.realpath(changed_file_info_from_ci)
    if not os.path.exists(or_file_path):
        print("[ERROR] change file is not exist, can not get file change info in this pull request.")
        return None
    with open(or_file_path) as or_f:
        lines = or_f.readlines()
        proto_changed_files = []
        tiling_changed_files = []
        pass_changed_files = []
        om_changed_files = []
        aicpu_changed_files = []
        plugin_changed_files = []
        onnx_plugin_changed_files = []
        other_changed_files = []


        base_path = os.path.join("ops", "built-in")
        ut_path = os.path.join("ops", "built-in", "tests", "ut")
        for line in lines:
            line = line.strip()
            if line.endswith(".py"):
                continue
            if line.startswith(os.path.join(base_path, "aicpu")) or line.startswith(
                    os.path.join(ut_path, "aicpu_test")) or line.startswith(
                    os.path.join(base_path, "tests", "utils")):
                aicpu_changed_files.append(line)
            elif line.startswith(os.path.join(base_path, "fusion_pass")) or line.startswith(
                    os.path.join(ut_path, "graph_fusion")):
                pass_changed_files.append(line)
            elif (line.startswith(os.path.join(base_path, "kernel/binary_config/utils")) or line.startswith(
                    os.path.join(ut_path, "binary_om_test"))) and \
                 (line.endswith(".cc") or line.endswith(".h") or line.endswith(".cpp")):
                om_changed_files.append(line)
            elif line.startswith(os.path.join(base_path, "op_proto")) or line.startswith(
                    os.path.join(ut_path, "ops_test")):
                proto_changed_files.append(line)
            elif line.startswith(os.path.join(base_path, "op_tiling")) or line.startswith(
                    os.path.join(ut_path, "op_tiling_test")):
                tiling_changed_files.append(lines)
            elif line.startswith(os.path.join(base_path, "framework", "tf_plugin")) or line.startswith(
                    os.path.join(ut_path, "plugin_test", "tensorflow")) or line.startswith(
                os.path.join(ut_path, "plugin_test", "common")):
                plugin_changed_files.append(line)
            elif line.startswith(os.path.join(base_path, "framework", "onnx_plugin")) or line.startswith(
                    os.path.join(ut_path, "plugin_test", "onnx")) or line.startswith(
                os.path.join(ut_path, "plugin_test", "common")):
                onnx_plugin_changed_files.append(line)
            else:
                other_changed_files.append(line)
    return FileChangeInfo(proto_changed_files=proto_changed_files, tiling_changed_files=tiling_changed_files,
                          pass_changed_files=pass_changed_files, om_changed_files=om_changed_files,
                          aicpu_changed_files=aicpu_changed_files, plugin_changed_files=plugin_changed_files,
                          onnx_plugin_changed_files=onnx_plugin_changed_files, other_changed_files=other_changed_files)


def get_change_relate_ut_dir_list(changed_file_info_from_ci):
    file_change_info = get_file_change_info_from_ci(
        changed_file_info_from_ci)
    if not file_change_info:
        print("[INFO] not found file change info, run all c++.")
        return None
    # file_change_info.print_change_info()

    def _get_relate_ut_list_by_file_change():

        relate_ut = set()
        other_file = set()
        if len(file_change_info.aicpu_changed_files) > 0:
            relate_ut.add(CPU_UT)
        if len(file_change_info.pass_changed_files) > 0:
            relate_ut.add(PASS_UT)
        if len(file_change_info.tiling_changed_files) > 0:
            relate_ut.add(TILING_UT)
        if len(file_change_info.proto_changed_files) > 0:
            relate_ut.add(PROTO_UT)
            relate_ut.add(PASS_UT)
            relate_ut.add(PLUGIN_UT)
        if len(file_change_info.plugin_changed_files) > 0:
            relate_ut.add(PLUGIN_UT)
        if len(file_change_info.onnx_plugin_changed_files) > 0:
            relate_ut.add(ONNX_PLUGIN_UT)
        if len(file_change_info.om_changed_files) > 0:
            relate_ut.add(OM_UT)
        if len(file_change_info.other_changed_files) > 0:
            other_file.add(OTHER_FILE)
        return relate_ut,other_file

    try:
        relate_uts,other_file = _get_relate_ut_list_by_file_change()
    except BaseException as e:
        print(e.args)
        return None
    return str(relate_uts),str(other_file)


if __name__ == '__main__':
  print(get_change_relate_ut_dir_list(sys.argv[1]))


