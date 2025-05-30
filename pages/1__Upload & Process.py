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
from src.proc_nudity import extract_nudity_sequences
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
from styles.styles import spacer

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
def analyze_video(video_path, output_dir, models, mode="Violence + Audio Detection"):
    """Analyzes the video content with automatic cleanup of temporary files.

    Args:
        video_path: Path to the video file
        output_dir: Directory to store processed files
        models: Dictionary of loaded models
        mode: Detection mode ("Violence + Audio Detection" or "Nudity + Audio Detection")
    """
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

            # Common processing steps for both modes
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

            # Mode-specific video processing
            with st.spinner("Analyzing video frames..."):
                frames_path = os.path.join(output_dir, "processed_frames")

                if mode == "Violence + Audio Detection":
                    frame_count, predictions_per_frame, confidence_scores_by_class, harmful_sequences = extract_frame_sequences(
                        video_path,
                        frames_path,
                        models['violence_model'],
                        models['violence_class_names'],
                        sequence_length=16,
                        progress_callback=lambda: progress_with_cancel_check(update_progress),
                    )
                    # Prepare scores for violence mode
                    harmful_score_visual = confidence_scores_by_class.get('Violence', 0.0)
                    safe_score_visual = confidence_scores_by_class.get('Safe', 0.0)
                else:  # Nudity + Text mode
                    frame_count, predictions_per_frame, confidence_scores_by_class, harmful_sequences = extract_nudity_sequences(
                        video_path,
                        frames_path,
                        models['nudity_model'],
                        models['nudity_class_names'],
                        sequence_length=16,
                        progress_callback=lambda: progress_with_cancel_check(update_progress),
                    )
                    # Prepare scores for nudity mode
                    harmful_score_visual = confidence_scores_by_class.get('nude', 0.0)
                    safe_score_visual = confidence_scores_by_class.get('safe', 0.0)

            with st.spinner("Calculating final results..."):
                bert_scores = {
                    'safe': safe_conf_text,
                    'harmful': harmful_conf_text
                }

                # With:
                if mode == "Violence + Audio Detection":
                    visual_scores = {
                        'safe': safe_score_visual,
                        'harmful': harmful_score_visual
                    }
                else:  # Nudity + Audio Detection mode
                    visual_scores = {
                        'safe': safe_score_visual,
                        'nude': harmful_score_visual  # Use 'nude' key for nudity mode
                    }

                # Use mode-specific fusion
                final_prediction, final_confidence = weighted_fusion(
                    bert_scores,
                    visual_scores,
                    mode="violence" if mode == "Violence + Audio Detection" else "nudity"
                )

            with st.spinner("Generating processed video..."):
                processed_video_path = os.path.join(output_dir, f"processed_{os.path.basename(output_dir)}.mp4")
                combine_frames_to_video(frames_path, processed_video_path, frame_count, audio_path)
                update_progress()

            # Prepare results dictionary
            results = {
                "mode": mode,
                "harmful_score_visual": harmful_score_visual,
                "safe_score_visual": safe_score_visual,
                "visual_scores": visual_scores,
                "harmful_conf_text": harmful_conf_text,
                "safe_conf_text": safe_conf_text,
                "bert_scores": bert_scores,
                "final_prediction": final_prediction,
                "final_confidence": final_confidence,
                "transcription": transcription,
                "highlighted_text": highlighted_text,
                "processing_time": time.time() - start_time,
            }

            # Add mode-specific keys for backward compatibility
            if mode == "Violence + Audio Detection":
                results.update({
                    "harmful_score_resnet": harmful_score_visual,
                    "safe_score_resnet": safe_score_visual,
                    "resnet_scores": visual_scores
                })
            else:
                results.update({
                    "nude_score": harmful_score_visual,
                    "safe_score_nudity": safe_score_visual
                })

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

def display_results(results, output_dir, mode="Violence + Audio Detection"):
    """Displays the analysis results in the Streamlit app."""
    st.subheader("Analysis Results")

    # Final verdict with color coding
    verdict_color = "red" if results['final_prediction'] == "Harmful" else "green"
    st.markdown(
        f"""
    <div style='padding: 10px; border-radius: 5px; background-color: {verdict_color}; color: white; text-align: center;'>
    <h3>CLASSIFIED AS: {results['final_prediction'].upper()}</h3>
    <p>Confidence: {results['final_confidence'] * 100:.2f}%</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    spacer(20)

    # Create expandable section for metrics
    with st.expander("View Detailed Metrics"):
        # Metrics row - update to use mode-specific keys
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1:
            text_harm_score = 1 - results['safe_conf_text']
            text_delta = (0.5 - results['safe_conf_text']) * 200
            st.metric(
                label="Text Harmful",
                value=f"{text_harm_score * 100:.2f}%",
                delta=f"{text_delta:.2f}%",
                delta_color="inverse",  # Red if increasing harm
            )
        with metric_col2:
            visual_harmful = results['harmful_score_resnet'] if mode == "Violence + Audio Detection" else results['nude_score']
            visual_delta = (visual_harmful - 0.5) * 200
            st.metric(
                label="Visual Harmful" if mode == "Violence + Audio Detection" else "Nudity",
                value=f"{visual_harmful * 100:.2f}%",
                delta=f"{visual_delta:.2f}%",
                delta_color="inverse",  # Red if increasing harm
            )
        with metric_col3:
            overall_conf = results['final_confidence']
            is_harmful = results['final_prediction'] == "Harmful"
            st.metric(
                label="Overall Harmful",
                value=f"{overall_conf * 100:.2f}%" if is_harmful else f"{(1 - overall_conf) * 100:.2f}%",
                delta="Harmful" if is_harmful else "Safe",
                delta_color="inverse" if is_harmful else "normal",
            )

        # Explanation and calculations
        st.markdown("---")
        text_harmful = results['harmful_conf_text']
        visual_harmful = results['harmful_score_resnet'] if mode == "Violence + Audio Detection" else results['nude_score']

        bert_weight = 0.4
        visual_weight = 0.6

        if mode != "Violence + Audio Detection" and visual_harmful > 0.7:
            bert_weight = 0.2
            visual_weight = 0.8

        combined_harmful = text_harmful * bert_weight + visual_harmful * visual_weight
        if mode != "Violence + Audio Detection" and visual_harmful > 0.85:
            combined_harmful = max(combined_harmful, visual_harmful * 1.1)
            combined_harmful = min(combined_harmful, 1.0)

        if mode == "Violence + Audio Detection":
            col1, col2 = st.columns(2)
            with col1:
                st.write("#### Determining the Final Verdict")
                st.markdown(f"""
                <div style='background-color: #f0f2f6; padding: 15px; border-radius: 5px;'>
                <p style='font-size: 16px;'>For this video, we combined:</p>
                <ul>
                  <li>Text analysis detected <b>{text_harmful*100:.1f}%</b> harmful content (weighted at <b>{bert_weight*100:.0f}%</b>)</li>
                  <li>Visual analysis detected <b>{visual_harmful*100:.1f}%</b> violent content (weighted at <b>{visual_weight*100:.0f}%</b>)</li>
                </ul>
                <p>This gives a final harmful score of <b>{combined_harmful*100:.1f}%</b>, making the verdict <b>{results['final_prediction']}</b>.</p>
                </div>
                """, unsafe_allow_html=True)
                st.text("")
                st.text("")
                st.text("")
                st.info("""
                Our system balances what is said (text) and what is shown (visual content).
                For violence detection, we give slightly more importance to what we see (60%) 
                compared to what is said (40%).
                """)

            with col2:
                # Show raw calculation code inline
                st.markdown("#### Behind the Calculation")
                override_note = ""
                if mode != "Violence + Audio Detection" and visual_harmful > 0.85:
                    override_note = (
                        f"<br><b>Note:</b> Visual score exceeded 85%, so we applied an override: "
                        f"Combined = max({combined_harmful:.4f}, {visual_harmful:.4f} × 1.1) → "
                        f"Final = <b>{combined_harmful:.4f}</b> (capped at 1.0 if needed)."
                    )

                st.markdown(f"""
                <div style='background-color: #f0f2f6; padding: 15px; border-radius: 5px;'>
                <b>1. Mode: {mode}</b><br>
                Text Score = <u>{text_harmful:.4f}</u>&emsp;
                Visual Score = <u>{visual_harmful:.4f}</u>

                <br><b>2. Weights</b>:<br>
                Text Weight = <u>{bert_weight:.1f}</u>&emsp;
                Visual Weight = <u>{visual_weight:.1f}</u>

                <b>3. Harmful Combined Score</b>:<br>
                (<b>{text_harmful:.4f}</b> × {bert_weight:.1f}) + (<b>{visual_harmful:.4f}</b> × {visual_weight:.1f}) = 
                <b>{text_harmful * bert_weight:.4f}</b> + <b>{visual_harmful * visual_weight:.4f}</b> = 
                <b>{combined_harmful:.4f}</b>{override_note}

                <b>4.</b> If Combined Score > 0.5 → <b>Harmful</b>&emsp;Else → <b>Safe</b>:<br>
                Final Decision: <u>{results['final_prediction']}</u><br>
                Final Confidence: <u>{results['final_confidence']:.4f}</u>
                </div>
                """, unsafe_allow_html=True)
        else:
            override_applied = visual_harmful > 0.85
            st.markdown(f"""
            <div style='background-color: #f0f2f6; padding: 15px; border-radius: 5px;'>
            <p style='font-size: 16px;'>For this video, we combined:</p>
            <ul>
              <li>Text analysis detected <b>{text_harmful*100:.1f}%</b> harmful content (weighted at <b>{bert_weight*100:.0f}%</b>)</li>
              <li>Visual analysis detected <b>{visual_harmful*100:.1f}%</b> nudity (weighted at <b>{visual_weight*100:.0f}%</b>)</li>
            </ul>
            {"<p><b>Note:</b> High nudity detection triggered special handling.</p>" if override_applied else ""}
            <p>This gives a final harmful score of <b>{combined_harmful*100:.1f}%</b>, making the verdict <b>{results['final_prediction']}</b>.</p>
            </div>
            """, unsafe_allow_html=True)

            st.info("""
            For nudity detection, we adjust our approach based on confidence:
            
            • When nudity is detected with high confidence (>70%), we give more weight (80%) 
              to what we see and less (20%) to what is said
              
            • With very high nudity confidence (>85%), we may override the text analysis completely,
              as visual evidence becomes the primary factor
            """)

    st.text("")
    st.text("")

    # Detailed results in tabs
    tab1, tab2, tab3 = st.tabs(["Text Analysis", "Visual Analysis", "Transcription"])

    with tab1:
        st.write("#### Text Classification")
        st.progress(results['safe_conf_text'], text=f"Safe Content: {results['safe_conf_text'] * 100:.2f}%")
        st.progress(
            results['harmful_conf_text'], text=f"Harmful Content: {results['harmful_conf_text'] * 100:.2f}%"
        )
        st.markdown('---')
        st.write("#### Highlighted Toxic Content")
        st.markdown(f"<div style='font-size:16px;'>{results['highlighted_text']}</div>", unsafe_allow_html=True)

    with tab2:
        st.write("#### Visual Classification")
        if mode == "Violence + Audio Detection":
            violence_percentage = results['harmful_score_resnet']
            safe_percentage = 1 - violence_percentage
            st.progress(safe_percentage, text=f"Safe: {safe_percentage * 100:.2f}%")
            st.progress(violence_percentage, text=f"Violent: {violence_percentage * 100:.2f}%")
        else:
            nude_percentage = results['nude_score']
            safe_percentage = 1 - nude_percentage
            st.progress(safe_percentage, text=f"Safe: {safe_percentage * 100:.2f}%")
            st.progress(nude_percentage, text=f"Nudity: {nude_percentage * 100:.2f}%")

        sequences = get_detected_sequences(output_dir)
        if sequences:
            st.markdown('---')
            st.write(f"**Detected {len(sequences)} {'violent' if mode == 'Violence + Audio Detection' else 'nudity'} sequences**")
            for i in range(0, len(sequences), 3):
                cols = st.columns(3)
                for col_idx in range(3):
                    if i + col_idx < len(sequences):
                        with cols[col_idx]:
                            st.markdown(f"**Sequence {i + col_idx + 1}**")
                            st.image(sequences[i + col_idx]['gif_path'], use_container_width=True)

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
            # Check file size before downloading
            file_size_mb = video_stream.filesize / (1024 * 1024)
            if file_size_mb > 500:
                raise ValueError(f"Video file is too large ({file_size_mb:.1f}MB). Maximum size is 500MB.")
                
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
    st.title("Analyze Video")
    # Load models
    # Use pre-loaded models instead of loading here
    if 'models' not in st.session_state or st.session_state.models is None:
        st.error("AI models failed to load. Please refresh the page.")
        return

    models = st.session_state.models  # Use the pre-loaded models

    logo_path = "images/Buddyguard_4_3.png"
    st.html("""
      <style>
        [alt=Logo] {
          height: 10rem;
        }
      </style>
            """)

    st.logo(logo_path)

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

    st.subheader("Detection Mode")
    detection_mode = st.radio(
        "Select detection type:",
        ("Violence + Audio Detection", "Nudity + Audio Detection"),
        index=0,
        horizontal=True
    )

    # File upload section
    with st.container():
        # Create two columns for upload and YouTube download
        col_upload, col_youtube = st.columns(2)
        
        # Left column: File Upload
        with col_upload:
            st.markdown("### Upload from Device")
            uploaded_file = st.file_uploader(
                "Upload a video file", 
                type=["mp4", "avi", "mov", "webm", "mpg", "mkv"], 
                key="file_uploader"
            )

            if uploaded_file is not None:
                if uploaded_file.size > 500 * 1024 * 1024:
                    st.error("File too large. Maximum size is 500MB.")
                else:
                    try:
                        video_path, video_name, output_dir = save_uploaded_video(uploaded_file)
                        st.session_state.uploaded_video = video_path
                        st.session_state.video_name = video_name
                        st.session_state.output_dir = output_dir
                        st.session_state.processing_complete = False
                        st.session_state.show_results = False
                        st.success("Video uploaded successfully!")
                    except ValueError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Error processing video: {str(e)}")

        # Right column: YouTube Download
        with col_youtube:
            st.markdown("### Download from YouTube")
            youtube_url = st.text_input(
                "Enter YouTube video URL",
                placeholder="Paste your YouTube link here",
                key="youtube_url",
            )

            if st.button("Download Video", key="upload_yt"):
                if youtube_url:
                    video_path, video_name, output_dir = download_youtube_video(youtube_url)
                    if video_path:
                        st.session_state.uploaded_video = video_path
                        st.session_state.video_name = video_name
                        st.session_state.output_dir = output_dir
                        st.session_state.processing_complete = False
                        st.session_state.show_results = False
                        st.success("Video downloaded successfully!")

    st.markdown("---")

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
                    st.session_state.uploaded_video, st.session_state.output_dir, models, detection_mode
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

    st.markdown("---")

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

        display_results(st.session_state.analysis_results, st.session_state.output_dir, detection_mode)

        spacer(20)

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