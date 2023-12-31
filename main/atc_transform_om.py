#!/usr/bin/env python
# coding=utf-8
"""
Function:
AtcTransformOm class
This class mainly involves atc transform om models.
Copyright Information:
Huawei Technologies Co., Ltd. All Rights Reserved © 2020
"""
import json
import os
import time

from op_test_frame.common import op_status
from op_test_frame.st.interface import utils
from op_test_frame.st.interface.const_manager import ConstManager
from op_test_frame.st.interface import op_st_case_info


class AtcTransformOm:
    """
    Class AtcTransformOm for creating acl_op.json and transforming om models.
    """
    def __init__(self, testcase_list, output_path, compile_flag, *arguments):
        self.testcase_list = testcase_list
        self.compile_flag = compile_flag
        self.machine_type = arguments[0]
        self.report = arguments[1]
        self._check_output_path(output_path, testcase_list)

    @staticmethod
    def _get_trans_data_info(desc_dic):
        if desc_dic.get('format') in ConstManager.OPTIONAL_TYPE_LIST or \
                desc_dic.get('type') == ConstManager.TYPE_UNDEFINED:
            data_shape = []
            data_type = ConstManager.TYPE_UNDEFINED
            data_format = ConstManager.TYPE_UNDEFINED
        else:
            data_shape = desc_dic.get('shape')
            data_type = desc_dic.get('type')
            data_format = desc_dic.get('format')
        return data_shape, data_type, data_format

    @staticmethod
    def _write_content_to_file(content, file_path):
        try:
            with os.fdopen(os.open(file_path, ConstManager.WRITE_FLAGS,
                                   ConstManager.WRITE_MODES),
                           'w+') as file_object:
                file_object.truncate(0)
                file_object.write(content)
        except OSError as err:
            utils.print_error_log("Unable to write file(%s): %s." % (file_path,
                                                                     str(err)))
            raise utils.OpTestGenException(
                ConstManager.OP_TEST_GEN_WRITE_FILE_ERROR) from err
        finally:
            pass
        utils.print_info_log("File %s generated successfully." % file_path)

    @staticmethod
    def _set_log_level_env(advance_args):
        """
        set log level
        """
        if advance_args is not None:
            utils.print_info_log('Set env for ATC & ACL.')
            get_log_level, get_slog_flag = advance_args.get_env_value()
            _set_log_level_env = ['export', 'ASCEND_GLOBAL_LOG_LEVEL='
                                  + get_log_level]
            set_slog_print_env = ['export', 'ASCEND_SLOG_PRINT_TO_STDOUT='
                                  + get_slog_flag]
            utils.print_info_log("Set env command line: %s && %s " % (
                " ".join(_set_log_level_env), " ".join(set_slog_print_env)))
            os.environ['ASCEND_GLOBAL_LOG_LEVEL'] = get_log_level
            os.environ['ASCEND_SLOG_PRINT_TO_STDOUT'] = get_slog_flag
            utils.print_info_log('Finish to set env for ATC & ACL.')

    @staticmethod
    def _get_atc_cmd(soc_version, advance_args):
        atc_cmd = ['atc', '--singleop=test_data/config/acl_op.json',
                   '--soc_version=' + soc_version, '--output=op_models']
        if advance_args is not None:
            atc_advance_cmd = advance_args.get_atc_advance_cmd()
            atc_cmd.extend(atc_advance_cmd)
        return atc_cmd

    def create_acl_op_json_content(self, testcase_list, output_path, compile_flag):
        """
        Prepare acl json content and write file
        """
        content = []
        if compile_flag is not None:
            compile_dic = {'compile_flag': compile_flag}
            content.append(compile_dic)
        for testcase_struct in testcase_list:
            tmp_dic = self._get_testcase_dict(testcase_struct, output_path)
            # only append non-repetitive json struct
            if tmp_dic not in content:
                content.append(tmp_dic)
        try:
            return str(json.dumps(content, sort_keys=True, indent=2))
        except TypeError:
            utils.print_error_log("")
        finally:
            pass
        return ""

    def add_op_st_stage_result(self, status=op_status.FAILED,
                               stage_name=None, result=None, cmd=None):
        """
        add op st stage_result
        """
        stage_result = op_st_case_info.OpSTStageResult(
            status, stage_name, result, cmd)
        for case_report in self.report.report_list:
            case_report.trace_detail.add_stage_result(stage_result)

    def create_acl_op(self):
        """
        Create acl_op.json
        """
        acl_json_content = self.create_acl_op_json_content(
            self.testcase_list, self.output_path, self.compile_flag)
        output_test_data_config_path = os.path.join(self.output_path + ConstManager.TEST_DATA_CONFIG_RELATIVE_PATH)
        if not os.path.exists(output_test_data_config_path):
            os.makedirs(output_test_data_config_path)
        utils.print_step_log("[%s] Generate acl_op.json for atc tools." % (os.path.basename(__file__)))
        self._write_content_to_file(acl_json_content, os.path.join(output_test_data_config_path, 'acl_op.json'))

    def transform_acl_json_to_om(self, soc_version, advance_args):
        """
        Transform acl_op.json to om models.
        """
        # generate acl_op.json for atc tools.
        self.create_acl_op()
        # set log level env.
        self._set_log_level_env(advance_args)
        # do atc single op model conversion
        utils.print_step_log("[%s] Start to convert single op to om model." % (os.path.basename(__file__)))
        origin_path = os.path.realpath(os.getcwd())
        run_out_path = os.path.join(self.output_path, ConstManager.RUN_OUT)
        op_models_path = os.path.join(run_out_path, 'op_models')
        os.chdir(run_out_path)
        atc_cmd = self._get_atc_cmd(soc_version, advance_args)
        cmd_str = "cd %s && %s " % (run_out_path, " ".join(atc_cmd))
        utils.print_info_log("ATC command line: %s" % cmd_str)
        try:
            self._execute_atc_cmd(atc_cmd, cmd_str)
        except utils.OpTestGenException:
            self.add_op_st_stage_result(op_status.FAILED,
                                        "atc_single_op_convert",
                                        None, cmd_str)
            if ConstManager.EXPECT_FAILED not in self.report.expect_dict.values():
                utils.check_path_exists(op_models_path, exception_type=ConstManager.ATC_TRANSFORM_ERROR)
        finally:
            pass
        self.add_op_st_stage_result(op_status.SUCCESS,
                                    "atc_single_op_convert",
                                    None, cmd_str)
        utils.print_info_log("Finish to convert single op.")
        os.chdir(origin_path)

    def _check_output_path(self, output_path, testcase_list):
        self.output_path = utils.check_output_path(
            output_path, testcase_list, self.machine_type)

    def _get_desc_dic(self, tmp_dic, key_desc, testcase_struct, output_path):
        tmp_dic[key_desc] = []
        input_name_list = []
        for index, desc_dic in enumerate(testcase_struct.get(key_desc)):
            data_shape, data_type, data_format = self._get_trans_data_info(desc_dic)
            if desc_dic.get('ori_format') is not None and \
                    desc_dic.get('ori_shape') is not None:
                res_desc_dic = {
                    'format': data_format,
                    'origin_format': desc_dic.get('ori_format'),
                    'type': data_type,
                    'shape': data_shape,
                    'origin_shape': desc_dic.get('ori_shape')}
            else:
                res_desc_dic = {
                    'format': data_format,
                    'type': data_type,
                    'shape': data_shape}
            # add is_const in acl_op.json
            utils.ConstInput.add_const_info_in_acl_json(desc_dic, res_desc_dic, output_path,
                                                        testcase_struct.get(ConstManager.CASE_NAME), index)
            # Add name field for input*.paramType = optional or dynamic scenarios.
            input_name = desc_dic.get('name')
            if input_name is not None:
                # check the input_desc has the same name.
                if input_name in input_name_list:
                    utils.print_error_log(
                        "The input name: (%s) has already exist." % input_name)
                    raise utils.OpTestGenException(
                        ConstManager.OP_TEST_GEN_INVALID_INPUT_NAME_ERROR)
                input_name_list.append(input_name)
                res_desc_dic.update(
                    {'name': desc_dic.get('name')})
            # Add shape_range in acl.json for dynamic shape of operators
            if desc_dic.get(ConstManager.SHAPE_RANGE):
                res_desc_dic.update(
                    {ConstManager.SHAPE_RANGE: desc_dic.get(ConstManager.SHAPE_RANGE)})
            tmp_dic[key_desc].append(res_desc_dic)

    def _get_testcase_dict(self, testcase_struct, output_path):
        # init dic with op name
        tmp_dic = {'op': testcase_struct.get('op')}
        # process input desc
        if "input_desc" in testcase_struct.keys():
            self._get_desc_dic(tmp_dic, "input_desc", testcase_struct, output_path)
        # process output desc
        if "output_desc" in testcase_struct.keys():
            self._get_desc_dic(tmp_dic, "output_desc", testcase_struct, output_path)
        # process attr
        if "attr" in testcase_struct.keys():
            tmp_dic['attr'] = []
            for attr_dic in testcase_struct.get('attr'):
                if attr_dic.get('type') == 'data_type' and attr_dic.get(
                        'value') in ConstManager.ATTR_TYPE_SUPPORT_TYPE_MAP.keys():
                    attr_dic['value'] = ConstManager.ATTR_TYPE_SUPPORT_TYPE_MAP.get(
                        attr_dic.get('value'))
                tmp_dic.get('attr').append(attr_dic)
        return tmp_dic

    def _execute_atc_cmd(self, atc_cmd, cmd_str):
        atc_start_time = time.time()
        utils.execute_command(atc_cmd)
        atc_end_time = time.time()
        utils.print_info_log('Atc execute time: %f s.'
                             % (atc_end_time - atc_start_time))
        self.add_op_st_stage_result(op_status.SUCCESS,
                                    "atc_single_op_convert",
                                    None, cmd_str)
