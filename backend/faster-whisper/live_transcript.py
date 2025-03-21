from faster_whisper import WhisperModel
import time
import pyaudio
import numpy as np
import os
import uuid
import signal
import sys
from datetime import datetime

# Setup PyAudio
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5  # Process audio in 5-second chunks

model_size = "large-v3"

# Create a session ID and transcript folder
session_id = str(uuid.uuid4())
transcript_folder = os.path.join(os.path.dirname(__file__), "..", "transcripts")
os.makedirs(transcript_folder, exist_ok=True)
transcript_file = os.path.join(transcript_folder, f"transcript_{session_id}.txt")

# Initialize the transcription log
transcription_log = []

# Function to handle termination
def signal_handler(sig, frame):
    print("\nTerminating and saving transcript...")
    # Save the transcription log
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write(f"Transcription Session: {session_id}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for start_time, end_time, text in transcription_log:
            f.write(f"[{start_time:.2f}s -> {end_time:.2f}s] {text}\n")
    
    print(f"Transcription saved to {transcript_file}")
    
    # Display the transcription log
    print("\nTranscription Log:")
    for start_time, end_time, text in transcription_log:
        print(f"[{start_time:.2f}s -> {end_time:.2f}s] {text}")
    
    sys.exit(0)

# Set up signal handler
signal.signal(signal.SIGINT, signal_handler)

# Let's calculate the time it takes to load the model
start = time.time()
print(f'Loading model {model_size}...')
model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
print(f'Model {model_size} loaded.')
end = time.time()
print(f"Model loading time: {end - start} seconds")

# Initialize PyAudio
p = pyaudio.PyAudio()

# Open stream
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("* Recording. Press Ctrl+C to stop and save the transcript.")

# Start recording and transcribing
try:
    total_time = 0
    while True:
        frames = []
        
        # Record for RECORD_SECONDS
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)
        
        # Convert the audio frames to a NumPy array
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32) / 32768.0
        
        # Transcribe the audio data
        segments, info = model.transcribe(audio_data, beam_size=5)
        
        # Process and store the segments
        for segment in segments:
            actual_start = total_time + segment.start
            actual_end = total_time + segment.end
            print(f"[{actual_start:.2f}s -> {actual_end:.2f}s] {segment.text}")
            transcription_log.append((actual_start, actual_end, segment.text))
        
        # Update the total time
        total_time += RECORD_SECONDS

except KeyboardInterrupt:
    signal_handler(None, None)
finally:
    # Clean up
    stream.stop_stream()
    stream.close()
    p.terminate()

