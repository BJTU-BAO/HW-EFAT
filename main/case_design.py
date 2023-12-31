#!/usr/bin/env python
# coding=utf-8
"""
Function:
CaseDesign class
This class mainly involves parse
Copyright Information:
Huawei Technologies Co., Ltd. All Rights Reserved © 2020
"""


import os

from op_test_frame.st.interface import utils
from op_test_frame.st.interface.subcase_design_fuzz import SubCaseDesignFuzz
from op_test_frame.st.interface.subcase_design_cross import SubCaseDesignCross
from op_test_frame.st.interface.const_manager import ConstManager


def check_required_key_valid(json_obj, required_key_list, tensor, json_path):
    """
    check required key valid
    :param json_obj: json object for case
    :param required_key_list: the list of required keys
    :param tensor: the key of json object
    :param json_path: the path of json object
    :return: none
    """
    if json_obj.get(ConstManager.ST_MODE) == "ms_python_train":
        required_key_list.append(ConstManager.ST_MODE)
    missing_keys = []
    for key in required_key_list:
        if key not in json_obj:
            missing_keys.append(key)
        if key == ConstManager.CASE_NAME or key == ConstManager.OP:
            utils.check_name_valid(json_obj.get(key), key)
    if len(missing_keys) > 0:
        utils.print_error_log(
            'The "%s" is missing key: %s. Please modify it in file %s.' % (
                tensor, missing_keys, json_path))
        raise utils.OpTestGenException(
            ConstManager.OP_TEST_GEN_INVALID_DATA_ERROR)


class CaseDesign:
    """
    the class for design test case.
    """

    def __init__(self, json_path_list, case_name_list, report):
        self.json_path_list = json_path_list.split(',')
        if case_name_list == 'all':
            self.case_name_list = None
        else:
            self.case_name_list = case_name_list.split(',')
        self.current_json_path = ''
        self.case_name_to_json_file_map = {}
        self.report = report

    def check_argument_valid(self):
        """
        check input json file valid
        """
        json_file_list = []
        for json_path in self.json_path_list:
            json_path = os.path.realpath(json_path)
            if not json_path.endswith(".json"):
                utils.print_error_log(
                    'The file "%s" is invalid, only supports .json file. '
                    'Please modify it.' % json_path)
                raise utils.OpTestGenException(
                    ConstManager.OP_TEST_GEN_INVALID_PATH_ERROR)
            utils.check_path_valid(json_path)
            json_file_list.append(json_path)
        self.json_path_list = json_file_list

    def generate_cases(self):
        """
        Generate test case by json file
        :return: the list of test case
        """
        total_case_in_file = []
        compile_flag = None
        for json_path in self.json_path_list:
            utils.print_info_log('Start to create sub test cases for %s.'
                                 % json_path)
            self.current_json_path = json_path
            # load json file
            json_object = utils.load_json_file(json_path)
            # parse json object
            for json_obj in json_object:
                if json_obj.get("compile_flag"):
                    compile_flag = json_obj.get("compile_flag")
                    continue
                check_required_key_valid(json_obj, ConstManager.REQUIRED_KEYS, 'case',
                                         self.current_json_path)
                # skip the case name not in case_name_list
                if self.case_name_list and \
                        json_obj[ConstManager.CASE_NAME] not in self.case_name_list:
                    continue
                total_case_in_file = self._get_total_case(json_obj, json_path,
                                                          total_case_in_file)
        return total_case_in_file, compile_flag

    def design(self):
        """
        Design test case by json file.
        :return: the test case list
        """
        # check json path valid
        self.check_argument_valid()

        # design sub test case by json file
        utils.print_step_log("[%s] Start to parser testcase json." % (os.path.basename(__file__)))
        case_list = self.generate_cases()

        if len(case_list[0]) == 0:
            case_info = 'all'
            if self.case_name_list:
                case_info = str(self.case_name_list)
            utils.print_error_log(
                'There is no case to generate for %s. Please modify the case '
                'name argument.' % case_info)
            raise utils.OpTestGenException(
                ConstManager.OP_TEST_GEN_INVALID_DATA_ERROR)
        return case_list

    def _get_total_case(self, json_obj, json_path, total_case_in_file):
        if json_obj[ConstManager.CASE_NAME] in self.case_name_to_json_file_map:
            utils.print_error_log(
                'The case name "%s" already exists. Please modify or '
                'remove the redundant case name in file %s.'
                % (json_obj[ConstManager.CASE_NAME], self.current_json_path))
            raise utils.OpTestGenException(
                ConstManager.OP_TEST_GEN_INVALID_DATA_ERROR)
        self.case_name_to_json_file_map[
            json_obj[ConstManager.CASE_NAME]] = json_path

        if json_obj.get(ConstManager.FUZZ_IMPL):
            subcase_parse = SubCaseDesignFuzz(self.current_json_path,
                                              json_obj,
                                              total_case_in_file,
                                              self.report)
        else:
            subcase_parse = SubCaseDesignCross(self.current_json_path,
                                               json_obj,
                                               total_case_in_file,
                                               self.report)
        total_case_in_file = subcase_parse.subcase_generate()
        return total_case_in_file
