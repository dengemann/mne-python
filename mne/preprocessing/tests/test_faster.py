import numpy as np
import mne

from nose.tools import (assert_true, assert_almost_equal,
                        assert_raises, assert_equal)
from numpy.testing import (assert_allclose, assert_array_equal)

from mne.preprocessing.faster import (_hurst, _freqs_power, _power_gradient,
                                      detect_bad_channels, detect_bad_epochs)

# Signal properties used in the tests
length = 2  # in seconds
srate = 200. # in Hertz
n_channels = 30
n_epochs = 100
n_samples = int(length * srate)
time = np.arange(n_samples) / srate


def test_hurst():
    """Test internal hurst exponent function."""
    np.random.seed(123)

    # Hurst exponent of a sine wave
    p = np.atleast_2d(np.sin(1000))
    assert_almost_equal(p, 0.82687954)

    # Positive first derivative, hurst > 1
    p = np.atleast_2d(np.log10(np.cumsum(np.random.randn(1000) + 100)))
    assert_true(_hurst(p) > 1)

    # First derivative alternating around zero, hurst ~ 0
    p = np.atleast_2d(np.log10(np.random.randn(1000) + 1000))
    assert_allclose(_hurst(p), 0, atol=0.1)

    # Positive, but fluctuating first derivative, hurst ~ 0.5
    p = np.atleast_2d(np.log10(np.cumsum(np.random.randn(1000)) + 1000))
    assert_allclose(_hurst(p), 0.5, atol=0.1)


# This function also implicitly tests _efficient_welch
def test_freqs_power():
    """Test internal function for frequency power estimation."""
    # Create signal with different frequency components
    freqs = [1, 5, 12.8, 23.4, 40]  # in Hertz
    srate = 100.0
    time = np.arange(10 * srate) / srate
    signal = np.sum([np.sin(2 * np.pi * f * time) for f in freqs], axis=0)
    signal = np.atleast_2d(signal)

    # These frequencies should be present
    for f in freqs:
        assert_almost_equal(_freqs_power(signal, srate, [f]), 3 + 1/3.)

    # The function should sum the individual frequency  powers
    assert_almost_equal(_freqs_power(signal, srate, freqs),
                        len(freqs) * (3 + 1/3.))

    # These frequencies should not be present
    assert_almost_equal(_freqs_power(signal, srate, [2, 4, 13, 23, 35]), 0)

    # Insufficient sample rate to calculate this frequency
    assert_raises(ValueError, _freqs_power, signal, srate, [51])


def test_power_gradient():
    """Test internal function for estimating power gradient"""
    #_power_gradient()
    pass


def _baseline_signal():
    """Helper function to create the baseline signal"""
    signal = np.tile(np.sin(time), (n_epochs, n_channels, 1))
    noise = np.random.randn(n_epochs, n_channels, n_samples)
    return signal, noise


def _to_epochs(signal, noise):
    """Helper function to create the epochs object"""
    events = np.tile(np.arange(n_epochs)[:, np.newaxis], (1, 3))
    return mne.EpochsArray(signal + noise,
                           mne.create_info(n_channels, srate, 'eeg'),
                           events)


def test_detect_bad_channels():
    """Test detecting bad channels through outlier detection"""
    signal, noise = _baseline_signal()

    # This channel has more noise
    noise[:, 0, :] *= 2

    # This channel does not correlate with the others
    signal[:, 1, :] = np.sin(time + 0.68)

    # This channel has excessive 50 Hz line noise
    signal[:, 2, :] = np.sin(50 * 2 * np.pi * time)

    # This channel has excessive 60 Hz line noise
    signal[:, 3, :] = np.sin(50 * 2 * np.pi * time)

    # This channel has a different noise signature (kurtosis)
    noise[:, 4, :] = 4 * np.random.rand(n_epochs, n_samples)

    # TODO: deviant hurst

    epochs = _to_epochs(signal, noise)
    bads = detect_bad_channels(epochs, max_iter=1, return_by_metric=True)
    assert_equal(bads, {
        'variance': ['0'],
        'correlation': ['1'],
        'line_noise': ['2', '3'],
        'kurtosis': ['4'],
        'hurst': ['2', '3'],
    })


def test_detect_bad_epochs():
    """Test detecting bad epochs through outlier detection"""
    signal, noise = _baseline_signal()

    # This epoch has more noise
    noise[0, :, :] *= 2

    # This epoch has some deviation
    signal[1, :, :] += 20

    # This epoch has a single spike across channels
    signal[2, :, 0] += 10

    epochs = _to_epochs(signal, noise)

    bads = detect_bad_epochs(epochs, max_iter=1, return_by_metric=True)
    assert_equal(bads, {
        'variance': [0],
        'deviation': [1],
        'amplitude': [0, 2],
    })
