from .base import VADUnitBase
from webrtcvad import Vad
from dataclasses import dataclass


@dataclass
class VADUnitWebRTCConfig:
    """Configurations of VAD Unit for WebRTC VAD.

    Please refer to the following URL for the details of the model.
    https://github.com/wiseman/py-webrtcvad

    Attributes:
        mode (int): Aggressiveness mode.
                    integer between 0 and 3, inclusive.
                    0 is the least aggressive about filtering out non-speech,
                    3 is the most aggressive.
        sample_rate (int): Sample rate.
        sample_width (int): Sample width.
        samples_per_frame (int): Samples per frame.
    """
    mode: int = 3
    sample_rate: int = 16000
    sample_width: int = 2
    samples_per_frame: int = 160


class VADUnitWebRTC(VADUnitBase):
    def __init__(self,
        mode: int = 3,
        sample_rate: int = 16000,
        sample_width: int = 2,
        samples_per_frame: int = 160,
    ):
        super().__init__()

        self.vad = Vad(mode)
        self._sample_rate = sample_rate
        self._sample_width = sample_width
        self._samples_per_frame = samples_per_frame
        self._actual_frame_size_in_bytes = self._sample_width * self._samples_per_frame

        assert self._sample_rate in [8000, 16000, 32000, 48000], f"Invalid sample rate: {self.sample_rate}"
        assert self._sample_width in [2], f"Invalid sample width: {self.sample_width}"
        actual_frame_size_in_ms = 1000 * self._samples_per_frame // self._sample_rate
        assert actual_frame_size_in_ms in [10, 20, 30], f"Invalid frame size: {actual_frame_size_in_ms}ms"

    def process(self, data: bytes) -> bool:
        assert len(data) == self.actual_frame_size_in_bytes, f"Data size is invalid: {len(data)} != {self.actual_frame_size_in_bytes}"
        return self.vad.is_speech(data, self.sample_rate)
