from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()
import os

VOICE_ID = os.getenv('VOICE_ID')
ELEVEN_LABS_API_KEY = os.getenv('ELEVEN_LABS_API_KEY')

_client = ElevenLabs(api_key=ELEVEN_LABS_API_KEY) if ELEVEN_LABS_API_KEY else None


def text_to_speech(text, output_file="output.mp3"):
    if not VOICE_ID or not _client:
        raise ValueError("Missing VOICE_ID or ELEVEN_LABS_API_KEY in environment")

    audio_stream = _client.text_to_speech.convert(
        text=text,
        voice_id=VOICE_ID,
        model_id='eleven_flash_v2_5',
        optimize_streaming_latency=4,
    )
    with open(output_file, "wb") as f:
        for chunk in audio_stream:
            if chunk:
                f.write(chunk)
    return output_file


if __name__ == "__main__":
    text_to_speech("Hello, I am Sana.")