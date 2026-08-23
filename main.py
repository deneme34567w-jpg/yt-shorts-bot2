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

if "YOUTUBE_TOKEN_JSON" in os.environ:
    with open("youtube_token.json", "w", encoding="utf-8") as f:
        f.write(os.environ["YOUTUBE_TOKEN_JSON"])

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
KLING_EMAIL = os.environ.get("KLING_EMAIL", "")
KLING_PASSWORD = os.environ.get("KLING_PASSWORD", "")

def foto_cek(page, isim):
    dosya_yolu = f"ekran_goruntuleri/{isim}"
    try:
        page.screenshot(path=dosya_yolu, timeout=8000)
        print(f" [FOTO] {isim} kaydedildi.")
    except Exception as e:
        print(f" [FOTO UYARI] {isim}: {e}")

# ================= 1. GEMINI PROMPT =================
def gemini_ile_kling_icerik_uret():
    print("\n[1/4] Gemini Kling AI için günlük ASMR promptu hazırlıyor...")
    bugun_tarih = datetime.now().strftime("%Y-%m-%d")
    
    sistem_talimati = f"""Sen Kling AI için sinematik ASMR video prompt uzmanısın.
Tarih: {bugun_tarih}.

GÖREV:
1. Dünya mutfaklarından viral olabilecek özgün minyatür bir yemek seç.
2. Kling AI'ın kamera hareketlerini, ışıklandırmasını ve doku fiziğini içeren 60-80 kelimelik İngilizce video promptu ve YouTube SEO başlığı yaz.

İmza Tarzı:
- "Ultra realistic 8k macro video of miniature cooking in a tiny kitchen on a warm wooden countertop..." ile başla.
- Ahşap tezgahta minyatür mutfak, tealight alevli taş ocak, bakır tava.
- Gerçek insan eli cam pipetle yağ damlatır.
- Minik kaşıkla yemek konur, cızırtı/buhar başlar. Malzemeler eklenir.
- Minik spatula ile çevrilir, mini seramik tabağa servis edilir.
- Makro lens, altın saat ışığı, ASMR sesleri, 8K fotogerçekçi.

ÇIKTI FORMATI (SADECE JSON):
{{
  "food_name": "Yemeğin İngilizce Adı",
  "prompt": "Ultra realistic 8k macro video of miniature cooking in a tiny kitchen...",
  "title": "Satisfying Tiny [Food Name] Cooking ASMR + Emoji + #Shorts",
  "description": "Miniature kitchen ASMR cooking experience: [Food Name]. 8K ultra realistic. #MiniatureCooking #ASMR #Shorts #Satisfying #KlingAI",
  "tags": ["miniature cooking", "mini food", "asmr cooking", "satisfying", "shorts", "kling ai"]
}}"""

    if GEMINI_KEY:
        try:
            client = genai.Client(api_key=GEMINI_KEY)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=sistem_talimati
            )
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            veri = json.loads(clean_json)
            print(f" Günün Menüsü: {veri.get('food_name', 'Minyatür Lezzet')}")
            print(f" YouTube Başlığı: {veri['title']}")
            return veri
        except Exception as e:
            print(f"Gemini API uyarısı ({e}), varsayılan şablon devrede...")

    return {
        "food_name": "Mini Souffle Pancake",
        "prompt": "Ultra realistic 8k macro video, 9:16 vertical shorts. Inside a cozy miniature kitchen, a stone stove glows with a tealight flame under a mini copper pan. Real human hand drops oil with glass pipette. Delicate fluffy pancake batter sizzles gently with realistic steam, flipped with mini spatula onto a ceramic dish with maple syrup. Macro lens, golden hour light, 8K photorealistic.",
        "title": "Satisfying Mini Souffle Pancake Cooking ASMR 🥞 #Shorts",
        "description": "Miniature kitchen ASMR cooking experience. 8K ultra realistic. #MiniatureCooking #ASMR #Shorts #Satisfying",
        "tags": ["miniature cooking", "mini food", "asmr cooking", "satisfying", "shorts"]
    }

# ================= 2. OTOMATİK GİRİŞ YAPICI =================
def otomatik_giris_yap(page):
    print(" Oturum kontrolü yapılıyor...")
    page.wait_for_timeout(3000)
    
    # Eğer giriş butonu varsa
    sign_in_btn = page.locator("button:has-text('Sign In'), button:has-text('Log In'), button:has-text('Giriş'), [class*='signin'], [class*='login']").first
    if sign_in_btn.is_visible(timeout=3000):
        print(" -> Oturum kapalı! E-posta ve şifre ile otomatik giriş yapılıyor...")
        sign_in_btn.click(force=True)
        page.wait_for_timeout(2000)

        # E-posta yaz
        email_box = page.locator("input[type='email'], input[placeholder*='email' i], input[name*='email' i]").first
        if email_box.is_visible(timeout=3000):
            email_box.fill(KLING_EMAIL)
            page.wait_for_timeout(500)

        # Şifre yaz
        pass_box = page.locator("input[type='password'], input[placeholder*='password' i], input[name*='password' i]").first
        if pass_box.is_visible(timeout=3000):
            pass_box.fill(KLING_PASSWORD)
            page.wait_for_timeout(500)

        # Giriş Yap butonuna bas
        submit_btn = page.locator("button[type='submit'], button:has-text('Log In'), button:has-text('Sign In')").last
        submit_btn.click(force=True)
        print(" -> Giriş bilgileri gönderildi!")
        page.wait_for_timeout(6000)

# ================= 3. KLING AI MOTORU =================
def kling_ile_video_uret(video_prompt):
    print("\n[2/4] Kling AI başlatılıyor (Otomatik Giriş & 66 Kredi Modu)...")
    yakalanan_video_bytes = []
    dosya_yolu = os.path.abspath("shorts_video.mp4")

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
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Ağ üzerinden MP4 yakalama
        def network_video_yakala(response):
            try:
                content_type = response.headers.get("content-type", "")
                url = response.url.lower()
                if ("video" in content_type or ".mp4" in url or "kling" in url) and response.status == 200:
                    data = response.body()
                    if len(data) > 300000:
                        yakalanan_video_bytes.append(data)
                        print(f" [AĞ] Video yakalandı! Boyut: {len(data)/(1024*1024):.2f} MB")
            except:
                pass

        page.on("response", network_video_yakala)
        
        print(" Kling AI açılıyor...")
        page.goto("https://klingai.com/text-to-video/new", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)

        # 1. Otomatik Giriş Kontrolü
        otomatik_giris_yap(page)

        foto_cek(page, "01_kling_acildi.png")

        # Pop-up'ları kapat
        for btn_text in ["Confirm", "Accept", "Close", "Got it", "Dismiss", "OK", "Anladım"]:
            try:
                page.locator(f"button:has-text('{btn_text}'), [aria-label*='close']").first.click(timeout=1000)
            except:
                pass

        # 2. 9:16 Formatını Seç
        try:
            oran_9_16 = page.locator("div:has-text('9:16'), button:has-text('9:16'), [data-value='9:16']").first
            if oran_9_16.is_visible(timeout=2000):
                oran_9_16.click(force=True)
                page.wait_for_timeout(400)
                print(" -> 9:16 Dikey Format seçildi.")
        except Exception as e:
            print(f"Format seçimi uyarısı: {e}")

        # 3. Promptu Yaz
        print("[3/4] Prompt giriliyor...")
        prompt_box = page.locator("textarea, div[contenteditable='true'], [placeholder*='describe' i], [placeholder*='Prompt' i]").first
        prompt_box.click(force=True)
        page.wait_for_timeout(300)
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        page.wait_for_timeout(200)
        page.keyboard.insert_text(video_prompt)
        page.wait_for_timeout(1000)
        foto_cek(page, "02_prompt_yazildi.png")

        # 4. Generate Butonuna Tıkla
        print(" Generate butonuna basılıyor...")
        generate_btn = page.locator("button:has-text('Generate'), button:has-text('Oluştur'), button[class*='generate']").last
        generate_btn.click(force=True)
        page.wait_for_timeout(4000)
        foto_cek(page, "03_uretim_basladi.png")

        # 5. Render ve İndirme Döngüsü (Maksimum 6 dakika)
        print(" Kling AI video render ediliyor (bekleniyor)...")
        baslangic = time.time()
        video_indirildi = False

        while time.time() - baslangic < 360:
            if len(yakalanan_video_bytes) > 0:
                with open(dosya_yolu, "wb") as f:
                    f.write(yakalanan_video_bytes[-1])
                print(" Video ağ akışından başarıyla kaydedildi!")
                video_indirildi = True
                break

            try:
                download_btn = page.locator("button[aria-label*='Download'], button:has-text('Download'), a[download], [data-testid*='download']").first
                if download_btn.is_visible(timeout=1000):
                    with page.expect_download(timeout=15000) as download_info:
                        download_btn.click(force=True)
                    download = download_info.value
                    download.save_as(dosya_yolu)
                    video_indirildi = True
                    print(" Video indirme butonundan başarıyla kaydedildi!")
                    break
            except:
                pass

            time.sleep(10)
            gecen = int(time.time() - baslangic)
            if gecen % 30 == 0:
                print(f" Video işleniyor... ({gecen}. saniye)")

        foto_cek(page, "04_son_durum.png")

        if not video_indirildi:
            raise Exception("Kling AI videosu üretildi ancak indirilemedi.")

        browser.close()
        print(f" 10s Video Başarıyla Hazırlandı: {dosya_yolu}")
        return dosya_yolu

# ================= 4. YOUTUBE OTOMATİK YÜKLEME =================
def youtube_yukle(dosya_yolu, meta_veri):
    print("\n[4/4] YouTube Shorts yüklemesi başlatılıyor...")
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
        icerik_paketi = gemini_ile_kling_icerik_uret()
        video_dosyasi = kling_ile_video_uret(icerik_paketi["prompt"])
        youtube_yukle(video_dosyasi, icerik_paketi)
    except Exception as e:
        print(f"\n HATA OLUŞTU: {str(e)}")
        raise e
