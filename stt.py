import os
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv
from faster_whisper import WhisperModel

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")


def record_and_transcribe(model, output_file="recording.wav", samplerate=44100):
    """Record audio from mic, save it, then transcribe to text."""

    # Remove old recording if it exists
    if os.path.exists(output_file):
        os.remove(output_file)

    print("Press ENTER to start recording...")
    input()

    print("[REC] Recording... Press ENTER to stop")

    # Record up to 60 seconds of audio
    recording = sd.rec(int(60 * samplerate), samplerate=samplerate, channels=1, dtype='float64')
    input()  # Wait for user to press ENTER
    sd.stop()

    print("[STOP] Saving audio...")

    # Save recording to file
    sf.write(output_file, recording, samplerate)

    print("[STT] Transcribing...")

    # Convert speech to text
    segments, _ = model.transcribe(output_file)
    text = " ".join([seg.text for seg in segments])

    print(f"Transcription: {text}")
    return text.strip()


if __name__ == "__main__":
    from huggingface_hub import snapshot_download

    # Download the Whisper model (single-threaded to avoid lock issues)
    model_path = snapshot_download('Systran/faster-whisper-small.en', max_workers=1)
    model = WhisperModel(model_path, device="cpu", compute_type="float32", use_auth_token=os.getenv("HF_TOKEN"))
    result = record_and_transcribe(model)
    print(f"Got: '{result}'")