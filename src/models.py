from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ColumnSchema:
    """오라클 컬럼 정보를 담는 데이터 클래스"""
    name: str
    data_type: str
    data_length: Optional[int]
    data_precision: Optional[int]
    data_scale: Optional[int]
    nullable: bool
    is_pk: bool
    comment: Optional[str]

    def get_erwin_datatype(self) -> str:
        """오라클 데이터 타입 → Erwin Physical 데이터 타입 (원본 유지)"""
        if "CHAR" in self.data_type:
            return f"{self.data_type}({self.data_length})"
        elif "NUMBER" in self.data_type:
            if self.data_precision:
                if self.data_scale:
                    return f"NUMBER({self.data_precision},{self.data_scale})"
                return f"NUMBER({self.data_precision})"
            return "NUMBER"
        return self.data_type

    def get_logical_datatype(self) -> str:
        """오라클 데이터 타입 → Erwin Logical 데이터 타입 (Oracle→Standard 변환)
        
        변환 규칙:
        - VARCHAR2 → VARCHAR
        - NVARCHAR2 → NVARCHAR
        - NUMBER → NUMERIC 또는 INTEGER (scale 따라)
        - 기타는 동일
        """
        if "VARCHAR2" in self.data_type:
            logical_type = self.data_type.replace("VARCHAR2", "VARCHAR")
            return f"{logical_type}({self.data_length})"
        elif "NVARCHAR2" in self.data_type:
            logical_type = self.data_type.replace("NVARCHAR2", "NVARCHAR")
            return f"{logical_type}({self.data_length})"
        elif "CHAR" in self.data_type:
            return f"{self.data_type}({self.data_length})"
        elif "NUMBER" in self.data_type:
            # NUMBER(p,0) 또는 precision만 있으면 INTEGER 계열로 변환 가능
            # 여기선 간단히 동일 형식 유지
            if self.data_precision:
                if self.data_scale and self.data_scale > 0:
                    return f"NUMERIC({self.data_precision},{self.data_scale})"
                return f"INTEGER"
            return "NUMERIC"
        elif self.data_type == "DATE":
            return "DATE"
        elif "TIMESTAMP" in self.data_type:
            return "TIMESTAMP"
        elif "CLOB" in self.data_type:
            return "TEXT"
        elif "BLOB" in self.data_type:
            return "BLOB"
        return self.data_type

@dataclass
class TableSchema:
    """테이블 전체 스키마 정보를 담는 데이터 클래스"""
    name: str
    columns: List[ColumnSchema]
    comment: Optional[str] = None
