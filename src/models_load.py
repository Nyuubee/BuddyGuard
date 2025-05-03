# src/models_load.py


# IMPORTS
# __________________________________________________________________
import torch

from transformers import BertTokenizer, pipeline
from src.models_def import BertClassifier

# @st.cache_resource
def load_models():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    bert_model_path = "./models/bert.pth"
    resnet_lstm_model_path = "./models/resnet50-lstm_10epoch(2).pt"  # Your ResNet-LSTM model
    violence_class_names = ['Safe', 'Violence']
    # New nudity model
    nudity_model_path = "./models/resnet50_5epoch_0001lr_weight_decay_(final)(2).pt"  # Update with your actual path
    nudity_class_names = ['nude', 'safe']

    # Load BERT model (unchanged)
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    bert_model = BertClassifier().to(device)
    bert_model.load_state_dict(torch.load(bert_model_path, map_location=device))
    bert_model.eval()

    # Load Whisper model (unchanged)
    whisper_model = pipeline("automatic-speech-recognition", "openai/whisper-tiny.en", torch_dtype=torch.float16, device=device)

    # Load Violence detection model
    violence_model = torch.load(resnet_lstm_model_path, map_location=device, weights_only=False)
    violence_model.eval()

    # Load Nudity detection model
    nudity_model = torch.load(nudity_model_path, map_location=device, weights_only=False)
    nudity_model.eval()

    return {
        'tokenizer': tokenizer,
        'bert_model': bert_model,
        'whisper_model': whisper_model,
        'violence_model': violence_model,
        'nudity_model': nudity_model,
        'violence_class_names': violence_class_names,
        'nudity_class_names': nudity_class_names,
        'device': device
    }

### END