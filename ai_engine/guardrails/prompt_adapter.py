"""Bridge to Quân's build_messages without importing a not-yet-merged module."""


def make_prompt_generator(build_messages, complete):
    """Both callbacks are server-owned. complete(messages) returns JSON str/dict.

    Call only as generate= in run_guarded_research. Never invoke on raw request
    text: this adapter assumes the guarded pipeline has already redacted inputs.
    Provider must use structured JSON output, no Markdown fences.
    """
    def generate(safe):
        messages = build_messages(
            safe.query, [dict(p) for p in safe.passages],
            facts=safe.material_facts, tax_period=safe.tax_period or None,
        )
        return complete(messages)
    return generate
