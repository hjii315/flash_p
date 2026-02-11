# 기술 스택
Python, CrewAI, SQLite, Open AI API Key

# 코드 생성 워크플로우
1. 사용자가 요구사항 입력(입력/출력, 성공기준, 제약)
2. 코드 생성
3. 역설계 문서 생성(Module map / Data flow / Invariants / Failure modes)
4. 초보자 비유 설명 생성 (현실 비유/코드매핑/필요성/한계)
5. 설명 검증/반박(오류/누락/가정 탐지)
6-1. 문제 없으면 퀴즈 생성
6-2. 수정 반영(코드/문서/설명 업데이트) 후 퀴즈 생성
7. 저장(SQLite + 로컬 폴더 파일)