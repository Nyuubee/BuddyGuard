import streamlit as st
from styles.styles import spacer

st.title("Threshold Settings (Not functional yet)")

spacer(60)

DEFAULT_WEIGHT_VALUE = 5
DEFAULT_CONFIDENCE_VALUE = 30

# Initialize weight slider values in session state if they don't exist
if 'visual_weight' not in st.session_state:
    st.session_state['visual_weight'] = DEFAULT_WEIGHT_VALUE
if 'textual_weight' not in st.session_state:
    st.session_state['textual_weight'] = DEFAULT_WEIGHT_VALUE

# Initialize temporary weight values for the sliders
if 'temp_visual_weight' not in st.session_state:
    st.session_state['temp_visual_weight'] = st.session_state['visual_weight']
if 'temp_textual_weight' not in st.session_state:
    st.session_state['temp_textual_weight'] = st.session_state['textual_weight']

# Initialize confidence slider values in session state if they don't exist
if 'cnn_confidence' not in st.session_state:
    st.session_state['cnn_confidence'] = DEFAULT_CONFIDENCE_VALUE
if 'bert_confidence' not in st.session_state:
    st.session_state['bert_confidence'] = DEFAULT_CONFIDENCE_VALUE

# Initialize temporary confidence values for the sliders
if 'temp_cnn_confidence' not in st.session_state:
    st.session_state['temp_cnn_confidence'] = st.session_state['cnn_confidence']
if 'temp_bert_confidence' not in st.session_state:
    st.session_state['temp_bert_confidence'] = st.session_state['bert_confidence']

def update_temp_textual_weight():
    """Updates the temporary value of textual weight based on visual weight."""
    st.session_state['temp_textual_weight'] = 10 - st.session_state['temp_visual_weight']

def update_temp_visual_weight():
    """Updates the temporary value of visual weight based on textual weight."""
    st.session_state['temp_visual_weight'] = 10 - st.session_state['temp_textual_weight']

def save_settings():
    """Updates the actual slider values in session state."""
    st.session_state['visual_weight'] = st.session_state['temp_visual_weight']
    st.session_state['textual_weight'] = st.session_state['temp_textual_weight']
    st.session_state['cnn_confidence'] = st.session_state['temp_cnn_confidence']
    st.session_state['bert_confidence'] = st.session_state['temp_bert_confidence']
    st.success("Settings saved!")

def reset_defaults():
    """Resets all temporary and saved slider values to the default and triggers a rerun."""
    st.session_state['temp_visual_weight'] = DEFAULT_WEIGHT_VALUE
    st.session_state['temp_textual_weight'] = 10 - DEFAULT_WEIGHT_VALUE
    st.session_state['visual_weight'] = DEFAULT_WEIGHT_VALUE
    st.session_state['textual_weight'] = 10 - DEFAULT_WEIGHT_VALUE
    st.session_state['temp_cnn_confidence'] = DEFAULT_CONFIDENCE_VALUE
    st.session_state['temp_bert_confidence'] = DEFAULT_CONFIDENCE_VALUE
    st.session_state['cnn_confidence'] = DEFAULT_CONFIDENCE_VALUE
    st.session_state['bert_confidence'] = DEFAULT_CONFIDENCE_VALUE
    st.info("Settings reset to default.")
    st.rerun()  # Trigger a rerun of the Streamlit app

# Check if the reset button was pressed
if st.button("Reset to Default"):
    reset_defaults()

st.subheader("Late Fusion Weights")

# Slider 1 (using temporary value)
st.slider(
    "**Visual Weight:**",
    min_value=0,
    max_value=10,
    value=st.session_state['temp_visual_weight'],
    key="temp_visual_weight",
    on_change=update_temp_textual_weight,  # Now updates the *other* temp value
    help="The weight given to visual features in the late fusion process, The higher the value the more priority (0-10)."
         "\n\nDefault value is 5.",
)


spacer(20)


# Slider 2 (using temporary value)
st.slider(
    "**Textual Weight:**",
    min_value=0,
    max_value=10,
    value=st.session_state['temp_textual_weight'],
    key="temp_textual_weight",
    on_change=update_temp_visual_weight,  # Now updates the *other* temp value
    help="The weight given to textual features in the late fusion process, The higher the value the more priority (0-10)."
         "\n\nDefault value is 5.",
)

st.write("---")

st.subheader("Confidence Thresholds")

# Slider 3 (CNN Confidence)
st.slider(
    "**Resnet Confidence Threshold:**",
    min_value=1,
    max_value=100,
    value=st.session_state['temp_cnn_confidence'],
    key="temp_cnn_confidence",
    help="The minimum confidence score required to be considered harmful imagery (0-100)."
         "\n\nDefault value is 30."
    # No on_change needed as it's independent
)


spacer(20)


# Slider 4 (BERT Confidence)
st.slider(
    "**BERT Confidence Threshold:**",
    min_value=1,
    max_value=100,
    value=st.session_state['temp_bert_confidence'],
    key="temp_bert_confidence",
    help="The minimum confidence score required to be considered detect harmful text (0-100)."
         "\n\nDefault value is 30."
    # No on_change needed as it's independent
)


# Add a spacer with a specific height
spacer1 = st.empty()
spacer1.write("")  # Initially empty
spacer1.markdown("<div style='padding-top: 40px;'></div>", unsafe_allow_html=True)


col1, col2 = st.columns(2)
with col1:
    if st.button("Save Settings"):
        save_settings()


spacer(20)


# Display the current saved values
st.subheader("Current Saved Values:")
st.write(f"Visual Weight: {st.session_state['visual_weight']}")
st.write(f"Textual Weight: {st.session_state['textual_weight']}")
st.write(f"CNN Confidence Threshold: {st.session_state['cnn_confidence']}")
st.write(f"BERT Confidence Threshold: {st.session_state['bert_confidence']}")
st.write(f"Sum of Weights: {st.session_state['visual_weight'] + st.session_state['textual_weight']}")