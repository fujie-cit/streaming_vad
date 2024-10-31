# Streaming Voice Activity Detection

## Installation

from GitHub:
```bash
pip install git+https://github.com/fujie-cit/streaming_vad.git
```

from local directory:
```bash
pip install -e .
```

## Usage

```python
import streaming_vad as sv

# initialize your streaming VAD object
vad = sv.StreamingVad()

# capture the audio as a bytes object whose length is 320 bytes (160 samples)
for audio in audio_stream:
    vad_data = vad.process(audio)

    if vad_data.state == sv.VadState.Started:
        # speech interval is just started.
        # vad_data.data has `start_frame_rollback' items of audio data.
        print('speech detected')
        print(len(vad_data.data))
    elif vad_data.state == sv.VadState.Continue:
        # speech interval is continuing.
        # vad_data.data has 1 audio data.
        print('speech detected')
        print(len(vad_data.data))
    elif vad_data.state == sv.VadState.Ended:
        # speech interval is just ended.
        # vad_data.data also has 1 audio data.
        print('speech detected')
        print(len(vad_data.data))
```

Please refer `demo.py` for more details.

