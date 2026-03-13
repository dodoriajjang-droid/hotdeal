import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import requests
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 🚨 텔레그램 설정 (스트림릿 Secrets 사용 권장!)
try:
    TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except Exception:
    TELEGRAM_TOKEN = None
    TELEGRAM_CHAT_ID = None
# ==========================================

if 'sent_deals' not in st.session_state:
    st.session_state.sent_deals = set()

def get_kst_today():
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')

# 🕒 제각각인 시간 텍스트를 파이썬 진짜 시간(datetime)으로 변환하는 마법의 함수
def parse_time_for_sort(time_str):
    now = datetime.now(pytz.timezone('Asia/Seoul'))
    try:
        if "방금" in time_str:
            return now
        elif "분 전" in time_str:
            minutes = int(re.search(r'\d+', time_str).group())
            return now - timedelta(minutes=minutes)
        elif "시간 전" in time_str:
            hours = int(re.search(r'\d+', time_str).group())
            return now - timedelta(hours=hours)
        else:
            # 14:20:11 또는 14:20 형태 처리
            parts = time_str.split(':')
            if len(parts) == 3:
                return now.replace(hour=int(parts[0]), minute=int(parts[1]), second=int(parts[2]), microsecond=0)
            elif len(parts) == 2:
                return now.replace(hour=int(parts[0]), minute=int(parts[1]), second=0, microsecond=0)
    except:
        pass
    # 파싱 실패 시 가장 과거의 시간으로 밀어버림
    return datetime.min.replace(tzinfo=pytz.timezone('Asia/Seoul'))

def send_telegram_message(title, link, site):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
        
    text = f"🔥 *[{site}] 신규 핫딜!*\n[{title}]({link})"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': False
    }
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def fetch_deals():
    results = []
    status = {'뽐뿌': '🔴 대기', '퀘이사존': '🔴 대기', '아카라이브': '🔒 차단됨', '에펨코리아': '🔒 차단됨'}
    
    scraper = cloudscraper.create_scraper()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # --- [1] 뽐뿌 장터 크롤링 ---
    try:
        pp_url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=pmarket"
        res = scraper.get(pp_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            html = res.content.decode('euc-kr', 'replace')
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.find_all('tr')
            count = 0
            
            for row in rows:
                a_tags = row.find_all('a')
                title, link, time_str = None, None, None
                
                for a in a_tags:
                    href = a.get('href', '')
                    if 'id=pmarket' in href and 'no=' in href:
                        link = "https://www.ppomppu.co.kr/zboard/" + href
                        temp_title = a.text.strip()
                        if temp_title: 
                            title = temp_title
                            break
                
                if title and link:
                    match = re.search(r'\b(\d{2}:\d{2}(?::\d{2})?)\b', row.text)
                    if match:
                        time_str = match.group(1)
                        results.append({'site': '뽐뿌', 'title': title, 'link': link, 'time': time_str})
                        count += 1
                        
            status['뽐뿌'] = f"🟢 성공 ({count}개)" if count > 0 else "🟡 당일 글 없음"
        else:
            status['뽐뿌'] = f"🔴 접속 차단 ({res.status_code})"
    except Exception as e:
        status['뽐뿌'] = f"🔴 에러"

    # --- [2] 퀘이사존 크롤링 ---
    try:
        qs_url = "https://quasarzone.com/bbs/qb_saleinfo"
        res = scraper.get(qs_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.select('a.subject-link')
            count = 0
            
            for a_tag in links:
                title_tag = a_tag.select_one('.tit')
                title = title_tag.text.strip() if title_tag else a_tag.text.strip()
                link = "https://quasarzone.com" + a_tag['href']
                
                parent = a_tag.find_parent(['div', 'tr', 'li'])
                if parent:
                    time_tag = parent.select_one('span.date')
                    if time_tag:
                        time_str = time_tag.text.strip()
                        if ":" in time_str or "전" in time_str:
                            results.append({'site': '퀘이사존', 'title': title, 'link': link, 'time': time_str})
                            count += 1
                                
            status['퀘이사존'] = f"🟢 성공 ({count}개)" if count > 0 else "🟡 파싱 실패"
        else:
            status['퀘이사존'] = f"🔴 접속 차단 ({res.status_code})"
    except Exception as e:
        status['퀘이사존'] = f"🔴 에러"

    # ✨ 핵심: 모든 데이터를 모은 뒤, 시간 최신순으로 정렬합니다.
    results.sort(key=lambda x: parse_time_for_sort(x['time']), reverse=True)

    # 정렬된 순서대로 텔레그램 전송 (최신 글부터 알림이 가도록)
    for item in results:
         if item['link'] not in st.session_state.sent_deals:
             send_telegram_message(item['title'], item['link'], item['site'])
             st.session_state.sent_deals.add(item['link'])

    return results, status

# --- Streamlit UI ---
st.set_page_config(page_title="실시간 핫딜 모니터링", layout="wide")

refresh_count = st_autorefresh(interval=300000, limit=None, key="deal_autorefresh")

st.title("🔥 통합 실시간 핫딜 모니터링")

kst_now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"최근 갱신 시간: {kst_now} (KST) | 자동 새로고침 횟수: {refresh_count}회")

if st.button('🔄 수동 새로고침'):
    st.rerun()

with st.spinner('핫딜 데이터를 긁어오는 중입니다... 🚀'):
    data, status = fetch_deals()

# 📊 현황판
st.subheader("📡 사이트별 수집 현황")
cols = st.columns(4)
cols[0].info(f"🔵 뽐뿌 (장터)\n\n**{status['뽐뿌']}**")
cols[1].success(f"🟠 퀘이사존\n\n**{status['퀘이사존']}**")
cols[2].warning(f"🟢 아카라이브\n\n**{status['아카라이브']}**")
cols[3].error(f"🟣 에펨코리아\n\n**{status['에펨코리아']}**")
st.divider()

if data:
    site_colors = {'뽐뿌': '🔵 뽐뿌', '퀘이사존': '🟠 퀘이사존'}
    for item in data:
        with st.container():
            col1, col2, col3 = st.columns([1.5, 6, 1])
            col1.write(f"**{site_colors.get(item['site'], item['site'])}**")
            col2.markdown(f"[{item['title']}]({item['link']})")
            col3.write(f"🕒 {item['time']}")
            st.divider()
else:
    st.warning("불러온 데이터가 없습니다.")
