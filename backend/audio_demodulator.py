"""
Audio demodulation module for FM and AM signals.
Converts IQ samples to audio PCM data for playback.
"""

import numpy as np
from scipy import signal as scipy_signal
import logging

logger = logging.getLogger(__name__)


class AudioDemodulator:
    """Handles FM and AM demodulation of IQ samples."""
    
    def __init__(self, sample_rate=2048000, audio_rate=48000):
        """
        Initialize the audio demodulator.
        
        Args:
            sample_rate: Input sample rate from SDR (Hz)
            audio_rate: Output audio sample rate (Hz)
        """
        self.sample_rate = sample_rate
        self.audio_rate = audio_rate
        self.decimation = int(sample_rate / audio_rate)
        
        # FM demodulation state
        self.fm_prev_phase = 0.0
        
        # Audio filters
        self._design_filters()
        
        logger.info(f"Audio demodulator initialized: {sample_rate}Hz -> {audio_rate}Hz (decimation: {self.decimation})")
    
    def _design_filters(self):
        """Design audio filters for demodulation."""
        # Low-pass filter for audio output (15 kHz cutoff for voice/music)
        nyquist = self.audio_rate / 2
        cutoff = min(15000, nyquist * 0.9)
        self.audio_lpf = scipy_signal.butter(5, cutoff / nyquist, btype='low', output='sos')
        
        # De-emphasis filter for FM (75 µs time constant)
        # tau = 75e-6
        # d = self.audio_rate * tau
        # b = [1 - np.exp(-1/d)]
        # a = [1, -np.exp(-1/d)]
        # self.deemph_filter = (b, a)
        
        logger.debug("Audio filters designed")
    
    def demodulate_fm(self, iq_samples: np.ndarray) -> np.ndarray:
        """
        Demodulate FM signal using frequency discriminator method.
        
        Args:
            iq_samples: Complex IQ samples from SDR
            
        Returns:
            Audio samples as float32 array (normalized -1 to 1)
        """
        try:
            # FM discriminator: differentiate the phase
            # phase = angle(sample[n] * conj(sample[n-1]))
            diff = iq_samples[1:] * np.conj(iq_samples[:-1])
            audio = np.angle(diff)
            
            # Normalize to prevent clipping
            if len(audio) > 0:
                audio = audio / (np.pi * 0.7)  # Leave headroom
            
            # Decimate to audio rate
            audio = scipy_signal.decimate(audio, self.decimation, ftype='iir', zero_phase=True)
            
            # Low-pass filter
            audio = scipy_signal.sosfilt(self.audio_lpf, audio)
            
            # Normalize to -1 to 1 range
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val * 0.95  # Leave headroom
            
            return audio.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error in FM demodulation: {e}")
            return np.zeros(len(iq_samples) // self.decimation, dtype=np.float32)
    
    def demodulate_am(self, iq_samples: np.ndarray) -> np.ndarray:
        """
        Demodulate AM signal using envelope detection.
        
        Args:
            iq_samples: Complex IQ samples from SDR
            
        Returns:
            Audio samples as float32 array (normalized -1 to 1)
        """
        try:
            # Envelope detection: magnitude of complex signal
            audio = np.abs(iq_samples)
            
            # Remove DC component
            audio = audio - np.mean(audio)
            
            # Decimate to audio rate
            audio = scipy_signal.decimate(audio, self.decimation, ftype='iir', zero_phase=True)
            
            # Low-pass filter
            audio = scipy_signal.sosfilt(self.audio_lpf, audio)
            
            # Normalize to -1 to 1 range
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val * 0.95  # Leave headroom
            
            return audio.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error in AM demodulation: {e}")
            return np.zeros(len(iq_samples) // self.decimation, dtype=np.float32)
    
    def demodulate(self, iq_samples: np.ndarray, mode: str = 'FM') -> np.ndarray:
        """
        Demodulate IQ samples based on mode.
        
        Args:
            iq_samples: Complex IQ samples from SDR
            mode: Demodulation mode ('FM' or 'AM')
            
        Returns:
            Audio samples as float32 array (normalized -1 to 1)
        """
        mode = mode.upper()
        
        if mode == 'FM':
            return self.demodulate_fm(iq_samples)
        elif mode == 'AM':
            return self.demodulate_am(iq_samples)
        else:
            logger.warning(f"Unknown demodulation mode: {mode}, defaulting to FM")
            return self.demodulate_fm(iq_samples)
    
    def update_sample_rate(self, sample_rate: int):
        """Update sample rate and recalculate decimation."""
        self.sample_rate = sample_rate
        self.decimation = int(sample_rate / self.audio_rate)
        self._design_filters()
        logger.info(f"Sample rate updated to {sample_rate}Hz (decimation: {self.decimation})")

