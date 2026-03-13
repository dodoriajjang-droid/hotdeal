import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

# --- Streamlit UI 기본 설정 ---
st.set_page_config(layout="wide")
st.title("🔥 실시간 핫딜 모아보기 (디버깅 모드)")

# --- 크롤링 함수 ---
@st.cache_data(ttl=300) 
def get_hot_deals():
    deals = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    # 1. 뽐뿌 크롤링
    ppomppu_url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"
    try:
        res = requests.get(ppomppu_url, headers=headers, timeout=10)
        res.encoding = 'euc-kr' 
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for row in soup.select("tr.list0, tr.list1"):
            title_tag = row.select_one("font.list_title")
            if not title_tag: continue
            title = title_tag.text.strip()
            
            a_tag = row.select_one("a")
            link = "https://www.ppomppu.co.kr/zboard/" + a_tag['href'] if a_tag else ""
            
            # 뽐뿌 날짜/시간 확인 (오늘 글이면 콜론이 포함됨)
            date_text = row.text 
            is_today = ":" in date_text 
            
            deals.append({"출처": "뽐뿌", "상품명": title, "게시글 링크": link, "오늘글": is_today})
    except Exception as e:
        st.error(f"뽐뿌 크롤링 실패: {e}")

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
            date_text = date_span.text.strip() if date_span else ""
            is_today = ":" in date_text
            
            deals.append({"출처": "퀘이사존", "상품명": title, "게시글 링크": link, "오늘글": is_today})
    except Exception as e:
        st.error(f"퀘이사존 크롤링 실패: {e}")

    return pd.DataFrame(deals)

# --- 화면 출력 부분 ---
# 테스트를 위한 체크박스 추가
show_only_today = st.checkbox("오늘 올라온 핫딜만 보기 (체크 해제 시 전체 보기)", value=True)

if st.button("🔄 새로고침"):
    st.cache_data.clear()

with st.spinner("핫딜 데이터를 불러오는 중..."):
    df_deals = get_hot_deals()

if not df_deals.empty:
    # 체크박스 상태에 따라 데이터 필터링
    if show_only_today:
        filtered_df = df_deals[df_deals["오늘글"] == True]
    else:
        filtered_df = df_deals
        
    # '오늘글' 컬럼은 화면에 보여줄 필요 없으니 제외
    display_df = filtered_df.drop(columns=["오늘글"])
    
    if not display_df.empty:
        st.success(f"총 {len(display_df)}개의 핫딜을 가져왔어!")
        st.dataframe(
            display_df,
            column_config={
                "출처": st.column_config.TextColumn("출처", width="small"),
                "상품명": st.column_config.TextColumn("상품명", width="large"),
                "게시글 링크": st.column_config.LinkColumn("게시글 링크 (클릭하여 이동)")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning("전체 데이터는 가져왔는데, '오늘' 올라온 글은 필터링에서 다 걸러진 것 같아.")
else:
    st.error("앗, 사이트에서 데이터를 아예 못 가져오고 있어. (봇 차단 또는 사이트 구조 변경 의심)")
