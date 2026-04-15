package com.example.aitestapp.network

import com.example.aitestapp.ui.ModalEvent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.nio.charset.StandardCharsets

class BackendApiClient(
    private val baseUrl: String,
    private val tempUserId: String
) {
    suspend fun initSession(level: String, topic: String, grammar: String): InitResponse = withContext(Dispatchers.IO) {
        val json = request(
            path = "/api/init",
            method = "GET",
            query = mapOf(
                "level" to level,
                "topic" to topic,
                "grammar" to grammar
            )
        )
        InitResponse(
            message = json.optString("message"),
            guide = json.optString("guide"),
            questionText = json.optString("question"),
            sessionInfo = json.optJSONObject("session_info")?.toSessionInfo()
        )
    }

    suspend fun sendCommand(commandType: String, commandValue: String): CommandResponse = withContext(Dispatchers.IO) {
        val body = JSONObject().apply {
            put("command_type", commandType)
            put("command_value", commandValue)
        }
        val json = request(
            path = "/api/command",
            method = "POST",
            body = body
        )
        CommandResponse(
            message = json.optString("message"),
            nextQuestion = json.optString("next_question").ifBlank { null },
            sessionInfo = json.optJSONObject("session_info")?.toSessionInfo()
        )
    }

    suspend fun chat(userInput: String): ChatResponse = withContext(Dispatchers.IO) {
        val body = JSONObject().apply {
            put("user_input", userInput)
        }
        val json = request(
            path = "/api/chat",
            method = "POST",
            body = body
        )
        val event = when (json.optString("event")) {
            "LEVEL_UP" -> ModalEvent.LEVEL_UP
            "LEVEL_DOWN" -> ModalEvent.LEVEL_DOWN
            else -> null
        }
        ChatResponse(
            feedback = json.opt("feedback")?.toFeedbackText()?.ifBlank { null },
            nextQuestion = json.optString("next_question").ifBlank { null },
            systemAlert = json.optString("system_alert").ifBlank { null },
            event = event,
            sessionInfo = json.optJSONObject("session_info")?.toSessionInfo()
        )
    }

    private fun request(
        path: String,
        method: String,
        query: Map<String, String> = emptyMap(),
        body: JSONObject? = null
    ): JSONObject {
        val queryString = if (query.isEmpty()) {
            ""
        } else {
            query.entries.joinToString("&") {
                "${it.key.urlEncode()}=${it.value.urlEncode()}"
            }
        }
        val fullUrl = buildString {
            append(baseUrl.trimEnd('/'))
            append(path)
            if (queryString.isNotEmpty()) {
                append("?")
                append(queryString)
            }
        }
        val connection = URL(fullUrl).openConnection() as HttpURLConnection
        connection.requestMethod = method
        connection.connectTimeout = 15000
        connection.readTimeout = 20000
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("X-Temp-User-Id", tempUserId)
        if (method == "POST") {
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            val payload = body?.toString().orEmpty()
            connection.outputStream.use { output ->
                output.write(payload.toByteArray(StandardCharsets.UTF_8))
            }
        }

        val statusCode = connection.responseCode
        val bodyText = try {
            val stream = if (statusCode in 200..299) connection.inputStream else connection.errorStream
            stream?.bufferedReader()?.use(BufferedReader::readText).orEmpty()
        } finally {
            connection.disconnect()
        }

        if (statusCode !in 200..299) {
            throw IOException("HTTP $statusCode: ${bodyText.ifBlank { "응답 본문 없음" }}")
        }
        if (bodyText.isBlank()) {
            return JSONObject()
        }
        return JSONObject(bodyText)
    }
}

private fun JSONObject.toSessionInfo(): SessionInfo {
    return SessionInfo(
        user = optString("user"),
        level = optString("level"),
        topic = optString("topic"),
        mode = optString("mode").ifBlank { null },
        reviewProgress = optString("review_progress").ifBlank { null },
        correctCount = if (has("correct_count")) optInt("correct_count") else null,
        incorrectCount = if (has("incorrect_count")) optInt("incorrect_count") else null,
        currentGauge = if (has("current_gauge")) optInt("current_gauge") else null
    )
}

private fun Any.toFeedbackText(): String {
    return when (this) {
        is String -> this
        is Number, is Boolean -> toString()
        is JSONArray -> {
            (0 until length())
                .map { index -> opt(index)?.toFeedbackText().orEmpty().trim() }
                .filter { it.isNotBlank() }
                .joinToString("\n")
        }
        is JSONObject -> {
            val sections = listOf(
                "피드백" to opt("feedback"),
                "교정 문장" to opt("corrected_text"),
                "핵심 문법" to opt("grammar_tag"),
                "설명" to opt("explanation"),
                "더 자연스러운 표현" to opt("better_expression"),
                "과거 이력 비교" to opt("history_comment")
            ).mapNotNull { (title, value) ->
                val content = value?.toFeedbackText()?.trim().orEmpty()
                if (content.isBlank()) null else "[$title]\n$content"
            }
            if (sections.isNotEmpty()) sections.joinToString("\n\n") else toString()
        }
        else -> toString()
    }
}

private fun String.urlEncode(): String = URLEncoder.encode(this, StandardCharsets.UTF_8.toString())
