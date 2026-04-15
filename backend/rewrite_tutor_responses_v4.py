import argparse
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


BANNED_PHRASES = [
    "문맥(격식/구어체)",
    "문맥(격식 / 구어체)",
    "격식/구어체",
]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _looks_like_third_conditional(text: str) -> bool:
    t = text.lower()
    # Heuristic: If + had p.p., would/could/might have p.p.
    return (
        "if" in t
        and re.search(r"\bif\b.*\bhad\b", t) is not None
        and re.search(r"\b(would|could|might)\s+have\b", t) is not None
    )


def _looks_like_second_conditional(text: str) -> bool:
    t = text.lower()
    # Heuristic: If + past (or were), would + base.
    return (
        "if" in t
        and re.search(r"\bwould\b(?!\s+have)", t) is not None
        and "would have" not in t
    )


def is_correct_row(row: Dict[str, Any]) -> bool:
    user_answer = _norm(row.get("input", {}).get("user_answer", ""))
    correction = _norm(row.get("output", {}).get("correction", ""))
    sample_type = row.get("output", {}).get("sample_type", "")
    if sample_type in {"abstain", "question"}:
        return False
    if not correction:
        return False
    return user_answer == correction


@dataclass(frozen=True)
class EvidenceTemplate:
    locator: str
    snippet: str


def build_evidence(target_grammar: str, user_answer: str) -> List[EvidenceTemplate]:
    tg = _norm(target_grammar)
    ua = user_answer.lower()

    def ev(a: EvidenceTemplate, b: EvidenceTemplate) -> List[EvidenceTemplate]:
        return [a, b]

    if tg == "관계대명사" or tg == "형용사절":
        return ev(
            EvidenceTemplate(
                "G-RPRO-002",
                "관계대명사는 선행사가 사람/사물인지에 따라 who/which/that 등을 선택하며, 절 안에서 주어·목적어 역할을 합니다.",
            ),
            EvidenceTemplate(
                "G-RPRO-003",
                "관계대명사가 목적어 역할일 때는 생략이 가능하지만, 주어 역할이면 생략할 수 없습니다.",
            ),
        )

    if tg == "관계부사":
        return ev(
            EvidenceTemplate(
                "G-RADV-002",
                "관계부사 where/when/why는 각각 장소/시간/이유를 수식하며, 뒤에는 ‘주어+동사’가 있는 완전한 절이 옵니다.",
            ),
            EvidenceTemplate(
                "G-RADV-003",
                "where = in/at which, when = on/in which처럼 ‘전치사 + which’로도 바꿔 쓸 수 있습니다.",
            ),
        )

    if tg == "조동사":
        return ev(
            EvidenceTemplate(
                "G-MOD-002",
                "조동사(can/must/should 등) 뒤에는 동사 원형이 오며, 3인칭 단수 -s나 to를 붙이지 않습니다.",
            ),
            EvidenceTemplate(
                "G-MOD-003",
                "to는 조동사 뒤가 아니라 ‘be able to’, ‘have to’처럼 별도의 구조에서 사용됩니다.",
            ),
        )

    if tg == "수동태":
        return ev(
            EvidenceTemplate(
                "G-PASS-002",
                "수동태는 be동사 + 과거분사(p.p.) 형태로 만들고, 시제에 따라 be동사만 바뀝니다.",
            ),
            EvidenceTemplate(
                "G-PASS-003",
                "행위자를 말해야 하면 by + 행위자를 덧붙이고, 필요 없으면 생략해도 자연스럽습니다.",
            ),
        )

    if tg == "수일치":
        return ev(
            EvidenceTemplate(
                "G-AGR-002",
                "동사는 주어의 핵심 명사(head noun)의 단수/복수에 맞춥니다. 전치사구(of ~)는 보통 수를 바꾸지 않습니다.",
            ),
            EvidenceTemplate(
                "G-AGR-003",
                "everyone/each/anyone은 단수 취급이며, ‘the number of + 복수명사’는 단수 동사를 씁니다.",
            ),
        )

    if tg == "조건문":
        if _looks_like_third_conditional(user_answer):
            return ev(
                EvidenceTemplate(
                    "G-COND-THIRD-001",
                    "3형 조건문(과거 사실 반대 가정)은 If + had p.p., 결과절은 would/could/might have + p.p. 패턴을 씁니다.",
                ),
                EvidenceTemplate(
                    "G-COND-THIRD-002",
                    "if절은 ‘과거완료’, 결과절은 ‘have + p.p.’ 형태가 핵심이라, 시점(과거)을 두 절 모두에서 맞춰야 합니다.",
                ),
            )
        if _looks_like_second_conditional(user_answer):
            return ev(
                EvidenceTemplate(
                    "G-COND-SECOND-001",
                    "2형 조건문(현재/미래의 비현실 가정)은 If + 과거형, 결과절은 would/could/might + 동사원형을 씁니다.",
                ),
                EvidenceTemplate(
                    "G-COND-SECOND-002",
                    "be동사는 보통 If I were처럼 were를 자주 쓰며, 의미는 ‘지금/미래에 사실이 아닌 가정’입니다.",
                ),
            )
        return ev(
            EvidenceTemplate(
                "G-COND-002",
                "일반 조건문(1형)에서 if절은 현재시제, 주절은 will/can/may 같은 조동사를 사용해 미래를 표현합니다.",
            ),
            EvidenceTemplate(
                "G-COND-003",
                "if절에서 will은 보통 피하지만, ‘의지/요청/고집’을 강조할 때는 예외적으로 가능할 수 있습니다.",
            ),
        )

    if tg == "가정법":
        return ev(
            EvidenceTemplate(
                "G-SUBJ-002",
                "과거 사실의 반대를 가정할 때는 If + had p.p., 결과절은 would/could/might have p.p.를 씁니다.",
            ),
            EvidenceTemplate(
                "G-SUBJ-003",
                "가정하는 시점(과거/현재)에 따라 결과절 형태가 달라질 수 있어, 두 절의 시점을 함께 점검해야 합니다.",
            ),
        )

    if tg == "간접화법":
        return ev(
            EvidenceTemplate(
                "G-REP-002",
                "간접화법은 보고동사(said/told/asked 등) 뒤에서 시제·대명사·지시어를 상황에 맞게 조정합니다.",
            ),
            EvidenceTemplate(
                "G-REP-003",
                "시제의 backshift(현재→과거 등)는 ‘항상’ 의무가 아니며, 내용이 여전히 사실이면 현재시제를 유지할 수 있습니다.",
            ),
        )

    if tg == "시제":
        if "since" in ua or "for " in ua:
            return ev(
                EvidenceTemplate(
                    "G-TENSE-002",
                    "since/for로 ‘기간’이 이어질 때는 현재완료(have + p.p.)나 현재완료진행을 써서 현재까지의 지속을 표현합니다.",
                ),
                EvidenceTemplate(
                    "G-TENSE-003",
                    "현재진행형(am/is/are + -ing)은 ‘지금 진행 중’에 초점이 있어, since/for와 함께 쓰면 어색해지는 경우가 많습니다.",
                ),
            )
        if any(w in ua for w in ["yesterday", "last ", "ago"]):
            return ev(
                EvidenceTemplate(
                    "G-TENSE-004",
                    "yesterday/last/ago 같은 과거 시간 표현이 있으면 과거시제를 우선 사용합니다.",
                ),
                EvidenceTemplate(
                    "G-TENSE-005",
                    "규칙 적용 후에는 동사 형태(불규칙/규칙)까지 함께 확인해야 합니다.",
                ),
            )
        return ev(
            EvidenceTemplate(
                "G-TENSE-006",
                "문장의 기준 시점(지금/과거/완료)을 먼저 정한 뒤, 동사 시제를 그 기준에 맞춰 일관되게 맞춥니다.",
            ),
            EvidenceTemplate(
                "G-TENSE-007",
                "시간 부사(since, already, just, yet 등)는 특정 시제를 강하게 요구할 수 있으니 함께 점검합니다.",
            ),
        )

    if tg == "분사(현재/과거분사)":
        return ev(
            EvidenceTemplate(
                "G-PART-002",
                "현재분사(-ing)는 ‘능동/진행’, 과거분사(p.p.)는 ‘수동/완료’ 의미가 중심이어서 의미에 따라 선택합니다.",
            ),
            EvidenceTemplate(
                "G-PART-003",
                "명사를 꾸밀 때는 ‘무엇이 ~하는지/무엇이 ~된 상태인지’로 의미를 먼저 확인하면 실수가 줄어듭니다.",
            ),
        )

    if tg == "동명사와 TO부정사":
        return ev(
            EvidenceTemplate(
                "G-VFORM-002",
                "표현/동사마다 목적어로 동명사(-ing) 또는 to부정사를 선택하는 패턴이 정해져 있는 경우가 많습니다.",
            ),
            EvidenceTemplate(
                "G-VFORM-003",
                "look forward to에서 to는 전치사이므로, 뒤에는 동명사(meeting)가 옵니다.",
            ),
        )

    if tg == "명사절":
        return ev(
            EvidenceTemplate(
                "G-NCLS-002",
                "명사절은 평서문 어순(주어+동사)을 유지합니다. (직접의문문처럼 도치하지 않음)",
            ),
            EvidenceTemplate(
                "G-NCLS-003",
                "why/how/what 같은 의문사는 명사절을 단독으로 이끌 수 있어, that과 중복해서 쓰지 않습니다.",
            ),
        )

    if tg == "부사절":
        return ev(
            EvidenceTemplate(
                "G-ADVCLS-002",
                "시간/조건 부사절(after/before/when/as soon as/if 등)에서는 미래 의미라도 현재시제를 쓰는 경우가 많습니다.",
            ),
            EvidenceTemplate(
                "G-ADVCLS-003",
                "although는 ‘양보/대조’, because는 ‘이유’로 의미가 달라 바꿔 쓰면 뜻이 달라질 수 있습니다.",
            ),
        )

    if tg == "도치 및 강조":
        return ev(
            EvidenceTemplate(
                "G-INV-002",
                "never/rarely/hardly/only then 같은 부정·제한 어구가 문두에 오면 조동사/ be동사가 주어 앞에 옵니다.",
            ),
            EvidenceTemplate(
                "G-INV-003",
                "조동사가 없으면 do/does/did를 보조로 세워 도치합니다. (예: Never did I ...)",
            ),
        )

    if tg == "대명사":
        return ev(
            EvidenceTemplate(
                "G-PRON-002",
                "지시대명사 this/that은 단수, these/those는 복수 명사와 함께 써야 자연스럽습니다.",
            ),
            EvidenceTemplate(
                "G-PRON-003",
                "대명사는 가리키는 대상의 수/의미가 일치해야 하며, 필요하면 명사를 함께 적어 모호함을 줄입니다.",
            ),
        )

    # fallback
    return ev(
        EvidenceTemplate(
            "G-GENERAL-001",
            "문법 오류는 ‘규칙(형태) → 의미(용법) → 예문’ 순서로 점검하면 빠르게 안정화됩니다.",
        ),
        EvidenceTemplate(
            "G-GENERAL-002",
            "교정문장은 원문에서 필요한 부분만 최소 수정하고, 의미가 바뀌지 않게 유지하는 것이 원칙입니다.",
        ),
    )


ERROR_HISTORY_TEMPLATES = [
    "추가로, 이전에 {eh} 같은 실수가 있었는데 이번에도 비슷한 맥락에서 반복됐어요.",
    "과거 기록({eh})을 보면 같은 유형에서 흔들렸는데, 이번에도 같은 규칙에서 실수했네요.",
    "{eh}에 이어 이번에도 비슷한 부분을 놓치기 쉬워요. 다음엔 같은 지점을 먼저 체크해 보세요.",
]


def build_personalized_nag(error_history: str) -> str:
    eh = _norm(error_history)
    if not eh:
        return ""
    template = random.choice(ERROR_HISTORY_TEMPLATES)
    return template.format(eh=eh)


def build_explanation(target_grammar: str, user_answer: str, correction: str) -> str:
    tg = _norm(target_grammar)
    ua = _norm(user_answer)
    cor = _norm(correction)

    if not cor:
        return ""

    # Heuristics per grammar topic to avoid nonsense.
    if tg == "조동사":
        return "조동사 뒤에는 동사 원형이 오므로, 불필요한 -s나 to를 제거합니다."
    if tg == "수동태":
        return "수동태는 be동사 + 과거분사 형태가 기본이므로, 해당 형태로 고칩니다."
    if tg == "도치 및 강조":
        return "부정어/제한어구가 문두에 오면 조동사/ be동사가 주어 앞에 오도록 도치합니다."
    if tg == "수일치":
        return "주어의 수(단수/복수)에 맞춰 동사 형태를 일치시킵니다."
    if tg == "조건문":
        if _looks_like_third_conditional(ua):
            return "3형 조건문은 If + had p.p., 결과절은 would/could/might have + p.p.로 과거 사실 반대를 표현합니다."
        if _looks_like_second_conditional(ua):
            return "2형 조건문은 If + 과거형, 결과절은 would + 동사원형으로 현재/미래의 비현실 가정을 표현합니다."
        return "일반 조건문(1형)에서는 if절에 현재시제를 쓰고, 주절에 will 등을 사용합니다."
    if tg == "가정법":
        return "과거 사실 반대 가정은 If + had p.p., 결과절은 would/could/might have p.p. 패턴을 씁니다."
    if tg == "간접화법":
        return "간접화법에서는 상황에 따라 시제(backshift)를 조정하지만, 항상 강제되는 것은 아닙니다."
    if tg == "시제" and ("since" in ua.lower() or "for " in ua.lower()):
        return "since/for로 기간을 말할 때는 현재완료를 써서 현재까지의 지속을 표현합니다."
    if tg == "명사절":
        return "명사절은 평서문 어순을 유지하며, 필요한 접속사/의문사만 남기고 중복 요소는 제거합니다."
    if tg == "관계대명사" or tg == "형용사절":
        return "선행사(사람/사물)와 절의 역할에 맞는 관계사를 선택합니다."
    if tg == "관계부사":
        return "관계부사는 뒤에 완전한 절이 오도록 구성하거나, 필요하면 전치사+which로 바꿉니다."
    if tg == "동명사와 TO부정사":
        return "표현에 맞는 동사 형태(동명사/to부정사)를 선택해 자연스럽게 만듭니다."
    if tg == "부사절":
        return "부사절 접속사 의미와 시제 규칙을 함께 맞춥니다."
    if tg == "대명사":
        return "대명사는 가리키는 대상의 수(단/복수)와 의미가 일치하도록 맞춥니다."

    # fallback: keep it short and safe
    if ua != cor:
        return "핵심 문법 규칙에 맞게 필요한 부분만 최소 수정했습니다."
    return "현재 문법 규칙에 맞게 올바르게 작성된 문장입니다."


def build_tutor_feedback(is_correct: bool, target_grammar: str, error_history: str) -> str:
    tg = _norm(target_grammar)
    if is_correct:
        return "좋아요! 핵심 규칙이 잘 적용됐습니다. 같은 유형 문장을 1~2개 더 만들어 확인해 보면 완전히 굳어요."

    practice = {
        "조동사": "조동사 뒤에는 ‘동사 원형’이라고 소리 내서 체크해 보세요.",
        "수동태": "be동사 + p.p. (과거분사) 형태만 먼저 만들고, 마지막에 by-구를 붙일지 결정해 보세요.",
        "수일치": "주어의 핵심 명사가 무엇인지(예: number, group, everyone)부터 표시해 보세요.",
        "조건문": "if절에는 보통 will을 넣지 않는다고 먼저 떠올리면 실수가 줄어요.",
        "도치 및 강조": "Never/Only 같은 문두 표현이 보이면 ‘조동사 먼저!’를 체크해 보세요.",
        "명사절": "명사절은 평서문 어순이라는 점을 먼저 고정해 보세요.",
        "관계대명사": "선행사가 사람인지 사물인지 먼저 표시한 뒤 who/which/that을 고르세요.",
        "관계부사": "where/when/why 뒤에 주어+동사가 있는지 먼저 확인해 보세요.",
        "시제": "시간 표현(since/yesterday 등)을 동사 옆에 표시하고 시제를 정해 보세요.",
    }.get(tg, "비슷한 문장을 2개만 더 바꿔 써 보면 규칙이 빠르게 고정됩니다.")

    nag = build_personalized_nag(error_history)
    if nag:
        return f"{nag} {practice}"
    return practice


def build_response(evidence: List[EvidenceTemplate], explanation: str, tutor_feedback: str, correction: str) -> str:
    # Enforce the order strictly.
    e1 = evidence[0].snippet
    e2 = evidence[1].snippet if len(evidence) > 1 else ""

    if e2:
        evidence_part = f"근거: 1) {e1} 2) {e2}"
    else:
        evidence_part = f"근거: {e1}"

    feedback_sentences = " ".join([s for s in [_norm(explanation), _norm(tutor_feedback)] if s])

    return (
        f"{evidence_part}\n"
        f"피드백: {feedback_sentences}\n"
        f"교정문장: {correction if correction else '해당 없음'}"
    )


def rewrite_row(row: Dict[str, Any]) -> Dict[str, Any]:
    inp = row.get("input", {})
    out = row.get("output", {})

    target_grammar = inp.get("target_grammar", "")
    user_answer = inp.get("user_answer", "")
    correction = out.get("correction", "")
    error_history = inp.get("error_history", "")

    sample_type = out.get("sample_type", "")
    # Keep abstain/question mostly as-is; just sanitize banned phrases.
    if sample_type in {"abstain", "question"}:
        # Remove banned phrase if accidentally present.
        resp = out.get("response", "")
        for bp in BANNED_PHRASES:
            resp = resp.replace(bp, "")
        out["response"] = resp
        row["output"] = out
        return row

    correct = is_correct_row(row)

    evidence_tpls = build_evidence(str(target_grammar), str(user_answer))
    evidence_objs = [
        {
            "source_type": "rag",
            "title": "English Grammar Core Rules v2",
            "locator": e.locator,
            "snippet": e.snippet,
        }
        for e in evidence_tpls
    ]

    explanation = build_explanation(str(target_grammar), str(user_answer), str(correction))
    tutor_feedback = build_tutor_feedback(correct, str(target_grammar), str(error_history))

    # Keep correction unchanged; if correct sample has correction equal to user_answer.
    response = build_response(evidence_tpls, explanation, tutor_feedback, str(correction))

    # Final safety: remove banned parroting phrases.
    for bp in BANNED_PHRASES:
        response = response.replace(bp, "")
        explanation = explanation.replace(bp, "")
        tutor_feedback = tutor_feedback.replace(bp, "")
        for eo in evidence_objs:
            eo["snippet"] = eo["snippet"].replace(bp, "")

    out["evidence"] = evidence_objs
    out["explanation"] = explanation
    out["tutor_feedback"] = tutor_feedback
    out["response"] = response

    row["output"] = out
    return row


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def quick_checks(path: Path) -> Dict[str, Any]:
    banned_hits = 0
    format_ok = 0
    total = 0

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            total += 1
            row = json.loads(line)
            resp = row.get("output", {}).get("response", "")
            if any(bp in resp for bp in BANNED_PHRASES):
                banned_hits += 1
            # order check
            idx_e = resp.find("근거:")
            idx_f = resp.find("피드백:")
            idx_c = resp.find("교정문장:")
            if idx_e != -1 and idx_f != -1 and idx_c != -1 and idx_e < idx_f < idx_c:
                format_ok += 1

    return {
        "total": total,
        "banned_hits": banned_hits,
        "format_ok": format_ok,
        "format_ok_rate": (format_ok / total) if total else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", dest="out_path", required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)

    rows_out: List[Dict[str, Any]] = []
    for row in iter_jsonl(in_path):
        rows_out.append(rewrite_row(row))

    write_jsonl(out_path, rows_out)

    checks = quick_checks(out_path)
    print(json.dumps({"written": str(out_path), **checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
