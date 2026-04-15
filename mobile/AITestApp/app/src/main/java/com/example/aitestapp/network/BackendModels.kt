package com.example.aitestapp.network

import com.example.aitestapp.ui.ModalEvent

data class SessionInfo(
    val user: String = "",
    val level: String = "",
    val topic: String = "",
    val mode: String? = null,
    val reviewProgress: String? = null,
    val correctCount: Int? = null,
    val incorrectCount: Int? = null,
    val currentGauge: Int? = null
)

data class InitResponse(
    val message: String,
    val guide: String,
    /** 영작 문제 한 문장(의도 모델 `<q>` 구간). 서버 `question` 필드 */
    val questionText: String,
    val sessionInfo: SessionInfo?
)

data class CommandResponse(
    val message: String,
    val nextQuestion: String?,
    val sessionInfo: SessionInfo?
)

data class ChatResponse(
    val feedback: String?,
    val nextQuestion: String?,
    val systemAlert: String?,
    val event: ModalEvent?,
    val sessionInfo: SessionInfo?
)
