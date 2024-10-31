from abc import ABC, abstractmethod
from typing import List

class VADUnitBase(ABC):
    def __init__(self):
        self._sample_rate = None
        self._sample_width = None
        self._samples_per_frame = None
        self._actual_frame_size_in_bytes = None

    @property
    def sample_rate(self) -> int:
        """サンプリング周波数[Hz]."""
        return self._sample_rate

    @property
    def sample_width(self) -> int:
        """サンプル幅[バイト数]."""
        return self._sample_width

    @property
    def samples_per_frame(self) -> int:
        """1フレームのサンプル数."""
        return self._samples_per_frame

    @property
    def actual_frame_size_in_bytes(self) -> int:
        """1フレームのバイト数."""
        return self._actual_frame_size_in_bytes

    @abstractmethod
    def process(self, data: bytes) -> bool:
        """音声データを処理する.
        Args:
            data (bytes): 音声データ.
        Returns:
            bool: 音声が検出されたかどうか.
        Exceptions:
            ValueError: サンプリング周波数, サンプル幅, フレームサイズが設定と異なる場合．
        """
        raise NotImplementedError("process method is not implemented.")

