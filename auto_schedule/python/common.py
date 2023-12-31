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
common
"""
from __future__ import absolute_import
import warnings
from te import tvm
from te import platform as cceconf
from te.platform import intrinsic_check_support
from te.utils.error_manager.error_manager_util import get_error_message
import te.platform.cce_params as cce_params
from tbe.common.testing.dsl_source_info import source_info_decorator
from .elewise_compute import vadds
from .elewise_compute import vmuls
from .elewise_compute import vmax
from .elewise_compute import vmin
from .elewise_compute import vabs
from .elewise_compute import vmul
from .elewise_compute import vrec
from .broadcast_compute import broadcast
from .cast_compute import round_half_up
from ..api import round_to
from ..api import cast_to
from .util import check_input_tensor_shape
from .util import DTYPE_MAP


_BLOCK_SIZE = cce_params.BLOCK_REDUCE
_BLOCK_INT8_SIZE = cce_params.BLOCK_REDUCE_INT8


@source_info_decorator()
def cast_to_round(data, dtype):
    """
    Parameters
    ----------
    data : tvm.tensor
        tensors need to change dtype

    dtype : string
        dst dtype need to cast to

    Returns
    -------
    tensor : tvm.tensor
    """
    warnings.warn("cast_to_round is deprecated, please replace it with the func round_half_up and cast_to",
                  DeprecationWarning)
    dtype = dtype.lower()
    if dtype != "int32":
        dict_args = {"errCode": "E90001",
                     "detailed_cause": f"The cast output dtype must be int32, while is [{dtype}]"}
        raise RuntimeError(dict_args, get_error_message(dict_args))

    src_dtype = data.dtype.lower()
    cast_type = DTYPE_MAP[src_dtype] + "2s32a"
    is_support_round_d = intrinsic_check_support("Intrinsic_vconv", cast_type)
    if not is_support_round_d:
        return cast_to(data, dtype)

    return round_half_up(data)


# 'pylint: disable=too-many-arguments
def img2col(input_img,
            col_shape,
            filter_h,
            filter_w,
            pad,
            stride,
            tag=None,
            padding_value=0.0):
    """
    img2col
    """
    warnings.warn(
        "te.lang.cce.te_compute.common.img2col is deprecated, please replace it with tbe.dsl.compute.common.img2col",
        DeprecationWarning)
    from tbe.dsl.compute.common import img2col
    return img2col(input_img, col_shape, filter_h, filter_w, pad, stride, tag, padding_value)


# 'pylint: disable=too-many-arguments
def im2col_6d(input_img,
              col_shape,
              filter_h,
              filter_w,
              pad,
              stride,
              padding_value=0.0,
              dilation=[1, 1]):
    """
    im2col_6d
    """
    # 'pylint: disable=too-many-locals
    warnings.warn("te.lang.cce.te_compute.common.im2col_6d is deprecated, "
                  "please replace it with the func tbe.dsl.compute.common.im2col_6d",
                  DeprecationWarning)
    from tbe.dsl.compute.common import im2col_6d
    return im2col_6d(input_img, col_shape, filter_h, filter_w, pad, stride, padding_value, dilation)


def im2col_fractal(a_im2col_shape, in_a, dst='ca', tag=None):
    """
    im2col_fractal
    """
    warnings.warn(
        "te.lang.cce.te_compute.common.im2col_fractal is deprecated, "
        "please replace it with tbe.dsl.compute.common.im2col_fractal",
        DeprecationWarning)
    from tbe.dsl.compute.common import im2col_fractal
    return im2col_fractal(a_im2col_shape, in_a, dst, tag)


def im2col_fractal_6d(a_im2col_shape, in_a):
    """
    im2col_fractal_6d
    """
    last_dim = in_a.shape[-1]

    # 'pylint: disable=too-many-locals
    warnings.warn("te.lang.cce.te_compute.common.im2col_fractal_6d is deprecated, "
                  "please replace it with the func tbe.dsl.compute.common.im2col_fractal_6d",
                  DeprecationWarning)
    from tbe.dsl.compute.common import im2col_fractal_6d
    return im2col_fractal_6d(a_im2col_shape, in_a)


def mad(mad_shape, in_a, in_b, res_type, offset_x=0, v200_flag=False):
    """
    mad
    """
    if res_type in ('int32', 'uint32'):
        r_k0 = tvm.reduce_axis((0, _BLOCK_INT8_SIZE), name='k0')
    else:
        r_k0 = tvm.reduce_axis((0, _BLOCK_SIZE), name='k0')
    r_k1 = tvm.reduce_axis((0, in_b.shape[1]), name='k1')
    # If tag set to 'gemv', computeOp return tensor of specific layout.
    # e.g. gemv of 1x32, tensor C is 1x32 but occupy 16x32 fractal matrix size.
    # gemv of 2x32 also occupy 16x32.
    if res_type == "float16":
        crmode = 'f162f16'
    else:
        crmode = 'f162f32'
    offset_x = offset_x if v200_flag else 0
    return tvm.compute(
        mad_shape,
        lambda n, cg, j1, i, j0: tvm.sum((in_a[
            n, cg, i // _BLOCK_SIZE, r_k1, i % _BLOCK_SIZE, r_k0] - offset_x).astype(
                res_type) * in_b[cg, r_k1, j1, j0, r_k0].astype(res_type),
                                         axis=[r_k1, r_k0]),
        name='mad',
        tag='gemm',
        attrs={'mode': crmode})


# 'pylint: disable=invalid-name
def tf_get_windowed_output_size(input_size, filter_size, stride, padding_type):
    """
    get output and padding size using tensorflow padding rule

    Parameters
    ----------
    input_size : int, feature map size

    filter_size : int, filter size

    stride: int, stride size

    padding_type: string, support "SAME", "VALID" or "EXPLICIT"

    Returns
    -------
    output_size: int, output feature map size

    padding_size: int, feature map padding size
    """
    if padding_type == 'EXPLICIT':
        dict_args = {"errCode": "E90001",
                     "detailed_cause": "tf_get_windowed_output_size does not handle EXPLITCIT padding; "
                                       "call tf_get_windowed_output_size_verbose instead."}
        raise RuntimeError(dict_args, get_error_message(dict_args))

    # 'pylint: disable=invalid-name
    output_size, padding_size, _ = tf_get_windowed_output_size_verbose(
        input_size, filter_size, stride, padding_type)

    return output_size, padding_size


# 'pylint: disable=invalid-name
def tf_get_windowed_output_size_verbose(input_size, filter_size, stride,
                                        padding_type):
    """
    get output and padding size using tensorflow padding rule

    Parameters
    ----------
    input_size : int, feature map size

    filter_size : int, filter size

    stride: int, stride size

    padding_type: string, support "SAME", "VALID" or "EXPLICIT"

    Returns
    -------
    output_size: int, output feature map size

    padding_before: int, feature map padding before size

    padding_after: int, feature map padding after size
    """
    dilation_rate = 1

    (output_size, padding_before,
     padding_after) = tf_get_windowed_output_size_verbose_v2(
         input_size, filter_size, dilation_rate, stride, padding_type)

    return output_size, padding_before, padding_after


def tf_get_windowed_output_size_verbose_v2(input_size, filter_size,
                                           dilation_rate, stride,
                                           padding_type):
    """
    get output and padding size using tensorflow padding rule

    Parameters
    ----------
    input_size : int, feature map size

    filter_size : int, filter size

    dilation_rate: int, dilation rate

    stride: int, stride size

    padding_type: string, support "SAME", "VALID" or "EXPLICIT"

    Returns
    -------
    output_size: int, output feature map size

    padding_before: int, feature map padding before size

    padding_after: int, feature map padding after size
    """
    if stride <= 0:
        dict_args = {"errCode": "E90001", "detailed_cause": f"Stride must be > 0, but stride is [{stride}]"}
        raise RuntimeError(dict_args, get_error_message(dict_args))

    if dilation_rate < 1:
        dict_args = {"errCode": "E90001",
                     "detailed_cause": f"dilation_rate must be >= 1, but dilation_rate is [{dilation_rate}]"}
        raise RuntimeError(dict_args, get_error_message(dict_args))

    effective_filter_size = (filter_size - 1) * dilation_rate + 1
    if padding_type == "VALID":
        output_size = (input_size - effective_filter_size + stride) // stride
        padding_before = 0
        padding_after = 0
    elif padding_type == "SAME":
        output_size = (input_size + stride - 1) // stride
        padding_needed = max(0, (output_size - 1) * stride +
                             effective_filter_size - input_size)
        padding_before = padding_needed // 2
        padding_after = padding_needed - padding_before
    else:
        dict_args = {
            "errCode": "E90001",
            "detailed_cause": f"Unsupported padding type [{padding_type}], padding_type must be VALID or SAME"}
        raise RuntimeError(dict_args, get_error_message(dict_args))

    return output_size, padding_before, padding_after


def calculate_one_or_zero(input_tensor, shape, dtype):
    """
    if input_tensor>0, then output is 1, or input_tensor <=0, then output is 0

    Parameters
    ----------
    input_tensor: TVM tensor
        input_tensor tensor
    shape: list or tuple
        the shape of input_tensor
    dtype: tr
        he dtype of input_tensor

    returns
    ----------
    result: TVM tensor
        a tensor all value is 1 or 0
    """
    # define help constant. use help_min*help_rec_one*help_rec_sec to get the
    # result 1
    if dtype == "float32":
        help_min = tvm.const(2**(-126), "float32")
        help_rec_one = tvm.const(2**38, "float32")
        help_rec_sec = tvm.const(2**44, "float32")
    elif dtype == "float16":
        help_min = tvm.const(2**(-24), "float16")
        help_rec_one = tvm.const(2**12, "float16")
        help_rec_sec = help_rec_one
    elif dtype == "int32":
        help_min = tvm.const(1, "int32")
        help_rec_one = help_min
        help_rec_sec = help_min

    # broadcast constant to tensor to do vmul
    help_tensor = broadcast(help_min, shape, dtype)
    help_zero_tensor = broadcast(tvm.const(0, dtype), shape, dtype)
    help_rec_one_tensor = broadcast(help_rec_one, shape, dtype)
    help_rec_sec_tensor = broadcast(help_rec_sec, shape, dtype)

    # process to get tmp_min_y in (input_tensor, help_tensor)
    tmp_min_y = vmin(input_tensor, help_tensor)
    # process to get tmp_max_y in (help_zero_tensor, help_tensor)
    tmp_max_y = vmax(tmp_min_y, help_zero_tensor)
    result_tmp = vmul(tmp_max_y, help_rec_one_tensor)
    if dtype == "float32":
        result_tmp = vmul(result_tmp, help_rec_sec_tensor)
    result = vmul(result_tmp, help_rec_sec_tensor)

    return result
