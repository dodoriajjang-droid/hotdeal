import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import hmac
import hashlib
import time
import json

# --- 파트너스 API 설정 ---
# 실제 서버 환경에 배포하실 때는 보안을 위해 st.secrets나 환경변수로 관리하시는 것이 좋습니다.
ACCESS_KEY = "여기에_본인의_액세스_키_입력"
SECRET_KEY = "여기에_본인의_시크릿_키_입력"
DOMAIN = "https://api-gateway.coupang.com"

def generate_hmac(method, url, secret_key, access_key):
    datetime_str = time.strftime('%y%m%d') + 'T' + time.strftime('%H%M%S') + 'Z'
    message = datetime_str + method + url
    signature = hmac.new(bytes(secret_key, 'utf-8'),
                         bytes(message, 'utf-8'),
                         hashlib.sha256).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={datetime_str}, signature={signature}"

def get_partners_link(original_url):
    method = "POST"
    url_path = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
    authorization = generate_hmac(method, url_path, SECRET_KEY, ACCESS_KEY)
    
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json"
    }
    payload = {"coupangUrls": [original_url]}
    
    try:
        response = requests.post(DOMAIN + url_path, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        data = response.json()
        return data['data'][0]['shortenUrl']
    except Exception as e:
        return f"에러 발생: {e}"

@st.cache_data(ttl=300) # 5분 동안 캐싱하여 서버 부하 방지
def get_hot_deals():
    """뽐뿌 핫딜 게시판 크롤링"""
    url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"
    
    # 웹 방화벽이나 보안 장비에서 봇(Bot) 트래픽으로 오인하여 차단하지 않도록 User-Agent 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    deals = []
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 뽐뿌 게시판 구조에 맞춘 CSS 선택자 (게시판 구조 변경 시 수정 필요)
        rows = soup.select("tr.list1, tr.list0")
        for row in rows:
            title_tag = row.select_one("font.list_title")
            a_tag = row.select_one("a")
            
            if title_tag and a_tag:
                title = title_tag.text.strip()
                # 상대 경로를 절대 경로로 변환
                link = "https://www.ppomppu.co.kr/zboard/" + a_tag['href']
                deals.append({"상품명": title, "게시글 링크": link})
                
    except Exception as e:
        st.error(f"크롤링 중 에러가 발생했습니다: {e}")
        
    return pd.DataFrame(deals)

# --- Streamlit UI 구성 ---
st.set_page_config(layout="wide")
st.title("🔥 핫딜 수집 & 쿠팡 파트너스 변환기")

# 1. 핫딜 크롤링 섹션
st.header("1. 실시간 핫딜 모아보기 (뽐뿌)")
if st.button("🔄 핫딜 목록 새로고침"):
    st.cache_data.clear() # 버튼 누르면 캐시 초기화 후 다시 불러옴

df_deals = get_hot_deals()

if not df_deals.empty:
    # 데이터프레임을 화면에 표출 (링크는 클릭 가능하게 설정)
    st.dataframe(
        df_deals,
        column_config={
            "게시글 링크": st.column_config.LinkColumn("게시글 링크 (클릭하여 이동)")
        },
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("현재 불러올 수 있는 핫딜 정보가 없습니다.")

st.divider()

# 2. 쿠팡 링크 변환 섹션
st.header("2. 쿠팡 수익형 링크로 변환")
st.write("위 핫딜 게시글에서 확인한 **쿠팡 원본 URL**을 아래에 입력하세요.")

input_url = st.text_input("쿠팡 상품 URL 입력:", placeholder="https://www.coupang.com/vp/products/...")

if st.button("🚀 파트너스 링크로 변환"):
    if "coupang.com" not in input_url:
        st.warning("유효한 쿠팡 URL을 입력해 주세요.")
    elif input_url:
        with st.spinner("링크 변환 중..."):
            partners_url = get_partners_link(input_url)
            
            if "에러 발생" not in partners_url:
                st.success("✅ 변환 완료!")
                st.code(partners_url, language="text")
                st.info("⚠️ 필수 기재 문구: '이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.'")
            else:
                st.error(partners_url)