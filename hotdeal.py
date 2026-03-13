import streamlit as st
import requests
from bs4 import BeautifulSoup
import pytz
from datetime import datetime

def get_ppomppu_today(keyword):
    # 1. 한국 시간(KST) 설정
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)
    
    # 장터(pmarket) 검색 URL
    url = f"https://www.ppomppu.co.kr/zboard/zboard.php?id=pmarket&search_type=sub_memo&keyword={keyword}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*-/*'
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'euc-kr' # 뽐뿌는 한글 깨짐 방지를 위해 euc-kr 설정 필수
        soup = BeautifulSoup(res.text, 'html.parser')
    except Exception as e:
        st.error(f"접속 중 오류 발생: {e}")
        return []

    items = []
    # 게시글 행 찾기 (pmarket 게시판의 실제 id 구조 반영)
    rows = soup.find_all('tr', class_=['list0', 'list1'])

    for row in rows:
        # 제목 및 링크 추출
        # 뽐뿌 특유의 복잡한 a 태그 구조 대응
        all_links = row.find_all('a')
        target_link = None
        for a in all_links:
            if 'view.php?id=pmarket' in a.get('href', ''):
                target_link = a
                break
        
        if not target_link: continue
        
        title = target_link.text.strip()
        link = "https://www.ppomppu.co.kr/zboard/" + target_link.get('href')

        # 날짜 추출 (보통 5번째 혹은 6번째 td에 위치)
        tds = row.find_all('td')
        if len(tds) < 5: continue
        
        # 뽐뿌 리스트에서 날짜/시간이 적힌 칸 찾기
        date_text = ""
        for td in tds:
            if 'eng' in td.get('class', []) or ':' in td.text:
                date_text = td.text.strip()
        
        # '오늘' 올라온 글 필터링 (시간 형식인 경우만)
        if ":" in date_text:
            items.append({'title': title, 'link': link, 'date': date_text})

    return items

# --- 화면 출력 ---
st.set_page_config(page_title="뽐뿌 실시간 모니터링", layout="wide")
st.title("🕵️ 뽐뿌 오늘 자 '스타킹' 검색 결과")

# 사이드바 없이 바로 검색 실행 (기본값: 오늘)
if st.button('데이터 새로고침') or 'first_run' not in st.session_state:
    st.session_state['first_run'] = True
    with st.spinner('뽐뿌에서 오늘 올라온 글만 솎아내고 있습니다...'):
        results = get_ppomppu_today("스타킹")
        
        if results:
            for res in results:
                col1, col2 = st.columns([1, 8])
                col1.write(f"🕒 {res['date']}")
                col2.markdown(f"[{res['title']}]({res['link']})")
        else:
            st.info("현재 뽐뿌에 오늘(KST) 올라온 관련 글이 없습니다.")
