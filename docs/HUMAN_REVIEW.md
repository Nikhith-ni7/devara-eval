# Human review rubric

Deterministic checks test whether expected phrases and requested structure appear. They do not prove that an answer is factually correct. Negation can fool lexical scoring; valid paraphrases can fail it. Review every regression and a fixed random sample of unchanged answers. For a first portfolio experiment, review all 50 baseline and candidate answers.

## Rating dimensions

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Correctness | Central claim false, misleading, or unsafe | Mostly correct with a substantive error or unjustified claim | Correct, with appropriate caveats and no substantive error |
| Completeness | Does not answer the question | Answers the core but misses a requested example or important constraint | Covers all requested parts and relevant edge cases |
| Clarity | Confusing, contradictory, or unusable | Understandable with avoidable ambiguity | Clear, direct, internally consistent |

Use each case's `review_notes` to check its specific trap. Missing, timed-out, or malformed answers receive correctness 0 and completeness 0; explain the provider failure instead of inventing semantic analysis. A well-worded but false answer may earn clarity 2 and correctness 0. Do not collapse these dimensions into an “accuracy” percentage.

## Procedure

1. Freeze dataset/scorer versions and a baseline/candidate pair before reviewing.
2. For a more rigorous experiment, export answers with randomized A/B labels before review. The current dashboard displays version labels and therefore is not blinded.
3. Read the question, expected concepts, case-specific notes, and full answer. Verify disputed programming claims using primary documentation.
4. Record all three ratings, your reviewer name, and concrete evidence: incorrect statement, missing edge case, or faulty example.
5. If possible, ask a second reviewer to independently rate a shared calibration sample. Report disagreements and how they were resolved; a solo review is valid but must be labeled as such.
6. Do not silently modify a rule to make a candidate pass. Update the dataset version and rerun both prompts after any scoring-rule correction.

## Worked example (illustrative, not a saved review)

Question: What does tuple immutability mean when a tuple contains a list?

Candidate: “A tuple can change freely.”

- Correctness: 0 — the tuple container cannot have its element bindings replaced.
- Completeness: 0 — no distinction between the tuple and its contained mutable list.
- Clarity: 1 — short and readable, but the unqualified wording obscures what can change.

The synthetic demo creates this regression at `prog-004`. You must save any actual review yourself; the application does not manufacture reviewer judgments.
