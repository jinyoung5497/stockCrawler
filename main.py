import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def get_stock_data(driver, url, filter_type):
    driver.get(url)
    time.sleep(3)  # 로딩 대기
    
    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    extracted = []
    
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) < 5: continue
        
        try:
            # 공통 데이터 추출
            name = cols[0].text.split('\n')[2] if '\n' in cols[0].text else cols[0].text
            price = cols[1].text.split('\n')[0].strip()
            
            # 등락률 추출 (숫자만 추출하여 float 변환)
            ratio_text = cols[2].text.replace('%', '').replace('+', '').strip()
            # '(-1.23)' 형태일 경우 괄호 제거
            if '(' in ratio_text:
                ratio_text = ratio_text.split('(')[-1].replace(')', '')
            ratio = float(ratio_text)
            
            # 거래대금 추출 (단위: 백만 -> 억으로 변환)
            value_raw = cols[4].text.replace(',', '').replace('백만', '').strip()
            value_eok = round(float(value_raw) / 100, 1)

            # --- 필터링 로직 ---
            if filter_type == "upper":
                # 1. 상한가 페이지: 15% 이상
                if ratio >= 15.0:
                    extracted.append([name, price, f"{ratio}%", value_eok, "상한가근접"])
            
            elif filter_type == "price_top":
                # 2. 거래대금 상위 페이지: 거래대금 500억 이상 & 상승률 6% 이상
                if value_eok >= 500 and ratio >= 6.0:
                    # 구분자를 '급등(500억↑)'으로 변경
                    extracted.append([name, price, f"{ratio}%", value_eok, "급등(500억↑)"])
                    
        except Exception as e:
            continue
            
    return extracted

def crawl_and_update_sheet():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        total_data = []

        # 1. 상한가 종목 수집
        print("상한가 종목 수집 중...")
        upper_url = "https://stock.naver.com/market/stock/kr/stocklist/upper"
        total_data.extend(get_stock_data(driver, upper_url, "upper"))

        # 2. 거래대금 상위(급락) 종목 수집
        print("거래대금 상위 급락 종목 수집 중...")
        top_url = "https://stock.naver.com/market/stock/kr/stocklist/priceTop"
        total_data.extend(get_stock_data(driver, top_url, "price_top"))

        # --- 구글 시트 업데이트 ---
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        client = gspread.authorize(creds)

        doc = client.open("주식 쉐도잉") 
        sheet = doc.get_worksheet(0)

        # 기존 영역 초기화 (B3부터 F열까지 넉넉히 삭제)
        sheet.batch_clear(["B3:F100"])

        if total_data:
            # 리스트를 등락률이나 이름순으로 정렬하고 싶다면 여기서 정렬 가능
            sheet.update('B3', total_data)
            print(f"성공: 총 {len(total_data)}개의 종목을 시트에 업데이트했습니다.")
        else:
            print("조건에 맞는 종목이 하나도 없습니다.")

    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_and_update_sheet()