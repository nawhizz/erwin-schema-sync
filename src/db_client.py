import oracledb
import os
from typing import Optional
from .models import TableSchema, ColumnSchema

class OracleClient:
    def __init__(self, connection_string: str = None):
        """
        초기화
        :param connection_string: user/password@host:port/service_name 형태 또는 적절한 DSN
        """
        self.conn = None
        self.connection_string = connection_string or os.getenv("ORACLE_CONNECTION_STRING")

    def connect(self):
        """데이터베이스 연결"""
        if not self.connection_string:
            raise ValueError("Connection string is required")
        
        # Thick 모드 활성화 (Oracle Client 32bit 사용 요청 반영)
        try:
            # 이미 초기화되었는지 확인 (전역적으로 한 번만 호출 가능)
            if not getattr(oracledb, "__initialized__", False):
                # 필요시 lib_dir 파라미터로 클라이언트 경로 지정 가능
                client_path = os.getenv("ORACLE_CLIENT_PATH")
                if client_path:
                    oracledb.init_oracle_client(lib_dir=client_path)
                else:
                    oracledb.init_oracle_client()
                
                oracledb.__initialized__ = True
                print("Oracle Client (Thick mode) initialized.")
        except Exception as e:
            print(f"Warning: Failed to initialize Oracle Client (Thick mode): {e}")
            print("Falling back to Thin mode (if possible) or ensure Oracle Client is installed and in PATH.")

        try:
            self.conn = oracledb.connect(self.connection_string)
            print("Successfully connected to Oracle Database")
        except oracledb.Error as e:
            print(f"Error connecting to Oracle: {e}")
            raise

    def close(self):
        """연결 종료"""
        if self.conn:
            self.conn.close()

    def get_table_schema(self, table_name: str, owner: Optional[str] = None) -> TableSchema:
        """
        테이블 스키마 정보 조회
        :param table_name: 조회할 테이블 명
        :param owner: 스키마 소유자 (옵션), 없으면 user_tables 등에서 조회
        :return: TableSchema 객체
        """
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        table_upper = table_name.upper()
        
        # 1. 컬럼 기본 정보 및 코멘트 조회
        # ALL_TAB_COLUMNS와 ALL_COL_COMMENTS 조인
        # owner 조건이 있으면 추가, 없으면 현재 접속된 유저 기준(USER_tab_columns) 등을 고려할 수 있으나
        # 여기서는 ALL_ 뷰를 사용하고, 필요시 필터링
        
        query_cols = """
            SELECT 
                tc.COLUMN_NAME,
                tc.DATA_TYPE,
                tc.DATA_LENGTH,
                tc.DATA_PRECISION,
                tc.DATA_SCALE,
                tc.NULLABLE,
                cc.COMMENTS
            FROM ALL_TAB_COLUMNS tc
            LEFT JOIN ALL_COL_COMMENTS cc
                ON tc.OWNER = cc.OWNER
                AND tc.TABLE_NAME = cc.TABLE_NAME
                AND tc.COLUMN_NAME = cc.COLUMN_NAME
            WHERE tc.TABLE_NAME = :tn
        """
        params = {"tn": table_upper}
        if owner:
            query_cols += " AND tc.OWNER = :owner"
            params["owner"] = owner.upper()
        
        query_cols += " ORDER BY tc.COLUMN_ID"
        
        cursor.execute(query_cols, params)
        rows = cursor.fetchall()
        
        if not rows:
            raise ValueError(f"Table '{table_upper}' not found or no columns retrieved.")

        # 2. PK 정보 조회
        query_pk = """
            SELECT acc.COLUMN_NAME
            FROM ALL_CONSTRAINTS ac
            JOIN ALL_CONS_COLUMNS acc
                ON ac.OWNER = acc.OWNER
                AND ac.CONSTRAINT_NAME = acc.CONSTRAINT_NAME
            WHERE ac.TABLE_NAME = :tn
                AND ac.CONSTRAINT_TYPE = 'P'
        """
        pk_params = {"tn": table_upper}
        if owner:
            query_pk += " AND ac.OWNER = :owner"
            pk_params["owner"] = owner.upper()
            
        cursor.execute(query_pk, pk_params)
        pk_rows = cursor.fetchall()
        pk_columns = {row[0] for row in pk_rows}
        
        # 3. 테이블 코멘트 조회
        query_tab_comment = """
            SELECT COMMENTS
            FROM ALL_TAB_COMMENTS
            WHERE TABLE_NAME = :tn
        """
        tab_params = {"tn": table_upper}
        if owner:
            query_tab_comment += " AND OWNER = :owner"
            tab_params["owner"] = owner.upper()
            
        cursor.execute(query_tab_comment, tab_params)
        tab_comment_row = cursor.fetchone()
        table_comment = tab_comment_row[0] if tab_comment_row else None

        columns = []
        for row in rows:
            col_name = row[0]
            data_type = row[1]
            data_length = row[2]
            data_precision = row[3]
            data_scale = row[4]
            nullable = (row[5] == 'Y')
            comment = row[6]
            is_pk = col_name in pk_columns
            
            columns.append(ColumnSchema(
                name=col_name,
                data_type=data_type,
                data_length=data_length,
                data_precision=data_precision,
                data_scale=data_scale,
                nullable=nullable,
                is_pk=is_pk,
                comment=comment
            ))

        cursor.close()
        
        return TableSchema(
            name=table_upper,
            columns=columns,
            comment=table_comment
        )
