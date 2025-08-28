"""
Video reconstruction functionality to combine styled images into final video
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from PIL import Image

try:
    from .config import get_config
    from .style_transformer import StyledImage
    from .utils import format_duration
except ImportError:
    from config import get_config
    from style_transformer import StyledImage
    from utils import format_duration

logger = logging.getLogger(__name__)


class VideoReconstructor:
    """Reconstruct video from styled images"""
    
    def __init__(self):
        self.config = get_config()
        self.frame_duration = self.config.get('video_reconstruction.frame_duration', 0.3)
        self.fps = self.config.get('video_reconstruction.fps', 30)
        self.target_width = self.config.get('video_reconstruction.resolution.width', 1920)
        self.target_height = self.config.get('video_reconstruction.resolution.height', 1080)
        self.codec = self.config.get('video_reconstruction.codec', 'libx264')
        self.quality = self.config.get('video_reconstruction.quality', 'high')
        self.transitions_enabled = self.config.get('video_reconstruction.transitions.enabled', True)
        self.transition_type = self.config.get('video_reconstruction.transitions.type', 'fade')
        self.transition_duration = self.config.get('video_reconstruction.transitions.duration', 0.1)
    
    def reconstruct_video(self, styled_images: List[StyledImage], output_dir: str, output_filename: str = None) -> str:
        """
        Reconstruct video from styled images
        
        Args:
            styled_images: List of styled images to combine
            output_dir: Output directory
            output_filename: Optional output filename
            
        Returns:
            Path to generated video file
        """
        if not styled_images:
            raise ValueError("No styled images provided for video reconstruction")
        
        # Sort images by scene ID to maintain order
        sorted_images = sorted(styled_images, key=lambda x: x.scene_id)
        
        if output_filename is None:
            output_filename = "heroshot_reconstructed.mp4"
        
        output_path = Path(output_dir) / output_filename
        
        logger.info(f"Reconstructing video from {len(sorted_images)} styled images")
        logger.info(f"Frame duration: {self.frame_duration}s, FPS: {self.fps}")
        logger.info(f"Target resolution: {self.target_width}x{self.target_height}")
        
        try:
            # Use MoviePy for video creation
            final_video_path = self._create_video_with_moviepy(sorted_images, str(output_path))
        except ImportError:
            logger.warning("MoviePy not available, falling back to OpenCV")
            final_video_path = self._create_video_with_opencv(sorted_images, str(output_path))
        
        # Save reconstruction metadata
        self._save_reconstruction_metadata(sorted_images, output_dir, final_video_path)
        
        total_duration = len(sorted_images) * self.frame_duration
        logger.info(f"Video reconstruction complete: {final_video_path}")
        logger.info(f"Total duration: {format_duration(total_duration)}")
        
        return final_video_path
    
    def _create_video_with_moviepy(self, styled_images: List[StyledImage], output_path: str) -> str:
        """
        Create video using MoviePy
        
        Args:
            styled_images: List of styled images
            output_path: Output video path
            
        Returns:
            Path to created video
        """
        try:
            from moviepy.editor import ImageClip, VideoFileClip, concatenate_videoclips, CompositeVideoClip
            from moviepy.video.fx.all import fadein, fadeout
        except ImportError:
            raise ImportError("moviepy package not available")
        
        logger.info("Creating video with MoviePy")
        
        clips = []
        
        for i, styled_image in enumerate(styled_images):
            # Load and resize image
            img_path = styled_image.styled_image_path
            
            if not os.path.exists(img_path):
                logger.warning(f"Styled image not found, skipping: {img_path}")
                continue
            
            # Create image clip
            clip = ImageClip(img_path, duration=self.frame_duration)
            
            # Resize to target resolution
            clip = clip.resize((self.target_width, self.target_height))
            
            # Add transitions if enabled
            if self.transitions_enabled and self.transition_type == 'fade':
                if i == 0:
                    # Fade in for first clip
                    clip = clip.fx(fadein, self.transition_duration)
                elif i == len(styled_images) - 1:
                    # Fade out for last clip
                    clip = clip.fx(fadeout, self.transition_duration)
                else:
                    # Fade in and out for middle clips
                    clip = clip.fx(fadein, self.transition_duration).fx(fadeout, self.transition_duration)
            
            clips.append(clip)
            logger.debug(f"Added clip {i+1}/{len(styled_images)}: {os.path.basename(img_path)}")
        
        if not clips:
            raise ValueError("No valid clips created")
        
        # Concatenate all clips
        if self.transitions_enabled and self.transition_type == 'crossfade':
            # Use crossfade transitions
            final_video = clips[0]
            for clip in clips[1:]:
                final_video = concatenate_videoclips([final_video, clip], method="crossfadein")
        else:
            # Simple concatenation
            final_video = concatenate_videoclips(clips, method="compose")
        
        # Set video properties
        final_video = final_video.set_fps(self.fps)
        
        # Determine codec settings based on quality
        codec_params = self._get_codec_params()
        
        logger.info(f"Writing video to: {output_path}")
        
        # Write video file
        final_video.write_videofile(
            output_path,
            fps=self.fps,
            codec=self.codec,
            **codec_params,
            verbose=False,
            logger=None
        )
        
        # Clean up
        final_video.close()
        for clip in clips:
            clip.close()
        
        return output_path
    
    def _create_video_with_opencv(self, styled_images: List[StyledImage], output_path: str) -> str:
        """
        Create video using OpenCV (fallback method)
        
        Args:
            styled_images: List of styled images
            output_path: Output video path
            
        Returns:
            Path to created video
        """
        import cv2
        
        logger.info("Creating video with OpenCV")
        
        # Define the codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, (self.target_width, self.target_height))
        
        frames_per_image = int(self.frame_duration * self.fps)
        
        for i, styled_image in enumerate(styled_images):
            img_path = styled_image.styled_image_path
            
            if not os.path.exists(img_path):
                logger.warning(f"Styled image not found, skipping: {img_path}")
                continue
            
            # Load and process image
            img = cv2.imread(img_path)
            if img is None:
                logger.warning(f"Could not load image: {img_path}")
                continue
            
            # Resize to target resolution
            img_resized = cv2.resize(img, (self.target_width, self.target_height))
            
            # Write frames (repeat image for duration)
            for frame_idx in range(frames_per_image):
                # Apply transitions if enabled
                if self.transitions_enabled and self.transition_type == 'fade':
                    alpha = self._calculate_fade_alpha(frame_idx, frames_per_image, i, len(styled_images))
                    if alpha < 1.0:
                        img_faded = (img_resized * alpha).astype(np.uint8)
                        out.write(img_faded)
                    else:
                        out.write(img_resized)
                else:
                    out.write(img_resized)
            
            logger.debug(f"Added frames for image {i+1}/{len(styled_images)}: {os.path.basename(img_path)}")
        
        # Release everything
        out.release()
        
        return output_path
    
    def _calculate_fade_alpha(self, frame_idx: int, frames_per_image: int, image_idx: int, total_images: int) -> float:
        """
        Calculate fade alpha for transitions
        
        Args:
            frame_idx: Current frame index within image
            frames_per_image: Total frames per image
            image_idx: Current image index
            total_images: Total number of images
            
        Returns:
            Alpha value for fade effect
        """
        transition_frames = int(self.transition_duration * self.fps)
        
        # Fade in at start
        if image_idx == 0 and frame_idx < transition_frames:
            return frame_idx / transition_frames
        
        # Fade out at end
        if image_idx == total_images - 1 and frame_idx >= frames_per_image - transition_frames:
            fade_progress = (frames_per_image - frame_idx) / transition_frames
            return fade_progress
        
        return 1.0
    
    def _get_codec_params(self) -> Dict[str, Any]:
        """
        Get codec parameters based on quality setting
        
        Returns:
            Dictionary of codec parameters
        """
        if self.quality == 'high':
            return {
                'bitrate': '8000k',
                'audio': False
            }
        elif self.quality == 'medium':
            return {
                'bitrate': '4000k',
                'audio': False
            }
        else:  # low
            return {
                'bitrate': '2000k',
                'audio': False
            }
    
    def _save_reconstruction_metadata(self, styled_images: List[StyledImage], output_dir: str, video_path: str):
        """
        Save reconstruction metadata to JSON file
        
        Args:
            styled_images: List of styled images used
            output_dir: Output directory
            video_path: Path to generated video
        """
        total_duration = len(styled_images) * self.frame_duration
        
        metadata = {
            'video_path': video_path,
            'total_images': len(styled_images),
            'total_duration': total_duration,
            'total_duration_formatted': format_duration(total_duration),
            'reconstruction_settings': {
                'frame_duration': self.frame_duration,
                'fps': self.fps,
                'target_resolution': f"{self.target_width}x{self.target_height}",
                'codec': self.codec,
                'quality': self.quality,
                'transitions_enabled': self.transitions_enabled,
                'transition_type': self.transition_type,
                'transition_duration': self.transition_duration
            },
            'image_sequence': [
                {
                    'scene_id': img.scene_id,
                    'styled_image_path': img.styled_image_path,
                    'style_preset': img.style_preset,
                    'order_index': i
                }
                for i, img in enumerate(styled_images)
            ]
        }
        
        metadata_file = Path(output_dir) / "video_reconstruction_metadata.json"
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Reconstruction metadata saved to: {metadata_file}")


class AdvancedVideoReconstructor(VideoReconstructor):
    """Advanced video reconstructor with additional features"""
    
    def __init__(self):
        super().__init__()
        self.enable_audio = self.config.get('video_reconstruction.audio.enabled', False)
        self.audio_track_path = self.config.get('video_reconstruction.audio.track_path', '')
        self.enable_effects = self.config.get('video_reconstruction.effects.enabled', False)
    
    def reconstruct_video_with_effects(self, styled_images: List[StyledImage], output_dir: str, 
                                     output_filename: str = None, audio_path: str = None) -> str:
        """
        Reconstruct video with advanced effects and optional audio
        
        Args:
            styled_images: List of styled images
            output_dir: Output directory
            output_filename: Optional output filename
            audio_path: Optional audio track path
            
        Returns:
            Path to generated video file
        """
        if not styled_images:
            raise ValueError("No styled images provided")
        
        sorted_images = sorted(styled_images, key=lambda x: x.scene_id)
        
        if output_filename is None:
            output_filename = "heroshot_enhanced.mp4"
        
        output_path = Path(output_dir) / output_filename
        
        logger.info(f"Creating enhanced video with {len(sorted_images)} images")
        
        try:
            from moviepy.editor import (
                ImageClip, AudioFileClip, CompositeVideoClip, 
                concatenate_videoclips, VideoFileClip
            )
            from moviepy.video.fx.all import fadein, fadeout, resize
        except ImportError:
            logger.error("MoviePy required for advanced video reconstruction")
            raise ImportError("moviepy package required for enhanced features")
        
        # Create video clips with effects
        clips = []
        
        for i, styled_image in enumerate(sorted_images):
            if not os.path.exists(styled_image.styled_image_path):
                logger.warning(f"Image not found: {styled_image.styled_image_path}")
                continue
            
            # Create base clip
            clip = ImageClip(styled_image.styled_image_path, duration=self.frame_duration)
            clip = clip.resize((self.target_width, self.target_height))
            
            # Apply effects if enabled
            if self.enable_effects:
                clip = self._apply_image_effects(clip, i, len(sorted_images))
            
            # Apply transitions
            if self.transitions_enabled:
                clip = self._apply_transitions(clip, i, len(sorted_images))
            
            clips.append(clip)
        
        if not clips:
            raise ValueError("No valid clips created")
        
        # Combine clips
        final_video = concatenate_videoclips(clips, method="compose")
        final_video = final_video.set_fps(self.fps)
        
        # Add audio if specified
        if audio_path and os.path.exists(audio_path):
            audio = AudioFileClip(audio_path)
            # Adjust audio duration to match video
            if audio.duration > final_video.duration:
                audio = audio.subclip(0, final_video.duration)
            elif audio.duration < final_video.duration:
                # Loop audio if it's shorter than video
                loops_needed = int(final_video.duration / audio.duration) + 1
                audio = concatenate_audioclips([audio] * loops_needed).subclip(0, final_video.duration)
            
            final_video = final_video.set_audio(audio)
        
        # Write final video
        codec_params = self._get_codec_params()
        final_video.write_videofile(
            str(output_path),
            fps=self.fps,
            codec=self.codec,
            **codec_params,
            verbose=False,
            logger=None
        )
        
        # Cleanup
        final_video.close()
        for clip in clips:
            clip.close()
        
        return str(output_path)
    
    def _apply_image_effects(self, clip, image_index: int, total_images: int):
        """
        Apply visual effects to image clip
        
        Args:
            clip: MoviePy ImageClip
            image_index: Index of current image
            total_images: Total number of images
            
        Returns:
            Modified clip with effects
        """
        # Add subtle zoom effect
        zoom_factor = 1.05
        clip = clip.resize(lambda t: 1 + (zoom_factor - 1) * t / clip.duration)
        
        return clip
    
    def _apply_transitions(self, clip, image_index: int, total_images: int):
        """
        Apply transition effects to clip
        
        Args:
            clip: MoviePy clip
            image_index: Index of current image
            total_images: Total number of images
            
        Returns:
            Modified clip with transitions
        """
        from moviepy.video.fx.all import fadein, fadeout
        
        if self.transition_type == 'fade':
            if image_index == 0:
                clip = clip.fx(fadein, self.transition_duration)
            elif image_index == total_images - 1:
                clip = clip.fx(fadeout, self.transition_duration)
            else:
                clip = clip.fx(fadein, self.transition_duration).fx(fadeout, self.transition_duration)
        
        return clip


def create_preview_video(styled_images: List[StyledImage], output_dir: str, 
                        preview_duration: float = 5.0) -> str:
    """
    Create a short preview video for quick review
    
    Args:
        styled_images: List of styled images
        output_dir: Output directory
        preview_duration: Total duration of preview in seconds
        
    Returns:
        Path to preview video
    """
    if not styled_images:
        raise ValueError("No styled images provided")
    
    # Calculate frame duration for preview
    frame_duration = preview_duration / len(styled_images)
    
    # Create temporary config for preview
    preview_reconstructor = VideoReconstructor()
    preview_reconstructor.frame_duration = frame_duration
    preview_reconstructor.target_width = 854  # Lower resolution for preview
    preview_reconstructor.target_height = 480
    
    preview_filename = "heroshot_preview.mp4"
    
    return preview_reconstructor.reconstruct_video(
        styled_images, 
        output_dir, 
        preview_filename
    )