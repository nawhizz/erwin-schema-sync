"""Erwin Key_Group 방식으로 PK 설정 테스트"""
import win32com.client
from win32com.client import gencache
import traceback

def test():
    log_file = r"D:\Projects\On\erwin-schema-sync\test_pk.log"
    with open(log_file, 'w', encoding='utf-8') as f:
        def log(msg):
            print(msg)
            f.write(msg + "\n")
            f.flush()
        
        log("=== Key_Group PK Test ===")
        
        try:
            app = gencache.EnsureDispatch("AllFusionERwin.SCAPI")
            model_path = r"D:\Projects\On\erwin-schema-sync\test.erwin"
            
            if app.PersistenceUnits.Count > 0:
                pu = app.PersistenceUnits.Item(0)
            else:
                pu = app.PersistenceUnits.Add(model_path)
            
            session = app.Sessions.Add()
            session.Open(pu, 0)
            txn = session.BeginTransaction()
            
            mobjs = session.ModelObjects
            
            # 1. Entity 생성
            entity = mobjs.Add("Entity")
            entity.Properties("Name").Value = "TEST_PK"
            entity.Properties("Physical_Name").Value = "TEST_PK"
            entity_id = entity.ObjectId
            log(f"Entity: {entity_id}")
            
            # 2. Attribute 생성
            attr = mobjs.Collect(entity_id).Add("Attribute")
            attr.Properties("Name").Value = "ID"
            attr.Properties("Physical_Name").Value = "ID"
            attr_id = attr.ObjectId
            log(f"Attribute: {attr_id}")
            
            # 3. Entity의 자식들 확인 (Key_Group 존재 여부)
            log("\nListing Entity children (ClassName)...")
            entity_children = mobjs.Collect(entity_id)
            for child in entity_children:
                try:
                    cn = child.ClassName
                    nm = child.Name if hasattr(child, 'Name') else "N/A"
                    log(f"  {cn}: {nm}")
                except Exception as e:
                    log(f"  Error: {e}")
            
            # 4. Key_Group 생성 시도
            log("\nCreating Key_Group...")
            try:
                kg = entity_children.Add("Key_Group")
                log(f"  Key_Group created: {kg.ObjectId}")
                
                # Key_Group 타입 설정
                log("  Setting Key_Group properties...")
                try:
                    kg.Properties("Name").Value = "PK_TEST"
                    log("    Name = PK_TEST")
                except Exception as e:
                    log(f"    Name failed: {e}")
                
                try:
                    kg.Properties("Key_Group_Type").Value = "PK"
                    log("    Key_Group_Type = PK")
                except Exception as e:
                    log(f"    Key_Group_Type failed: {e}")
                
                # 5. Key_Group_Member 추가
                log("\n  Adding Key_Group_Member...")
                kg_children = mobjs.Collect(kg.ObjectId)
                try:
                    member = kg_children.Add("Key_Group_Member")
                    log(f"    Member created: {member.ObjectId}")
                    
                    # Attribute 참조 설정
                    log("    Setting Attribute reference...")
                    
                    # 가능한 속성명 시도
                    ref_props = ["Attribute_Ref", "Key_Attribute", "Attribute", "Owned_By"]
                    for rp in ref_props:
                        try:
                            member.Properties(rp).Value = attr_id
                            log(f"    [OK] {rp} = {attr_id}")
                            break
                        except Exception as e:
                            log(f"    [FAIL] {rp}")
                            
                except Exception as e:
                    log(f"    Member creation failed: {e}")
                
            except Exception as e:
                log(f"  Key_Group creation failed: {e}")
            
            session.RollbackTransaction(txn)
            session.Close()
            log("\nRolled back. Done.")
            
        except Exception as e:
            log(f"ERROR: {e}")
            traceback.print_exc()
    
    print(f"Log: {log_file}")

if __name__ == "__main__":
    test()
