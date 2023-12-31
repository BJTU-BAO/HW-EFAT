#!/usr/bin/env python
# coding=utf-8
"""
Function:
DataGenerator class
This class mainly involves generate data.
Copyright Information:
Huawei Technologies Co., Ltd. All Rights Reserved © 2020
"""

import sys
import os
import importlib
import functools
import time

import numpy as np

from op_test_frame.st.interface import utils
from op_test_frame.st.interface import dynamic_handle
from op_test_frame.st.interface.const_manager import ConstManager


class DataGenerator:
    """
    The class for data generator.
    """

    def __init__(self, case_list, output_path, cmd_mi, report):
        self.case_list = case_list
        self.report = report
        if cmd_mi:
            self.output_path = os.path.join(output_path, 'run', 'out',
                                            'test_data', 'data')
        else:
            op_name_path = os.path.join(output_path, case_list[0]['op'])
            self.output_path = os.path.join(output_path, op_name_path, 'run',
                                            'out', 'test_data', 'data')

    @staticmethod
    def gen_data(data_shape, min_value, max_value, dtype,
                 distribution='uniform'):
        """
        generate data
        :param data_shape: the data shape
        :param min_value: min value
        :param max_value: max value
        :param dtype: the data type
        :param distribution: the data distribution
        :return: the numpy data
        """
        np_type = getattr(np, utils.map_type_to_expect_type(dtype))

        if np_type == np.bool:
            min_value = 0
            max_value = 2  # [0, 2) in uniform
            np_type = np.int8
        if distribution == 'uniform':
            # Returns the uniform distribution random value.
            # min indicates the random minimum value,
            # and max indicates the random maximum value.
            data = np.random.uniform(low=min_value, high=max_value,
                                     size=data_shape).astype(np_type)
        elif distribution == 'normal':
            # Returns the normal (Gaussian) distribution random value.
            # min is the central value of the normal distribution,
            # and max is the standard deviation of the normal distribution.
            # The value must be greater than 0.
            data = np.random.normal(loc=min_value,
                                    scale=abs(max_value) + 1e-4,
                                    size=data_shape).astype(np_type)
        elif distribution == 'beta':
            # Returns the beta distribution random value.
            # min is alpha and max is beta.
            # The values of both min and max must be greater than 0.
            data = np.random.beta(a=abs(min_value) + 1e-4,
                                  b=abs(max_value) + 1e-4,
                                  size=data_shape).astype(np_type)
        elif distribution == 'laplace':
            # Returns the Laplacian distribution random value.
            # min is the central value of the Laplacian distribution,
            # and max is the exponential attenuation of the Laplacian
            # distribution.  The value must be greater than 0.
            data = np.random.laplace(loc=min_value,
                                     scale=abs(max_value) + 1e-4,
                                     size=data_shape).astype(np_type)
        elif distribution == 'triangular':
            # Return the triangle distribution random value.
            # min is the minimum value of the triangle distribution,
            # mode is the peak value of the triangle distribution,
            # and max is the maximum value of the triangle distribution.
            mode = np.random.uniform(low=min_value, high=max_value)
            data = np.random.triangular(left=min_value, mode=mode,
                                        right=max_value,
                                        size=data_shape).astype(np_type)
        elif distribution == 'relu':
            # Returns the random value after the uniform distribution
            # and relu activation.
            data_pool = np.random.uniform(low=min_value, high=max_value,
                                          size=data_shape).astype(np_type)
            data = np.maximum(0, data_pool)
        elif distribution == 'sigmoid':
            # Returns the random value after the uniform distribution
            # and sigmoid activation.
            data_pool = np.random.uniform(low=min_value, high=max_value,
                                          size=data_shape).astype(np_type)
            data = 1 / (1 + np.exp(-data_pool))
        elif distribution == 'softmax':
            # Returns the random value after the uniform distribution
            # and softmax activation.
            data_pool = np.random.uniform(low=min_value, high=max_value,
                                          size=data_shape).astype(np_type)
            data = np.exp(data_pool) / np.sum(np.exp(data_pool))
        elif distribution == 'tanh':
            # Returns the random value after the uniform distribution
            # and tanh activation.
            data_pool = np.random.uniform(low=min_value, high=max_value,
                                          size=data_shape).astype(np_type)
            data = (np.exp(data_pool) - np.exp(-data_pool)) / \
                   (np.exp(data_pool) + np.exp(-data_pool))
        else:
            utils.print_error_log('The distribution(%s) is invalid.' %
                                  distribution)
            raise utils.OpTestGenException(
                ConstManager.OP_TEST_GEN_WRITE_FILE_ERROR)
        if np_type == np.bool:
            data = data.astype(np_type)
        return data

    @staticmethod
    def _check_data_size(data, value, input_shape):
        input_size = functools.reduce(lambda x, y: x * y, input_shape)
        data_size = functools.reduce(lambda x, y: x * y, data.shape)
        if input_size != data_size:
            utils.print_error_log(
                "The size of data from %s not equal to input shape size." % value)
            raise utils.OpTestGenException(
                ConstManager.OP_TEST_GEN_WRITE_FILE_ERROR)

    @staticmethod
    def _save_data(data, file_path):
        data.tofile(file_path)
        os.chmod(file_path, ConstManager.WRITE_MODES)

    @staticmethod
    def _get_expect_result_tensors(module, expect_func, calc_func_params_tmp):
        func = getattr(module, expect_func)
        return func(**calc_func_params_tmp)

    def gen_data_with_value(self, input_shape, value, dtype):
        """
        generate data with value
        :param input_shape: the data shape
        :param value: input value
        :param dtype: the data type
        :return: the numpy data
        """
        dtype = utils.map_type_to_expect_type(dtype)
        if isinstance(value, str):
            data = np.fromfile(value, dtype)
            self._check_data_size(data, value, input_shape)
            data.shape = input_shape
            return data
        data = np.array(value, dtype=dtype)
        if list(data.shape) == input_shape or len(input_shape) == 0:
            return data
        utils.print_error_log("The value shape is not equal to the input shape.")
        raise utils.OpTestGenException(
            ConstManager.OP_TEST_GEN_WRITE_FILE_ERROR)

    def generate(self):
        """
        generate data by case list
        """
        utils.check_path_valid(self.output_path, True)
        gen_data_start = time.time()
        utils.print_step_log("[%s] Generate data for testcase." % (os.path.basename(__file__)))
        for case in self.case_list:
            # support no input scene
            if len(case.get('input_desc')) < 1:
                utils.print_info_log("There are no inputs. Skip generating input data.")
                return
            case_name = case.get('case_name')
            utils.print_info_log(
                'Start to generate the input data for %s.' % case_name)
            param_info = ""
            # get intput  and output param
            param_info_list, calc_func_params_tmp = \
                self._generate_params_desc(case, case_name)
            # get attr param
            if case.get('attr'):
                for _, attr in enumerate(case.get('attr')):
                    attr_name = attr.get('name')
                    param_info_list.append("{attr_name}".format(
                        attr_name=attr_name))
                    calc_func_params_tmp.update(
                        {attr_name: attr.get('value')})
            if case.get("calc_expect_func_file") \
                    and case.get("calc_expect_func_file_func"):
                param_info += ', '.join(param_info_list)
                utils.print_info_log(
                    '-------------------------------->>>>>> Expect function information <<<<<<-----------------------')
                utils.print_info_log(
                    "The parameter information passed by user's cases is: %s(%s)."
                    % (case.get("calc_expect_func_file_func"), param_info))
                utils.print_info_log("Please ensure that the above parameters "
                                     "in the expected function are consistent.")
                utils.print_info_log(
                    '------------------------------------------------------------------------------------------------')
            expect_data_paths = self._generate_expect_data(
                case, calc_func_params_tmp)
            # deal with report
            case_report = self.report.get_case_report(case_name)
            case_report.trace_detail.st_case_info.input_data_paths = \
                self.output_path
            if expect_data_paths:
                case_report.trace_detail.st_case_info.expect_data_paths = \
                    expect_data_paths
                utils.print_info_log(
                    'Finish to generator the expect output data for '
                    '%s.' % case_name)
        gen_data_end = time.time()
        utils.print_info_log('Generate data execute time: %f s.'
                             % (gen_data_end - gen_data_start))
        utils.print_info_log("Generate data for testcase in %s." % self.output_path)

    def _gen_op_iput_data(self, input_shape, input_desc):
        range_min, range_max = input_desc.get('value_range')
        dtype = input_desc.get('type')
        value = input_desc.get('value')
        if value:
            data = self.gen_data_with_value(input_shape, value, dtype)
        else:
            data = self.gen_data(
                input_shape, range_min, range_max, dtype,
                input_desc.get('data_distribute'))
        return data

    def _gen_input_data(self, input_shape, input_desc, file_path):
        try:
            data = self._gen_op_iput_data(input_shape, input_desc)
        except MemoryError as error:
            utils.print_warn_log(
                'Failed to generate data for %s. The shape is too '
                'large to invoke MemoryError. %s' % (file_path, error))
            raise utils.OpTestGenException(ConstManager.OP_TEST_GEN_WRITE_FILE_ERROR) from error
        finally:
            pass
        return data

    def _get_input_dict_with_data(self, input_desc, file_path, input_shape):
        """
        Data generation modes in two scenarios are considered.s:
        1.Trans data 2.constant data
        """
        is_const_distribute = (input_desc.get(ConstManager.IS_CONST) and
                               input_desc.get(ConstManager.DATA_DISTRIBUTE) and
                               input_desc.get(ConstManager.VALUE) is None)
        if is_const_distribute:
            input_dic = self._get_const_data_input_dict(input_desc, file_path, input_shape)
        else:
            input_dic = self._get_trans_data_input_dict(input_desc, file_path, input_shape)
        return input_dic

    def _get_const_data_input_dict(self, input_desc, file_path, input_shape):
        data_list = np.fromfile(file_path, dtype=input_desc.get('type'))
        self._check_data_size(data_list, file_path, input_shape)
        input_shape = tuple(input_shape)
        data = np.array(data_list).reshape(input_shape)
        input_dic = {
            'value': data,
            'dtype': input_desc.get('type'),
            'shape': input_shape,
            'format': input_desc.get('format')
        }
        return input_dic

    def _get_trans_data_input_dict(self, input_desc, file_path, input_shape):
        if os.path.exists(file_path):
            utils.print_error_log(
                'The file %s already exists, please delete it then'
                ' retry.' % file_path)
            raise utils.OpTestGenException(
                ConstManager.OP_TEST_GEN_WRITE_FILE_ERROR)
        data = self._gen_input_data(input_shape, input_desc, file_path)
        input_dic = {
            'value': data,
            'dtype': input_desc.get('type'),
            'shape': input_shape,
            'format': input_desc.get('format')
        }
        try:
            self._save_data(data, file_path)
        except OSError as error:
            utils.print_warn_log(
                'Failed to generate data for %s. %s' % (
                    file_path, error))
            raise utils.OpTestGenException(ConstManager.OP_TEST_GEN_WRITE_FILE_ERROR) from error
        finally:
            pass
        return input_dic

    def _get_input_desc_and_gen_data(
            self, case, case_name, calc_func_params_tmp, param_info_list):
        """
        get input desc info
        """
        for index, input_desc in enumerate(case.get('input_desc')):
            if input_desc.get('type') in ConstManager.OPTIONAL_TYPE_LIST:
                continue
            # consider dynamic shape scenario
            input_shape = dynamic_handle.replace_shape_to_typical_shape(
                input_desc)
            file_path = os.path.join(
                self.output_path,
                case_name + '_input_' + str(index) + '.bin')
            input_dict = self._get_input_dict_with_data(input_desc, file_path, input_shape)
            if input_desc.get('name'):
                input_name = input_desc.get('name')
                calc_func_params_tmp.update(
                    {input_name: input_dict})
                param_info_list.append("{input_name}".format(
                    input_name=input_name))

    def _generate_params_desc(self, case, case_name):
        calc_func_params_tmp = {}
        param_info_list = []
        self._get_input_desc_and_gen_data(
            case, case_name, calc_func_params_tmp, param_info_list)
        for _, output_desc in enumerate(case['output_desc']):
            output_shape = dynamic_handle.replace_shape_to_typical_shape(
                output_desc)
            output_dic = {
                'dtype': output_desc.get('type'),
                'shape': output_shape,
                'format': output_desc.get('format')
            }
            if output_desc.get('name'):
                output_name = output_desc.get('name')
                calc_func_params_tmp.update(
                    {output_name: output_dic})
                param_info_list.append("{output_name}".format(
                    output_name=output_name))
        return param_info_list, calc_func_params_tmp

    def _get_tensors_and_func(self, case, calc_func_params_tmp):
        expect_func_file = case.get("calc_expect_func_file")
        expect_func = case.get("calc_expect_func_file_func")
        sys.path.append(os.path.dirname(expect_func_file))
        py_file = os.path.basename(expect_func_file)
        module_name, _ = os.path.splitext(py_file)
        utils.print_info_log("Start to import %s in %s." % (module_name,
                                                            py_file))
        module = importlib.import_module(module_name)
        try:
            expect_result_tensors = self._get_expect_result_tensors(module, expect_func, calc_func_params_tmp)
        except Exception as ex:
            utils.print_error_log(
                'Failed to execute function "%s" in %s. %s' % (
                    expect_func, expect_func_file, str(ex)))
            raise utils.OpTestGenException(ConstManager.OP_TEST_GEN_INVALID_PARAM_ERROR) from ex
        finally:
            pass
        if not isinstance(expect_result_tensors, (list, tuple)):
            expect_result_tensors = [expect_result_tensors, ]
        return expect_result_tensors, expect_func

    def _generate_expect_data(self, case, calc_func_params_tmp):
        expect_data_paths = []
        case_name = case.get('case_name')
        expect_data_dir = os.path.join(self.output_path, 'expect')
        utils.make_dirs(expect_data_dir)
        if case.get("calc_expect_func_file") \
                and case.get("calc_expect_func_file_func"):
            utils.print_info_log(
                'Start to generate the expect output data for %s.' %
                case_name)
            expect_result_tensors, expect_func = self._get_tensors_and_func(
                case, calc_func_params_tmp)
            for idx, expect_result_tensor in enumerate(expect_result_tensors):
                output_dtype = case['output_desc'][idx]['type']
                if str(expect_result_tensor.dtype) != output_dtype:
                    utils.print_warn_log("The dtype of expect date clc by "
                                         "%s is %s , is not same as "
                                         "the dtype(%s) in output_desc index("
                                         "%s). "
                                         % (expect_func,
                                            expect_result_tensor.dtype,
                                            output_dtype, str(idx)))
                expect_data_name = "%s_expect_output_%s_%s.bin" % (
                    case.get('case_name'), str(idx), output_dtype)
                expect_data_path = os.path.join(expect_data_dir,
                                                expect_data_name)
                expect_result_tensor.tofile(expect_data_path)
                utils.print_info_log("Successfully generated expect "
                                     "data:%s." % expect_data_path)
                expect_data_paths.append(expect_data_path)
        return expect_data_paths
