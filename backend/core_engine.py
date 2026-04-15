import os
import yaml
from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from database import search_history, search_history_by_tag, save_history, get_grammar_rule_by_tag
from dotenv import load_dotenv
import requests
import json
import openai
import re
from pydantic import BaseModel, Field
from typing import Literal


load_dotenv()

# 프롬프트 YAML 로드 (prompts/prompts.yaml)
_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "prompts.yaml")
with open(_PROMPT_PATH, encoding="utf-8") as _f:
    PROMPTS = yaml.safe_load(_f)

# grammar_atlas.json 로드 (tag_id -> item 도식)
_ATLAS_PATH = os.path.join(os.path.dirname(__file__), "grammar_atlas.json")
with open(_ATLAS_PATH, encoding="utf-8") as _af:
    _GRAMMAR_ATLAS: Dict[str, dict] = {item["tag_id"]: item for item in json.load(_af)}

def _lookup_atlas(tag_id: str) -> str:
    """tag_id로 grammar_atlas 항목 조회 → 프롬프트용 압축 텍스트 반환. 없으면 빈 문자열."""
    item = _GRAMMAR_ATLAS.get(tag_id) # 사전에 캐싱해놓은 문법사전 데이터에서 tag_id 기준 항목 조회
    if not item:
        return ""
    checklist = "\n".join(f"  - {c}" for c in item.get("checklist", []))
    return (
        f"[담당 문법 기준: {item['rule_name']}]\n"
        f"핵심 공식: {item['core_formula']}\n"
        f"체크리스트:\n{checklist}\n"
        f"오답 예시: {item['wrong_example']}\n"
        f"정답 예시: {item['correct_example']}"
    )

def _lookup_grammar_db(tag_id: str) -> str:
    """tag_id로 DB의 grammar_rules 테이블에서 항목 조회 → 프롬프트용 압축 텍스트 반환. 없으면 빈 문자열."""
    item = get_grammar_rule_by_tag(tag_id)
    if not item:
        return ""
    
    checklist_data = item.get("checklist", [])
    if isinstance(checklist_data, str):
        try:
            checklist_data = json.loads(checklist_data)
        except:
            checklist_data = [checklist_data]
            
    checklist_str = "\n".join(f"  - {c}" for c in checklist_data) if checklist_data else "없음"
    
    return (
        f"[담당 문법 기준: {item['rule_name']}]\n"
        f"핵심 공식: {item['core_formula']}\n"
        f"체크리스트:\n{checklist_str}\n"
        f"오답 예시: {item['wrong_example']}\n"
        f"정답 예시: {item['correct_example']}\n"
        f"원문 요약: {item['original_description']}"
    )

# 노드별 모델 설정 (.env에서 즉시 스위칭 가능)
MODEL_MAIN = os.getenv("MODEL_MAIN", "gpt-4o-mini")
MODEL_GENERATE_QUESTION = os.getenv("MODEL_GENERATE_QUESTION", "gpt-4o-mini")
MODEL_GENERATE_REVIEW = os.getenv("MODEL_GENERATE_REVIEW", "gpt-4o-mini")
MODEL_VERIFY = os.getenv("MODEL_VERIFY", "gpt-4o-mini")

# 유저 설정에 따른 라우팅을 지원하는 기본 모델 설정
llm = ChatOpenAI(model=MODEL_MAIN, temperature=0.1)
CORRECTNESS_THRESHOLD = 8  # 정답 인정 기준 점수 (0~10)


# Runpod vLLM(OpenAI-compatible) 설정
# 예) https://xxxxx-8000.proxy.runpod.net/v1
RUNPOD_OPENAI_BASE_URL = os.getenv("RUNPOD_OPENAI_BASE_URL", "").strip()
RUNPOD_OPENAI_MODEL = os.getenv("RUNPOD_OPENAI_MODEL", "/workspace/artifacts/qwen_tutor_v2_final").strip()


def _normalize_base_url(base_url: str) -> str:
    base_url = (base_url or "").strip()
    if not base_url:
        return ""
    return base_url if base_url.endswith("/v1") else base_url.rstrip("/") + "/v1"


def _runpod_client() -> openai.OpenAI:
    base_url = _normalize_base_url(RUNPOD_OPENAI_BASE_URL)
    if not base_url:
        raise ValueError("RUNPOD_OPENAI_BASE_URL is not set (must include /v1 or will be normalized)")
    return openai.OpenAI(base_url=base_url, api_key="none")


def _call_runpod_chat(system_prompt: str, user_prompt: str, temperature: float = 0.0, max_tokens: int = 512) -> str:
    client = _runpod_client()
    resp = client.chat.completions.create(
        model=RUNPOD_OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


def _call_runpod_chat_messages(messages: List[Dict[str, str]], temperature: float = 0.0, max_tokens: int = 512) -> str:
    client = _runpod_client()
    resp = client.chat.completions.create(
        model=RUNPOD_OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


def _extract_between(text: str, start_label: str, end_label: str) -> str:
    if not text:
        return ""
    start = text.find(start_label)
    if start == -1:
        return ""
    start += len(start_label)
    end = text.find(end_label, start)
    chunk = text[start:end] if end != -1 else text[start:]
    return chunk.strip()


def _extract_correction_from_response(text: str) -> str:
    # Supports lines like: "교정문장: ..."
    m = re.search(r"교정문장\s*:\s*(.+)", text)
    if not m:
        return ""
    candidate = m.group(1).strip()
    if candidate in {"해당 없음", "제공 불가"}:
        return ""
    # stop at newline if any extra content continues
    return candidate.splitlines()[0].strip()


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


# 1. 오늘의 문법 (Grammar)
# 2. 간단한 설명 (Explanation) - 원문 요약을 바탕으로 이해하기 쉽게 설명
# 3. 예문 (Example) - 영작 문제에 참고가 되도록 제공
# 4. hint : 주요 (단어:뜻) 영작 문제에 대한 힌트 몇개 제시
# 5. 영작 문제 (Question) - 유저가 영어로 번역해야 할 한국어 문장
class GenerateQuestionSchema(BaseModel):
    grammar: str = Field(description="오늘의 문법")
    explanation: str = Field(description="간단한 설명")
    example: str = Field(description="예문")
    hint: str = Field(description="주요 (단어:뜻) 영작 문제에 대한 힌트 몇개 제시")
    question: str = Field(description="유저가 영어로 번역해야 할 한국어 문장")


# 레벨별 출제 설명 (프롬프트 주입용 압축 규칙)
LEVEL_DESCRIPTION_MAP: Dict[str, str] = {
    "초급": "기초 어휘(A1~A2) 중심, 단문 위주(10~14단어), 조건절/복문 최소화, 힌트 4개 내외",
    "중급": "중등 수준 어휘(A2~B1), 1~2절 문장(12~18단어), 핵심 문법 1개 명확히 반영, 힌트 2~3개",
    "고급": "대학생 수준 어휘(B1~B2), 2절 이상 허용(16~24단어), 뉘앙스 표현 허용, 힌트 1~2개",
    "네이티브": "비즈니스/학술 맥락 어휘(C1), 고급 복문 허용(20~30단어), 힌트 최소화(0~1개)"
}


# 0. 문제 출제 엔진 추가 (Step 4.1)
""" current_question: 이전 질문 텍스트 """
def generate_question(level: str, 
                      topic: str, 
                      target_grammar: str = None, 
                      current_question: str = "") -> Dict[str, str]:
    # null처리
    current_question = current_question if current_question else ""

    """유저의 레벨과 주제에 맞춰 학습할 문법, 예문, 그리고 영작할 한국어 문장을 출제합니다. target_grammar가 주어지면 해당 문법을 무조건 출제합니다."""
    print(f"\n[GenerateQuestion] {level} 레벨의 '{topic}' 주제로 문제 생성 중...")
    
    import random
    # TODO picked_situation 따로관리
    sub_situations = {
        "비즈니스": ["화상 회의 지각", "까다로운 고객의 환불 요청", "복사기 고장으로 인한 패닉", "중요한 이메일 오발송", "연봉 협상", "퇴사 통보", "신제품 발표회"],
        "여행": ["공항 수하물 분실", "호텔 룸서비스 오주문", "현지인에게 길 묻기", "기념품 깎기", "갑작스러운 비", "여권 분실", "렌터카 고장"],
        "일상": ["친구와의 약속 파토", "배달 음식 오배송", "층간 소음 항의", "다이어트 결심", "반려동물 목욕시키기", "중고 거래 직거래", "미용실에서의 망한 머리"],
        "학교": ["기말고사 벼락치기", "까다로운 조별 과제 무임승차", "동아리 회식", "도서관 자리 다툼", "교수님과의 면담", "축제 준비", "기숙사 룸메이트와의 갈등"],
    }
    picked_situation = random.choice(sub_situations.get(topic, ["예상치 못한 돌발 상황", "사소한 오해", "긴급한 부탁", "반가운 소식"]))

    # TODO 인스트럭션 텍스트로 따로 관리
    if target_grammar:
        grammar_db_info = _lookup_grammar_db(target_grammar)
        grammar_instruction = f"유저가 오늘 영작해 볼 만한 핵심 문법 패턴 '{target_grammar}'에 대해 집중적으로 다루어 줘.\n현재유저의 레벨은 {level}이고, 주제는 {topic}이다.\n"
        #[참고할 DB 문법 정보]\n{grammar_db_info}"
    else:
        grammar_instruction = "유저가 오늘 영작해 볼 만한 핵심 문법 패턴 1가지를 랜덤하게 선정해."
    
    system_prompt = PROMPTS["generate_question"]["system"].format(
        grammar_instruction=grammar_instruction,
        level_description=LEVEL_DESCRIPTION_MAP.get(
            level,
            "기본 난이도: 어휘 A2~B1, 1~2절 문장(12~18단어), 힌트 2~3개"
        ),
        current_question=current_question,
        topic=topic,
        picked_situation=picked_situation
    )
    human_prompt = PROMPTS["generate_question"]["human"].format(
        level=level,
        topic=topic,
        level_description=LEVEL_DESCRIPTION_MAP.get(
            level,
            "레벨 미지정: 어휘 난이도는 중간(A2~B1), 문장 길이는 12~18단어, 힌트는 2~3개로 제한"
        )
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt)
    ])
    
    # Fixed : 문제 생성시 온도 조절
    # 난이도 제약 준수율을 높이기 위해 온도를 중간값으로 조정
    diverse_llm = ChatOpenAI(model=MODEL_GENERATE_QUESTION, temperature=0.5)
    chain = prompt | diverse_llm.with_structured_output(GenerateQuestionSchema)
    response = chain.invoke({"level": level, "topic": topic})

    grammar = (response.grammar or "").strip()
    question_desc = (response.explanation or "").strip()
    question_example = (response.example or "").strip()
    question_hint = (response.hint or "").strip()
    question_text = (response.question or "").strip()

    raw_content = (
        f"1. 오늘의 문법 (Grammar)\n{grammar}\n\n"
        f"2. 간단한 설명 (Explanation)\n{question_desc}\n\n"
        f"3. 예문 (Example)\n{question_example}\n\n"
        f"4. Hint\n{question_hint}\n\n"
        f"5. 영작 문제 (Question)\n{question_text}"
    )

    return {
        "full_guide": raw_content,
        "question_text": question_text,
        "gen_question_desc": question_desc,
        "gen_question_example": question_example,
        "gen_question_hint": question_hint
    }
    

# 0.5 오답 복습 문제 출제 엔진 (Step 1.5)
def generate_review_question(history_record: tuple) -> Dict[str, str]:
    """유저의 과거 오답 기록을 바탕으로 관련 문법 복습 문제와 안내문을 생성합니다."""
    original, corrected, grammar_point, explanation = history_record
    print(f"\n[ReviewQuestion] 과거 오답 '{grammar_point}' 복습 문제 생성 중...")
    
    system_prompt = PROMPTS["generate_review"]["system"]
    human_prompt = PROMPTS["generate_review"]["human"]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt)
    ])
    
    diverse_llm = ChatOpenAI(model=MODEL_GENERATE_REVIEW, temperature=0.7)
    chain = prompt | diverse_llm
    response = chain.invoke({
        "original": original,
        "corrected": corrected,
        "grammar_point": grammar_point,
        "explanation": explanation
    })
    
    raw_content = response.content
    question_text = ""
    if "영작 문제" in raw_content:
        # 간단 파싱
        try:
            question_text = raw_content.split("영작 문제")[1].replace("(", "").replace("Question)", "").replace(":", "").strip()
        except:
            pass
            
    return {
        "full_guide": raw_content,
        "question_text": question_text
    }

# 1. State 정의
# 💡 [AI 스터디 포인트] LangGraph State (상태 관리)
# 각각의 노드(함수)들이 독립적으로 돌아가는 대신, 하나의 큰 딕셔너리(State) 객체를 돌려보며 
# 각 파이프라인 단계에서 필요한 데이터(intent, history_context 등)를 끼워넣어 누적시킵니다.
class TutorState(TypedDict):
    user_id: str
    target_grammar: str    # (신규) 출제 시 의도한 타겟 문법
    current_question: str   # (신규) 출제된 문제
    current_input: str      # 유저가 방금 입력한 영작문(또는 질문)
    intent: str             # (신규) 분류: translation, question, unrelated, new_question
    is_correct: bool        # (신규) 1단계 검증: 문장이 정답인지 여부
    expected_tag: str       # (신규) 오답일 경우 예상되는 핵심 문법 테그
    history_context: str    # DB에서 조회된 과거 이력
    feedback: str           # LLM이 생성한 피드백 (과거 이력 + 현재 교정)
    corrected_text: str     # LLM이 수정한 올바른 문장 (정답)
    grammar_tag: str        # 주요 문법 에러 태그 (예: "article", "tense")
    explanation: str        # 추가된 설명 필드 (선택 사항)
    better_expression: str  # (신규) 일상/구어체 추천 표현
    retry_count: int        # (신규) 검증 피드백 반복 횟수
    reviewer_feedback: str  # (신규) 검증관이 재작성을 요청한 피드백 내용
    gen_question_desc: str # (신규) 출제된 문제 설명
    gen_question_example: str # (신규) 출제된 문제 예시
    gen_question_hint: str # (신규) 출제된 문제 힌트


# 1. 출력 스키마 정의 (Pydantic)
class IntentSchema(BaseModel):
    intent: Literal['new_question', 'unrelated', 'question', 'translation'] = Field(
        description="유저의 입력 의도 분류"
    )

# 2. 출력 스키마 정의 (Pydantic)
class ScoreSchema(BaseModel):
    score: int = Field(
        ge=0, le=10, 
        description="영작 정확도 (0-10점). translation이 아니면 0점"
    )
    tag: str = Field(
        description="핵심 문법 규칙 1단어 (예: Article, Tense). 없으면 'None'"
    )
    reason: str = Field(
        description="분류 및 점수 부여의 간략한 근거"
    )

class VerifySchema(BaseModel):
    is_pass: bool = Field(
        description="피드백이 모든 판단 기준을 통과하여 치명적인 문제가 없다면 true, 기준에 미달하는 치명적인 오류가 있다면 false"
    )
    reason: str = Field(
        description="통과 시 'PASS', 실패 시 '기준 [번호] 실패: [이유]' 형식으로 간략히 작성"
    )



# 2. RetrieveNode 구현 (사전 판별 + 스마트 검색)
# 💡 [AI 스터디 포인트] Intent Classification & Routing (의도 분류 및 라우팅)
# 무작정 무거운 메인 LLM을 부르기 전에, 
# 1. 유저의 텍스트가 번역 시도인지 단순 잡담인지를 판별하고 (Self-RAG)
# 2. 만약 정답이라면 뒤의 무거운 RAG 단계를 아예 스킵해버리는 비용/속도 최적화 기법입니다.
def retrieve_node(state: TutorState) -> Dict[str, Any]:
    print(f"\n[RetrieveNode] 유저 입력 분석 및 1차 검증 시작(잡담 필터링)...")

    # 1. 의도 분류
    #분류 로직 따로 빼기
    classify_prompt = PROMPTS["retrieve"]["classify"]
    classify_chain = ChatPromptTemplate.from_template(classify_prompt) | llm.with_structured_output(IntentSchema)
    intent_result = classify_chain.invoke({
        "current_input": state["current_input"]
    })
    intent = intent_result.intent
    
    # Fixed : Self-RAG : 현재 기준으로 의도분류와 정답을 판별하는 일 두가지를 한번에 하고있음.
    # default 값 설정
    score = 0 # 정답 인정 기준 점수 (0~10)
    expected_tag = "None" # 오답 예상 태그
    is_correct = False
    
    # 2. 정답 평가 (의도가 번역인 경우에만)
    # 받아온 결과를 파싱하여 의도, 정답 인정 기준 점수, 오답 예상 태그를 추출
    # Fixed : 문제는 이 형식을 안지킬수도 있음. -> 출력파서 제공
    # 출력 형식:
    # Intent: [분류단어]
    # Score: [점수]
    # Tag: [태그 단어]
    if intent == "translation":
        pre_eval_prompt = PROMPTS["retrieve"]["pre_eval"]
        eval_chain = ChatPromptTemplate.from_template(pre_eval_prompt) | llm.with_structured_output(ScoreSchema)
        eval_res = eval_chain.invoke({ # Fixed : 문제는 정답인지 아닌지를 그냥 문장을 던져서 1차원적으로 판별하는 로직
            "current_question": state.get("current_question", "없음"),
            "current_input": state["current_input"],
            "gen_question_desc": state.get("gen_question_desc", ""),
            "gen_question_example": state.get("gen_question_example", ""),
            "gen_question_hint": state.get("gen_question_hint", "")
        })
        
        score = eval_res.score
        expected_tag = eval_res.tag
        
        print(f"[RetrieveNode] 평가 사유: {eval_res.reason}")
        
        if score >= CORRECTNESS_THRESHOLD:
            is_correct = True

    print(f"[RetrieveNode] 결과 -> 의도: {intent}, 정답여부: {is_correct} (점수: {score}), 예상태그: {expected_tag}")

    history_context = ""
    # 2.2 의도가 번역이 아니면 DB 검색 스킵
    if intent != "translation":
        print(f"[RetrieveNode] '{intent}' 의도 감지. DB 검색 스킵.")
    # 2.3 정답이면 DB 검색 스킵
    elif is_correct:
        print("[RetrieveNode] 정답이므로 과거 오답 이력 검색을 스킵합니다.")
        history_context = "해당 문장은 완벽한 정답입니다. 칭찬만 해주세요."
    else:
        print(f"[RetrieveNode] {expected_tag} 오류 감지. DB에서 과거 유사 사례 검색 중...")

        collected: list = []  # (kind, record) 튜플 리스트

        # 출제 문법 tag 기준으로
        # [A] target_grammar(tag_id) 기준 최신 오답 1개
        target_grammar = state.get("target_grammar", "")
        if target_grammar:
            tag_hits = search_history_by_tag(user_id=state["user_id"], tag_id=target_grammar, limit=1)
            if tag_hits:
                collected.append(("tag", tag_hits[0]))
                print(f"[디버깅] [A] tag검색 hit: {tag_hits[0][0]} ({tag_hits[0][2]})")
            else:
                print(f"[디버깅] [A] tag검색 hit 없음 (tag_id={target_grammar})")

        # [B] 유사도 기준 Top1 (중복 제거)
        sim_hits = search_history(
            user_id=state["user_id"], 
            current_question=state["current_question"],
            limit=5, 
            expected_tag=expected_tag)
        if sim_hits:
            already = {r[0] for _, r in collected}
            if sim_hits[0][0] not in already:
                collected.append(("sim", sim_hits[0]))
                print(f"[디버깅] [B] 유사도검색 hit: {sim_hits[0][0]} ({sim_hits[0][2]})")
            else:
                print(f"[디버깅] [B] 유사도검색 결과가 [A]와 중복 — 스킵")

        if not collected:
            history_context = "과거 오답 기록이 없습니다."
            print("[디버깅] 검색 결과 없음")
        else:
            lines = []
            for kind, r in collected:
                label = "같은문법 과거기록" if kind == "tag" else "유사문장 과거기록"
                lines.append(f"[{label}] 이전입력: '{r[0]}' -> 교정: '{r[1]}' (태그: {r[2]})")
            history_context = "\n".join(lines)
            print(f"\n---------------------------------------")
            print(f"[디버깅] 최종 컨텍스트 ({len(collected)}건):\n{history_context}")
            print(f"------------------------------------------")

        print(f"[RetrieveNode] 검색 완료. 컨텍스트 길이: {len(history_context)}" )
        
    return {
        "intent": intent,
        "is_correct": is_correct,
        "expected_tag": expected_tag,
        "history_context": history_context
    }


class GrammarAnalysisSchema(BaseModel):
        corrected_text: str = Field(description="교정된 완벽한 원어민 영어 문장")
        grammar_tag: str = Field(description="핵심 문법 오류 태그 단어 1개 (짧은 영어 단어)")
        explanation: str = Field(description="오답 이유에 대한 간단하고 명확한 한국어 설명 (틀린 이유 팩트만 전달)")
        better_expression: str = Field(description="원어민들이 더 자주 쓰는 자연스러운 구어체 대안 1개 (선택 사항)")
    
class DraftFeedbackSchema(BaseModel):
    feedback: str = Field(description="따뜻하고 분석적인 한국어 메시지")
    corrected_text: str = Field(description="교정된 완벽한 원어민 영어 문장")
    grammar_tag: str = Field(description="핵심 문법 오류 태그 단어 1개 (짧은 영어 단어)")
    explanation: str = Field(description="오답 이유에 대한 간단하고 명확한 한국어 설명 (틀린 이유 팩트만 전달)")
    better_expression: str = Field(description="원어민들이 더 자주 쓰는 자연스러운 구어체 대안 1개 (선택 사항)")
    history_comment: str = Field(description="과거 이력 비교 코멘트")



# 3. FeedbackNode (LLM 코어) 구현
def feedback_node(state: TutorState) -> Dict[str, Any]:
    intent = state.get("intent", "translation")
    
    if intent == "unrelated":
        return {"feedback": "학습과 관련된 질문을 해주세요.", "corrected_text": "", "grammar_tag": "", "explanation": "", "better_expression": ""}
    elif intent == "new_question":
        return {"feedback": "네, 다른 문제를 준비할게요!", "corrected_text": "", "grammar_tag": "", "explanation": "", "better_expression": ""}
    elif intent == "question":
        print("[FeedbackNode] 일반 학습 질문에 답변 생성 중...")
        # ✅ 기존 로직 유지: 질문(intent=question)은 기존 ChatOpenAI 체인을 사용
        prompt = ChatPromptTemplate.from_messages([
            ("system", PROMPTS["feedback"]["question_system"]),
            ("human", "{current_input}")
        ])
        ans = (prompt | llm).invoke({"current_input": state["current_input"]}).content
        return {"feedback": ans, "corrected_text": "", "grammar_tag": "", "explanation": "", "better_expression": ""}
        
        
     # --- [추가해야 할 부분] ---
    if state.get("is_correct"):
        print("[FeedbackNode] 완벽한 정답이므로 분석 로직을 스킵하고 칭찬 피드백을 반환합니다.")
        return {
            "feedback": "정확합니다! 문법적인 오류 없이 완벽하게 영작하셨습니다. 아주 잘하셨어요! 👏✨",
            "corrected_text": state.get("current_input", ""),
            "grammar_tag": "None",
            "explanation": "완벽한 문장입니다.",
            "better_expression": ""
        }
    # --------------------------
    
    """검색된 '과거 오답 이력'과 '현재 입력 문장'을 LLM에 전달하여 '기억력' 기반 피드백을 생성합니다."""
    # 💡 [AI 스터디 포인트] RAG (Retrieval-Augmented Generation)
    # 데이터베이스에서 찾아온 유저의 과거 오답 이력(<history_context>)을 시스템 프롬프트에 동적으로 "주입"합니다.
    # LLM은 원래 유저를 모르지만, 이 주입된 컨텍스트 덕분에 "지난번에도 틀렸네요!"라는 개인화된 대답이 가능해집니다.
    print("[FeedbackNode] LLM 번역 피드백 생성 중...")
    
    current_question = state.get("current_question", "")
    current_input = state.get("current_input", "")

    # grammar_atlas 조회
    # 문법 가이드 문서 조회
    # Fixed : 가이드 문서 로드 수정 필요 (DB에서 조회하는 신규 함수 사용)
    grammar_reference = _lookup_grammar_db(state.get("target_grammar", ""))
    print(f"[FeedbackNode] grammar_reference tag: {state.get('target_grammar', '')} / 로드: {'O' if grammar_reference else 'X'}")

    grammar_analysis_prompt = PROMPTS["feedback"]["translation_analysis"].format(
        current_question=current_question,
        current_input=current_input,
        grammar_reference=grammar_reference,
        gen_question_desc=state.get("gen_question_desc", ""),
        gen_question_example=state.get("gen_question_example", ""),
        gen_question_hint=state.get("gen_question_hint", "")
    )
    
    # 1. 문법 분석 (Analyze Error)
    print(f" === debug : [FeedbackNode] 1. 분석 프롬프트:\n{grammar_analysis_prompt} === \n")
    analysis_chain = ChatPromptTemplate.from_messages([
        ("system", grammar_analysis_prompt),
        ("human", PROMPTS["feedback"]["human_normal"])
    ]) | llm.with_structured_output(GrammarAnalysisSchema)
    
    analysis_res = analysis_chain.invoke({
        "current_question": current_question,
        "current_input": current_input,
        "gen_question_desc": state.get("gen_question_desc", ""),
        "gen_question_example": state.get("gen_question_example", ""),
        "gen_question_hint": state.get("gen_question_hint", "")
    })
    
    print (f"===[FeedbackNode] 1. 분석 결과:\n{analysis_res}\n===")
    
    
    # Fixed : 출력 스키마 정의 (Pydantic)필요
    corrected_text = analysis_res.corrected_text.strip() if analysis_res.corrected_text else ""
    grammar_tag = analysis_res.grammar_tag.strip() if analysis_res.grammar_tag else ""
    explanation = analysis_res.explanation.strip() if analysis_res.explanation else ""
    better_expression = analysis_res.better_expression.strip() if analysis_res.better_expression else ""
    

    # if "Corrected Text" in analysis_res:
    #     try:
    #         corrected_text = analysis_res.split("Corrected Text")[1].split("\n")[0].replace(":", "").strip()
    #     except:
    #         pass
            
    # if "Grammar Tag" in analysis_res:
    #      try:
    #         grammar_tag_raw = analysis_res.split("Grammar Tag")[1].split("Explanation")[0]
    #         grammar_tag = grammar_tag_raw.split("\n")[0].replace(":", "").strip()
    #      except:
    #          pass

    # if "Explanation" in analysis_res:
    #      try:
    #         explanation_raw = analysis_res.split("Explanation")[1]
    #         if "Better Expression" in explanation_raw:
    #             explanation_raw = explanation_raw.split("Better Expression")[0]
    #         explanation = explanation_raw.replace(":", "").strip()
    #      except:
    #          pass
             
    # if "Better Expression" in analysis_res:
    #      try:
    #         better_expression = analysis_res.split("Better Expression")[1].replace(":", "").strip()
    #      except:
    #          pass

    # if not grammar_tag:
    #     grammar_tag = state.get("expected_tag", "")
        
    # 2. 과거 이력 대조 (Match History)
    history_context = state.get("history_context", "")
    
    # TODO 그지같은 코드 수정 필요
    if not history_context or "해당 문장은 완벽한 정답입니다" in history_context or "과거 오답 기록이 없습니다" in history_context:
        history_comment = "이번이 처음 틀린 유형이거나 과거 이력이 없습니다."
    else:
        grammar_history_prompt = PROMPTS["feedback"]["translation_history"].format(
            history_context=history_context,
            grammar_tag=grammar_tag,
            explanation=explanation
        )
        history_chain = ChatPromptTemplate.from_messages([
            ("system", grammar_history_prompt),
            ("human", "과거 이력과 비교해서 코멘트를 하나 작성해줘.")
        ]) | llm
        history_comment = history_chain.invoke({
            "history_context": history_context,
            "grammar_tag": grammar_tag,
            "explanation": explanation
        }).content.strip()
        
    print (f"===[FeedbackNode] 2. 이력 대조 코멘트:\n{history_comment}\n===")
    
    # 3. 최종 피드백 작성 (Draft Feedback)
    draft_feedback_prompt = PROMPTS["feedback"]["translation_draft"].format(
        corrected_text=corrected_text,
        grammar_tag=grammar_tag,
        explanation=explanation,
        better_expression=better_expression,
        history_comment=history_comment
    )
    
    reviewer_feedback = state.get("reviewer_feedback", "")
    if reviewer_feedback:
        print(f"[FeedbackNode] ⚠️ 수석 교사(QA)의 지시를 받아 피드백을 재작성 중입니다... (재시도: {state.get('retry_count', 0)}회)")
        human_prompt = PROMPTS["feedback"]["human_retry"].format(reviewer_feedback=reviewer_feedback)
    else:
        human_prompt = "분석 결과를 바탕으로 지정된 항목 형식을 엄격히 지켜서 피드백 메시지를 작성해줘."

    draft_chain = ChatPromptTemplate.from_messages([
        ("system", draft_feedback_prompt),
        ("human", human_prompt)
    ]) | llm.with_structured_output(DraftFeedbackSchema)
    
    feedback = draft_chain.invoke({
        "current_question": current_question,
        "current_input": current_input
    })
    
    print (f"===[FeedbackNode] 3. 최종 생성된 피드백:\n{feedback}\n===")
    
    print("[FeedbackNode] 피드백 생성 완료.")
    
    return {
        "feedback": feedback,
        "corrected_text": corrected_text,
        "grammar_tag": grammar_tag,
        "explanation": explanation,
        "better_expression": better_expression
    }


# 4. 자가 검증 (Self-RAG) Node 구현
# 💡 [AI 스터디 포인트] Self-RAG (자가 점검 / Hallucination 방지)
# 생성형 AI는 그럴듯한 거짓말(환각)을 할 리스크가 큽니다.
# 이를 방지하기 위해 생성(Feedback) 노드 다음에 무조건 온도(Temperature)가 0인 매우 엄격한 
# 평가자 LLM 노드를 하나 더 붙여서, 스스로의 결과물을 채점하고 이상하면 교정해버리는 안전장치입니다.
def verify_node(state: TutorState) -> Dict[str, Any]:
    intent = state.get("intent", "translation")
    
    # 일반 질문이거나 완벽한 정답인 경우 검증을 패스합니다.
    if intent != "translation" or state.get("is_correct"):
        print("[VerifyNode] 완벽한 정답이거나 오답 피드백이 아니므로 검증을 스킵합니다.")
        return {}
        
    print("[VerifyNode] 생성된 피드백의 정확성 및 환각(Hallucination) 검증 중...")
    
    # Fixed 프롬프트 다시 셋팅 이상함.
    qa_prompt = PROMPTS["verify"]["qa_prompt"].format(
        current_question=state.get('current_question', ''),
        current_input=state['current_input'],
        feedback=state.get('feedback', ''),
        grammar_reference=_lookup_grammar_db(state.get('target_grammar', ''))
    )
    
    reviewer_llm = ChatOpenAI(model=MODEL_VERIFY, temperature=0.0).with_structured_output(VerifySchema)
    validation_res = reviewer_llm.invoke(qa_prompt)
    
    # LLM이 분석 후 마지막에 PASS를 출력하는 경우도 처리 (마지막 줄 기준)
    # Fixed : 반드시 PASS 같은 형식을 뱉지 않음. (해결: Structured Output 강제 적용 완료)
    if validation_res.is_pass:
        print("[VerifyNode] 검증 통과 (오류 없음).")
        return {"reviewer_feedback": ""}  # 검증 통과 시 루프 종료 신호
    
    retry_count = state.get("retry_count", 0)
    
    if retry_count >= 2:
        print("[VerifyNode] ⚠️ 최대 재시도 횟수 초과. 더 이상 반복하지 않고 현재 생성된 피드백을 강제로 채택합니다.")
        return {"reviewer_feedback": ""}
        
    print(f"[VerifyNode] ⚠️ 피드백에서 오류를 발견했습니다! 튜터에게 재작성을 요청합니다. (재시도 {retry_count + 1}/2)")
    print(f"=== 검증관 피드백: {validation_res.reason}")

    # 생성된 피드백 텍스트 내용을 직접 덮어쓰지 않고, 
    # 검증관의 피드백만 상태에 담아서 돌려보내면 LangGraph 루프가 FeedbackNode로 돌아감.
    return {
        "reviewer_feedback": validation_res.reason,
        "retry_count": retry_count + 1
    }


    

# # 루브릭 검증 적용
# def verify_node(state: TutorState) -> Dict[str, Any]:
#     intent = state.get("intent", "translation")
    
#     # 일반 질문이거나 완벽한 정답인 경우 검증을 패스합니다.
#     if intent != "translation" or state.get("is_correct"):
#         print("[VerifyNode] 완벽한 정답이거나 오답 피드백이 아니므로 검증을 스킵합니다.")
#         return {"reviewer_feedback": ""}
        
#     print("[VerifyNode] 루브릭(Rubric) 기반 정밀 검증 및 환각 체크 중...")
    
#     print("=================")
#     print("1. 출제된 한국어 문제: ", state.get('current_question', ''))
#     print("2. 유저의 원본 입력: ", state['current_input'])
#     print("3. 과거 오답 이력(RAG): ", state.get('history_context', '없음'))
#     print("4. feedback : ", state.get('feedback', ''))
#     print("=================")


#     # 루브릭 기반의 엄격한 프롬프트 구성
#     qa_prompt = f"""당신은 까다롭기로 유명한 '수석 영어 교육 에디터'입니다.
# 아래 제공된 [데이터]를 바탕으로 튜터의 피드백을 검토하고, **단 하나의 루브릭이라도 미달되면 즉시 REJECT** 하십시오.

# [데이터]
# 1. 출제된 한국어 문제: {state.get('current_question', '')}
# 2. 유저의 원본 입력: {state['current_input']}
# 3. 과거 오답 이력(RAG): {state.get('history_context', '없음')}
# 4. 튜터 생성 피드백:
# ---
# {state.get('feedback', '')}
# ---

# [검수 루브릭 - 아래 중 하나라도 해당하면 REJECT]
# 1. **의도 불일치**: 튜터가 제시한 '튜터 생성 피드백'이 원래 '출제된 한국어 문제'의 시제, 강조점, 뉘앙스를 제대로 살리지 못했는가?
# 2. **역번역(Back-translation) 오류**: 튜터의 '튜터 생성 피드백'을 기반으로 다시 영어 문장을 만들면, 기존의 '출제된 한국어 문제' 와 문장 의미가 일치하는가?
# 3. **기억력 결핍**: [과거 오답 이력]이 존재함에도 불구하고, 피드백에서 이를 언급하며 유저의 습관을 지적하지 않았는가? (이력이 있을 때만 해당)
# 4. **설명 환각**: 튜터가 설명한 문법 규칙이 틀렸거나, 유저가 하지 않은 실수를 지적하는 등 환각 증상이 있는가?

# [응답 규칙]
# - 모든 루브릭을 완벽히 통과할 경우에만: 'PASS' 출력.
# - 하나라도 문제가 있을 경우: 'REJECT'라고 명시하고, 몇 번 루브릭 위반인지와 함께 **튜터가 다음 번에 어떻게 수정해야 하는지 구체적인 가이드라인**을 작성하십시오.
# """
    
#     # 검증 노드는 일관성을 위해 temperature를 0으로 고정합니다.
#     # 성능을 위해 gpt-4o를 사용하는 것을 강력 추천하지만, 기존 환경에 맞춰 유지합니다.
#     reviewer_llm = ChatOpenAI(model="gpt-4o", temperature=0.0) 
#     validation_res = reviewer_llm.invoke(qa_prompt).content.strip()
    
#     # 'PASS' 여부 확인 (대소문자 무관, 앞부분 일치 확인)
#     if validation_res.upper().startswith("PASS"):
#         print("[VerifyNode] ✅ 모든 루브릭 통과 (PASS).")
#         return {"reviewer_feedback": ""} 
    
#     retry_count = state.get("retry_count", 0)
    
#     # 최대 재시도 체크
#     if retry_count >= 2:
#         print("[VerifyNode] ⚠️ 최대 재시도(2회)를 초과했습니다. 품질이 낮더라도 현재 피드백을 종료합니다.")
#         return {"reviewer_feedback": ""}
        
#     print(f"[VerifyNode] ❌ REJECT 발생! 지적 사항: {validation_res[:100]}...")
#     print(f"            (재시도 카운트: {retry_count + 1}/2)")
    
#     # 검증 결과(비판)를 reviewer_feedback에 담아 FeedbackNode로 되돌려 보냄
#     return {
#         "reviewer_feedback": validation_res,
#         "retry_count": retry_count + 1
#     }





# 5. SaveNode 구현
def save_node(state: TutorState) -> Dict[str, Any]:
    intent = state.get("intent", "translation")
    
    if intent != "translation":
        print("[SaveNode] 번역/작문 제출이 아니므로 히스토리에 기록하지 않습니다.")
        return {}
        
    if state.get("is_correct"):
        print("[SaveNode] 완벽한 정답이므로 오답 DB에 기록하지 않습니다.")
        return {}
        
    """피드백이 완성된 오답 문장을 다시 벡터 DB에 기록합니다."""
    print(f"[SaveNode] 이번 입력({state['current_input']})을 히스토리 DB에 기록합니다.")
    
    # 원문, 수정본, 태그 정보를 벡터화하여 저장
    save_history(
        user_id=state["user_id"],
        original=state["current_input"],
        corrected=state["corrected_text"],
        grammar_point=state["grammar_tag"],
        explanation=state.get("explanation", "")
    )
    
    print("[SaveNode] DB 기록 완료.")
    return {}

# 6. TODO Graph 조립
# 💡 [AI 스터디 포인트] DAG (Directed Acyclic Graph)
# 노드(작업 단위)들을 가져와서 어떤 순서로 실행할지 선을 그어주는(Edge 연결) 파이프라인 조립체입니다.
def build_tutor_graph() -> StateGraph:
    """핵심 튜터링 사이클 LangGraph를 조립합니다."""
    workflow = StateGraph(TutorState)
    
    # 노드 추가 (함수를 그래프에 매핑)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("feedback", feedback_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("save", save_node)
    
    # 엣지 연결 (여기서는 순차 실행이지만, 조건부 라우팅도 가능합니다)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "feedback")
    workflow.add_edge("feedback", "verify")
    
    # 💡 [AI 스터디 포인트] Conditional Edges (조건부 간선)
    # verify_node의 결과(reviewer_feedback 유무)에 따라 어디로 갈지 결정하는 라우팅 함수
    def route_after_verify(state: TutorState) -> str:
        if state.get("reviewer_feedback"):
            return "feedback" # 반려 사유가 있으면 다시 피드백 엣지로 감
        return "save"         # 통과했으면 저장하러 감
        
    workflow.add_conditional_edges("verify", route_after_verify, {"feedback": "feedback", "save": "save"})
    
    workflow.add_edge("save", END)
    
    return workflow.compile()

# 단독 실행 테스트용
if __name__ == "__main__":
    app_graph = build_tutor_graph()
    
    test_state = {
        "user_id": "test_user_001",
        "target_grammar": "",
        "current_question": "나는 어제 병원에 갔다.",
        "current_input": "I go to hospital yesterday.",
        "intent": "translation",
        "is_correct": False,
        "expected_tag": "",
        "history_context": "",
        "feedback": "",
        "corrected_text": "",
        "grammar_tag": "",
        "explanation": "",
        "better_expression": "",
        "retry_count": 0,
        "reviewer_feedback": "",
        "gen_question_desc": "",
        "gen_question_example": "",
        "gen_question_hint": ""
    }
    
    print("=== Core Engine Test Run ===")
    result = app_graph.invoke(test_state)
    
    print("\\n[최종 피드백 결과]")
    print(result["feedback"])
    print("\\n[추출 데이터]")
    print(f"- Corrected: {result['corrected_text']}")
    print(f"- Tag: {result['grammar_tag']}")
