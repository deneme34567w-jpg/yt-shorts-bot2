import os
import time
import json
import base64
import random
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

if not GEMINI_KEY:
    raise Exception("GEMINI_API_KEY bulunamadı!")

client = genai.Client(api_key=GEMINI_KEY)

def foto_cek(page, isim):
    dosya_yolu = f"ekran_goruntuleri/{isim}"
    try:
        page.screenshot(path=dosya_yolu, timeout=8000)
        print(f" [FOTO] {isim} kaydedildi.")
    except Exception as e:
        print(f" [FOTO UYARI] {isim}: {e}")

# ================= 503 YOĞUNLUK KORUMALI GEMINI İSTEMCİSİ =================
def gemini_guvenli_cagri(contents, deneme_sayisi=3):
    modeller = ['gemini-2.5-flash', 'gemini-1.5-flash']
    
    for mod in modeller:
        for attempt in range(deneme_sayisi):
            try:
                response = client.models.generate_content(
                    model=mod,
                    contents=contents
                )
                return response.text
            except Exception as e:
                hata = str(e)
                if "503" in hata or "UNAVAILABLE" in hata or "429" in hata:
                    print(f" [Gemini {mod} Yoğunluk 503] {attempt+1}. deneme, 3 sn bekleniyor...")
                    time.sleep(3 * (attempt + 1))
                else:
                    print(f" [Gemini Model Uyarısı ({mod})]: {e}")
                    break
    return None

# ================= 1. PROMPT VE METADATA ÜRETİCİ =================
def icerik_uret():
    print("\n[1/3] Gemini günün menüsünü ve sinematik promptunu hazırlıyor...")
    bugun_tarih = datetime.now().strftime("%Y-%m-%d")
    sistem_talimati = f"""Sen Kling AI için sinematik ASMR minyatür mutfak video yönetmenisin.
Tarih: {bugun_tarih}.

GÖREV:
1. Dünya mutfaklarından özgün, viral olabilecek 10 saniyelik 9:16 dikey bir yemek videosu promptu ve YouTube SEO verisi yaz.

İmza Tarzı:
- "Ultra realistic 8k macro video of miniature cooking in a tiny kitchen on a warm wooden countertop..." ile başla.
- Ahşap tezgahta minyatür mutfak, tealight alevli taş ocak ve bakır tava.
- Gerçek insan eli cam pipetle yağ damlatır.
- Minik kaşıkla yemek konur, cızırtı/buhar başlar. Malzemeler eklenir.
- Minik spatula ile çevrilir, mini seramik tabağa servis edilir.
- Makro lens, altın saat ışığı, ASMR sesleri, 8K fotogerçekçi, ultra realistic lighting.

ÇIKTI FORMATI (SADECE JSON):
{{
  "food_name": "Yemeğin Adı",
  "prompt": "Ultra realistic 8k macro video of miniature cooking in a tiny kitchen on a warm wooden countertop...",
  "title": "Satisfying Tiny [Food Name] Cooking ASMR + Emoji + #Shorts",
  "description": "Miniature kitchen ASMR cooking experience: [Food Name]. 8K ultra realistic. #MiniatureCooking #ASMR #Shorts #Satisfying #KlingAI",
  "tags": ["miniature cooking", "mini food", "asmr cooking", "satisfying", "shorts", "kling ai"]
}}"""

    raw_text = gemini_guvenli_cagri(sistem_talimati)
    if raw_text:
        try:
            clean_json = raw_text.replace("```json", "").replace("```", "").strip()
            veri = json.loads(clean_json)
            print(f" Menü: {veri.get('food_name')}")
            print(f" Başlık: {veri['title']}")
            return veri
        except:
            pass

    # Eğer 503 devam ederse yedek listeden rastgele seç
    yedekler = [
        ("Miniature Wagyu Smash Burger", "Ultra realistic 8k macro video of miniature cooking in a tiny kitchen on a warm wooden countertop. A real human hand drops oil with a glass pipette onto a sizzling copper pan. A tiny spatula presses a miniature gourmet wagyu beef patty, melting cheddar cheese, served on a tiny toasted brioche bun. Golden hour lighting, crisp ASMR sounds, 8K ultra-realistic."),
        ("Miniature Japanese Souffle Pancake", "Ultra realistic 8k macro video of miniature cooking in a tiny kitchen on a warm wooden countertop. Real human hand drops butter with pipette. Fluffy Japanese pancake batter sizzles in copper pan, flipped with tiny spatula onto a ceramic dish with maple syrup. Macro lens, golden hour light, 8K photorealistic."),
        ("Miniature Crispy Churros", "Ultra realistic 8k macro video of miniature cooking in a tiny kitchen on a warm wooden countertop. Real hand drops oil into mini pan. Tiny churro dough fries to golden crisp perfection, dusted with cinnamon sugar, served with warm chocolate dip. Macro lens, ASMR sizzling, 8K ultra-realistic.")
    ]
    secilen = random.choice(yedekler)
    print(f" [Yedek Menü Devrede]: {secilen[0]}")
    return {
        "food_name": secilen[0],
        "prompt": secilen[1],
        "title": f"Satisfying Tiny {secilen[0]} Cooking ASMR 🥞✨ #Shorts",
        "description": f"Miniature kitchen ASMR cooking experience: {secilen[0]}. 8K ultra realistic. #MiniatureCooking #ASMR #Shorts #Satisfying",
        "tags": ["miniature cooking", "mini food", "asmr cooking", "satisfying", "shorts"]
    }

# ================= 2. GERİ BESLEMELİ GEMINI VİSİON AJANI =================
def gemini_otonom_karar_al(ekran_yolu, video_prompt, adim_no, onceki_karar, onceki_sonuc):
    print(f"\n -> [GEMINI GÖZÜ] Ekran inceleniyor (Adım {adim_no})...")
    img = Image.open(ekran_yolu)
    
    ajan_talimati = f"""Sen tarayıcıyı yöneten otonom ve kendini düzelten bir AI Ajanısın (Self-Correcting GUI Agent).
Şu anda ekrandaki görüntüye bakıyorsun (Çözünürlük: 1920x1080).

HEDEF SIRASI:
1. Eğer ekranda 'Sign In' / 'Log In' / '登录' / '立即体验' butonu varsa tıkla.
2. Açılan formda e-posta kutusuna '{KLING_EMAIL}' ve şifre kutusuna '{KLING_PASSWORD}' yazıp giriş yap.
3. 'AI Video' / 'Text to Video' bölümüne git.
4. '9:16' dikey formatını seç.
5. Prompt kutusuna şu metni yaz: "{video_prompt}"
6. 'Generate' (Oluştur) butonuna bas (Günlük 66 ücretsiz krediyi kullanır).
7. Video üretimi bittiğinde (kart veya indirme butonu belirdiğinde) indir ve 'done' eylemini ver.

GERİ BİLDİRİM:
- Bir önceki adımda yaptığın eylem: {json.dumps(onceki_karar)}
- Görev: Ekrana bakarak önceki eyleminin BAŞARILI olup olmadığını doğrula. Iskaladıysan koordinatı düzelt.

BANA SADECE AŞAĞIDAKİ JSON FORMATINDA CEVAP VER:
{{
  "ekran_durumu": "Şu an ekranda gördüğün durumun analizi",
  "onceki_adim_degerlendirmesi": "Önceki adım başarılı oldu mu? Sapma var mı?",
  "eylem": "click" | "type" | "press" | "wait" | "done",
  "x": 0-1920 arası tam X pikseli,
  "y": 0-1080 arası tam Y pikseli,
  "yazilacak_metin": "Eğer type ise yazılacak metin",
  "basilacak_tus": "Enter" | "Control+Enter" | "Escape",
  "bekleme_saniyesi": 2
}}"""

    raw_json = gemini_guvenli_cagri([ajan_talimati, img])
    if raw_json:
        try:
            clean_json = raw_json.replace("```json", "").replace("```", "").strip()
            karar = json.loads(clean_json)
            print(f"    Görsel Analiz: {karar.get('ekran_durumu')}")
            print(f"    Karar: {karar.get('eylem')} -> Hedef (X: {karar.get('x')}, Y: {karar.get('y')})")
            return karar
        except:
            pass

    return {"eylem": "wait", "bekleme_saniyesi": 3}

# ================= 3. OTONOM VİDEO ÜRETİM DÖNGÜSÜ =================
def otonom_kling_video_uret(video_prompt):
    print("\n[2/3] Kling AI Otonom Vision Agent döngüsü başlatılıyor...")
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
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        def network_video_yakala(response):
            try:
                content_type = response.headers.get("content-type", "")
                url = response.url.lower()
                if ("video" in content_type or ".mp4" in url or "kling" in url) and response.status == 200:
                    data = response.body()
                    if len(data) > 300000:
                        yakalanan_video_bytes.append(data)
                        print(f" [AĞ] Kling MP4 video akışı yakalandı! ({len(data)/(1024*1024):.2f} MB)")
            except:
                pass

        page.on("response", network_video_yakala)

        print(" Kling AI açılıyor...")
        page.goto("https://klingai.com", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(5000)

        video_tamamlandi = False
        onceki_karar = {}
        onceki_sonuc = ""

        for adim in range(1, 25):
            ekran_foto = f"ekran_goruntuleri/adim_{adim:02d}.png"
            page.screenshot(path=ekran_foto, timeout=8000)

            if len(yakalanan_video_bytes) > 0:
                with open(dosya_yolu, "wb") as f:
                    f.write(yakalanan_video_bytes[-1])
                video_tamamlandi = True
                print(" Video ağ akışından başarıyla yakalandı ve kaydedildi!")
                break

            try:
                karar = gemini_otonom_karar_al(ekran_foto, video_prompt, adim, onceki_karar, onceki_sonuc)
            except Exception as e:
                print(f"Gemini analiz uyarısı: {e}")
                time.sleep(3)
                continue

            eylem = karar.get("eylem")
            x = karar.get("x", 960)
            y = karar.get("y", 540)

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
                print(f" -> Gemini bekliyor ({bekle} sn)...")
                time.sleep(bekle)

            elif eylem == "done":
                print(" -> Gemini videonun indirildiğini bildirdi!")
                video_tamamlandi = True
                break

            onceki_karar = karar
            onceki_sonuc = f"{eylem} uygulandı."

        foto_cek(page, "son_durum.png")

        if not video_tamamlandi and len(yakalanan_video_bytes) > 0:
            with open(dosya_yolu, "wb") as f:
                f.write(yakalanan_video_bytes[-1])
            video_tamamlandi = True

        if not video_tamamlandi:
            raise Exception("Kling AI süreci tamamlanamadı.")

        browser.close()
        print(f" 10s Video Başarıyla Hazırlandı: {dosya_yolu}")
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
            "categoryId": "26"
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
        video_dosyasi = otonom_kling_video_uret(icerik_paketi["prompt"])
        youtube_yukle(video_dosyasi, icerik_paketi)
    except Exception as e:
        print(f"\n HATA OLUŞTU: {str(e)}")
        raise e
