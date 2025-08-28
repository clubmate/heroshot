"""
Main CLI interface for HeroShot video processing pipeline
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, List
from tqdm import tqdm

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from config import init_config, get_config
from utils import setup_logging, create_output_directory, get_video_info, format_duration
from video_loader import VideoLoader, validate_video_source, detect_source_type
from scene_detector import SceneDetector
from hero_shot_extractor import HeroShotExtractor
from style_transformer import StyleTransformationPipeline
from video_reconstructor import VideoReconstructor, create_preview_video

logger = logging.getLogger(__name__)


class HeroShotPipeline:
    """Main HeroShot processing pipeline"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize pipeline with configuration
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config = init_config(config_path)
        self._setup_logging()
        
        # Initialize pipeline components
        self.video_loader = VideoLoader()
        self.scene_detector = SceneDetector()
        self.hero_shot_extractor = HeroShotExtractor()
        self.style_transformer = StyleTransformationPipeline()
        self.video_reconstructor = VideoReconstructor()
        
        logger.info("HeroShot pipeline initialized")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = self.config.get('logging.level', 'INFO')
        verbose = self.config.get('logging.verbose', False)
        log_file = self.config.get('logging.log_file')
        
        setup_logging(log_level, verbose, log_file)
    
    def process_video(self, 
                     input_source: str,
                     skip_scene_detection: bool = False,
                     skip_hero_shot: bool = False,
                     skip_style_transformation: bool = False,
                     skip_video_reconstruction: bool = False) -> str:
        """
        Process video through complete pipeline
        
        Args:
            input_source: Video source (YouTube URL or local file)
            skip_scene_detection: Skip scene detection step
            skip_hero_shot: Skip hero shot extraction step
            skip_style_transformation: Skip style transformation step
            skip_video_reconstruction: Skip video reconstruction step
            
        Returns:
            Path to final output directory
        """
        logger.info("Starting HeroShot video processing pipeline")
        logger.info(f"Input source: {input_source}")
        
        # Validate input source
        if not validate_video_source(input_source):
            raise ValueError(f"Invalid video source: {input_source}")
        
        source_type = detect_source_type(input_source)
        logger.info(f"Detected source type: {source_type}")
        
        # Step 1: Load video
        logger.info("Step 1: Loading video...")
        with tqdm(desc="Loading video", disable=not self.config.get('performance.show_progress_bars', True)) as pbar:
            video_path, video_info = self.video_loader.load_video(input_source)
            pbar.update(1)
        
        logger.info(f"Video loaded: {video_path}")
        logger.info(f"Duration: {video_info.get('duration_formatted', 'Unknown')}")
        logger.info(f"Resolution: {video_info.get('resolution', 'Unknown')}")
        
        # Create output directory
        video_name = video_info.get('title', Path(video_path).stem)
        output_dir = create_output_directory(
            self.config.get('output.base_directory', 'outputs'),
            video_name,
            self.config.get('output.create_subdirectory', True)
        )
        
        scenes = []
        hero_shots = []
        styled_images = []
        
        # Step 2: Scene detection
        if not skip_scene_detection and self.config.get('scene_detection.enabled', True):
            logger.info("Step 2: Detecting scenes...")
            with tqdm(desc="Scene detection", disable=not self.config.get('performance.show_progress_bars', True)) as pbar:
                scenes = self.scene_detector.detect_scenes(video_path, str(output_dir))
                pbar.update(1)
            
            logger.info(f"Detected {len(scenes)} scenes")
        else:
            logger.info("Skipping scene detection")
            # Create single scene for entire video if skipped
            from scene_detector import Scene
            total_duration = video_info.get('duration', 60)  # Default fallback
            scenes = [Scene(1, 0.0, total_duration, total_duration)]
        
        # Step 3: Hero shot extraction
        if not skip_hero_shot and self.config.get('hero_shot.enabled', True) and scenes:
            logger.info("Step 3: Extracting hero shots...")
            with tqdm(desc="Hero shot extraction", total=len(scenes), 
                     disable=not self.config.get('performance.show_progress_bars', True)) as pbar:
                hero_shots = self.hero_shot_extractor.extract_hero_shots(
                    video_path, scenes, str(output_dir)
                )
                pbar.update(len(scenes))
            
            logger.info(f"Extracted {len(hero_shots)} hero shots")
        else:
            logger.info("Skipping hero shot extraction")
        
        # Step 4: Style transformation
        if not skip_style_transformation and self.config.get('style_transformation.enabled', True) and hero_shots:
            logger.info("Step 4: Applying style transformation...")
            with tqdm(desc="Style transformation", total=len(hero_shots),
                     disable=not self.config.get('performance.show_progress_bars', True)) as pbar:
                styled_images = self.style_transformer.transform_hero_shots(
                    hero_shots, str(output_dir)
                )
                pbar.update(len(hero_shots))
            
            logger.info(f"Generated {len(styled_images)} styled images")
        else:
            logger.info("Skipping style transformation")
        
        # Step 5: Video reconstruction
        if not skip_video_reconstruction and self.config.get('video_reconstruction.enabled', True) and styled_images:
            logger.info("Step 5: Reconstructing video...")
            with tqdm(desc="Video reconstruction", disable=not self.config.get('performance.show_progress_bars', True)) as pbar:
                final_video_path = self.video_reconstructor.reconstruct_video(
                    styled_images, str(output_dir)
                )
                pbar.update(1)
            
            logger.info(f"Final video created: {final_video_path}")
            
            # Create preview video
            try:
                preview_path = create_preview_video(styled_images, str(output_dir))
                logger.info(f"Preview video created: {preview_path}")
            except Exception as e:
                logger.warning(f"Failed to create preview video: {e}")
        else:
            logger.info("Skipping video reconstruction")
        
        logger.info("HeroShot pipeline completed successfully!")
        logger.info(f"Output directory: {output_dir}")
        
        return str(output_dir)


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
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
    
    # Input source
    parser.add_argument(
        'input_source',
        help='Video source: YouTube URL or local file path'
    )
    
    # Configuration
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (YAML or JSON)'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        help='Output directory (overrides config)'
    )
    
    # Pipeline control
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
    
    # Style options
    parser.add_argument(
        '--style-preset',
        type=str,
        choices=['cinematic', 'cartoon', 'oil_painting'],
        help='Style preset for transformation (overrides config)'
    )
    
    # Scene detection options
    parser.add_argument(
        '--scene-threshold',
        type=float,
        help='Scene detection threshold (overrides config)'
    )
    
    # Video options
    parser.add_argument(
        '--frame-duration',
        type=float,
        help='Duration per frame in final video (overrides config)'
    )
    
    parser.add_argument(
        '--fps',
        type=int,
        help='Frames per second for final video (overrides config)'
    )
    
    # Logging options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Set logging level (overrides config)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='Log file path (overrides config)'
    )
    
    # Other options
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
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        # Initialize pipeline
        pipeline = HeroShotPipeline(args.config)
        config = get_config()
        
        # Override config with command line arguments
        arg_overrides = {}
        
        if args.output_dir:
            arg_overrides['output_dir'] = args.output_dir
        if args.style_preset:
            arg_overrides['style_preset'] = args.style_preset
        if args.scene_threshold:
            arg_overrides['scene_threshold'] = args.scene_threshold
        if args.frame_duration:
            arg_overrides['frame_duration'] = args.frame_duration
        if args.verbose:
            arg_overrides['verbose'] = True
        if args.log_level:
            arg_overrides['log_level'] = args.log_level
        if args.log_file:
            arg_overrides['log_file'] = args.log_file
        
        config.override_from_args(arg_overrides)
        
        # Update logging if overridden
        if args.verbose or args.log_level or args.log_file:
            setup_logging(
                config.get('logging.level', 'INFO'),
                config.get('logging.verbose', False),
                config.get('logging.log_file')
            )
        
        # Dry run mode
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual processing will be performed")
            logger.info(f"Input source: {args.input_source}")
            logger.info(f"Source type: {detect_source_type(args.input_source)}")
            logger.info("Pipeline steps that would be executed:")
            if not args.skip_scene_detection:
                logger.info("  - Scene detection")
            if not args.skip_hero_shot:
                logger.info("  - Hero shot extraction")
            if not args.skip_style:
                logger.info("  - Style transformation")
            if not args.skip_reconstruction:
                logger.info("  - Video reconstruction")
            logger.info("Use without --dry-run to execute the pipeline")
            return
        
        # Preview only mode
        if args.preview_only:
            logger.info("PREVIEW MODE - Creating quick preview only")
            # Force shorter processing for preview
            config.set('hero_shot.max_frames_to_analyze', 5)
            config.set('video_reconstruction.frame_duration', 0.5)
        
        # Execute pipeline
        output_dir = pipeline.process_video(
            args.input_source,
            skip_scene_detection=args.skip_scene_detection,
            skip_hero_shot=args.skip_hero_shot,
            skip_style_transformation=args.skip_style,
            skip_video_reconstruction=args.skip_reconstruction
        )
        
        print(f"\n✅ Processing complete!")
        print(f"📁 Output directory: {output_dir}")
        print("\n📋 Generated files:")
        
        # List generated files
        output_path = Path(output_dir)
        if (output_path / "scenes_metadata.json").exists():
            print(f"  - Scene metadata: scenes_metadata.json")
        if (output_path / "hero_shots").exists():
            hero_shot_count = len(list((output_path / "hero_shots").glob("*.png")))
            print(f"  - Hero shots: {hero_shot_count} images in hero_shots/")
        if (output_path / "styled_images").exists():
            styled_count = len(list((output_path / "styled_images").glob("*.png")))
            print(f"  - Styled images: {styled_count} images in styled_images/")
        
        # List video files
        video_files = list(output_path.glob("*.mp4"))
        for video_file in video_files:
            print(f"  - Video: {video_file.name}")
        
        print(f"\n🎬 Ready to view your transformed video!")
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()