# pages/4__Tutorial.py

import streamlit as st
from styles.styles import spacer

# Configure the page
st.set_page_config(
    page_title="BuddyGuard Tutorial",
    page_icon="📚",
    layout="wide"
)

logo_path = "images/Buddyguard_4_3.png"
st.html("""
  <style>
    [alt=Logo] {
      height: 10rem;
    }
  </style>
        """)

st.logo(logo_path)

def tutorial_page():
    st.title("BuddyGuard Tutorial 📚")

    # Introduction section
    st.markdown("""
    <div style="
        background-color: #e3f2fd;
        border-left: 6px solid #2196F3;
        padding: 15px;
        margin-bottom: 20px;
        border-radius: 4px;
    ">
        <h3 style="margin-top:0">Welcome to BuddyGuard!</h3>
        <p>This tutorial will guide you through the process of analyzing videos for harmful content using our AI-powered system.</p>
    </div>
    """, unsafe_allow_html=True)

    # Table of Contents
    st.markdown("""
    ## Table of Contents
    - [Step 1: Get Started](#step-1-get-started)
    - [Step 2: Upload a Video](#step-2-upload-a-video)
    - [Step 3: Select Detection Mode](#step-3-select-detection-mode)
    - [Step 4: Understanding Results](#step-4-understanding-results)
        - [A. Interpreting Analysis Results](#a-interpreting-analysis-results)
        - [B. Textual Analysis Results](#b-textual-analysis-results)
        - [C. Visual Analysis Results](#c-visual-analysis-results)
        - [D. Overall Analysis Results](#d-overall-analysis-results)
    - [Step 5: Managing History & Reports](#step-5-managing-history-reports)
        - [A. Reviewing Past Analyses](#a-reviewing-past-analyses)
        - [B. Generating PDF Reports](#b-generating-pdf-reports)
    - [Tips for Best Results](#tips-for-best-results)
    """)

    st.markdown("---")

    # Step 1: Get Started
    with st.container():
        st.header("Step 1: Get Started", anchor="step-1-get-started")
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("""
            ### In the Home page

            Choose one option:

            1. **Get Started**: Press this button to get started on the Upload & Process page.
            2. **Upload & Process page**: You can go to the Upload & Process page by pressing this button in the sidebar.
            """)

        with col2:
            st.image("images/Step 1 Get Started Tutorial.png", use_container_width=True)

    st.markdown("---")
    spacer(20)

    # Step 2: Upload a Video
    with st.container():
        st.header("Step 2: Upload a Video", anchor="step-2-upload-a-video")
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("""
                ### Choose Your Video Source

                BuddyGuard supports two methods for video analysis:

                1. **Upload from Device**: Upload MP4, AVI, MOV, WEBM, MPG, or MKV files directly from your computer.
                2. **YouTube Link**: Provide a YouTube URL to analyze public videos.

                #### Video Requirements:
                - Duration: 10-180 seconds
                - Maximum file size: 500MB
                - Good quality video and audio for best results
                """)

        with col2:
            st.image("images/Step 2 Video Source Tutorial.png", use_container_width=True)

    st.markdown("---")
    spacer(20)

    # Step 3: Select Detection Mode
    with st.container():
        st.header("Step 3: Select Detection Mode", anchor="step-3-select-detection-mode")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("""
            ### Choose Your Detection Method

            BuddyGuard offers two specialized detection modes:

            1. **Violence + Audio Detection**: Analyzes videos for violent scenes and harmful speech.
            2. **Nudity + Audio Detection**: Detects inappropriate visual content and harmful speech.

            #### How to Choose:
            - Select **Violence Detection** for monitoring aggressive content, fights, weapons, etc.
            - Select **Nudity Detection** for filtering inappropriate visual content.
            - Both modes include audio analysis for harmful speech.
            """)

        with col2:
            st.image("images/Step 3 Detection Mode Tutorial.png", use_container_width=True)

    st.markdown("---")
    spacer(20)

    # Step 4: Analysis Results
    with st.container():
        st.header("Step 4: Understanding Results", anchor="step-4-understanding-results")

        col1, col2 = st.columns([1, 1])

        with col1:
            # Section A
            st.markdown('<a name="a-interpreting-analysis-results"></a>', unsafe_allow_html=True)
            st.subheader("A. Interpreting Analysis Results")
            st.markdown("""
            - **What it shows:** This section of the analysis results provides the overall conclusion reached by BuddyGuard regarding the uploaded video, along with a measure of certainty for that conclusion.
            - **VERDICT: HARMFUL:** This is the overall assessment of the video content based on the chosen detection mode (either Violence + Audio or Nudity + Audio). 
            - **Confidence Score:** This percentage represents the level of certainty BuddyGuard has in its verdict.""")

        with col2:
            st.image("images/Step 4 A Processed Video Tutorial.png", use_container_width=True)

        spacer(20)
        col1, col2 = st.columns([1, 1])

        with col1:
            # Section B
            st.markdown('<a name="b-textual-analysis-results"></a>', unsafe_allow_html=True)
            st.subheader("B. Textual Analysis Results")
            st.markdown("""
                    - **What it means:** If you selected a mode that includes audio analysis (both "Violence + Audio" and "Nudity + Audio" do), BuddyGuard will transcribe the spoken content of the video.
                    - **Safe and Harmful Text Scores:** BuddyGuard will analyze the transcribed text and assign scores indicating the likelihood of safe and harmful content within the speech. This allows you to see a more granular breakdown of the audio analysis.
                    - **Detected Transcript with Highlighted Harmful Texts:** The tool will present the full transcript of the audio. Any parts of the transcript that are identified as potentially harmful (based on the "harmful text score") will be visually highlighted. This makes it easy to pinpoint the specific instances of harmful speech.
                    """)

        with col2:
            st.image("images/Step 4 B Detailed Text Analysis Tutorial.png", use_container_width=True)

        spacer(20)
        col1, col2 = st.columns([1, 1])

        with col1:
            # Section C
            st.markdown('<a name="c-visual-analysis-results"></a>', unsafe_allow_html=True)
            st.subheader("C. Visual Analysis Results")
            st.markdown("""
                    - **What it means:** If you selected the "Violence + Audio Detection" mode, BuddyGuard will analyze the video frames for visual indicators of violence.
                    - **Safe and Violent Visual Scores:** Similar to the text scores, BuddyGuard will likely assign scores indicating the likelihood of safe and violent visual content within the video. This provides a quantitative measure of the detected violence.
                    - **Detected Sequences:** The tool might identify and highlight specific segments or sequences within the video where violent content is detected. 
                    """)

        with col2:
            st.image("images/Step 4 C Detailed Visual Analysis Tutorial.png", use_container_width=True)

        spacer(20)
        col1, col2 = st.columns([1, 1])

        with col1:
            # Section D
            st.markdown('<a name="d-overall-analysis-results"></a>', unsafe_allow_html=True)
            st.subheader("D. Overall Analysis Results")
            st.markdown("""
                            - **Text Harmful:** This score tells you how likely the words spoken in the video are to be considered harmful.
                            - **Visual Harmful:** This score indicates how likely the images and actions within the video are to be considered harmful, based on the type of analysis you chose.
                            - **Overall Score:** This is the combined assessment of harmfulness, taking both the audio and visual analysis into account.
                            """)

        with col2:
            st.image("images/Step 4 D Overall Scores Tutorial.png", use_container_width=True)

    st.markdown("---")
    spacer(20)

    # Step 5: History and Reports
    with st.container():
        st.header("Step 5: Managing History & Reports", anchor="step-5-managing-history-reports")

        col1, col2 = st.columns([1, 1])

        with col1:
            # Section A
            st.markdown('<a name="a-reviewing-past-analyses"></a>', unsafe_allow_html=True)
            st.subheader("A. Reviewing Past Analyses")
            st.markdown("""
            This section of BuddyGuard seems to focus on how you can access and review the results of videos you've previously analyzed.

            - **Access Previous Results**: Dropdown menu shows your last 5 analyses
            - **Complete Records**: All details preserved exactly as originally analyzed
            - **Side-by-Side Comparison**: Easily compare multiple analyses
            """)

        with col2:
            st.image("images/Step 5 A History Tutorial.png", use_container_width=True)


        spacer(20)
        col1, col2 = st.columns([1, 1])

        with col1:
            # Section B
            st.markdown('<a name="b-generating-pdf-reports"></a>', unsafe_allow_html=True)
            st.subheader("B. Generating PDF Reports")
            st.markdown("""
            - **Generate PDF Report Button:** Clicking this button initiates the process of compiling the analysis results for the currently viewed video into a PDF document.
            """)

        with col2:
            st.image("images/Step 5 B Generate PDF tutorial.png", use_container_width=True)

    st.markdown("---")

    # Tips and Best Practices
    st.header("Tips for Best Results", anchor="tips-for-best-results")

    tips_cols = st.columns(3)

    with tips_cols[0]:
        st.markdown("""
        ### Video Quality
        - Use clear, well-lit videos
        - Ensure audio is clear and audible
        - Avoid heavy background noise
        - Higher resolution yields better results
        """)

    with tips_cols[1]:
        st.markdown("""
        ### Processing Time
        - Processing time varies with video length
        - Complex videos take longer to analyze
        - Do not refresh page during processing
        - Shorter videos (<60s) process faster
        """)

    with tips_cols[2]:
        st.markdown("""
        ### Accuracy Considerations
        - Review all results manually
        - Check detected sequences
        - Consider context of flagged content
        - Remember AI has limitations
        """)

    st.markdown("---")

    # Call to Action
    st.markdown("""
    <div style="
        text-align: center;
        padding: 20px;
        background-color: #f5f5f5;
        border-radius: 10px;
        margin-top: 20px;
    ">
        <h3>Ready to Try BuddyGuard?</h3>
        <p>Head to the Upload & Process page to get started!</p>
    </div>
    """, unsafe_allow_html=True)

    spacer(20)

    if st.button("Go to Upload & Process", type="primary"):
        st.switch_page("pages/1__Upload & Process.py")


if __name__ == "__main__":
    tutorial_page()