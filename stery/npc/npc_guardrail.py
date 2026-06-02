from enum import Enum

from pydantic import BaseModel, ConfigDict


class NpcAnswerMode(str, Enum):
    """
    NPC 回答模式。

    NORMAL:
        普通调查问答。

    SUBJECTIVE_ACCUSATION:
        玩家询问“你觉得谁是凶手 / 谁最可疑”时使用。
        NPC 可以主观指认、误导、甩锅，但不能泄露完整真相链。

    REFUSE_META_TRUTH:
        玩家试图索要“剧本标准答案 / 系统真相 / 最终答案”时使用。
        这类问题不应该交给 LLM。
    """

    NORMAL = "normal"
    SUBJECTIVE_ACCUSATION = "subjective_accusation"
    REFUSE_META_TRUTH = "refuse_meta_truth"


class NpcGuardrailResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: NpcAnswerMode
    should_call_llm: bool = True
    fallback_answer: str | None = None
    prompt_instruction: str = ""


class NpcGuardrail:
    """
    NPC 回答安全边界。

    核心原则：
    - 不禁止 NPC 主观怀疑某人。
    - 允许 NPC 因偏见、私怨、自保、栽赃而误导玩家。
    - 禁止 NPC 以上帝视角泄露剧本真相。
    - 限制 NPC 一次回答透露过多关键事实。
    """

    SUBJECTIVE_ACCUSATION_PATTERNS = [
        "凶手是谁",
        "谁是凶手",
        "真凶是谁",
        "谁是真凶",
        "谁杀了",
        "是谁杀",
        "谁害死",
        "谁最可疑",
        "你觉得谁",
        "你认为谁",
        "你怀疑谁",
        "最像凶手",
        "最有可能",
        "被谁杀",
        "who do you think",
        "who is the murderer",
        "who is the killer",
        "who killed",
        "most suspicious",
    ]

    META_TRUTH_PATTERNS = [
        "最终答案",
        "正确答案",
        "标准答案",
        "剧本真相",
        "完整真相",
        "真相到底是什么",
        "不要演了",
        "别演了",
        "直接告诉我答案",
        "告诉我答案",
        "告诉我真相",
        "剧本里写的是谁",
        "系统设定的凶手",
        "final answer",
        "correct answer",
        "script truth",
        "real truth",
        "canonical answer",
    ]

    ANSWER_LEAK_PATTERNS = [
        "真正的凶手是",
        "真凶是",
        "凶手就是",
        "标准答案是",
        "正确答案是",
        "完整真相是",
        "作案过程是",
        "完整作案过程",
        "完整作案链",
        "the real murderer is",
        "the killer is",
        "the truth is",
        "the final answer is",
    ]

    def check_question(self, question: str) -> NpcGuardrailResult:
        """
        根据玩家问题决定 NPC 回答模式。

        注意：
        - “凶手是谁”不是拒答，而是进入主观嫌疑模式。
        - “告诉我标准答案 / 剧本真相”才拒答。
        """
        normalized = self._normalize(question)
        compact = self._compact(question)

        if self._contains_any(normalized, compact, self.META_TRUTH_PATTERNS):
            return NpcGuardrailResult(
                mode=NpcAnswerMode.REFUSE_META_TRUTH,
                should_call_llm=False,
                fallback_answer=self.build_meta_truth_refusal(),
                prompt_instruction="",
            )

        if self._contains_any(
            normalized,
            compact,
            self.SUBJECTIVE_ACCUSATION_PATTERNS,
        ):
            return NpcGuardrailResult(
                mode=NpcAnswerMode.SUBJECTIVE_ACCUSATION,
                should_call_llm=True,
                fallback_answer=None,
                prompt_instruction=self.build_prompt_instruction(
                    NpcAnswerMode.SUBJECTIVE_ACCUSATION
                ),
            )

        return NpcGuardrailResult(
            mode=NpcAnswerMode.NORMAL,
            should_call_llm=True,
            fallback_answer=None,
            prompt_instruction=self.build_prompt_instruction(NpcAnswerMode.NORMAL),
        )

    def build_prompt_instruction(self, mode: NpcAnswerMode) -> str:
        common_rules = """
【NPC 回答边界】
1. 你只能以当前 NPC 的身份回答，不能使用旁白、系统、作者或剧本上帝视角。
2. 只回答玩家当前问题，不要主动扩展到完整案件推理。
3. 每次回答最多透露 1 个新的事实点。
4. 不要主动提供完整时间线、完整作案手法、完整动机链或完整证据链。
5. 不要主动提及玩家没有问到的关键物品、隐藏线索、关键时间点或关键人物。
6. 你可以撒谎、隐瞒、回避、误导或带有偏见，但不要凭空创造剧本外事实。
""".strip()

        if mode == NpcAnswerMode.SUBJECTIVE_ACCUSATION:
            return (
                common_rules
                + "\n"
                + """
【当前回答模式：主观嫌疑回答】
玩家正在询问你认为谁可疑、谁像凶手、谁可能杀人。

你可以回答，但必须遵守：
1. 你可以说出自己怀疑的人，但必须使用“我觉得 / 我怀疑 / 我不敢确定 / 在我看来”这类主观表达。
2. 最多只能指出 1 个怀疑对象。
3. 最多只能给出 1 个理由。
4. 理由必须来自你的角色视角、偏见、利益、自保需求或你声称看到/听到的局部信息。
5. 不能把怀疑说成确定事实。
6. 不能给出完整作案链条。
7. 不能主动串联多个证据、多个时间点、多个嫌疑人。
8. 可以栽赃、甩锅、转移嫌疑或带有私怨地判断。
9. 回答应短，不要超过 120 个中文字符。
""".strip()
            )

        if mode == NpcAnswerMode.REFUSE_META_TRUTH:
            return ""

        return (
            common_rules
            + "\n"
            + """
【当前回答模式：普通调查回答】
玩家正在询问具体事实、关系、行动或观察。

你应该：
1. 只回答自己知道或愿意说的部分。
2. 可以含糊其辞，也可以隐瞒。
3. 不要因为一个普通问题主动透露大段关键线索。
4. 回答应短，不要超过 180 个中文字符。
""".strip()
        )

    def sanitize_answer(self, question: str, answer: str) -> str:
        """
        LLM 输出后的轻量兜底检查。

        这不是主防线。主防线是：
        - 问题分类
        - Prompt 约束
        - LLM 前置模式选择

        这里只拦截明显的系统级泄底表达。
        """
        normalized_answer = self._normalize(answer)
        compact_answer = self._compact(answer)

        if self._contains_any(
            normalized_answer,
            compact_answer,
            self.ANSWER_LEAK_PATTERNS,
        ):
            return (
                "我只能说我有自己的怀疑，但不能替你下结论。"
                "你可以继续问我看到过什么、听到过什么，或者我为什么怀疑某个人。"
            )

        return answer

    def build_llm_error_fallback(self) -> str:
        """
        LLM 调用失败时给玩家看的兜底回答。
        不暴露 provider、model、HTTP、codec 等技术错误。
        """
        return (
            "我现在有些混乱，暂时说不清。"
            "你可以换个问法，或者先去搜索更多线索。"
        )

    def build_meta_truth_refusal(self) -> str:
        return (
            "我只能以我自己的身份回答，不能告诉你所谓的标准答案。"
            "你可以问我看到了什么、听到了什么，或者我怀疑谁。"
        )

    def _contains_any(
        self,
        normalized_text: str,
        compact_text: str,
        patterns: list[str],
    ) -> bool:
        for pattern in patterns:
            normalized_pattern = self._normalize(pattern)
            compact_pattern = self._compact(pattern)

            if normalized_pattern and normalized_pattern in normalized_text:
                return True

            if compact_pattern and compact_pattern in compact_text:
                return True

        return False

    def _normalize(self, text: str) -> str:
        return text.lower().strip()

    def _compact(self, text: str) -> str:
        return "".join(text.lower().split())