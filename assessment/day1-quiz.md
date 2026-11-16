# Day 1 quiz: Building the agent

> **Hands-on workshop for the AI-Driven DevOps (AIDD) program, School of Computer Science and Engineering, Jain (Deemed-to-be University), Bengaluru**

10 questions · 10 minutes · one correct answer each unless stated.

1. What does a large language model (LLM) fundamentally do?
   a) Searches the internet for answers  b) Predicts the next piece of text  c) Runs SQL queries  d) Stores your previous chats

2. You ask a model about "CampusMate Rule 42B" (which doesn't exist) and it confidently quotes a rule. This is called:
   a) Overfitting  b) Tokenisation  c) Hallucination  d) Throttling

3. Why does a chatbot "remember" earlier messages in a conversation?
   a) The model stores them in its weights  b) The app resends the conversation history with each request  c) AWS keeps a cookie  d) Temperature is set to 0

4. You give a Strands agent a `@tool` function and ask a question that needs it. What happens?
   a) The tool runs before every message  b) The model asks for the tool, Strands runs it and passes the result back, then the model answers  c) The model reads your Python source code  d) Nothing, tools must be called by hand

5. Which IAM concept answers "who can do what on which resource"?
   a) Region  b) Policy  c) VPC  d) Availability Zone

6. In Strands Agents, how does the model know when to use your `@tool` function?
   a) From the function's name, type hints and docstring  b) From the file name  c) It calls every tool every time  d) From the AWS region

7. What does AgentCore Runtime require for `runtimeSessionId`?
   a) A number  b) At least 33 characters  c) The student's email  d) Exactly 8 digits

8. You call the deployed agent twice with the same session ID and once with a new one. What happens?
   a) All three remember each other  b) Same session remembers; the new session starts fresh  c) None remember  d) The new session crashes

9. In AgentCore Memory, why does notebook 06 wait and retry before checking long-term facts?
   a) The API is rate-limited to one call per minute  b) Long-term extraction runs asynchronously in the background  c) Memory needs a reboot  d) To save money

10. Our AgentCore Gateway uses AWS_IAM inbound authorization. What does that mean?
    a) Anyone with the URL can call it  b) Callers must sign requests with AWS credentials allowed to invoke this gateway  c) Users log in with Cognito  d) Only Lambda can call it

---
<details><summary><b>Answer key: instructor only</b></summary>

1 b · 2 c · 3 b · 4 b · 5 b · 6 a · 7 b · 8 b · 9 b · 10 b
</details>
