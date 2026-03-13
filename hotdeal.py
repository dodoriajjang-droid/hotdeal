import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

def get_ppomppu_today_items(keyword):
    # 1. 한국 시간(KST) 기준 설정
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    
    # 뽐뿌 장터 검색 URL 설정 (보내주신 pmarket 기준)
    url = f"https://www.ppomppu.co.kr/zboard/zboard.php?id=pmarket&search_type=sub_memo&keyword={keyword}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"뽐뿌 접속 오류: {e}")
        return []

    items = []
    # 뽐뿌 게시판 목록 파싱
    rows = soup.select('tr.list1, tr.list0')
    
    for row in rows:
        # 제목 파싱
        title_tag = row.select_one('font.list_title') or row.select_one('td.list_vspace a')
        if not title_tag: continue
        title = title_tag.text.strip()

        # 링크 파싱
        link_tag = row.select_one('td.list_vspace a')
        if not link_tag: continue
        href = link_tag.get('href', '')
        # 상대 경로인 경우 절대 경로로 변환
        link = f"https://www.ppomppu.co.kr/zboard/{href}" if href else ""

        # 날짜 파싱
        date_tag = row.select_one('td.eng.list_vspace')
        if not date_tag: continue
        date_text = date_tag.text.strip()

        # 2 & 3. 체크박스 제거 및 '오늘' 기본값 처리
        # 뽐뿌는 오늘 올라온 글은 '13:54:34' 처럼 시간 형식으로, 
        # 이전 글은 '26.03.12' 처럼 날짜 형식으로 표시됩니다.
        # 따라서 ':' 문자가 포함되어 있으면 KST 기준 당일 글로 간주합니다.
        is_today = ":" in date_text 

        if is_today:
            items.append({
                'title': title, 
                'link': link, 
                'date': date_text
            })

    return items

# --- 실행 부분 ---
# '오늘만 보기' 체크박스 관련 UI 코드(st.checkbox 등)는 삭제되었습니다.
keyword = "스타킹"
print(f"=== 뽐뿌 '{keyword}' 오늘(KST) 올라온 게시글 ===")

results = get_ppomppu_today_items(keyword)

if results:
    for idx, item in enumerate(results, 1):
        print(f"{idx}. {item['title']} [{item['date']}]")
        print(f"   링크: {item['link']}")
else:
    print("오늘 올라온 게시글이 없습니다.")
