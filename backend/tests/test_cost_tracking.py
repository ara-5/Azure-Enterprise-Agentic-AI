from app.core.cost_tracking import _cost_for


def test_cost_for_chat_uses_input_and_output_rates():
    cost = _cost_for("chat", prompt_tokens=1000, completion_tokens=1000)
    # default rates: input 0.0025/1K, output 0.01/1K
    assert round(cost, 6) == round(0.0025 + 0.01, 6)


def test_cost_for_embedding_uses_embedding_rate_only():
    cost = _cost_for("embedding", prompt_tokens=1000, completion_tokens=0)
    assert round(cost, 6) == round(0.00013, 6)


def test_cost_for_zero_tokens_is_zero():
    assert _cost_for("chat", 0, 0) == 0.0
