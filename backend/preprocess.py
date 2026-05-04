import cv2
import numpy as np
from PIL import Image
import io
import logging
import time
from typing import Tuple, Dict, List

logger = logging.getLogger(__name__)


def detect_skew_angle(gray_image: np.ndarray) -> float:
    """Returns skew angle in degrees using Hough line detection"""
    try:
        # Apply edge detection
        edges = cv2.Canny(gray_image, 50, 150, apertureSize=3)
        
        # Detect lines using Hough transform
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        
        if lines is None:
            return 0.0
        
        angles = []
        for rho, theta in lines[:20]:  # Use first 20 lines
            angle = np.degrees(theta) - 90
            # Filter angles to reasonable skew range
            if -45 < angle < 45:
                angles.append(angle)
        
        if not angles:
            return 0.0
        
        # Return median angle to avoid outliers
        return float(np.median(angles))
    
    except Exception as e:
        logger.warning(f"Skew detection failed: {e}")
        return 0.0


def correct_skew(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotates image to correct detected skew"""
    if abs(angle) < 0.5:  # Skip rotation for very small angles
        return image
    
    try:
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        
        # Create rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Calculate new image dimensions
        cos_angle = abs(rotation_matrix[0, 0])
        sin_angle = abs(rotation_matrix[0, 1])
        new_w = int((h * sin_angle) + (w * cos_angle))
        new_h = int((h * cos_angle) + (w * sin_angle))
        
        # Adjust rotation matrix for new center
        rotation_matrix[0, 2] += (new_w / 2) - center[0]
        rotation_matrix[1, 2] += (new_h / 2) - center[1]
        
        # Apply rotation
        rotated = cv2.warpAffine(image, rotation_matrix, (new_w, new_h), 
                                flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        return rotated
    
    except Exception as e:
        logger.warning(f"Skew correction failed: {e}")
        return image


def segment_into_lines(pil_image: Image.Image) -> List[Image.Image]:
    """
    Segments a preprocessed prescription image into individual line crops.

    Strategy:
    1. Convert RGB PIL image → OpenCV grayscale
    2. Otsu binary threshold (works well on already-binarised preprocessed images)
    3. Horizontal morphological dilation with a resolution-relative kernel to
       merge adjacent characters into single horizontal blobs per line
    4. Find external contours of those blobs
    5. Sort contours top-to-bottom; skip noise blobs that are too small
    6. Crop each line from the *original* PIL image with a small vertical pad
    7. Return the list of line PIL images, or [pil_image] as a safe fallback

    Args:
        pil_image: RGB PIL image (output of preprocess_prescription_image)

    Returns:
        List of PIL.Image objects, one per detected text line.
    """
    try:
        # --- 1. PIL RGB → OpenCV grayscale ---
        img_np = np.array(pil_image)
        # pil_image is RGB; convert to BGR for OpenCV then to gray
        bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        h_img, w_img = gray.shape

        # --- 2. Otsu threshold ---
        # The image coming from preprocess is already near-binary (adaptive
        # threshold + denoised), so Otsu reliably produces a clean binary mask.
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # --- 3. Horizontal dilation (resolution-relative kernel) ---
        # A fixed 50px kernel fails at different DPIs; scale to ~1/15 of image width.
        # Clamp between 30 and 150 px to handle very small or very large images.
        kernel_w = int(np.clip(w_img // 15, 30, 150))
        kernel_h = 3  # thin vertical extent keeps adjacent lines separate
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, kernel_h))
        dilated = cv2.dilate(binary, kernel, iterations=1)

        # --- 4. Find external contours ---
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            logger.warning("segment_into_lines: no contours found, returning full image as fallback")
            return [pil_image]

        # --- 5. Filter noise blobs and sort top-to-bottom ---
        # Minimum thresholds: skip blobs that are too thin (smudges/borders).
        # Use relative thresholds so they work across resolutions.
        min_h = max(10, h_img // 80)   # at least ~1.25% of image height
        min_w = max(40, w_img // 30)   # at least ~3.3% of image width

        bounding_boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h < min_h or w < min_w:
                logger.debug(f"Skipping noise blob at y={y}: w={w}, h={h}")
                continue
            bounding_boxes.append((x, y, w, h))

        if not bounding_boxes:
            logger.warning("segment_into_lines: all blobs filtered as noise, returning full image")
            return [pil_image]

        # Sort top-to-bottom by the y coordinate of the bounding box
        bounding_boxes.sort(key=lambda b: b[1])

        # --- 6. Crop each line with vertical padding ---
        pad = max(4, h_img // 200)  # ~0.5% vertical padding, min 4px
        line_images: List[Image.Image] = []

        for x, y, w, h in bounding_boxes:
            y1 = max(0, y - pad)
            y2 = min(h_img, y + h + pad)
            x1 = max(0, x - pad)
            x2 = min(w_img, x + w + pad)

            crop = pil_image.crop((x1, y1, x2, y2))
            line_images.append(crop)

        logger.info(f"segment_into_lines: detected {len(line_images)} lines "
                    f"(image {w_img}x{h_img}, kernel_w={kernel_w})")

        return line_images

    except Exception as e:
        logger.error(f"segment_into_lines failed: {e}", exc_info=True)
        # Safe fallback: pass the full image to OCR unchanged
        return [pil_image]


def preprocess_prescription_image(image_bytes: bytes) -> Tuple[Image.Image, Dict]:
    """
    Full preprocessing pipeline for Indian prescription photos.
    
    Steps:
    1. Decode bytes to numpy array via cv2.imdecode
    2. Convert to grayscale
    3. Deskew: detect skew angle via Hough line transform, rotate to correct
    4. Adaptive thresholding: cv2.adaptiveThreshold with ADAPTIVE_THRESH_GAUSSIAN_C
       blockSize=11, C=2 for handwritten text
    5. Denoise: cv2.fastNlMeansDenoising
    6. Contrast stretch: clip histogram to 2nd and 98th percentile
    7. Upscale if image shorter dimension < 800px (bicubic, target 1200px)
    8. Return as PIL.Image in RGB mode (TrOCR expects RGB)
    
    Returns:
        Tuple of (processed_image, preprocessing_metadata)
    """
    start_time = time.time()
    metadata = {}
    
    try:
        # Step 1: Decode bytes to numpy array
        step_start = time.time()
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Could not decode image")
        
        metadata['decode_time_ms'] = int((time.time() - step_start) * 1000)
        logger.info(f"Image decoded: {image.shape}")
        
        # Step 2: Convert to grayscale
        step_start = time.time()
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        metadata['grayscale_time_ms'] = int((time.time() - step_start) * 1000)
        
        # Step 3: Deskew
        step_start = time.time()
        skew_angle = detect_skew_angle(gray)
        metadata['skew_angle'] = skew_angle
        
        if abs(skew_angle) > 0.5:
            gray = correct_skew(gray, skew_angle)
            logger.info(f"Corrected skew by {skew_angle:.2f} degrees")
        
        metadata['deskew_time_ms'] = int((time.time() - step_start) * 1000)
        
        # Step 4: Adaptive thresholding
        step_start = time.time()
        # Use adaptive threshold for handwritten text
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, blockSize=11, C=2
        )
        
        metadata['threshold_time_ms'] = int((time.time() - step_start) * 1000)
        
        # Step 5: Denoise
        step_start = time.time()
        denoised = cv2.fastNlMeansDenoising(thresh, h=10, templateWindowSize=7, searchWindowSize=21)
        metadata['denoise_time_ms'] = int((time.time() - step_start) * 1000)
        
        # Step 6: Contrast stretch
        step_start = time.time()
        # Calculate 2nd and 98th percentiles
        p2, p98 = np.percentile(denoised, (2, 98))
        
        # Clip and stretch contrast
        stretched = np.clip(denoised, p2, p98)
        stretched = ((stretched - p2) / (p98 - p2) * 255).astype(np.uint8)
        
        metadata['contrast_stretch_time_ms'] = int((time.time() - step_start) * 1000)
        
        # Step 7: Upscale if needed
        step_start = time.time()
        h, w = stretched.shape
        min_dim = min(h, w)
        metadata['original_size'] = (w, h)
        metadata['was_upscaled'] = False
        
        if min_dim < 800:
            # Calculate scale factor to make shorter dimension 1200px
            scale_factor = 1200 / min_dim
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            
            stretched = cv2.resize(stretched, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            metadata['was_upscaled'] = True
            metadata['scale_factor'] = scale_factor
            metadata['final_size'] = (new_w, new_h)
            logger.info(f"Upscaled from {w}x{h} to {new_w}x{new_h}")
        else:
            metadata['final_size'] = (w, h)
        
        metadata['upscale_time_ms'] = int((time.time() - step_start) * 1000)
        
        # Step 8: Convert to PIL Image in RGB mode
        step_start = time.time()
        # Convert grayscale to RGB for TrOCR
        rgb_image = cv2.cvtColor(stretched, cv2.COLOR_GRAY2RGB)
        pil_image = Image.fromarray(rgb_image)
        
        metadata['pil_conversion_time_ms'] = int((time.time() - step_start) * 1000)
        metadata['total_processing_time_ms'] = int((time.time() - start_time) * 1000)
        
        logger.info(f"Preprocessing completed in {metadata['total_processing_time_ms']}ms")
        
        return pil_image, metadata
    
    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        # Return original image as fallback
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is not None:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_image)
                metadata['error'] = str(e)
                metadata['fallback_used'] = True
                return pil_image, metadata
        except:
            pass
        
        # Last resort: create a blank image
        blank_image = Image.new('RGB', (800, 600), color='white')
        metadata['error'] = str(e)
        metadata['blank_fallback'] = True
        return blank_image, metadata