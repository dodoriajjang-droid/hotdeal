import streamlit as st
from curl_cffi import requests as requests_cffi # 🚨 핵심: 완벽한 크롬 위장 라이브러리
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import requests
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 🚨 텔레그램 설정
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
            parts = time_str.split(':')
            if len(parts) == 3:
                return now.replace(hour=int(parts[0]), minute=int(parts[1]), second=int(parts[2]), microsecond=0)
            elif len(parts) == 2:
                return now.replace(hour=int(parts[0]), minute=int(parts[1]), second=0, microsecond=0)
    except:
        pass
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
    status = {'뽐뿌': '🔴 대기', '퀘이사존': '🔴 대기', '아카라이브': '🔴 대기', '에펨코리아': '🔴 대기'}
    
    # --- [1] 뽐뿌 장터 크롤링 ---
    try:
        pp_url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=pmarket"
        # 🚨 impersonate="chrome" 옵션이 핵심입니다!
        res = requests_cffi.get(pp_url, impersonate="chrome", timeout=10)
        
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
        res = requests_cffi.get(qs_url, impersonate="chrome", timeout=10)
        
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

    # --- [3] 아카라이브 (핫딜 채널) 크롤링 ---
    try:
        arca_url = "https://arca.live/b/hotdeal"
        res = requests_cffi.get(arca_url, impersonate="chrome", timeout=10)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select('.vrow:not(.notice)') 
            count = 0
            
            for row in rows:
                title_tag = row.select_one('.title')
                if title_tag:
                    title = title_tag.text.strip()
                    a_tag = row.select_one('a')
                    if a_tag and 'href' in a_tag.attrs:
                        link = "https://arca.live" + a_tag['href']
                        
                        time_tag = row.select_one('time')
                        if time_tag:
                            time_str = time_tag.text.strip()
                            if ":" in time_str:
                                results.append({'site': '아카라이브', 'title': title, 'link': link, 'time': time_str})
                                count += 1
            status['아카라이브'] = f"🟢 성공 ({count}개)" if count > 0 else "🟡 봇 차단(Captcha)"
        else:
            status['아카라이브'] = f"🔴 접속 차단 ({res.status_code})"
    except Exception as e:
        status['아카라이브'] = f"🔴 에러"

    # --- [4] 에펨코리아 (핫딜 게시판) 크롤링 ---
    try:
        fm_url = "https://www.fmkorea.com/hotdeal"
        res = requests_cffi.get(fm_url, impersonate="chrome", timeout=10)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select('tr')
            count = 0
            
            for row in rows:
                title_td = row.select_one('td.title')
                if title_td:
                    a_tag = title_td.select_one('a')
                    if a_tag:
                        title = re.sub(r'\s+', ' ', a_tag.text).strip()
                        href = a_tag['href']
                        link = "https://www.fmkorea.com" + href if href.startswith('/') else href
                        
                        time_td = row.select_one('td.time')
                        if time_td:
                            time_str = time_td.text.strip()
                            if ":" in time_str:
                                results.append({'site': '에펨코리아', 'title': title, 'link': link, 'time': time_str})
                                count += 1
            status['에펨코리아'] = f"🟢 성공 ({count}개)" if count > 0 else "🟡 봇 차단(Captcha)"
        else:
            status['에펨코리아'] = f"🔴 접속 차단 ({res.status_code})"
    except Exception as e:
        status['에펨코리아'] = f"🔴 에러"

    # 최신순 정렬
    results.sort(key=lambda x: parse_time_for_sort(x['time']), reverse=True)

    for item in results:
         if item['link'] not in st.session_state.sent_deals:
             send_telegram_message(item['title'], item['link'], item['site'])
             st.session_state.sent_deals.add(item['link'])

    return results, status

# --- Streamlit UI ---
st.set_page_config(page_title="실시간 핫딜 모니터링", layout="wide")
refresh_count = st_autorefresh(interval=300000, limit=None, key="deal_autorefresh")

st.title("🔥 통합 실시간 핫딜 모니터링 (크롬 위장 모드)")

kst_now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"최근 갱신 시간: {kst_now} (KST) | 자동 새로고침 횟수: {refresh_count}회")

if st.button('🔄 수동 새로고침'):
    st.rerun()

with st.spinner('4개 커뮤니티 데이터를 긁어오는 중입니다... 🚀'):
    data, status = fetch_deals()

st.subheader("📡 사이트별 수집 현황")
cols = st.columns(4)
cols[0].info(f"🔵 뽐뿌 (장터)\n\n**{status['뽐뿌']}**")
cols[1].success(f"🟠 퀘이사존\n\n**{status['퀘이사존']}**")
cols[2].warning(f"🟢 아카라이브\n\n**{status['아카라이브']}**")
cols[3].error(f"🟣 에펨코리아\n\n**{status['에펨코리아']}**")
st.divider()

if data:
    site_colors = {'뽐뿌': '🔵 뽐뿌', '퀘이사존': '🟠 퀘이사존', '아카라이브': '🟢 아카라이브', '에펨코리아': '🟣 에펨코리아'}
    for item in data:
        with st.container():
            col1, col2, col3 = st.columns([1.5, 6, 1])
            col1.write(f"**{site_colors.get(item['site'], item['site'])}**")
            col2.markdown(f"[{item['title']}]({item['link']})")
            col3.write(f"🕒 {item['time']}")
            st.divider()
else:
    st.warning("불러온 데이터가 없습니다.")
