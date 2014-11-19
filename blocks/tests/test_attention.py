import numpy

import theano
from theano import tensor

from blocks.attention import SequenceContentAttention

floatX = theano.config.floatX

def test_sequence_content_attention():
    seq_len = 5
    batch_size = 6
    state_dim = 2
    sequence_dim = 3
    match_dim = 4

    attention = SequenceContentAttention(
        state_names=["states"], state_dims={"states" : state_dim},
        sequence_dim=sequence_dim, match_dim=match_dim)
    attention.allocate()

    sequences = tensor.tensor3('sequences')
    states = tensor.matrix('states')
    weights = attention.take_look(sequences, states=states)
    assert weights.ndim == 2
    assert weights.dtype == floatX

    seq_values = numpy.zeros((seq_len, batch_size, sequence_dim), dtype=floatX)
    states_values = numpy.zeros((batch_size, state_dim), dtype=floatX)
    weight_values = theano.function([sequences, states], [weights])(
        seq_values, states_values)[0]
    assert weight_values.shape == (seq_len, batch_size)
    assert numpy.all(weight_values >= 0)
    assert numpy.all(weight_values <= 1)

