import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 1. API 키 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# 2. 생성할 문법 카테고리 정의 (총 약 120개 타겟)
GRAMMAR_CATEGORIES = {
    "Tense": "현재, 과거, 미래, 진행, 완료시제 전반 (약 15개 태그)",
    "Modals_Subjunctive": "조동사(can, must 등) 및 가정법 과거/과거완료/혼합 (약 20개 태그)",
    "Verbals": "to부정사, 동명사, 분사(현재/과거분사, 분사구문) (약 20개 태그)",
    "Parts_of_Speech": "명사, 관사, 대명사, 형용사, 부사, 비교급 (약 25개 태그)",
    "Sentence_Structure": "문장 5형식, 수의 일치, 수동태, 도치, 강조 (약 20개 태그)",
    "Clauses_Conjunctions": "관계대명사/부사, 접속사, 전치사 (약 20개 태그)"
}

def generate_grammar_atlas():
    atlas_data = []
    
    print("🚀 Grammar Atlas 생성을 시작합니다...")

    for category, description in GRAMMAR_CATEGORIES.items():
        print(f"📦 카테고리 생성 중: {category}...")
        
        prompt = f"""
        너는 20년 경력의 영어 수석 교사이자 교육 콘텐츠 엔지니어이다.
        상용 AI 영어 튜터 서비스에서 사용할 '표준 문법 채점 가이드라인'을 구축해야 한다.

        [요구사항]
        1. 카테고리: {category} ({description})
        2. 각 문법 항목은 반드시 아래 JSON 규격을 지킬 것.
        3. 'checklist'는 AI가 유저의 문장을 검사할 때 쓸 아주 구체적인 논리적 검토 항목이어야 함.
        4. 한국인이 해당 문법에서 가장 자주 저지르는 실수를 'wrong_example'에 넣을 것.

        [JSON 규격 예시]
        {{
          "tag_id": "구체적인_영문_태그명",
          "category": "{category}",
          "rule_name": "한글 문법 명칭",
          "core_formula": "문법 공식 (예: had + p.p.)",
          "checklist": [
            "검토항목 1",
            "검토항목 2"
          ],
          "wrong_example": "틀린 예문",
          "correct_example": "맞는 예문"
        }}

        위 형식에 맞춰 {category}에 해당하는 마이크로 태그들을 배열(List) 형태로 최대한 상세히 생성해줘.
        """

        try:
            response = client.chat.completions.create(
                model="gpt-4o",  # 최상위 모델 사용 권장
                messages=[{"role": "system", "content": "You are a professional English grammar expert."},
                          {"role": "user", "content": prompt}],
                response_format={ "type": "json_object" } # JSON 모드 강제
            )
            
            # 응답 파싱
            content = json.loads(response.choices[0].message.content)
            
            # JSON 키값은 모델마다 다를 수 있으니 유연하게 처리
            items = content.get("items") or content.get(category) or list(content.values())[0]
            
            if isinstance(items, list):
                atlas_data.extend(items)
                print(f"✅ {category} 완료 ({len(items)}개 항목 추가됨)")
            
            # API 레이트 리밋 방지를 위해 잠시 대기
            time.sleep(2)

        except Exception as e:
            print(f"❌ {category} 생성 중 오류 발생: {e}")

    # 3. 결과 저장
    with open("grammar_atlas.json", "w", encoding="utf-8") as f:
        json.dump(atlas_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ 모든 작업 완료! 총 {len(atlas_data)}개의 문법 태그가 grammar_atlas.json에 저장되었습니다.")

if __name__ == "__main__":
    generate_grammar_atlas()