import os
import openai
import json
import random

# 🚨 새 API 키로 변경 필수
from dotenv import load_dotenv

load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

categories = [
    "일상 생활", "비즈니스/업무", "해외 여행", "학술/토론", "취업/인터뷰",
    "식당/카페", "쇼핑/고객 서비스", "병원/건강", "사교/네트워킹", 
    "취미/여가 생활", "IT/기술 지원", "긴급 상황/사건 사고"
]
levels = ["초급 (Beginner)", "중급 (Intermediate)", "고급 (Advanced)"]
grammars = [
    "시제", "수일치", "의문문(간접/부가 의문문 포함)", "관계대명사", "가정법", 
    "관사", "전치사", "수동태", "명사절", "부사절", 
    "형용사절", "비교급과 최상급", "조동사", "분사(현재/과거분사)", "접속사", 
    "관계부사", "명령문", "간접화법", "조건문", "동명사와 TO부정사", 
    "대명사", "도치 및 강조"
]

def generate_question_data(count=10, repeat=10):
    for r in range(repeat):
        print(f"🔄 [진행 상황] {r+1}/{repeat} 회차 호출 중... ({count}개 생성)")
        
        conditions = []
        for _ in range(count):
            conditions.append({
                "category": random.choice(categories),
                "level": random.choice(levels),
                "grammar": random.choice(grammars)
            })
            
        system_prompt = "너는 영어 교육용 문제를 출제하는 전문 출제위원이야."
        
        # 🌟 핵심 프롬프트: 배열 기호([]) 금지, 한 줄 JSONL 강제, key_vocabulary 통일
        user_prompt = f"""
        다음 {count}개의 조건 리스트에 맞춰서 각각 1개씩, 총 {count}개의 영어작문 문제를 생성해줘.
        
        [조건 리스트]
        {json.dumps(conditions, ensure_ascii=False, indent=2)}
        
        [출력 형식 및 엄격한 규칙]
        1. 전체를 배열 기호([ ])로 절대 감싸지 마.
        2. 객체와 객체 사이에 콤마(,)를 쓰지 마.
        3. 마크다운 기호(```json 등)나 인사말을 절대 쓰지 마.
        4. 반드시 한 줄에 하나의 완벽한 JSON 객체만 출력하고 줄바꿈(\n) 해.
        5. 'key_vocabulary'는 반드시 [["단어", "뜻"], ["단어", "뜻"]] 형태의 리스트 배열로 통일해.
        
        [정확한 출력 예시 (이 형태 그대로 {count}줄 출력)]
        {{"instruction": "유저의 레벨과 요청된 주제에 맞춰...", "input": {{"category": "식당/카페", "level": "초급 (Beginner)", "target_grammar": "관사"}}, "output": {{"situation": "...", "korean_sentence": "...", "english_answer": "...", "key_vocabulary": [["apple", "사과"]], "grading_points": "...", "error_points": "..."}}}}
        {{"instruction": "유저의 레벨과 요청된 주제에 맞춰...", "input": {{"category": "해외 여행", "level": "중급 (Intermediate)", "target_grammar": "수동태"}}, "output": {{"situation": "...", "korean_sentence": "...", "english_answer": "...", "key_vocabulary": [["distribute", "배포하다"]], "grading_points": "...", "error_points": "..."}}}}
        """

        try:
            # json_object 모드를 끄고 순수 텍스트로 받아야 완벽한 JSONL이 나옵니다.
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7 # 약간의 안정성을 위해 0.7로 조정
            )

            raw_text = response.choices[0].message.content.strip()
            
            # 혹시 모를 마크다운(```json, ```jsonl 등) 찌꺼기 제거
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1].rsplit("\n", 1)[0]

            lines = raw_text.split('\n')
            success_count = 0
            
            # 실시간 파일 쓰기 (Append 모드)
            with open("question_gen_data_final.jsonl", "a", encoding="utf-8") as f:
                for line in lines:
                    line = line.strip()
                    # 빈 줄이나 괄호만 있는 줄 등은 건너뜀
                    if not line or line in ["[", "]", ","]: 
                        continue
                        
                    # 끝에 콤마가 잘못 붙어있다면 제거
                    if line.endswith(","):
                        line = line[:-1]
                        
                    try:
                        # 완벽한 JSON인지 검증 후 저장
                        data = json.loads(line)
                        f.write(json.dumps(data, ensure_ascii=False) + "\n")
                        success_count += 1
                    except json.JSONDecodeError:
                        print(f"⚠️ 파싱 에러 (건너뜀): {line[:60]}...")
            
            print(f"✅ [{r+1}/{repeat}] 회차 완료: {success_count}개 정상 저장")
                    
        except Exception as e:
            print(f"❌ [{r+1}/{repeat}] 회차 에러 발생: {e}")
            continue

# ----------------------------------------------------
# 🌟 실행
# ----------------------------------------------------

# 시작 전 파일 초기화
open("question_gen_data_final.jsonl", "w", encoding="utf-8").close()

print("🚀 데이터 생성을 시작합니다...")
# 10개씩 10번 = 총 100개 (1000개를 원하면 repeat=100)
generate_question_data(count=10, repeat=10)

print("🎉 모든 생성이 완료되었습니다! question_gen_data_final.jsonl 파일을 확인하세요.")