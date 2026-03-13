import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# 1. 한국 시간(KST) 및 오늘 날짜 설정 (클라우드 서버는 기본이 UTC이므로 필수)
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
                date_tag = row.select_one('td.eng.list_vspace')
                if date_tag and ":" in date_tag.text: 
                    title_tag = row.select_one('font.list_title')
                    if title_tag:
                        link_tag = row.select_one('td.list_vspace a')
                        if link_tag:
                            link = "https://www.ppomppu.co.kr/zboard/" + link_tag['href']
                            results.append({'site': '뽐뿌', 'title': title_tag.text.strip(), 'link': link, 'time': date_tag.text.strip()})
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
            
            rows = soup.select('table tbody tr')
            for row in rows:
                time_tag = row.select_one('span.date')
                if time_tag and (":" in time_tag.text or "전" in time_tag.text):
                    title_tag = row.select_one('span.tit')
                    link_tag = row.select_one('a.subject-link')
                    
                    if title_tag and link_tag:
                        link = "https://quasarzone.com" + link_tag['href']
                        results.append({'site': '퀘이사존', 'title': title_tag.text.strip(), 'link': link, 'time': time_tag.text.strip()})
        else:
            st.error(f"퀘이사존 접속 실패: 응답 코드 {res.status_code}")
    except Exception as e:
        st.error(f"퀘이사존 크롤링 중 에러 발생: {e}")

    return results

# --- Streamlit UI ---
st.set_page_config(page_title="실시간 핫딜 모니터링", layout="wide")
st.title("🔥 오늘의 실시간 핫딜 (KST 기준)")

# 화면 상단에 현재 KST 시간 표시
kst_now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"서버 데이터 갱신 시간: {kst_now}")

if st.button('새로고침'):
    st.rerun()

with st.spinner('핫딜 정보를 불러오는 중입니다...'):
    data = fetch_deals()

if data:
    for item in data:
        with st.container():
            col1, col2, col3 = st.columns([1, 6, 1])
            col1.info(item['site'])
            col2.markdown(f"**[{item['title']}]({item['link']})**")
            col3.write(f"🕒 {item['time']}")
            st.divider()
else:
    st.warning("현재 올라온 당일 게시글이 없거나 데이터를 불러오지 못했습니다. 에러 메시지를 확인해 주세요.")
