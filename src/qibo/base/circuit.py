# -*- coding: utf-8 -*-
# @authors: S. Carrazza and A. Garcia
from abc import ABCMeta, abstractmethod
from typing import Tuple


class BaseCircuit(object):
    """This class implements the circuit object which holds all gates.

    Args:
        nqubits (int): number of quantum bits.

    Example:
        ::

            from qibo.models import Circuit
            c = Circuit(3) # initialized circuit with 3 qubits
    """

    __metaclass__ = ABCMeta

    def __init__(self, nqubits):
        """Initialize properties."""
        self.nqubits = nqubits
        self.queue = []
        # Flag to keep track if the circuit was executed
        # We do not allow adding gates in an executed circuit
        self.is_executed = False

        self.measurement_sets = dict()
        self.measurement_gate = None
        self.measurement_gate_result = None

    def __add__(self, circuit):
        """Add circuits.

        Args:
            circuit: Circuit to be added to the current one.
        Return:
            The resulting circuit from the addition.
        """
        return BaseCircuit._circuit_addition(self, circuit)

    @classmethod
    def _circuit_addition(cls, c1, c2):
        if c1.nqubits != c2.nqubits:
            raise ValueError("Cannot add circuits with different number of "
                             "qubits. The first has {} qubits while the "
                             "second has {}".format(c1.nqubits, c2.nqubits))
        newcircuit = cls(c1.nqubits)
        for gate in c1.queue:
            newcircuit.add(gate)
        for gate in c2.queue:
            newcircuit.add(gate)
        return newcircuit

    def _check_measured(self, gate_qubits: Tuple[int]):
        """Helper method for `add`.

        Checks if the qubits that a gate acts are already measured and raises
        a `NotImplementedError` if they are because currently we do not allow
        measured qubits to be reused.
        """
        for qubit in gate_qubits:
            if (self.measurement_gate is not None and
                qubit in self.measurement_gate.target_qubits):
                raise ValueError("Cannot reuse qubit {} because it is already "
                                 "measured".format(qubit))

    def add(self, gate):
        """Add a gate to a given queue.

        Args:
            gate (qibo.gates): the specific gate (see :ref:`Gates`).
        """
        if self._final_state is not None:
            raise RuntimeError("Cannot add gates to a circuit after it is "
                               "executed.")

        # Set number of qubits in gate
        if gate._nqubits is None:
            gate.nqubits = self.nqubits
        elif gate.nqubits != self.nqubits:
            raise ValueError("Attempting to add gate with {} total qubits to "
                             "a circuit with {} qubits."
                             "".format(gate.nqubits, self.nqubits))

        self._check_measured(gate.qubits)
        if gate.name == "measure":
            self.add_measurement(gate)
        else:
            self.queue.append(gate)

    def add_measurement(self, gate):
        """Gets called automatically by `add` when `gate` is measurement.

        This is because measurement gates (`gates.M`) are treated differently
        than all other gates.
        The user is not supposed to use the `add_measurement` method.
        """
        # Set register's name and log the set of qubits in `self.measurement_sets`
        name = gate.register_name
        if name is None:
            name = "Register{}".format(len(self.measurement_sets))
            gate.register_name = name
        elif name in self.measurement_sets:
            raise KeyError("Register name {} has already been used."
                           "".format(name))
        self.measurement_sets[name] = gate.target_qubits

        # Update circuit's global measurement gate
        if self.measurement_gate is None:
            self.measurement_gate = gate
        else:
            self.measurement_gate.add(gate.target_qubits)

    @property
    def size(self) -> int:
        """
        Return:
            number of qubits in the circuit
        """
        return self.nqubits

    @property
    def depth(self) -> int:
        """
        Return:
            number of gates/operations in the circuit
        """
        return len(self.queue)

    @abstractmethod
    def execute(self):
        """Executes the circuit on a given backend.

        Args:
            model: (qibo.models.Circuit): The circuit to be executed.
        Returns:
            The final wave function.
        """
        raise NotImplementedError
