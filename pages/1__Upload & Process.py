# pages/1__Upload & Process.py

import glob
import logging
import os
import time
import streamlit as st
from pytubefix import YouTube
from slugify import slugify

# Import custom modules
from src.proc_audio import extract_audio, transcribe_audio, display_transcription_with_timestamps
from src.proc_text import classify_text
from src.proc_video import combine_frames_to_video
from src.proc_video_sequence import extract_frame_sequences
from src.utils import (
    is_portrait_video,
    get_total_frames,
    calculate_average_scores,
    weighted_fusion,
    save_results,
    get_detected_sequences,
    get_video_duration
)


# --- Initialize Session State ---
if 'uploaded_video' not in st.session_state:
    st.session_state.uploaded_video = None
if 'cancel_processing' not in st.session_state:
    st.session_state.cancel_processing = False
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'show_results' not in st.session_state:
    st.session_state.show_results = False
if 'video_name' not in st.session_state:
    st.session_state.video_name = None
if 'output_dir' not in st.session_state:
    st.session_state.output_dir = None
if 'download_progress' not in st.session_state:
    st.session_state.download_progress = None
if 'models' not in st.session_state:
    st.session_state.models = None

# At the top of your file
CLEANUP_TEMP_FILES = True  # Can be made configurable via st.toggle()

# --- Helper Functions ---
def analyze_video(video_path, output_dir, models):
    """Analyzes the video content with automatic cleanup of temporary files."""
    start_time = time.time()
    progress_bar = st.progress(0)
    processing_status = st.empty()
    st.session_state.cancel_processing = False
    total_frames = get_total_frames(video_path)
    total_work = total_frames + 2  # Frames + audio processing + final processing
    current_work = [0]

    def update_progress(increment=1):
        current_work[0] += increment
        progress_percentage = min(current_work[0] / total_work, 1.0)
        progress_bar.progress(progress_percentage)
        if st.session_state.cancel_processing:
            st.warning("Process cancelled by user")
            st.stop()

    try:
        with processing_status.container():
            st.spinner(f"Analyzing video: {os.path.basename(video_path)}")
            if st.button("Cancel Process", type="secondary", use_container_width=True, key="cancel_btn"):
                st.session_state.cancel_processing = True
                st.warning("Cancelling process...")
                st.stop()

            with st.spinner("Extracting audio..."):
                audio_path = os.path.join(output_dir, "output_audio.wav")
                extract_audio(video_path, audio_path)
                update_progress()

            with st.spinner("Transcribing audio..."):
                transcription = transcribe_audio(audio_path, models['whisper_model'])
                update_progress()

            with st.spinner("Analyzing text content..."):
                text_label, harmful_conf_text, safe_conf_text, highlighted_text = classify_text(
                    transcription, models['bert_model'], models['tokenizer'], models['device']
                )
                update_progress()

            with st.spinner("Analyzing video frames..."):
                frames_path = os.path.join(output_dir, "processed_frames")
                frame_count, predictions_per_frame, confidence_scores_by_class, harmful_sequences = extract_frame_sequences(
                    video_path,
                    frames_path,
                    models['resnet_model'],
                    models['class_names'],
                    sequence_length=16,
                    progress_callback=lambda: progress_with_cancel_check(update_progress),
                )

            with st.spinner("Calculating final results..."):
                average_confidence_by_class = calculate_average_scores(confidence_scores_by_class)
                harmful_score_resnet = average_confidence_by_class.get('Violence', 0.0)
                safe_score_resnet = average_confidence_by_class.get('Safe', 0.0)

                bert_scores = {'safe': safe_conf_text, 'harmful': harmful_conf_text}
                resnet_scores = {'safe': safe_score_resnet, 'harmful': harmful_score_resnet}
                final_prediction, final_confidence = weighted_fusion(
                    bert_scores, resnet_scores, bert_weight=0.5, resnet_weight=0.5
                )

            with st.spinner("Generating processed video..."):
                processed_video_path = os.path.join(output_dir, f"processed_{os.path.basename(output_dir)}.mp4")
                combine_frames_to_video(frames_path, processed_video_path, frame_count, audio_path)
                update_progress()

            results = {
                "harmful_score_resnet": harmful_score_resnet,
                "safe_score_resnet": safe_score_resnet,
                "resnet_scores": resnet_scores,
                "harmful_conf_text": harmful_conf_text,
                "safe_conf_text": safe_conf_text,
                "bert_scores": bert_scores,
                "final_prediction": final_prediction,
                "final_confidence": final_confidence,
                "transcription": transcription,
                "highlighted_text": highlighted_text,
                "processing_time": time.time() - start_time,
            }
            save_results(output_dir, os.path.basename(output_dir), results)

            if CLEANUP_TEMP_FILES:
                cleanup_temp_files(output_dir)

            return results, processed_video_path

    except Exception as e:
        st.error(f"Error during processing: {str(e)}")
        # Attempt cleanup even if processing failed
        try:
            cleanup_temp_files(output_dir)
        except Exception as cleanup_error:
            st.warning(f"Additional error during cleanup: {str(cleanup_error)}")
        raise e

def cleanup_temp_files(output_dir):
    """Remove temporary files after video processing while preserving essential results."""
    try:
        # Files to remove
        temp_files = [
            os.path.join(output_dir, "video.mp4"),  # Original video
            os.path.join(output_dir, "output_audio.wav"),  # Temporary audio
            os.path.join(output_dir, f"{os.path.basename(output_dir)}.mp4")  # Original uploaded file if exists
        ]

        # Directories to clean
        temp_dirs = [
            os.path.join(output_dir, "processed_frames")  # Frame images
        ]

        # Remove files
        for file_path in temp_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Removed temporary file: {file_path}")

        # Clean directories (remove contents but keep directory structure)
        for dir_path in temp_dirs:
            if os.path.exists(dir_path):
                for file_name in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file_name)
                    try:
                        if os.path.isfile(file_path) and not file_name.endswith('.gif'):  # Keep GIFs
                            os.remove(file_path)
                            logging.info(f"Removed temporary frame: {file_path}")
                    except Exception as e:
                        st.warning(f"Couldn't remove {file_path}: {str(e)}")

    except Exception as e:
        st.warning(f"Cleanup warning: {str(e)}")
        raise

def display_results(results, output_dir):
    """Displays the analysis results in the Streamlit app."""
    st.subheader("Analysis Results")

    # Final verdict with color coding
    verdict_color = "red" if results['final_prediction'] == "Harmful" else "green"
    st.markdown(
        f"""
    <div style='padding: 10px; border-radius: 5px; background-color: {verdict_color}; color: white; text-align: center;'>
    <h3>VERDICT: {results['final_prediction'].upper()}</h3>
    <p>Confidence: {results['final_confidence'] * 100:.2f}%</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Metrics row
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric(
            "Text Harmful",
            f"{(1 - results['safe_conf_text']) * 100:.2f}%",
            f"{(0.5 - results['safe_conf_text']) * 200:.2f}%"
            if results['safe_conf_text'] < 0.5
            else f"{(0.5 - results['safe_conf_text']) * 200:.2f}%",
        )
    with metric_col2:
        st.metric(
            "Visual Harmful",
            f"{(1 - results['safe_score_resnet']) * 100:.2f}%",
            f"{(0.5 - results['safe_score_resnet']) * 200:.2f}%"
            if results['safe_score_resnet'] < 0.5
            else f"{(0.5 - results['safe_score_resnet']) * 200:.2f}%",
        )
    with metric_col3:
        st.metric(
            "Overall Harmful",
            f"{results['final_confidence'] * 100:.2f}%"
            if results['final_prediction'] == "Harmful"
            else f"{(1 - results['final_confidence']) * 100:.2f}%",
            "Harmful" if results['final_prediction'] == "Harmful" else "Safe",
        )

    # Detailed results in tabs
    tab1, tab2, tab3 = st.tabs(["Text Analysis", "Visual Analysis", "Transcription"])

    with tab1:
        st.write("#### Text Classification")
        st.progress(results['safe_conf_text'], text=f"Safe Content: {results['safe_conf_text'] * 100:.2f}%")
        st.progress(
            results['harmful_conf_text'], text=f"Harmful Content: {results['harmful_conf_text'] * 100:.2f}%"
        )
        st.write("#### Highlighted Toxic Content")
        st.markdown(f"<div style='font-size:16px;'>{results['highlighted_text']}</div>", unsafe_allow_html=True)

    with tab2:
        st.write("#### Visual Classification")
        violence_percentage = results['harmful_score_resnet']
        safe_percentage = 1 - violence_percentage
        st.progress(safe_percentage, text=f"Safe: {safe_percentage * 100:.2f}%")
        st.progress(violence_percentage, text=f"Violent: {violence_percentage * 100:.2f}%")

        sequences = get_detected_sequences(output_dir)
        if sequences:
            st.write(f"**Detected {len(sequences)} violent sequences**")
            for i in range(0, len(sequences), 2):
                cols = st.columns(2)
                for col_idx in range(2):
                    if i + col_idx < len(sequences):
                        with cols[col_idx]:
                            st.markdown(f"**Sequence {i + col_idx + 1}**")
                            st.image(sequences[i + col_idx]['gif_path'], use_container_width=True)
        else:
            st.info("No violent sequences detected")

    with tab3:
        display_transcription_with_timestamps(results['transcription'], "results_video_player")

def download_youtube_video(youtube_url):
    """Downloads a YouTube video and returns the local file path and video name."""
    try:
        yt = YouTube(
            youtube_url,
            on_progress_callback=lambda stream, chunk, bytes_remaining: st.session_state.download_progress.progress(
                1 - (bytes_remaining / stream.filesize)
            ),
        )

        # Check duration before downloading
        if yt.length < 10:
            raise ValueError(f"Video is too short ({yt.length} seconds). Minimum length is 10 seconds.")
        if yt.length > 180:
            raise ValueError(f"Video is too long ({yt.length} seconds). Maximum length is 180 seconds.")

        video_stream = yt.streams.filter(file_extension='mp4').first()
        if video_stream:
            safe_title = slugify(yt.title, max_length=50, word_boundary=True, save_order=True)
            video_name = safe_title[:50]
            # Only create new folder if processing output exists in existing folder
            output_dir, video_name = get_unique_output_dir("output", video_name, check_processing_output=True)
            video_path = os.path.join(output_dir, "video.mp4")

            st.session_state.download_progress = st.progress(0)
            with st.spinner(f"Downloading: {yt.title[:50]}..."):
                video_stream.download(output_path=output_dir, filename="video.mp4")
            st.session_state.download_progress.empty()
            return video_path, video_name, output_dir
        else:
            st.error("No suitable video stream found")
            return None, None, None
    except Exception as e:
        st.error(f"Error downloading video: {str(e)}")
        return None, None, None

def get_unique_output_dir(base_dir, video_name, check_processing_output=False):
    """
    Creates a unique output directory.
    If check_processing_output is True, will only create new folder if processing output exists.
    """
    counter = 1
    original_name = video_name

    # First try with the original name
    output_dir = os.path.join(base_dir, video_name)

    # If we're not checking for processing output or if no processing output exists
    if not check_processing_output or not processing_output_exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        return output_dir, video_name

    # If processing output exists, start incrementing
    while True:
        video_name = f"{original_name} ({counter})"
        output_dir = os.path.join(base_dir, video_name)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            return output_dir, video_name
        # If folder exists but has no processing output, use it
        if not processing_output_exists(output_dir):
            return output_dir, video_name
        counter += 1

def processing_output_exists(output_dir):
    """Check if processing output files already exist in the directory."""
    # Check for the processed video file
    processed_video_pattern = os.path.join(output_dir, "processed_*.mp4")
    if glob.glob(processed_video_pattern):
        return True

    # Check for results JSON file
    results_file = os.path.join(output_dir, "results.json")
    if os.path.exists(results_file):
        return True

    return False

def progress_with_cancel_check(update_fn):
    """Wrapper for progress callback that checks for cancellation."""
    if st.session_state.cancel_processing:
        st.warning("Process cancelled by user")
        st.stop()
    update_fn()

def save_uploaded_video(uploaded_file):
    """Saves the uploaded video file and returns the local file path and video name."""
    video_name = slugify(os.path.splitext(uploaded_file.name)[0], lowercase=False, max_length=50)
    # Only create new folder if processing output exists in existing folder
    output_dir, video_name = get_unique_output_dir("output", video_name, check_processing_output=True)
    video_path = os.path.join(output_dir, f"{video_name}.mp4")

    with st.spinner("Saving uploaded video..."):
        with open(video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Check video duration
        duration = get_video_duration(video_path)
        if duration < 10:
            os.remove(video_path)
            os.rmdir(output_dir)  # Clean up the empty directory
            raise ValueError(f"Video is too short ({duration:.1f} seconds). Minimum length is 10 seconds.")
        if duration > 180:
            os.remove(video_path)
            os.rmdir(output_dir)  # Clean up the empty directory
            raise ValueError(f"Video is too long ({duration:.1f} seconds). Maximum length is 180 seconds.")

    return video_path, video_name, output_dir

# --- Main Streamlit App ---
def main():
    st.title("Upload & Process Video")

    # Load models
    # Use pre-loaded models instead of loading here
    if 'models' not in st.session_state or st.session_state.models is None:
        st.error("AI models failed to load. Please refresh the page.")
        return

    models = st.session_state.models  # Use the pre-loaded models

    # Add CSS to control video size
    st.markdown(
        """
    <style>
        .portrait-video video { max-height: 200px !important; margin: 0 auto; display: block; }
        .stImage { margin-bottom: 10px; }
        .stImage img { border-radius: 5px; border: 1px solid #ddd; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # File upload section
    with st.container():
        st.subheader("Upload Video")
        col1, col2 = st.columns([3, 1])
        youtube_url = col1.text_input(
            "Enter YouTube video URL",
            placeholder="Paste your YouTube link here",
            label_visibility="collapsed",
            key="youtube_url",
        )

        if col2.button("Upload YouTube Video", key="upload_yt"):
            if youtube_url:
                video_path, video_name, output_dir = download_youtube_video(youtube_url)
                if video_path:
                    st.session_state.uploaded_video = video_path
                    st.session_state.video_name = video_name
                    st.session_state.output_dir = output_dir
                    st.session_state.processing_complete = False
                    st.session_state.show_results = False
                    st.success("Video downloaded successfully!")

        uploaded_file = st.file_uploader(
            "Or upload a video file", type=["mp4", "avi", "mov", "webm", "mpg"], key="file_uploader"
        )

        if uploaded_file is not None:
            if uploaded_file.size > 100 * 1024 * 1024:
                st.error("File too large. Maximum size is 100MB.")
            else:
                try:
                    video_path, video_name, output_dir = save_uploaded_video(uploaded_file)
                    st.session_state.uploaded_video = video_path
                    st.session_state.video_name = video_name
                    st.session_state.output_dir = output_dir
                    st.session_state.processing_complete = False
                    st.session_state.show_results = False
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Error processing video: {str(e)}")

    # Show uploaded video preview
    if st.session_state.uploaded_video is not None:
        video_path = st.session_state.uploaded_video

        col1, col2, col3 = st.columns(3)

        with col2:
            st.subheader("Video Preview")
            if os.path.exists(video_path):
                if is_portrait_video(video_path):
                    st.markdown('<div class="portrait-video">', unsafe_allow_html=True)
                    st.video(video_path)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.video(video_path)

        # Only show process button if not already processed
        if not st.session_state.processing_complete:
            if st.button("Analyze Video", type="primary", use_container_width=True, key="analyze_btn"):
                st.session_state.processing_complete = False
                st.session_state.show_results = False
                results, processed_video_path = analyze_video(
                    st.session_state.uploaded_video, st.session_state.output_dir, models
                )
                if results:
                    st.session_state.processing_complete = True
                    st.session_state.show_results = True
                    st.session_state.processed_video_path = processed_video_path
                    st.session_state.analysis_results = results
                    processing_time = results['processing_time']
                    minutes, seconds = divmod(processing_time, 60)
                    time_str = f"{int(minutes)}m {int(seconds)}s" if minutes > 0 else f"{int(seconds)} seconds"
                    st.success(f"Analysis complete! Processing time: {time_str}")
                    st.balloons()

    # Show results only after processing is complete
    if st.session_state.show_results and st.session_state.processing_complete and 'analysis_results' in st.session_state:
        # Show processed video
        processed_video_path = st.session_state.get("processed_video_path")
        col1, col2, col3 = st.columns(3)

        with col2:
            st.subheader("Processed Video")
            if processed_video_path and os.path.exists(processed_video_path):
                if is_portrait_video(processed_video_path):
                    st.markdown('<div class="portrait-video">', unsafe_allow_html=True)
                    st.video(processed_video_path)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.video(processed_video_path)

        display_results(st.session_state.analysis_results, st.session_state.output_dir)

        # Clear button
        if st.button("Start New Analysis", type="primary", key="new_analysis"):
            st.session_state.uploaded_video = None
            st.session_state.processing_complete = False
            st.session_state.show_results = False
            st.session_state.cancel_processing = False
            st.session_state.video_name = None
            st.session_state.output_dir = None
            st.session_state.analysis_results = None
            st.session_state.processed_video_path = None
            st.rerun()


if __name__ == "__main__":
    main()