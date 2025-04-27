# Use the official PyTorch image as base with CUDA support
FROM pytorch/pytorch:2.2.2-cuda12.1-cudnn8-runtime

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV NVIDIA_VISIBLE_DEVICES=all
ENV FFMPEG_BINARY="/usr/bin/ffmpeg"

# First, remove the conda-installed ffmpeg to avoid conflicts
RUN conda remove --force ffmpeg -y && \
    conda clean -afy

# Install system dependencies with full ffmpeg and codecs
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libavcodec-extra58 \
    libx264-dev \
    libx265-dev \
    libvpx-dev \
    libaom-dev \
    libdav1d-dev \
    libmp3lame-dev \
    libopus-dev \
    libsm6 \
    libxext6 \
    libgl1 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    git \
    && rm -rf /var/lib/apt/lists/*

# Verify FFmpeg installation with codecs (skip the grep checks)
RUN ffmpeg -version

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create and set working directory
WORKDIR /app

# Copy application files
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/output /app/saves/reports && \
    chmod -R 777 /app/output /app/saves/reports

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]