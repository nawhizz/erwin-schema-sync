# Erwin Schema Sync

Oracle 데이터베이스의 테이블 스키마 정보를 Erwin Data Modeler로 동기화하는 Python CLI 도구입니다.

## 기능

- Oracle 데이터베이스에서 테이블 및 컬럼 정보 추출
- Erwin Data Modeler (7.3+)에 Entity 및 Attribute 자동 생성
- COM API를 통한 Erwin과의 직접 연동

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
ORACLE_USER=your_username
ORACLE_PASSWORD=your_password
ORACLE_DSN=localhost:1521/ORCL
```

## 사용법

```bash
# 단일 테이블 동기화
uv run src/main.py --table EMP --model "path/to/model.erwin"

# 여러 테이블 동기화 (개별 지정)
uv run src/main.py --table EMP --table DEPT --model "path/to/model.erwin"

# 파일에서 테이블 목록 읽어서 동기화
uv run src/main.py --file tables.txt --model "path/to/model.erwin"

# 혼합 사용 가능
uv run src/main.py --table EMP --file tables.txt --model "path/to/model.erwin"
```

### 테이블 목록 파일 형식 (tables.txt)

```
# 주석은 # 으로 시작
EMP
DEPT
SALGRADE
```

## 프로젝트 구조

```
erwin-schema-sync/
├── src/
│   ├── __init__.py
│   ├── main.py          # CLI 진입점
│   ├── db_client.py     # Oracle DB 클라이언트
│   ├── erwin_client.py  # Erwin COM 클라이언트
│   └── models.py        # 데이터 모델 (TableSchema, ColumnSchema)
├── .env                 # 환경 변수 (Oracle 접속 정보)
├── pyproject.toml       # 프로젝트 설정
└── README.md
```

## 주요 구현 사항

### Erwin COM API 연동

Erwin SCAPI를 통해 모델 객체를 생성합니다:

```python
# Entity 생성
entity = session.ModelObjects.Add("Entity")
entity.Properties("Name").Value = "EMP"

# Attribute 생성 (Entity 하위에 추가)
entity_children = session.ModelObjects.Collect(entity.ObjectId)
attr = entity_children.Add("Attribute")
attr.Properties("Name").Value = "EMPNO"
```

### 핵심 발견

| 문제 | 원인 | 해결 |
|------|------|------|
| "Name is read only" | GUID 클래스 ID 사용 | **문자열** "Entity" 사용 |
| "cannot be child of Model" | Attribute를 Model에 직접 추가 | `Collect(entityId).Add()` 사용 |

## 라이선스

Private
