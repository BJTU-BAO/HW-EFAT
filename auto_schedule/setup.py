#!/usr/bin/env python
# -*- coding:utf-8 -*-
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
Setup TBE package.
"""
from __future__ import absolute_import

from setuptools import find_packages
from setuptools.dist import Distribution
from setuptools import setup


class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True

    def is_pure(self):
        return False


setup_kwargs = {
    "include_package_data": True,
    "data_files": [('', ['LICENSE']),]
}

setup(name='te',
      version='0.4.0',
      description="TVM: An End to End Tensor IR/DSL Stack for Deep Learning Systems",
      zip_safe=False,
      install_requires=[
        'numpy',
        'decorator',
        'attrs',
        'psutil',
      ],
      packages=find_packages(),
      package_data={'tbe': ['common/utils/errormgr/errormanager.json']},
      distclass=BinaryDistribution,
      url='https://github.com/apache/incubator-tvm',
      **setup_kwargs)
