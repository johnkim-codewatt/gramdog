import os
import json

def get_connection():
    import psycopg2
    from dotenv import load_dotenv
    
    # Load .env from parent directory
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    return psycopg2.connect(database_url)

def insert_wikibooks_grammar():
    # 1. DB 초기화 (테이블 생성)
    from database import init_db
    init_db()
    
    # 2. JSON 파일 읽기
    json_path = os.path.join(os.path.dirname(__file__), "wikibooks_grammar.json")
    with open(json_path, "r", encoding="utf-8") as f:
        rules = json.load(f)
        
    conn = get_connection()
    cur = conn.cursor()
    
    inserted_count = 0
    updated_count = 0
    
    for rule in rules:
        try:
            # ON CONFLICT 문을 사용하여 tag_id가 이미 존재하면 업데이트 (book_name, author 포함)
            cur.execute("""
                INSERT INTO grammar_rules (
                    book_name, author, tag_id, category, rule_name, 
                    core_formula, checklist, wrong_example, correct_example, original_description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tag_id) DO UPDATE SET
                    book_name = EXCLUDED.book_name,
                    author = EXCLUDED.author,
                    category = EXCLUDED.category,
                    rule_name = EXCLUDED.rule_name,
                    core_formula = EXCLUDED.core_formula,
                    checklist = EXCLUDED.checklist,
                    wrong_example = EXCLUDED.wrong_example,
                    correct_example = EXCLUDED.correct_example,
                    original_description = EXCLUDED.original_description
                RETURNING (xmax = 0) AS is_insert;
            """, (
                "Wikibooks English Grammar",
                "Wikibooks Contributors",
                rule.get("tag_id"),
                rule.get("category"),
                rule.get("rule_name"),
                rule.get("core_formula"),
                json.dumps(rule.get("checklist", [])), # JSONB 필드용
                rule.get("wrong_example"),
                rule.get("correct_example"),
                rule.get("original_description")
            ))
            
            is_insert = cur.fetchone()[0]
            if is_insert:
                inserted_count += 1
            else:
                updated_count += 1
                
        except Exception as e:
            print(f"Error inserting/updating rule {rule.get('tag_id')}: {e}")
            conn.rollback()
            continue
            
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"Successfully processed {len(rules)} rules.")
    print(f"Inserted: {inserted_count}, Updated: {updated_count}")

if __name__ == "__main__":
    print("Starting to insert Wikibooks Grammar rules into DB...")
    insert_wikibooks_grammar()
