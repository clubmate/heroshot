#!/usr/bin/env python3
"""
Test script for HeroShot CLI interface without heavy dependencies
"""

import sys
import os
import argparse

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def create_parser():
    """Create command line argument parser (simplified version)"""
    parser = argparse.ArgumentParser(
        description="HeroShot - AI-powered video processing pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "https://www.youtube.com/watch?v=VIDEO_ID"
  %(prog)s "/path/to/video.mp4" --config custom_config.yaml
  %(prog)s "video.mp4" --skip-style --output-dir outputs/
  %(prog)s "https://youtu.be/VIDEO_ID" --style-preset cartoon --verbose
        """
    )
    
    parser.add_argument(
        'input_source',
        help='Video source: YouTube URL or local file path'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (YAML or JSON)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        help='Output directory (overrides config)'
    )
    
    parser.add_argument(
        '--skip-scene-detection',
        action='store_true',
        help='Skip scene detection step'
    )
    
    parser.add_argument(
        '--skip-hero-shot',
        action='store_true',
        help='Skip hero shot extraction step'
    )
    
    parser.add_argument(
        '--skip-style',
        action='store_true',
        help='Skip style transformation step'
    )
    
    parser.add_argument(
        '--skip-reconstruction',
        action='store_true',
        help='Skip video reconstruction step'
    )
    
    parser.add_argument(
        '--style-preset',
        type=str,
        choices=['cinematic', 'cartoon', 'oil_painting'],
        help='Style preset for transformation (overrides config)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--preview-only',
        action='store_true',
        help='Only create a preview video (faster processing)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually processing'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='HeroShot 0.1.0'
    )
    
    return parser

def main():
    """Test main function"""
    parser = create_parser()
    
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    args = parser.parse_args()
    
    print("✅ CLI parsing works!")
    print(f"Input source: {args.input_source}")
    print(f"Config file: {args.config}")
    print(f"Output dir: {args.output_dir}")
    print(f"Dry run: {args.dry_run}")
    print(f"Verbose: {args.verbose}")
    
    # Test configuration loading
    try:
        from config import Config
        config = Config()
        print("✅ Configuration system works!")
        
        # Test utility functions
        from utils import is_youtube_url, detect_source_type
        source_type = detect_source_type(args.input_source)
        is_youtube = is_youtube_url(args.input_source)
        print(f"✅ Source detection: {source_type} (YouTube: {is_youtube})")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()