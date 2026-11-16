# Day 2 quiz: Making it production-ready

> **Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science and Engineering, Jain (Deemed-to-be University), Bengaluru**

10 questions · 10 minutes · one correct answer each.

1. In the Flask portal, what does the student dropdown control?
   a) The AWS region  b) The Memory actor ID, so each student is remembered separately  c) The model  d) The Lambda timeout

2. A **span** in a trace is:
   a) The whole request from question to answer  b) One step inside a request, such as one tool call or one model call  c) A CloudWatch alarm  d) A log group

3. CloudWatch Transaction Search is:
   a) A per-agent setting  b) An account-level setting that must be on to search agent traces  c) A paid add-on for Lambda  d) Part of Cedar

4. Why do input tokens grow with each step of an agent's answer?
   a) The model gets slower  b) Each model call includes the system prompt, tool descriptions and everything so far  c) Memory duplicates messages  d) Logging adds tokens

5. "LLM-as-a-judge" means:
   a) A human grades the model  b) A second model scores answers against a rubric  c) The model grades itself during the answer  d) A Cedar policy scores answers

6. Online evaluation vs an on-demand spot check: which is true?
   a) Online is instant; spot checks take a day  b) Online continuously scores sampled live sessions (minutes later); a spot check scores one session on request (seconds)  c) They are the same  d) Spot checks need no traces

7. Why is "never file leave over 3 days" in the system prompt *not* security?
   a) System prompts are encrypted  b) The model can be persuaded by injected text; nothing outside the model enforces it  c) Prompts expire  d) It is too long

8. In Cedar, if one policy permits an action and another forbids it, the result is:
   a) Permit  b) Forbid  c) Random  d) The newer policy wins

9. In our leave policy, `context.input.days` refers to:
   a) The days since the student joined  b) The `days` argument of the tool call being checked  c) Today's date  d) The model's temperature

10. A student files 3 days today and 3 days tomorrow. The `leave_limit` policy:
    a) Blocks the second request because it checks totals  b) Allows both, because it checks one call at a time; cumulative limits need state  c) Blocks both  d) Deletes the first request

---
<details><summary><b>Answer key: instructor only</b></summary>

1 b · 2 b · 3 b · 4 b · 5 b · 6 b · 7 b · 8 b · 9 b · 10 b
</details>
