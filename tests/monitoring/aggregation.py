import numpy
import theano.tensor

from blocks import bricks
from blocks.bricks import application, VariableRole
from blocks.graph import ComputationGraph
from blocks.monitoring.aggregation import (DatasetEvaluator, mean,
                                           MinibatchEvaluator)


class TestBrick(bricks.Brick):
    def __init__(self, **kwargs):
        super(TestBrick, self).__init__(**kwargs)

    def _allocate(self):
        self.params = [theano.shared(0, 'V')]

    @application(inputs=['input_'], outputs=['output'])
    def apply(self, input_, application_call):
        V = self.params[0]

        application_call.add_monitor((V ** 2).sum(),
                                     name='V_mon')

        mean_input = mean(input_.sum(), input_.shape.prod())
        application_call.add_monitor(mean_input, name='mean_input')

        application_call.add_monitor(input_.mean(),
                                     name='per_batch_mean_input')

        return input_ + V


def test_param_monitor():
    X = theano.tensor.vector('X')
    brick = TestBrick(name='test_brick')
    Y = brick.apply(X)
    graph = ComputationGraph([Y])

    V_monitors = [v for v in graph.variables
                  if v.name == 'V_mon']
    validator = DatasetEvaluator({v.name: v for v in V_monitors})

    V_vals = validator.evaluate(None)
    assert V_vals['V_mon'] == 0


def test_dataset_evaluators():
    X = theano.tensor.vector('X')
    brick = TestBrick(name='test_brick')
    Y = brick.apply(X)
    graph = ComputationGraph([Y])
    V_monitors = [v for v in graph.variables
                  if getattr(v.tag, 'role', None) == VariableRole.MONITOR]
    validator = DatasetEvaluator({v.name: v for v in V_monitors})

    full_set = numpy.arange(100.0, dtype='float32')
    batches = numpy.split(full_set, numpy.cumsum(numpy.arange(6) + 1))
    batches = [{'X': b} for b in batches]

    V_vals = validator.evaluate(batches)
    assert V_vals['V_mon'] == 0
    numpy.testing.assert_allclose(V_vals['mean_input'], full_set.mean())
    per_batch_mean = numpy.mean([b['X'].mean() for b in batches])
    numpy.testing.assert_allclose(V_vals['per_batch_mean_input'],
                                  per_batch_mean)


def test_minibatch_evaluators():
    X = theano.tensor.vector('X')
    brick = TestBrick(name='test_brick')
    Y = brick.apply(X)
    graph = ComputationGraph([Y])
    V_monitors = [v for v in graph.variables
                  if getattr(v.tag, 'role', None) == VariableRole.MONITOR]

    train_monitor = MinibatchEvaluator({v.name: v for v in V_monitors})

    full_set = numpy.arange(100.0, dtype='float32')
    batches = numpy.split(full_set, numpy.cumsum(numpy.arange(6) + 1))
    batches = [{'X': b} for b in batches]

    train_fun = theano.function([X], [Y],
                                updates=train_monitor.updates)

    for b in batches:
        train_fun(**b)
        M_vals = train_monitor.read_expressions()
        assert M_vals['V_mon'] == 0
        numpy.testing.assert_allclose(M_vals['mean_input'], b['X'].mean())
        numpy.testing.assert_allclose(M_vals['per_batch_mean_input'],
                                      b['X'].mean())