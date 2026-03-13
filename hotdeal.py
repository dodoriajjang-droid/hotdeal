import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re  # 문자열(시간) 추출 필살기

# 1. 한국 시간(KST) 및 오늘 날짜 설정
def get_kst_today():
    kst = pytz.timezone('Asia/Seoul')
    return datetime.now(kst).strftime('%Y-%m-%d')

def fetch_deals():
    results = []
    scraper = cloudscraper.create_scraper()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # --- [1] 뽐뿌 크롤링 (정규식 필살기 적용) ---
    try:
        pp_url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"
        res = scraper.get(pp_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            html = res.content.decode('euc-kr', 'replace')
            soup = BeautifulSoup(html, 'html.parser')
            
            rows = soup.find_all('tr')
            for row in rows:
                # 1. 'zboard.php?id=ppomppu&no=' 가 포함된 진짜 게시글 링크만 찾기
                title_a = None
                for a in row.find_all('a'):
                    if 'id=ppomppu&no=' in a.get('href', '') and a.text.strip():
                        title_a = a
                        break
                
                if title_a:
                    # 2. 클래스 이름 다 무시하고 텍스트 전체에서 시간(00:00:00 또는 00:00)만 강제 추출
                    row_text = row.text.replace('\n', ' ')
                    time_match = re.search(r'\b(\d{2}:\d{2}:\d{2})\b', row_text) or re.search(r'\b(\d{2}:\d{2})\b', row_text)
                    
                    if time_match:
                        title = title_a.text.strip()
                        link = "https://www.ppomppu.co.kr/zboard/" + title_a['href']
                        results.append({'site': '뽐뿌', 'title': title, 'link': link, 'time': time_match.group(1)})
        else:
            st.error(f"뽐뿌 접속 실패: 응답 코드 {res.status_code}")
    except Exception as e:
        st.error(f"뽐뿌 크롤링 중 에러 발생: {e}")

    # --- [2] 퀘이사존 크롤링 ---
    try:
        qs_url = "https://quasarzone.com/bbs/qb_saleinfo"
        res = scraper.get(qs_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.select('a.subject-link')
            
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
    except Exception as e:
        st.error(f"퀘이사존 크롤링 중 에러 발생: {e}")

    # --- [3] 아카라이브 (핫딜 채널) 크롤링 ---
    try:
        arca_url = "https://arca.live/b/hotdeal"
        res = scraper.get(arca_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # 공지사항(.notice) 제외하고 일반 글(.vrow)만 가져오기
            rows = soup.select('.vrow:not(.notice)') 
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
                            if ":" in time_str: # 아카라이브도 당일 글은 14:20 형태로 나옴
                                results.append({'site': '아카라이브', 'title': title, 'link': link, 'time': time_str})
    except Exception as e:
        st.error(f"아카라이브 크롤링 중 에러 발생: {e}")

    # --- [4] 에펨코리아 (핫딜 게시판) 크롤링 ---
    try:
        fm_url = "https://www.fmkorea.com/hotdeal"
        res = scraper.get(fm_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select('tr') # 펨코는 테이블 구조 사용
            for row in rows:
                title_td = row.select_one('td.title')
                if title_td:
                    a_tag = title_td.select_one('a')
                    if a_tag:
                        # 댓글 수 등 불필요한 공백 제거
                        title = re.sub(r'\s+', ' ', a_tag.text).strip()
                        
                        # 링크 조합
                        href = a_tag['href']
                        link = "https://www.fmkorea.com" + href if href.startswith('/') else href
                        
                        time_td = row.select_one('td.time')
                        if time_td:
                            time_str = time_td.text.strip()
                            if ":" in time_str:
                                results.append({'site': '에펨코리아', 'title': title, 'link': link, 'time': time_str})
    except Exception as e:
        st.error(f"에펨코리아 크롤링 중 에러 발생: {e}")

    return results

# --- Streamlit UI ---
st.set_page_config(page_title="실시간 핫딜 모니터링", layout="wide")
st.title("🔥 오늘의 실시간 핫딜 (KST 기준)")

kst_now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"서버 데이터 갱신 시간: {kst_now}")

if st.button('🔄 새로고침'):
    st.rerun()

with st.spinner('4개 커뮤니티의 핫딜 정보를 긁어오는 중입니다... 🚀'):
    data = fetch_deals()

if data:
    st.success(f"총 {len(data)}개의 당일 핫딜을 불러왔습니다!")
    
    # 사이트별로 태그 색상을 다르게 주기 위한 딕셔너리
    site_colors = {
        '뽐뿌': '🔵 뽐뿌',
        '퀘이사존': '🟠 퀘이사존',
        '아카라이브': '🟢 아카라이브',
        '에펨코리아': '🟣 에펨코리아'
    }

    for item in data:
        with st.container():
            col1, col2, col3 = st.columns([1.5, 6, 1])
            # 사이트 이름 출력
            col1.write(f"**{site_colors.get(item['site'], item['site'])}**")
            col2.markdown(f"[{item['title']}]({item['link']})")
            col3.write(f"🕒 {item['time']}")
            st.divider()
else:
    st.warning("현재 올라온 당일 게시글이 없거나 데이터를 파싱하지 못했습니다.")
