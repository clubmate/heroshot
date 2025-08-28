"""
Scene detection functionality for video segmentation
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from .config import get_config
from .utils import format_duration, sanitize_filename

logger = logging.getLogger(__name__)


@dataclass
class Scene:
    """Represents a video scene"""
    start_time: float
    end_time: float
    duration: float
    scene_id: int
    filename: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scene to dictionary"""
        return {
            'scene_id': self.scene_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'start_time_formatted': format_duration(self.start_time),
            'end_time_formatted': format_duration(self.end_time),
            'duration_formatted': format_duration(self.duration),
            'filename': self.filename
        }


class SceneDetector:
    """Scene detection using various methods"""
    
    def __init__(self):
        self.config = get_config()
        self.detector_type = self.config.get('scene_detection.detector_type', 'content')
        self.threshold = self.config.get('scene_detection.threshold', 30.0)
        self.min_scene_length = self.config.get('scene_detection.min_scene_length', 1.0)
    
    def detect_scenes(self, video_path: str, output_dir: str) -> List[Scene]:
        """
        Detect scenes in video
        
        Args:
            video_path: Path to input video
            output_dir: Directory to save scene segments
            
        Returns:
            List of detected scenes
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        logger.info(f"Starting scene detection on: {video_path}")
        logger.info(f"Detection method: {self.detector_type}, Threshold: {self.threshold}")
        
        # Try PySceneDetect first, fallback to OpenCV-based detection
        try:
            scenes = self._detect_with_pyscenedetect(video_path)
        except ImportError:
            logger.warning("PySceneDetect not available, using OpenCV-based detection")
            scenes = self._detect_with_opencv(video_path)
        
        if not scenes:
            logger.warning("No scenes detected, creating single scene for entire video")
            scenes = self._create_single_scene(video_path)
        
        # Filter scenes by minimum length
        filtered_scenes = [s for s in scenes if s.duration >= self.min_scene_length]
        
        if len(filtered_scenes) != len(scenes):
            logger.info(f"Filtered {len(scenes) - len(filtered_scenes)} scenes shorter than {self.min_scene_length}s")
        
        scenes = filtered_scenes
        
        # Save scene segments if enabled
        if self.config.get('output.preserve_original_segments', True):
            scenes = self._save_scene_segments(video_path, scenes, output_dir)
        
        # Save scene metadata
        self._save_scene_metadata(scenes, output_dir)
        
        logger.info(f"Detected {len(scenes)} scenes")
        return scenes
    
    def _detect_with_pyscenedetect(self, video_path: str) -> List[Scene]:
        """
        Detect scenes using PySceneDetect
        
        Args:
            video_path: Path to video file
            
        Returns:
            List of detected scenes
        """
        try:
            from scenedetect import VideoManager, SceneManager
            from scenedetect.detectors import ContentDetector, ThresholdDetector, AdaptiveDetector
        except ImportError:
            raise ImportError("scenedetect package not available")
        
        # Create video manager
        video_manager = VideoManager([video_path])
        scene_manager = SceneManager()
        
        # Add detector based on configuration
        if self.detector_type == 'content':
            detector = ContentDetector(threshold=self.threshold)
        elif self.detector_type == 'threshold':
            detector = ThresholdDetector(threshold=self.threshold)
        elif self.detector_type == 'adaptive':
            detector = AdaptiveDetector()
        else:
            logger.warning(f"Unknown detector type: {self.detector_type}, using content detector")
            detector = ContentDetector(threshold=self.threshold)
        
        scene_manager.add_detector(detector)
        
        # Start video manager and detect scenes
        video_manager.start()
        scene_manager.detect_scenes(frame_source=video_manager)
        
        # Get scene list
        scene_list = scene_manager.get_scene_list()
        
        # Convert to our Scene objects
        scenes = []
        for i, (start_time, end_time) in enumerate(scene_list):
            scene = Scene(
                scene_id=i + 1,
                start_time=start_time.get_seconds(),
                end_time=end_time.get_seconds(),
                duration=end_time.get_seconds() - start_time.get_seconds()
            )
            scenes.append(scene)
        
        video_manager.release()
        
        logger.info(f"PySceneDetect found {len(scenes)} scenes")
        return scenes
    
    def _detect_with_opencv(self, video_path: str) -> List[Scene]:
        """
        Detect scenes using OpenCV-based method
        
        Args:
            video_path: Path to video file
            
        Returns:
            List of detected scenes
        """
        import cv2
        import numpy as np
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"Analyzing {frame_count} frames at {fps} fps")
        
        # Calculate frame differences
        scene_changes = []
        prev_gray = None
        frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if prev_gray is not None:
                # Calculate histogram difference
                diff = cv2.compareHist(
                    cv2.calcHist([prev_gray], [0], None, [256], [0, 256]),
                    cv2.calcHist([gray], [0], None, [256], [0, 256]),
                    cv2.HISTCMP_CORREL
                )
                
                # Scene change if correlation is below threshold
                correlation_threshold = 1.0 - (self.threshold / 100.0)
                if diff < correlation_threshold:
                    scene_changes.append(frame_idx / fps)
            
            prev_gray = gray
            frame_idx += 1
            
            # Progress logging
            if frame_idx % 1000 == 0:
                progress = (frame_idx / frame_count) * 100
                logger.debug(f"Scene detection progress: {progress:.1f}%")
        
        cap.release()
        
        # Create scenes from change points
        scenes = []
        scene_starts = [0.0] + scene_changes
        scene_ends = scene_changes + [frame_count / fps]
        
        for i, (start, end) in enumerate(zip(scene_starts, scene_ends)):
            if end - start >= self.min_scene_length:
                scene = Scene(
                    scene_id=i + 1,
                    start_time=start,
                    end_time=end,
                    duration=end - start
                )
                scenes.append(scene)
        
        logger.info(f"OpenCV detection found {len(scenes)} scenes")
        return scenes
    
    def _create_single_scene(self, video_path: str) -> List[Scene]:
        """
        Create single scene for entire video
        
        Args:
            video_path: Path to video file
            
        Returns:
            List with single scene
        """
        import cv2
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        cap.release()
        
        scene = Scene(
            scene_id=1,
            start_time=0.0,
            end_time=duration,
            duration=duration
        )
        
        return [scene]
    
    def _save_scene_segments(self, video_path: str, scenes: List[Scene], output_dir: str) -> List[Scene]:
        """
        Save individual scene segments as video files
        
        Args:
            video_path: Path to original video
            scenes: List of scenes
            output_dir: Output directory
            
        Returns:
            Updated scenes with filenames
        """
        try:
            from moviepy.editor import VideoFileClip
        except ImportError:
            logger.error("moviepy not available, cannot save scene segments")
            return scenes
        
        output_path = Path(output_dir) / "segments"
        output_path.mkdir(parents=True, exist_ok=True)
        
        video_name = Path(video_path).stem
        
        logger.info(f"Saving {len(scenes)} scene segments to {output_path}")
        
        # Load video
        video = VideoFileClip(video_path)
        
        updated_scenes = []
        for scene in scenes:
            try:
                # Extract scene segment
                segment = video.subclip(scene.start_time, scene.end_time)
                
                # Create filename
                filename = f"{video_name}_scene_{scene.scene_id:03d}.mp4"
                filepath = output_path / filename
                
                # Save segment
                segment.write_videofile(
                    str(filepath),
                    verbose=False,
                    logger=None,
                    temp_audiofile_path=str(output_path / "temp_audio.m4a")
                )
                
                # Update scene with filename
                updated_scene = Scene(
                    scene_id=scene.scene_id,
                    start_time=scene.start_time,
                    end_time=scene.end_time,
                    duration=scene.duration,
                    filename=str(filepath)
                )
                updated_scenes.append(updated_scene)
                
                logger.debug(f"Saved scene {scene.scene_id}: {filename}")
                
            except Exception as e:
                logger.error(f"Failed to save scene {scene.scene_id}: {e}")
                updated_scenes.append(scene)  # Keep original scene without filename
        
        video.close()
        
        logger.info("Scene segment extraction complete")
        return updated_scenes
    
    def _save_scene_metadata(self, scenes: List[Scene], output_dir: str):
        """
        Save scene metadata to JSON file
        
        Args:
            scenes: List of scenes
            output_dir: Output directory
        """
        metadata = {
            'total_scenes': len(scenes),
            'total_duration': sum(s.duration for s in scenes),
            'scenes': [scene.to_dict() for scene in scenes],
            'detection_settings': {
                'detector_type': self.detector_type,
                'threshold': self.threshold,
                'min_scene_length': self.min_scene_length
            }
        }
        
        metadata_file = Path(output_dir) / "scenes_metadata.json"
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Scene metadata saved to: {metadata_file}")


def load_scene_metadata(metadata_path: str) -> List[Scene]:
    """
    Load scene metadata from JSON file
    
    Args:
        metadata_path: Path to metadata JSON file
        
    Returns:
        List of scenes
    """
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    scenes = []
    for scene_data in metadata['scenes']:
        scene = Scene(
            scene_id=scene_data['scene_id'],
            start_time=scene_data['start_time'],
            end_time=scene_data['end_time'],
            duration=scene_data['duration'],
            filename=scene_data.get('filename')
        )
        scenes.append(scene)
    
    return scenes