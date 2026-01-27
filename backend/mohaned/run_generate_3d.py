import os
import sys
from vertex_utils import generate_3d
import requests
from dotenv import load_dotenv

load_dotenv()

def main():
    img1_path = "output/final_phase2_standard.png"
    img2_path = "output/final_phase2_tilted.png"
    output_glb = "output/factory_model_v2.glb"

    if not os.path.exists(img1_path) or not os.path.exists(img2_path):
        print(f"Error: Required images not found. Ensure {img1_path} and {img2_path} exist.")
        sys.exit(1)

    print(f"🚀 Generating 3D model from {img1_path} and {img2_path}...")
    
    try:
        with open(img1_path, "rb") as f1, open(img2_path, "rb") as f2:
            # Pass file handles to replicate via generate_3d
            result = generate_3d(images=[f1, f2])
            
        model_url = result.get("model_file") if isinstance(result, dict) else None
        
        if not model_url:
            print("⚠️ No model_file found in 3D generation output.")
            print("Full result:", result)
            return

        print(f"📥 Downloading 3D model from {model_url}...")
        r = requests.get(model_url, timeout=60)
        r.raise_for_status()
        
        with open(output_glb, "wb") as f:
            f.write(r.content)
            
        print(f"✅ Success! Saved 3D model to {output_glb}")
        
    except Exception as e:
        print(f"❌ 3D generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
