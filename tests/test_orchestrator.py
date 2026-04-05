from backend.agents.orchestrator.main_graph import ResearchAssistantOrchestrator


def test_pipeline_interrupt_sequence() -> None:
    orchestrator = ResearchAssistantOrchestrator()
    state = orchestrator.create_initial_state(
        task_id="task_demo",
        task_type="analysis",
        user_query="我想分析农业产值对碳排放的影响，同时控制农药使用量",
        data_files=[],
        paper_files=[],
    )

    state = orchestrator.run_until_pause(state)
    assert state["current_node"] == "data_mapping"
    assert state["interrupt_reason"] == "data_mapping_required"

    for expected_node in ["literature", "novelty", "analysis", "brief"]:
        state["human_decision"] = {"decision": "approved", "payload": {}}
        state = orchestrator.run_until_pause(state, resume=True)
        assert state["current_node"] == expected_node
        assert state["status"] == "interrupted"

    state["human_decision"] = {"decision": "approved", "payload": {}}
    state = orchestrator.run_until_pause(state, resume=True)
    assert state["current_node"] == "writing"
    assert state["status"] == "done"
    assert state["result"] is not None
