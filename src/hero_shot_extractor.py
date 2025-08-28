"""
Hero shot extraction functionality for selecting best frames from video segments
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass

try:
    from .config import get_config
    from .scene_detector import Scene
    from .utils import sanitize_filename
except ImportError:
    from config import get_config
    from scene_detector import Scene
    from utils import sanitize_filename

logger = logging.getLogger(__name__)


@dataclass
class HeroShot:
    """Represents a hero shot extracted from a scene"""
    scene_id: int
    frame_time: float
    score: float
    image_path: str
    caption: Optional[str] = None
    scoring_details: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert hero shot to dictionary"""
        return {
            'scene_id': self.scene_id,
            'frame_time': self.frame_time,
            'score': self.score,
            'image_path': self.image_path,
            'caption': self.caption,
            'scoring_details': self.scoring_details or {}
        }


class FrameScorer:
    """Frame scoring algorithms for hero shot selection"""
    
    def __init__(self):
        self.config = get_config()
        self.scoring_method = self.config.get('hero_shot.scoring_method', 'combined')
        self.sharpness_weight = self.config.get('hero_shot.sharpness_weight', 0.4)
        self.variance_weight = self.config.get('hero_shot.variance_weight', 0.3)
        self.contrast_weight = self.config.get('hero_shot.contrast_weight', 0.3)
    
    def score_frame(self, frame: np.ndarray) -> Tuple[float, Dict[str, float]]:
        """
        Score a frame for hero shot selection
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            Tuple of (total_score, score_details)
        """
        import cv2
        
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate individual scores
        sharpness_score = self._calculate_sharpness(gray)
        variance_score = self._calculate_variance(gray)
        contrast_score = self._calculate_contrast(gray)
        
        # Calculate combined score
        if self.scoring_method == 'sharpness':
            total_score = sharpness_score
        elif self.scoring_method == 'variance':
            total_score = variance_score
        elif self.scoring_method == 'contrast':
            total_score = contrast_score
        else:  # combined
            total_score = (
                sharpness_score * self.sharpness_weight +
                variance_score * self.variance_weight +
                contrast_score * self.contrast_weight
            )
        
        score_details = {
            'sharpness': sharpness_score,
            'variance': variance_score,
            'contrast': contrast_score,
            'method': self.scoring_method
        }
        
        return total_score, score_details
    
    def _calculate_sharpness(self, gray: np.ndarray) -> float:
        """
        Calculate sharpness using Laplacian variance
        
        Args:
            gray: Grayscale image
            
        Returns:
            Sharpness score (normalized 0-1)
        """
        import cv2
        
        # Laplacian filter for edge detection
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        
        # Normalize to 0-1 range (empirical scaling)
        normalized_score = min(variance / 10000.0, 1.0)
        
        return normalized_score
    
    def _calculate_variance(self, gray: np.ndarray) -> float:
        """
        Calculate pixel variance
        
        Args:
            gray: Grayscale image
            
        Returns:
            Variance score (normalized 0-1)
        """
        variance = gray.var()
        
        # Normalize to 0-1 range (empirical scaling)
        normalized_score = min(variance / 6000.0, 1.0)
        
        return normalized_score
    
    def _calculate_contrast(self, gray: np.ndarray) -> float:
        """
        Calculate contrast using standard deviation
        
        Args:
            gray: Grayscale image
            
        Returns:
            Contrast score (normalized 0-1)
        """
        contrast = gray.std()
        
        # Normalize to 0-1 range (empirical scaling)
        normalized_score = min(contrast / 80.0, 1.0)
        
        return normalized_score


class CaptionGenerator:
    """Generate captions for hero shots using vision-language models"""
    
    def __init__(self):
        self.config = get_config()
        self.model_name = self.config.get('hero_shot.caption_generation.model', 'Salesforce/blip-image-captioning-base')
        self.max_length = self.config.get('hero_shot.caption_generation.max_length', 50)
        self.model = None
        self.processor = None
        self._load_model()
    
    def _load_model(self):
        """Load vision-language model for captioning"""
        if not self.config.get('hero_shot.caption_generation.enabled', True):
            logger.info("Caption generation disabled")
            return
        
        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration
            import torch
            
            logger.info(f"Loading caption model: {self.model_name}")
            
            self.processor = BlipProcessor.from_pretrained(self.model_name)
            self.model = BlipForConditionalGeneration.from_pretrained(self.model_name)
            
            # Move to GPU if available
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.model.to(device)
            
            logger.info(f"Caption model loaded on {device}")
            
        except ImportError:
            logger.warning("transformers package not available, captions will not be generated")
            self.model = None
            self.processor = None
        except Exception as e:
            logger.error(f"Failed to load caption model: {e}")
            self.model = None
            self.processor = None
    
    def generate_caption(self, image: np.ndarray) -> Optional[str]:
        """
        Generate caption for image
        
        Args:
            image: Input image as numpy array (BGR format)
            
        Returns:
            Generated caption or None if failed
        """
        if self.model is None or self.processor is None:
            return None
        
        try:
            import torch
            from PIL import Image
            import cv2
            
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            
            # Process image
            inputs = self.processor(pil_image, return_tensors="pt")
            
            # Move to same device as model
            device = next(self.model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # Generate caption
            with torch.no_grad():
                output = self.model.generate(
                    **inputs,
                    max_length=self.max_length,
                    num_beams=4,
                    early_stopping=True
                )
            
            # Decode caption
            caption = self.processor.decode(output[0], skip_special_tokens=True)
            
            return caption
            
        except Exception as e:
            logger.error(f"Failed to generate caption: {e}")
            return None


class HeroShotExtractor:
    """Extract hero shots from video scenes"""
    
    def __init__(self):
        self.config = get_config()
        self.sample_interval = self.config.get('hero_shot.sample_interval', 0.5)
        self.max_frames_to_analyze = self.config.get('hero_shot.max_frames_to_analyze', 30)
        self.frame_scorer = FrameScorer()
        self.caption_generator = CaptionGenerator()
    
    def extract_hero_shots(self, video_path: str, scenes: List[Scene], output_dir: str) -> List[HeroShot]:
        """
        Extract hero shots from video scenes
        
        Args:
            video_path: Path to video file
            scenes: List of scenes to process
            output_dir: Output directory for hero shots
            
        Returns:
            List of extracted hero shots
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        output_path = Path(output_dir) / "hero_shots"
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Extracting hero shots from {len(scenes)} scenes")
        
        hero_shots = []
        
        for scene in scenes:
            logger.info(f"Processing scene {scene.scene_id} ({scene.duration:.1f}s)")
            
            hero_shot = self._extract_scene_hero_shot(
                video_path, scene, output_path
            )
            
            if hero_shot:
                hero_shots.append(hero_shot)
                logger.info(f"Extracted hero shot for scene {scene.scene_id} (score: {hero_shot.score:.3f})")
            else:
                logger.warning(f"Failed to extract hero shot for scene {scene.scene_id}")
        
        # Save hero shot metadata
        self._save_hero_shot_metadata(hero_shots, output_dir)
        
        logger.info(f"Extracted {len(hero_shots)} hero shots")
        return hero_shots
    
    def _extract_scene_hero_shot(self, video_path: str, scene: Scene, output_path: Path) -> Optional[HeroShot]:
        """
        Extract hero shot from a single scene
        
        Args:
            video_path: Path to video file
            scene: Scene to process
            output_path: Output path for hero shot
            
        Returns:
            Extracted hero shot or None if failed
        """
        import cv2
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return None
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Calculate frame sampling parameters
        scene_duration = scene.end_time - scene.start_time
        num_samples = min(
            int(scene_duration / self.sample_interval),
            self.max_frames_to_analyze
        )
        
        if num_samples == 0:
            num_samples = 1
        
        # Sample frames and score them
        best_score = -1
        best_frame = None
        best_time = None
        best_details = None
        
        for i in range(num_samples):
            # Calculate frame time
            if num_samples == 1:
                frame_time = scene.start_time + scene_duration / 2  # Middle of scene
            else:
                progress = i / (num_samples - 1)
                frame_time = scene.start_time + progress * scene_duration
            
            # Seek to frame
            frame_number = int(frame_time * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Read frame
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Score frame
            score, details = self.frame_scorer.score_frame(frame)
            
            if score > best_score:
                best_score = score
                best_frame = frame.copy()
                best_time = frame_time
                best_details = details
        
        cap.release()
        
        if best_frame is None:
            logger.error(f"No valid frames found for scene {scene.scene_id}")
            return None
        
        # Save best frame as hero shot
        video_name = Path(video_path).stem
        filename = f"{video_name}_scene_{scene.scene_id:03d}_hero.png"
        image_path = output_path / filename
        
        cv2.imwrite(str(image_path), best_frame)
        
        # Generate caption
        caption = self.caption_generator.generate_caption(best_frame)
        
        # Create hero shot object
        hero_shot = HeroShot(
            scene_id=scene.scene_id,
            frame_time=best_time,
            score=best_score,
            image_path=str(image_path),
            caption=caption,
            scoring_details=best_details
        )
        
        return hero_shot
    
    def _save_hero_shot_metadata(self, hero_shots: List[HeroShot], output_dir: str):
        """
        Save hero shot metadata to JSON file
        
        Args:
            hero_shots: List of hero shots
            output_dir: Output directory
        """
        metadata = {
            'total_hero_shots': len(hero_shots),
            'extraction_settings': {
                'scoring_method': self.frame_scorer.scoring_method,
                'sample_interval': self.sample_interval,
                'max_frames_to_analyze': self.max_frames_to_analyze,
                'caption_generation_enabled': self.config.get('hero_shot.caption_generation.enabled', True)
            },
            'hero_shots': [hero_shot.to_dict() for hero_shot in hero_shots]
        }
        
        metadata_file = Path(output_dir) / "hero_shots_metadata.json"
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Hero shot metadata saved to: {metadata_file}")


def load_hero_shot_metadata(metadata_path: str) -> List[HeroShot]:
    """
    Load hero shot metadata from JSON file
    
    Args:
        metadata_path: Path to metadata JSON file
        
    Returns:
        List of hero shots
    """
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    hero_shots = []
    for hero_data in metadata['hero_shots']:
        hero_shot = HeroShot(
            scene_id=hero_data['scene_id'],
            frame_time=hero_data['frame_time'],
            score=hero_data['score'],
            image_path=hero_data['image_path'],
            caption=hero_data.get('caption'),
            scoring_details=hero_data.get('scoring_details')
        )
        hero_shots.append(hero_shot)
    
    return hero_shots