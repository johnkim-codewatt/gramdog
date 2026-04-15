import os
import openai
import json
import random

from dotenv import load_dotenv

load_dotenv()

# 🚨 제발... 새로 발급받은 안전한 키로 교체해서 쓰세요!
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


def generate_tutor_data(count=10, repeat=10):
    for r in range(repeat):
        print(f"🔄 [진행 상황] {r+1}/{repeat} 회차 호출 중... ({count}개 생성)")
        
        conditions = []
        for _ in range(count):
            conditions.append({
                "category": random.choice(categories),
                "level": random.choice(levels),
                "grammar": random.choice(grammars)
            })
            
        system_prompt = "너는 고품질 LLM 학습 데이터를 생성하는 데이터 엔지니어이자 영어 교육 전문가야."
        
        # 🌟 핵심 프롬프트: 10개 조건 전달 + 배열 기호 금지 + JSONL 강제
        user_prompt = f"""
        다음 {count}개의 조건 리스트에 맞춰서 각각 1개씩, 총 {count}개의 영어 튜터링 피드백 데이터를 생성해줘.
        
        [조건 리스트]
        {json.dumps(conditions, ensure_ascii=False, indent=2)}
        
        [상황 설정]
        유저가 만든 문장에서 주어진 문법(target_grammar) 실수가 발생했으며, 과거에도 비슷한 실수를 했던 이력이 있는 상황을 정교하게 가정해.
        
        [출력 형식 및 엄격한 규칙]
        1. 전체를 배열 기호([ ])로 절대 감싸지 마.
        2. 객체와 객체 사이에 콤마(,)를 쓰지 마.
        3. 마크다운 기호(```json 등)나 인사말을 절대 쓰지 마.
        4. 반드시 한 줄에 하나의 완벽한 JSON 객체만 출력하고 줄바꿈(\n) 해.
        5. 유연한 피드백 : 현대 영어에서 널리 허용되는 표현은 오답 처리하지 마. 오직 명백한 문법적, 뉘앙스적 오류만 교정해. (예를들어: Everyone 뒤에 singular 'their' 사용, 제한적 용법의 'which' 허용 등)"
        
        [정확한 출력 예시 (이 형태 그대로 {count}줄 출력)]
        {{"instruction": "너는 친절하고 전문적인 AI 영어 튜터야. 사용자의 레벨과 과거 오답 이력을 참고하여, 입력된 유저의 영작 문장을 교정하고 상세한 피드백을 제공해줘.", "input": {{"category": "식당/카페", "level": "초급 (Beginner)", "target_grammar": "관사", "user_answer": "유저의 틀린 영작 문장", "error_history": "이 유저가 과거에 범했던 관련 문법 실수 요약"}}, "output": {{"correction": "올바른 교정 문장", "explanation": "문법적 오류에 대한 상세한 한국어 설명", "tutor_feedback": "과거 오답 이력을 언급하며 유저를 격려하는 따뜻한 피드백"}}}}
        {{"instruction": "너는 친절하고 전문적인 AI 영어 튜터야. 사용자의 레벨과 과거 오답 이력을 참고하여, 입력된 유저의 영작 문장을 교정하고 상세한 피드백을 제공해줘.", "input": {{"category": "비즈니스/업무", "level": "중급 (Intermediate)", "target_grammar": "수동태", "user_answer": "유저의 틀린 영작 문장", "error_history": "이 유저가 과거에 범했던 관련 문법 실수 요약"}}, "output": {{"correction": "올바른 교정 문장", "explanation": "문법적 오류에 대한 상세한 한국어 설명", "tutor_feedback": "과거 오답 이력을 언급하며 유저를 격려하는 따뜻한 피드백"}}}}
        """

        try:
            # json_object 모드를 끄고 순수 텍스트(한 줄 나열)로 유도
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7 
            )

            raw_text = response.choices[0].message.content.strip()
            
            # 마크다운 찌꺼기 방어 로직
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1].rsplit("\n", 1)[0]

            lines = raw_text.split('\n')
            success_count = 0
            
            # append 모드로 실시간 저장
            with open("tutor_finetuning_data_1000.jsonl", "a", encoding="utf-8") as f:
                for line in lines:
                    line = line.strip()
                    if not line or line in ["[", "]", ","]: 
                        continue
                        
                    if line.endswith(","):
                        line = line[:-1]
                        
                    try:
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
# 🌟 실행 부분
# ----------------------------------------------------

# 시작 전 파일 초기화
# open("tutor_finetuning_data_1000.jsonl", "w", encoding="utf-8").close()

print("🚀 튜터(Tutor) 피드백 데이터 생성을 시작합니다...")

count = 10
repeat = 30
# 10개씩 100번 = 총 1,000개 추출!
generate_tutor_data(count, repeat)

print(f"🎉 {count * repeat}개의 데이터가 tutor_finetuning_data_1000.jsonl 파일로 완벽하게 저장되었습니다!")