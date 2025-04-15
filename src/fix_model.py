import torch
from src.models_def import ResNetLSTMModel  # Use your current class definition

# Load the problematic model
device = "cuda" if torch.cuda.is_available() else "cpu"
model = torch.load("C:/Users/ronri/OneDrive/Desktop/Coding/Python/BuddyGuard/models/resnet50-lstm_10epoch(2).pt", map_location=device, weights_only=False)

# Immediately re-save it with updated architecture
torch.save(model.state_dict(), "C:/Users/ronri/OneDrive/Desktop/Coding/Python/BuddyGuard/models/resnet50-lstm_fixed.pt")  # Save ONLY weights