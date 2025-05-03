# src/proc_nudity.py
import datetime
import os

import imageio
import torch
import torchvision.transforms as transforms
from PIL import Image
import cv2
import numpy as np


def preprocess_frame_for_nudity(frame, transform):
    """Convert frame to tensor for nudity detection"""
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    return transform(image).unsqueeze(0)


def detect_nudity_in_frame(frame, model, transform, device, threshold=0.85):
    """Detect nudity in a single frame with confidence threshold"""
    input_tensor = preprocess_frame_for_nudity(frame, transform).to(device)

    with torch.no_grad():
        outputs = model(input_tensor)
        probabilities = torch.nn.functional.softmax(outputs, dim=1)
        confidence, preds = torch.max(probabilities, 1)

    pred_idx = preds.item()
    conf = confidence.item()

    # Only classify as nude if confidence exceeds threshold
    if pred_idx == 0 and conf < threshold:  # 0 is 'nude' class
        return 'safe', conf
    return ['nude', 'safe'][pred_idx], conf


def annotate_frame(frame, pred_class, confidence, frame_count, fps):
    """Add annotation to frame showing detection results"""
    annotated_frame = frame.copy()

    # Set text color based on prediction
    if pred_class == 'nude':
        color = (0, 0, 255)  # Red for nudity
        label = f"Nudity ({confidence:.2f})"
    else:
        color = (0, 255, 0)  # Green for safe
        label = f"Safe ({confidence:.2f})"

    # Add timestamp
    timestamp = str(datetime.timedelta(seconds=frame_count / fps)).split('.')[0]

    # Add prediction label
    cv2.putText(annotated_frame, label, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    # Add frame counter
    cv2.putText(annotated_frame, f"Frame: {frame_count}", (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Add timestamp
    cv2.putText(annotated_frame, f"Time: {timestamp}", (20, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    return annotated_frame


def extract_nudity_sequences(video_path, output_dir, model, class_names,
                             sequence_length=16, threshold=0.85, progress_callback=None):
    """Extract sequences with potential nudity"""
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    frame_count = 0
    sequence_buffer = []
    nudity_sequences = []
    predictions_per_frame = []
    confidence_scores = {'nude': [], 'safe': []}
    device = next(model.parameters()).device

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Classify frame
        pred_class, confidence = detect_nudity_in_frame(
            frame, model, transform, device, threshold
        )

        # Annotate frame with detection results
        annotated_frame = annotate_frame(frame, pred_class, confidence, frame_count, fps)

        # Save annotated frame
        output_path = os.path.join(output_dir, f"frame_{frame_count:04d}.jpg")
        cv2.imwrite(output_path, annotated_frame)

        if progress_callback:
            progress_callback()

        predictions_per_frame.append((frame_count, pred_class, confidence))
        confidence_scores[pred_class].append(confidence)

        # Store frame if nudity detected
        if pred_class == 'nude':
            sequence_buffer.append(annotated_frame.copy())

            # When we have a full sequence
            if len(sequence_buffer) >= sequence_length:
                # Create GIF for the detected sequence
                gif_path = os.path.join(output_dir, f"nudity_sequence_{frame_count}.gif")
                imageio.mimsave(gif_path, sequence_buffer, duration=200, loop=0)

                nudity_sequences.append({
                    'start_frame': frame_count - sequence_length + 1,
                    'end_frame': frame_count,
                    'confidence': confidence,
                    'frames': sequence_buffer.copy(),
                    'type': 'nudity',
                    'gif_path': gif_path
                })
                sequence_buffer = []
        else:
            sequence_buffer = []

    cap.release()

    # Calculate average confidence
    avg_confidence = {
        'nude': np.mean(confidence_scores['nude']) if confidence_scores['nude'] else 0.0,
        'safe': np.mean(confidence_scores['safe']) if confidence_scores['safe'] else 1.0
    }

    return frame_count, predictions_per_frame, avg_confidence, nudity_sequences