# reboot_macro.py
import time
from playwright.sync_api import sync_playwright

def run_reboot_macro():
    # 💡 자동화하고 싶은 앱들의 식별 키워드 리스트입니다.
    # 제공해주신 HTML 소스에 적힌 실제 앱 이름들을 바탕으로 구성했습니다.
    target_apps = [
        "codyssey_1_project ∙ main ∙ bot/app.py"
    ]

    with sync_playwright() as p:
        # 백그라운드 브라우저 가동
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state="auth.json")
        page = context.new_page()
        
        print("🌐 스트림릿 Community Cloud 대시보드 진입 중...")
        page.goto("https://share.streamlit.io/")
        
        # 페이지 전체 로딩 대기
        page.wait_for_load_state("networkidle")
        time.sleep(5) 
        
        # 리스트에 등록된 앱들을 하나씩 순서대로 처리합니다.
        for target_app in target_apps:
            print(f"\n========================================")
            print(f"🔍 🎯 타겟팅 앱: '{target_app}' 작업 시작")
            print(f"========================================")
            
            try:
                # 1. target_app 텍스트를 포함하고 있는 테이블 행(tr) 선별
                app_row = page.locator("tr").filter(has_text=target_app)
                
                # 목록에 앱이 없을 경우를 대비한 안전장치
                if app_row.count() == 0:
                    print(f"⚠️ '{target_app}' 앱을 화면 목록에서 찾을 수 없어 건너뜁니다.")
                    continue
                
                # 2. 해당 행 내부에서 고유 속성인 data-testid="app-menu"를 가진 3점 버튼 찾기
                kebab_menu = app_row.get_by_test_id("app-menu").first
                
                # 버튼이 보일 때까지 대기 후 클릭
                kebab_menu.wait_for(state="visible", timeout=10000)
                kebab_menu.click()
                print(f"📱 3점 메뉴 열기 성공.")
                time.sleep(2)
                
                # 3. 드롭다운 메뉴에서 'Reboot' 문구 클릭
                reboot_option = page.get_by_text("Reboot").first
                reboot_option.wait_for(state="visible", timeout=5000)
                reboot_option.click()
                print("🚀 [Reboot] 명령 전송 완료!")
                time.sleep(2)
                
                # 4. "정말 재부팅 하시겠습니까?" 최종 확인 모달창 대응
                confirm_button = page.locator("button:has-text('Reboot')").last
                if confirm_button.is_visible():
                    confirm_button.click()
                    print("✅ 재부팅 최종 확인 모달 승인 완료.")
                
                print(f"✨ '{target_app}' 앱 재부팅 시퀀스 정상 완료.")
                time.sleep(3)  # 다음 앱으로 넘어가기 전 브라우저 안정화 대기
                
            except Exception as e:
                print(f"❌ '{target_app}' 처리 중 오류 발생: {e}")
                # 어떤 앱에서 터졌는지 디버깅하기 쉽게 각각 스크린샷 파일명을 다르게 저장합니다.
                page.screenshot(path=f"error_{target_app}.png")
                print(f"📸 에러 화면을 'error_{target_app}.png'로 저장했습니다.")
                # 하나의 앱이 실패하더라도 나머지 앱들은 계속 시도하도록 continue 처리합니다.
                continue
                
        browser.close()
        print("\n🎉 모든 등록된 프로젝트의 자동화 매크로 작업이 종료되었습니다!")

if __name__ == "__main__":
    run_reboot_macro()
