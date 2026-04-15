package com.example.aitestapp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.BorderStroke
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ElevatedButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aitestapp.network.BackendApiClient
import com.example.aitestapp.network.SessionInfo
import com.example.aitestapp.ui.AppPhase
import com.example.aitestapp.ui.LEVEL_LIST
import com.example.aitestapp.ui.LineType
import com.example.aitestapp.ui.ModalEvent
import com.example.aitestapp.ui.TOPIC_LIST
import com.example.aitestapp.ui.UiLine
import com.example.aitestapp.ui.grammarListForLevel
import com.example.aitestapp.ui.theme.AITestAppTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            AITestAppTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    TutorApp(modifier = Modifier.padding(innerPadding))
                }
            }
        }
    }
}

@Composable
fun TutorApp(modifier: Modifier = Modifier) {
    val appContext = LocalContext.current.applicationContext
    val apiClient = remember { BackendApiClient(BuildConfig.BACKEND_BASE_URL, BuildConfig.TEMP_USER_ID) }
    val intentClassifier = remember { IntentClassifier(appContext) }
    DisposableEffect(Unit) {
        onDispose { intentClassifier.close() }
    }
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()

    var phase by rememberSaveable { mutableStateOf(AppPhase.SPLASH) }
    var inputText by rememberSaveable { mutableStateOf("") }
    var loading by rememberSaveable { mutableStateOf(false) }
    var selectedLevel by rememberSaveable { mutableStateOf("") }
    var selectedTopic by rememberSaveable { mutableStateOf("") }
    var modalEvent by remember { mutableStateOf<ModalEvent?>(null) }
    var session by remember { mutableStateOf<SessionInfo?>(null) }
    /** 영작 문제 문장만 — 학습 `<q>`와 동일. full_guide 넣으면 128토큰 밖으로 유저 답이 잘림 */
    var lastQuestionStemForIntent by remember { mutableStateOf<String?>(null) }
    val lines = remember { mutableStateListOf<UiLine>() }

    fun appendLine(type: LineType, text: String) {
        lines.add(UiLine(type, text))
    }

    fun showTopicOptions() {
        appendLine(LineType.SYSTEM, "[Sys] 오늘의 학습 주제를 선택해 주세요.")
        TOPIC_LIST.forEachIndexed { index, topic ->
            appendLine(LineType.SYSTEM, "[T${index + 1}] $topic")
        }
    }

    fun showGrammarOptions(level: String) {
        appendLine(LineType.SYSTEM, "[Sys] 이어서 집중 학습할 문법을 선택해 주세요.")
        grammarListForLevel(level).forEachIndexed { index, grammar ->
            appendLine(LineType.SYSTEM, "[G${index + 1}] ${grammar.name}")
        }
    }

    suspend fun initChatPhase(grammarId: String, grammarName: String) {
        val grammarValue = if (grammarId == "random") "리셋" else grammarId
        loading = true
        phase = AppPhase.CHAT
        appendLine(LineType.SYSTEM, "[Sys] '$grammarName' 문법이 선택되었습니다.")
        appendLine(LineType.SYSTEM, "[Sys] 서버 초기화 중...")
        try {
            val response = apiClient.initSession(
                level = selectedLevel,
                topic = selectedTopic,
                grammar = grammarValue
            )
            session = response.sessionInfo ?: session
            appendLine(LineType.SYSTEM, "[Sys] ${response.message}")
            lastQuestionStemForIntent = response.questionText.ifBlank {
                QuestionStemExtractor.fromGuide(response.guide)
            }
            appendLine(LineType.TUTOR, "[📝 Question]\n${response.guide}")
        } catch (e: Exception) {
            appendLine(LineType.ERROR, "[Error] 초기화 실패: ${e.message ?: "알 수 없는 오류"}")
        } finally {
            loading = false
        }
    }

    suspend fun handleCommand(input: String) {
        val trimmed = input.removePrefix("!").trim()
        if (trimmed.isBlank()) {
            appendLine(LineType.ERROR, "[Error] 명령어가 비어 있습니다.")
            return
        }

        val parts = trimmed.split(" ", limit = 2)
        val commandType = parts[0]
        val commandValue = if (parts.size > 1) parts[1] else ""
        loading = true
        try {
            val response = apiClient.sendCommand(commandType, commandValue)
            session = response.sessionInfo ?: session
            appendLine(LineType.SYSTEM, "[Sys] ${response.message}")
            response.nextQuestion?.let {
                lastQuestionStemForIntent = QuestionStemExtractor.fromGuide(it)
                appendLine(LineType.TUTOR, "[📝 Next Question]\n$it")
            }
        } catch (e: Exception) {
            appendLine(LineType.ERROR, "[Error] 명령어 처리 실패: ${e.message ?: "알 수 없는 오류"}")
        } finally {
            loading = false
        }
    }

    suspend fun handleChat(text: String) {
        loading = true
        try {
            val response = apiClient.chat(text)
            session = response.sessionInfo ?: session
            modalEvent = response.event ?: modalEvent
            response.feedback?.let {
                appendLine(LineType.TUTOR, "[Tutor Feedback]\n$it")
            }
            response.systemAlert?.let {
                appendLine(LineType.SYSTEM, "[Sys] $it")
            }
            response.nextQuestion?.let {
                lastQuestionStemForIntent = QuestionStemExtractor.fromGuide(it)
                appendLine(LineType.TUTOR, "[📝 Next Question]\n$it")
            }
        } catch (e: Exception) {
            appendLine(LineType.ERROR, "[Error] 서버 응답 실패: ${e.message ?: "알 수 없는 오류"}")
        } finally {
            loading = false
        }
    }

    fun handleLevelSelection(value: String) {
        val cleaned = value.trim()
        val indexed = cleaned.removePrefix("L").toIntOrNull()?.let { index ->
            LEVEL_LIST.getOrNull(index - 1)
        }
        val level = indexed ?: LEVEL_LIST.find { it == cleaned }
        if (level == null) {
            appendLine(LineType.ERROR, "[Error] 올바른 레벨을 선택해 주세요.")
            return
        }
        selectedLevel = level
        appendLine(LineType.USER, "C:\\USER> $cleaned")
        appendLine(LineType.SYSTEM, "[Sys] '$level' 레벨이 선택되었습니다.")
        phase = AppPhase.SETUP_TOPIC
        showTopicOptions()
    }

    fun handleTopicSelection(value: String) {
        val cleaned = value.trim()
        val indexed = cleaned.removePrefix("T").toIntOrNull()?.let { index ->
            TOPIC_LIST.getOrNull(index - 1)
        }
        val topic = indexed ?: TOPIC_LIST.find { it == cleaned }
        if (topic == null) {
            appendLine(LineType.ERROR, "[Error] 올바른 주제를 선택해 주세요.")
            return
        }
        selectedTopic = topic
        appendLine(LineType.USER, "C:\\USER> $cleaned")
        appendLine(LineType.SYSTEM, "[Sys] '$topic' 주제가 선택되었습니다.")
        phase = AppPhase.SETUP_GRAMMAR
        showGrammarOptions(selectedLevel)
    }

    fun handleGrammarSelection(value: String) {
        val cleaned = value.trim()
        val grammarPool = grammarListForLevel(selectedLevel)
        val indexed = cleaned.removePrefix("G").toIntOrNull()?.let { index ->
            grammarPool.getOrNull(index - 1)
        }
        val grammar = indexed ?: grammarPool.find { it.name == cleaned }
        if (grammar == null) {
            appendLine(LineType.ERROR, "[Error] 올바른 문법을 선택해 주세요.")
            return
        }
        appendLine(LineType.USER, "C:\\USER> $cleaned")
        scope.launch { initChatPhase(grammar.id, grammar.name) }
    }

    fun submitInput() {
        if (loading || inputText.isBlank()) return
        val current = inputText.trim()
        inputText = ""
        when (phase) {
            AppPhase.SETUP_LEVEL -> handleLevelSelection(current)
            AppPhase.SETUP_TOPIC -> handleTopicSelection(current)
            AppPhase.SETUP_GRAMMAR -> handleGrammarSelection(current)
            AppPhase.CHAT -> {
                appendLine(LineType.USER, "C:\\USER> $current")
                scope.launch {
                    if (current == "패스" || current == "!패스") {
                        handleChat("패스")
                    } else if (current.startsWith("!")) {
                        handleCommand(current)
                    } else {
                        val q = lastQuestionStemForIntent
                        if (q.isNullOrBlank()) {
                            appendLine(
                                LineType.ERROR,
                                "[Error] 저장된 출제 문항이 없어 분류할 수 없습니다."
                            )
                            return@launch
                        }
                        loading = true
                        try {
                            val outcome = withContext(Dispatchers.Default) {
                                intentClassifier.classifyIntent(q, current)
                            }
                            when (outcome) {
                                is IntentOutcome.LoadError -> {
                                    appendLine(LineType.SYSTEM, "[Intent·기기] ${IntentGateMessages.MODEL_ERROR}")
                                    handleChat("패스")
                                }
                                is IntentOutcome.Ok -> {
                                    val tag = IntentGateMessages.trainingTag(outcome.classId)
                                    appendLine(
                                        LineType.SYSTEM,
                                        "[Intent·기기] ${outcome.labelForUi} · $tag"
                                    )
                                    if (outcome.classId == IntentOutcome.CLASS_TRANSLATION) {
                                        handleChat(current)
                                    } else {
                                        appendLine(
                                            LineType.SYSTEM,
                                            IntentGateMessages.guideForClassId(outcome.classId)
                                        )
                                        handleChat("패스")
                                    }
                                }
                            }
                        } finally {
                            loading = false
                        }
                    }
                }
            }
            AppPhase.SPLASH -> Unit
        }
    }

    LaunchedEffect(phase) {
        if (phase == AppPhase.SPLASH) {
            delay(1500)
            phase = AppPhase.SETUP_LEVEL
            lines.clear()
            lastQuestionStemForIntent = null
            appendLine(LineType.SYSTEM, "AI 영작 튜터 시스템에 연결되었습니다.")
            appendLine(LineType.SYSTEM, "[Sys] 임시 사용자(${BuildConfig.TEMP_USER_ID})로 시작합니다.")
            appendLine(LineType.SYSTEM, "[Sys] 학습 레벨을 선택해 주세요.")
            LEVEL_LIST.forEachIndexed { index, level ->
                appendLine(LineType.SYSTEM, "[L${index + 1}] $level")
            }
        }
    }

    LaunchedEffect(lines.size, loading) {
        if (lines.isNotEmpty()) {
            listState.animateScrollToItem(lines.lastIndex)
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFFF5F5F7))
    ) {
        TopHeader(phase = phase, loading = loading, session = session)
        HorizontalDivider(color = Color(0xFFE3E5E8))

        if (phase == AppPhase.SPLASH) {
            SplashScreen()
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(horizontal = 14.dp),
                contentPadding = PaddingValues(vertical = 14.dp)
            ) {
                items(lines.size) { index ->
                    Bubble(line = lines[index])
                }
            }

            SetupOptions(
                phase = phase,
                selectedLevel = selectedLevel,
                onLevel = ::handleLevelSelection,
                onTopic = ::handleTopicSelection,
                onGrammar = ::handleGrammarSelection
            )

            InputBar(
                phase = phase,
                text = inputText,
                loading = loading,
                onTextChange = { inputText = it },
                onSubmit = ::submitInput
            )
        }
    }

    if (modalEvent != null) {
        AlertDialog(
            onDismissRequest = { modalEvent = null },
            title = {
                Text(
                    text = if (modalEvent == ModalEvent.LEVEL_UP) "축하합니다!" else "주의가 필요해요",
                    fontWeight = FontWeight.Bold
                )
            },
            text = {
                Text(
                    text = if (modalEvent == ModalEvent.LEVEL_UP) {
                        "게이지 100% 달성! 다음 레벨로 도전하세요."
                    } else {
                        "게이지가 0%에 도달했습니다. 피드백을 반영해 다시 도전해 보세요."
                    }
                )
            },
            confirmButton = {
                Button(onClick = { modalEvent = null }) {
                    Text("확인")
                }
            }
        )
    }
}

@Composable
private fun TopHeader(phase: AppPhase, loading: Boolean, session: SessionInfo?) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color.White)
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        Text(
            text = "AI 영작 튜터 - Grammar Dog",
            fontWeight = FontWeight.ExtraBold,
            fontSize = 20.sp,
            color = Color(0xFF1D1D1F)
        )
        Spacer(Modifier.height(4.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = when (phase) {
                    AppPhase.SETUP_LEVEL -> "레벨 선택"
                    AppPhase.SETUP_TOPIC -> "주제 선택"
                    AppPhase.SETUP_GRAMMAR -> "문법 선택"
                    AppPhase.CHAT -> "학습 진행"
                    AppPhase.SPLASH -> "연결 중"
                },
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFF6E6E73)
            )
            if (loading) {
                Spacer(Modifier.width(8.dp))
                CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp)
            }
        }
        session?.let {
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatusPill(label = "LV ${it.level}")
                StatusPill(label = "정답 ${it.correctCount ?: 0}")
                StatusPill(label = "오답 ${it.incorrectCount ?: 0}")
                StatusPill(label = "Gauge ${it.currentGauge ?: 0}%")
            }
        }
    }
}

@Composable
private fun StatusPill(label: String) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = Color(0xFFF2F2F4),
        contentColor = Color(0xFF1D1D1F),
        border = BorderStroke(1.dp, Color(0xFFD1D1D6))
    ) {
        Text(
            text = label,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
            fontSize = 12.sp
        )
    }
}

@Composable
private fun SplashScreen() {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Surface(
                modifier = Modifier.size(90.dp),
                shape = CircleShape,
                color = Color(0xFFE9EDF5)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(text = "🐶", fontSize = 38.sp)
                }
            }
            Spacer(Modifier.height(18.dp))
            Text(
                text = "튜터 서버 연결 중...",
                color = Color(0xFF4A4A4C),
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

@Composable
private fun Bubble(line: UiLine) {
    val align = if (line.type == LineType.USER) Alignment.CenterEnd else Alignment.CenterStart
    val color = when (line.type) {
        LineType.USER -> Color(0xFF0A84FF)
        LineType.ERROR -> Color(0xFFFF453A)
        else -> Color.White
    }
    val textColor = if (line.type == LineType.USER || line.type == LineType.ERROR) Color.White else Color(0xFF1D1D1F)
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        contentAlignment = align
    ) {
        Surface(
            shape = RoundedCornerShape(18.dp),
            color = color,
            border = if (line.type == LineType.SYSTEM || line.type == LineType.TUTOR) BorderStroke(1.dp, Color(0xFFD1D1D6)) else null
        ) {
            Text(
                text = line.text,
                color = textColor,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                lineHeight = 21.sp
            )
        }
    }
}

@Composable
private fun SetupOptions(
    phase: AppPhase,
    selectedLevel: String,
    onLevel: (String) -> Unit,
    onTopic: (String) -> Unit,
    onGrammar: (String) -> Unit
) {
    val options = when (phase) {
        AppPhase.SETUP_LEVEL -> LEVEL_LIST
        AppPhase.SETUP_TOPIC -> TOPIC_LIST
        AppPhase.SETUP_GRAMMAR -> grammarListForLevel(selectedLevel).map { it.name }
        else -> emptyList()
    }
    if (options.isEmpty()) return

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 4.dp)
    ) {
        LazyColumn(
            modifier = Modifier.height((options.size.coerceAtMost(4) * 46).dp)
        ) {
            items(options.size) { index ->
                ElevatedButton(
                    onClick = {
                        when (phase) {
                            AppPhase.SETUP_LEVEL -> onLevel(options[index])
                            AppPhase.SETUP_TOPIC -> onTopic(options[index])
                            AppPhase.SETUP_GRAMMAR -> onGrammar(options[index])
                            else -> Unit
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp),
                    colors = ButtonDefaults.elevatedButtonColors(containerColor = Color.White)
                ) {
                    Text(text = options[index], color = Color(0xFF1D1D1F))
                }
            }
        }
    }
}

@Composable
private fun InputBar(
    phase: AppPhase,
    text: String,
    loading: Boolean,
    onTextChange: (String) -> Unit,
    onSubmit: () -> Unit
) {
    Surface(color = Color.White, shadowElevation = 8.dp) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 10.dp)
                .navigationBarsPadding(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = text,
                onValueChange = onTextChange,
                modifier = Modifier.weight(1f),
                enabled = !loading,
                placeholder = {
                    Text(
                        when (phase) {
                            AppPhase.SETUP_LEVEL -> "레벨 선택 (예: L1 또는 초급)"
                            AppPhase.SETUP_TOPIC -> "주제 선택 (예: T1 또는 일상)"
                            AppPhase.SETUP_GRAMMAR -> "문법 선택 (예: G1 또는 랜덤)"
                            AppPhase.CHAT -> "영작 입력 (!레벨 초급, !주제 여행, !문법 리셋)"
                            AppPhase.SPLASH -> "연결 중..."
                        }
                    )
                },
                shape = RoundedCornerShape(20.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color(0xFF0A84FF),
                    unfocusedBorderColor = Color(0xFFD1D1D6),
                    focusedContainerColor = Color(0xFFF7F7FA),
                    unfocusedContainerColor = Color(0xFFF7F7FA)
                )
            )
            Spacer(Modifier.width(10.dp))
            Button(
                onClick = onSubmit,
                enabled = !loading && text.isNotBlank(),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0A84FF))
            ) {
                Text("전송")
            }
        }
    }
}
