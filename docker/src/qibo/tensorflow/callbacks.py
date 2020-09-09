import numpy as np
import tensorflow as tf
from qibo.config import DTYPES, EIGVAL_CUTOFF
from typing import List, Optional, Union


class Callback:
    """Base callback class.

    All Tensorflow callbacks should inherit this class and implement its
    `__call__` method.

    Results of a callback can be accessed by indexing the corresponding object.
    """

    def __init__(self):
        self._results = []
        self._nqubits = None

    @property
    def nqubits(self) -> int:
        """Total number of qubits in the circuit that the callback was added in."""
        return self._nqubits

    @nqubits.setter
    def nqubits(self, n: int):
        self._nqubits = n

    def __getitem__(self, k) -> tf.Tensor:
        if isinstance(k, int):
            if k > len(self._results):
                raise IndexError("Attempting to access callbacks {} run but "
                                 "the callback has been used in {} executions."
                                 "".format(k, len(self._results)))
            return self._results[k]
        if isinstance(k, slice) or isinstance(k, list) or isinstance(k, tuple):
            return tf.stack(self._results[k])
        raise IndexError("Unrecognized type for index {}.".format(k))

    def __call__(self, state: tf.Tensor) -> tf.Tensor:
        raise NotImplementedError

    def append(self, result: tf.Tensor):
        self._results.append(result)

    def extend(self, result: tf.Tensor):
        self._results.extend(result)


class PartialTrace(Callback):
    """Calculates reduced density matrix of a state.

    This is used by the :class:`qibo.tensorflow.callbacks.EntanglementEntropy`
    callback. It can also be used as a standalone callback in order to access
    a reduced density matrix in the middle of a circuit execution.

    Args:
        partition (list): List with qubit ids that defines the first subsystem.
            If `partition` is not given then the first subsystem is the first
            half of the qubits.
    """

    def __init__(self, partition: Optional[List[int]] = None):
        super(PartialTrace, self).__init__()
        self.partition = partition
        self.rho_dim = None
        self._traceout = None

    @property
    def nqubits(self) -> int:
        return self._nqubits

    @nqubits.setter
    def nqubits(self, n: int):
        self._nqubits = n
        if self.partition is None:
            self.partition = list(range(n // 2 + n % 2))

        if len(self.partition) < n // 2:
            # Revert parition so that we diagonalize a smaller matrix
            self.partition = [i for i in range(n)
                              if i not in set(self.partition)]
        self.rho_dim = 2 ** (n - len(self.partition))
        self._traceout = None

    @property
    def _traceout_str(self):
        """Einsum string used to trace out when state is density matrix."""
        if self._traceout is None:
            from qibo.tensorflow.einsum import DefaultEinsum
            partition = set(self.partition)
            self._traceout = DefaultEinsum.partialtrace_str(partition, self.nqubits)
        return self._traceout

    def __call__(self, state: tf.Tensor, is_density_matrix: bool = False
                 ) -> tf.Tensor:
        """Calculates reduced density matrix.

        Traces out all qubits contained in `self.partition`.
        """
        # Cast state in the proper shape
        if not (isinstance(state, np.ndarray) or isinstance(state, tf.Tensor)):
            raise TypeError("State of unknown type {} was given in callback "
                            "calculation.".format(type(state)))
        if self._nqubits is None:
            self.nqubits = int(np.log2(tuple(state.shape)[0]))

        shape = (1 + int(is_density_matrix)) * self.nqubits * (2,)
        state = tf.reshape(state, shape)

        if is_density_matrix:
            rho = tf.einsum(self._traceout_str, state)
        else:
            rho = tf.tensordot(state, tf.math.conj(state),
                               axes=[self.partition, self.partition])
        return tf.reshape(rho, (self.rho_dim, self.rho_dim))


class EntanglementEntropy(PartialTrace):
    """Von Neumann entanglement entropy callback.

    Args:
        partition (list): List with qubit ids that defines the first subsystem
            for the entropy calculation.
            If `partition` is not given then the first subsystem is the first
            half of the qubits.

    Example:
        ::

            from qibo import models, gates, callbacks
            # create entropy callback where qubit 0 is the first subsystem
            entropy = callbacks.EntanglementEntropy([0])
            # initialize circuit with 2 qubits and add gates
            c = models.Circuit(2)
            # add callback gates between normal gates
            c.add(gates.CallbackGate(entropy))
            c.add(gates.H(0))
            c.add(gates.CallbackGate(entropy))
            c.add(gates.CNOT(0, 1))
            c.add(gates.CallbackGate(entropy))
            # execute the circuit
            final_state = c()
            print(entropy[:])
            # Should print [0, 0, 1] which is the entanglement entropy
            # after every gate in the calculation.
    """
    _log2 = tf.cast(tf.math.log(2.0), dtype=DTYPES.get('DTYPE'))

    def __init__(self, partition: Optional[List[int]] = None):
        super(EntanglementEntropy, self).__init__()
        self.partition = partition
        self.rho_dim = None
        self._traceout = None

    @classmethod
    def _entropy(cls, rho: tf.Tensor) -> tf.Tensor:
      """Calculates entropy by diagonalizing the density matrix."""
      # Diagonalize
      eigvals = tf.math.real(tf.linalg.eigvalsh(rho))
      # Treating zero and negative eigenvalues
      masked_eigvals = tf.gather(eigvals, tf.where(eigvals > EIGVAL_CUTOFF))[:, 0]
      entropy = - tf.reduce_sum(masked_eigvals * tf.math.log(masked_eigvals))
      return entropy / cls._log2

    def __call__(self, state: tf.Tensor, is_density_matrix: bool = False
                 ) -> tf.Tensor:
        # Construct reduced density matrix
        rho = super(EntanglementEntropy, self).__call__(state, is_density_matrix)
        # Calculate entropy of reduced density matrix
        return self._entropy(rho)