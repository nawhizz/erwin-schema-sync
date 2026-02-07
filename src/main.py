import argparse
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from src.db_client import OracleClient
from src.erwin_client import ErwinClient


def load_tables_from_file(file_path: str) -> list:
    """파일에서 테이블 목록을 읽어옴 (한 줄에 하나의 테이블명)"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Table list file not found: {file_path}")
    
    tables = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 공백 제거 및 빈 줄/주석 무시
            table_name = line.strip()
            if table_name and not table_name.startswith('#'):
                tables.append(table_name)
    
    return tables


def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Oracle to Erwin Schema Sync Tool")
    parser.add_argument("--table", "-t", action="append", help="Target Oracle Table Name (can be specified multiple times)")
    parser.add_argument("--file", "-f", help="Path to file containing table names (one per line)")
    parser.add_argument("--conn", "-c", help="Oracle Connection String (or set ORACLE_CONNECTION_STRING env)")
    parser.add_argument("--owner", "-o", help="Table Owner/Schema (Optional)")
    parser.add_argument("--area", "-a", default="General", help="Erwin Subject Area (Optional, Default: General)")
    parser.add_argument("--model", "-m", help="Path to Erwin model file (.erwin) to open if not attached")
    
    args = parser.parse_args()
    
    # 테이블 목록 수집
    tables = []
    if args.table:
        tables.extend(args.table)
    if args.file:
        try:
            tables.extend(load_tables_from_file(args.file))
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    if not tables:
        print("Error: At least one table must be specified via --table or --file.")
        sys.exit(1)
    
    print(f"Tables to sync: {', '.join(tables)} ({len(tables)} total)")
    
    conn_str = args.conn or os.getenv("ORACLE_CONNECTION_STRING")
    if not conn_str:
        print("Error: Oracle connection string must be provided via argument or env var.")
        sys.exit(1)
        
    try:
        # [CRITICAL] Erwin 연결을 먼저 수행해야 함 (COM vs OracleDB 충돌 방지)
        print("Connecting to Erwin...")
        erwin_client = ErwinClient()
        try:
            erwin_client.connect(model_path=args.model)
        except Exception as e:
            print(f"Error connecting to Erwin: {e}")
            sys.exit(1)

        # Oracle 클라이언트 초기화
        db_client = OracleClient(conn_str)
        
        success_count = 0
        fail_count = 0
        
        try:
            for table_name in tables:
                print(f"\n{'='*50}")
                print(f"Processing table: {table_name}")
                print('='*50)
                
                try:
                    # Oracle Schema 조회
                    table_schema = db_client.get_table_schema(table_name, args.owner)
                    print(f"Found table '{table_schema.name}' with {len(table_schema.columns)} columns.")
                    
                    # Erwin 업데이트
                    erwin_client.create_or_update_entity(table_schema, args.area)
                    print(f"[SUCCESS] Synced '{table_name}' to Erwin.")
                    success_count += 1
                    
                except Exception as e:
                    print(f"[FAILED] Error processing '{table_name}': {e}")
                    fail_count += 1
                    continue
                    
        finally:
            db_client.close()
        
        # 결과 요약
        print(f"\n{'='*50}")
        print("SYNC COMPLETE")
        print('='*50)
        print(f"  Success: {success_count}")
        print(f"  Failed:  {fail_count}")
        print(f"  Total:   {len(tables)}")

    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(0)

if __name__ == "__main__":
    main()
