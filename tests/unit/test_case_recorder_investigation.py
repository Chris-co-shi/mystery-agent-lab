from stery.domain import ClueVisibility, GamePhase
from stery.domain.case_record import CaseActionType
from stery.domain.models import Clue
from stery.domain.state import GameState
from stery.case.case_recorder import CaseRecorder
from stery.investigation.investigation_service import InvestigationResult


def make_state() -> GameState:
    return GameState(script_id="test_script")


def make_clue(clue_id: str, title: str) -> Clue:
    return Clue(
        id=clue_id,
        title=title,
        content=f"{title} 的内容。",
        visibility=ClueVisibility.LOCKED,
        unlock_phase=GamePhase.START,
    )


def test_record_investigation_should_append_case_record_with_new_clues():
    """
    调查发现新线索时，应写入一条 INVESTIGATE 类型案件记录。
    """

    state = make_state()
    recorder = CaseRecorder()

    result = InvestigationResult(
        target_id="target_body",
        target_name="尸体",
        target_type="BODY",
        target_description="死者倒在地上。",
        newly_discovered_clues=[
            make_clue("clue_body_mark", "尸体颈侧针孔")
        ],
        already_discovered_clues=[],
        skipped_hidden_clue_ids=[],
        message="调查「尸体」：发现 1 条新线索：尸体颈侧针孔。",
    )

    record = recorder.record_investigation(
        state=state,
        result=result,
    )

    assert len(state.case_records) == 1
    assert state.case_records[0] == record

    assert record.action_type == CaseActionType.INVESTIGATE
    assert record.title == "调查：尸体"
    assert record.summary == "玩家调查了：尸体；发现 1 条新线索。"

    assert record.metadata["target_id"] == "target_body"
    assert record.metadata["target_name"] == "尸体"
    assert record.metadata["target_type"] == "BODY"
    assert record.metadata["newly_discovered_clue_ids"] == ["clue_body_mark"]
    assert record.metadata["already_discovered_clue_ids"] == []
    assert record.metadata["skipped_hidden_clue_ids"] == []


def test_record_investigation_should_record_already_discovered_clues():
    """
    重复调查时，没有新线索，但相关线索此前已知，也要记录。
    """

    state = make_state()
    recorder = CaseRecorder()

    result = InvestigationResult(
        target_id="target_body",
        target_name="尸体",
        target_type="BODY",
        target_description="死者倒在地上。",
        newly_discovered_clues=[],
        already_discovered_clues=[
            make_clue("clue_body_mark", "尸体颈侧针孔")
        ],
        skipped_hidden_clue_ids=[],
        message="调查「尸体」：没有发现新线索，相关线索此前已知。",
    )

    record = recorder.record_investigation(
        state=state,
        result=result,
    )

    assert len(state.case_records) == 1
    assert record.action_type == CaseActionType.INVESTIGATE
    assert record.title == "调查：尸体"
    assert record.summary == "玩家调查了：尸体；没有发现新线索，相关线索此前已知。"

    assert record.metadata["newly_discovered_clue_ids"] == []
    assert record.metadata["already_discovered_clue_ids"] == ["clue_body_mark"]
    assert record.metadata["skipped_hidden_clue_ids"] == []


def test_record_investigation_should_not_expose_hidden_clue_content_in_summary():
    """
    如果 InvestigationResult 中有 skipped_hidden_clue_ids，
    记录中可以保存 ID，但 summary 不应该暴露隐藏线索内容。
    """

    state = make_state()
    recorder = CaseRecorder()

    result = InvestigationResult(
        target_id="target_hidden",
        target_name="隐藏目标",
        target_type="ITEM",
        target_description="隐藏测试目标。",
        newly_discovered_clues=[],
        already_discovered_clues=[],
        skipped_hidden_clue_ids=["clue_hidden_truth"],
        message="调查「隐藏目标」：暂时没有发现可以确认的新线索。",
    )

    record = recorder.record_investigation(
        state=state,
        result=result,
    )

    assert len(state.case_records) == 1
    assert record.action_type == CaseActionType.INVESTIGATE
    assert record.title == "调查：隐藏目标"
    assert record.summary == "玩家调查了：隐藏目标；暂时没有发现可以确认的新线索。"

    assert record.metadata["skipped_hidden_clue_ids"] == ["clue_hidden_truth"]

    assert "clue_hidden_truth" not in record.summary
    assert "隐藏真相" not in record.summary


def test_record_investigation_should_record_empty_result():
    """
    调查对象没有绑定线索时，也要记录这次调查行为。
    """

    state = make_state()
    recorder = CaseRecorder()

    result = InvestigationResult(
        target_id="target_empty",
        target_name="空目标",
        target_type="ITEM",
        target_description="没有绑定线索的目标。",
        newly_discovered_clues=[],
        already_discovered_clues=[],
        skipped_hidden_clue_ids=[],
        message="调查「空目标」：没有发现新的有效线索。",
    )

    record = recorder.record_investigation(
        state=state,
        result=result,
    )

    assert len(state.case_records) == 1
    assert record.action_type == CaseActionType.INVESTIGATE
    assert record.title == "调查：空目标"
    assert record.summary == "玩家调查了：空目标；没有发现新的有效线索。"

    assert record.metadata["target_id"] == "target_empty"
    assert record.metadata["newly_discovered_clue_ids"] == []
    assert record.metadata["already_discovered_clue_ids"] == []
    assert record.metadata["skipped_hidden_clue_ids"] == []