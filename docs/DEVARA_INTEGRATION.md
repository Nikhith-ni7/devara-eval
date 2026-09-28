# Connect your Devara bot

The actual `Nikhith-ni7/owlmind_Devara` source could not be retrieved during this build. This project therefore defines an explicit integration contract rather than assuming your function names, framework, authentication, or deployment behavior. The adapter is tested with mock HTTP responses. It has **not** been verified against your live bot.

## Option A: expose an HTTP endpoint

Set the complete endpoint URL before starting the evaluator:

```bash
export DEVARA_URL=http://127.0.0.1:9000/answer
# Only when your endpoint requires a bearer token:
export DEVARA_API_KEY=your-local-secret
bash scripts/start.sh
```

Do not commit real keys. Values are read from the environment, not from `.env` files automatically.

The evaluator POSTs:

```json
{
  "question": "Explain the difference between a Python list and a tuple.",
  "system_prompt": "You are Devara, a programming assistant. Answer accurately.",
  "prompt_version": "devara-baseline-v1",
  "model": "devara-local",
  "temperature": 0,
  "seed": 42
}
```

Your endpoint returns HTTP 200 with:

```json
{"response": "Lists are mutable; tuples are immutable..."}
```

An empty string is an explicit failed result. Invalid JSON, missing fields, non-string answers, oversized responses, HTTP failures, and timeouts are classified separately. Extra response metadata is currently ignored. Response bodies and secrets from provider error pages are not copied into stored error messages.

The endpoint must honor the requested prompt/model settings, or clearly reject unsupported settings. Model APIs that do not support a seed can document that limitation in experiment notes. Each question must use fresh conversation state, unless a future dataset explicitly tests multi-turn behavior. Never feed expected facts or reference answers into Devara when collecting real results.

## Option B: use the included Python bridge

Create a wrapper in your own Devara repository. Adapt its body to your real bot:

```python
# my_eval_wrapper.py in your Devara repository
async def answer_for_eval(*, question, system_prompt, prompt_version, model, temperature, seed):
    # Replace this call with your real Devara entry point.
    # Construct fresh messages/state and use the settings above.
    reply = await your_existing_bot_call(
        question=question,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        seed=seed,
    )
    return reply  # must be a string
```

Then, in an environment with both your bot dependencies and FastAPI installed:

```bash
export PYTHONPATH="/absolute/path/to/your/Devara/repository"
export DEVARA_CALLABLE=my_eval_wrapper:answer_for_eval
uvicorn examples.devara_bridge:app --host 127.0.0.1 --port 9000
```

Run this command from the evaluation project root so `examples` can be imported. The bridge fails on startup if the callable is missing. Both synchronous and asynchronous functions are supported; synchronous functions run in a thread pool. A disconnected/timed-out synchronous function may continue running in its thread, so implement your bot's own provider timeout too.

In another terminal, set `DEVARA_URL` and start the evaluator. Pick a Devara version in **Run history**. The default `devara-local` model label is a placeholder for your deployment; create versions with the real model or deployment revision before publishing evidence.

## Before reporting live results

- Confirm from your bot's logs that the two system prompts actually reached the model.
- Record the exact Devara commit, model identifier/digest, retrieval configuration, and relevant dependencies.
- Keep dataset/scorer versions, request deadlines, and generation settings fixed when isolating a prompt change.
- Record warmup/cold-start behavior and repeat runs; a single timing sample is not a reliable performance conclusion.
- Save human reviews and examples of both improvements and regressions.

For semantic correctness, use the rubric. For a stronger experiment, build a held-out dataset that was not used to tune prompts or scoring aliases.
