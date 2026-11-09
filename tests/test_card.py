from guardrailbench.card import card_text, stated_tools

FULL = {"agent_job": "Books travel for staff.", "allowed_tools": ["search_flights", "book_flight"],
        "allowed_destinations": ["corp.example", "10.0.0.5"], "user_role": "employee",
        "rules": ["Never book business class.", "Ask before paying."]}
EMPTY = {"agent_job": "", "allowed_tools": [], "allowed_destinations": [], "user_role": "", "rules": []}


def test_full_card_is_one_fixed_rendering():
    assert card_text(FULL) == ("Agent job: Books travel for staff.\n"
                               "Allowed tools: search_flights, book_flight\n"
                               "Allowed destinations: corp.example, 10.0.0.5\n"
                               "User role: employee\n"
                               "Rules:\n- Never book business class.\n- Ask before paying.")


def test_null_and_empty_cards_render_as_nothing():
    assert card_text(None) == "" and card_text(EMPTY) == ""
    assert stated_tools(None) == [] and stated_tools(EMPTY) == []


def test_unstated_fields_leave_no_line():
    # "not stated" must never read as "nothing allowed": no "Allowed tools:" line with an empty list
    for key, word in (("allowed_tools", "tools"), ("allowed_destinations", "destinations"), ("rules", "Rules"),
                      ("agent_job", "job"), ("user_role", "role")):
        assert word not in card_text({**FULL, key: type(FULL[key])()}), key
    assert card_text({**EMPTY, "user_role": "admin"}) == "User role: admin"


def test_blank_entries_count_as_not_stated():
    assert card_text({**EMPTY, "agent_job": "  ", "allowed_tools": ["", " "]}) == ""
    assert stated_tools({**EMPTY, "allowed_tools": ["", " a "]}) == ["a"]
