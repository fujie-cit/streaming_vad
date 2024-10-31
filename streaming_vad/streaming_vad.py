from typing import Dict, Any, List, Union
from enum import Enum
from dataclasses import dataclass, field, asdict
from .vad_unit.base import VADUnitBase
from .vad_unit.silero import VADUnitSilero
from .vad_unit.webrtcvad import VADUnitWebRTC


AVAILABLE_VAD_UNITS: Dict[str, VADUnitBase] = {
    'webrtcvad': VADUnitWebRTC,
    'silero': VADUnitSilero,
}
"""利用可能な VAD ユニットの辞書."""


class VADState(Enum):
    """VAD の状態を表す列挙型."""
    Idle = 0,     """VAD が音声を検出していない状態."""
    Started = 1,  """VAD が音声を検出し始めた状態."""
    Ended = 2,    """VAD が音声の終了を検出した状態."""
    Continue = 3, """VAD が音声を検出し続けている状態."""


@dataclass
class VADData:
    """VAD結果を格納するデータクラス.

    Attributes:
        state (VADState): VAD の状態.
        data (List[bytes]): 音声データのリスト.
            1つの要素は1フレーム分の音声データを表す.
            Started状態の場合, ロールバック分も含めた複数フレームが格納される.
            その他の場合は原則的に1フレーム分のデータが格納される.
    """
    state: VADState = VADState.Idle
    data: List[bytes] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"VADData(state={self.state.name}, packets=[{len(self.data)}frames])"


class StreamingVAD:
    """ストリーミング音声データに対する VAD を提供するクラス.

    Attributes:
        sample_rate: サンプリング周波数[Hz].
        sample_width: サンプル幅[バイト数].
        samples_per_frame: 1フレームのサンプル数.
        start_frame_num_thresh: 音声開始と判定するためのフレーム数の閾値.
        start_frame_rollback: 音声開始判定後にロールバックするフレーム数.
        end_frame_num_thresh: 音声終了と判定するためのフレーム数の閾値.
        output_idle_frame: 非音声区間のフレームも出力するかどうか.
    """
    def __init__(self,
                 sample_rate: int = 16000,
                 sample_width: int = 2,
                 samples_per_frame: int = 160,
                 start_frame_num_thresh: int = 5,
                 start_frame_rollback: int = 10,
                 end_frame_num_thresh: int = 30,
                 output_idle_frame: bool = False,
                 vad_unit_name: str = 'silero',
                 vad_unit_config: Union[object, Dict[str, Any]] = None):
        """
        Args:
            sample_rate (int): サンプリング周波数[Hz].
            sample_width (int): サンプル幅[バイト数].
            samples_per_frame (int): 1フレームのサンプル数.
            start_frame_num_thresh (int): 音声開始と判定するためのフレーム数の閾値.
            start_frame_rollback (int): 音声開始判定後にロールバックするフレーム数.
            end_frame_num_thresh (int): 音声終了と判定するためのフレーム数の閾値.
            output_idle_frame (bool): 非音声区間のフレームも出力するかどうか.
            vad_unit_name (str): VAD ユニットの名前.
            vad_unit_config (Union[object, Dict[str, Any]]): VAD ユニットの設定.
                object: VAD ユニットの設定を格納したオブジェクト.
                Dict[str, Any]: VAD ユニットの設定を格納した辞書.
        """
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.samples_per_frame = samples_per_frame
        self.start_frame_num_thresh = start_frame_num_thresh
        self.start_frame_rollback = start_frame_rollback
        self.end_frame_num_thresh = end_frame_num_thresh
        self.output_idle_frame = output_idle_frame

        assert vad_unit_name in AVAILABLE_VAD_UNITS, f"Invalid VAD unit name: {vad_unit_name}"

        vad_unit_config_as_dict = {}
        if isinstance(vad_unit_config, dict):
            vad_unit_config_as_dict = vad_unit_config
        elif isinstance(vad_unit_config, object):
            vad_unit_config_as_dict = asdict(vad_unit_config)
        self.vad_unit: VADUnitBase = AVAILABLE_VAD_UNITS[vad_unit_name](**vad_unit_config_as_dict)

        # VAD Unit とのパラメータの整合性をチェック
        # サンプリング周波数とサンプル幅は一致していなければいけない
        assert self.sample_rate == self.vad_unit.sample_rate, f"Sample rate mismatch: {self.sample_rate} != {self.vad_unit.sample_rate}"
        assert self.sample_width == self.vad_unit.sample_width, f"Sample width mismatch: {self.sample_width} != {self.vad_unit.sample_width}"
        # フレームサイズは VAD Unit のものの方が大きく，整数倍である必要がある
        assert self.samples_per_frame <= self.vad_unit.samples_per_frame, f"Samples per frame mismatch: {self.samples_per_frame} > {self.vad_unit.samples_per_frame}"
        assert self.vad_unit.samples_per_frame % self.samples_per_frame == 0, f"Samples per frame is not a multiple of {self.samples_per_frame}"

        # フレームサイズ（バイト単位）
        self.actual_frame_size_in_bytes = self.sample_width * self.samples_per_frame

        # VAD Unitに与えるフレーム長（こちらのフレーム長基準）
        self.vad_unit_frame_ratio = self.vad_unit.samples_per_frame // self.samples_per_frame
        # VAD Unitに与えるフレームのためのバッファ
        self.vad_unit_frame_buffer: List[bytes] = []

        # 1フレーム前の VAD Unit の結果
        self.prev_vad_unit_result = False
        # VAD Unit の結果のカウント
        # 非音声区間時はTrueのカウント，音声区間時はFalseのカウント
        self.vad_unit_result_count = 0
        # VAD の状態
        self.vad_state = VADState.Idle
        # 返却値のためのバッファ
        self.vad_result_buffer: List[bytes] = []


    def reset(self):
        """VAD の状態をリセットする."""
        self.vad_unit_frame_buffer.clear()
        self.prev_vad_unit_result = False
        self.vad_unit_result_count = 0
        self.vad_state = VADState.Idle
        self.vad_result_buffer.clear()


    def process(self, audio_data: bytes) -> VADData:
        """音声データを処理し, VAD の状態を返す."""
        assert len(audio_data) == self.actual_frame_size_in_bytes, f"Data size is invalid: {len(audio_data)} != {self.actual_frame_size_in_bytes}"

        # フレームをバッファに追加
        self.vad_unit_frame_buffer.append(audio_data)
        # バッファがフレーム数に達したら VAD Unit に処理を依頼
        # その後，バッファをクリア
        if len(self.vad_unit_frame_buffer) == self.vad_unit_frame_ratio:
            vad_result = self.vad_unit.process(b''.join(self.vad_unit_frame_buffer))
            self.vad_unit_frame_buffer.clear()
        else:
            vad_result = self.prev_vad_unit_result
        self.prev_vad_unit_result = vad_result

        # 結果出力用のバッファにデータを追加
        self.vad_result_buffer.append(audio_data)
        if len(self.vad_result_buffer) > self.start_frame_rollback:
            overflow_data = self.vad_result_buffer.pop(0)
        else:
            overflow_data = None

        if self.vad_state == VADState.Idle:
            if vad_result:
                self.vad_unit_result_count += 1
            else:
                self.vad_unit_result_count = 0
            if self.vad_unit_result_count >= self.start_frame_num_thresh:
                return_value = VADData(VADState.Started, self.vad_result_buffer.copy())
                self.vad_result_buffer.clear()
                self.vad_unit_count = 0
                self.vad_state = VADState.Continue
            else:
                return_value = VADData(VADState.Idle, [])
                if self.output_idle_frame and overflow_data is not None:
                    return_value.data.append(overflow_data)
        elif self.vad_state == VADState.Continue:
            if vad_result:
                self.vad_unit_result_count = 0
            else:
                self.vad_unit_result_count += 1
            if self.vad_unit_result_count >= self.end_frame_num_thresh:
                return_value = VADData(VADState.Ended, self.vad_result_buffer.copy())
                self.vad_result_buffer.clear()
                self.vad_unit_count = 0
                self.vad_state = VADState.Idle
            else:
                return_value = VADData(VADState.Continue, self.vad_result_buffer.copy())
                self.vad_result_buffer.clear()
        else:
            raise ValueError(f"Invalid VAD state: {self.vad_state}")
        return return_value


if __name__ == "__main__":
    import pyaudio
    from streaming_vad.vad_unit.silero import VADUnitSileroConfig

    config = VADUnitSileroConfig(threshold=0.5)
    stream_vad = StreamingVAD(output_idle_frame=True,
                             vad_unit_name='silero',
                             vad_unit_config=config)

    # マイクから音声を取得する
    CHUNK = 160
    FORMAT = pyaudio.paInt16
    CHANNELS = 1

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=16000,
                    input=True,
                    frames_per_buffer=CHUNK)
    stream.start_stream()

    try:
        while True:
            audio_data = stream.read(CHUNK, exception_on_overflow=False)
            vad_data = stream_vad.process(audio_data)
            print(vad_data)
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
