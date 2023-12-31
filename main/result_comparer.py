#!/usr/bin/env python
# coding=utf-8
# Copyright 2020-2021 Huawei Technologies Co., Ltd
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
"""
result compare
"""
import os
import time
import numpy as np

from op_test_frame.common import op_status
from op_test_frame.st.interface import utils
from op_test_frame.st.interface import op_st_case_info
from op_test_frame.st.interface.compare_data import CompareData
from op_test_frame.st.interface.const_manager import ConstManager


class ResultTxtParser:
    """
    class parse result.txt.
    """
    def __init__(self, report, run_dir):
        self.report = report
        self.run_dir = run_dir

    def parser_result_txt(self):
        """
        parser result.txt
        :return: result_info_list list
        """
        result_info_list = []
        run_result_list = self._read_result_txt()
        for line in run_result_list:
            if len(line.split("  ")) != 3:
                continue
            index, case_name, result = line.split("  ")
            if not index.isdigit():
                utils.print_warn_log("The result line '%s' format error." %
                                     line)
                continue
            result_info_list.append((index, case_name, result))
        return result_info_list

    def _read_result_txt(self):
        # check run result.txt exists, if not exist , record failed and skip compare
        result_txt = self._check_result_txt()
        run_result_list = list()
        if result_txt:
            txt = utils.read_file(result_txt)
            run_result_list = txt.split('\n')
        return run_result_list

    def _check_result_txt(self):
        result_txt = os.path.join(self.run_dir, 'run', 'out', 'result_files', 'result.txt')
        if not os.path.exists(result_txt) or not os.access(result_txt, os.R_OK):
            utils.print_error_log("Failed to get %s. Please check the run result." % result_txt)
            # add run failed stage result to report
            run_acl_result = op_st_case_info.OpSTStageResult(op_status.FAILED, "run_acl_code", None)
            for case_report in self.report.report_list:
                case_report.trace_detail.add_stage_result(run_acl_result)
            return ""
        utils.print_info_log("Find result.txt in %s." % result_txt)
        return result_txt


class ResultCompare:
    """
    Class for result compare.
    """
    def __init__(self, report, run_dir, err_thr, error_report):
        self.report = report
        self.err_thr = err_thr
        self.error_report = error_report
        self.run_dir = run_dir

    @staticmethod
    def compare_by_path(result_dir, expect_dir, error_report):
        """
        compare output data with expect data by path
        :param result_dir: result data path
        :param expect_dir: expecet data path
        :return:
        """
        start_time = time.time()
        utils.print_info_log(
            'Step:------>>>>>> Start to compare result <<<<<<------ ')
        names = os.listdir(result_dir)
        result_list = []
        for name in names:
            result_file = os.path.join(result_dir, name)
            expect_name = name.replace("_output_", "_expect_output_")
            expect_file = os.path.join(expect_dir, expect_name)
            if not os.path.isfile(result_file):
                utils.print_warn_log("There is no result file :%s" %
                                    result_file)
                continue
            if not os.path.isfile(expect_file):
                utils.print_warn_log("There is no expect output file"
                                    ":%s" % expect_file)
                continue

            np_type = _parse_dtype_by_filename(result_file)
            if not np_type:
                utils.print_warn_log("Failed to get numpy data type from file "
                                    "name(%s),the np_type = %s")
                continue
            npu_output = np.fromfile(result_file, np_type)
            cpu_output = np.fromfile(expect_file, np_type)
            compare_data_obj = CompareData('current case', [0.01, 0.05], error_report, '')
            result, error_percent, max_error = compare_data_obj.compare(npu_output, cpu_output)
            result_list.append([result, error_percent, max_error])
        utils.print_info_log('End to compare result. Duration:%0.2f second.'
                            % (time.time() - start_time))

    @staticmethod
    def _add_op_st_stage_result(case_report, status=op_status.FAILED, stage_name=None, result=None):
        stage_result = op_st_case_info.OpSTStageResult(status, stage_name, result)
        case_report.trace_detail.add_stage_result(stage_result)

    @staticmethod
    def _check_isfile(result_file, expect_file):
        utils.print_info_log("The result file %s compares with the expected data %s" % (
            os.path.basename(result_file),
            os.path.basename(expect_file)))
        if not os.path.isfile(result_file):
            utils.print_warn_log("There is no result file :%s, skip compare." % result_file)
            return False
        if not os.path.isfile(expect_file):
            utils.print_warn_log("There is no expect output file :%s,skip compare." % expect_file)
            return False
        return True

    @staticmethod
    def _get_data_type(case_info, idx):
        output_configs = case_info.op_params.get("output_desc")
        if not output_configs:
            utils.print_warn_log("Failed to output data type.")
            return None
        str_type = output_configs[idx].get("type")
        np_type = _get_np_dtype(str_type)
        utils.print_info_log("The data type is {}, the numpy type is {}".format(str_type, np_type))
        return np_type

    def compare(self):
        """
        compare
        :return:
        """
        start_time = time.time()
        utils.print_info_log('Step:------>>>>>> Start to get result <<<<<<------ ')
        # 1. read run result.txt
        result_txt_parser = ResultTxtParser(self.report, self.run_dir)
        result_info_list = result_txt_parser.parser_result_txt()
        for result_info in result_info_list:
            index, case_name, result = result_info
            case_report = self.report.get_case_report(case_name)
            if not case_report:
                continue
            # get expect function info  from st_report.json
            with_expect_func = case_report.trace_detail.st_case_info.op_params.get("calc_expect_func_file_func")
            if with_expect_func:
                self._get_compare_stage_result(index, case_name, result, case_report)
            else:
                self._get_run_stage_result(result, case_name, case_report)
        # exist expect func, print process cost time.
        utils.print_info_log('End to get result. Duration:%0.2f second.' % (time.time() - start_time))

    def _get_case_info(self, case_name, index, case_report):
        utils.print_info_log("There case '%s' run success." % case_name)
        self._add_op_st_stage_result(case_report, op_status.SUCCESS, "run_acl_code", None)
        utils.print_info_log('Index %s:------>>>>>> Start to compare %s result <<<<<<------ ' % (index, case_name))
        case_info = case_report.trace_detail.st_case_info
        if not case_info:
            utils.print_warn_log("There is no case info for '%s'." % case_name)
            self._add_op_st_stage_result(case_report, op_status.FAILED, "compare_data", None)
            return None
        if not case_info.expect_data_paths:
            utils.print_warn_log("There is no expect data in %s for '%s'."
                                 % (case_info.expect_data_paths, case_name))
            self._add_op_st_stage_result(case_report, op_status.FAILED, "compare_data", None)
            return None
        return case_info

    def _get_compare_stage_result(self, index, case_name, result, case_report):
        if result == "[fail]":
            utils.print_info_log("Failed to run case '%s'. There is no result data for comparison. "
                                 "Skip the comparison." % case_name)
            self._add_op_st_stage_result(case_report, op_status.FAILED, "run_acl_code", None)
        elif result == "[pass]":
            case_info = self._get_case_info(case_name, index, case_report)
            if not case_info:
                return
            result_list = self._get_compare_result_list(case_info)
            # add compare report
            compare_status = op_status.SUCCESS
            if not result_list:
                compare_status = op_status.FAILED
            for result_info in result_list:
                if result_info[0] == "Failed":
                    compare_status = op_status.FAILED
            self._add_op_st_stage_result(case_report, compare_status, "compare_data", None)
        else:
            utils.print_warn_log("The result in result.txt only support '[pass]' and '[fail]', '%s' is "
                                 "unsupported." % result)

    def _get_run_stage_result(self, result, case_name, case_report):
        # get run npu result
        if result == "[fail]":
            utils.print_info_log("Failed to run case '%s'." % case_name)
            self._add_op_st_stage_result(
                case_report, op_status.FAILED, "run_acl_code", None)
        elif result == "[pass]":
            utils.print_info_log("Case '%s' run successfully." % case_name)
            self._add_op_st_stage_result(
                case_report, op_status.SUCCESS, "run_acl_code", None)
        else:
            utils.print_warn_log("The result in result.txt only support "
                                 "'[pass]' and '[fail]', '%s' is "
                                 "unsupported." % result)

    def _get_err_thr(self, case_info):
        if self.err_thr:
            err_thr = self.err_thr
        elif case_info.op_params.get(ConstManager.ERROR_THRESHOLD):
            err_thr = case_info.op_params.get(ConstManager.ERROR_THRESHOLD)
        else:
            err_thr = ConstManager.DEFAULT_ERROR_THRESHOLD
        return err_thr

    def _get_compare_result_list(self, case_info):
        result_list = list()
        for idx, expect_file in enumerate(case_info.expect_data_paths):
            result_file = case_info.planned_output_data_paths[idx]
            if not self._check_isfile(result_file, expect_file):
                continue
            np_type = self._get_data_type(case_info, idx)
            if not np_type:
                utils.print_warn_log("Failed to get numpy data type. Skip compare")
                continue
            npu_output = np.fromfile(result_file, np_type)
            cpu_output = np.fromfile(expect_file, np_type)
            err_thr = self._get_err_thr(case_info)
            compare_data_obj = CompareData(case_info.op_params, err_thr, self.error_report, self.run_dir)
            result, error_percent, max_error = compare_data_obj.compare(npu_output, cpu_output)
            result_list.append([result, error_percent, max_error])
        return result_list


def _parse_dtype_by_filename(file_name):
    file_str_list = file_name.split("_")
    file_str = file_str_list[-1]  # eg:int32.bin
    str_type = file_str.split(".")[0]
    return _get_np_dtype(str_type)


def _get_np_dtype(type_str):
    type_dict = {
        'fp64': np.float64, 'fp32': np.float32, 'float32': np.float32,
        'float': np.float32, 'fp16': np.float16, 'float16': np.float16,
        'int64': np.int64, 'int32': np.int32, 'int16': np.int16,
        'int8': np.int8, 'double': np.double,
        'uint64': np.uint64, 'uint32': np.uint32, 'uint16': np.uint16,
        'uint8': np.uint8,
        'bool': np.bool, 'complex64': np.complex64,
        'complex128': np.complex128,
    }
    return type_dict.get(type_str)
