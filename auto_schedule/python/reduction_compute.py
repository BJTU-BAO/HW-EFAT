#!/usr/bin/env python
# -*- coding: UTF-8 -*-
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
"""
reduction compute
"""
# 'pylint: disable=import-error
from decorator import decorator
import warnings
from te import tvm
from te.utils.error_manager.error_manager_util import get_error_message
from te.utils.shape_util import shape_to_list
from tbe.common.testing.dsl_source_info import source_info_decorator
from .cast_compute import _cast
from .elewise_compute import vmuls
from ..api import sum
from ..api import reduce_min
from ..api import reduce_max
from ..api import reduce_prod
from .util import refine_axis
from .util import is_cast_support
from .util import check_input_tensor_shape

NAME_INDEX = [0]


@decorator
def _auto_cast_of_tuple_reduce(func, *args, **kwargs):
    '''
    auto cast dectorator.
    Before calling elewise api, check the input tensor is supported by the intr.
    If not supported, casting the input tensor to supported dtype.
    (On condition that the cast type is supported.
    If the cast type is not supported,raising a RuntimeError).
    '''
    func_name = func.__name__
    supported_types = ("float16", "float32")
    if func_name != "tuple_sum":
        dict_args = {"errCode": "E90001", "detailed_cause": f"function name [{func_name}] must be tuple_sum"}
        raise RuntimeError(dict_args, get_error_message(dict_args))

    def _is_last_axis(shape, axis):
        if isinstance(axis, (tuple, list)):
            local_axis = axis
        else:
            local_axis = [axis]
        return len(shape) - 1 in local_axis

    def _check_tensor(tensor_list):
        if len(tensor_list) != 2:
            dict_args = {"errCode": "E90001",
                         "detailed_cause": f"Tuple reduce input tensors must be 2. while is [{len(tensor_list)}]"}
            raise RuntimeError(dict_args, get_error_message(dict_args))
        shape1 = shape_to_list(tensor_list[0].shape)
        shape2 = shape_to_list(tensor_list[1].shape)
        if shape1 != shape2:
            dict_args = {"errCode": "E90001",
                         "detailed_cause": f"Tuple reduce input tensors must have same shape. "
                                           f"while shape1 is [{shape1}], shape2 is [{shape2}]"}
            raise RuntimeError(dict_args, get_error_message(dict_args))

    def _deal_tensor_dtype(raw_tensor, supported_types):
        dtype = raw_tensor.dtype
        if func_name == "tuple_sum" and not _is_last_axis(raw_tensor.shape,
                                                          axis):
            supported_types = supported_types + ("int32",)
        dealed_tensor = raw_tensor
        if dtype not in supported_types:
            if "float32" in supported_types and is_cast_support(dtype,
                                                                "float32"):
                dealed_tensor = _cast(raw_tensor, "float32")
            else:
                dealed_tensor = _cast(raw_tensor, "float16")
        return dealed_tensor

    if len(args) == 3:
        if not isinstance(args[0], (tuple, list)):
            dict_args = {
                "errCode": "E90001",
                "detailed_cause": f"The first input type must be list or tuple, while type is [{type(args[0])}]"}
            raise RuntimeError(dict_args, get_error_message(dict_args))

        raw_tensor_list = args[0]
        axis = args[1]
        keepdims = args[2]

        _check_tensor(raw_tensor_list)

        temp_tensor_list = []
        for raw_tensor in raw_tensor_list:
            temp_tensor = _deal_tensor_dtype(raw_tensor, supported_types)
            temp_tensor_list.append(temp_tensor)

        return func(temp_tensor_list, axis, keepdims)

    return func(*args, **kwargs)


@source_info_decorator()
@_auto_cast_of_tuple_reduce
def tuple_sum(input_tensor_list, axis, keepdims=False):
    """
    calculate sum of raw_tensor, only support float16
    Parameters
    ----------
    input_tensor_list : wrapped_tensor or tvm.tensor list that each tensor has same reduce operation
    axis : int or list
        reduce axis (range : [-len(raw_tensor.shape), len(raw_tensor.shape) - 1])
    keepdims : if true, retains reduced dimensions with length 1, default value is None
    Returns
    -------
    res : wrapped_tensor
    """
    warnings.warn("tuple_sum is deprecated, please replace it with the func sum",
                  DeprecationWarning)
    return _tuple_reduce_op(input_tensor_list, axis, "tuple_reduce_sum",
                            keepdims)


def _tuple_reduce_op(input_tensor_list, axis, in_op, keepdims=False):
    """
    factory method of tuple reduce operations
    keepdims : if true, retains reduced dimensions with length 1, default value is None
    """
    if axis is None:
        dict_args = {"errCode": "E90001", "detailed_cause": "The axis is None!"}
        raise RuntimeError(dict_args, get_error_message(dict_args))

    check_input_tensor_shape(input_tensor_list[0])

    if axis in ((), []):
        res = []
        for tensor in input_tensor_list:
            temp_res = vmuls(tensor, tvm.const(1, dtype=tensor.dtype))
            res.append(temp_res)
        return res

    def __tuple_reduce_compute(data_shape, axis, tensor_list, func):
        def compute_func(*indice):
            """
            compute_func
            """
            count_indice = 0
            count_reduce = 0
            res_indice = []
            for index in range(len(data_shape)):
                if index not in axis:
                    res_indice.append(indice[count_indice])
                    count_indice += 1
                else:
                    res_indice.append(reduce_axises[count_reduce])
                    count_reduce += 1
                    if keepdims:
                        count_indice += 1

            return func(
                (tensor_list[0](*res_indice), tensor_list[1](*res_indice)),
                axis=reduce_axises)

        reduce_axises = []
        for index, axis_num in enumerate(axis):
            reduce_axises.append(
                tvm.reduce_axis((0, data_shape[axis_num]),
                                name='k' + str(index + 1)))
        res_reshape = []
        for index, shape_l in enumerate(data_shape):
            if index not in axis:
                res_reshape.append(shape_l)
            else:
                if keepdims:
                    res_reshape.append(1)

        # all axis reduce, the dim is 1
        if not res_reshape:
            res_reshape.append(1)

        name = "reduce_" + str(NAME_INDEX[0])
        NAME_INDEX[0] += 1

        reduce_res = tvm.compute(res_reshape, compute_func, name=name)
        return reduce_res

    tuple_sum_func = tvm.comm_reducer(lambda x, y: (x[0] + y[0], x[1] + y[1]),
                                      lambda t0, t1: (tvm.const(0, dtype=t0),
                                                      tvm.const(0, dtype=t1)),
                                      name="tuple_sum")

    if in_op.lower() == "tuple_reduce_sum":
        reduce_func = tuple_sum_func
    else:
        dict_args = {"errCode": "E90003",
                     "detailed_cause": f"Not Support yet for op [{in_op}], in_op must be tuple_reduce_sum"}
        raise RuntimeError(dict_args, get_error_message(dict_args))

    op_tensor = input_tensor_list[0]
    shape = shape_to_list(op_tensor.shape)
    res_axis = refine_axis(axis, shape)
    for i in res_axis:
        is_last_axis = (i == (len(shape) - 1))
        if is_last_axis:
            break

    with tvm.tag_scope(in_op.lower()):
        res = __tuple_reduce_compute(shape, res_axis, input_tensor_list,
                                     reduce_func)

    return res
