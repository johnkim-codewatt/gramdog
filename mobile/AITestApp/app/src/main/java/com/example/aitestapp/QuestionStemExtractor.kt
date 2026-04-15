package com.example.aitestapp

/**
 * 서버 `guide` / `next_question`은 [core_engine.generate_question]의 full_guide로,
 * 학습 데이터의 `<q>…</q>`에는 **영작 한 문장(question_text)** 만 들어가야 한다.
 * 전체 guide를 넣으면 128토큰에서 `<u>유저답</u>`이 잘려 항상 unknown에 가깝게 나온다.
 */
object QuestionStemExtractor {
    private val sectionHeader = Regex("""5\.\s*영작\s*문제.*""", RegexOption.IGNORE_CASE)

    fun fromGuide(guide: String): String {
        val lines = guide.lines()
        val idx = lines.indexOfFirst { sectionHeader.matches(it.trim()) }
        if (idx >= 0 && idx + 1 < lines.size) {
            val body = lines
                .drop(idx + 1)
                .dropWhile { it.isBlank() }
                .takeWhile { it.isNotBlank() }
                .joinToString("\n")
                .trim()
            if (body.isNotBlank()) return body
        }
        return guide.trim()
    }
}
