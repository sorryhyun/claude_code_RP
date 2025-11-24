# ChitChats

Claude Code 설치만으로 사용 가능한 RP 툴입니다. (pro/max 구독 인증해주세요!)

## 기능

- **멀티 에이전트 대화** - 서로 다른 성격을 가진 여러 Claude Code 에이전트가 함께 채팅
- **HTTP 폴링** - 폴링을 통한 실시간 메시지 업데이트 (2초 간격)
- **에이전트 커스터마이징** - 프로필 사진이 있는 마크다운 파일을 통한 성격 구성
- **1:1 다이렉트 채팅** - 개별 에이전트와의 개인 대화
- **확장된 사고** - 에이전트 추론 과정 보기 (32K 사고 토큰)
- **JWT 인증** - 토큰 만료가 있는 안전한 비밀번호 기반 인증
- **속도 제한** - 모든 엔드포인트에 대한 무차별 대입 공격 방지

## 기술 스택

**백엔드:** FastAPI, SQLAlchemy (async), SQLite, Anthropic Claude SDK
**프론트엔드:** React, TypeScript, Vite, Tailwind CSS

## 빠른 시작

### 1. 종속성 설치

```bash
make install
```

### 1.5 클로드코드 설치 및 계정 인증

```bash
npm install -g @anthropic-ai/claude-code
```
로 설치 후, 로그인을 통해 구독중인 계정을 인증하면, 별도의 절차 없이 (make install만으로) 진행 가능합니다.

### 2. 인증 구성

```bash
make generate-hash  # 비밀번호 해시 생성
python -c "import secrets; print(secrets.token_hex(32))"  # JWT 시크릿 생성
cp .env.example .env  # API_KEY_HASH와 JWT_SECRET을 .env에 추가
```

자세한 내용은 [SETUP.md](SETUP.md)를 참조하세요.

### 3. 실행 및 접속

```bash
make dev
```

http://localhost:5173을 열고 비밀번호로 로그인하세요.

## 시뮬레이션 및 테스트

**시뮬레이션 실행:**
```bash
make simulate ARGS='-s "AI 윤리 논의" -a "alice,bob,charlie"'
# 또는 스크립트를 직접 사용:
# ./scripts/simulation/simulate_chatroom.sh -s "..." -a "..."
```

**에이전트 테스트:**
```bash
make test-agents ARGS='10 agent1 agent2 agent3'
```
또는
```bash
make evaluate-agents ARGS='--target-agent "프리렌" --evaluator "페른" --questions 2'
```
자세한 내용은 [SIMULATIONS.md](SIMULATIONS.md) 및 [SETUP.md](SETUP.md)를 참조하세요.

## 에이전트 구성

에이전트는 `agents/` 디렉토리의 폴더 기반 구조를 사용하여 구성됩니다:

```
agents/
  agent_name/
    ├── in_a_nutshell.md       # 간단한 정체성 요약 (3인칭)
    ├── characteristics.md      # 성격 특성 (3인칭)
    ├── recent_events.md       # 대화에서 자동 업데이트
    ├── anti_pattern.md        # 피해야 할 행동 (선택사항)
    ├── consolidated_memory.md # 부제가 있는 장기 기억 (선택사항)
    ├── memory_brain.md        # 메모리 브레인 구성 (선택사항)
    └── profile.*              # 선택적 프로필 사진 (png, jpg, jpeg, gif, webp, svg)
```

에이전트 폴더에 선택적 프로필 사진(png, jpg, jpeg, gif, webp, svg)을 추가하세요. 변경 사항은 재시작 없이 즉시 적용됩니다.

**도구 구성:** 에이전트 행동 가이드라인 및 디버그 설정은 `backend/config/tools/`의 YAML 파일을 통해 구성됩니다. 코드 변경 없이 가이드라인 버전을 전환하거나 디버그 로깅을 활성화할 수 있습니다. 자세한 내용은 [CLAUDE.md](CLAUDE.md)를 참조하세요.

## 명령어

```bash
make dev           # 전체 스택 실행
make install       # 종속성 설치
make stop          # 서버 중지
make clean         # 빌드 아티팩트 정리
```

## API

**인증:**
- `POST /auth/login` - 비밀번호로 로그인, JWT 토큰 반환
- `GET /auth/verify` - 현재 JWT 토큰 검증

**룸:**
- `POST /rooms` - 룸 생성
- `GET /rooms` - 모든 룸 목록
- `GET /rooms/{id}` - 룸 세부정보 가져오기
- `DELETE /rooms/{id}` - 룸 삭제

**에이전트:**
- `GET /agents` - 에이전트 목록
- `POST /agents` - 구성에서 에이전트 생성
- `GET /agents/{id}/direct-room` - 1:1 룸 가져오기
- `PATCH /agents/{id}` - 에이전트 페르소나 업데이트
- `GET /agents/{name}/profile-pic` - 에이전트 프로필 사진 가져오기

**메시지 및 폴링:**
- `GET /rooms/{id}/messages/poll?since_id={id}` - 새 메시지 폴링 (속도 제한: 60/분)
- `POST /rooms/{id}/messages/send` - 메시지 전송 및 에이전트 응답 트리거 (속도 제한: 30/분)
- `GET /rooms/{id}/chatting-agents` - 현재 응답 중인 에이전트 목록 가져오기 (속도 제한: 120/분)
- `DELETE /rooms/{id}/messages` - 모든 메시지 삭제 (관리자 전용)

전체 API 참조는 [backend/README.md](backend/README.md)를, 인증 세부정보는 [SETUP.md](SETUP.md)를 참조하세요.

## 배포

Vercel 프론트엔드 + ngrok 백엔드를 사용한 프로덕션 배포는 [SETUP.md](SETUP.md)를 참조하세요.

**배포 전략:**
- **백엔드:** ngrok 터널이 있는 로컬 머신 (또는 선택한 클라우드 호스팅)
- **프론트엔드:** Vercel (또는 다른 정적 호스팅)
- **CORS:** 백엔드 `.env`의 `FRONTEND_URL`을 통해 구성
- **인증:** 비밀번호/JWT 기반 ([SETUP.md](SETUP.md) 참조)

## 구성

**백엔드 `.env`:** `API_KEY_HASH` (필수), `JWT_SECRET` (필수), `USER_NAME`, `DEBUG_AGENTS`, `MEMORY_BY`, `MAX_THINKING_TOKENS`, `FRONTEND_URL`

**프론트엔드 `.env`:** `VITE_API_BASE_URL` (기본값: http://localhost:8000)

자세한 내용은 [SETUP.md](SETUP.md) 및 [backend/README.md](backend/README.md)를 참조하세요.
