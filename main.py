import os
import shutil
from gradio_client import Client

OUTPUT_DIR = "downloads"
FINAL_VIDEO_NAME = "mini_cooking_asmr.mp4"

PROMPT = (
    "Macro cinematic shot, cozy warm morning kitchen lighting. "
    "A tiny copper skillet sits on a stone stove heated by a small tealight candle flame on a wooden table. "
    "A glass dropper drops cooking oil into the pan, then a tiny spoon pours thick green-onion pancake batter into the sizzling pan. "
    "Steam rising, hyper-realistic physics, 8k, ASMR aesthetic, vertical framing."
)

def generate_video_huggingface():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # GitHub Secret'tan gelen HF_TOKEN'ı oku
    hf_token = os.getenv("HF_TOKEN", None)
    
    print("\n" + "="*50)
    print("[*] GITHUB ACTIONS: HUGGING FACE BULUT GPU MOTORU BAŞLATILDI")
    print("="*50)
    
    # LTX-Video modeline bağlanıyoruz
    client = Client("Lightricks/LTX-Video", hf_token=hf_token)
    
    print(f"\n[*] Prompt: {PROMPT[:70]}...")
    print("[*] Video bulut GPU'sunda render ediliyor, lütfen bekleyin...")

    try:
        result = client.predict(
            prompt=PROMPT,
            negative_prompt="blurry, low quality, distorted, deformed, watermark, text",
            width=576,
            height=1024,
            num_frames=121,
            guidance_scale=3.0,
            api_name="/generate_video"
        )

        print(f"\n[✓] Render tamamlandı! Dosya konumu: {result}")

        destination = os.path.join(OUTPUT_DIR, FINAL_VIDEO_NAME)
        video_path = result[0] if isinstance(result, (tuple, list)) else result

        shutil.copy(video_path, destination)
        print(f"\n[✓] VİDEO OLUŞTURULDU: {destination}")

    except Exception as e:
        print(f"\n[!] Hata oluştu: {e}")
        raise e

if __name__ == "__main__":
    generate_video_huggingface()
