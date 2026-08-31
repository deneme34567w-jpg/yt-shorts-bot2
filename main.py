# GitHub Secrets üzerinden gelen token
hf_token = os.getenv("HF_TOKEN", None)

print("\n" + "="*50)
print("[*] GITHUB ACTIONS: HUGGING FACE BULUT GPU MOTORU BAŞLATILDI")
print("="*50)

# gradio_client'ta parametre adı 'token'dır veya HF_TOKEN env varsa otomatik algılar
if hf_token:
    client = Client("Lightricks/LTX-Video", token=hf_token)
else:
    client = Client("Lightricks/LTX-Video")

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
