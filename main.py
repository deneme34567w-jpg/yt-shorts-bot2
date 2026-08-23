import os
import time
import json
import base64
import requests
from datetime import datetime
from PIL import Image
from playwright.sync_api import sync_playwright
from google import genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

os.makedirs("ekran_goruntuleri", exist_ok=True)

if "FLOW_STATE_BASE64" in os.environ:
    with open("flow_state.json", "wb") as f:
        f.write(base64.b64decode(os.environ["FLOW_STATE_BASE64"]))

if "YOUTUBE_TOKEN_JSON" in os.environ:
    with open("youtube_token.json", "w", encoding="utf-8") as f:
        f.write(os.environ["YOUTUBE_TOKEN_JSON"])

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_KEY:
    raise Exception("GEMINI_API_KEY bulunamadı!")

client = genai.Client(api_key=GEMINI_KEY)

# ================= 1. GEMINI 3.6 FLASH: PROMPT VE SEO ÜRETİCİ =================
def icerik_uret():
    print("\n[1/3] Gemini 3.6 Flash günün menüsünü ve promptunu hazırlıyor...")
    sistem_talimati = """Sen dünyanın en iyi ASMR minyatür mutfak video yönetmenisin.
Bugün için dünya mutfaklarından özgün, viral olabilecek 10 saniyelik 9:16 dikey bir yemek videosu promptu ve YouTube SEO verisi yaz.

İmza Tarzı:
- Sıcak ahşap tezgahta minyatür mutfak, tealight alevli taş ocak ve bakır tava.
- Gerçek insan eli cam pipetle yağ damlatır.
- Minik kaşıkla yemek konur, cızırtı/buhar başlar. Malzemeler eklenir.
- Minik spatula ile çevrilir, mini seramik tabağa servis edilir.
- Makro lens, altın saat ışığı, ASMR sesleri, 8K fotogerçekçi.

ÇIKTI FORMATI (SADECE JSON):
{
  "food_name": "Yemeğin Adı",
  "prompt": "In a 9:16 vertical miniature kitchen on a warm wooden countertop...",
  "title": "Satisfying Tiny [Food Name] Cooking ASMR + Emoji + #Shorts",
  "description": "Miniature kitchen ASMR cooking experience. 8K ultra realistic. #MiniatureCooking #ASMR #Shorts #Satisfying",
  "tags": ["miniature cooking", "mini food", "asmr cooking", "satisfying", "shorts"]
}"""

    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=sistem_talimati
    )
    clean_json = response.text.replace("```json", "").replace("```", "").strip()
    veri = json.loads(clean_json)
    print(f" Menü: {veri.get('food_name')}")
    print(f" Başlık: {veri.get('title')}")
    return veri

# ================= 2. GEMINI 3.6 FLASH GÖRSEL AJAN KARAR MOTORU =================
def gemini_karar_ver(ekran_yolu, video_prompt, adim_sayisi):
    print(f" -> [AJAN GÖZÜ] Gemini 3.6 Flash ekrana bakıyor (Adım {adim_sayisi})...")
    img = Image.open(ekran_yolu)
    
    ajan_talimati = f"""Sen tarayıcıyı yöneten otonom bir AI Ajanısın (Autonomous GUI Agent).
Şu anki ekran görüntüsünü dikkatle incele. 1920x1080 çözünürlükte çalışıyoruz.

HEDEFİMİZ:
1. Eğer ekranda giriş/hesap seçme penceresi varsa hesaba tıkla veya giriş yap.
2. Eğer ana sayfadaysan son projeyi veya yeni projeyi aç.
3. Proje içindeysen Video, 9:16, Omni Flash ve 10s ayarlarını yap.
4. Prompt kutusunu bul ve şu metni yaz: "{video_prompt}"
5. Beyaz gönderme okuna tıkla ve videonun üretilmesini bekle.
6. Video üretildiğinde (oynatıcı veya indirme butonu belirdiğinde) indir ve işlemi tamamla.

BANA SADECE AŞAĞIDAKİ JSON FORMATINDA CEVAP VER:
{{
  "durum_analizi": "Ekranda ne gördüğünün 1 cümlelik özeti",
  "eylem": "click" | "type" | "press" | "wait" | "done",
  "x": 0-1920 arası X koordinatı,
  "y": 0-1080 arası Y koordinatı,
  "yazilacak_metin": "Eğer eylem type ise yazılacak metin",
  "basilacak_tus": "Enter" | "Control+Enter" | "Escape",
  "bekleme_saniyesi": 3
}}"""

    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=[ajan_talimati, img]
    )
    clean_json = response.text.replace("```json", "").replace("```", "").strip()
    karar = json.loads(clean_json)
    print(f"    Görsel Analiz: {karar.get('durum_analizi')}")
    print(f"    Alınan Karar: {karar.get('eylem')} (X: {karar.get('x')}, Y: {karar.get('y')})")
    return karar

# ================= 3. OTONOM VİDEO ÜRETİM DÖNGÜSÜ =================
def otonom_video_uret(video_prompt):
    print("\n[2/3] Otonom Vision Agent döngüsü başlatılıyor...")
    dosya_yolu = os.path.abspath("shorts_video.mp4")
    yakalanan_video_bytes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1920,1080",
                "--ignore-certificate-errors"
            ]
        )
        
        context = browser.new_context(
            storage_state="flow_state.json" if os.path.exists("flow_state.json") else None,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Ağ dinleyicisi
        def network_video_yakala(response):
            try:
                content_type = response.headers.get("content-type", "")
                url = response.url.lower()
                if ("video" in content_type or ".mp4" in url or "googlevideo" in url or "videoplayback" in url) and response.status == 200:
                    data = response.body()
                    if len(data) > 300000:
                        yakalanan_video_bytes.append(data)
                        print(f" [AĞ] MP4 video akışı yakalandı! ({len(data)/(1024*1024):.2f} MB)")
            except:
                pass

        page.on("response", network_video_yakala)

        print(" Google Flow'a bağlanılıyor...")
        page.goto("https://labs.google/flow", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(5000)

        # OTONOM GÖRSEL KARAR DÖNGÜSÜ (Maksimum 20 Adım)
        video_tamamlandi = False
        for adim in range(1, 21):
            ekran_foto = f"ekran_goruntuleri/adim_{adim:02d}.png"
            page.screenshot(path=ekran_foto, timeout=8000)
            
            # Ağdan video zaten yakalandıysa bitir
            if len(yakalanan_video_bytes) > 0:
                with open(dosya_yolu, "wb") as f:
                    f.write(yakalanan_video_bytes[-1])
                video_tamamlandi = True
                print(" Video ağ akışından başarıyla kaydedildi!")
                break

            # Gemini 3.6 Flash'a ekranı göster ve karar aldır
            try:
                karar = gemini_karar_ver(ekran_foto, video_prompt, adim)
            except Exception as e:
                print(f"Gemini analiz hatası: {e}")
                time.sleep(4)
                continue

            eylem = karar.get("eylem")
            x = karar.get("x", 960)
            y = karar.get("y", 540)

            # Gemini'nin kararını uygula
            if eylem == "click":
                page.mouse.click(x, y)
                page.wait_for_timeout(karar.get("bekleme_saniyesi", 2) * 1000)
            
            elif eylem == "type":
                page.mouse.click(x, y)
                page.wait_for_timeout(300)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                metin = karar.get("yazilacak_metin", video_prompt)
                page.keyboard.insert_text(metin)
                page.wait_for_timeout(karar.get("bekleme_saniyesi", 2) * 1000)

            elif eylem == "press":
                tus = karar.get("basilacak_tus", "Enter")
                page.keyboard.press(tus)
                page.wait_for_timeout(karar.get("bekleme_saniyesi", 2) * 1000)

            elif eylem == "wait":
                bekle = karar.get("bekleme_saniyesi", 10)
                print(f" -> Gemini beklemeyi tercih etti ({bekle} saniye)...")
                time.sleep(bekle)

            elif eylem == "done":
                print(" -> Gemini görevin bittiğini bildirdi!")
                video_tamamlandi = True
                break

        page.screenshot(path="ekran_goruntuleri/son_durum.png", timeout=8000)

        if not video_tamamlandi and len(yakalanan_video_bytes) > 0:
            with open(dosya_yolu, "wb") as f:
                f.write(yakalanan_video_bytes[-1])
            video_tamamlandi = True

        if not video_tamamlandi:
            raise Exception("Otonom ajan videoyu tamamlayamadı.")

        browser.close()
        print(f" 10s Video Hazır: {dosya_yolu}")
        return dosya_yolu

# ================= 4. YOUTUBE OTOMATİK YÜKLEME =================
def youtube_yukle(dosya_yolu, meta_veri):
    print("\n[3/3] YouTube Shorts yüklemesi başlatılıyor...")
    if not os.path.exists("youtube_token.json"):
        raise Exception("youtube_token.json bulunamadı!")

    creds = Credentials.from_authorized_user_file("youtube_token.json")
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": meta_veri["title"],
            "description": meta_veri["description"],
            "tags": meta_veri["tags"],
            "categoryId": "26"  # Howto & Style
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(dosya_yolu, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f" Yükleme İlerlemesi: %{int(status.progress() * 100)}")

    video_id = response.get("id")
    print(f"\n BAŞARILI! YouTube Shorts yayında: https://youtube.com/shorts/{video_id}")

# ================= ANA ÇALIŞTIRICI =================
if __name__ == "__main__":
    try:
        icerik_paketi = icerik_uret()
        video_dosyasi = otonom_video_uret(icerik_paketi["prompt"])
        youtube_yukle(video_dosyasi, icerik_paketi)
    except Exception as e:
        print(f"\n HATA OLUŞTU: {str(e)}")
        raise e
