"""
Define the default circuit, constants and types.
"""
# Logging level from 0 (all) to 3 (errors)
LOG_LEVEL = 3

# Select the default backend engine
BACKEND_NAME = "tensorflow"

# Choose the least significant qubit
LEAST_SIGNIFICANT_QUBIT = 0

if LEAST_SIGNIFICANT_QUBIT != 0: # pragma: no cover
    raise NotImplementedError("The least significant qubit should be 0.")

# Load backend specifics
if BACKEND_NAME == "tensorflow":
    import os
    import warnings

    os.environ["TF_CPP_MIN_LOG_LEVEL"] = str(LOG_LEVEL)
    import numpy as np
    import tensorflow as tf
    # Backend access
    K = tf

    # characters used in einsum strings
    EINSUM_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    # Entanglement entropy eigenvalue cut-off
    # Eigenvalues smaller than this cut-off are ignored in entropy calculation
    EIGVAL_CUTOFF = 1e-14

    # Default types
    DTYPES = {
        'STRING': 'double',
        'DTYPEINT': tf.int64,
        'DTYPE': tf.float64,
        'DTYPECPX': tf.complex128,
        'NPTYPECPX': np.complex128
    }

    # Flag for raising warning in ``set_precision`` and ``set_backend``
    ALLOW_SWITCHERS = True

    # Gate backends
    BACKEND = {'GATES': 'custom', 'EINSUM': None, 'STRING': 'custom'}

    # Set devices recognized by tensorflow
    DEVICES = {
        'CPU': tf.config.list_logical_devices("CPU"),
        'GPU': tf.config.list_logical_devices("GPU")
    }
    # set default device to GPU if it exists
    if DEVICES['GPU']: # pragma: no cover
        DEVICES['DEFAULT'] = DEVICES['GPU'][0].name
    elif DEVICES['CPU']:
        DEVICES['DEFAULT'] = DEVICES['CPU'][0].name
    else: # pragma: no cover
        raise RuntimeError("Unable to find Tensorflow devices.")

    # Define numpy and tensorflow matrices
    # numpy matrices are exposed to user via ``from qibo import matrices``
    # tensorflow matrices are used by native gates (``/tensorflow/gates.py``)
    from qibo.tensorflow import matrices as _matrices
    matrices = _matrices.NumpyMatrices()
    tfmatrices = _matrices.TensorflowMatrices()


    def set_backend(backend='custom'):
        """Sets backend used to implement gates.

        Args:
            backend (str): possible options are 'custom' for the gates that use
                custom tensorflow operator and 'defaulteinsum' or 'matmuleinsum'
                for the gates that use tensorflow primitives (``tf.einsum`` or
                ``tf.matmul`` respectively).
        """
        if not ALLOW_SWITCHERS and backend != BACKEND['GATES']:
            warnings.warn("Backend should not be changed after allocating gates.",
                          category=RuntimeWarning)
        if backend == 'custom':
            BACKEND['NAME'] = backend
            BACKEND['GATES'] = 'custom'
            BACKEND['EINSUM'] = None
        elif backend == 'defaulteinsum':
            from qibo.tensorflow import einsum
            BACKEND['NAME'] = backend
            BACKEND['GATES'] = 'native'
            BACKEND['EINSUM'] = einsum.DefaultEinsum()
        elif backend == 'matmuleinsum':
            from qibo.tensorflow import einsum
            BACKEND['NAME'] = backend
            BACKEND['GATES'] = 'native'
            BACKEND['EINSUM'] = einsum.MatmulEinsum()
        else:
            raise RuntimeError(f"Gate backend '{backend}' not supported.")


    def get_backend():
        """Get backend used to implement gates.

        Returns:
            A string with the backend name.
        """
        return BACKEND['STRING']


    def set_precision(dtype='double'):
        """Set precision for states and gates simulation.

        Args:
            dtype (str): possible options are 'single' for single precision
                (complex64) and 'double' for double precision (complex128).
        """
        if not ALLOW_SWITCHERS and dtype != DTYPES['STRING']:
            warnings.warn("Precision should not be changed after allocating gates.",
                          category=RuntimeWarning)
        if dtype == 'single':
            DTYPES['DTYPE'] = tf.float32
            DTYPES['DTYPECPX'] = tf.complex64
            DTYPES['NPTYPECPX'] = np.complex64
        elif dtype == 'double':
            DTYPES['DTYPE'] = tf.float64
            DTYPES['DTYPECPX'] = tf.complex128
            DTYPES['NPTYPECPX'] = np.complex128
        else:
            raise RuntimeError(f'dtype {dtype} not supported.')
        DTYPES['STRING'] = dtype
        matrices.allocate_matrices()
        tfmatrices.allocate_matrices()


    def get_precision():
        """Get precision for states and gates simulation.

        Returns:
            A string with the precision name ('single', 'double').
        """
        return DTYPES['STRING']


    def set_device(device_name: str):
        """Set default execution device.

        Args:
            device_name (str): Device name. Should follow the pattern
                '/{device type}:{device number}' where device type is one of
                CPU or GPU.
        """
        if not ALLOW_SWITCHERS and device_name != DEVICES['DEFAULT']: # pragma: no cover
            warnings.warn("Device should not be changed after allocating gates.",
                          category=RuntimeWarning)
        parts = device_name[1:].split(":")
        if device_name[0] != "/" or len(parts) < 2 or len(parts) > 3:
            raise ValueError("Device name should follow the pattern: "
                             "/{device type}:{device number}.")
        device_type, device_number = parts[-2], int(parts[-1])
        if device_type not in {"CPU", "GPU"}:
            raise ValueError(f"Unknown device type {device_type}.")
        if device_number >= len(DEVICES[device_type]):
            raise ValueError(f"Device {device_name} does not exist.")

        DEVICES['DEFAULT'] = device_name
        with tf.device(device_name):
            tfmatrices.allocate_matrices()


    def get_device():
        """Get execution device.

        Returns:
            A string with the device name.
        """
        return DEVICES['DEFAULT']


else: # pragma: no cover
    raise NotImplementedError("Only Tensorflow backend is implemented.")