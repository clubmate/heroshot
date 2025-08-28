"""
Utility functions for HeroShot
"""

import os
import re
import hashlib
import logging
from pathlib import Path
from typing import Optional, Union, Tuple
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO", verbose: bool = False, log_file: Optional[str] = None):
    """
    Setup logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        verbose: Enable verbose logging
        log_file: Optional log file path
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    if verbose:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
    else:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    logger.info(f"Logging setup complete - Level: {level}, Verbose: {verbose}")


def is_youtube_url(url: str) -> bool:
    """
    Check if URL is a YouTube URL
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is a YouTube URL
    """
    youtube_domains = [
        'youtube.com', 'youtu.be', 'www.youtube.com', 'www.youtu.be',
        'm.youtube.com', 'music.youtube.com'
    ]
    
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower() in youtube_domains
    except:
        return False


def extract_youtube_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from URL
    
    Args:
        url: YouTube URL
        
    Returns:
        Video ID or None if not found
    """
    # Common YouTube URL patterns
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]+)',
        r'youtube\.com\/v\/([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename for filesystem compatibility
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Replace spaces with underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip(' .')
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    # Ensure not empty
    if not sanitized:
        sanitized = "untitled"
    
    return sanitized


def create_output_directory(base_dir: str, video_name: str, create_subdirectory: bool = True) -> Path:
    """
    Create output directory structure
    
    Args:
        base_dir: Base output directory
        video_name: Video name for subdirectory
        create_subdirectory: Whether to create subdirectory
        
    Returns:
        Path to output directory
    """
    base_path = Path(base_dir)
    
    if create_subdirectory:
        sanitized_name = sanitize_filename(video_name)
        output_path = base_path / sanitized_name
    else:
        output_path = base_path
    
    # Create directories
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (output_path / "segments").mkdir(exist_ok=True)
    (output_path / "hero_shots").mkdir(exist_ok=True)
    (output_path / "styled_images").mkdir(exist_ok=True)
    
    logger.info(f"Created output directory: {output_path}")
    return output_path


def get_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """
    Calculate file hash
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)
        
    Returns:
        File hash as hex string
    """
    hash_algo = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_algo.update(chunk)
    
    return hash_algo.hexdigest()


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "1h 23m 45s")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable string
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def get_video_info(file_path: str) -> dict:
    """
    Get basic video information
    
    Args:
        file_path: Path to video file
        
    Returns:
        Dictionary with video information
    """
    import cv2
    
    try:
        cap = cv2.VideoCapture(file_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {file_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        duration = frame_count / fps if fps > 0 else 0
        file_size = os.path.getsize(file_path)
        
        cap.release()
        
        return {
            'duration': duration,
            'fps': fps,
            'frame_count': frame_count,
            'width': width,
            'height': height,
            'resolution': f"{width}x{height}",
            'file_size': file_size,
            'file_size_formatted': format_file_size(file_size),
            'duration_formatted': format_duration(duration)
        }
        
    except Exception as e:
        logger.error(f"Failed to get video info for {file_path}: {e}")
        return {}


def ensure_model_cache_dir() -> Path:
    """
    Ensure model cache directory exists
    
    Returns:
        Path to model cache directory
    """
    cache_dir = Path.home() / ".cache" / "heroshot" / "models"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def validate_gpu_availability() -> Tuple[bool, Optional[str]]:
    """
    Check GPU availability and return device info
    
    Returns:
        Tuple of (is_available, device_name)
    """
    try:
        import torch
        
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            return True, device_name
        else:
            return False, None
            
    except ImportError:
        logger.warning("PyTorch not available, cannot check GPU")
        return False, None


def get_optimal_device() -> str:
    """
    Get optimal device for computation
    
    Returns:
        Device string ("cuda", "mps", or "cpu")
    """
    try:
        import torch
        
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
            
    except ImportError:
        return "cpu"


def detect_source_type(source: str) -> str:
    """
    Detect source type (YouTube or local file)
    
    Args:
        source: Source string (URL or file path)
        
    Returns:
        Source type: 'youtube' or 'local'
    """
    if is_youtube_url(source):
        return 'youtube'
    else:
        return 'local'