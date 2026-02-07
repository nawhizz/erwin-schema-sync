import win32com.client
import os
from typing import Optional
from .models import TableSchema, ColumnSchema

class ErwinClient:
    def __init__(self):
        self.app = None
        self.persistence_units = None
        self.session = None

    def connect(self, model_path: Optional[str] = None):
        """Erwin 애플리케이션에 연결 (COM)"""
        from win32com.client import gencache
        import traceback
        import win32com.client
        
        target_pid = "AllFusionERwin.SCAPI"
        
        self.app = None
        print(f"Connecting to Erwin SCAPI using '{target_pid}'...")
        
        try:
            self.app = gencache.EnsureDispatch(target_pid)
            print(f"!!! SUCCESS !!! Connected via EnsureDispatch.")
            
        except Exception as e:
            print(f"EnsureDispatch failed: {e}")
            print("Retrying with standard Dispatch...")
            try:
                self.app = win32com.client.Dispatch(target_pid)
                print(f"!!! SUCCESS !!! Connected via Dispatch.")
            except Exception as dispatch_err:
                print(f"FATAL: Could not connect to Erwin. Error: {dispatch_err}")
                traceback.print_exc()
                raise dispatch_err

        if self.app:
            try:
                self.persistence_units = self.app.PersistenceUnits
                count = 0
                try:
                    count = self.persistence_units.Count
                    print(f"Persistence Units Count: {count}")
                except Exception as e:
                    print(f"Warning: Could not read PersistenceUnits.Count: {e}")

                if model_path:
                    abs_path = os.path.abspath(model_path)
                    if not os.path.exists(abs_path):
                        raise FileNotFoundError(f"Model file not found: {abs_path}")
                        
                    print(f"Attempting to open model file: {abs_path}")
                    try:
                        self.persistence_units.Add(abs_path)
                        print("Model opened successfully.")
                    except Exception as open_err:
                        print(f"Failed to open model via Add(path): {open_err}")
                        raise open_err
                elif count == 0:
                     print("Warning: No model is open and no --model argument provided.")

            except Exception as post_connect_err:
                print(f"Error after connection: {post_connect_err}")
                traceback.print_exc()
                raise post_connect_err


    def get_active_model(self):
        """활성화된 모델(Persistence Unit) 반환"""
        if not self.persistence_units or self.persistence_units.Count == 0:
            raise ValueError("No open models found in Erwin.")
        
        return self.persistence_units.Item(0)

    def create_or_update_entity(self, table_schema: TableSchema, area_name: str = "General"):
        """테이블 스키마를 기반으로 Erwin 엔티티 생성 또는 업데이트
        
        핵심:
        - Entity 생성: session.ModelObjects.Add("Entity")
        - Attribute 생성: session.ModelObjects.Collect(entityId).Add("Attribute")
        """
        if not self.app:
            self.connect()

        model = self.get_active_model()
        
        # 세션 생성 (Level 0 = Model Level)
        session = self.app.Sessions.Add()
        session.Open(model, 0)
        self.session = session
        
        # 트랜잭션 시작
        txn_id = session.BeginTransaction()
        
        try:
            print(f"Processing Entity: {table_schema.name}...")
            
            model_objects = session.ModelObjects
            
            # 1. Entity 생성 (문자열 클래스명 사용)
            print(f"Creating Entity using Add('Entity')...")
            erwin_entity = model_objects.Add("Entity")
            entity_id = erwin_entity.ObjectId
            print(f"Entity object created: {entity_id}")
            
            # 2. Entity 이름 설정
            print(f"Setting Entity Name to '{table_schema.name}'...")
            try:
                erwin_entity.Properties("Name").Value = table_schema.name
                print(f"  [SUCCESS] Entity Name set to: {table_schema.name}")
            except Exception as e:
                print(f"  [FAIL] Could not set Name: {e}")
            
            # 3. Attribute 추가 (Collect 메서드 사용!)
            # Entity의 하위 객체 컬렉션을 가져와서 Attribute 추가
            print(f"\nAdding {len(table_schema.columns)} Attributes to Entity...")
            
            # Entity 하위 컬렉션 가져오기
            entity_children = model_objects.Collect(entity_id)
            
            for col in table_schema.columns:
                print(f"  Adding Attribute: {col.name}")
                try:
                    # Entity 하위 컬렉션에 Attribute 추가
                    attr = entity_children.Add("Attribute")
                    
                    # Attribute 이름 설정
                    try:
                        attr.Properties("Name").Value = col.name
                        print(f"    [SUCCESS] Attribute Name: {col.name}")
                    except Exception as e:
                        print(f"    [FAIL] Could not set Attribute Name: {e}")

                except Exception as attr_err:
                    print(f"    Failed to add attribute: {attr_err}")

            session.CommitTransaction(txn_id)
            print("\nTransaction Committed.")
            
            # 세션 종료
            session.Close()
            
            # 모델 파일에 저장 (중요!)
            print("Saving model to file...")
            model.Save()
            print("Model saved successfully.")

        except Exception as e:
            print(f"Error during entity creation: {e}")
            session.RollbackTransaction(txn_id)
            session.Close()
            raise
