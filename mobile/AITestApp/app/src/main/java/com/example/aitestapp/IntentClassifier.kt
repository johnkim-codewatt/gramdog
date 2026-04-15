package com.example.aitestapp

import android.content.Context
import android.util.Log
import org.tensorflow.lite.Interpreter

//package com.example.aitestapp
//
//import android.content.Context
//import android.util.Log
//import org.tensorflow.lite.Interpreter
//import java.io.FileInputStream
//import java.nio.MappedByteBuffer
//import java.nio.channels.FileChannel
//
//class IntentClassifier(context: Context) {
//    private var interpreter: Interpreter? = null
//
//    init {
//        try {
//            // assets 폴더에서 tflite 모델 로드
//            val modelBuffer = loadModelFile(context, "intent_classifier.tflite")
//            val options = Interpreter.Options()
//
//            interpreter = Interpreter(modelBuffer, options)
//            Log.d("TFLite", "✅ 모델 로드 성공!")
//        } catch (e: Exception) {
//            Log.e("TFLite", "❌ 모델 로드 실패: ${e.message}")
//        }
//    }
//
//    private fun loadModelFile(context: Context, modelName: String): MappedByteBuffer {
//        val fileDescriptor = context.assets.openFd(modelName)
//        val inputStream = FileInputStream(fileDescriptor.fileDescriptor)
//        val fileChannel = inputStream.channel
//        return fileChannel.map(
//            FileChannel.MapMode.READ_ONLY,
//            fileDescriptor.startOffset,
//            fileDescriptor.declaredLength
//        )
//    }
//
//    // 모델 생사 확인용 테스트 추론 함수
//    fun testInference() {
//        interpreter?.let {
//            // 파이썬 환경과 동일한 [1, 128] 규격의 입력 데이터(Long) 준비
//            val dummyInputIds = Array(1) { LongArray(128) { 0L } } // 빈 값으로 채움
//            val dummyAttentionMask = Array(1) { LongArray(128) { 1L } } // 모두 1 처리
//
//            // 입력값을 Object 배열로 묶기
//            val inputs = arrayOf<Any>(dummyInputIds, dummyAttentionMask)
//
//            // 결과값을 담을 [1, 4] 규격의 Float 배열
//            val outputLogits = Array(1) { FloatArray(4) }
//            val outputs = mutableMapOf<Int, Any>(0 to outputLogits)
//
//            // ✨ 모델 추론 실행!
//            it.runForMultipleInputsOutputs(inputs, outputs)
//
//            // 결과 확인
//            val result = outputLogits[0]
//            Log.d("TFLite", """
//                🎉 추론 완료!
//                engstudy: ${result[0]}
//                freetalk: ${result[1]}
//                translation: ${result[2]}
//                unknown: ${result[3]}
//            """.trimIndent())
//        } ?: Log.e("TFLite", "모델이 아직 메모리에 안 올라왔습니다.")
//    }
//
//    fun close() {
//        interpreter?.close()
//    }
//}



class IntentClassifier(context: Context) {
    private var interpreter: Interpreter? = null
    // ✨ 번역기 등반!
    private var tokenizer: WordPieceTokenizer? = null

    init {
        try {
            // assets 폴더에서 tflite 모델 로드
            val modelBuffer = loadModelFile(context, "intent_classifier.tflite")
            val options = Interpreter.Options()
            
            interpreter = Interpreter(modelBuffer, options)
            Log.d("TFLite", "✅ 모델 로드 성공!")
            
            // 초기화 시점에 토크나이저도 객체 생성!
            tokenizer = WordPieceTokenizer(context)
        } catch (e: Exception) {
            Log.e("TFLite", "❌ 모델 로드 실패: ${e.message}")
        }
    }

    private fun loadModelFile(context: Context, modelName: String): java.nio.MappedByteBuffer {
        val fileDescriptor = context.assets.openFd(modelName)
        val inputStream = java.io.FileInputStream(fileDescriptor.fileDescriptor)
        val fileChannel = inputStream.channel
        return fileChannel.map(
            java.nio.channels.FileChannel.MapMode.READ_ONLY,
            fileDescriptor.startOffset,
            fileDescriptor.declaredLength
        )
    }

    /** 문제 stem + 유저 입력 → 의도 클래스(0~3) 및 UI 라벨 */
    fun classifyIntent(question: String, userInput: String): IntentOutcome {
        val currentInterpreter = interpreter
            ?: return IntentOutcome.LoadError("모델 로드 안 됨")
        val currentTokenizer = tokenizer
            ?: return IntentOutcome.LoadError("토크나이저 로드 안 됨")

        val text = "<q>$question</q> <u>$userInput</u>"
        val (inputArray, maskArray) = currentTokenizer.tokenize(text)
        val inputIds = arrayOf(inputArray)
        val attentionMask = arrayOf(maskArray)
        val inputs = arrayOf<Any>(inputIds, attentionMask)

        val outputLogits = Array(1) { FloatArray(4) }
        val outputs = mutableMapOf<Int, Any>(0 to outputLogits)
        currentInterpreter.runForMultipleInputsOutputs(inputs, outputs)

        val result = outputLogits[0]
        var maxIndex = 0
        var maxValue = result[0]
        for (i in 1 until result.size) {
            if (result[i] > maxValue) {
                maxValue = result[i]
                maxIndex = i
            }
        }

        val labelForUi = when (maxIndex) {
            0 -> "영어공부 질문"
            1 -> "잡담 및 농담"
            2 -> "번역·영작 시도"
            3 -> "판별 불가(기타)"
            else -> "판별 불가"
        }

        Log.d("TFLite", """
            === AI 의도 분석 ===
            텍스트: "$text"
            의도: $labelForUi (class=$maxIndex)
            logits -> eng: ${result[0]} / free: ${result[1]} / trans: ${result[2]} / unk: ${result[3]}
        """.trimIndent())

        return IntentOutcome.Ok(classId = maxIndex, labelForUi = labelForUi)
    }

    fun close() {
        interpreter?.close()
        interpreter = null
    }
}
