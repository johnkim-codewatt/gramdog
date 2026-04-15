"use client";

import { useEffect, useState, useRef } from "react";
import lottie from "lottie-web";

type Line = {
    type: "system" | "user" | "tutor" | "error" | "ascii";
    text: string;
};

type SessionInfo = {
    user: string;
    level: string;
    topic: string;
    target_grammar?: string;
    mode?: string;
    review_progress?: string;
    correct_count?: number;
    incorrect_count?: number;
    current_gauge?: number;
};

export default function TerminalUI() {
    const [lines, setLines] = useState<Line[]>([]);
    const [inputVal, setInputVal] = useState("");
    const [loading, setLoading] = useState(false);
    const [streamingText, setStreamingText] = useState<string | null>(null);
    const [session, setSession] = useState<SessionInfo | null>(null);
    const [theme, setTheme] = useState<"retro" | "duo">("duo");

    // 모달 상태 관리 (게이지 100% or 0% 이벤트용)
    const [modalEvent, setModalEvent] = useState<"LEVEL_UP" | "LEVEL_DOWN" | null>(null);

    // App Phase: "SPLASH" -> "SETUP_LEVEL" -> "SETUP_TOPIC" -> "SETUP_GRAMMAR" -> "CHAT"
    const [phase, setPhase] = useState<"SPLASH" | "SETUP_LEVEL" | "SETUP_TOPIC" | "SETUP_GRAMMAR" | "CHAT">("SPLASH");

    // 상태 저장을 위한 임시 변수
    const [selectedLevelTemp, setSelectedLevelTemp] = useState<string>("");
    const [selectedTopicTemp, setSelectedTopicTemp] = useState<string>("");

    const bottomRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const mascotLottieRef = useRef<HTMLDivElement>(null);
    const pawsLottieRef = useRef<HTMLDivElement>(null);
    const loadingLottieRef = useRef<HTMLDivElement>(null);

    const API_URL = "http://127.0.0.1:8000";

    const LEVEL_LIST = ["초급", "중급", "고급", "네이티브"];
    const TOPIC_LIST = ["일상", "비즈니스", "여행", "학교", "연애", "취미"];
    const GRAMMAR_LIST: { id: string; name: string }[] = [
        { id: "random", name: "랜덤" },
        // — Modals & Subjunctive —
        { id: "can/could_usage", name: "can/could 사용법" },
        { id: "must/have_to_usage", name: "must/have to 사용법" },
        { id: "would_usage", name: "would 사용법" },
        { id: "wish_past_simple_usage", name: "wish + 과거형" },
        { id: "should_have_p.p._usage", name: "should have + 과거분사" },
        // — Verbals —
        { id: "infinitive_as_subject", name: "주어로 쓰인 to부정사" },
        { id: "gerund_as_subject", name: "주어로 쓰인 동명사" },
        { id: "infinitive_of_purpose", name: "목적을 나타내는 to부정사" },
        { id: "participle_construction", name: "분사구문" },
        { id: "gerund_as_object", name: "목적어로 쓰인 동명사" },
        // — Parts of Speech —
        { id: "article_definite", name: "정관사" },
        { id: "article_indefinite", name: "부정관사" },
        { id: "adjective_comparative", name: "형용사 비교급" },
        // — Sentence Structure —
        { id: "simple_past_structure", name: "과거형 문장 구조" },
        { id: "passive_voice_structure", name: "수동태 구조" },
        { id: "complex_sentence_structure", name: "복문 구조" },
        { id: "compound_sentence_structure", name: "병렬 구조" },
    ];

    const LEVEL_GRAMMAR_POOLS: Record<string, string[]> = {
        "초급": [
            "can/could_usage",
            "must/have_to_usage",
            "infinitive_of_purpose",
            "article_definite",
            "article_indefinite",
            "simple_past_structure"
        ],
        "중급": [
            "would_usage",
            "gerund_as_subject",
            "gerund_as_object",
            "adjective_comparative",
            "passive_voice_structure",
            "compound_sentence_structure"
        ],
        "고급": [
            "wish_past_simple_usage",
            "should_have_p.p._usage",
            "infinitive_as_subject",
            "participle_construction",
            "complex_sentence_structure"
        ],
        "네이티브": [
            "wish_past_simple_usage",
            "should_have_p.p._usage",
            "participle_construction",
            "complex_sentence_structure",
            "compound_sentence_structure"
        ]
    };

    const getFilteredGrammarList = (level: string) => {
        const allowedIds = new Set(LEVEL_GRAMMAR_POOLS[level] || []);
        const filtered = GRAMMAR_LIST.filter(g => g.id === "random" || allowedIds.has(g.id));
        return filtered.length > 0 ? filtered : GRAMMAR_LIST;
    };

    // 초기 로드 시 아트 및 테마 설정
    useEffect(() => {
        // Splash Screen 타이머 (3초 후 SETUP_LEVEL로 이동)
        if (phase === "SPLASH") {
            const timer = setTimeout(() => {
                setPhase("SETUP_LEVEL");
                initSetupPhase();
            }, 3000);
            return () => clearTimeout(timer);
        }
    }, [phase]);

    useEffect(() => {
        if (!mascotLottieRef.current) return;

        const animationPath = phase === "SPLASH" ? "/Cute%20Doggie.json" : "/Moody%20Dog.json";
        const animation = lottie.loadAnimation({
            container: mascotLottieRef.current,
            renderer: "svg",
            loop: true,
            autoplay: true,
            path: animationPath,
        });
        animation.setSpeed(1.25);

        return () => {
            animation.destroy();
        };
    }, [phase, theme]);

    const isStreaming = streamingText !== null;

    useEffect(() => {
        if (!pawsLottieRef.current || !isStreaming) return;

        const animation = lottie.loadAnimation({
            container: pawsLottieRef.current,
            renderer: "svg",
            loop: true,
            autoplay: true,
            path: "/paws%20animation.json",
        });
        animation.setSpeed(1.6);

        return () => {
            animation.destroy();
        };
    }, [isStreaming, theme]);

    useEffect(() => {
        if (!loadingLottieRef.current || !loading || streamingText !== null) return;

        const animation = lottie.loadAnimation({
            container: loadingLottieRef.current,
            renderer: "svg",
            loop: true,
            autoplay: true,
            path: "/My%20French%20Bulldog.json",
        });
        animation.setSpeed(1.5);

        return () => {
            animation.destroy();
        };
    }, [loading, streamingText, theme]);

    const initSetupPhase = () => {
        appendLine("ascii", `
========================================================
   ___   ___  ____    ___  _____  ____   ___   ____ 
  / _ \\ / _ \\/ __/___/ _ \\/ __/ |/ / _ \\/ __/  / __/
 / // // // /\\ \\/___/ ___/ _//    / // / _/   _\\ \\  
/____/ \\___/___/   /_/  /___/_/|_/____/___/  /___/  
                                                    
  C:\\\\> AI JUNIOR TUTOR SYSTEM v2.0 (MODEM LINK OK)
========================================================
    `);
        appendLine("system", "[Sys] 통신 모듈 초기화 중...");

        // SETUP 단계 돌입 (레벨 먼저)
        setTimeout(() => {
            appendLine("system", "[Sys] 먼저 학습 레벨을 선택해 주십시오. (번호 입력 혹은 클릭)");
            LEVEL_LIST.forEach((l, idx) => {
                appendLine("system", `    [L${idx + 1}] ${l}`);
            });
        }, 500);

        // 자동 포커스
        if (inputRef.current) inputRef.current.focus();
    };

    // 로그 자동 스크롤
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [lines, loading]);

    const appendLine = (type: Line["type"], text: string) => {
        setLines(prev => [...prev, { type, text }]);
    };

    const streamFeedback = async (fullText: string) => {
        setStreamingText("");
        for (let i = 0; i <= fullText.length; i++) {
            setStreamingText(fullText.substring(0, i));
            await new Promise(resolve => setTimeout(resolve, 15)); // 글자당 15ms 대기
            bottomRef.current?.scrollIntoView({ behavior: "smooth" });
        }
        setStreamingText(null);
    };

    const formatFeedbackText = (feedback: unknown): string => {
        if (feedback === null || feedback === undefined) return "";
        if (typeof feedback === "string") return feedback;
        if (typeof feedback === "number" || typeof feedback === "boolean") return String(feedback);

        if (Array.isArray(feedback)) {
            return feedback
                .map(item => formatFeedbackText(item).trim())
                .filter(Boolean)
                .join("\n");
        }

        if (typeof feedback === "object") {
            const feedbackObj = feedback as {
                feedback?: unknown;
                corrected_text?: unknown;
                grammar_tag?: unknown;
                explanation?: unknown;
                better_expression?: unknown;
                history_comment?: unknown;
            };

            const blocks: string[] = [];
            const appendBlock = (title: string, value: unknown) => {
                const text = formatFeedbackText(value).trim();
                if (text) blocks.push(`[${title}]\n${text}`);
            };

            appendBlock("피드백", feedbackObj.feedback);
            appendBlock("교정 문장", feedbackObj.corrected_text);
            appendBlock("핵심 문법", feedbackObj.grammar_tag);
            appendBlock("설명", feedbackObj.explanation);
            appendBlock("더 자연스러운 표현", feedbackObj.better_expression);
            appendBlock("과거 이력 비교", feedbackObj.history_comment);

            if (blocks.length > 0) {
                return blocks.join("\n\n");
            }

            try {
                return JSON.stringify(feedback, null, 2);
            } catch {
                return String(feedback);
            }
        }

        return String(feedback);
    };

    const parseGuideSections = (rawText: string) => {
        const lines = rawText
            .split("\n")
            .map(line => line.trim())
            .filter(Boolean);

        const firstSectionIdx = lines.findIndex(line => /^\d+\.\s+/.test(line));
        if (firstSectionIdx < 0) return null;

        const headerLine = lines.find(line => line.startsWith("[📝"));
        const header = headerLine
            ? headerLine.replace("[📝", "").replace("]", "").trim()
            : "Question";

        const sections: Array<{ title: string; body: string[] }> = [];
        let current: { title: string; body: string[] } | null = null;

        for (let i = firstSectionIdx; i < lines.length; i++) {
            const line = lines[i];
            if (/^\d+\.\s+/.test(line)) {
                if (current) sections.push(current);
                current = {
                    title: line.replace(/^\d+\.\s*/, "").trim(),
                    body: []
                };
            } else if (current) {
                current.body.push(line);
            }
        }

        if (current) sections.push(current);
        if (sections.length === 0) return null;

        return { header, sections };
    };

    const renderGuideBubbleContent = (rawText: string) => {
        const parsed = parseGuideSections(rawText);
        if (!parsed) return rawText;

        const convertGrammarTagToKorean = (text: string) => {
            let converted = text;
            GRAMMAR_LIST.forEach(({ id, name }) => {
                if (id === "random") return;
                if (converted.includes(id)) {
                    converted = converted.split(id).join(name);
                }
            });
            return converted;
        };

        return (
            <div className="space-y-3">
                <div className="text-[18px] font-extrabold tracking-tight text-[#1d1d1f]">
                    {parsed.header}
                </div>
                {parsed.sections.map((section, idx) => (
                    <div
                        key={`${section.title}-${idx}`}
                        className="rounded-2xl border border-[#e5e5ea] bg-[#f8f8fa] px-3 py-2.5"
                    >
                        <div className="text-[17px] font-bold tracking-tight text-[#1d1d1f] mb-1.5">
                            {section.title}
                        </div>
                        <div className="text-[15px] leading-relaxed text-[#2c2c2e] whitespace-pre-wrap">
                            {section.title.includes("문법")
                                ? convertGrammarTagToKorean(section.body.join("\n"))
                                : section.body.join("\n")}
                        </div>
                    </div>
                ))}
            </div>
        );
    };

    const parseFeedbackSections = (rawText: string) => {
        const normalizedLines = rawText
            .split("\n")
            .map(line => line.trim())
            .filter(Boolean)
            .filter(line => !/^=+$/.test(line));

        if (normalizedLines.length === 0) return null;

        let header = "Tutor Feedback";
        if (/^\[Tutor Feedback\]$/i.test(normalizedLines[0])) {
            normalizedLines.shift();
        }

        const sections: Array<{ title: string; body: string[] }> = [];
        let current: { title: string; body: string[] } | null = null;

        normalizedLines.forEach(line => {
            const sectionMatch = line.match(/^\[(.+)\]$/);
            if (sectionMatch) {
                if (current) sections.push(current);
                current = { title: sectionMatch[1], body: [] };
                return;
            }
            if (current) current.body.push(line);
        });

        if (current) sections.push(current);
        if (sections.length === 0) return null;

        return { header, sections };
    };

    const renderFeedbackBubbleContent = (rawText: string) => {
        const parsed = parseFeedbackSections(rawText);
        if (!parsed) return rawText.replace(/\[Tutor Feedback\]/g, "").trim();

        return (
            <div className="space-y-3">
                <div className="text-[18px] font-extrabold tracking-tight text-[#1d1d1f]">
                    {parsed.header}
                </div>
                {parsed.sections.map((section, idx) => (
                    <div
                        key={`${section.title}-${idx}`}
                        className="rounded-2xl border border-[#e5e5ea] bg-[#f8f8fa] px-3 py-2.5"
                    >
                        <div className="text-[16px] font-bold tracking-tight text-[#1d1d1f] mb-1.5">
                            {section.title}
                        </div>
                        <div className="text-[15px] leading-relaxed text-[#1d1d1f] whitespace-pre-wrap">
                            {section.body.join("\n")}
                        </div>
                    </div>
                ))}
            </div>
        );
    };

    const initChatPhase = async (selectedLevel: string, selectedTopic: string, selectedGrammarId: string) => {
        setPhase("CHAT");
        setLoading(true);

        try {
            const grammarCmdValue = selectedGrammarId === "random" ? "리셋" : selectedGrammarId;
            appendLine("system", "[Sys] 메인 서버(Mainframe) 접속 요청 중...");

            // 레벨, 주제, 문법 파라미터를 담아 초기화 요청 (새 문제 생성)
            const res = await fetch(`${API_URL}/api/init?level=${encodeURIComponent(selectedLevel)}&topic=${encodeURIComponent(selectedTopic)}&grammar=${encodeURIComponent(grammarCmdValue)}`);
            const data = await res.json();

            if (data.session_info) setSession(data.session_info);

            appendLine("system", `[Sys] ${data.message}`);
            appendLine("tutor", `\n[📝 Question]\n${data.guide}`);
        } catch (err: any) {
            appendLine("error", `[Fatal] 서버 연결 실패: ${err.message}`);
        } finally {
            setLoading(false);
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    };

    const handleCommand = async (fullInput: string) => {
        const parts = fullInput.split(" ");
        const cmd = parts[0].substring(1);
        const val = parts.slice(1).join(" ");

        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/api/command`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ command_type: cmd, command_value: val })
            });
            const data = await res.json();
            appendLine("system", `[Sys] ${data.message}`);

            // 주제나 레벨이 바뀌었을 수 있으므로 시각화 갱신용으로 로컬 세션 패치
            if (data.session_info) {
                setSession(data.session_info);
            }
            if (data.next_question) {
                appendLine("tutor", `\n[📝 Question]\n${data.next_question}`);
            }
        } catch (err: any) {
            appendLine("error", `[Error] 명령어 처리 실패: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleChat = async (text: string) => {
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_input: text })
            });
            const data = await res.json();

            if (data.session_info) {
                setSession(data.session_info);
            }

            if (data.event) {
                setModalEvent(data.event);
            }

            const feedbackText = formatFeedbackText(data.feedback);
            if (feedbackText.trim()) {
                const formattedFeedback = `\n================================\n[Tutor Feedback]\n${feedbackText}\n================================`;
                await streamFeedback(formattedFeedback);
                appendLine("tutor", formattedFeedback);
            }
            if (data.system_alert) {
                appendLine("system", `\n[Sys] ${data.system_alert}`);
            }
            if (data.next_question) {
                appendLine("tutor", `\n[📝 Next Question]\n${data.next_question}`);
            }
        } catch (err: any) {
            appendLine("error", `[Error] 서버 응답 타임아웃: ${err.message}`);
        } finally {
            setLoading(false);
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    };

    const onSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!inputVal.trim() || loading) return;

        const currentInput = inputVal.trim();
        appendLine("user", `C:\\\\USER> ${currentInput}`);
        setInputVal("");

        if (phase === "SETUP_LEVEL") {
            const num = parseInt(currentInput.replace("L", ""));
            let level = "";
            if (!isNaN(num) && num >= 1 && num <= LEVEL_LIST.length) {
                level = LEVEL_LIST[num - 1];
            } else if (LEVEL_LIST.includes(currentInput)) {
                level = currentInput;
            }

            if (level) {
                appendLine("system", `[Sys] '${level}' 레벨이 선택되었습니다.`);
                setSelectedLevelTemp(level);
                setPhase("SETUP_TOPIC");

                // 주제 선택 안내 출력
                setTimeout(() => {
                    appendLine("system", "\n[Sys] 오늘의 학습 주제를 선택해 주십시오. (번호 입력 혹은 클릭)");
                    TOPIC_LIST.forEach((t, idx) => {
                        appendLine("system", `    [T${idx + 1}] ${t}`);
                    });
                }, 300);
            } else {
                appendLine("error", `[Error] 올바른 레벨 번호(L1~L${LEVEL_LIST.length})나 이름을 입력하세요.`);
            }
            return;
        }

        if (phase === "SETUP_TOPIC") {
            const num = parseInt(currentInput.replace("T", ""));
            let topic = "";
            if (!isNaN(num) && num >= 1 && num <= TOPIC_LIST.length) {
                topic = TOPIC_LIST[num - 1];
            } else if (TOPIC_LIST.includes(currentInput)) {
                topic = currentInput;
            }

            if (topic) {
                appendLine("system", `[Sys] '${topic}' 테마가 선택되었습니다.`);
                setSelectedTopicTemp(topic);
                setPhase("SETUP_GRAMMAR");

                // 문법 선택 안내 출력
                setTimeout(() => {
                    appendLine("system", "\n[Sys] 이어서 집중 학습할 문법을 선택해 주십시오.");
                    const filteredGrammarList = getFilteredGrammarList(selectedLevelTemp);
                    filteredGrammarList.forEach((g, idx) => {
                        appendLine("system", `    [G${idx + 1}] ${g.name}`);
                    });
                }, 300);
            } else {
                appendLine("error", "[Error] 올바른 주제 번호나 이름을 입력하세요.");
            }
            return;
        }

        if (phase === "SETUP_GRAMMAR") {
            const num = parseInt(currentInput.replace("G", ""));
            const filteredGrammarList = getFilteredGrammarList(selectedLevelTemp);
            let foundGrammar: { id: string; name: string } | undefined;
            if (!isNaN(num) && num >= 1 && num <= filteredGrammarList.length) {
                foundGrammar = filteredGrammarList[num - 1];
            } else {
                foundGrammar = filteredGrammarList.find(g => g.name === currentInput);
            }

            if (foundGrammar) {
                appendLine("system", `[Sys] '${foundGrammar.name}' 문법이 선택되었습니다.`);
                await initChatPhase(selectedLevelTemp, selectedTopicTemp, foundGrammar.id);
            } else {
                appendLine("error", "[Error] 올바른 문법 번호나 이름을 입력하세요.");
            }
            return;
        }

        // CHAT Phase
        if (currentInput.startsWith("!")) {
            await handleCommand(currentInput);
        } else {
            await handleChat(currentInput);
        }
    };

    const handleLevelClick = (level: string) => {
        if (phase !== "SETUP_LEVEL" || loading) return;
        appendLine("user", `C:\\\\USER> ${level}`);
        appendLine("system", `[Sys] '${level}' 레벨이 선택되었습니다.`);
        setSelectedLevelTemp(level);
        setPhase("SETUP_TOPIC");

        setTimeout(() => {
            appendLine("system", "\n[Sys] 오늘의 학습 주제를 선택해 주십시오. (번호 입력 혹은 클릭)");
            TOPIC_LIST.forEach((t, idx) => {
                appendLine("system", `    [T${idx + 1}] ${t}`);
            });
        }, 300);
    };

    const handleTopicClick = (topic: string) => {
        if (phase !== "SETUP_TOPIC" || loading) return;
        appendLine("user", `C:\\\\USER> ${topic}`);
        appendLine("system", `[Sys] '${topic}' 테마가 선택되었습니다.`);
        setSelectedTopicTemp(topic);
        setPhase("SETUP_GRAMMAR");

        setTimeout(() => {
            appendLine("system", "\n[Sys] 이어서 집중 학습할 문법을 선택해 주십시오.");
            const filteredGrammarList = getFilteredGrammarList(selectedLevelTemp);
            filteredGrammarList.forEach((g, idx) => {
                appendLine("system", `    [G${idx + 1}] ${g.name}`);
            });
        }, 300);
    };

    const handleGrammarClick = async (grammarName: string) => {
        if (phase !== "SETUP_GRAMMAR" || loading) return;
        const filteredGrammarList = getFilteredGrammarList(selectedLevelTemp);
        const found = filteredGrammarList.find(g => g.name === grammarName);
        if (!found) return;
        appendLine("user", `C:\\\\USER> ${found.name}`);
        appendLine("system", `[Sys] '${found.name}' 문법이 선택되었습니다.`);
        await initChatPhase(selectedLevelTemp, selectedTopicTemp, found.id);
    };

    const toggleTheme = () => {
        setTheme(prev => prev === "retro" ? "duo" : "retro");
    };

    // 스테이터스 바 컴포넌트 (레벨 선택 후부터 표시)
    const StatusBar = () => {
        if (!session) return null;
        const currentGauge = session.current_gauge ?? 0;
        if (theme === "retro") {
            return (
                <div className="flex gap-3 items-center text-xs font-bold flex-wrap">
                    <span>🏅 {session.level}</span>
                    <span style={{ color: '#4ade80' }}>✅ {session.correct_count ?? 0}</span>
                    <span style={{ color: '#f87171' }}>❌ {session.incorrect_count ?? 0}</span>

                    {/* 게이지 시각화 바 */}
                    <span className="flex items-center gap-1">
                        🎯
                        <div className="w-16 h-2 bg-slate-200 rounded-full overflow-hidden inline-[flex]">
                            <div
                                className="h-full bg-[var(--color-duo-green)] transition-all duration-500 ease-out"
                                style={{ width: `${currentGauge}%` }}
                            />
                        </div>
                        <span className="ml-1 w-7 text-right">{currentGauge}%</span>
                    </span>
                </div>
            );
        }

        return (
            <div className="flex gap-2 items-center text-xs font-semibold text-[#1d1d1f] flex-wrap">
                <span className="px-2 py-1 rounded-full bg-white border border-[#d2d2d7]">LV {session.level}</span>
                <span className="px-2 py-1 rounded-full bg-[#ecfdf3] text-[#1f9d55] border border-[#b6ecd2]">정답 {session.correct_count ?? 0}</span>
                <span className="px-2 py-1 rounded-full bg-[#fff1f0] text-[#d62828] border border-[#ffd3d0]">오답 {session.incorrect_count ?? 0}</span>
                <span className="flex items-center gap-2 px-2 py-1 rounded-full bg-white border border-[#d2d2d7]">
                    <span className="text-[#6e6e73]">Gauge</span>
                    <div className="w-20 h-2 bg-[#ececf0] rounded-full overflow-hidden inline-[flex]">
                        <div
                            className="h-full transition-all duration-500 ease-out"
                            style={{ width: `${currentGauge}%`, backgroundColor: "#0071e3" }}
                        />
                    </div>
                    <span className="w-8 text-right text-[#6e6e73]">{currentGauge}%</span>
                </span>
            </div>
        );
    };

    return (
        <div
            className={`h-[100dvh] w-full p-2 sm:p-3 flex flex-col select-none relative overflow-hidden transition-colors duration-300 ${theme === "retro" ? "crt-flicker" : ""}`}
            style={{
                backgroundColor: theme === "retro" ? 'var(--background)' : '#f5f5f7',
                color: theme === "retro" ? 'var(--foreground)' : '#1d1d1f',
                fontFamily: theme === "retro"
                    ? 'var(--font-primary)'
                    : '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif'
            }}
            data-theme={theme}
        >
            {/* CRT Overlay Effect (Retro Only) */}
            {theme === "retro" && <div className="crt-overlay"></div>}

            {phase === "SPLASH" ? (
                /* Splash Screen UI */
                <div className="flex-1 flex flex-col items-center justify-center relative z-10 rounded-2xl border border-transparent" style={{ backgroundColor: theme === "retro" ? 'var(--color-dos-blue)' : '#ffffff', borderColor: theme === "retro" ? "transparent" : "#d2d2d7", boxShadow: theme === "retro" ? "none" : "0 8px 24px rgba(0,0,0,0.08)" }}>
                    {/* 
                    <pre className="text-center font-bold mb-8 leading-tight sm:text-lg md:text-xl lg:text-2xl" style={{ color: theme === "retro" ? 'var(--warning)' : 'black' }}>
                        {theme === "retro" ? `
 _______   _______  ____    ____  ______   ______    _______  _______   
|       \\ |   ____| \\   \\  /   / /      | /  __  \\  |       \\|   ____|  
|  .--.  ||  |__     \\   \\/   / |  ,----'|  |  |  | |  .--.  |  |__     
|  |  |  ||   __|     \\      /  |  |     |  |  |  | |  |  |  |   __|    
|  '--'  ||  |____     \\    /   |  \`----.|  \`--'  | |  '--'  |  |____   
|_______/ |_______|     \\__/     \\______| \\______/  |_______| |_______|  
` : `
  ___  ___  _  _  ___  ___  ___  ___ 
 |   \\| __|| || |/ __|/ _ \\|   \\| __|
 | |) | _| | \\/ | (__| (_) | |) | _| 
 |___/|___| \\__/ \\___|\\___/|___/|___|
`}
                    </pre>
                    */}
                    <div className="text-center font-semibold mb-6 text-4xl sm:text-5xl md:text-6xl tracking-tight" style={{ color: theme === "retro" ? 'var(--warning)' : '#1d1d1f' }}>
                        {/* DEVCODE 영어 튜터 v0.2 */}
                    </div>
                    {/* Lottie Slot: splash/header intro */}
                    {theme !== "retro" && (
                        // <div className="w-32 h-32 mb-4 rounded-3xl border border-[#d2d2d7] bg-[#f2f2f4] flex items-center justify-center overflow-hidden">
                            <div ref={mascotLottieRef} className="w-38 h-38" aria-label="Cute Doggie animation" />
                        // </div>
                    )}
                    <div className="font-semibold animate-pulse text-lg" style={{ color: theme === "retro" ? 'var(--foreground)' : '#6e6e73' }}>
                        {/* Loading DEVCODE Tutor System... <span className={theme === "retro" ? "blink" : ""}>{theme === "retro" ? "_" : "🔄"}</span> */}
                    </div>
                </div>
            ) : theme === "retro" ? (
                /* 고전 스타일 윈도우 프레임 */
                <div className="flex-1 flex flex-col border-[4px] p-[4px] relative z-10" style={{ borderColor: 'var(--foreground)', backgroundColor: 'var(--color-dos-blue)' }}>
                    {/* 상태바 Header */}
                    <div className="font-bold px-4 py-2 flex justify-between items-center text-sm sm:text-base border-b-[4px]" style={{ backgroundColor: 'var(--foreground)', color: 'var(--color-dos-blue)', borderColor: 'var(--foreground)' }}>
                        <span>[ DEVCODE ] <span className="opacity-80 ml-2">{session ? `USER: ${session.user}` : "STATUS: OFFLINE"}</span></span>
                        <span className="animate-pulse">_</span>
                        <div className="flex items-center gap-4">
                            <span className="hidden sm:inline">
                                {session
                                    ? `LV: [${session.level}] | TPC: [${session.topic}]` + (session.mode === "REVIEW" ? ` | MODE: [REVIEW ${session.review_progress}]` : "")
                                    : "AWAITING CONNECTION..."}
                            </span>
                            <button
                                onClick={toggleTheme}
                                className="px-2 py-1 text-xs sm:text-sm rounded border-2 transition-transform active:scale-95"
                                style={{ backgroundColor: 'var(--color-dos-black)', color: 'var(--warning)', borderColor: 'var(--warning)' }}
                                title="Toggle Theme"
                            >
                                ✨ DUO
                            </button>
                        </div>
                    </div>
                    {/* Retro 스테이터스 바 */}
                    {session && (
                        <div className="relative z-10 px-4 py-1 flex gap-4 text-xs font-bold border-b-[2px]" style={{ backgroundColor: 'var(--color-dos-black)', borderColor: 'var(--foreground)', color: 'var(--accent)', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)' }}>
                            <span>★ LV: {session.level}</span>
                            <span style={{ color: '#4ade80' }}>O(correct): {session.correct_count ?? 0}</span>
                            <span style={{ color: '#f87171' }}>X(incorrect): {session.incorrect_count ?? 0}</span>
                            <span>🎯 GAUGE: {'[' + '='.repeat(Math.round((session.current_gauge ?? 0) / 10)) + ' '.repeat(10 - Math.round((session.current_gauge ?? 0) / 10)) + ']'} {session.current_gauge ?? 0}%</span>
                        </div>
                    )}

                    {/* 대화 로그 영역 */}
                    <div
                        className="flex-1 overflow-y-auto p-4 space-y-3 whitespace-pre-wrap word-break text-base sm:text-lg leading-relaxed"
                        onClick={() => inputRef.current?.focus()}
                    >
                        {lines.map((line, i) => (
                            <div
                                key={i}
                                className={
                                    line.type === "ascii" ? "font-bold tracking-widest leading-tight" :
                                        line.type === "system" ? "" :
                                            line.type === "error" ? "font-bold px-2 py-1 inline-block" :
                                                line.type === "user" ? "font-bold opacity-90" : ""
                                }
                                style={{
                                    color: line.type === "ascii" ? 'var(--warning)' :
                                        line.type === "system" ? 'var(--accent)' :
                                            line.type === "error" ? 'var(--foreground)' :
                                                line.type === "user" ? 'var(--foreground)' : 'var(--foreground)',
                                    backgroundColor: line.type === "error" ? 'var(--error)' : 'transparent'
                                }}
                            >
                                {(line.type === "system" && phase === "SETUP_LEVEL" && line.text.includes("[L")) ? (
                                    <span
                                        className="cursor-pointer transition-colors px-2 py-1 inline-block mb-1"
                                        style={{ color: 'var(--foreground)' }}
                                        onClick={() => {
                                            const match = line.text.match(/\[L\d+\]\s(.+)/);
                                            if (match) handleLevelClick(match[1]);
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.backgroundColor = 'var(--highlight-bg)';
                                            e.currentTarget.style.color = 'var(--highlight-fg)';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.backgroundColor = 'transparent';
                                            e.currentTarget.style.color = 'var(--foreground)';
                                        }}
                                    >
                                        {line.text}
                                    </span>
                                ) : (line.type === "system" && phase === "SETUP_TOPIC" && line.text.includes("[T")) ? (
                                    <span
                                        className="cursor-pointer transition-colors px-2 py-1 inline-block mb-1"
                                        style={{ color: 'var(--foreground)' }}
                                        onClick={() => {
                                            const match = line.text.match(/\[T\d+\]\s(.+)/);
                                            if (match) handleTopicClick(match[1]);
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.backgroundColor = 'var(--highlight-bg)';
                                            e.currentTarget.style.color = 'var(--highlight-fg)';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.backgroundColor = 'transparent';
                                            e.currentTarget.style.color = 'var(--foreground)';
                                        }}
                                    >
                                        {line.text}
                                    </span>
                                ) : (line.type === "system" && phase === "SETUP_GRAMMAR" && line.text.includes("[G")) ? (
                                    <span
                                        className="cursor-pointer transition-colors px-2 py-1 inline-block mb-1"
                                        style={{ color: 'var(--foreground)' }}
                                        onClick={() => {
                                            const match = line.text.match(/\[G\d+\]\s(.+)/);
                                            if (match) handleGrammarClick(match[1]);
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.backgroundColor = 'var(--highlight-bg)';
                                            e.currentTarget.style.color = 'var(--highlight-fg)';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.backgroundColor = 'transparent';
                                            e.currentTarget.style.color = 'var(--foreground)';
                                        }}
                                    >
                                        {line.text}
                                    </span>
                                ) : (
                                    line.text
                                )}
                            </div>
                        ))}

                        {streamingText !== null && (
                            <div className="font-bold opacity-90" style={{ color: 'var(--foreground)' }}>
                                {streamingText}<span className="blink">_</span>
                            </div>
                        )}

                        {loading && streamingText === null && (
                            <div className="font-bold mt-4 animate-pulse inline-block px-2 py-1" style={{ color: 'var(--color-dos-black)', backgroundColor: 'var(--warning)' }}>
                                [Sys] PROCESSING DATA...<span className="blink">_</span>
                            </div>
                        )}
                        <div ref={bottomRef} className="h-4" />
                    </div>

                    {/* 하단 명령줄 (고정) */}
                    <form onSubmit={onSubmit} className="flex gap-2 p-3 border-t-[4px] relative z-10" style={{ borderColor: 'var(--foreground)', backgroundColor: 'var(--color-dos-blue)' }}>
                        <span className="font-bold mt-[2px] hidden sm:inline" style={{ color: 'var(--foreground)' }}>C:\\USER{">"}</span>
                        <span className="font-bold mt-[2px] sm:hidden" style={{ color: 'var(--foreground)' }}>{">"}</span>
                        <input
                            ref={inputRef}
                            type="text"
                            value={inputVal}
                            onChange={(e) => setInputVal(e.target.value)}
                            disabled={loading}
                            placeholder={
                                loading ? ""
                                    : phase === "SETUP_LEVEL" ? `레벨 번호(L1~L${LEVEL_LIST.length})를 입력하거나 클릭하세요...`
                                        : phase === "SETUP_TOPIC" ? "주제 번호(T1~T6)를 입력하거나 클릭하세요..."
                                            : phase === "SETUP_GRAMMAR" ? `문법 번호(G1~G${getFilteredGrammarList(selectedLevelTemp).length})를 입력하거나 클릭하세요...`
                                                : "영작문을 입력! (!레벨 / 패스)"
                            }
                            className="flex-1 bg-transparent outline-none border-none caret-white sm:text-lg"
                            style={{ color: 'var(--warning)' }}
                            autoFocus
                            autoComplete="off"
                            spellCheck="false"
                        />
                    </form>
                </div>
            ) : (
                /* 모던 애플 스타일 프레임 */
                <div className="w-full max-w-4xl mx-auto flex-1 flex flex-col relative z-10 sm:my-4 bg-white sm:rounded-[28px] shadow-[0_8px_24px_rgba(0,0,0,0.08)] overflow-hidden border border-[#d2d2d7] transition-all duration-300">
                    {/* 모던 헤더 */}
                    <div className="relative z-20 flex justify-between items-center px-5 py-4 border-b border-[#e5e5ea] bg-white">
                        <div className="flex items-center gap-3">
                            {/* Lottie Slot: header mascot */}
                            <div className="w-11 h-11 rounded-2xl bg-[#f2f2f4] border border-[#d2d2d7] flex items-center justify-center overflow-hidden">
                                <div ref={mascotLottieRef} className="w-12 h-12" aria-label="Cute Doggie animation" />
                            </div>
                            <div>
                                <h1 className="font-semibold text-[#1d1d1f] text-xl tracking-tight leading-none mb-1"> AI 영작 튜터 - Grammar Dog v0.3</h1>
                                <div className="text-sm font-medium text-[#6e6e73] tracking-wide">
                                    {session ? `LV ${session.level} • ${session.topic}` : "학습 준비 중..."}
                                </div>
                            </div>
                        </div>
                        {/* <button
                            onClick={toggleTheme}
                            className="px-4 py-2 text-sm font-semibold text-[#1d1d1f] bg-[#f2f2f4] rounded-xl border border-[#d2d2d7] transition-colors duration-150 hover:bg-[#eaeaef]"
                        > */}
                            {/* DOS 모드 */}
                        {/* </button> */}
                    </div>
                    {/* Apple 스테이터스 바 */}
                    {session && (
                        <div className="relative z-10 px-5 py-2.5 flex gap-4 items-center border-b border-[#e5e5ea] bg-[#f8f8fa]">
                            <StatusBar />
                        </div>
                    )}

                    {/* 대화 로그 영역 */}
                    <div
                        className="relative flex-1 overflow-y-auto p-4 sm:p-6 space-y-5 bg-[#f5f5f7]"
                        onClick={() => inputRef.current?.focus()}
                    >
                        {lines.filter(l => l.type !== "ascii").map((line, i) => (
                            <div
                                key={i}
                                className={`flex ${line.type === "user" ? "justify-end" : "justify-start"}`}
                            >
                                {line.type !== "user" && (
                                    <div className="w-9 h-9 rounded-full bg-[#f2f2f7] flex items-center justify-center mr-3 shrink-0 text-[11px] font-semibold tracking-wide text-[#1d1d1f] border border-[#d2d2d7]">
                                        {line.type === "error" ? "!" : "AI"}
                                    </div>
                                )}
                                <div className="flex flex-col max-w-[85%]">
                                    <div
                                        className={`p-4 sm:text-[17px] leading-relaxed shadow-sm whitespace-pre-wrap word-break ${line.type === "user"
                                            ? "bg-[#0a84ff] text-white rounded-[18px] rounded-tr-sm font-semibold shadow-[0_4px_12px_rgba(10,132,255,0.22)]"
                                            : line.type === "error"
                                                ? "bg-[#ff453a] text-white rounded-[18px] rounded-tl-sm font-semibold shadow-[0_2px_8px_rgba(255,69,58,0.2)]"
                                                : "bg-white border border-[#d2d2d7] text-[#1d1d1f] rounded-[18px] rounded-tl-sm font-medium shadow-[0_2px_8px_rgba(0,0,0,0.06)]"
                                            }`}
                                    >
                                        {(line.type === "system" && phase === "SETUP_LEVEL" && line.text.includes("[L")) ? (
                                            <span
                                                className="block cursor-pointer p-4 my-2 border border-[#d2d2d7] rounded-2xl bg-[#ffffff] text-[#1d1d1f] font-medium hover:bg-[#f7faff] hover:border-[#0a84ff] transition-colors text-center text-lg"
                                                onClick={() => {
                                                    const match = line.text.match(/\[L\d+\]\s(.+)/);
                                                    if (match) handleLevelClick(match[1]);
                                                }}
                                            >
                                                {line.text.replace(/\[L\d+\]\s/, "📚")}
                                            </span>
                                        ) : (line.type === "system" && phase === "SETUP_TOPIC" && line.text.includes("[T")) ? (
                                            <span
                                                className="block cursor-pointer p-4 my-2 border border-[#d2d2d7] rounded-2xl bg-[#ffffff] text-[#1d1d1f] font-medium hover:bg-[#f7faff] hover:border-[#0a84ff] transition-colors text-center text-lg"
                                                onClick={() => {
                                                    const match = line.text.match(/\[T\d+\]\s(.+)/);
                                                    if (match) handleTopicClick(match[1]);
                                                }}
                                            >
                                                {line.text.replace(/\[T\d+\]\s/, "🎯 ")}
                                            </span>
                                        ) : (line.type === "system" && phase === "SETUP_GRAMMAR" && line.text.includes("[G")) ? (
                                            <span
                                                className="block cursor-pointer p-4 my-2 border border-[#d2d2d7] rounded-2xl bg-[#ffffff] text-[#1d1d1f] font-medium hover:bg-[#f7faff] hover:border-[#0a84ff] transition-colors text-center text-lg"
                                                onClick={() => {
                                                    const match = line.text.match(/\[G\d+\]\s(.+)/);
                                                    if (match) handleGrammarClick(match[1]);
                                                }}
                                            >
                                                {line.text.replace(/\[G\d+\]\s/, "📝 ")}
                                            </span>
                                        ) : (line.type === "tutor" && (line.text.includes("[📝 Question]") || line.text.includes("[📝 Next Question]"))) ? (
                                            renderGuideBubbleContent(line.text)
                                        ) : (line.type === "tutor" && line.text.includes("[Tutor Feedback]")) ? (
                                            renderFeedbackBubbleContent(line.text)
                                        ) : (
                                            line.text.replace(/\[Sys\]\s?/, "")
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}

                        {streamingText !== null && (
                            <div className="flex justify-start">
                                <div className="w-9 h-9 rounded-full bg-[#f2f2f7] flex items-center justify-center mr-3 shrink-0 text-[11px] font-semibold tracking-wide text-[#1d1d1f] border border-[#d2d2d7]">
                                    AI
                                </div>
                                <div className="flex flex-col max-w-[85%]">
                                    <div className="p-4 sm:text-[17px] leading-relaxed whitespace-pre-wrap word-break bg-white border border-[#d2d2d7] text-[#1d1d1f] rounded-[18px] rounded-tl-sm font-medium shadow-[0_2px_8px_rgba(0,0,0,0.06)]">
                                        {streamingText}
                                        <span className="inline-block w-1.5 h-4 ml-1 bg-slate-400 animate-pulse align-middle"></span>
                                    </div>
                                </div>
                            </div>
                        )}

                        {loading && streamingText === null && (
                            <div className="flex justify-start">
                                <div className="w-9 h-9 rounded-full bg-[#f2f2f7] flex items-center justify-center mr-3 shrink-0 text-[11px] font-semibold tracking-wide text-[#1d1d1f] border border-[#d2d2d7]">
                                    AI
                                </div>
                                <div className="px-5 py-4 bg-white border border-[#d2d2d7] rounded-[18px] rounded-tl-sm shadow-[0_2px_8px_rgba(0,0,0,0.06)] flex items-center h-[72px]">
                                    <div ref={loadingLottieRef} className="w-34 h-24" aria-label="Loading french bulldog animation" />
                                </div>
                            </div>
                        )}

                        <div ref={bottomRef} className="h-4" />
                    </div>

                    {/* 하단 명령줄 (Apple) */}
                    <form onSubmit={onSubmit} className="p-4 bg-white border-t border-[#e5e5ea] z-20 shadow-[0_-8px_18px_-8px_rgba(0,0,0,0.08)] sm:rounded-b-[28px]">
                        <div className="flex gap-3">
                            <input
                                ref={inputRef}
                                type="text"
                                value={inputVal}
                                onChange={(e) => setInputVal(e.target.value)}
                                disabled={loading}
                                placeholder={
                                    loading ? "입력 대기 중..."
                                        : phase === "SETUP_LEVEL" ? "레벨을 선택하거나 입력하세요..."
                                            : phase === "SETUP_TOPIC" ? "주제를 선택하거나 입력하세요..."
                                                : phase === "SETUP_GRAMMAR" ? "문법을 선택하거나 입력하세요..."
                                                    : "여기에 영작해 보세요! (!레벨 / 패스)"
                                }
                                className="flex-1 px-5 py-4 bg-[#f2f2f4] border border-[#d2d2d7] focus:border-[#0071e3] focus:bg-white rounded-2xl outline-none text-[#1d1d1f] sm:text-lg font-medium transition-colors placeholder:text-[#8f8f94] placeholder:font-medium"
                                autoFocus
                                autoComplete="off"
                                spellCheck="false"
                            />
                            <button
                                type="submit"
                                disabled={loading || !inputVal.trim()}
                                className="px-8 font-semibold text-white rounded-2xl transition-colors disabled:opacity-50 bg-[#0071e3] hover:bg-[#0062c3] shadow-sm flex items-center justify-center text-lg hidden sm:block"
                            >
                                확인
                            </button>
                            {/* 모바일 최적화 버튼 (접근성) */}
                            <button
                                type="submit"
                                disabled={loading || !inputVal.trim()}
                                className="w-14 font-semibold text-white rounded-2xl transition-colors disabled:opacity-50 bg-[#0071e3] hover:bg-[#0062c3] shadow-sm flex items-center justify-center text-lg sm:hidden"
                            >
                                ↑
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {isStreaming && (
                <div className="pointer-events-none fixed inset-0 z-40 flex items-end justify-end p-6 sm:p-10">
                    <div className="w-[52vw] h-[52vw] max-w-[460px] max-h-[460px] opacity-95 drop-shadow-[0_12px_30px_rgba(0,0,0,0.3)] animate-pulse">
                        <div ref={pawsLottieRef} className="w-full h-full" aria-label="Paws animation" />
                    </div>
                </div>
            )}

            {/* 게이미피케이션 모달 오버레이 */}
            {modalEvent && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-in fade-in duration-300">
                    <div className="bg-white p-8 rounded-3xl shadow-[0_12px_28px_rgba(0,0,0,0.12)] flex flex-col items-center max-w-sm w-[90%] transform transition-all scale-100 animate-in zoom-in-90 duration-300 border border-[#d2d2d7]">
                        {/* Lottie Slot: modal event visual */}
                        {/* <div className="w-16 h-16 mb-4 rounded-2xl border border-[#d2d2d7] bg-[#f2f2f4] flex items-center justify-center text-[10px] font-semibold text-[#6e6e73]">
                            <div className="w-12 h-6 rounded-lg bg-[#f2f2f4] border border-[#d2d2d7] flex items-center justify-center overflow-hidden">
                                <div ref={pawsLottieRef} className="w-10 h-5" aria-label="Paws animation" />
                            </div>
                        </div> */}
                        {modalEvent === "LEVEL_UP" ? (
                            <>
                                <h2 className="text-2xl font-semibold text-[#1d1d1f] mb-2 text-center leading-tight">축하합니다!<br />게이지 100% 달성</h2>
                                <p className="text-[#6e6e73] font-medium text-center mb-6">훌륭한 실력이군요!<br />다음 레벨에 도전해 보세요.</p>
                                <button
                                    onClick={() => setModalEvent(null)}
                                    className="w-full py-4 rounded-2xl font-semibold text-white text-lg bg-[#0071e3] hover:bg-[#0062c3] transition-colors"
                                >
                                    계속하기 (NEXT)
                                </button>
                            </>
                        ) : (
                            <>
                                <h2 className="text-2xl font-semibold text-[#1d1d1f] mb-2 text-center leading-tight">위험방수!<br />게이지 0% 추락</h2>
                                <p className="text-[#6e6e73] font-medium text-center mb-6">오답이 너무 많아<br />레벨이 강등될 위기입니다!</p>
                                <button
                                    onClick={() => setModalEvent(null)}
                                    className="w-full py-4 rounded-2xl font-semibold text-white text-lg bg-[#ff3b30] hover:bg-[#e2352b] transition-colors"
                                >
                                    다시 도전하기
                                </button>
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
