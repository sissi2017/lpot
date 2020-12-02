#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Intel Corporation
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

from abc import abstractmethod
from ilit.utils.utility import LazyImport, singleton
from ..utils import logger
from sklearn.metrics import accuracy_score, f1_score
import numpy as np

torch_ignite = LazyImport('ignite')
torch = LazyImport('torch')
tf = LazyImport('tensorflow')
mx = LazyImport('mxnet')

@singleton
class TensorflowMetrics(object):
    def __init__(self):
        self.metrics = {}
        self.metrics.update(TENSORFLOW_METRICS)

@singleton
class PyTorchMetrics(object):
    def __init__(self):
        self.metrics = {
            "Accuracy": WrapPyTorchMetric(
                torch_ignite.metrics.Accuracy),
            "Loss": WrapPyTorchMetric(
                torch_ignite.metrics.Loss),
            "MeanAbsoluteError": WrapPyTorchMetric(
                torch_ignite.metrics.MeanAbsoluteError),
            "MeanPairwiseDistance": WrapPyTorchMetric(
                torch_ignite.metrics.MeanPairwiseDistance),
            "MeanSquaredError": WrapPyTorchMetric(
                torch_ignite.metrics.MeanSquaredError),
            # "TopKCategoricalAccuracy":WrapPyTorchMetric(
            #     torch_ignite.metrics.TopKCategoricalAccuracy),
            "topk": WrapPyTorchMetric(
                torch_ignite.metrics.TopKCategoricalAccuracy),
            "Average": WrapPyTorchMetric(
                torch_ignite.metrics.Average, True),
            "GeometricAverage": WrapPyTorchMetric(
                torch_ignite.metrics.GeometricAverage, True),
            "ConfusionMatrix": WrapPyTorchMetric(
                torch_ignite.metrics.ConfusionMatrix),
            # IoU and mIoU are funtions, while call the function it return a MetricsLambda class
            "IoU": WrapPyTorchMetric(
                torch_ignite.metrics.IoU),
            "mIoU": WrapPyTorchMetric(
                torch_ignite.metrics.mIoU),
            "DiceCoefficient": WrapPyTorchMetric(
                torch_ignite.metrics.DiceCoefficient),

            "MetricsLambda": WrapPyTorchMetric(
                torch_ignite.metrics.MetricsLambda),
            "EpochMetric": WrapPyTorchMetric(
                torch_ignite.metrics.EpochMetric),
            "Fbeta": WrapPyTorchMetric(
                torch_ignite.metrics.Fbeta),
            "Precision": WrapPyTorchMetric(
                torch_ignite.metrics.Precision),
            "Recall": WrapPyTorchMetric(
                torch_ignite.metrics.Recall),
            "RootMeanSquaredError": WrapPyTorchMetric(
                torch_ignite.metrics.RootMeanSquaredError),
            "RunningAverage": WrapPyTorchMetric(
                torch_ignite.metrics.RunningAverage),
            "VariableAccumulation": WrapPyTorchMetric(
                torch_ignite.metrics.VariableAccumulation),
            "Frequency": WrapPyTorchMetric(
                torch_ignite.metrics.Frequency, True),
        }
        self.metrics.update(PYTORCH_METRICS)

@singleton
class MXNetMetrics(object):
    def __init__(self):
        self.metrics = {
            "Accuracy": WrapMXNetMetric(mx.metric.Accuracy),
            "TopKAccuracy": WrapMXNetMetric(mx.metric.TopKAccuracy),
            "F1": WrapMXNetMetric(mx.metric.F1),
            # "Fbeta":WrapMXNetMetric(mx.metric.Fbeta),
            # "BinaryAccuracy":WrapMXNetMetric(mx.metric.BinaryAccuracy),
            "MCC": WrapMXNetMetric(mx.metric.MCC),
            "MAE": WrapMXNetMetric(mx.metric.MAE),
            "MSE": WrapMXNetMetric(mx.metric.MSE),
            "RMSE": WrapMXNetMetric(mx.metric.RMSE),
            # "MeanPairwiseDistance":WrapMXNetMetric(mx.metric.MeanPairwiseDistance),
            # "MeanCosineSimilarity":WrapMXNetMetric(mx.metric.MeanCosineSimilarity),
            "CrossEntropy": WrapMXNetMetric(mx.metric.CrossEntropy),
            "Perplexity": WrapMXNetMetric(mx.metric.Perplexity),
            "NegativeLogLikelihood": WrapMXNetMetric(mx.metric.NegativeLogLikelihood),
            "PearsonCorrelation": WrapMXNetMetric(mx.metric.PearsonCorrelation),
            "PCC": WrapMXNetMetric(mx.metric.PCC),
            "Loss": WrapMXNetMetric(mx.metric.Loss),
        }
        self.metrics.update(MXNET_METRICS)


framework_metrics = {"tensorflow": TensorflowMetrics,
                     "mxnet": MXNetMetrics,
                     "pytorch": PyTorchMetrics, }

# user/model specific metrics will be registered here
TENSORFLOW_METRICS = {}
MXNET_METRICS = {}
PYTORCH_METRICS = {}

registry_metrics = {"tensorflow": TENSORFLOW_METRICS,
                    "mxnet": MXNET_METRICS,
                    "pytorch": PYTORCH_METRICS, }


class METRICS(object):
    def __init__(self, framework):
        assert framework in ("tensorflow", "pytorch",
                             "mxnet"), "framework support tensorflow pytorch mxnet"
        self.metrics = framework_metrics[framework]().metrics

    def __getitem__(self, metric_type):
        assert metric_type in self.metrics.keys(), "only support metrics in {}".\
            format(self.metrics.keys())

        return self.metrics[metric_type]

    def register(self, name, metric_cls):
        assert name not in self.metrics.keys(), 'registered metric name already exists.'
        self.metrics.update({name: metric_cls})


def metric_registry(metric_type, framework):
    """The class decorator used to register all Metric subclasses.
       cross framework metric is supported by add param as framework='tensorflow, pytorch, mxnet'

    Args:
        cls (class): The class of register.

    Returns:
        cls: The class of register.
    """
    def decorator_metric(cls):
        for single_framework in [fwk.strip() for fwk in framework.split(',')]:
            assert single_framework in [
                "tensorflow",
                "mxnet",
                "pytorch"], "The framework support tensorflow mxnet pytorch"

            if metric_type in registry_metrics[single_framework].keys():
                raise ValueError('Cannot have two metrics with the same name')
            registry_metrics[single_framework][metric_type] = cls
        return cls
    return decorator_metric


class Metric(object):
    def __init__(self, metric, single_output=False):
        self._metric_cls = metric
        self._single_output = single_output

    def __call__(self, *args, **kwargs):
        self._metric = self._metric_cls(*args, **kwargs)
        return self

    @abstractmethod
    def update(self, preds, labels=None, sample_weight=None):
        raise NotImplementedError

    @abstractmethod
    def reset(self):
        raise NotImplementedError

    @abstractmethod
    def result(self):
        raise NotImplementedError

    @property
    def metric(self):
        return self._metric

class WrapPyTorchMetric(Metric):

    def update(self, preds, labels=None, sample_weight=None):
        if self._single_output:
            output = torch.as_tensor(preds)
        else:
            output = (torch.as_tensor(preds), torch.as_tensor(labels))
        self._metric.update(output)

    def reset(self):
        self._metric.reset()

    def result(self):
        return self._metric.compute()


class WrapMXNetMetric(Metric):

    def update(self, preds, labels=None, sample_weight=None):
        preds = mx.nd.array(preds)
        labels = mx.nd.array(labels)
        self._metric.update(labels=labels, preds=preds)

    def reset(self):
        self._metric.reset()

    def result(self):
        acc_name, acc = self._metric.get()
        return acc

def _topk_shape_validate(preds, labels):
    # preds shape can be Nxclass_num or class_num(N=1 by default)
    # it's more suitable for 'Accuracy' with preds shape Nx1(or 1) output from argmax
    preds = np.array(preds)

    # consider labels just int value 1x1
    if isinstance(labels, int):
        labels = [labels]
    # labels most have 2 axis, 2 cases: N(or Nx1 sparse) or Nxclass_num(one-hot)
    # only support 2 dimension one-shot labels
    # or 1 dimension one-hot class_num will confuse with N
    labels = np.array(labels)

    if len(preds.shape) == 1:
        N = 1
        class_num = preds.shape[0]
        preds = preds.reshape([-1, class_num])
    elif len(preds.shape) >= 2:
        N = preds.shape[0]
        preds = preds.reshape([N, -1])
        class_num = preds.shape[1]
    
    label_N = labels.shape[0]
    assert label_N == N, 'labels batch size should same with preds'
    labels = labels.reshape([N, -1])
    # one-hot labels will have 2 dimension not equal 1
    if labels.shape[1] != 1:
        labels = labels.argsort()[..., -1:]
    return preds, labels

@metric_registry('topk', 'mxnet')
class MxnetTopK(Metric):
    """The class of calculating topk metric, which usually is used in classification.

    Args:
        topk (dict): The dict of topk for configuration.

    """

    def __init__(self, k=1):
        self.k = k
        self.num_correct = 0
        self.num_sample = 0

    def update(self, preds, labels, sample_weight=None):
 
        preds, labels = _topk_shape_validate(preds, labels)
        preds = preds.argsort()[..., -self.k:]
        if self.k == 1:
            correct = accuracy_score(preds, labels, normalize=False)
            self.num_correct += correct

        else:
            for p, l in zip(preds, labels):
                # get top-k labels with np.argpartition
                # p = np.argpartition(p, -self.k)[-self.k:]
                l = l.astype('int32')
                if l in p:
                    self.num_correct += 1

        self.num_sample += len(labels) 

    def reset(self):
        self.num_correct = 0
        self.num_sample = 0

    def result(self):
        if self.num_sample == 0:
            logger.warning("sample num is 0 can't calculate topk")
            return 0
        else:
            return self.num_correct / self.num_sample

@metric_registry('topk', 'tensorflow')
class TensorflowTopK(Metric):
    """The class of calculating topk metric, which usually is used in classification.

    Args:
        topk (dict): The dict of topk for configuration.

    """

    def __init__(self, k=1):
        self.k = k
        self.num_correct = 0
        self.num_sample = 0

    def update(self, preds, labels, sample_weight=None):
 
        preds, labels = _topk_shape_validate(preds, labels)

        labels = labels.reshape([len(labels)])
        with tf.Graph().as_default() as acc_graph:
          topk = tf.nn.in_top_k(predictions=tf.constant(preds, dtype=tf.float32),
                                targets=tf.constant(labels, dtype=tf.int32), k=self.k)
          fp32_topk = tf.cast(topk, tf.float32)
          correct_tensor = tf.reduce_sum(input_tensor=fp32_topk)

          with tf.compat.v1.Session() as acc_sess:
            correct  = acc_sess.run(correct_tensor)

        self.num_sample += len(labels)
        self.num_correct += correct

    def reset(self):
        self.num_correct = 0
        self.num_sample = 0

    def result(self):
        if self.num_sample == 0:
            logger.warning("sample num is 0 can't calculate topk")
            return 0
        else:
            return self.num_correct / self.num_sample

@metric_registry('COCOmAP', 'tensorflow')
class TensorflowCOCOMAP(Metric):
    """The class of calculating mAP metric

    """
    def __init__(self):
        import ilit.metric.coco_label_map as coco_label_map
        self.image_ids = []
        self.ground_truth_list = []
        self.detection_list = []
        self.annotation_id = 1
        self.category_map = coco_label_map.category_map
        self.category_id_set = set(
            [cat for cat in self.category_map])

    def update(self, detection, labels, sample_weight=None):
        from ilit.metric.coco_tools import ExportSingleImageGroundtruthToCoco,\
            ExportSingleImageDetectionBoxesToCoco
        image_id = labels[1]
        ground_truth = labels[0]
        if image_id in self.image_ids:
            return
        self.image_ids.append(image_id)
        self.ground_truth_list.extend(
            ExportSingleImageGroundtruthToCoco(
                image_id=image_id,
                next_annotation_id=self.annotation_id,
                category_id_set=self.category_id_set,
                groundtruth_boxes=ground_truth['boxes'],
                groundtruth_classes=ground_truth['classes']))
        self.annotation_id += ground_truth['boxes'].shape[0]
        
        self.detection_list.extend(
            ExportSingleImageDetectionBoxesToCoco(
                image_id=image_id,
                category_id_set=self.category_id_set,
                detection_boxes=detection['boxes'],
                detection_scores=detection['scores'],
                detection_classes=detection['classes']))

    def reset(self):
        self.image_ids = []
        self.ground_truth_list = []
        self.detection_list = []
        self.annotation_id = 1

    def result(self):
        from ilit.metric.coco_tools import COCOWrapper, COCOEvalWrapper
        if len(self.ground_truth_list) == 0:
            logger.warning("sample num is 0 can't calculate mAP") 
            return 0
        else:
            groundtruth_dict = {
                'annotations':
                self.ground_truth_list,
                'images': [{
                    'id': image_id
                } for image_id in self.image_ids],
                'categories': [{
                    'id': k,
                    'name': v
                } for k, v in self.category_map.items()]
            }
            coco_wrapped_groundtruth = COCOWrapper(groundtruth_dict)
            coco_wrapped_detections = coco_wrapped_groundtruth.LoadAnnotations(
                self.detection_list)
            box_evaluator = COCOEvalWrapper(coco_wrapped_groundtruth,
                                                 coco_wrapped_detections,
                                                 agnostic_mode=False)
            box_metrics, box_per_category_ap = box_evaluator.ComputeMetrics(
                include_metrics_per_category=False, all_metrics_per_category=False)
            box_metrics.update(box_per_category_ap)
            box_metrics = {
                'DetectionBoxes_' + key: value
                for key, value in iter(box_metrics.items())
            }

            return box_metrics['DetectionBoxes_Precision/mAP']

