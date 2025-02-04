#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ..adaptor.pytorch import _cfg_to_qconfig, _cfgs_to_fx_cfgs
from ..adaptor.pytorch import _propagate_qconfig, get_torch_version
from . import logger
import torch
from torch.quantization import add_observer_, convert
import torch.quantization as tq
import yaml
import os
import copy

yaml.SafeLoader.add_constructor('tag:yaml.org,2002:python/tuple',
                                 lambda loader, node: tuple(loader.construct_sequence(node)))

def load(checkpoint_dir, model):
    """Execute the quantize process on the specified model.

    Args:
        checkpoint_dir (dir): The folder of checkpoint.
                              'best_configure.yaml' and 'best_model_weights.pt' are needed
                              in This directory. 'checkpoint' dir is under workspace folder
                              and workspace folder is define in configure yaml file.
        model (object): fp32 model need to do quantization.

    Returns:
        (object): quantized model
    """

    tune_cfg_file = os.path.join(os.path.abspath(os.path.expanduser(checkpoint_dir)),
                                 'best_configure.yaml')
    weights_file = os.path.join(os.path.abspath(os.path.expanduser(checkpoint_dir)),
                                'best_model_weights.pt')
    assert os.path.exists(
        tune_cfg_file), "tune configure file %s didn't exist" % tune_cfg_file
    assert os.path.exists(
        weights_file), "weight file %s didn't exist" % weights_file

    with open(tune_cfg_file, 'r') as f:
        tune_cfg = yaml.safe_load(f)

    version = get_torch_version()
    if tune_cfg['approach'] != "post_training_dynamic_quant":
        if version < '1.7':
            q_mapping = tq.default_mappings.DEFAULT_MODULE_MAPPING
        elif version < '1.8':
            q_mapping = \
                tq.quantization_mappings.get_static_quant_module_mappings()
        else:
            q_mapping = \
                tq.quantization_mappings.get_default_static_quant_module_mappings()
    else:
        if version < '1.7':
            q_mapping = \
                tq.default_mappings.DEFAULT_DYNAMIC_MODULE_MAPPING
        elif version < '1.8':
            q_mapping = \
                tq.quantization_mappings.get_dynamic_quant_module_mappings()
        else:
            q_mapping = \
                tq.quantization_mappings.get_default_dynamic_quant_module_mappings()

    if version < '1.7':
        white_list = \
            tq.default_mappings.DEFAULT_DYNAMIC_MODULE_MAPPING \
            if tune_cfg['approach'] == 'post_training_dynamic_quant' else \
            tq.default_mappings.DEFAULT_QCONFIG_PROPAGATE_WHITE_LIST
    elif version < '1.8':
        white_list = \
            tq.quantization_mappings.get_dynamic_quant_module_mappings() \
            if tune_cfg['approach'] == 'post_training_dynamic_quant' else \
            tq.quantization_mappings.get_qconfig_propagation_list()
    else:
        white_list = \
            tq.quantization_mappings.get_default_dynamic_quant_module_mappings() \
            if tune_cfg['approach'] == 'post_training_dynamic_quant' else \
            tq.quantization_mappings.get_default_qconfig_propagation_list()

    if tune_cfg['approach'] == "post_training_dynamic_quant":
        op_cfgs = _cfg_to_qconfig(tune_cfg, tune_cfg['approach'])
    else:
        op_cfgs = _cfg_to_qconfig(tune_cfg)

    try:                         # pragma: no cover
        # For torch.fx approach
        if version >= '1.7':
            q_model = copy.deepcopy(model.eval())
            from torch.quantization.quantize_fx import prepare_fx, convert_fx
            fx_op_cfgs = _cfgs_to_fx_cfgs(op_cfgs, tune_cfg['approach'])
            if version < '1.8':
                q_model = torch._fx.symbolic_trace(q_model)
            q_model = prepare_fx(q_model, fx_op_cfgs)
            q_model = convert_fx(q_model)
            weights = torch.load(weights_file)
            q_model.load_state_dict(weights)
            return q_model
    except Exception as e:      # pragma: no cover
        logger.info("The model can't be convert to fx graph! Just use eager mode!")
        logger.info(str(e))

    q_model = copy.deepcopy(model.eval())
    _propagate_qconfig(q_model, op_cfgs, white_list=white_list, approach=tune_cfg['approach'])
    # sanity check common API misusage
    if not any(hasattr(m, 'qconfig') and m.qconfig for m in q_model.modules()):
        logger.warn("None of the submodule got qconfig applied. Make sure you "
                    "passed correct configuration through `qconfig_dict` or "
                    "by assigning the `.qconfig` attribute directly on submodules")
    if tune_cfg['approach'] != "post_training_dynamic_quant":
        add_observer_(q_model)
    q_model = convert(q_model, mapping=q_mapping, inplace=True)
    weights = torch.load(weights_file)
    q_model.load_state_dict(weights)
    return q_model
