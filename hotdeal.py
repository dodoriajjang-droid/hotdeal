import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re

def get_kst_today():
    return datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')

def fetch_deals():
    results = []
    status = {
        '뽐뿌': '🔴 대기', 
        '퀘이사존': '🔴 대기', 
        '아카라이브': '🔒 클라우드 IP 차단됨', 
        '에펨코리아': '🔒 클라우드 IP 차단됨'
    }
    
    scraper = cloudscraper.create_scraper()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # --- [1] 뽐뿌 크롤링 (역추적 방식 적용!) ---
    try:
        pp_url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"
        res = scraper.get(pp_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            html = res.content.decode('euc-kr', 'replace')
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. 뽐뿌의 고유한 '제목 폰트 클래스'를 싹 다 찾습니다.
            title_fonts = soup.find_all('font', class_='list_title')
            count = 0
            
            for font in title_fonts:
                title = font.text.strip()
                
                # 2. 제목을 감싸는 링크(a) 태그 찾기
                a_tag = font.find_parent('a')
                if not a_tag or 'href' not in a_tag.attrs:
                    continue
                link = "https://www.ppomppu.co.kr/zboard/" + a_tag['href']
                
                # 3. 제목이 있는 그 '줄(tr)' 전체를 찾아서 시간 추출하기
                tr = font.find_parent('tr')
                if tr:
                    # 줄 전체 텍스트에서 XX:XX:XX 또는 XX:XX 형태의 숫자 스캔
                    match = re.search(r'\b(\d{2}:\d{2}(?::\d{2})?)\b', tr.text)
                    if match:
                        time_str = match.group(1)
                        results.append({'site': '뽐뿌', 'title': title, 'link': link, 'time': time_str})
                        count += 1
            
            status['뽐뿌'] = f"🟢 성공 ({count}개)" if count > 0 else "🟡 파싱 실패 (당일 글 없음)"
        else:
            status['뽐뿌'] = f"🔴 접속 차단 ({res.status_code})"
    except Exception as e:
        status['뽐뿌'] = f"🔴 에러: {str(e)[:15]}"

    # --- [2] 퀘이사존 크롤링 (성공 로직 유지) ---
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
        status['퀘이사존'] = f"🔴 에러: {str(e)[:15]}"

    return results, status

# --- Streamlit UI ---
st.set_page_config(page_title="실시간 핫딜 모니터링", layout="wide")
st.title("🔥 통합 실시간 핫딜 모니터링")

kst_now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"최근 갱신 시간: {kst_now} (KST)")

if st.button('🔄 새로고침'):
    st.rerun()

with st.spinner('뽐뿌와 퀘이사존 데이터를 긁어오는 중입니다... 🚀'):
    data, status = fetch_deals()

# 📊 현황판
st.subheader("📡 사이트별 수집 현황")
cols = st.columns(4)
cols[0].info(f"🔵 뽐뿌\n\n**{status['뽐뿌']}**")
cols[1].success(f"🟠 퀘이사존\n\n**{status['퀘이사존']}**")
cols[2].warning(f"🟢 아카라이브\n\n**{status['아카라이브']}**")
cols[3].error(f"🟣 에펨코리아\n\n**{status['에펨코리아']}**")
st.divider()

if data:
    site_colors = {
        '뽐뿌': '🔵 뽐뿌',
        '퀘이사존': '🟠 퀘이사존'
    }

    for item in data:
        with st.container():
            col1, col2, col3 = st.columns([1.5, 6, 1])
            col1.write(f"**{site_colors.get(item['site'], item['site'])}**")
            col2.markdown(f"[{item['title']}]({item['link']})")
            col3.write(f"🕒 {item['time']}")
            st.divider()
else:
    st.warning("불러온 데이터가 없습니다.")
