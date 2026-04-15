import os
import json
import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# 내부 AI 로직 임포트
from core_engine import build_tutor_graph, generate_question, generate_review_question
from database import init_db, get_recent_mistakes, get_top_mistake_grammars, increment_correct, get_user_stats, update_gauge

load_dotenv()

# grammar_atlas.json 로드 (tag_id 목록 컨스트 저장)
_ATLAS_PATH = os.path.join(os.path.dirname(__file__), "grammar_atlas.json")
with open(_ATLAS_PATH, encoding="utf-8") as _af:
    _ATLAS_TAG_IDS: list = [item["tag_id"] for item in json.load(_af)]

_LEVEL_GRAMMAR_POOLS = {
    "초급": [
        "can/could_usage",
        "must/have_to_usage",
        "infinitive_of_purpose",
        "article_definite",
        "article_indefinite",
        "simple_past_structure"
    ],
    "중급": [
        "would_usage",
        "gerund_as_subject",
        "gerund_as_object",
        "adjective_comparative",
        "passive_voice_structure",
        "compound_sentence_structure"
    ],
    "고급": [
        "wish_past_simple_usage",
        "should_have_p.p._usage",
        "infinitive_as_subject",
        "participle_construction",
        "complex_sentence_structure"
    ],
    "네이티브": [
        "wish_past_simple_usage",
        "should_have_p.p._usage",
        "participle_construction",
        "complex_sentence_structure",
        "compound_sentence_structure"
    ]
}


def _pick_grammar() -> str:
    """TARGET_GRAMMAR 우선. 없으면 현재 LEVEL의 문법 풀에서 랜덤 선택."""
    if STATE.get("TARGET_GRAMMAR"):
        return STATE["TARGET_GRAMMAR"]

    level = STATE.get("LEVEL", "")
    pool = [tag for tag in _LEVEL_GRAMMAR_POOLS.get(level, []) if tag in _ATLAS_TAG_IDS]
    if pool:
        return random.choice(pool)
    return random.choice(_ATLAS_TAG_IDS)

app = FastAPI(title="AI Tutor API Server")

# 프론트엔드(Next.js) 연동을 위한 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 전역 상태 관리 (로컬 단일 유저용 메모리 캐시) ===
# 실제 서비스에서는 Redis나 DB를 붙여 세션별로 관리해야 합니다.
# TODO: 오답 복습 모드 활성화 플래그 확인
ENABLE_REVIEW_MODE = False  # 오답 복습 모드 활성화 플래그 (True: 켜짐, False: 꺼짐)

STATE = {
    "USER_ID": "demo_user1",
    "LEVEL": "초급",
    "TOPIC": "일상",
    "TARGET_GRAMMAR": None,          # 유저가 고정한 문법 tag_id (없으면 랜덤모드)
    "CURRENT_QUESTION_GRAMMAR": "",  # 이번 문제에 실제 사용된 tag_id
    "LAST_QUESTION_TEXT": "",
    "current_question_data": None,
    "MODE": "MAIN",          # "REVIEW" or "MAIN"
    "REVIEW_ITEMS": [],
    "REVIEW_INDEX": 0
}

tutor_graph = build_tutor_graph()

# DB 초기화 (실행 시 최초 1회)
init_db()

def _build_session_info() -> dict:
    """현재 STATE와 DB stats를 합쳐 session_info 딕셔너리를 반환합니다."""
    stats = get_user_stats(STATE["USER_ID"])
    return {
        "user": STATE["USER_ID"],
        "level": STATE["LEVEL"],
        "topic": STATE["TOPIC"],
        "mode": STATE["MODE"],
        "review_progress": f"{STATE['REVIEW_INDEX'] + 1}/{len(STATE['REVIEW_ITEMS'])}" if STATE["MODE"] == "REVIEW" else None,
        "correct_count": stats["correct_count"],
        "incorrect_count": stats["incorrect_count"],
        "current_gauge": stats["current_gauge"],
    }

# Request Models
class ChatRequest(BaseModel):
    user_input: str

class CommandRequest(BaseModel):
    command_type: str
    command_value: str

@app.get("/api/init")
def init_session(level: str = None, 
                 topic: str = None, 
                 grammar: str = None):
    """지정된 설정값으로 최초 1회 문제 생성"""
    if level:
        STATE["LEVEL"] = level
    if topic:
        STATE["TOPIC"] = topic
        
    # 문법은 '리셋' 혹은 None이 넘어올 수 있음
    if grammar and grammar != "리셋":
        STATE["TARGET_GRAMMAR"] = grammar
    else:
        STATE["TARGET_GRAMMAR"] = None
        
    # 복습 모드 체크
    review_items = get_recent_mistakes(STATE["USER_ID"], limit=3)
    if ENABLE_REVIEW_MODE and review_items:
        STATE["MODE"] = "REVIEW"
        STATE["REVIEW_ITEMS"] = review_items
        STATE["REVIEW_INDEX"] = 0
        first_review = review_items[0]
        STATE["current_question_data"] = generate_review_question(first_review)
        msg = "💡 오답 복습 모드를 시작합니다. 지난번에 틀렸던 문제들을 먼저 복습할게요!"
        progress = f"1/{len(review_items)}"
    else: # 메인 학습 시작
        STATE["MODE"] = "MAIN"
        picked = _pick_grammar() # 유저가 선택한 문법 tag_id
        STATE["CURRENT_QUESTION_GRAMMAR"] = picked
        STATE["current_question_data"] = generate_question(
            STATE["LEVEL"],
            STATE["TOPIC"],
            picked,
            current_question=STATE.get("LAST_QUESTION_TEXT", "") # 이전 질문 텍스트
        )
        STATE["LAST_QUESTION_TEXT"] = STATE["current_question_data"].get("question_text", "")
        msg = f"[{STATE['TOPIC']}] 카테고리의 새로운 학습 세션이 시작되었습니다."
        progress = None
    
    return {
        "status": "success",
        "message": msg,
        "session_info": _build_session_info(),
        "question": STATE["current_question_data"]["question_text"],
        "guide": STATE["current_question_data"]["full_guide"]
    }

@app.post("/api/command")
def handle_command(req: CommandRequest):
    """시스템 설정 변경 (레벨, 주제, 문법)"""
    cmd = req.command_type
    val = req.command_value
    
    if cmd == "레벨":
        STATE["LEVEL"] = val
        msg = f"레벨이 '{val}'(으)로 변경되었습니다. (다음 문제부터 적용)"
    elif cmd == "주제":
        STATE["TOPIC"] = val
        msg = f"주제가 '{val}'(으)로 변경되었습니다. (다음 문제부터 적용)"
    elif cmd == "문법":
        if val == "리셋":
            STATE["TARGET_GRAMMAR"] = None
            msg = "타겟 문법이 '랜덤'으로 초기화되었습니다."
        else:
            STATE["TARGET_GRAMMAR"] = val
            msg = f"타겟 문법이 '{val}'(으)로 고정되었습니다."
    elif cmd == "모드":
        if val == "복습":
            review_items = get_top_mistake_grammars(STATE["USER_ID"], limit=10)
            if not review_items:
                return {
                    "status": "error",
                    "message": "⚠️ 아직 오답 기록이 없어 복습 모드를 시작할 수 없습니다.",
                    "session_info": _build_session_info()
                }
            STATE["MODE"] = "REVIEW"
            STATE["REVIEW_ITEMS"] = review_items
            STATE["REVIEW_INDEX"] = 0
            STATE["current_question_data"] = generate_review_question(review_items[0])
            return {
                "status": "success",
                "message": f"📚 복습 모드 시작! 가장 많이 틀린 문법 Top {len(review_items)}개를 순서대로 복습합니다.",
                "session_info": _build_session_info(),
                "next_question": STATE["current_question_data"]["full_guide"]
            }
        else:
            msg = f"알 수 없는 모드입니다: '{val}'. 사용 가능한 모드: 복습"
    else:
        msg = "알 수 없는 명령어입니다."
        
    return {
        "status": "success", 
        "message": msg,
        "session_info": _build_session_info()
    }

@app.post("/api/chat")
def chat(req: ChatRequest):
    """유저의 영작 제출 및 피드백 생성"""
    try:
        user_input = req.user_input.strip()
        
        if user_input in ["다른문제", "패스"]:
            picked = _pick_grammar()
            STATE["CURRENT_QUESTION_GRAMMAR"] = picked
            STATE["current_question_data"] = generate_question(
                STATE["LEVEL"],
                STATE["TOPIC"],
                picked,
                current_question=STATE.get("LAST_QUESTION_TEXT", "")
            )
            STATE["LAST_QUESTION_TEXT"] = STATE["current_question_data"].get("question_text", "")
            return {
                "intent": "new_question",
                "feedback": "네, 다른 문제를 준비할게요!",
                "next_question": STATE["current_question_data"]["full_guide"]
            }
            
        if not STATE["current_question_data"]:
            # 세션이 날아갔을 경우 복구
            picked = _pick_grammar()
            STATE["CURRENT_QUESTION_GRAMMAR"] = picked
            STATE["current_question_data"] = generate_question(
                STATE["LEVEL"],
                STATE["TOPIC"],
                picked,
                current_question=STATE.get("LAST_QUESTION_TEXT", "")
            )
            STATE["LAST_QUESTION_TEXT"] = STATE["current_question_data"].get("question_text", "")

        tutor_state = {
            "user_id": STATE["USER_ID"],
            "current_question": STATE["current_question_data"]["question_text"],
            "current_input": user_input,
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
            "target_grammar": STATE.get("CURRENT_QUESTION_GRAMMAR", "") or "",
            "gen_question_desc": STATE["current_question_data"].get("gen_question_desc", ""),
            "gen_question_example": STATE["current_question_data"].get("gen_question_example", ""),
            "gen_question_hint": STATE["current_question_data"].get("gen_question_hint", "")
        }
        
        # LangGraph 호출
        result = tutor_graph.invoke(tutor_state)
        
        intent = result.get("intent", "translation")
        feedback = result.get("feedback", "")
        is_correct = result.get("is_correct", False) # is_correct 추가
        response_data = {
            "intent": intent,
            "feedback": feedback,
            "next_question": None,
            "session_info": {
                "user": STATE["USER_ID"],
                "level": STATE["LEVEL"],
                "topic": STATE["TOPIC"],
                "mode": STATE["MODE"],
                "review_progress": f"{STATE['REVIEW_INDEX'] + 1}/{len(STATE['REVIEW_ITEMS'])}" if STATE["MODE"] == "REVIEW" else None
            }
        }
        
        # 게이미피케이션 (게이지 처리)
        if intent == "translation":
            amount = 15 if is_correct else -10
            new_gauge = update_gauge(STATE["USER_ID"], amount)
            
            if new_gauge >= 100:
                response_data["event"] = "LEVEL_UP"
                update_gauge(STATE["USER_ID"], -new_gauge) # 0으로 초기화
            elif amount < 0 and new_gauge <= 0:
                # 방금 틀려서 0 이하가 된 경우 (단순히 이미 0이었는데 계속 0인 경우 제외 로직은 단순화하여 처음 0 도달 시로 취급)
                # 엄밀하게 하려면 이전 게이지를 불러와서 >0 이었다가 <=0 이 된 건지 확인이 필요하나, 
                # 여기서는 amount < 0이고 new_gauge == 0 인 경우를 강등 모달로 호출
                response_data["event"] = "LEVEL_DOWN"
                update_gauge(STATE["USER_ID"], -new_gauge) # 확실히 0 고정

        # 정답을 맞췄거나, 유저가 명시적으로 다른 문제를 요구했을 때 다음 단계 진입
        if intent == "new_question" or (intent == "translation" and is_correct):
            # 정답 시 DB에 카운트 증가
            if intent == "translation" and is_correct:
                increment_correct(STATE["USER_ID"])
            
            if STATE["MODE"] == "REVIEW":
                STATE["REVIEW_INDEX"] += 1
                if STATE["REVIEW_INDEX"] < len(STATE["REVIEW_ITEMS"]):
                    # 다음 복습 문제
                    next_item = STATE["REVIEW_ITEMS"][STATE["REVIEW_INDEX"]]
                    STATE["current_question_data"] = generate_review_question(next_item)
                    response_data["system_alert"] = f"💡 다음 복습 문제입니다. ({STATE['REVIEW_INDEX'] + 1}/{len(STATE['REVIEW_ITEMS'])})"
                    response_data["next_question"] = STATE["current_question_data"]["full_guide"]
                else:
                    # 복습 종료 -> 메인 진도 시작
                    STATE["MODE"] = "MAIN"
                    STATE["current_question_data"] = generate_question(
                        STATE["LEVEL"],
                        STATE["TOPIC"],
                        STATE["TARGET_GRAMMAR"],
                        current_question=STATE.get("LAST_QUESTION_TEXT", "")
                    )
                    STATE["LAST_QUESTION_TEXT"] = STATE["current_question_data"].get("question_text", "")
                    response_data["system_alert"] = "🎉 복습이 모두 끝났습니다! 다시 메인모드로 진입합니다."
                    response_data["next_question"] = STATE["current_question_data"]["full_guide"]
                    
            else: # MAIN 모드
                # 스마트 출제: 오답 취약점 발견 시 다음 타겟 문법 강제 지정
                top_mistake = result.get("top_mistake_grammar", "")
                if top_mistake:
                    STATE["TARGET_GRAMMAR"] = top_mistake
                    response_data["system_alert"] = f"🎯 이전 오답 이력을 바탕으로 다음 문제는 '{top_mistake}' 패턴을 집중적으로 출제합니다!"
                    
                STATE["current_question_data"] = generate_question(
                    STATE["LEVEL"],
                    STATE["TOPIC"],
                    STATE["TARGET_GRAMMAR"],
                    current_question=STATE.get("LAST_QUESTION_TEXT", "")
                )
                STATE["LAST_QUESTION_TEXT"] = STATE["current_question_data"].get("question_text", "")
                response_data["next_question"] = STATE["current_question_data"]["full_guide"]
                
        else:
            # 오답인 경우 재시도 격려 메시지
            response_data["system_alert"] = "튜터의 피드백을 참고하여 다시 한 번 영작에 도전해 보세요! (패스를 원하시면 '!패스' 또는 '패스' 입력)"
            
        response_data["session_info"] = _build_session_info()
        return response_data
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "intent": "error",
            "system_alert": f"⚠️ 서버 처리 중 내부 오류가 발생했습니다: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    # 로컬 테스트용
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
