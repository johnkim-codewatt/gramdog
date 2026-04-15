package com.example.aitestapp

import android.content.Context
import com.google.ai.edge.litertlm.Engine
import com.google.ai.edge.litertlm.EngineConfig
import com.google.ai.edge.litertlm.LogSeverity
import org.junit.Test

import org.junit.Assert.*
import java.io.File
import kotlin.use

/**
 * Example local unit test, which will execute on the development machine (host).
 *
 * See [testing documentation](http://d.android.com/tools/testing).
 */
class ExampleUnitTest {
    @Test
    fun addition_isCorrect() {
        assertEquals(4, 2 + 2)
    }

    @Test
    fun mainTest() = kotlinx.coroutines.runBlocking {
        Engine.setNativeMinLogSeverity(LogSeverity.ERROR) // Hide log for TUI app

        val engineConfig = EngineConfig(modelPath = "src/main/assets/gemma-4-E2B-it.litertlm")
        Engine(engineConfig).use { engine ->
            engine.initialize()

            engine.createConversation().use { conversation ->
                while (true) {
                    print("\n>>> ")
                    conversation.sendMessageAsync(readln()).collect {
                        print(it)
                    }
                }
            }
        }
    }





}