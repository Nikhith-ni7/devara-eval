# Demonstrate and publish this project

## Three-minute demo

1. State the engineering problem: prompt changes can improve average scores while breaking previously working answers.
2. Run the synthetic comparison and identify it as synthetic. Show the aggregate pass count and the five individual regressions.
3. Open the tuple question (`prog-004`), read both answers, and explain the failed checks.
4. Open timeout (`prog-014`), malformed (`prog-024`), empty (`prog-034`), and provider-error (`prog-044`) cases. Explain that the remaining tests continued.
5. Save a human review and explain why keyword checks are insufficient for correctness.
6. Export the report, show the snapshot hashes, and run the automated test suite.
7. Explain the Devara integration contract and distinguish tested adapter behavior from live integration status.

## Before you claim this as a live Devara evaluation

Connect your actual bot. Commit the final source and dataset. Record a controlled baseline/candidate pair, the bot commit and model version, and human reviews. Repeat the runs to understand variability. Publish selected raw examples with sensitive content removed.

Do not call fixture results “AI accuracy,” claim a performance improvement from a single sample, or imply live integration was tested before it was. Do not claim three to five weeks of personal implementation work merely because that was the original estimate. Review and understand generated code, make your own changes, and be able to explain your decisions during an interview.

## Suggested repository title

**Devara Eval — AI Response Evaluation and Regression Testing**

## Honest initial resume bullet

“Developed and validated a FastAPI, SQLite, and React evaluation platform with a versioned 50-question programming dataset, prompt comparison, provider failure handling, and human-review workflows.”

Only add live Devara findings after actually measuring them. Describe your own implementation and learning accurately, including AI assistance if asked.

## First improvements to own

- Connect Devara and add one real integration test using your wrapper.
- Add ten original questions from failures you discover and version the dataset.
- Review every changed answer and document any lexical false positives.
- Add an experiment notebook with repeated latency measurements and model provenance.
- Replace the in-process queue only when you need multiple workers or reliable job resumption.
