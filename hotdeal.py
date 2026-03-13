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
    # 접속 성공 여부를 기록할 현황판 딕셔너리
    status = {
        '뽐뿌': '🔴 실패/차단', 
        '퀘이사존': '🔴 실패/차단', 
        '아카라이브': '🔴 실패/차단', 
        '에펨코리아': '🔴 실패/차단'
    }
    
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
            
            # 뽐뿌의 진짜 게시글 줄인 list0, list1만 정확히 타겟팅
            rows = soup.find_all('tr', class_=['list0', 'list1'])
            count = 0
            
            for row in rows:
                title_tag = row.select_one('font.list_title')
                if not title_tag: continue
                
                a_tag = title_tag.find_parent('a')
                if not a_tag: continue
                
                title = title_tag.text.strip()
                link = "https://www.ppomppu.co.kr/zboard/" + a_tag['href']
                
                # 시간 찾기 (td 태그 중 'eng' 클래스를 가진 곳에 ':'이 있으면 무조건 시간)
                time_str = ""
                for td in row.find_all('td', class_='eng'):
                    if ':' in td.text:
                        time_str = td.text.strip()
                        break
                        
                if time_str:
                    results.append({'site': '뽐뿌', 'title': title, 'link': link, 'time': time_str})
                    count += 1
            
            status['뽐뿌'] = f"🟢 성공 ({count}개)" if count > 0 else "🟡 파싱 실패 (구조변경)"
        else:
            status['뽐뿌'] = f"🔴 차단됨 ({res.status_code})"
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
            status['퀘이사존'] = f"🟢 성공 ({count}개)" if count > 0 else "🟡 파싱 실패"
        else:
            status['퀘이사존'] = f"🔴 차단됨 ({res.status_code})"
    except Exception as e:
        status['퀘이사존'] = f"🔴 에러: {str(e)[:15]}"

    # --- [3] 아카라이브 크롤링 ---
    try:
        arca_url = "https://arca.live/b/hotdeal"
        res = scraper.get(arca_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select('.vrow:not(.notice)')
            count = 0
            
            for row in rows:
                title_tag = row.select_one('.title')
                if title_tag:
                    title = title_tag.text.strip()
                    a_tag = row.select_one('a')
                    if a_tag:
                        link = "https://arca.live" + a_tag.get('href', '')
                        time_tag = row.select_one('time')
                        if time_tag and ":" in time_tag.text:
                            results.append({'site': '아카라이브', 'title': title, 'link': link, 'time': time_tag.text.strip()})
                            count += 1
            status['아카라이브'] = f"🟢 성공 ({count}개)" if count > 0 else "🟡 봇 차단(Captcha) 의심"
        else:
            status['아카라이브'] = f"🔴 차단됨 ({res.status_code})"
    except Exception as e:
        status['아카라이브'] = f"🔴 에러: {str(e)[:15]}"

    # --- [4] 에펨코리아 크롤링 ---
    try:
        fm_url = "https://www.fmkorea.com/hotdeal"
        res = scraper.get(fm_url, headers=headers, timeout=10)
        
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
                        if time_td and ":" in time_td.text:
                            results.append({'site': '에펨코리아', 'title': title, 'link': link, 'time': time_td.text.strip()})
                            count += 1
            status['에펨코리아'] = f"🟢 성공 ({count}개)" if count > 0 else "🟡 봇 차단(Captcha) 의심"
        else:
            status['에펨코리아'] = f"🔴 차단됨 ({res.status_code})"
    except Exception as e:
        status['에펨코리아'] = f"🔴 에러: {str(e)[:15]}"

    return results, status

# --- Streamlit UI ---
st.set_page_config(page_title="실시간 핫딜 모니터링", layout="wide")
st.title("🔥 통합 실시간 핫딜 모니터링")

kst_now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"최근 갱신 시간: {kst_now} (KST)")

if st.button('🔄 새로고침'):
    st.rerun()

with st.spinner('4개 커뮤니티 데이터를 가져오는 중입니다... 🚀'):
    data, status = fetch_deals()

# 📊 사이트별 상태 현황판 출력 (가장 중요)
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
        '퀘이사존': '🟠 퀘이사존',
        '아카라이브': '🟢 아카라이브',
        '에펨코리아': '🟣 에펨코리아'
    }

    for item in data:
        with st.container():
            col1, col2, col3 = st.columns([1.5, 6, 1])
            col1.write(f"**{site_colors.get(item['site'], item['site'])}**")
            col2.markdown(f"[{item['title']}]({item['link']})")
            col3.write(f"🕒 {item['time']}")
            st.divider()
else:
    st.warning("불러온 데이터가 없습니다. 상단의 상태 현황판을 확인해 주세요.")
