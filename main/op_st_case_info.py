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
op st case info,
apply info classes: OpSTCase, OpSTStageResult, OpSTCaseTrace ,
"""
from op_test_frame.common import op_status


class OpSTCase:
    """
    The class for store case info.
    """
    def __init__(self, case_name=None, op_params=None):
        self.case_name = case_name
        self.op_params = op_params
        self.input_data_paths = None
        self.planned_output_data_paths = None
        self.expect_data_paths = None

    @staticmethod
    def parser_json_obj(json_obj):
        """
        parse json to OpSTCase, call by OpSTCaseTrace
        :param json_obj: the json content
        :return: OpSTCase object
        """
        if not json_obj:
            return ""
        op_case = OpSTCase(case_name=json_obj.get("case_name"),
                           op_params=json_obj.get("op_params"))
        op_case.expect_data_paths = json_obj.get("expect_data_paths")
        op_case.planned_output_data_paths = json_obj.get("planned_output_data_paths")
        op_case.input_data_paths = json_obj["input_data_path"]
        return op_case

    def to_json_obj(self):
        """
        generate json
        :return: json
        """
        return {
            "case_name": self.case_name,
            "op_params": self.op_params,
            "input_data_path": self.input_data_paths,
            "expect_data_paths": self.expect_data_paths,
            "planned_output_data_paths": self.planned_output_data_paths,
        }


class OpSTStageResult:
    """
    The class for store stage information.
    """
    def __init__(self, status=op_status.FAILED, stage_name=None,
                 result=None, cmd=None):
        self.status = status
        self.result = result
        self.stage_name = stage_name
        self.cmd = cmd

    @staticmethod
    def parser_json_obj(json_obj):
        """
        parse json to OpSTStageResult
        :param json_obj:
        :return: OpSTStageResult object
        """
        if json_obj.get("cmd"):
            return OpSTStageResult(json_obj.get("status"), json_obj.get("stage_name"),
                                   json_obj.get("result"), json_obj.get("cmd"))
        return OpSTStageResult(json_obj.get("status"), json_obj.get("stage_name"),
                               json_obj.get("result"))

    def is_success(self):
        """
        check the stage status is success or not
        :return: bool
        """
        return self.status == op_status.SUCCESS

    def to_json_obj(self):
        """
        generate json
        :return: json
        """
        if self.cmd:
            return {
                "status": self.status,
                "result": self.result,
                "stage_name": self.stage_name,
                "cmd": self.cmd
            }
        return {
            "status": self.status,
            "result": self.result,
            "stage_name": self.stage_name,
        }


class OpSTCaseTrace:
    """
    The class for store st case trace information.
    """
    def __init__(self, st_case_info: OpSTCase):
        self.st_case_info = st_case_info
        self.stage_result = []

    @staticmethod
    def parser_json_obj(json_obj):
        """
        parse json to OpSTCaseTrace, call by OpSTCaseReport
        :param json_obj: the json content
        :return: OpSTCaseTrace object
        """
        if not json_obj:
            return ""
        res = OpSTCaseTrace(OpSTCase.parser_json_obj(json_obj.get("st_case_info")))
        stage_result_tuple = (OpSTStageResult.parser_json_obj(stage_obj) for
                              stage_obj in json_obj.get("stage_result"))
        res.stage_result = list(stage_result_tuple)
        return res

    def add_stage_result(self, stage_res: OpSTStageResult):
        """
        add stage result to STCaseTrace
        :param stage_res: stage information
        :return: stage result list
        """
        for result in self.stage_result:
            if result.stage_name == stage_res.stage_name:
                result.result = stage_res.result
                result.cmd = stage_res.cmd
                result.status = stage_res.status
        self.stage_result.append(stage_res)

    def to_json_obj(self):
        """
        generate json
        :return: json
        :return:
        """
        stage_result = (stage_obj.to_json_obj() for stage_obj in self.stage_result)
        return {
            "st_case_info": self.st_case_info.to_json_obj(),
            "stage_result": list(stage_result),
        }
