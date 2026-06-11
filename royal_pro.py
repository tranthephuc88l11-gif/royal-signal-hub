import streamlit as st
import google.generativeai as genai
import json
import os
import yt_dlp
from datetime import datetime, timedelta
from youtube_transcript_api import YouTubeTranscriptApi

# --- 1. CẤU HÌNH HỆ THỐNG LƯU TRỮ (FIX LỖI STREAMLIT CLOUD) ---
BASE_DATABASE = "production_database"
os.makedirs(BASE_DATABASE, exist_ok=True)

TOPIC_CONFIG = {
    "👑 ROYAL NEWS": {
        "folder": "royal_news",
        "channels": [
            "https://www.youtube.com/@crownwatchnews/videos",
            "https://www.youtube.com/@PalaceInsider1/videos",
            "https://www.youtube.com/@ThePrimeExpedition/videos",
            "https://www.youtube.com/@CrownMeltdown/videos",
            "https://www.youtube.com/@RoyalCheezee/videos",
            "https://www.youtube.com/@VintageExpose1/videos",
            "https://www.youtube.com/@PalaceUncovered2/videos"
        ]
    },
    "🚀 TECH NEWS": {
        "folder": "tech_news",
        "channels": ["https://www.youtube.com/@verge/videos"]
    }
}

# --- 2. QUẢN LÝ SESSION STATE (CHỐNG RESET DỮ LIỆU) ---
def init_session():
    keys = {
        'trending_list': [], 
        'selected_topic': "", 
        'selected_transcript': "",
        'outline': None, 
        'current_part': 0, 
        'full_script_list': [], 
        'seo_result': ""
    }
    for key, value in keys.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# --- 3. CÁC HÀM TIỆN ÍCH HỆ THỐNG ---
def get_topic_path(cat):
    path = os.path.join(BASE_DATABASE, TOPIC_CONFIG[cat]["folder"])
    os.makedirs(path, exist_ok=True)
    return path

def call_ai(prompt, key):
    """SỬ DỤNG DUY NHẤT GEMINI 3 FLASH PREVIEW"""
    if not key: return "MISSING API KEY"
    genai.configure(api_key=key)
    try:
        model = genai.GenerativeModel('gemini-3-flash-preview')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ LỖI GEMINI 3: {str(e)}"

def get_yt_trending(url):
    # Lọc 7 ngày gần nhất
    date_limit = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
    ydl_opts = {
        'quiet': True, 'extract_flat': False, 'playlistend': 30,
        'daterange': yt_dlp.utils.DateRange(start=date_limit), 'ignoreerrors': True
    }
    results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and 'entries' in info:
                for e in info['entries']:
                    if e and e.get('view_count', 0) >= 10000:
                        results.append({
                            'title': e['title'], 'id': e['id'], 
                            'views': e['view_count'], 'url': f"https://www.youtube.com/watch?v={e['id']}"
                        })
    except: pass
    return results

def get_ts_safe(v_id):
    try:
        ts_list = YouTubeTranscriptApi.list_transcripts(v_id)
        try: ts = ts_list.find_transcript(['en'])
        except: ts = ts_list.find_generated_transcript(['en'])
        return " ".join([t['text'] for t in ts.fetch()])
    except: return ""

# --- 4. GIAO DIỆN STREAMLIT ---
st.set_page_config(page_title="AI Production Hub Pro V24", page_icon="👑", layout="wide")

with st.sidebar:
    st.title("👑 PRODUCTION HUB")
    gemini_key = st.text_input("Gemini API Key:", type="password", key="api_key_input")
    
    st.divider()
    # THƯ MỤC MẸ
    main_cat = st.selectbox("📂 THƯ MỤC MẸ (CATEGORY):", list(TOPIC_CONFIG.keys()), key="cat_box")
    
    st.divider()
    # QUY TRÌNH CON
    st.write("**QUY TRÌNH LÀM VIỆC:**")
    menu = st.radio("Chọn bước:", 
                    ["1. TÌM TRENDING (SPY)", 
                     "2. VIẾT LẠI KỊCH BẢN", 
                     "3. SEO & THUMBNAIL HOÀNG GIA", 
                     "4. 📜 LỊCH SỬ KỊCH BẢN"], key="menu_radio")
    
    st.divider()
    if st.button("➕ RESET DỰ ÁN MỚI"):
        for k in ['selected_topic', 'selected_transcript', 'outline', 'current_part', 'full_script_list', 'seo_result', 'trending_list']:
            st.session_state[k] = "" if isinstance(st.session_state.get(k), str) else (None if k=='outline' else [])
        st.session_state.current_part = 0
        st.rerun()

# --- XỬ LÝ LOGIC ---

# --- MENU 1: TÌM TRENDING ---
if menu == "1. TÌM TRENDING (SPY)":
    st.header(f"🔍 {main_cat}: Viral Spy (7 Days / >10k views)")
    target_channel = st.selectbox("Chọn kênh đối thủ:", TOPIC_CONFIG[main_cat]["channels"])
    if st.button("BẮT ĐẦU QUÉT"):
        with st.spinner("Đang thâm nhập YouTube..."):
            st.session_state.trending_list = get_yt_trending(target_channel)
    
    if st.session_state.trending_list:
        st.success(f"Tìm thấy {len(st.session_state.trending_list)} video!")
        for v in st.session_state.trending_list:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"🔥 **{v['title']}** ({v['views']:,} views)")
                st.markdown(f"🔗 [Link Video]({v['url']})")
            with col2:
                if st.button("CHỌN", key=v['id']):
                    st.session_state.selected_topic = v['title']
                    st.session_state.selected_transcript = get_ts_safe(v['id'])
                    st.success("Đã nạp video! Chuyển qua Bước 2.")

# --- MENU 2: VIẾT LẠI KỊCH BẢN ---
elif menu == "2. VIẾT LẠI KỊCH BẢN":
    st.header(f"✍️ {main_cat}: Rewrite Master (5000 Words - Gemini 3)")
    
    # LUÔN HIỆN CÁC Ô NHẬP LIỆU
    st.session_state.selected_topic = st.text_input("Project Name:", value=st.session_state.selected_topic)
    st.session_state.selected_transcript = st.text_area("Original Transcript:", value=st.session_state.selected_transcript, height=200)

    st.divider()

    if st.session_state.outline is None:
        if st.button("BƯỚC 1: LÊN DÀN Ý & PHÂN BỔ SỐ TỪ"):
            if not gemini_key or not st.session_state.selected_transcript: 
                st.error("Thiếu Key hoặc Transcript!")
            else:
                prompt_o = f"""
                ACT AS A MASTER CONTENT CREATOR (Master of high-level retention).
                Task: Create a detailed OUTLINE to REWRITE this script into a 5000-word viral YouTube script.
                Category: {main_cat}
                
                STRICT RULES FOR OUTLINE:
                1. DIVIDE INTO EXACTLY SIX PARTS.
                2. ASSIGN A SPECIFIC WORD COUNT PER PART (Total must reach 5000 words).
                3. NUMERICAL RULE: NO DIGITS AT ALL. (Example: 'three' not 3).
                4. LANGUAGE: ENGLISH ONLY.
                
                Topic: {st.session_state.selected_topic}
                Transcript: {st.session_state.selected_transcript[:3500]}
                """
                with st.spinner("Gemini 3 đang phân bổ số từ..."):
                    res = call_ai(prompt_o, gemini_key)
                    if "❌" not in res:
                        st.session_state.outline = res
                        st.session_state.current_part = 1
                        st.rerun()
                    else: st.error(res)
    else:
        st.info(f"Dự án: {st.session_state.selected_topic} (Phần {st.session_state.current_part}/6)")
        with st.expander("📋 Xem Dàn Ý Chi Tiết", expanded=True): st.markdown(st.session_state.outline)
        
        if st.session_state.current_part <= 6:
            if st.button(f"VIẾT TIẾP PHẦN {st.session_state.current_part} (BÁM SÁT SỐ TỪ)"):
                prompt_w = f"""
                OUTLINE REFERENCE: {st.session_state.outline}. 
                TASK: Write PART {st.session_state.current_part} of the script in ENGLISH ONLY. 
                
                STRICT REQUIREMENTS:
                1. WORD COUNT: Refer to the outline above. Write deeply to reach the word count allocated for this part.
                2. NO DIGITS: ABSOLUTELY NO NUMBERS AS DIGITS. (Example: 'twenty-twenty-four' not 2024).
                3. STYLE: Dramatic, high-stakes storytelling, Royal expert tone.
                """
                with st.spinner(f"Gemini 3 đang viết phần {st.session_state.current_part}..."):
                    res_part = call_ai(prompt_w, gemini_key)
                    if "❌" not in res_part:
                        st.session_state.full_script_list.append(f"## PART {st.session_state.current_part}\n\n{res_part}")
                        if st.session_state.current_part == 6:
                            # Tự động lưu theo thư mục mẹ
                            path = get_topic_path(main_cat)
                            f_name = f"{path}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                            with open(f_name, 'w', encoding='utf-8') as f:
                                json.dump({"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "topic": st.session_state.selected_topic, "content": "\n\n".join(st.session_state.full_script_list)}, f, ensure_ascii=False, indent=4)
                        st.session_state.current_part += 1
                        st.rerun()
                    else: st.error(res_part)

        for p in st.session_state.full_script_list: st.markdown(p); st.divider()
        if st.session_state.current_part > 6:
            st.success("✅ Kịch bản 5000 chữ hoàn thành và đã lưu vào History!")
            st.download_button("Download Full Script", "\n\n".join(st.session_state.full_script_list), file_name=f"{st.session_state.selected_topic}.md")

# --- MENU 3: SEO ---
elif menu == "3. SEO & THUMBNAIL HOÀNG GIA":
    st.header("📊 SEO & Thumbnail Strategist")
    titles = st.text_area("Dán 10 tiêu đề đối thủ:")
    full_script_text = "\n\n".join(st.session_state.full_script_list)
    script_box = st.text_area("Kịch bản của bạn:", value=full_script_text, height=150)
    
    if st.button("🚀 TẠO SEO"):
        prompt_seo = f"""
        Analyze these 10 titles: {titles}
        TASK 1: CREATE 5 NEW TITLES.
        TASK 2: THUMBNAIL COMPOSITION (Visual brief).
        TASK 3: WRITE DESCRIPTION using THIS EXACT TEMPLATE:
        
        [Summary based on {script_box[:500]}]
        • [Keypoint 1]
        • [Keypoint 2]
        👉 Don’t miss our deep dives into royal truth and tradition
        Subscribe: https://www.youtube.com/@RoyalSignal-1
        and turn on the bell for more royal stories!
        
        📍 Disclaimer
        Independent commentary and analysis for discussion. We do not verify allegations. Context is examined under YouTube Fair Use.
        #KateMiddleton #QueenCamilla #RoyalNews #BreakingNews #PrincessOfWales #RoyalFamily #HouseOfWindsor #RoyalExpert #KingCharlesIII #BritishMonarchy
        
        ENGLISH ONLY.
        """
        st.session_state.seo_result = call_ai(prompt_seo, gemini_key)
    
    if st.session_state.seo_result:
        st.markdown(st.session_state.seo_result)

# --- MENU 4: LỊCH SỬ ---
elif menu == "4. 📜 LỊCH SỬ KỊCH BẢN":
    st.header(f"📜 {main_cat}: History")
    folder = get_topic_path(main_cat)
    files = [f for f in os.listdir(folder) if f.endswith('.json')]
    if not files:
        st.info("Chưa có kịch bản nào.")
    else:
        for fn in sorted(files, reverse=True):
            with open(os.path.join(folder, fn), 'r', encoding='utf-8') as file:
                data = json.load(file)
                with st.expander(f"📅 {data['date']} | 🎬 {data['topic']}"):
                    st.markdown(data['content'])
                    if st.button("Xóa vĩnh viễn bài này", key=fn):
                        os.remove(os.path.join(folder, fn))
                        st.rerun()
