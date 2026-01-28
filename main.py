import streamlit as st
import pandas as pd
import time
from urllib.parse import urlparse

# SELENIUM
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="HumanBank v12",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS: GLOBAL OSINT UI ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }

    /* Yan Menü */
    section[data-testid="stSidebar"] { background-color: #0f1319; border-right: 1px solid #2d333b; }

    /* Metrik Kartları */
    div[data-testid="metric-container"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }
    label[data-testid="stMetricLabel"] { color: #8b949e; }
    div[data-testid="stMetricValue"] { color: #58a6ff; font-family: 'Courier New', monospace; }

    /* Tablo */
    .stDataFrame { border: 1px solid #30363d; border-radius: 5px; }

    /* Butonlar */
    .stButton>button {
        background: linear-gradient(90deg, #1f6feb, #238636);
        color: white; border: none; font-weight: bold; transition: 0.3s;
    }
    .stButton>button:hover { box-shadow: 0 0 15px rgba(31, 111, 235, 0.4); }

    /* Terminal Log */
    .log-box {
        font-family: 'Consolas', monospace; font-size: 12px; color: #8b949e;
        background-color: #0d1117; padding: 10px; border-radius: 5px;
        border-left: 3px solid #1f6feb; max-height: 200px; overflow-y: auto;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'found_data' not in st.session_state: st.session_state.found_data = []
if 'logs' not in st.session_state: st.session_state.logs = []


def add_log(msg):
    ts = time.strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{ts}] {msg}")


def add_data(platform, user, url, title):
    for d in st.session_state.found_data:
        if d['URL'] == url: return False
    st.session_state.found_data.append({
        "Platform": platform,
        "Kullanıcı": user,
        "URL": url,
        "Başlık": title,
        "Zaman": time.strftime("%H:%M")
    })
    return True


# --- MOTOR ---
class GlobalHarvester:
    def __init__(self):
        self.driver = None

    def start_driver(self):
        options = EdgeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        try:
            service = EdgeService(EdgeChromiumDriverManager().install())
        except:
            service = EdgeService()
        self.driver = webdriver.Edge(service=service, options=options)

    def close_driver(self):
        if self.driver: self.driver.quit()

    def scan(self, target, placeholders):
        self.start_driver()
        add_log(f"Global tarama başlatıldı: {target}")

        # --- GENİŞLETİLMİŞ PLATFORM LİSTESİ ---
        platforms = {
            "Instagram": f'site:instagram.com "{target}"',
            "Twitter (X)": f'site:twitter.com "{target}"',
            "Facebook": f'site:facebook.com "{target}"',
            "TikTok": f'site:tiktok.com "{target}"',
            "Reddit": f'site:reddit.com "{target}"',
            "LinkedIn": f'site:linkedin.com/in/ "{target}"',
            "YouTube": f'site:youtube.com "{target}"',
            "Pinterest": f'site:pinterest.com "{target}"',
            "Github": f'site:github.com "{target}"',
            "Telegram": f'site:t.me "{target}"',
            "Tumblr": f'site:tumblr.com "{target}"',
            "VK (Rusya)": f'site:vk.com "{target}"'
        }

        progress_bar = placeholders['status'].progress(0, text="Başlatılıyor...")
        total = len(platforms)
        step = 0

        for platform_name, query in platforms.items():
            progress_bar.progress((step / total), text=f"🌍 Taranıyor: {platform_name}...")
            add_log(f"--> {platform_name} sorgulanıyor...")

            try:
                self.driver.get("https://www.google.com")
                time.sleep(1)  # Hızlı geçiş

                try:
                    box = self.driver.find_element(By.NAME, "q")
                    box.clear()
                    box.send_keys(query)
                    box.send_keys(Keys.RETURN)
                except:
                    add_log(f"HATA: {platform_name} arama kutusu bulunamadı (Captcha?)")
                    continue

                time.sleep(2)  # Sonuç bekleme

                links = self.driver.find_elements(By.TAG_NAME, "a")
                found = 0

                for link in links:
                    try:
                        url = link.get_attribute("href")
                        # Filtre: Google linki değilse ve platform adını içeriyorsa
                        domain_match = platform_name.split()[0].lower()  # "Twitter (X)" -> "twitter"
                        if url and domain_match in url and "google.com" not in url:

                            user = self._extract_user(url, platform_name)
                            title = link.text if link.text else f"{platform_name} Sonucu"

                            if add_data(platform_name, user, url, title):
                                found += 1
                                self._update_ui(placeholders)
                    except:
                        continue

                if found > 0:
                    add_log(f"✅ {platform_name}: {found} veri bulundu.")
                else:
                    add_log(f"[-] {platform_name}: Temiz.")

            except Exception as e:
                add_log(f"Sistem Hatası: {e}")

            step += 1
            time.sleep(1)  # Platformlar arası kısa bekleme

        progress_bar.progress(1.0, text="Tarama Tamamlandı.")
        time.sleep(1)
        progress_bar.empty()
        placeholders['status'].success("Tüm ağlar tarandı.")
        self.close_driver()

    def _extract_user(self, url, platform):
        try:
            path = urlparse(url).path
            parts = path.strip("/").split("/")

            # Özel Platform Kuralları
            if "reddit" in platform.lower() and "user" in parts:
                return f"u/{parts[parts.index('user') + 1]}"
            if "youtube" in platform.lower() and path.startswith("/@"):
                return parts[0]
            if "facebook" in platform.lower() and "people" in parts:
                return "Profil"

            # Varsayılan
            clean = parts[0]
            if clean in ["p", "reel", "status", "video", "pin"]: return "İçerik/Post"
            return clean if clean else "Bilinmiyor"
        except:
            return "Bilinmiyor"

    def _update_ui(self, placeholders):
        df = pd.DataFrame(st.session_state.found_data)
        if not df.empty:
            placeholders['table'].dataframe(
                df.iloc[::-1],
                use_container_width=True,
                column_config={
                    "URL": st.column_config.LinkColumn("Link", display_text="🔗 Görüntüle"),
                    "Platform": st.column_config.TextColumn("Kaynak", width="medium"),
                }
            )

            # Metrik Güncelleme
            total = len(df)
            top_plat = df['Platform'].mode()[0] if not df.empty else "-"
            unique_users = df['Kullanıcı'].nunique()

            placeholders['m1'].metric("Toplam Sonuç", total)
            placeholders['m2'].metric("En Aktif Platform", top_plat)
            placeholders['m3'].metric("Benzersiz Profil", unique_users)


# --- ANA UI ---
def main():
    with st.sidebar:
        st.title("HumanBank v12")
        st.caption("Global Dragnet Edition")
        st.divider()

        target = st.text_input("Hedef (Kullanıcı Adı/Etiket)", placeholder="Örn: #cybersecurity veya mrrobot")

        c1, c2 = st.columns(2)
        start = c1.button("🌍 TARAMAYI BAŞLAT")
        clear = c2.button("🗑️ TEMİZLE")

        if clear:
            st.session_state.found_data = []
            st.session_state.logs = []
            st.rerun()

        st.markdown("---")
        st.markdown("**Kapsanan Ağlar:**")
        st.code("Facebook, Twitter, Insta, TikTok\nReddit, YouTube, Github, Pinterest\nTelegram, VK, Tumblr, Medium")

    # --- DASHBOARD ---

    # 1. Metrikler
    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
    m1 = c1.empty()
    m2 = c2.empty()
    m3 = c3.empty()
    status_msg = c4.empty()  # Progress bar buraya gelecek

    # Başlangıç Değerleri
    df_start = pd.DataFrame(st.session_state.found_data)
    m1.metric("Toplam Sonuç", len(df_start))
    m2.metric("En Aktif Platform", "-")
    m3.metric("Benzersiz Profil", 0)

    # 2. Ana Tablo
    st.subheader("📡 Küresel Dijital Ayak İzleri")
    table_ph = st.empty()

    if not df_start.empty:
        table_ph.dataframe(
            df_start.iloc[::-1],
            use_container_width=True,
            column_config={"URL": st.column_config.LinkColumn("Link", display_text="🔗 Görüntüle")}
        )
    else:
        table_ph.info("Veritabanı temiz. Küresel tarama için başlatın.")

    # 3. Log Paneli
    with st.expander("📟 Tarama Logları", expanded=True):
        log_ph = st.empty()
        if st.session_state.logs:
            log_text = "\n".join(st.session_state.logs)
            st.code(log_text)
        else:
            st.code("Sistem Hazır. Hedef bekleniyor...")

    # İŞLEM
    if start and target:
        placeholders = {"m1": m1, "m2": m2, "m3": m3, "table": table_ph, "status": status_msg}
        bot = GlobalHarvester()
        bot.scan(target, placeholders)


if __name__ == "__main__":
    main()