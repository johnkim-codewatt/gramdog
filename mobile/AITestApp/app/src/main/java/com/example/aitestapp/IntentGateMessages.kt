package com.example.aitestapp

/** translation이 아닐 때 안내 + 자동 패스용 멘트 */
object IntentGateMessages {
    const val ENGSTUDY =
        "문법·학습 질문으로 보여요. 영작 채점은 건너뛰고 다음 문제로 넘어갈게요."

    const val FREETALK =
        "잡담으로 보여요. 지금은 영작 연습에 집중해 주세요. 다음 문제로 넘어갈게요."

    const val UNKNOWN =
        "의도를 확실히 알기 어려워요. 다음 문제로 넘어갈게요."

    const val MODEL_ERROR =
        "기기에서 의도를 분류할 수 없어요. 다음 문제로 넘어갈게요."

    fun guideForClassId(classId: Int): String = when (classId) {
        0 -> ENGSTUDY
        1 -> FREETALK
        3 -> UNKNOWN
        else -> UNKNOWN
    }

    fun trainingTag(classId: Int): String = when (classId) {
        0 -> "engstudy"
        1 -> "freetalk"
        2 -> "translation"
        3 -> "unknown"
        else -> "unknown"
    }
}
