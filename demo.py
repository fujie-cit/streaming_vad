import streaming_vad as sv
import pyaudio

### StreamingVADの初期化

# 利用する VAD Unit の名前.
# 'silero' または 'webrtcvad' を指定可能.
vad_unit_name = 'silero'

# VAD Unit の設定.
# VADUnitSileroConfig または VADUnitWebRTCConfig のインスタンスを指定可能.
# 詳細は各クラスのドキュメントを参照のこと.
# 下記の設定は，VAD判定の閾値を0.5にするという意味. 0.8なら厳しくなり，0.2なら緩くなる.
vad_unit_config = sv.VADUnitSileroConfig(threshold=0.5)

# StreamingVADオブジェクトの初期化.
# - デフォルトでサンプリング周波数は16,000，サンプル幅は2バイト.
#   これらの値は標準的な音声認識で使われる値なので変更する必要は基本的にない.
# - デフォルトでフレームサイズは160サンプル（10ms）となる.
#   こちらは場合によっては変更する必要が生じる可能性があるが，
#   VAD Unitによる制限を受ける可能性がある. 特にSileroを使う場合は,
#   640サンプル以下かつ，640を1以上の整数で割った値となるようにする必要がある.
# - ストリーミングVADとして重要なパラメータは以下の通り:
#   - start_frame_num_thresh: 音声が始まったと判定するためのフレーム数（デフォルト5）
#                             VAD Unit がこの回数だけ連続で音声と判定したら音声が始まったと判定する.
#   - start_frame_rollback: 音声開始直後に遡って出力するフレーム数（デフォルト10）
#   - end_frame_num_thresh: 音声が終わったと判定するためのフレーム数（デフォルト30）
#                           音声区間開始後，この回数だけ連続で音声でないと判定したら音声が終わったと判定する.
#   これらの値を適切に変更しないと, わずかな音で区間が開始されたり, わずかな無音で
#   区間が終了される可能性がある.
# - その他のパラメータ:
#   - output_idle_frame: 音声区間以外も出力するかどうか（デフォルトFalse).
#                        通常は音声区間と判定されなかった場合は，音声信号を出力しないが,
#                        このフラグがTrueのときは出力する.
stream_vad = sv.StreamingVAD(
    output_idle_frame=True,
    vad_unit_name=vad_unit_name,
    vad_unit_config=vad_unit_config
)

### マイクから音声を取得してVADを実行
p = pyaudio.PyAudio()
CHUNK = 160
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)
stream.start_stream()

try:
    frame_count = 0
    while True:
        # 音声信号を1フレーム分（160サンプル分）読み込み
        data = stream.read(CHUNK)
        # VADを実行
        vad_data = stream_vad.process(data)

        # 結果は VADData オブジェクトとして返ってくる.
        # VADData.state には VADState の値が入り,
        # VADData.data には音声区間と判定されたフレームのリストが入る.
        #
        # VADStateは以下の4種類の値が入る:
        # - VADState.Idle: 音声区間外
        # - VADState.Started: 音声区間開始
        # - VADState.Continue: 音声区間継続
        # - VADState.Ended: 音声区間終了
        #
        # VADData.data は state の値によって異なる:
        # - Idle状態かつ output_idle_frame=False の場合は必ず空.
        #   Idle状態で output_idle_frame=True の場合は空,
        #   または1フレーム分の音声データが入る.
        # - Started状態の場合は, start_frame_rollback フレーム分の音声データが入る.
        # - Continue状態, またはEnded状態の場合は, 1フレーム分の音声データが入る.
        if vad_data.state == sv.VADState.Started:
            print('VAD started')
            frame_count = 1
        elif vad_data.state == sv.VADState.Continue:
            frame_count += 1
            print('\rVAD continue: frame_count={}'.format(frame_count), end='')
        elif vad_data.state == sv.VADState.Ended:
            frame_count += 1
            print(f'\nVAD ended: frame_count={frame_count}')

except KeyboardInterrupt:
    pass
finally:
    stream.stop_stream()
    stream.close()
    p.terminate()




