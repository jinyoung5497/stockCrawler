import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def crawl_and_update_sheet():
    # --- 1. 셀레니움 설정 ---
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 브라우저 창을 띄우지 않으려면 활성화
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # 네이버 상한가 페이지 접속
        url = "https://stock.naver.com/market/stock/kr/stocklist/upper"
        driver.get(url)
        time.sleep(3)  # 데이터 로딩 대기

        # 데이터 추출
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        extracted_data = []

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 5: continue
            name = cols[0].text.split('\n')[2]    # 종목명
            price = cols[1].text.split('\n')[0].strip()       # 종가
            ratio_raw = cols[2].text.split('(')[-1].replace('%)', '').replace('+', '') # 등락률 숫자만
            ratio = float(ratio_raw)
            
            # 거래대금 추출 및 '억' 단위 가공
            # 네이버는 거래대금을 '1,234백만' 형식으로 표기함
            value_raw = cols[4].text.replace(',', '').replace('백만', '')
            value_eok = round(float(value_raw) / 100, 1)

            # 15% 이상 필터링
            if ratio >= 15.0:
                extracted_data.append([name, price, f"{ratio}%", value_eok])

        # --- 2. 구글 시트 연결 및 업데이트 ---
        # 인증 파일 경로 및 범위 설정
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        client = gspread.authorize(creds)

        # 시트 이름으로 열기 (실제 시트 이름으로 수정하세요)
        doc = client.open("주식 쉐도잉") 
        sheet = doc.get_worksheet(0) # 첫 번째 탭

        # 기존 데이터 삭제 (C3부터 하단 영역)
        # 2행은 헤더이므로 유지
        sheet.batch_clear(["B3:F100"])

        # 데이터 입력 (C3 셀부터 시작)
        if extracted_data:
            sheet.update('B3', extracted_data)
            print(f"성공: {len(extracted_data)}개의 종목을 업데이트했습니다.")
        else:
            print("조건에 맞는 종목이 없습니다.")

    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_and_update_sheet()