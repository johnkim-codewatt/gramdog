import os
import openai
import json
import random
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


# (categories, levels, grammars 리스트는 기존과 동일하게 유지)

def generate_correct_tutor_data(count=10, repeat=20): 
    for r in range(repeat):
        print(f"🔄 [정답 칭찬 데이터] {r+1}/{repeat} 회차 생성 중... ({count}개씩)")
        
        conditions = []
        for _ in range(count):
            conditions.append({
                "category": random.choice(categories),
                "level": random.choice(levels),
                "grammar": random.choice(grammars)
            })
            
        system_prompt = "너는 고품질 LLM 학습 데이터를 생성하는 데이터 엔지니어이자, 유저를 기분 좋게 칭찬하는 긍정적인 영어 교육 전문가야."
        
        # 🌟 정답 전용 프롬프트
        user_prompt = f"""
        다음 {count}개의 조건 리스트에 맞춰서 각각 1개씩, 총 {count}개의 '유저가 완벽한 정답을 제출한 상황'의 영어 피드백 데이터를 생성해줘.
        
        [조건 리스트]
        {json.dumps(conditions, ensure_ascii=False, indent=2)}
        
        [상황 설정 - 매우 중요]
        1. 유저가 주어진 문법(target_grammar)을 활용하여 에러 하나 없이 '완벽한 영작 문장(user_answer)'을 만들어낸 상황.
        2. 하지만 과거에는 이 문법을 자주 틀렸던 이력(error_history)이 있을수 있음.
        
        [출력 형식 및 엄격한 규칙]
        1. 전체를 배열 기호([ ])로 절대 감싸지 마.
        2. 객체 사이에 콤마(,) 금지.
        3. 반드시 한 줄에 하나의 완벽한 JSON 객체만 출력하고 줄바꿈(\n) 해.
        4. 칭찬 멘트(tutor_feedback)가 매번 똑같지 않도록, 과거 이력을 구체적으로 언급하며 다양하게 작성해.
        
        [정확한 출력 예시 (이 형태 그대로 {count}줄 출력)]
        {{"instruction": "너는 친절하고 전문적인 AI 영어 튜터야. 사용자의 레벨과 과거 오답 이력을 참고하여 상세한 피드백을 제공해줘.", "input": {{"category": "식당/카페", "level": "초급 (Beginner)", "target_grammar": "관사", "user_answer": "I would like a cup of coffee.", "error_history": "과거에 셀 수 있는 명사 앞에 관사(a/an)를 빼먹는 실수를 자주 했음"}}, "output": {{"correction": "I would like a cup of coffee.", "explanation": "문법적으로 완벽한 문장입니다! 'cup'과 같은 셀 수 있는 단수 명사 앞에 부정관사 'a'를 아주 정확하게 사용하셨어요.", "tutor_feedback": "와, 완벽해요! 예전에는 관사를 자주 놓치셨는데, 이제 완벽하게 감을 잡으셨네요. 정말 자랑스럽습니다!"}}}}
        """

        try:
            # 🌟 비용 절감을 위해 똑똑한 mini 모델 사용!
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8
            )

            raw_text = response.choices[0].message.content.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1].rsplit("\n", 1)[0]

            lines = raw_text.split('\n')
            
            # 🌟 기존 파일에 그대로 이어서 씁니다 (Append)
            with open("tutor_finetuning_data_1000.jsonl", "a", encoding="utf-8") as f:
                for line in lines:
                    line = line.strip()
                    if not line or line in ["[", "]", ","]: continue
                    if line.endswith(","): line = line[:-1]
                        
                    try:
                        data = json.loads(line)
                        f.write(json.dumps(data, ensure_ascii=False) + "\n")
                    except json.JSONDecodeError:
                        continue
            
            print(f"✅ [{r+1}/{repeat}] 회차 완료!")
                    
        except Exception as e:
            print(f"❌ 에러 발생: {e}")
            continue

# ----------------------------------------------------
# 🌟 실행 부분
# ----------------------------------------------------
print("🚀 정답(칭찬) 데이터 200개 추가 생성을 시작합니다...")

# 10개씩 20번 = 200개 (mini 모델이라 순식간에 끝납니다!)
generate_correct_tutor_data(count=10, repeat=20)

print("🎉 드디어 1,000개의 황금비율 데이터가 모두 완성되었습니다!")