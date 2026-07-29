# Young Minds Fellowship — Cohort Two Application (SandBench)

Applicant: [Your full name] — solo founder, applying as an individual
Product: SandBench — https://sandbench.vercel.app/ · https://github.com/Umgauthamram/sandbench
Status: personal project, owned by the applicant

Anything in `[square brackets]` is a personal detail only you can fill in. Everything else is factual to the current build.

**Note on the account:** this draft is being written from Sudhakar's Claude account, but the application, the project, and the work are yours. Use your own name and your own email on the form — a mismatch between the applicant name and the GitHub/contact details is the kind of thing reviewers query.

---

## 1. Video script (~2 minutes spoken)

> Record on Loom, camera on, one take is fine. Set sharing to "anyone with the link". Talk slower than feels natural.

**[0:00 — Open with the problem, not yourself]**

"Right now, a huge share of the code being written in the world isn't being written by people. It's being written by AI models and AI agents. And most of it goes straight into a repo, or straight into production, without anyone actually checking two things: is it correct, and is it safe to run?

Those are different questions, and today they're answered by different tools. Correctness is a test suite. Safety is a security scan. Nobody gives you one answer.

**[0:25 — The specific risk]**

And there's a sharper version of this problem. To find out if unknown code is safe, you have to run it. But running untrusted code is exactly the dangerous act — remote code execution, data exfiltration, a script that quietly calls out to a server you've never heard of. So teams either don't check, or they check on a machine they shouldn't be checking on.

**[0:45 — What I built]**

That's what I'm building SandBench for. You hand it code — yours, or something a model generated — and it runs it inside a hardened, offline, throwaway sandbox: no network, read-only filesystem, capped memory and CPU, all Linux capabilities dropped. And critically, it doesn't run against your kernel — it runs behind gVisor, a userspace kernel, so even a container escape has to get through that before it touches the host. It runs the static gates and the tests, watches what the code actually *tries* to do, and gives you back one verdict: clean, suspicious, broken, or malicious — with the evidence behind it. And when the code is broken, it attempts a patch and re-runs it to prove the patch worked.

**[1:15 — The part that makes it more than a scanner]**

Every one of those runs is recorded as a training example — the score before the fix, the score after, the difference is the reward signal. So the same loop that judges code becomes a reinforcement-learning environment that can train a model to *repair* code. Hugging Face is where you go to find a model. SandBench is where you find out whether what that model produced is safe to run — and it turns that answer into training data you own.

**[1:35 — Why me, why this matters]**

I care about this because [say it plainly — e.g. "I've watched how fast people trust AI-generated code, including myself", or your own moment where unverified code caused a real problem]. The gap between "the model gave me code" and "I know this code is safe" is where a lot of damage is going to happen over the next few years, and it's mostly invisible right now.

It also matters that this runs entirely on your own machine, offline. The teams with the most to lose from running untrusted code — regulated industries, defence, anyone with proprietary source — are exactly the teams who can't ship their code to a cloud sandbox. So they don't check at all. I want to fix that.

**[2:00 — Close]**

The working system is live, the engine and CLI run end to end, and I'm now looking for the first AI labs and testing teams to point it at real code. That's what I'd use the fellowship for."

---

## 2. Team or Solo?

**Solo.**

I'm the sole founder and sole builder of SandBench. I designed the architecture and wrote the full stack myself — the hardened Docker sandbox and execution engine, the static and dynamic analysis gates, the scoring and verdict logic, the LLM repair loop, the Redis job queue, the Python worker, the Next.js portal, and the CLI. There are no co-founders. Applying as an individual.

---

## 3. What have you tried or built so far?

**A working end-to-end prototype, self-hosted and live.** Not a mockup — you can clone it and get a verdict in three commands, or use the hosted portal at sandbench.vercel.app.

What exists today:

**The sandbox (the hard part).** Every submission runs in a fresh, ephemeral Docker container with outbound networking fully disabled (`--network none`), a read-only root filesystem with a single writable `/work` tmpfs, hard caps on memory (256MB), CPU (0.5 share) and process count (64 PIDs), all Linux capabilities dropped, and `no-new-privileges` enforced. The container is destroyed after every run. This is what makes running unknown code survivable.

**A verdict, not a pass/fail.** Static gates (Bandit, Semgrep, YARA, plus obfuscation heuristics) run before execution; dynamic monitoring records what the code actually attempted during execution — blocked network calls, writes outside `/work`, resource limits hit. Those combine into one legible judgment — `clean` / `suspicious` / `broken` / `malicious` — with the supporting evidence attached, not just a score.

**A repair loop that produces training data.** When code fails, SandBench sends the code and the failure logs to a model, applies the returned unified diff, and re-runs it in a fresh sandbox to verify the fix. The improvement (`score_after − score_before`) is the reward signal, and each attempt is stored as a redacted trace. Run the engine once and it's a code-safety check; run it a thousand times and it's a benchmark; keep the traces and it's an RL environment you can fine-tune your own repair model on. The repair model is deliberately swappable — start on a hosted API, swap in your own local fine-tune, no client changes.

**Two interfaces on one engine.** A CLI (`python cli/main.py check`) for developers and agent pipelines, and a multi-user web portal with a versioned leaderboard (peak score per user, per task, per suite version; anything flagged malicious is quarantined and scored 0%).

**Deployed architecture.** Next.js frontend on Vercel, Redis job queue, Python execution worker on an Ubuntu host via Coolify with access to the Docker daemon — so the engine scales independently of the UI, and the whole thing can also be run air-gapped on a single machine.

**Design decisions I'd defend:** offline-by-default, so proprietary code never leaves the network; user-supplied API keys held only in host-side memory, never written to the database, logs, or traces; and a documented contamination policy for the task suites, because a benchmark you can memorise is worthless.

**Honest status:** the system works and the security model holds, but I have not yet run it against real production codebases at another organisation. No external users or pilots yet. That's the immediate next step, and it's the main thing I want the fellowship's help with.

---

## 4. Who are your users/customers, and how have you engaged with them?

**Who it's for — three groups, in priority order:**

1. **AI labs and model teams** who need to evaluate code their models produce, at volume, without a human reading every diff — and who want the eval runs to become a training set rather than a one-off leaderboard number.
2. **Test and QA engineers, and platform/security engineers**, who inherit AI-generated code and get asked "is this safe to merge?" with no tool that answers correctness and safety together.
3. **Teams who cannot use a cloud sandbox at all** — regulated, defence, or otherwise proprietary work. Today they largely don't verify untrusted code, because verifying it means either shipping their source out or running it somewhere dangerous. SandBench's self-hostable, offline design exists specifically for them, and I think this is the wedge.

**How I've engaged so far — being straight about it:**

I've been my own first user. The system was built against my own need: I kept generating code with models and had no honest way to answer "should I run this?" So every design decision — the verdict categories, the offline default, the evidence trail, the swappable repair model — came out of using it on real code myself rather than from a market study.

I have **not** yet done structured user discovery with AI labs or QA teams, and I'm not going to pretend otherwise. The product is open source and live so that engagement can start from something real rather than a pitch deck.

**What I plan to do in the first weeks of the fellowship:**

- Run 10–15 direct conversations with test/QA engineers and platform-security engineers, with one specific question: how do you decide today whether AI-generated code is safe to merge, and what do you do when you can't tell?
- Offer 3 free hands-on pilots: they point SandBench at their own suite, and I watch where the verdicts are wrong, unhelpful, or too slow.
- Approach model teams with the RL angle: bring your model, run the suite, keep the traces — measure whether a model fine-tuned on SandBench traces actually repairs code better. That result is the strongest proof this is a product and not a tool.
- Use the fellowship network to reach the offline/regulated segment, which is the hardest to reach cold and the most likely to pay.

---

## 5. Why did you choose to work on this idea?

Because I hit the problem myself, and then realised the tooling for it doesn't exist.

I was generating a lot of code with models. It looked right. Sometimes it was right. But I had no way to answer the only question that mattered — *can I run this?* — without just running it and hoping. And when I looked for something that would tell me, I found the ecosystem split cleanly in half: benchmarks that measure correctness and assume nothing is hostile, and security scanners that look for hostility and don't care whether the code works. Neither one gives you a verdict. [Optional: add the specific moment — the piece of AI-generated code that did something you didn't expect.]

Then there's the part that made me commit. The act of verifying untrusted code *is* the risky act. You can't know what code does without running it, and running it is what exposes you. That's a genuinely hard engineering problem, not a UI problem, and hard problems are where a solo builder can still get ahead of well-funded teams — because most of the value is in the sandbox being actually correct, and that's craft, not headcount.

The third reason is the one I care about most. Verdicts are useful, but they're a commodity — someone will always undercut them. Traces aren't. Every run SandBench does produces a training example, so the loop that judges code can train a model that repairs code, and that model belongs to whoever ran the loop. A leaderboard row is disposable. A model you own isn't. That turns a security utility into infrastructure, and I'd rather spend years building infrastructure.

And I want this to work for the teams who currently get nothing. Cloud-only sandboxes exclude exactly the people with the most to lose from running untrusted code. Building it offline-first was harder and slower, and it's the decision I'm proudest of. [Optional: one line about why open, self-hostable, sovereign tooling matters to you — especially building this from India.]

---

## Quick checklist before submitting

- [ ] Loom or Drive video link set to **anyone with the link can view** — check it in an incognito window
- [ ] Video under the length limit; you say the problem before you say the product name
- [ ] Fill the `[bracketed]` personal lines — the "why me" moment is the part reviewers remember
- [ ] Every claim above is true of the current build; delete anything you can't demo if asked
- [ ] Include both links: live site and GitHub repo
