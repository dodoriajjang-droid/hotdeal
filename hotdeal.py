# --- [1] 뽐뿌 크롤링 ---
    try:
        pp_url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"
        res = scraper.get(pp_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            html = res.content.decode('euc-kr', 'replace')
            
            # 🚨 디버깅용: 뽐뿌에서 진짜 뭘 받아왔는지 화면에 출력해 봅니다.
            st.warning("뽐뿌에서 받아온 데이터 미리보기:")
            st.code(html[:500]) # HTML 첫 500글자만 화면에 표시
            
            soup = BeautifulSoup(html, 'html.parser')
            # ... (이하 기존 코드 동일) ...
