package com.example.aitestapp

import android.content.Context
import java.io.BufferedReader
import java.io.InputStreamReader

class WordPieceTokenizer(context: Context, vocabFileName: String = "vocab.txt") {
    private val vocab = mutableMapOf<String, Long>()
    private val clsTokenId: Long
    private val sepTokenId: Long
    private val padTokenId: Long

    init {
        // assets에서 단어장 로드
        val inputStream = context.assets.open(vocabFileName)
        val reader = BufferedReader(InputStreamReader(inputStream))
        var index = 0L
        reader.forEachLine { line ->
            vocab[line] = index++
        }
        reader.close()
        
        clsTokenId = vocab["[CLS]"] ?: 5L
        sepTokenId = vocab["[SEP]"] ?: 4L
        padTokenId = vocab["[PAD]"] ?: 0L
    }

    // 문장을 숫자로 분해하는 메인 함수
    fun tokenize(text: String, maxLength: Int = 128): Pair<LongArray, LongArray> {
        val tokens = mutableListOf<Long>()
        tokens.add(clsTokenId) // 문장 시작 표시 알림

        // 띄어쓰기 및 임시 특수문자 완벽 분리 (아주 중요: <, >, /, 구두점 등 모두 분리)
        val cleanedText = text.replace(Regex("([^가-힣a-zA-Z0-9])")) { " ${it.value} " }
        val words = cleanedText.trim().split("\\s+".toRegex())

        for (word in words) {
            if (word.isEmpty()) continue
            
            var isBad = false
            var start = 0
            val subTokens = mutableListOf<Long>()
            
            while (start < word.length) {
                var end = word.length
                var curToken: Long? = null
                
                while (start < end) {
                    val substr = word.substring(start, end)
                    val prefix = if (start > 0) "##$substr" else substr
                    if (vocab.containsKey(prefix)) {
                        curToken = vocab[prefix]
                        break
                    }
                    end--
                }
                
                if (curToken == null) {
                    isBad = true
                    break
                }
                
                subTokens.add(curToken)
                start = end
            }
            
            // 모르는 단어 분리 실패 처리
            if (isBad) tokens.add(vocab["[UNK]"] ?: 1L)
            else tokens.addAll(subTokens)
            
            if (tokens.size >= maxLength - 1) break
        }

        tokens.add(sepTokenId) // 문장 종료 알림

        // [128] 크기로 규격 맞추기 (남는 공간은 PAD(0)으로 채우기)
        val inputIds = LongArray(maxLength) { padTokenId }
        val attentionMask = LongArray(maxLength) { 0L }
        
        for (i in 0 until minOf(tokens.size, maxLength)) {
            inputIds[i] = tokens[i]
            attentionMask[i] = 1L // 실제 단어가 있는 곳은 1로 체크해 줍니다
        }
        
        return Pair(inputIds, attentionMask)
    }
}
