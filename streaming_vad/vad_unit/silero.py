from .base import VADUnitBase
import torch
import numpy as np
from dataclasses import dataclass


@dataclass
class VADUnitSileroConfig:
    """Configurations of VAD Unit for Silero VAD.

    Please refer to the following URL for the details of the model.
    https://github.com/snakers4/silero-vad

    Attributes:
        model_repo_or_dir (str): Model repository or directory.
        model_name (str): Model name.
        threshold (float): Threshold
    """
    model_repo_or_dir: str = 'snakers4/silero-vad'
    model_name: str = 'silero_vad'
    threshold: float = 0.5


class VADUnitSilero(VADUnitBase):
    def __init__(self,
        model_repo_or_dir: str = 'snakers4/silero-vad',
        model_name: str = 'silero_vad',
        threshold: float = 0.5,
    ):
        self.model, _ = torch.hub.load(repo_or_dir=model_repo_or_dir, model=model_name)
        self.threshold = threshold
        self._sample_rate = 16000
        self._sample_width = 2
        self._samples_per_frame = 640 # 40ms
        self._actual_frame_size_in_bytes = self._sample_width * self._samples_per_frame

    def process(self, data: bytes) -> bool:
        assert len(data) == self.actual_frame_size_in_bytes, f"Data size is invalid: {len(data)} != {self.actual_frame_size_in_bytes}"
        audio_float32 = (np.frombuffer(data, dtype=np.int16) / (2**15 - 1)).astype(np.float32)
        audio_tensor = torch.tensor(audio_float32)
        confidence = self.model(audio_tensor, 16000).item()
        return confidence > self.threshold
