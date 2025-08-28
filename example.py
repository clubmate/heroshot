#!/usr/bin/env python3
"""
Example usage script for HeroShot
This demonstrates how to use the HeroShot pipeline programmatically
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def example_usage():
    """Example of using HeroShot programmatically"""
    
    print("🎬 HeroShot Example Usage")
    print("=" * 50)
    
    # Example 1: Configuration system
    print("\n1. Configuration System:")
    try:
        from config import Config
        
        # Load default configuration
        config = Config()
        print(f"   ✅ Default output directory: {config.get('output.base_directory')}")
        print(f"   ✅ Scene detection threshold: {config.get('scene_detection.threshold')}")
        print(f"   ✅ Style preset: {config.get('style_transformation.generation.style_preset')}")
        
        # Override configuration
        config.set('output.base_directory', 'my_custom_outputs')
        print(f"   ✅ Updated output directory: {config.get('output.base_directory')}")
        
    except Exception as e:
        print(f"   ❌ Configuration error: {e}")
    
    # Example 2: Utility functions
    print("\n2. Utility Functions:")
    try:
        from utils import is_youtube_url, sanitize_filename, detect_source_type
        
        # Test YouTube URL detection
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        local_file = "/path/to/video.mp4"
        
        print(f"   ✅ '{youtube_url}' is YouTube: {is_youtube_url(youtube_url)}")
        print(f"   ✅ '{local_file}' is YouTube: {is_youtube_url(local_file)}")
        
        # Test source type detection
        print(f"   ✅ Source type for YouTube URL: {detect_source_type(youtube_url)}")
        print(f"   ✅ Source type for local file: {detect_source_type(local_file)}")
        
        # Test filename sanitization
        unsafe_name = "My Video: Special/Characters? <Unsafe>"
        safe_name = sanitize_filename(unsafe_name)
        print(f"   ✅ Sanitized filename: '{unsafe_name}' → '{safe_name}'")
        
    except Exception as e:
        print(f"   ❌ Utility functions error: {e}")
    
    # Example 3: Video loader
    print("\n3. Video Loader:")
    try:
        from video_loader import VideoLoader, validate_video_source
        
        loader = VideoLoader()
        print("   ✅ Video loader initialized")
        
        # Test source validation
        test_sources = [
            "https://www.youtube.com/watch?v=test",
            "https://youtu.be/test",
            "video.mp4",
            "invalid://url"
        ]
        
        for source in test_sources:
            is_valid = validate_video_source(source)
            source_type = detect_source_type(source)
            print(f"   ✅ '{source}' → Valid: {is_valid}, Type: {source_type}")
        
    except Exception as e:
        print(f"   ❌ Video loader error: {e}")
    
    # Example 4: CLI interface simulation
    print("\n4. CLI Interface:")
    print("   Example commands:")
    print("   ✅ python src/main.py 'https://www.youtube.com/watch?v=VIDEO_ID'")
    print("   ✅ python src/main.py 'video.mp4' --config configs/preview_config.yaml")
    print("   ✅ python src/main.py 'video.mp4' --skip-style --dry-run")
    print("   ✅ python src/main.py 'video.mp4' --style-preset cartoon --verbose")
    
    # Example 5: Configuration files
    print("\n5. Available Configurations:")
    config_files = [
        "configs/config.yaml - Default configuration",
        "configs/preview_config.yaml - Fast preview mode",
        "configs/high_quality_config.yaml - High quality output"
    ]
    
    for config_file in config_files:
        print(f"   ✅ {config_file}")
    
    print("\n" + "=" * 50)
    print("🚀 Ready to process videos with HeroShot!")
    print("\nNext steps:")
    print("1. Install full dependencies: pip install -r requirements.txt")
    print("2. Run with a test video: python src/main.py 'path/to/video.mp4' --dry-run")
    print("3. Check the generated outputs/ directory")

if __name__ == "__main__":
    example_usage()