# Erwin Schema Sync

Oracle 데이터베이스의 테이블 스키마 정보를 Erwin Data Modeler로 동기화하는 Python CLI 도구입니다.

## 기능

- Oracle 데이터베이스에서 테이블 및 컬럼 정보 추출
- Erwin Data Modeler (7.3+)에 Entity 및 Attribute 자동 생성
- **Logical/Physical 이름 분리** (Oracle Comment → Logical Name)
- **데이터타입 동기화** (Physical: NUMBER, VARCHAR2 / Logical: INTEGER, VARCHAR)
- **Primary Key 자동 설정** (Entity 상단 Key Area에 표시)
- **중복 엔티티 자동 삭제 후 재생성**
- 여러 테이블 일괄 처리 지원

## 요구 사항

- Python 3.10+ (32-bit, Erwin COM 호환을 위해)
- Erwin Data Modeler 7.3 이상
- Oracle Database 접근 가능한 계정

## 설치

```bash
# uv 사용 (권장)
uv sync

# 또는 pip 사용
pip install -e .
```

## 환경 설정

`.env` 파일에 Oracle 접속 정보를 설정합니다:

```env
ORACLE_CONNECTION_STRING=user/password@host:port/service_name

# 선택: Oracle Instant Client 경로 (Thick 모드용)
# ORACLE_CLIENT_PATH=C:\oracle\instantclient_21_32bit
```

### 환경 변수 설명

| 변수 | 필수 | 설명 |
|------|------|------|
| `ORACLE_CONNECTION_STRING` | ✅ | Oracle 접속 문자열 (Easy Connect 형식) |
| `ORACLE_CLIENT_PATH` | ❌ | Oracle Instant Client 경로 (32-bit 필수) |

### Thick 모드 vs Thin 모드

| 모드 | 필요 조건 | 장점 |
|------|----------|------|
| Thin | 없음 (순수 Python) | 설치 간편, 대부분 기능 작동 |
| Thick | Oracle Instant Client (32-bit) | 모든 Oracle 기능 지원 |

- `ORACLE_CLIENT_PATH`가 **설정되지 않으면** → 시스템 PATH에서 Oracle Client 자동 탐색
- **32-bit Oracle Client가 없으면** → 자동으로 Thin 모드로 폴백


## 사용법

```bash
# 단일 테이블 동기화
uv run src/main.py --table EMP --model "path/to/model.erwin"

# 여러 테이블 동기화 (개별 지정)
uv run src/main.py --table EMP --table DEPT --model "path/to/model.erwin"

# 파일에서 테이블 목록 읽어서 동기화
uv run src/main.py --file tables.txt --model "path/to/model.erwin"
```

### 테이블 목록 파일 형식 (tables.txt)

```
# 주석은 # 으로 시작
EMP
DEPT
SALGRADE
```

## 동기화 규칙

### Logical / Physical 이름

| 구분 | Erwin 속성 | 값 |
|------|------------|------|
| Entity Logical | `Name` | Oracle 테이블 Comment (예: 직원정보) |
| Entity Physical | `Physical_Name` | DB 테이블명 (예: EMP) |
| Attribute Logical | `Name` | Oracle 컬럼 Comment (예: 직원번호) |
| Attribute Physical | `Physical_Name` | DB 컬럼명 (예: EMPNO) |

> Comment가 없으면 DB 이름을 Logical에도 사용합니다.

### 데이터타입 변환

| Oracle 타입 | Physical (Erwin) | Logical (Erwin) |
|------------|-----------------|----------------|
| VARCHAR2(n) | VARCHAR2(n) | VARCHAR(n) |
| NUMBER(p,0) | NUMBER(p) | INTEGER |
| NUMBER(p,s) | NUMBER(p,s) | NUMERIC(p,s) |
| DATE | DATE | DATE |

### Primary Key

- Oracle PK 제약조건이 있는 컬럼은 자동으로 Erwin Key Area(상단)에 배치됩니다.
- `Key_Group` (Type=PK) + `Key_Group_Member` 방식으로 구성됩니다.

## 프로젝트 구조

```
erwin-schema-sync/
├── src/
│   ├── main.py          # CLI 진입점
│   ├── db_client.py     # Oracle DB 클라이언트
│   ├── erwin_client.py  # Erwin COM 클라이언트
│   └── models.py        # 데이터 모델
├── .env                 # Oracle 접속 정보
└── pyproject.toml
```

## 라이선스

Private
