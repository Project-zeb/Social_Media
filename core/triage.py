import torch
import requests
import io
from PIL import Image
from transformers import MarianMTModel, MarianTokenizer, CLIPProcessor, CLIPModel

# --- 1. INITIALIZE THE ENGINES ---
model_name = "Helsinki-NLP/opus-mt-hi-en"
translator_tokenizer = MarianTokenizer.from_pretrained(model_name)
translator_model = MarianMTModel.from_pretrained(model_name)

clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

def run_multimodal_triage(event):
    """
    Automated Triage: Translates Hindi and assigns initial Intel Tiers.
    Tier 2 = AI Verified (Math Support) | Tier 1 = Flagged/Suspicious
    """
    post = event.posts.first()
    if not post:
        return

    # --- 2. MULTILINGUAL TRANSLATION (Helsinki-NLP) ---
    inputs = translator_tokenizer(post.raw_text, return_tensors="pt", padding=True)
    translated_tokens = translator_model.generate(**inputs)
    english_text = translator_tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
    
    # Store the translation in the situational overview
    event.summary = english_text

    # --- 3. MULTIMODAL VERIFICATION (OpenAI CLIP) ---
    score = 0.0
    if post.image_url:
        try:
            # Handle both URLs and local file paths for the viva demo
            if post.image_url.startswith('http'):
                response = requests.get(post.image_url, timeout=5)
                img = Image.open(io.BytesIO(response.content)).convert("RGB")
            else:
                img = Image.open(post.image_url).convert("RGB")
            
            clip_inputs = clip_processor(text=[english_text], images=img, return_tensors="pt", padding=True)
            with torch.no_grad():
                outputs = clip_model(**clip_inputs)
            score = float(outputs.logits_per_image[0][0])
        except Exception as e:
            print(f"⚠️ [TRIAGE ERROR]: {e}")
            score = 0.0

    # --- 4. THE POWER TIER FILTER ---
    event.ai_triage_score = score
    
    # Logic: High Math Score (Vector Similarity) translates to Tier 2
    if score > 22.0:
        event.status = 'HIGH_PRIORITY'
        event.intel_tier = 2  # AI-Verified Intelligence
    else:
        event.status = 'FLAGGED'
        event.intel_tier = 1  # Suspicious / Mismatch
    
    event.save()