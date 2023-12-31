#!/usr/bin/env python
# coding=utf-8
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
"""
op st repory info,
apply info classes: OpSTCaseReport, OpSTReport
"""

import os
import json

import numpy as np
from op_test_frame.common import op_status
from op_test_frame.utils import file_util
from op_test_frame.st.interface.op_st_case_info import OpSTCaseTrace
from op_test_frame.st.interface.const_manager import ConstManager
from op_test_frame.st.interface import utils


class ReportJsonEncoder(json.JSONEncoder):
    """
    class ReportJsonEncoder
    """

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, complex):
            return {obj.__class__.__name__: True, "real": obj.real,
                    "imag": obj.imag}
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


class OpSTCaseReport:
    """
    The class for store case report information.
    """
    def __init__(self, case_run_trace: OpSTCaseTrace):
        self.case_name = case_run_trace.st_case_info.case_name
        self.status = op_status.SUCCESS
        self.trace_detail = case_run_trace
        self.expect = ConstManager.EXPECT_SUCCESS

    @staticmethod
    def parser_json_obj(json_obj):
        """
        parse json to OpSTCaseReport, call by OpSTReport
        :param json_obj: the json content
        :return: OpSTCaseReport object
        """
        if not json_obj:
            return ""
        return OpSTCaseReport(OpSTCaseTrace.parser_json_obj(
            json_obj.get("trace_detail")))

    def update_case_status(self):
        """
        update case status
        :return:
        """
        stage_list = self.trace_detail.stage_result
        for stage_res in stage_list:
            if not stage_res.is_success():
                self.status = op_status.FAILED

    def update_case_expect(self, expect_dict):
        """
        update case expect
        :param: expect_dict
        """
        if "_sub_case" in self.case_name:
            sub_str_index = self.case_name.rfind("_sub_case")
        elif "_fuzz_case" in self.case_name:
            sub_str_index = self.case_name.rfind("_fuzz_case")
        else:
            sub_str_index = self.case_name.rfind("_case")
        parent_case_name = self.case_name[:sub_str_index]
        if parent_case_name in expect_dict.keys() and \
                expect_dict.get(parent_case_name) == ConstManager.EXPECT_FAILED:
            self.expect = ConstManager.EXPECT_FAILED

    def to_json_obj(self):
        """
        generate json
        :return: json
        """
        return {
            "case_name": self.case_name,
            "status": self.status,
            "expect": self.expect,
            "trace_detail": None if not self.trace_detail else self.trace_detail.to_json_obj()
        }


class OpSTReport:
    """
    The class for store st report information.
    """
    def __init__(self, run_cmd=None):
        self.run_cmd = run_cmd
        self.total_cnt = 0
        self.failed_cnt = 0
        self.success_cnt = 0
        self.report_list = []
        self.expect_dict = {}

    @staticmethod
    def parser_json_obj(json_obj):
        """
        parse json to the OpSTReport
        :param json_obj: the json content
        :return: the OpSTReport object
        """
        rpt = OpSTReport(json_obj.get("run_cmd"))
        for case_rpt in (OpSTCaseReport.parser_json_obj(case_obj) for case_obj in json_obj.get("report_list")):
            rpt.add_case_report(case_rpt)
        return rpt

    @staticmethod
    def _save_json_file(report_data_path, json_str):
        if os.path.exists(report_data_path):
            os.remove(report_data_path)
        with os.fdopen(os.open(report_data_path, ConstManager.DATA_FILE_FLAGS,
                               ConstManager.DATA_FILE_MODES), 'w') as rpt_fout:
            rpt_fout.write(json_str)

    def set_expect(self, input_json_path):
        """
        set expect value from json
        param input_json_path: input json file path
        return: None
        """
        op_case_list = utils.load_json_file(input_json_path)
        for op_case in op_case_list:
            op_case_name = op_case.get(ConstManager.CASE_NAME)
            self.expect_dict[op_case_name] = ConstManager.EXPECT_SUCCESS
            if "expect" in op_case.keys():
                expect_value = op_case.get("expect")
                if expect_value in [ConstManager.EXPECT_SUCCESS, ConstManager.EXPECT_FAILED]:
                    self.expect_dict[op_case_name] = expect_value
                else:
                    utils.print_warn_log("please use 'success' or 'failed' for the value of expect,"
                                         "the default value 'success' is used here.")

    def update_cnt(self, case: OpSTCaseReport):
        """
        update all kinds of cnt
        :param case: OpStCaseReport object
        """
        self.total_cnt += 1
        if case.status == case.expect:
            self.success_cnt += 1
        else:
            self.failed_cnt += 1

    def add_case_report(self, case_rpt: OpSTCaseReport):
        """
        add case to report
        :param case_rpt: the OpSTCaseReport object
        :return: None
        """
        self.report_list.append(case_rpt)

    def get_case_report(self, case_name):
        """
        get OpSTCaseReport object by case name
        :param case_name: the test case name
        :return: the OpSTCaseReport object
        """
        case_reports_tuple = (x for x in self.report_list if x.case_name == case_name)
        case_reports = list(case_reports_tuple)
        case_count = len(case_reports)
        if case_count < 1:
            utils.print_warn_log("There is no test case named %s. Please "
                                 "check." % case_name)
            return ""
        if case_count > 1:
            utils.print_warn_log("There is %d test case named %s. Please "
                                 "check. " % (case_count, case_name))
            return ""
        return case_reports[0]

    def console_print(self):
        """
        print summary info to console
        :return:None
        """
        print(self._summary_txt())

    def load(self, report_file):
        """
        load report by report file
        :param report_file:the path of report
        :return: None
        """
        with open(report_file) as r_f:
            json_str = r_f.read()
        json_obj = json.loads(json_str)
        self.run_cmd = json_obj.get("run_cmd")
        for case_rpt in (OpSTCaseReport.parser_json_obj(case_obj) for case_obj in json_obj.get("report_list")):
            self.add_case_report(case_rpt)

    def save(self, report_data_path):
        """
        save the report information to the file
        :param report_data_path: the json file to store information
        :return:None
        """
        json_obj = self._to_json_obj()
        report_data_path = os.path.realpath(report_data_path)
        report_data_dir = os.path.dirname(report_data_path)
        if not os.path.exists(report_data_dir):
            file_util.makedirs(report_data_dir, mode=ConstManager.DATA_DIR_MODES)
        json_str = json.dumps(json_obj, indent=4, cls=ReportJsonEncoder)
        try:
            self._save_json_file(report_data_path, json_str)
        except OSError as ex:
            utils.print_error_log(
                'Failed to create {}. Please check the path permission or '
                'disk space. {} '.format(report_data_dir, str(ex)))
            raise utils.OpTestGenException(ConstManager.OP_TEST_GEN_INVALID_PATH_ERROR) from ex
        finally:
            pass

    def _to_json_obj(self):
        report_tuple = (case_rpt.to_json_obj() for case_rpt in self.report_list)
        return {
            "run_cmd": self.run_cmd,
            "report_list": list(report_tuple),
            "summary": self._summary_to_json()
        }

    def _summary_to_json(self):
        return {
            "test case count": self.total_cnt,
            "success count": self.success_cnt,
            "failed count": self.failed_cnt
        }

    def _summary_txt(self):
        if not self.report_list:
            return ""
        for case in self.report_list:
            case.update_case_status()
            case.update_case_expect(self.expect_dict)
            self.update_cnt(case)

        total_txt = """========================================================================
run command: %s
------------------------------------------------------------------------
- test case count: %d
- success count: %d
- failed count: %d
------------------------------------------------------------------------
""" % (self.run_cmd, self.total_cnt, self.success_cnt, self.failed_cnt)
        total_txt += "========================================================================\n"
        return total_txt
