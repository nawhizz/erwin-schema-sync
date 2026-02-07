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
        """오라클 데이터 타입을 Erwin 데이터 타입 문자열로 변환 (기본 매핑)"""
        # TODO: 더 정교한 매핑 필요
        if "CHAR" in self.data_type:
            return f"{self.data_type}({self.data_length})"
        elif "NUMBER" in self.data_type:
            if self.data_precision:
                if self.data_scale:
                    return f"NUMBER({self.data_precision},{self.data_scale})"
                return f"NUMBER({self.data_precision})"
            return "NUMBER"
        # 필요한 경우 추가 매핑 작성
        return self.data_type

@dataclass
class TableSchema:
    """테이블 전체 스키마 정보를 담는 데이터 클래스"""
    name: str
    columns: List[ColumnSchema]
    comment: Optional[str] = None
