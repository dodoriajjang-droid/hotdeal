import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

# --- Streamlit UI 기본 설정 ---
st.set_page_config(layout="wide")
st.title("🔥 실시간 장터 & 핫딜 모아보기")

@st.cache_data(ttl=300) 
def get_hot_deals():
    deals = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    # 혹시 날짜가 텍스트(예: 03-13, 26.03.13)로 표시될 경우를 대비해 오늘 날짜 문자열 생성
    today_dash = datetime.now().strftime("%m-%d")
    today_dot = datetime.now().strftime("%y.%m.%d")
    
    # 1. 뽐뿌 '장터' (pmarket) 크롤링
    ppomppu_url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=pmarket"
    try:
        res = requests.get(ppomppu_url, headers=headers, timeout=10)
        res.encoding = 'euc-kr' 
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for row in soup.select("tr.list0, tr.list1"):
            # 장터 게시판은 font 태그 대신 a 태그를 직접 찾는 것이 정확함
            a_tags = row.select("a")
            link_tag = None
            
            for a in a_tags:
                href = a.get("href", "")
                # 댓글 링크나 썸네일이 아닌 본문 제목 링크만 골라내기
                if "id=pmarket" in href and "no=" in href and a.text.strip():
                    link_tag = a
                    break
            
            if not link_tag: continue
            
            title = link_tag.text.strip()
            link = "https://www.ppomppu.co.kr/zboard/" + link_tag['href']
            
            # 등록일 추출 (장터 게시판 구조에 맞춤)
            date_str = "알수없음"
            tds = row.select("td.eng.list_vspace, td.list_vspace")
            for td in tds:
                text = td.text.strip()
                if ":" in text or "." in text or "-" in text or "/" in text:
                    date_str = text
                    break
            
            # 콜론(:)이 있거나 오늘 날짜와 일치하면 '오늘글'로 판별
            is_today = (":" in date_str) or (today_dash in date_str) or (today_dot in date_str)
            
            deals.append({"출처": "뽐뿌(장터)", "등록일": date_str, "상품명": title, "게시글 링크": link, "오늘글": is_today})
    except Exception as e:
        st.error(f"뽐뿌 장터 크롤링 실패: {e}")

    # 2. 퀘이사존 크롤링
    quasar_url = "https://quasarzone.com/bbs/qb_saleinfo"
    try:
        res = requests.get(quasar_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for item in soup.select("div.market-info-list-cont"):
            title_span = item.select_one("span.ellipsis-with-reply-cnt")
            if not title_span: continue
            title = title_span.text.strip()
            
            a_tag = item.select_one("a.subject-link") or item.select_one("p.tit a")
            link = "https://quasarzone.com" + a_tag['href'] if a_tag else ""
            
            date_span = item.select_one("span.date")
            date_str = date_span.text.strip() if date_span else "알수없음"
            
            # 콜론(:)이 있거나 오늘 날짜와 일치하면 '오늘글'로 판별
            is_today = (":" in date_str) or (today_dash in date_str) or (today_dot in date_str)
            
            deals.append({"출처": "퀘이사존", "등록일": date_str, "상품명": title, "게시글 링크": link, "오늘글": is_today})
    except Exception as e:
        st.error(f"퀘이사존 크롤링 실패: {e}")

    return pd.DataFrame(deals)

# --- 화면 출력 부분 ---
show_only_today = st.checkbox("오늘 올라온 글만 보기 (체크 해제 시 전체 보기)", value=True)

if st.button("🔄 새로고침"):
    st.cache_data.clear()

with st.spinner("데이터를 불러오는 중..."):
    df_deals = get_hot_deals()

if not df_deals.empty:
    if show_only_today:
        filtered_df = df_deals[df_deals["오늘글"] == True]
    else:
        filtered_df = df_deals
        
    display_df = filtered_df.drop(columns=["오늘글"])
    
    if not display_df.empty:
        st.success(f"총 {len(display_df)}개의 글을 가져왔어!")
        st.dataframe(
            display_df,
            column_config={
                "출처": st.column_config.TextColumn("출처", width="small"),
                "등록일": st.column_config.TextColumn("등록일", width="small"),
                "상품명": st.column_config.TextColumn("상품명", width="large"),
                "게시글 링크": st.column_config.LinkColumn("게시글 링크 (클릭하여 이동)")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning("전체 데이터는 가져왔는데, 필터링 결과 '오늘' 올라온 글이 없어!")
else:
    st.error("데이터를 가져오지 못했어.")
