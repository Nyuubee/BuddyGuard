# src/utils.py


# IMPORTS
# ________________________________________________________________
import cv2
import json
import os
import torch
import numpy as np
import streamlit as st
import torchvision.transforms as transforms
from fpdf import FPDF
from PIL import Image
import imageio
from datetime import timedelta

def add_annotation_to_frame(frame, pred, prob, frame_count, fps, class_names):
    """Add prediction overlay to a frame (same as inference code)"""
    timestamp = str(timedelta(seconds=frame_count / fps)).split('.')[0]
    annotated_frame = frame.copy()
    height, width = annotated_frame.shape[:2]

    label = f"{class_names[pred]} ({prob:.2f})"
    color = (0, 255, 0) if pred == 0 else (0, 0, 255)  # Green/Red

    cv2.putText(annotated_frame, label, (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2, cv2.LINE_AA)
    cv2.putText(annotated_frame, f"Time: {timestamp}", (50, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(annotated_frame, f"Frame: {frame_count}", (50, height - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return annotated_frame


def save_sequence_as_gif(frames, preds, probs, frame_numbers, fps, output_dir, sequence_id, video_name, class_names):
    """Save an annotated sequence as GIF"""
    os.makedirs(output_dir, exist_ok=True)
    gif_path = os.path.join(output_dir, f"{video_name}_seq_{sequence_id}_{class_names[preds[-1]]}.gif")

    pil_frames = []
    for i, frame in enumerate(frames):
        annotated_frame = add_annotation_to_frame(
            frame, preds[i], probs[i], frame_numbers[i], fps, class_names
        )
        img = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)

        # Check aspect ratio of the original frame
        height, width = frame.shape[:2]
        is_portrait = height > width

        # Resize based on aspect ratio
        if is_portrait:
            # Portrait (9:16) - maintain height but adjust width
            target_height = 480
            target_width = int(target_height * width / height)
            pil_frames.append(Image.fromarray(img).resize((target_width, target_height)))
        else:
            # Landscape (16:9)
            target_width = 480
            target_height = 270
            pil_frames.append(Image.fromarray(img).resize((target_width, target_height)))

    imageio.mimsave(gif_path, pil_frames, duration=200, loop=0)
    return gif_path

class NumpyTypeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (torch.Tensor, torch.nn.Parameter)):  # Handle PyTorch tensors
            return obj.cpu().detach().numpy().tolist()
        elif isinstance(obj, np.generic):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

def preprocess_image(image):
  transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
  ])
  return transform(image)

def get_total_frames(video_path):
  cap = cv2.VideoCapture(video_path)
  total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
  cap.release()
  return total

# function to select diverse frames to avoid showing similar ones
def select_diverse_frames(nsfw_frames, max_frames=5):
  if not nsfw_frames:
    return []

  if len(nsfw_frames) <= max_frames:
    return nsfw_frames

  # Sort by confidence first
  sorted_frames = sorted(nsfw_frames, key=lambda x: x['confidence'], reverse=True)

  # Take top frame and then select frames that are spaced out
  selected = [sorted_frames[0]]

  # Try to select frames that are spaced out
  spacing = max(1, len(nsfw_frames) // max_frames)
  remaining_slots = max_frames - 1

  for i in range(spacing, len(sorted_frames), spacing):
    if remaining_slots <= 0:
      break
    selected.append(sorted_frames[i])
    remaining_slots -= 1

  return selected

def save_results(output_dir, video_name, results):
    history_file = "./saves/processed_videos.json"
    os.makedirs("./saves", exist_ok=True)

    # Convert all tensors in results to serializable formats
    serializable_results = {}
    for key, value in results.items():
        if isinstance(value, (torch.Tensor, torch.nn.Parameter)):
            serializable_results[key] = value.cpu().detach().numpy().tolist()
        elif isinstance(value, np.ndarray):
            serializable_results[key] = value.tolist()
        elif isinstance(value, (np.float32, np.float64)):
            serializable_results[key] = float(value)
        else:
            serializable_results[key] = value

    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            history = json.load(f)
    else:
        history = {}

    history[video_name] = serializable_results

    with open(history_file, "w") as f:
        json.dump(history, f, cls=NumpyTypeEncoder, indent=4)


def weighted_fusion(bert_scores, resnet_scores, bert_weight=0.4, resnet_weight=0.6):
    # Give more weight to visual violence detection
    if resnet_scores['harmful'] > 0.3:  # If violence is detected with >30% confidence
        resnet_weight = min(resnet_weight * 1.5, 0.8)  # Increase visual weight

    combined_harmful = (bert_scores['harmful'] * bert_weight +
                        resnet_scores['harmful'] * resnet_weight)

    final_prediction = "Harmful" if combined_harmful > 0.5 else "Safe"
    final_confidence = combined_harmful if final_prediction == "Harmful" else 1 - combined_harmful

    return final_prediction, final_confidence

def calculate_average_scores(confidence_scores_by_class):
    averages = {}
    for class_name, scores in confidence_scores_by_class.items():
        if isinstance(scores, (list, tuple)):  # If it's already a list
            averages[class_name] = sum(scores) / len(scores) if scores else 0.0
        else:  # If it's a single float/numpy value
            averages[class_name] = float(scores)
    return averages

def save_to_pdf(video_name, history_file):  # Changed parameter name from result_path to history_file
    output_dir = os.path.join("saves", "reports", video_name)
    os.makedirs(output_dir, exist_ok=True)

    pdf_path = os.path.join(output_dir, f"{video_name}_report.pdf")

    # Load results from the provided history file
    if not os.path.exists(history_file):
        raise FileNotFoundError("Processed videos history file not found!")

    with open(history_file, "r") as f:
        history = json.load(f)

    if video_name not in history:
        raise ValueError(f"Results for '{video_name}' not found in the history file.")

    results = history[video_name]

    # Create PDF object
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Add title
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, txt=f"Analysis Report: {video_name}", ln=True, align="C")
    pdf.ln(10)

    # Add final prediction and confidence
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Final Prediction: {results['final_prediction']} ({results['final_confidence']*100:.2f}%)", ln=True)
    pdf.ln(5)

    # Add Text Classification Results
    pdf.cell(200, 10, txt="Text Classification Results:", ln=True)
    pdf.cell(200, 10, txt=f"- Harmful: {results['harmful_conf_text']*100:.2f}%", ln=True)
    pdf.cell(200, 10, txt=f"- Safe: {results['safe_conf_text']*100:.2f}%", ln=True)
    pdf.ln(5)

    # Add Visual Classification Results
    pdf.cell(200, 10, txt="Video Classification Results:", ln=True)
    pdf.cell(200, 10, txt=f"- Harmful: {results['harmful_score_resnet']*100:.2f}%", ln=True)
    pdf.cell(200, 10, txt=f"- Safe: {results['safe_score_resnet']*100:.2f}%", ln=True)
    pdf.ln(5)

    # Add Transcription
    pdf.cell(200, 10, txt="Video Transcription:", ln=True)
    pdf.ln(5)
    for segment in results["transcription"]:
        pdf.cell(200, 10, txt=f"{segment['start_time']}s: {segment['text']}", ln=True)

    # Save PDF
    pdf.output(pdf_path)
    return pdf_path

def is_portrait_video(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    if ret:
        height, width, _ = frame.shape
        cap.release()
        return height > width
    cap.release()
    return False

def get_video_duration(video_path):
    """Get the duration of a video in seconds."""
    import cv2
    video = cv2.VideoCapture(video_path)
    fps = video.get(cv2.CAP_PROP_FPS)
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps
    video.release()
    return duration

def get_detected_sequences(output_dir):
    """Find all saved GIFs in the processed_frames/detected_sequences subfolder"""
    # Look in the correct nested directory structure
    gif_dir = os.path.join(output_dir, "processed_frames", "detected_sequences")
    if not os.path.exists(gif_dir):
        return []

    return [
        {
            'gif_path': os.path.join(gif_dir, f),
            'name': f.replace('.gif', '')
        }
        for f in sorted(os.listdir(gif_dir))
        if f.endswith('.gif')
    ]

def create_clickable_blog_post_with_image(title, url, summary, image_url, fixed_width="500px", fixed_height="400px"):
    # Creates a clickable blog post element with an image preview and fixed size.
    st.markdown(
        f"""
        <div style="width: {fixed_width}; height: {fixed_height}; border: 1px solid #e0e0e0; padding: 10px; margin-bottom: 10px; border-radius: 5px; display: flex; flex-direction: column;">
            <a href="{url}" target="_blank" style="text-decoration: none; display: block; flex-grow: 1;">
                <img src="{image_url}" alt="{title}" style="width: 100%; max-height: 200px; object-fit: cover; border-radius: 5px; margin-bottom: 10px;">
                <h3 style="margin-top: 0;">{title}</h3>
            </a>
            <p style="flex-grow: 1; overflow: hidden;">{summary}</p>
        </div>
        """,
        unsafe_allow_html=True,
     )

blog_posts = [
        {
            "title": "Effects of Inappropriate Content to Minors",
            "url": "https://thedigitalparents.com/online-safety/effects-of-inappropriate-content-to-minors/",
            "summary": "Here we are going to discuss the effects inappropriate content can have on your child and the consequences. Also, why they shouldn’t watch inappropriate content, and how to establish some guidelines for your child.",
            "image_url": "https://thedigitalparents.b-cdn.net/wp-content/uploads/2023/12/pexels-pavel-danilyuk-8763024.jpg",
        },

        {
            "title": "What Is Content Moderation? | Types of Content Moderation, Tools, and more",
            "url": "https://imagga.com/blog/what-is-content-moderation/",
            "summary": "The volume of content generated online every second is staggering. Platforms built around user-generated content face constant challenges in managing inappropriate or illegal text, images, videos, and live streams.",
            "image_url": "https://imagga.com/blog/wp-content/uploads/2021/09/Art6_featured_image-1024x682.jpg",
        },

        {
            "title": "What are the Dangers of Inappropriate Content for Kids?",
            "url": "https://ogymogy.com/blog/dangers-of-inappropriate-content/",
            "summary": "The internet is not just a place, it’s a potentially dangerous territory for everyone, especially children. The threat of encountering inappropriate content is real and immediate, with excessive screen time leading to study distraction, anxiety, depression, and more. Understanding these risks and the potential harm of adult content for kids is not just necessary, it’s vital.",
            "image_url": "https://ogymogy.com/blog/wp-content/uploads/2024/06/what-are-the-danger-of-content-.jpg",
        },

        {
            "title": "Creating a Safe and Respectful Online Community by Understanding the Importance of Content Moderation in Social Media",
            "url": "https://newmediaservices.com.au/the-importance-of-content-moderation-in-social-media/",
            "summary": "Social media is a crucial part of our lives. It’s the first thing we check when we wake up and the last thing we visit before sleeping at night. We use it to engage with friends, share updates, and discover new content.",
            "image_url": "https://newmediaservices.com.au/wp-content/uploads/2024/07/The-Importance-of-Content-Moderation-in-Social-Media.webp",
        },

        {
            "title": "Online harms: protecting children and young people",
            "url": "https://learning.nspcc.org.uk/news/2024/january/online-harms-protecting-children-and-young-people#:~:text=Accessing%20and%20engaging%20with%20harmful%20content%20online%20can,to%20help%20keep%20children%20safe%20from%20online%20harm%3F",
            "summary": "Accessing and engaging with harmful content online can be damaging to children’s wellbeing, leaving them scared and confused. It can also influence their behaviour or what they believe. But what is harmful online content? And what can we do to help keep children safe from online harm?",
            "image_url": "https://learning.nspcc.org.uk/media/qttbeugx/online-harms-blog.jpg",
        },
        {
            "title": "The Vital Role of Content Moderation: A Deep Dive into Online Safety",
            "url": "https://blog.emb.global/vital-role-of-content-moderation/",
            "summary": "Content moderation is crucial and evolving. It involves careful scrutiny, assessment, and possible removal of user-created content. This is to foster a secure and positive online space. This practice is key. It’s vital for our journey through the complex networks of online interaction.",
            "image_url": "https://blog.emb.global/wp-content/uploads/2023/11/Try-Magic-Design-2023-11-28T130131.812-1024x576.webp",
        },
        # Add more articles as needed
    ]
# END
# ________________________________________________________________