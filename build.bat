@echo off
chcp 65001 > nul
rem 박산 키우기 exe 만들기: 이 파일을 더블클릭하거나 명령 창에서 build.bat 실행
rem 결과: dist\박산키우기.exe (Python이 없는 PC에서도 실행되는 파일 하나)
rem 자동으로 돌릴 때(끝에 멈추지 않게): build.bat nopause
cd /d "%~dp0"
set PY=py
where py > nul 2> nul || set PY=python
%PY% -m pip install -r requirements.txt || goto :fail
%PY% -m PyInstaller --onefile --windowed --clean --noconfirm --name 박산키우기 src\main.py || goto :fail
echo.
echo 완료: dist\박산키우기.exe
if /i not "%~1"=="nopause" pause
exit /b 0
:fail
echo 빌드에 실패했습니다. 위의 오류 메시지를 확인해 주세요.
if /i not "%~1"=="nopause" pause
exit /b 1
