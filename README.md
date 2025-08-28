# HeroShot

AI-powered video processing pipeline for extracting hero shots and applying style transformations.

## Overview

HeroShot is a comprehensive Python script that processes videos through an intelligent pipeline:

1. **Input Video** - Load videos from YouTube URLs or local files
2. **Scene Detection** - Automatically detect cuts and save segments
3. **Hero Shot Extraction** - Select the best representative frame from each scene
4. **Style Transformation** - Apply AI-powered style transformations using Flux + LoRA models
5. **Video Reconstruction** - Combine styled images into a final video

## Features

- 🎥 **Multi-source Input**: YouTube URLs (yt-dlp) and local video files
- 🔍 **Smart Scene Detection**: PySceneDetect with OpenCV fallback
- 🎯 **Intelligent Frame Selection**: Multi-factor scoring (sharpness, variance, contrast)
- 🤖 **AI Captioning**: Automatic image descriptions using BLIP models
- 🎨 **Style Transformation**: Flux diffusion models with LoRA support
- 📽️ **Video Reconstruction**: MoviePy-based video creation with transitions
- ⚙️ **Configurable Pipeline**: YAML-based configuration with CLI overrides
- 📊 **Progress Tracking**: Progress bars and comprehensive logging
- 🚀 **GPU Acceleration**: CUDA/MPS support for AI models

## Installation

### Requirements

- Python 3.8+
- FFmpeg (for video processing)
- CUDA-compatible GPU (recommended for style transformation)

### Install Dependencies

```bash
# Clone repository
git clone https://github.com/clubmate/heroshot.git
cd heroshot

# Install Python dependencies
pip install -r requirements.txt

# Optional: Install with GPU support
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### Install Package

```bash
# Development installation
pip install -e .

# Or install directly
pip install .
```

## Quick Start

### Basic Usage

```bash
# Process YouTube video
python src/main.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Process local video file
python src/main.py "/path/to/video.mp4"

# Use custom configuration
python src/main.py "video.mp4" --config custom_config.yaml
```

### Advanced Usage

```bash
# Skip specific steps
python src/main.py "video.mp4" --skip-style --skip-reconstruction

# Use specific style preset
python src/main.py "video.mp4" --style-preset cartoon

# Custom output directory
python src/main.py "video.mp4" --output-dir "./my_outputs/"

# Preview mode (faster processing)
python src/main.py "video.mp4" --preview-only

# Verbose logging
python src/main.py "video.mp4" --verbose
```

## Configuration

HeroShot uses YAML configuration files. The default configuration is in `configs/config.yaml`.

### Key Configuration Sections

```yaml
# Input/Output settings
input:
  source_type: "auto"  # "youtube", "local", or "auto"
output:
  base_directory: "outputs"
  create_subdirectory: true

# Scene detection
scene_detection:
  threshold: 30.0
  min_scene_length: 1.0
  detector_type: "content"

# Hero shot extraction
hero_shot:
  scoring_method: "combined"
  sample_interval: 0.5
  caption_generation:
    enabled: true
    model: "Salesforce/blip-image-captioning-base"

# Style transformation
style_transformation:
  flux:
    model_path: "black-forest-labs/FLUX.1-dev"
    device: "auto"
  presets:
    cinematic:
      prompt_suffix: "cinematic, dramatic lighting"
      guidance_scale: 7.5

# Video reconstruction
video_reconstruction:
  frame_duration: 0.3
  fps: 30
  resolution:
    width: 1920
    height: 1080
```

## CLI Options

```bash
usage: main.py [-h] [--config CONFIG] [--output-dir OUTPUT_DIR]
               [--skip-scene-detection] [--skip-hero-shot] [--skip-style]
               [--skip-reconstruction] [--style-preset {cinematic,cartoon,oil_painting}]
               [--scene-threshold SCENE_THRESHOLD] [--frame-duration FRAME_DURATION]
               [--fps FPS] [--verbose] [--log-level {DEBUG,INFO,WARNING,ERROR}]
               [--log-file LOG_FILE] [--preview-only] [--dry-run] [--version]
               input_source

positional arguments:
  input_source          Video source: YouTube URL or local file path

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        Path to configuration file (YAML or JSON)
  --output-dir OUTPUT_DIR, -o OUTPUT_DIR
                        Output directory (overrides config)
  --skip-scene-detection
                        Skip scene detection step
  --skip-hero-shot      Skip hero shot extraction step
  --skip-style          Skip style transformation step
  --skip-reconstruction
                        Skip video reconstruction step
  --style-preset {cinematic,cartoon,oil_painting}
                        Style preset for transformation
  --verbose, -v         Enable verbose logging
  --preview-only        Only create a preview video (faster processing)
  --dry-run             Show what would be done without actually processing
```

## Output Structure

```
outputs/
├── video_name/
│   ├── segments/                 # Individual scene segments (MP4)
│   ├── hero_shots/              # Extracted hero shot images (PNG)
│   ├── styled_images/           # Style-transformed images (PNG)
│   ├── scenes_metadata.json     # Scene detection results
│   ├── hero_shots_metadata.json # Hero shot extraction data
│   ├── styled_images_metadata.json # Style transformation data
│   ├── video_reconstruction_metadata.json # Final video data
│   ├── heroshot_reconstructed.mp4 # Final styled video
│   └── heroshot_preview.mp4     # Quick preview video
```

## Style Presets

### Built-in Presets

- **Cinematic**: Dramatic lighting, film grain, professional photography
- **Cartoon**: Animated style, colorful, stylized
- **Oil Painting**: Classical art, textured brushstrokes, renaissance style

### Custom Presets

Add custom presets to your configuration file:

```yaml
style_transformation:
  presets:
    my_style:
      prompt_suffix: "my custom style description"
      negative_prompt: "what to avoid"
      guidance_scale: 7.5
      num_inference_steps: 30
```

## Dependencies

### Core Dependencies
- `yt-dlp` - YouTube video downloading
- `scenedetect` - Scene detection
- `opencv-python` - Image/video processing
- `moviepy` - Video editing and creation
- `Pillow` - Image handling
- `PyYAML` - Configuration management

### AI/ML Dependencies
- `torch` - PyTorch deep learning framework
- `transformers` - Hugging Face transformers (BLIP captioning)
- `diffusers` - Diffusion models (Flux)

## Performance Tips

### GPU Acceleration
- Ensure CUDA/MPS is available for style transformation
- Use `fp16` precision for faster inference
- Adjust `gpu_memory_fraction` in config if needed

### Processing Optimization
- Use `--preview-only` for quick tests
- Adjust `max_frames_to_analyze` for faster hero shot extraction
- Enable `parallel_processing` in config

### Memory Management
- Lower resolution for preview videos
- Use smaller batch sizes for style transformation
- Clear GPU cache between scenes if needed

## Troubleshooting

### Common Issues

1. **FFmpeg not found**: Install FFmpeg and ensure it's in PATH
2. **CUDA out of memory**: Reduce batch size or use CPU processing
3. **YouTube download fails**: Check yt-dlp version and network connection
4. **Model loading fails**: Ensure sufficient disk space for model cache

### Debug Mode

```bash
# Enable verbose logging
python src/main.py "video.mp4" --verbose --log-level DEBUG

# Dry run to test configuration
python src/main.py "video.mp4" --dry-run
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- PySceneDetect for scene detection algorithms
- Hugging Face for transformer models
- Black Forest Labs for Flux diffusion models
- MoviePy for video processing capabilities