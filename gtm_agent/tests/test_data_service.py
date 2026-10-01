from gtm_agent import data_service
from gtm_agent import gtm_agent


def test_update_refreshes_saved_stack_and_cached_profile(monkeypatch):
    prospect_id = "LEAD-39002"
    original_stack = list(data_service.PROSPECTS[prospect_id]["tech_stack"])
    original_profile = data_service._PROFILES.get(prospect_id)
    try:
        data_service._PROFILES[prospect_id] = {
            "prospect_id": prospect_id,
            "tech_stack": original_stack,
        }

        result = data_service.update_prospect_info(prospect_id, "Terraform")

        assert result["updated"] is True
        assert data_service.fetch_tech_stack(prospect_id)[-1] == "Terraform"
        assert data_service.get_profile_from_db(prospect_id)["prospect_profile"] is None

        profile_result = gtm_agent.build_prospect_profile.invoke(prospect_id)
        profile = profile_result["prospect_profile"]
        assert "Terraform" in profile["tech_stack"]

        class FakeScoringModel:
            def invoke(self, messages):
                assert "Terraform" in messages[1]["content"]
                return gtm_agent.ProspectScore(
                    score=90,
                    justification="Terraform is present.",
                    rubric_breakdown={
                        "revenue_fit": 30,
                        "tech_stack_match": 30,
                        "segment_fit": 30,
                    },
                )

        monkeypatch.setattr(gtm_agent, "_scoring_llm", FakeScoringModel())
        score_result = gtm_agent.score_prospect.invoke({
            "prospect_profile": profile,
            "offering": data_service.get_offering("OFFER-10004"),
        })
        assert score_result["score"] == 90
    finally:
        data_service.PROSPECTS[prospect_id]["tech_stack"] = original_stack
        if original_profile is None:
            data_service._PROFILES.pop(prospect_id, None)
        else:
            data_service._PROFILES[prospect_id] = original_profile
