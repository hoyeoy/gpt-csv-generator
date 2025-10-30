# debug_test.py
import newsclipping_thebell # 스크래핑 함수를 포함하는 파일
import pandas as pd
from datetime import datetime, timedelta

def main():
    # --- 1. 날짜 범위 테스트 ---
    # days_ago=1 : 어제 날짜 (GPT Action이 요청하는 기본값)
    # days_ago=0 : 오늘 날짜 (현재 시각에 따라 기사가 없을 수 있음)
    # days_ago=5 : 5일 전 날짜 (확실히 기사가 있을 만한 과거 날짜로 테스트)
    
    test_days_ago = 5 # 5일 전으로 테스트하여 데이터 수집 여부 확인
    
    print(f"==================================================")
    print(f"테스트 시작: {test_days_ago}일 전 기사 수집 시도")
    print(f"==================================================")
    
    try:
        # newsclipping_thebell.py 파일의 run 함수 호출
        df_result = newsclipping_thebell.run(params={"days_ago": test_days_ago})
        
        # --- 2. 결과 분석 ---
        print("\n[ 최종 결과 ]")
        print(f"총 수집된 기사 수: {len(df_result)}개")
        
        if len(df_result) > 0:
            print("\n[ 수집된 데이터 샘플 (상위 5개) ]")
            print(df_result.head())
            # 디버깅 용으로 CSV 파일 저장
            df_result.to_csv("local_test_output.csv", index=False, encoding='utf-8-sig')
            print("\n데이터가 'local_test_output.csv'에 저장되었습니다.")
        else:
            print("\n🚨🚨🚨 로컬에서도 수집된 데이터가 0개입니다. 🚨🚨🚨")
            print("→ 원인 진단이 필요합니다.")
            
    except Exception as e:
        print(f"\n❌ 치명적인 오류 발생: {e}")

if __name__ == "__main__":
    main()
