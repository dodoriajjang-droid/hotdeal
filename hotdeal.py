import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import requests
from streamlit_autorefresh import st_autorefresh  # 자동 새로고침 라이브러리

# ==========================================
# 🚨 텔레그램 설정 (여기에 본인의 정보를 입력하세요!)
TELEGRAM_TOKEN = "여기에_봇파더에게_받은_토큰_입력"
TELEGRAM_CHAT_ID = "여기에_내_챗아이디_입력"
# ==========================================

# 이미 알림을 보낸 핫딜 링크를 기억해두는 저장소 (중복 전송 방지)
if 'sent_deals' not in st.session_state:
    st.session_state.sent_deals = set()

def get_kst_today():
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')

# 텔레그램 발송 함수
def send_telegram_message(title, link, site):
    # 토큰 설정을 안 했다면 무시
    if TELEGRAM_TOKEN == "여기에_봇파더에게_받은_토큰_입력":
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
    status = {'뽐뿌': '🔴 대기', '퀘이사존': '🔴 대기', '아카라이브': '🔒 클라우드 IP 차단됨', '에펨코리아': '🔒 클라우드 IP 차단됨'}
    
    scraper = cloudscraper.create_scraper()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # --- [1] 뽐뿌 크롤링 ---
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
                        
                        # ✨ 신규 핫딜이면 텔레그램 전송 후 기록!
                        if link not in st.session_state.sent_deals:
                            send_telegram_message(title, link, "뽐뿌")
                            st.session_state.sent_deals.add(link)
                            
            status['뽐뿌'] = f"🟢 성공 ({count}개)" if count > 0 else "🟡 파싱 실패 (당일 글 없음)"
        else:
            status['뽐뿌'] = f"🔴 접속 차단 ({res.status_code})"
    except Exception as e:
        status['뽐뿌'] = f"🔴 에러: {str(e)[:15]}"

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
                            
                            # ✨ 신규 핫딜이면 텔레그램 전송 후 기록!
                            if link not in st.session_state.sent_deals:
                                send_telegram_message(title, link, "퀘이사존")
                                st.session_state.sent_deals.add(link)
                                
            status['퀘이사존'] = f"🟢 성공 ({count}개)" if count > 0 else "🟡 파싱 실패"
        else:
            status['퀘이사존'] = f"🔴 접속 차단 ({res.status_code})"
    except Exception as e:
        status['퀘이사존'] = f"🔴 에러: {str(e)[:15]}"

    return results, status

# --- Streamlit UI ---
st.set_page_config(page_title="실시간 핫딜 모니터링", layout="wide")

# ⏱️ 5분(300,000 밀리초)마다 자동으로 페이지를 새로고침합니다.
# 브라우저 창을 켜두기만 하면 알아서 작동합니다.
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
