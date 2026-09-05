INPUT_PRICE_PER_1M = 0.05
OUTPUT_PRICE_PER_1M = 0.40


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    input_cost = (prompt_tokens / 1_000_000) * INPUT_PRICE_PER_1M
    output_cost = (completion_tokens / 1_000_000) * OUTPUT_PRICE_PER_1M
    return round(input_cost + output_cost, 6)