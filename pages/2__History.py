# pages/2__History.py

import os
import json
import streamlit as st
import tempfile
from streamlit_pdf_viewer import pdf_viewer
from src.proc_audio import display_transcription_with_timestamps
from src.utils import save_to_pdf, is_portrait_video, get_detected_sequences
from styles.styles import spacer

# History page
st.title("View Processed Videos")

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
st.markdown("""
    <style>
    .portrait-video video { max-height: 200px !important; margin: 0 auto;  display: block; }
    .stImage { margin-bottom: 10px; }
    .stImage img { border-radius: 5px; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True
)

history_file = "saves/processed_videos.json"
if os.path.exists(history_file):
    with open(history_file, "r") as f:
        history = json.load(f)

    if not history:
        st.info("No processed videos found. Process some videos in the Upload tab first.")
    else:
        selected_video = st.selectbox("Select a processed video:", list(history.keys()))
        if selected_video:
            results = history[selected_video]
            video_name = os.path.splitext(selected_video)[0]

            # Determine detection mode
            mode = results.get('mode', 'Violence + Text')  # Default to violence for backward compatibility

            col1, col2, col3 = st.columns(3)
            with col2:
                video_path = os.path.join("output", video_name, f"processed_{video_name}.mp4")
                if os.path.exists(video_path):
                    if is_portrait_video(video_path):
                        st.markdown('<div class="portrait-video">', unsafe_allow_html=True)
                        st.video(video_path)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.video(video_path)
                else:
                    st.warning("Processed video not found!")

            # Final verdict with color coding
            verdict_color = "red" if results['final_prediction'] == "Harmful" else "green"
            st.markdown(f"""
            <div style='padding: 10px; border-radius: 5px; background-color: {verdict_color}; color: white; text-align: center;'>
            <h3>CLASSIFIED AS: {results['final_prediction'].upper()}</h3>
            <p>Confidence: {results['final_confidence'] * 100:.2f}%</p>
            </div>
            """, unsafe_allow_html=True)

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

            # Create tabs for different analysis sections
            tab1, tab2, tab3, tab4 = st.tabs(["Text Analysis", "Visual Analysis", "Transcription", "PDF"])

            with tab1:
                st.write("#### Text Classification")
                st.progress(results['safe_conf_text'], text=f"Safe Content: {results['safe_conf_text'] * 100:.2f}%")
                st.progress(results['harmful_conf_text'], text=f"Harmful Content: {results['harmful_conf_text'] * 100:.2f}%")
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
                
                # Get sequences from the original output folder
                output_dir = os.path.join("output", video_name)
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
                st.write("### Timestamp and Transcription")
                display_transcription_with_timestamps(results['transcription'], "video_player")

            with tab4:
                # Create a temporary file for PDF viewing
                if 'temp_pdf_path' not in st.session_state:
                    st.session_state.temp_pdf_path = None
                
                # Generate PDF for viewing as soon as the tab is opened
                try:
                    # Create a temporary directory that will be automatically cleaned up
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Add download button
                        # Generate permanent PDF for download
                        pdf_save_path = os.path.join("saves", "reports", video_name, f"{video_name}_report.pdf")
                        os.makedirs(os.path.dirname(pdf_save_path), exist_ok=True)
                        save_to_pdf(video_name, history_file, output_path=pdf_save_path)
                        
                        with open(pdf_save_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                            st.download_button(
                                label="Download PDF Report",
                                data=pdf_bytes,
                                file_name=f"{video_name}_report.pdf",
                                mime="application/pdf",
                                type="primary"
                            )

                        temp_pdf_path = os.path.join(temp_dir, f"{video_name}_temp_report.pdf")
                        # Generate PDF report using the existing function
                        save_to_pdf(video_name, history_file, output_path=temp_pdf_path)
                        st.session_state.temp_pdf_path = temp_pdf_path
                        
                        # Display PDF viewer
                        st.markdown('---')
                        pdf_viewer(temp_pdf_path)
                        st.markdown('---')
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")
else:
    st.info("No processed videos found. Process some videos in the Upload tab first.")