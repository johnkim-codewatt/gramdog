package com.example.aitestapp

/** TFLite 의도 분류 결과. 학습 label_map: 0 engstudy, 1 freetalk, 2 translation, 3 unknown */
sealed class IntentOutcome {
    data class Ok(
        val classId: Int,
        val labelForUi: String,
    ) : IntentOutcome()

    data class LoadError(
        val message: String,
    ) : IntentOutcome()

    companion object {
        const val CLASS_TRANSLATION = 2
    }
}
