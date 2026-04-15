package com.example.aitestapp.ui

enum class AppPhase {
    SPLASH,
    SETUP_LEVEL,
    SETUP_TOPIC,
    SETUP_GRAMMAR,
    CHAT
}

enum class LineType {
    SYSTEM,
    USER,
    TUTOR,
    ERROR
}

data class UiLine(
    val type: LineType,
    val text: String
)

data class GrammarItem(
    val id: String,
    val name: String
)

enum class ModalEvent {
    LEVEL_UP,
    LEVEL_DOWN
}

val LEVEL_LIST = listOf("초급", "중급", "고급", "네이티브")
val TOPIC_LIST = listOf("일상", "비즈니스", "여행", "학교", "연애", "취미")
val GRAMMAR_LIST = listOf(
    GrammarItem("random", "랜덤"),
    GrammarItem("can/could_usage", "can/could 사용법"),
    GrammarItem("must/have_to_usage", "must/have to 사용법"),
    GrammarItem("would_usage", "would 사용법"),
    GrammarItem("wish_past_simple_usage", "wish + 과거형"),
    GrammarItem("should_have_p.p._usage", "should have + 과거분사"),
    GrammarItem("infinitive_as_subject", "주어로 쓰인 to부정사"),
    GrammarItem("gerund_as_subject", "주어로 쓰인 동명사"),
    GrammarItem("infinitive_of_purpose", "목적을 나타내는 to부정사"),
    GrammarItem("participle_construction", "분사구문"),
    GrammarItem("gerund_as_object", "목적어로 쓰인 동명사"),
    GrammarItem("article_definite", "정관사"),
    GrammarItem("article_indefinite", "부정관사"),
    GrammarItem("adjective_comparative", "형용사 비교급"),
    GrammarItem("simple_past_structure", "과거형 문장 구조"),
    GrammarItem("passive_voice_structure", "수동태 구조"),
    GrammarItem("complex_sentence_structure", "복문 구조"),
    GrammarItem("compound_sentence_structure", "병렬 구조")
)

private val levelGrammarPools = mapOf(
    "초급" to listOf(
        "can/could_usage",
        "must/have_to_usage",
        "infinitive_of_purpose",
        "article_definite",
        "article_indefinite",
        "simple_past_structure"
    ),
    "중급" to listOf(
        "would_usage",
        "gerund_as_subject",
        "gerund_as_object",
        "adjective_comparative",
        "passive_voice_structure",
        "compound_sentence_structure"
    ),
    "고급" to listOf(
        "wish_past_simple_usage",
        "should_have_p.p._usage",
        "infinitive_as_subject",
        "participle_construction",
        "complex_sentence_structure"
    ),
    "네이티브" to listOf(
        "wish_past_simple_usage",
        "should_have_p.p._usage",
        "participle_construction",
        "complex_sentence_structure",
        "compound_sentence_structure"
    )
)

fun grammarListForLevel(level: String): List<GrammarItem> {
    val allowedIds = levelGrammarPools[level]?.toSet().orEmpty()
    val filtered = GRAMMAR_LIST.filter { it.id == "random" || allowedIds.contains(it.id) }
    return if (filtered.isNotEmpty()) filtered else GRAMMAR_LIST
}
