"""
Image Quality Scoring for CAD/3D Model Generation.

Uses Google Cloud Vision API to analyze and score downloaded machine images
based on suitability for 2D/3D CAD conversion (Module 2).

Scoring criteria:
- Machine visibility & prominence
- Image quality (sharpness, brightness, contrast)
- View angle (front/side/isometric preferred)
- Absence of occlusions
- Object detection confidence
"""

import logging
from typing import List, Dict, Optional, Tuple
import httpx
from google.cloud import vision
import os

logger = logging.getLogger(__name__)


# ============================================================================
# IMAGE QUALITY SCORING
# ============================================================================

class ImageQualityScorer:
    """Score images for suitability in CAD/3D model generation."""
    
    def __init__(self):
        """Initialize Vision API client."""
        try:
            self.vision_client = vision.ImageAnnotatorClient()
            self.has_vision_api = True
        except Exception as e:
            logger.warning(f"Vision API not available: {e}")
            self.has_vision_api = False
    
    async def score_image(self, image_url: str) -> Dict[str, float]:
        """
        Score a single image for CAD/3D conversion suitability.
        
        Returns score dict with:
        - overall_score: 0-100 (higher is better)
        - machine_prominence: 0-100 (how much image is the machine)
        - clarity_score: 0-100 (sharpness, brightness, contrast)
        - angle_score: 0-100 (suitability of viewing angle)
        - occlusion_score: 0-100 (how visible is the full machine)
        - recommended: True/False (>70 overall score)
        """
        
        if not self.has_vision_api:
            logger.warning("Vision API not available, returning default scores")
            return {
                "overall_score": 50.0,
                "machine_prominence": 50.0,
                "clarity_score": 50.0,
                "angle_score": 50.0,
                "occlusion_score": 50.0,
                "recommended": False,
                "reason": "Vision API not configured"
            }
        
        try:
            image = vision.Image()
            image.source.image_uri = image_url
            
            # Run multiple detection types
            request = vision.AnnotateImageRequest(
                image=image,
                features=[
                    vision.Feature(type_=vision.Feature.Type.OBJECT_LOCALIZATION),
                    vision.Feature(type_=vision.Feature.Type.IMAGE_PROPERTIES),
                    vision.Feature(type_=vision.Feature.Type.WEB_DETECTION),
                    vision.Feature(type_=vision.Feature.Type.SAFE_SEARCH_DETECTION),
                ]
            )
            
            response = self.vision_client.annotate_image(request)
            
            # Calculate individual scores
            machine_prominence = self._score_machine_prominence(response, image_url)
            clarity_score = self._score_clarity(response)
            angle_score = self._score_viewing_angle(response)
            occlusion_score = self._score_occlusion(response)
            
            # CAD-specific suitability scoring
            cad_suitability, cad_recommendation = self._score_cad_suitability(
                response, machine_prominence, clarity_score, angle_score, occlusion_score
            )
            
            # Use CAD suitability as primary score, but keep standard metrics for reference
            overall_score = cad_suitability
            
            recommended = overall_score >= 70.0
            
            return {
                "overall_score": round(overall_score, 1),
                "cad_suitability_score": round(cad_suitability, 1),
                "machine_prominence": round(machine_prominence, 1),
                "clarity_score": round(clarity_score, 1),
                "angle_score": round(angle_score, 1),
                "occlusion_score": round(occlusion_score, 1),
                "background_cleanliness": round(self._score_background_cleanliness(response), 1),
                "machine_completeness": round(self._score_machine_completeness(response), 1),
                "image_relevance": round(self._score_image_relevance(response), 1),
                "recommended": recommended,
                "cad_recommendation": cad_recommendation,
                "reason": self._get_recommendation_reason(
                    machine_prominence, clarity_score, angle_score, occlusion_score
                )
            }
            
        except Exception as e:
            logger.error(f"Image scoring failed for {image_url}: {e}")
            return {
                "overall_score": 0.0,
                "machine_prominence": 0.0,
                "clarity_score": 0.0,
                "angle_score": 0.0,
                "occlusion_score": 0.0,
                "recommended": False,
                "reason": f"Scoring error: {str(e)}"
            }
    
    def _score_machine_prominence(self, response, image_url: str) -> float:
        """
        Score how much of the image is the actual machine (not background).
        
        Uses object detection to find machine-like objects.
        """
        try:
            objects = response.localized_object_annotations
            
            if not objects:
                return 20.0  # No objects detected
            
            # Find largest object (likely the machine)
            max_size = 0.0
            machine_confidence = 0.0
            
            for obj in objects:
                # Calculate bounding box size as % of image
                box = obj.bounding_poly
                if box.normalized_vertices:
                    # Rough size calculation
                    size = 1.0  # Placeholder
                    if size > max_size:
                        max_size = size
                        # Check if object name suggests it's machinery
                        if any(word in obj.name.lower() for word in 
                               ['machine', 'equipment', 'industrial', 'press', 'mixer', 'pump', 'engine']):
                            machine_confidence = obj.score * 100
                        else:
                            machine_confidence = obj.score * 50  # Lower confidence for generic objects
            
            # Clamp to 0-100
            prominence = min(100.0, max(0.0, machine_confidence))
            return prominence
            
        except Exception as e:
            logger.debug(f"Machine prominence scoring failed: {e}")
            return 50.0
    
    def _score_clarity(self, response) -> float:
        """
        Score image quality: sharpness, brightness, contrast.
        
        Uses Vision API image properties.
        """
        try:
            props = response.image_properties_annotation
            
            if not props or not props.dominant_colors:
                return 50.0
            
            clarity_score = 50.0
            
            # Check color distribution (good contrast = varied colors)
            if props.dominant_colors.colors:
                num_colors = len(props.dominant_colors.colors)
                # 4-8 dominant colors suggests good contrast
                if 4 <= num_colors <= 8:
                    clarity_score += 20
                elif num_colors > 8:
                    clarity_score += 15
                elif num_colors >= 3:
                    clarity_score += 10
            
            # Note: Vision API doesn't directly measure sharpness
            # But we can infer from successful object detection
            # (sharp images have clearer object boundaries)
            
            return min(100.0, clarity_score)
            
        except Exception as e:
            logger.debug(f"Clarity scoring failed: {e}")
            return 50.0
    
    def _score_viewing_angle(self, response) -> float:
        """
        Score viewing angle suitability for 3D reconstruction.
        
        Preferred angles:
        - Front view (orthogonal) - best for CAD
        - Side view (orthogonal) - best for CAD
        - Isometric (45 degrees) - good for 3D
        - Top view - good for layout
        - Avoid: extreme angles, foreshortening
        """
        try:
            # Vision API doesn't directly measure viewing angle
            # But object detection quality indicates view clarity
            objects = response.localized_object_annotations
            
            if not objects:
                return 30.0
            
            # Multiple clear objects suggest good angle
            num_objects = len(objects)
            avg_confidence = sum(obj.score for obj in objects) / len(objects)
            
            # Score based on detection quality
            # Good angle = confident object detection
            angle_score = avg_confidence * 100
            
            # Bonus for specific machinery keywords
            for obj in objects:
                if any(word in obj.name.lower() for word in 
                       ['front', 'side', 'view', 'profile', 'isometric']):
                    angle_score += 10
            
            return min(100.0, angle_score)
            
        except Exception as e:
            logger.debug(f"Angle scoring failed: {e}")
            return 50.0
    
    def _score_occlusion(self, response) -> float:
        """
        Score how much of the machine is visible (not occluded).
        
        High score = full machine visible
        Low score = parts hidden by people, clutter, shadows
        """
        try:
            # Check for people/objects that might occlude the machine
            objects = response.localized_object_annotations
            
            occlusion_score = 100.0
            
            # Penalize for obstructing objects
            for obj in objects:
                if any(word in obj.name.lower() for word in 
                       ['person', 'human', 'people', 'hand', 'object', 'clutter']):
                    occlusion_score -= (obj.score * 20)
            
            # Check for shadows/dark areas (use properties)
            props = response.image_properties_annotation
            if props and props.dominant_colors:
                # Many dark colors might indicate shadows
                dark_colors = sum(1 for color in props.dominant_colors.colors 
                                 if color.color.red < 50 and color.color.green < 50 and color.color.blue < 50)
                if dark_colors > 3:
                    occlusion_score -= 15
            
            return max(20.0, occlusion_score)
            
        except Exception as e:
            logger.debug(f"Occlusion scoring failed: {e}")
            return 50.0
    
    def _score_background_cleanliness(self, response) -> float:
        """
        Score background quality for CAD conversion.
        
        Best: Solid colored background (studio setting)
        Good: Plain background with minimal objects
        Poor: Busy background, outdoor setting, people visible
        """
        try:
            props = response.image_properties_annotation
            objects = response.localized_object_annotations
            
            cleanliness_score = 50.0
            
            # Bonus for solid-color background (ideal for CAD)
            if props and props.dominant_colors:
                colors_list = list(props.dominant_colors.colors)
                
                # If one color dominates significantly, background is clean
                if colors_list:
                    top_color_fraction = colors_list[0].pixel_fraction if colors_list[0].pixel_fraction else 0
                    
                    # >60% same color = very clean background
                    if top_color_fraction > 0.6:
                        cleanliness_score = 90.0
                    # 40-60% = reasonably clean
                    elif top_color_fraction > 0.4:
                        cleanliness_score = 75.0
                    # <40% = busy background
                    else:
                        cleanliness_score = 45.0
            
            # Penalize for outdoor/background objects
            for obj in objects:
                obj_name = obj.name.lower()
                # Penalize for things that aren't the machine
                if any(word in obj_name for word in 
                       ['person', 'human', 'person', 'sky', 'tree', 'outdoor', 
                        'background', 'wall', 'floor', 'chair', 'table', 'vehicle']):
                    cleanliness_score -= (obj.score * 10)
            
            return max(10.0, min(100.0, cleanliness_score))
            
        except Exception as e:
            logger.debug(f"Background cleanliness scoring failed: {e}")
            return 50.0
    
    def _score_machine_completeness(self, response) -> float:
        """
        Score how complete/full the machine view is.
        
        Best: Full machine visible from one side (front, side, or isometric)
        Good: Most of machine visible
        Poor: Partial view, cropped, only one component visible
        """
        try:
            objects = response.localized_object_annotations
            
            if not objects:
                return 30.0
            
            completeness_score = 50.0
            
            # Check size of main object (should be large if full machine is visible)
            main_objects = [obj for obj in objects 
                          if any(word in obj.name.lower() for word in 
                                ['machine', 'equipment', 'press', 'pump', 'mixer', 'industrial'])]
            
            if main_objects:
                main_obj = max(main_objects, key=lambda x: x.score)
                
                # Large bounding box = full machine visible
                if main_obj.bounding_poly and main_obj.bounding_poly.normalized_vertices:
                    # Estimate box size
                    vertices = main_obj.bounding_poly.normalized_vertices
                    if len(vertices) >= 2:
                        # Simple size estimation
                        x_coords = [v.x for v in vertices]
                        y_coords = [v.y for v in vertices]
                        width = max(x_coords) - min(x_coords) if x_coords else 0
                        height = max(y_coords) - min(y_coords) if y_coords else 0
                        area = width * height
                        
                        # >25% of image = full machine
                        if area > 0.25:
                            completeness_score = 85.0
                        # >15% = most visible
                        elif area > 0.15:
                            completeness_score = 70.0
                        # >10% = partial
                        elif area > 0.10:
                            completeness_score = 50.0
            
            return min(100.0, completeness_score)
            
        except Exception as e:
            logger.debug(f"Machine completeness scoring failed: {e}")
            return 50.0
    
    def _score_image_relevance(self, response) -> float:
        """
        Score whether this is actually a machine image (filter irrelevant content).
        
        High score: Clear machine/equipment images
        Medium score: Contains machine but with other content
        Low score: Not a machine image (person, diagram, drawing, photo of photo)
        """
        try:
            objects = response.localized_object_annotations
            
            machine_keywords = [
                'machine', 'equipment', 'industrial', 'press', 'pump', 'mixer',
                'motor', 'engine', 'compressor', 'extruder', 'injection', 'mold',
                'furnace', 'heater', 'tank', 'separator', 'conveyor', 'robot',
                'cad', 'mechanical', 'apparatus', 'apparatus'
            ]
            
            irrelevant_keywords = [
                'person', 'human', 'people', 'face', 'photo', 'diagram',
                'drawing', 'screenshot', 'text', 'document', 'certificate',
                'logo', 'chart', 'graph', 'webpage'
            ]
            
            relevance_score = 40.0  # Start low, machines must be clearly detected
            
            # Check detected objects
            machine_score = 0.0
            irrelevant_score = 0.0
            
            for obj in objects:
                obj_name = obj.name.lower()
                
                if any(word in obj_name for word in machine_keywords):
                    machine_score += (obj.score * 50)  # High boost for machine parts
                
                if any(word in obj_name for word in irrelevant_keywords):
                    irrelevant_score += (obj.score * 40)  # Penalize for irrelevant content
            
            # Combine scores
            relevance_score = machine_score - irrelevant_score
            
            # If we detected clear machines, high score
            if machine_score > 0.5:
                relevance_score = max(relevance_score, 75.0)
            
            return max(0.0, min(100.0, relevance_score))
            
        except Exception as e:
            logger.debug(f"Image relevance scoring failed: {e}")
            return 50.0
    
    def _score_cad_suitability(self, response, machine_prominence: float, clarity: float, 
                               angle: float, occlusion: float) -> Tuple[float, str]:
        """
        Calculate overall CAD suitability score for 3D conversion.
        
        CAD-specific criteria prioritize:
        1. Background cleanliness (solid color best)
        2. Machine completeness (full visible machine)
        3. Image relevance (is this actually a machine?)
        4. Standard metrics (prominence, clarity, angle, occlusion)
        
        Returns: (cad_suitability_score, recommendation_text)
        """
        try:
            # CAD-specific scores
            background_cleanliness = self._score_background_cleanliness(response)
            machine_completeness = self._score_machine_completeness(response)
            image_relevance = self._score_image_relevance(response)
            
            # Weighted CAD suitability score
            cad_score = (
                background_cleanliness * 0.25 +   # Clean background most important
                machine_completeness * 0.25 +     # Full machine visibility
                image_relevance * 0.20 +          # Is this really a machine?
                clarity * 0.15 +                  # Image clarity
                angle * 0.10 +                    # Viewing angle
                occlusion * 0.05                  # Minimal occlusion
            )
            
            # Generate recommendation
            if cad_score >= 80:
                recommendation = "Excellent - Ready for 3D CAD conversion"
            elif cad_score >= 70:
                recommendation = "Good - Suitable for CAD conversion with minor cleanup"
            elif cad_score >= 60:
                recommendation = "Fair - May require manual intervention in CAD"
            elif cad_score >= 50:
                recommendation = "Poor - Multiple issues but usable as reference"
            else:
                recommendation = "Not recommended for CAD conversion"
            
            return min(100.0, cad_score), recommendation
            
        except Exception as e:
            logger.debug(f"CAD suitability scoring failed: {e}")
            return 50.0, "Unable to calculate CAD suitability"
    
    @staticmethod
    def _get_recommendation_reason(prominence: float, clarity: float, angle: float, occlusion: float) -> str:
        """Generate human-readable reason for score."""
        issues = []
        
        if prominence < 60:
            issues.append("Machine not prominent enough in image")
        if clarity < 60:
            issues.append("Image quality/contrast could be better")
        if angle < 60:
            issues.append("Viewing angle not ideal for CAD conversion")
        if occlusion < 60:
            issues.append("Part of machine is occluded or hidden")
        
        if not issues:
            return "Excellent image quality, suitable for CAD/3D conversion"
        
        return "; ".join(issues)


# ============================================================================
# BATCH IMAGE SCORING & SELECTION
# ============================================================================

def _filter_product_images(image_urls: List[str]) -> List[str]:
    """Filter out non-product images (diagrams, tables, navbars, trackers, etc)."""
    exclude_keywords = [
        'navbar', 'envelope', 'diagram',
        'chart', 'logo', 'icon', 'payment', 'certification', 'campaign',
        'promotion', 'facebook.com', 'google', 'analytics', 'ad.doubleclick',
        'banner'
    ]
    
    filtered = []
    for url in image_urls:
        url_lower = url.lower()
        
        # Skip if URL contains exclusion keywords
        if any(kw in url_lower for kw in exclude_keywords):
            logger.debug(f"Skipping non-product image (keyword): {url[:60]}...")
            continue
        
        # Skip Facebook tracking pixels specifically
        if 'facebook.com/tr' in url_lower or 'facebook.com/tr?' in url_lower:
            logger.debug(f"Skipping tracking pixel: {url[:60]}...")
            continue
        
        filtered.append(url)
    
    logger.info(f"Filtered images: {len(image_urls)} → {len(filtered)} product images")
    return filtered


async def score_and_select_best_image(image_urls: List[str]) -> Dict:
    """
    Score multiple machine images and select the best one for Module 2.
    
    Returns:
    {
        'best_image_url': str,
        'score': float (0-100),
        'all_scores': [{'url': str, 'scores': dict}],
        'recommendation': str
    }
    """
    if not image_urls:
        return {
            "best_image_url": None,
            "score": 0.0,
            "all_scores": [],
            "recommendation": "No images provided"
        }
    
    # Filter out non-product images first
    product_images = _filter_product_images(image_urls)
    
    if not product_images:
        logger.warning("No product images found after filtering")
        return {
            "best_image_url": None,
            "score": 0.0,
            "all_scores": [],
            "recommendation": "No product images found (all were filtered as non-product)"
        }
    
    scorer = ImageQualityScorer()
    results = []
    
    logger.info(f"Scoring {len(product_images)} product images for CAD/3D suitability...")
    
    for url in product_images[:10]:  # Score top 10 to save API calls
        scores = await scorer.score_image(url)
        results.append({
            "url": url,
            "scores": scores
        })
        logger.info(f"  {url[:60]}... → {scores['overall_score']}/100")
    
    # Find best image
    # If all scores are similar (low variance), use heuristic filename scoring
    scores = [r['scores']['overall_score'] for r in results]
    score_variance = max(scores) - min(scores) if scores else 0
    
    # Lower threshold - be more aggressive with filename heuristics
    if score_variance < 10:  # All scores are too similar, use filename heuristic
        logger.info(f"Low score variance ({score_variance:.1f}) - using filename heuristics instead")
        
        # Prefer images with product-related keywords in filename
        product_keywords = ['product', 'machine', 'lathe', 'turret', 'solo', 'control', 'spindle', 'customcnc', 'powerturn']
        
        def filename_score(url):
            filename = url.lower()
            score = 0
            for kw in product_keywords:
                if kw in filename:
                    score += 10
            # Penalize generic numbered images
            if any(x in filename for x in ['300x225', 'thumbnail', 'nav']):
                score -= 5
            return score
        
        # Sort by filename heuristic, then by Vision score
        results_sorted = sorted(results, key=lambda x: (filename_score(x['url']), -x['scores']['overall_score']), reverse=True)
        best = results_sorted[0]
        logger.info(f"Selected by filename heuristic: {best['url'].split('/')[-1]} (score: {filename_score(best['url'])})")
    else:
        best = max(results, key=lambda x: x['scores']['overall_score'])
        logger.info(f"Selected by Vision API score: {best['url'].split('/')[-1]}")
    
    # Count how many are recommended
    recommended_count = sum(1 for r in results if r['scores']['recommended'])
    
    return {
        "best_image_url": best['url'],
        "best_image_score": best['scores']['overall_score'],
        "best_image_details": best['scores'],
        "all_scores": results,
        "recommended_count": recommended_count,
        "total_scored": len(results),
        "ready_for_module2": best['scores']['overall_score'] >= 70,
        "recommendation": best['scores']['reason']
    }


async def enrich_machine_with_best_image(enriched_machine: dict) -> dict:
    """
    Enhance enriched machine with best image selection.
    
    Adds to enriched_machine:
    - best_image_url: Best quality image for Module 2
    - image_quality_score: 0-100
    - image_analysis: Detailed scoring breakdown
    """
    
    images = enriched_machine.get('images', [])
    
    if not images:
        enriched_machine['best_image_url'] = None
        enriched_machine['image_quality_score'] = 0.0
        enriched_machine['image_analysis'] = {"reason": "No images found"}
        return enriched_machine
    
    # Score and select best image
    selection = await score_and_select_best_image(images)
    
    enriched_machine['best_image_url'] = selection['best_image_url']
    enriched_machine['image_quality_score'] = selection['best_image_score']
    enriched_machine['image_analysis'] = {
        "best_image_details": selection['best_image_details'],
        "total_images_analyzed": selection['total_scored'],
        "recommended_images": selection['recommended_count'],
        "suitable_for_module2_cad": selection['ready_for_module2'],
        "recommendation": selection['recommendation'],
        "all_image_scores": [
            {
                "url": r['url'],
                "overall_score": r['scores']['overall_score'],
                "metrics": {
                    "machine_prominence": r['scores']['machine_prominence'],
                    "clarity": r['scores']['clarity_score'],
                    "angle": r['scores']['angle_score'],
                    "occlusion": r['scores']['occlusion_score'],
                }
            }
            for r in selection['all_scores']
        ]
    }
    
    return enriched_machine


# ============================================================================
# TEST/DEMO
# ============================================================================

async def demo_image_scoring():
    """Test image scoring with real machine images."""
    
    # Sample KraussMaffei injection press images
    test_urls = [
        "https://www.kraussmaffei.com/en/about-us/news/image-gallery/kraussmaffei-at-k-2022-1",
        "https://www.exapro.com/sp/kraussmaffei-km1000-8100mc-51850/",
    ]
    
    print("\n" + "="*80)
    print("TESTING IMAGE QUALITY SCORING FOR CAD/3D CONVERSION")
    print("="*80)
    
    selection = await score_and_select_best_image(test_urls)
    
    print(f"\nBest Image: {selection['best_image_url']}")
    print(f"Overall Score: {selection['best_image_score']}/100")
    print(f"Ready for Module 2: {selection['ready_for_module2']}")
    print(f"\nRecommendation: {selection['recommendation']}")
    
    print("\nDetailed Scores:")
    for result in selection['all_scores']:
        print(f"\n  URL: {result['url'][:60]}...")
        print(f"    Overall: {result['scores']['overall_score']}")
        print(f"    Machine Prominence: {result['scores']['machine_prominence']}")
        print(f"    Clarity: {result['scores']['clarity_score']}")
        print(f"    Angle: {result['scores']['angle_score']}")
        print(f"    Occlusion: {result['scores']['occlusion_score']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_image_scoring())
