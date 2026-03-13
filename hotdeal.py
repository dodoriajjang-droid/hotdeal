import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

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

    # --- [1] 뽐뿌 크롤링 ---
    try:
        pp_url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"
        res = scraper.get(pp_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            html = res.content.decode('euc-kr', 'replace')
            soup = BeautifulSoup(html, 'html.parser')
            
            rows = soup.select('tr.list1, tr.list0')
            for row in rows:
                title_tag = row.select_one('.list_title')
                
                if title_tag:
                    title = title_tag.text.strip()
                    a_tag = title_tag.find_parent('a')
                    
                    if a_tag and 'href' in a_tag.attrs:
                        link = "https://www.ppomppu.co.kr/zboard/" + a_tag['href']
                        
                        # 🚨 [수정된 부분] 게시글 번호에 속지 않고 '시간' 데이터만 골라내기
                        time_str = ""
                        for tag in row.select('.eng'):
                            if ":" in tag.text: # 텍스트 안에 ':' (콜론)이 있어야만 당일 시간 데이터로 인정
                                time_str = tag.text.strip()
                                break # 시간을 찾았으니 더 이상 찾지 않고 멈춤
                        
                        if time_str:
                            results.append({'site': '뽐뿌', 'title': title, 'link': link, 'time': time_str})
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
        else:
            st.error(f"퀘이사존 접속 실패: 응답 코드 {res.status_code}")
    except Exception as e:
        st.error(f"퀘이사존 크롤링 중 에러 발생: {e}")

    return results

# --- Streamlit UI ---
st.set_page_config(page_title="실시간 핫딜 모니터링", layout="wide")
st.title("🔥 오늘의 실시간 핫딜 (KST 기준)")

kst_now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"서버 데이터 갱신 시간: {kst_now}")

if st.button('🔄 새로고침'):
    st.rerun()

with st.spinner('핫딜 정보를 불러오는 중입니다...'):
    data = fetch_deals()

if data:
    st.success(f"총 {len(data)}개의 당일 핫딜을 불러왔습니다!")
    for item in data:
        with st.container():
            col1, col2, col3 = st.columns([1, 6, 1])
            col1.info(item['site'])
            col2.markdown(f"**[{item['title']}]({item['link']})**")
            col3.write(f"🕒 {item['time']}")
            st.divider()
else:
    st.warning("현재 올라온 당일 게시글이 없거나 데이터를 파싱하지 못했습니다.")
