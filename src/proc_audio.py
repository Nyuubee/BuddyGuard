### src/proc_audio.py


### IMPORTS
### ________________________________________________________________
import ffmpeg
import streamlit as st
from transformers import pipeline

def extract_audio(video_path, audio_path):
    stream = ffmpeg.input(video_path)
    stream = ffmpeg.output(stream, audio_path, acodec='pcm_s16le', ac=1, ar='16000')
    ffmpeg.run(stream)

# def transcribe_audio(audio_path, whisper_model):
#     result = whisper_model(audio_path, return_timestamps=True)
#
#     transcribed_segments = []
#     for segment in result["chunks"]:
#         start_time = segment["timestamp"][0]  # Start timestamp in seconds
#         text = segment["text"]
#
#         transcribed_segments.append({
#             "start_time": start_time,
#             "text": text
#         })
#
#     return transcribed_segments

def transcribe_audio(audio_path, whisper_model):
    result = whisper_model(audio_path, return_timestamps=True)

    transcribed_segments = []
    for segment in result["chunks"]:
        # Ensure timestamp exists and is valid
        if segment["timestamp"] and isinstance(segment["timestamp"], (list, tuple)) and len(segment["timestamp"]) > 0:
            start_time = segment["timestamp"][0]  # Start timestamp in seconds
            if start_time is not None:
                transcribed_segments.append({
                    "start_time": start_time,
                    "text": segment["text"]
                })

    return transcribed_segments

# def display_transcription_with_timestamps(transcription, video_id):
#     formatted_transcription = ""
#
#     for segment in transcription:
#         start_time = segment["start_time"]
#         text = segment["text"]
#
#         # Convert seconds to MM:SS format
#         minutes = int(start_time // 60)
#         seconds = int(start_time % 60)
#         formatted_time = f"{minutes:02}:{seconds:02}"
#
#         # Add a clickable span for seeking
#         formatted_transcription += (
#             f"<span style='cursor:pointer; color:cyan; text-decoration:underline;' "
#             f"onclick='seekVideo(\"{video_id}\", {start_time})'>{formatted_time}</span> {text}<br>"
#         )
#
#     # Inject JavaScript for seeking
#     import streamlit as st
#     st.markdown("""
#         <script>
#         function seekVideo(video_id, time) {
#             var vid = document.getElementById(video_id);
#             if (vid) {
#                 vid.currentTime = time;
#                 vid.play();
#             }
#         }
#         </script>
#     """, unsafe_allow_html=True)
#
#     st.markdown(f"<div style='font-size:18px;'>{formatted_transcription}</div>", unsafe_allow_html=True)


def display_transcription_with_timestamps(transcription, video_id):
    if not transcription:
        st.warning("No transcription available")
        return

    formatted_transcription = ""

    for segment in transcription:
        start_time = segment.get("start_time")
        text = segment.get("text", "")

        if start_time is None:
            formatted_transcription += f"{text}<br>"
            continue

        try:
            # Convert seconds to MM:SS format
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            formatted_time = f"{minutes:02}:{seconds:02}"

            # Add clickable span for seeking
            formatted_transcription += (
                f"<span style='cursor:pointer; color:cyan; text-decoration:underline;' "
                f"onclick='seekVideo(\"{video_id}\", {start_time})'>{formatted_time}</span> {text}<br>"
            )
        except (TypeError, ValueError) as e:
            formatted_transcription += f"{text}<br>"
            continue

    # Inject JavaScript for seeking
    st.markdown("""
        <script>
        function seekVideo(video_id, time) {
            var vid = document.getElementById(video_id);
            if (vid) {
                vid.currentTime = time;
                vid.play();
            }
        }
        </script>
    """, unsafe_allow_html=True)

    st.markdown(f"<div style='font-size:18px;'>{formatted_transcription}</div>", unsafe_allow_html=True)

### END
### ________________________________________________________________
