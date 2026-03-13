@st.cache_data(ttl=300) # 5분 캐싱
def get_hot_deals():
    deals = []
    
    # 1. 뽐뿌 크롤링 (차단 우회를 위한 강력한 헤더 및 인코딩 설정)
    ppomppu_url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"
    ppomppu_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.ppomppu.co.kr/",
        "Connection": "keep-alive"
    }
    
    try:
        res_p = requests.get(ppomppu_url, headers=ppomppu_headers, timeout=10)
        res_p.encoding = 'euc-kr' # 뽐뿌 특유의 한글 깨짐 방지
        res_p.raise_for_status()
        
        soup_p = BeautifulSoup(res_p.text, 'html.parser')
        rows = soup_p.select("tr.list1, tr.list0")
        
        for row in rows:
            title_tag = row.select_one("font.list_title")
            a_tag = row.select_one("a")
            if title_tag and a_tag:
                title = title_tag.text.strip()
                link = "https://www.ppomppu.co.kr/zboard/" + a_tag['href']
                deals.append({"출처": "뽐뿌", "상품명": title, "게시글 링크": link})
    except Exception as e:
        st.error(f"뽐뿌 크롤링 실패: {e}")

    # 2. 퀘이사존 크롤링 (서버/IT/하드웨어 특화)
    quasar_url = "https://quasarzone.com/bbs/qb_saleinfo"
    quasar_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    try:
        res_q = requests.get(quasar_url, headers=quasar_headers, timeout=10)
        res_q.raise_for_status()
        soup_q = BeautifulSoup(res_q.text, 'html.parser')
        
        # 퀘이사존 게시글 목록 구조
        items = soup_q.select(".market-info-list-cont p.tit a")
        for item in items:
            title_span = item.select_one("span.ellipsis-with-reply-cnt")
            if title_span:
                title = title_span.text.strip()
                link = "https://quasarzone.com" + item['href']
                deals.append({"출처": "퀘이사존", "상품명": title, "게시글 링크": link})
    except Exception as e:
        st.error(f"퀘이사존 크롤링 실패: {e}")

    return pd.DataFrame(deals)
