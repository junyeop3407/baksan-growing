# 테스트 실행: 앱 폴더에서  bash tests/run.sh
# 컴퓨터마다 파이썬 명령이 달라서(Windows: py, Mac: python3) pytest가 깔린 것을 찾아 쓴다.
cd "$(dirname "$0")/.." || exit 1
for py in py python3 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import pytest" >/dev/null 2>&1; then
    exec "$py" -m pytest -q tests "$@"
  fi
done
echo "pytest가 설치된 파이썬을 찾지 못했습니다. 'py -m pip install -r requirements-dev.txt'로 설치해 주세요." >&2
exit 1
