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

    def find_entity_by_name(self, session, entity_name: str):
        """Physical Name으로 Entity 객체 검색
        
        Note: Logical Name(Name)은 Comment 값이 들어가므로, 
        중복 체크 시 Physical Name(Physical_Name)으로 검색해야 함.
        """
        model_objects = session.ModelObjects
        for obj in model_objects:
            try:
                if obj.ClassName == "Entity":
                    # Physical_Name 속성으로 검색
                    try:
                        physical_name = obj.Properties("Physical_Name").Value
                        if physical_name == entity_name:
                            return obj
                    except:
                        # Physical_Name이 없으면 Name으로 폴백
                        if obj.Name == entity_name:
                            return obj
            except:
                continue
        return None

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
            
            # 0. 중복 체크 및 삭제
            print(f"Checking for existing entity '{table_schema.name}'...")
            existing_entity = self.find_entity_by_name(session, table_schema.name)
            if existing_entity:
                print(f"  Found existing entity: {existing_entity.ObjectId}")
                print(f"  Deleting existing entity...")
                try:
                    model_objects.Remove(existing_entity.ObjectId)
                    print(f"  [SUCCESS] Deleted existing entity.")
                except Exception as del_err:
                    print(f"  [WARNING] Failed to delete existing entity: {del_err}")
            else:
                print("  No existing entity found.")
            
            # 1. Entity 생성 (문자열 클래스명 사용)
            print(f"Creating Entity using Add('Entity')...")
            erwin_entity = model_objects.Add("Entity")
            entity_id = erwin_entity.ObjectId
            print(f"Entity object created: {entity_id}")
            
            # 2. Entity 이름 설정 (Logical = Comment, Physical = DB Name)
            # Logical Name: Comment가 있으면 Comment, 없으면 DB 이름
            logical_name = table_schema.comment or table_schema.name
            physical_name = table_schema.name
            
            print(f"Setting Entity Names...")
            print(f"  Logical (Name): '{logical_name}'")
            print(f"  Physical (Physical_Name): '{physical_name}'")
            
            try:
                erwin_entity.Properties("Name").Value = logical_name
                print(f"  [SUCCESS] Logical Name set.")
            except Exception as e:
                print(f"  [FAIL] Could not set Logical Name: {e}")
            
            try:
                erwin_entity.Properties("Physical_Name").Value = physical_name
                print(f"  [SUCCESS] Physical Name set.")
            except Exception as e:
                print(f"  [FAIL] Could not set Physical Name: {e}")
            
            # 3. Attribute 추가 (Collect 메서드 사용!)
            print(f"\nAdding {len(table_schema.columns)} Attributes to Entity...")
            
            # Entity 하위 컬렉션 가져오기
            entity_children = model_objects.Collect(entity_id)
            
            # PK 설정을 위해 Attribute ObjectId 저장
            pk_attr_ids = {}
            
            for col in table_schema.columns:
                # Logical Name: Comment가 있으면 Comment, 없으면 컬럼명
                col_logical_name = col.comment or col.name
                col_physical_name = col.name
                
                print(f"  Adding Attribute: {col_physical_name}")
                try:
                    # Entity 하위 컬렉션에 Attribute 추가
                    attr = entity_children.Add("Attribute")
                    
                    # Logical Name (Name) 설정
                    try:
                        attr.Properties("Name").Value = col_logical_name
                        print(f"    Logical: '{col_logical_name}'")
                    except Exception as e:
                        print(f"    [FAIL] Logical Name: {e}")
                    
                    # Physical Name 설정
                    try:
                        attr.Properties("Physical_Name").Value = col_physical_name
                        print(f"    Physical: '{col_physical_name}'")
                    except Exception as e:
                        print(f"    [FAIL] Physical Name: {e}")
                    
                    # Physical Data Type 설정
                    try:
                        data_type = col.get_erwin_datatype()
                        attr.Properties("Physical_Data_Type").Value = data_type
                        print(f"    Physical DT: '{data_type}'")
                    except Exception as e:
                        print(f"    [FAIL] Physical Data Type: {e}")
                    
                    # Logical Data Type 설정
                    try:
                        logical_dtype = col.get_logical_datatype()
                        attr.Properties("Logical_Data_Type").Value = logical_dtype
                        print(f"    Logical DT: '{logical_dtype}'")
                    except Exception as e:
                        print(f"    [FAIL] Logical Data Type: {e}")
                    
                    # PK용 ObjectId 저장
                    if col.is_pk:
                        pk_attr_ids[col.name] = attr.ObjectId

                except Exception as attr_err:
                    print(f"    Failed to add attribute: {attr_err}")
            
            # 4. PK(Primary Key) 설정
            # PK 컬럼들을 모아서 Key_Group + Key_Group_Member로 구성
            pk_columns = [c for c in table_schema.columns if c.is_pk]
            if pk_columns:
                print(f"\nConfiguring Primary Key ({len(pk_columns)} columns)...")
                try:
                    # Key_Group 생성
                    kg = entity_children.Add("Key_Group")
                    kg.Properties("Name").Value = f"PK_{table_schema.name}"
                    kg.Properties("Key_Group_Type").Value = "PK"
                    print(f"  Key_Group created: PK_{table_schema.name}")
                    
                    # 각 PK 컬럼에 대해 Key_Group_Member 추가
                    kg_children = model_objects.Collect(kg.ObjectId)
                    for pk_col in pk_columns:
                        try:
                            # Attribute ObjectId 찾기
                            pk_attr_id = pk_attr_ids.get(pk_col.name)
                            if pk_attr_id:
                                member = kg_children.Add("Key_Group_Member")
                                member.Properties("Attribute_Ref").Value = pk_attr_id
                                print(f"  [PK] {pk_col.name}")
                        except Exception as e:
                            print(f"  [FAIL] PK member for {pk_col.name}: {e}")
                except Exception as e:
                    print(f"  [ERROR] Key_Group creation failed: {e}")

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
