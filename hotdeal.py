import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# 1. 한국 시간(KST) 및 오늘 날짜 설정
def get_kst_today():
    kst = pytz.timezone('Asia/Seoul')
    return datetime.now(kst).strftime('%Y-%m-%d')

def fetch_deals():
    today_str = get_kst_today()
    results = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # --- [1] 뽐뿌 뽐뿌게시판 크롤링 ---
    try:
        pp_url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"
        res = requests.get(pp_url, headers=headers, timeout=5)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        rows = soup.select('tr.list1, tr.list0')
        for row in rows:
            date_tag = row.select_one('td.eng.list_vspace')
            if date_tag and ":" in date_tag.text: # 뽐뿌는 오늘 글이 '14:20' 식으로 표시됨
                title_tag = row.select_one('font.list_title')
                if title_tag:
                    link = "https://www.ppomppu.co.kr/zboard/" + row.select_one('td.list_vspace a')['href']
                    results.append({'site': '뽐뿌', 'title': title_tag.text.strip(), 'link': link, 'time': date_tag.text.strip()})
    except: pass

    # --- [2] 퀘이사존 핫딜 게시판 크롤링 ---
    try:
        qs_url = "https://quasarzone.com/bbs/qb_saleinfo"
        res = requests.get(qs_url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 퀘이사존은 오늘 글이 "14:20" 또는 "방금 전" 등으로 표시될 수 있음
        rows = soup.select('table tbody tr')
        for row in rows:
            time_tag = row.select_one('span.date')
            if time_tag and (":" in time_tag.text or "분 전" in time_tag.text):
                title_tag = row.select_one('span.tit')
                if title_tag:
                    link = "https://quasarzone.com" + row.select_one('a.subject-link')['href']
                    results.append({'site': '퀘이사존', 'title': title_tag.text.strip(), 'link': link, 'time': time_tag.text.strip()})
    except: pass

    return results

# --- Streamlit UI ---
st.set_page_config(page_title="실시간 핫딜 모니터링", layout="wide")
st.title("🔥 오늘의 실시간 핫딜 (KST 기준)")
st.caption(f"기준 시간: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')}")

if st.button('새로고침'):
    st.rerun()

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
    st.warning("현재 올라온 당일 게시글이 없습니다.")
