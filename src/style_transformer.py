"""
Style transformation functionality using Flux and LoRA models
"""

import os
import json
import logging
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass
from PIL import Image

try:
    from .config import get_config
    from .hero_shot_extractor import HeroShot
    from .utils import get_optimal_device, ensure_model_cache_dir
except ImportError:
    from config import get_config
    from hero_shot_extractor import HeroShot
    from utils import get_optimal_device, ensure_model_cache_dir

logger = logging.getLogger(__name__)


@dataclass
class StyledImage:
    """Represents a styled image generated from a hero shot"""
    scene_id: int
    original_hero_shot_path: str
    styled_image_path: str
    style_preset: str
    prompt: str
    negative_prompt: str
    generation_params: Dict[str, Any]
    seed: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert styled image to dictionary"""
        return {
            'scene_id': self.scene_id,
            'original_hero_shot_path': self.original_hero_shot_path,
            'styled_image_path': self.styled_image_path,
            'style_preset': self.style_preset,
            'prompt': self.prompt,
            'negative_prompt': self.negative_prompt,
            'generation_params': self.generation_params,
            'seed': self.seed
        }


class FluxStyleTransformer:
    """Style transformation using Flux diffusion models"""
    
    def __init__(self):
        self.config = get_config()
        self.device = self._get_device()
        self.model_path = self.config.get('style_transformation.flux.model_path', 'black-forest-labs/FLUX.1-dev')
        self.precision = self.config.get('style_transformation.flux.precision', 'fp16')
        self.lora_enabled = self.config.get('style_transformation.lora.enabled', False)
        self.lora_weights_path = self.config.get('style_transformation.lora.weights_path', '')
        self.lora_scale = self.config.get('style_transformation.lora.scale', 1.0)
        
        self.pipeline = None
        self._load_model()
    
    def _get_device(self) -> str:
        """Get optimal device for computation"""
        device_setting = self.config.get('style_transformation.flux.device', 'auto')
        
        if device_setting == 'auto':
            return get_optimal_device()
        else:
            return device_setting
    
    def _load_model(self):
        """Load Flux diffusion model"""
        try:
            from diffusers import FluxPipeline
            import torch
            
            logger.info(f"Loading Flux model: {self.model_path}")
            logger.info(f"Device: {self.device}, Precision: {self.precision}")
            
            # Set torch dtype based on precision
            if self.precision == 'fp16':
                torch_dtype = torch.float16
            elif self.precision == 'bf16':
                torch_dtype = torch.bfloat16
            else:
                torch_dtype = torch.float32
            
            # Load pipeline
            self.pipeline = FluxPipeline.from_pretrained(
                self.model_path,
                torch_dtype=torch_dtype,
                device_map="auto" if self.device == "cuda" else None,
                cache_dir=str(ensure_model_cache_dir())
            )
            
            # Move to device if not using device_map
            if self.device != "cuda" or not hasattr(self.pipeline, 'device_map'):
                self.pipeline = self.pipeline.to(self.device)
            
            # Enable memory efficient attention if available
            if hasattr(self.pipeline.unet, 'enable_xformers_memory_efficient_attention'):
                try:
                    self.pipeline.unet.enable_xformers_memory_efficient_attention()
                    logger.info("Enabled xformers memory efficient attention")
                except Exception as e:
                    logger.warning(f"Could not enable xformers: {e}")
            
            # Load LoRA weights if enabled
            if self.lora_enabled and self.lora_weights_path:
                self._load_lora_weights()
            
            logger.info("Flux model loaded successfully")
            
        except ImportError:
            logger.error("diffusers package not available. Please install with: pip install diffusers")
            raise ImportError("diffusers is required for style transformation")
        except Exception as e:
            logger.error(f"Failed to load Flux model: {e}")
            raise
    
    def _load_lora_weights(self):
        """Load LoRA weights for the model"""
        try:
            if not os.path.exists(self.lora_weights_path):
                logger.error(f"LoRA weights file not found: {self.lora_weights_path}")
                return
            
            logger.info(f"Loading LoRA weights: {self.lora_weights_path}")
            
            # Load LoRA weights (implementation depends on specific LoRA format)
            # This is a placeholder - actual implementation would depend on the LoRA format
            self.pipeline.load_lora_weights(self.lora_weights_path)
            
            logger.info(f"LoRA weights loaded with scale: {self.lora_scale}")
            
        except Exception as e:
            logger.error(f"Failed to load LoRA weights: {e}")
    
    def transform_image(self, 
                       image_path: str, 
                       style_preset: str, 
                       caption: Optional[str] = None,
                       seed: Optional[int] = None) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Transform image using specified style preset
        
        Args:
            image_path: Path to input image
            style_preset: Style preset name
            caption: Optional caption to enhance prompt
            seed: Optional seed for reproducible generation
            
        Returns:
            Tuple of (generated_image, generation_params)
        """
        if self.pipeline is None:
            raise RuntimeError("Flux model not loaded")
        
        # Load input image
        input_image = Image.open(image_path).convert('RGB')
        
        # Get style preset configuration
        preset_config = self._get_style_preset_config(style_preset)
        
        # Build prompt
        prompt = self._build_prompt(preset_config, caption)
        negative_prompt = preset_config.get('negative_prompt', '')
        
        # Generation parameters
        generation_params = {
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'guidance_scale': preset_config.get('guidance_scale', 7.5),
            'num_inference_steps': preset_config.get('num_inference_steps', 30),
            'width': input_image.width,
            'height': input_image.height,
        }
        
        # Set seed for reproducibility
        if seed is not None:
            import torch
            generator = torch.Generator(device=self.device).manual_seed(seed)
            generation_params['generator'] = generator
        
        logger.info(f"Generating styled image with preset: {style_preset}")
        logger.debug(f"Prompt: {prompt}")
        
        try:
            # Generate styled image
            with torch.autocast(self.device if self.device != 'cpu' else 'cpu'):
                result = self.pipeline(
                    image=input_image,
                    **generation_params
                )
            
            generated_image = result.images[0]
            
            return generated_image, generation_params
            
        except Exception as e:
            logger.error(f"Failed to generate styled image: {e}")
            raise
    
    def _get_style_preset_config(self, style_preset: str) -> Dict[str, Any]:
        """
        Get configuration for style preset
        
        Args:
            style_preset: Name of style preset
            
        Returns:
            Style preset configuration
        """
        presets = self.config.get('style_transformation.presets', {})
        
        if style_preset not in presets:
            logger.warning(f"Style preset '{style_preset}' not found, using default")
            style_preset = 'cinematic'
        
        return presets.get(style_preset, {
            'prompt_suffix': 'high quality, detailed',
            'negative_prompt': 'low quality, blurry',
            'guidance_scale': 7.5,
            'num_inference_steps': 30
        })
    
    def _build_prompt(self, preset_config: Dict[str, Any], caption: Optional[str] = None) -> str:
        """
        Build prompt for generation
        
        Args:
            preset_config: Style preset configuration
            caption: Optional caption
            
        Returns:
            Built prompt string
        """
        prompt_parts = []
        
        # Add caption if available
        if caption:
            prompt_parts.append(caption)
        
        # Add style suffix
        prompt_suffix = preset_config.get('prompt_suffix', '')
        if prompt_suffix:
            prompt_parts.append(prompt_suffix)
        
        return ', '.join(prompt_parts)


class StyleTransformationPipeline:
    """Main style transformation pipeline"""
    
    def __init__(self):
        self.config = get_config()
        self.transformer = FluxStyleTransformer()
        self.default_style_preset = self.config.get('style_transformation.generation.style_preset', 'cinematic')
        self.random_style_selection = self.config.get('style_transformation.generation.random_style_selection', False)
        self.multiple_variations = self.config.get('style_transformation.generation.multiple_variations', False)
        self.variations_per_image = self.config.get('style_transformation.generation.variations_per_image', 1)
        self.base_seed = self.config.get('style_transformation.generation.seed', None)
    
    def transform_hero_shots(self, hero_shots: List[HeroShot], output_dir: str) -> List[StyledImage]:
        """
        Transform all hero shots with style transformation
        
        Args:
            hero_shots: List of hero shots to transform
            output_dir: Output directory for styled images
            
        Returns:
            List of styled images
        """
        output_path = Path(output_dir) / "styled_images"
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting style transformation for {len(hero_shots)} hero shots")
        
        styled_images = []
        available_presets = list(self.config.get('style_transformation.presets', {}).keys())
        
        if not available_presets:
            available_presets = ['cinematic']
            logger.warning("No style presets found, using default")
        
        for hero_shot in hero_shots:
            logger.info(f"Transforming hero shot for scene {hero_shot.scene_id}")
            
            # Determine style preset(s)
            if self.random_style_selection:
                style_presets = [random.choice(available_presets)]
            else:
                style_presets = [self.default_style_preset]
            
            # Generate multiple variations if enabled
            num_variations = self.variations_per_image if self.multiple_variations else 1
            
            for variation_idx in range(num_variations):
                for style_preset in style_presets:
                    try:
                        styled_image = self._transform_single_hero_shot(
                            hero_shot, 
                            style_preset, 
                            output_path,
                            variation_idx
                        )
                        
                        if styled_image:
                            styled_images.append(styled_image)
                            
                    except Exception as e:
                        logger.error(f"Failed to transform hero shot {hero_shot.scene_id}: {e}")
        
        # Save styled image metadata
        self._save_styled_image_metadata(styled_images, output_dir)
        
        logger.info(f"Style transformation complete. Generated {len(styled_images)} styled images")
        return styled_images
    
    def _transform_single_hero_shot(self, 
                                  hero_shot: HeroShot, 
                                  style_preset: str, 
                                  output_path: Path,
                                  variation_idx: int = 0) -> Optional[StyledImage]:
        """
        Transform a single hero shot
        
        Args:
            hero_shot: Hero shot to transform
            style_preset: Style preset to use
            output_path: Output directory
            variation_idx: Variation index for multiple generations
            
        Returns:
            Styled image or None if failed
        """
        # Generate seed
        if self.base_seed is not None:
            seed = self.base_seed + hero_shot.scene_id * 1000 + variation_idx
        else:
            seed = None
        
        # Transform image
        generated_image, generation_params = self.transformer.transform_image(
            hero_shot.image_path,
            style_preset,
            hero_shot.caption,
            seed
        )
        
        # Create output filename
        base_name = Path(hero_shot.image_path).stem
        if variation_idx > 0:
            filename = f"{base_name}_{style_preset}_var{variation_idx:02d}.png"
        else:
            filename = f"{base_name}_{style_preset}.png"
        
        output_file = output_path / filename
        
        # Save generated image
        generated_image.save(str(output_file), format='PNG')
        
        # Create styled image object
        styled_image = StyledImage(
            scene_id=hero_shot.scene_id,
            original_hero_shot_path=hero_shot.image_path,
            styled_image_path=str(output_file),
            style_preset=style_preset,
            prompt=generation_params['prompt'],
            negative_prompt=generation_params['negative_prompt'],
            generation_params=generation_params,
            seed=seed
        )
        
        logger.info(f"Generated styled image: {filename}")
        return styled_image
    
    def _save_styled_image_metadata(self, styled_images: List[StyledImage], output_dir: str):
        """
        Save styled image metadata to JSON file
        
        Args:
            styled_images: List of styled images
            output_dir: Output directory
        """
        metadata = {
            'total_styled_images': len(styled_images),
            'transformation_settings': {
                'model_path': self.transformer.model_path,
                'device': self.transformer.device,
                'precision': self.transformer.precision,
                'lora_enabled': self.transformer.lora_enabled,
                'default_style_preset': self.default_style_preset,
                'random_style_selection': self.random_style_selection,
                'multiple_variations': self.multiple_variations,
                'variations_per_image': self.variations_per_image
            },
            'styled_images': [styled_image.to_dict() for styled_image in styled_images]
        }
        
        metadata_file = Path(output_dir) / "styled_images_metadata.json"
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Styled image metadata saved to: {metadata_file}")


def load_styled_image_metadata(metadata_path: str) -> List[StyledImage]:
    """
    Load styled image metadata from JSON file
    
    Args:
        metadata_path: Path to metadata JSON file
        
    Returns:
        List of styled images
    """
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    styled_images = []
    for styled_data in metadata['styled_images']:
        styled_image = StyledImage(
            scene_id=styled_data['scene_id'],
            original_hero_shot_path=styled_data['original_hero_shot_path'],
            styled_image_path=styled_data['styled_image_path'],
            style_preset=styled_data['style_preset'],
            prompt=styled_data['prompt'],
            negative_prompt=styled_data['negative_prompt'],
            generation_params=styled_data['generation_params'],
            seed=styled_data.get('seed')
        )
        styled_images.append(styled_image)
    
    return styled_images