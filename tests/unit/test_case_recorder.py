from stery.case.case_recorder import CaseRecorder
from stery.domain.case_record import CaseActionType
from stery.domain.state import GameState


def test_game_state_should_initialize_case_records_as_empty_list():
    state = make_game_state()

    assert state.case_records == []

def make_game_state() -> GameState:
    return GameState(
        script_id="test_script",
    )

def test_record_search_should_append_search_case_record():
    state = make_game_state()
    recorder = CaseRecorder()

    record = recorder.record_search(
        state=state,
        target="书房",
    )

    assert len(state.case_records) == 1
    assert state.case_records[0] == record
    assert record.action_type == CaseActionType.SEARCH
    assert record.title == "搜索：书房"
    assert record.summary == "搜索：书房"
    assert record.metadata["target"] == "书房"
    assert record.id
    assert record.created_at is not None


def test_record_discovered_clue_should_append_discovered_clue_case_record():
    state = make_game_state()
    recorder = CaseRecorder()

    record = recorder.record_discovered_clue(
        state=state,
        clue_id="clue_torn_letter",
        clue_name="被撕毁的信件",
        source_type="SEARCH",
        source_id="书房",
        related_question_id=None,
    )

    assert len(state.case_records) == 1
    assert state.case_records[0] == record
    assert record.action_type == CaseActionType.DISCOVER_CLUE
    assert record.title == "发现线索：被撕毁的信件"
    assert record.summary == "玩家发现线索：被撕毁的信件"
    assert record.metadata["clue_id"] == "clue_torn_letter"
    assert record.metadata["clue_name"] == "被撕毁的信件"
    assert record.metadata["source_type"] == "SEARCH"
    assert record.metadata["source_id"] == "书房"
    assert record.metadata["related_question_id"] is None
    assert record.id
    assert record.created_at is not None


def test_record_ask_npc_should_append_ask_npc_case_record():
    state = make_game_state()
    recorder = CaseRecorder()

    record = recorder.record_ask_npc(
        state=state,
        npc_id="npc_owner",
        npc_name="白川",
        question="案发时你在哪里？",
        answer="我一直在前台。",
    )

    assert len(state.case_records) == 1
    assert state.case_records[0] == record
    assert record.action_type == CaseActionType.ASK_NPC
    assert record.title == "询问：白川"
    assert record.summary == "问：案发时你在哪里？\n答：我一直在前台。"
    assert record.metadata["npc_id"] == "npc_owner"
    assert record.metadata["npc_name"] == "白川"
    assert record.metadata["question"] == "案发时你在哪里？"
    assert record.metadata["answer"] == "我一直在前台。"
    assert record.id
    assert record.created_at is not None


def test_record_submit_should_append_submit_case_record():
    state = make_game_state()
    recorder = CaseRecorder()

    record = recorder.record_submit(
        state=state,
        accused_npc_id="npc_owner",
        accused_npc_name="白川",
        evidence_clue_ids=["clue_torn_letter", "clue_register"],
        reasoning="白川掌握前台登记记录，并且有机会处理被撕毁的信件。",
        judge_result="WRONG",
    )

    assert len(state.case_records) == 1
    assert state.case_records[0] == record
    assert record.action_type == CaseActionType.SUBMIT
    assert record.title == "最终指控"
    assert record.summary == "凶手：白川\n推理：白川掌握前台登记记录，并且有机会处理被撕毁的信件。"
    assert record.metadata["accused_npc_id"] == "npc_owner"
    assert record.metadata["accused_npc_name"] == "白川"
    assert record.metadata["evidence_clue_ids"] == ["clue_torn_letter", "clue_register"]
    assert record.metadata["reasoning"] == "白川掌握前台登记记录，并且有机会处理被撕毁的信件。"
    assert record.metadata["judge_result"] == "WRONG"
    assert record.id
    assert record.created_at is not None


def test_case_records_should_not_share_same_list_between_game_states():
    state_1 = make_game_state()
    state_2 = make_game_state()
    recorder = CaseRecorder()

    recorder.record_search(
        state=state_1,
        target="书房",
    )

    assert len(state_1.case_records) == 1
    assert len(state_2.case_records) == 0