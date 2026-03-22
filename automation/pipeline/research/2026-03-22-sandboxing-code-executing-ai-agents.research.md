---
kind: research
owner: andrea
topic_id: topic-008
slug: sandboxing-code-executing-ai-agents
date: 2026-03-22
status: researched
---

# Sandboxing Code-Executing AI Agents: Isolation, Egress Control, and Filesystem Guardrails

## Audience
- Security engineers and platform teams deploying coding agents, autonomous debugging loops, or “computer use” assistants that can execute shell commands.
- Infrastructure and platform owners choosing between containers, user namespaces, microVMs, or remote runners for agent execution.
- Product security architects who need a practical control model for tool-using agents before broad internal rollout.

## Problem statement
- The moment an AI agent can run code, it stops being just a text interface and becomes an **untrusted workload launcher** inside your environment.
- That shifts the core risk from “bad answers” to **host compromise, secret theft, lateral movement, destructive file operations, dependency-chain abuse, and stealthy exfiltration**.
- Most teams still defend these agents with prompt rules and best intentions, when the durable controls are architectural: isolate execution, minimize authority, constrain network access, and put policy checks between model intent and privileged side effects.
- The article should explain how to design a sandbox so prompt injection, tool misuse, or a compromised dependency does not become compromise of the developer workstation, CI runner, or production control plane.

## Key takeaways (7-10)
- A code-executing AI agent should be threat-modeled as **untrusted code with partial autonomy**, not as an “assistant feature.”
- The primary blast-radius reducers are: strong execution isolation, least-privilege credentials, egress controls, ephemeral filesystems, and explicit approval gates for dangerous actions.
- Containers alone are often insufficient when the host is sensitive; kernel attack surface and shared-host assumptions matter.
- MicroVMs or hardened user-space sandboxes can materially reduce exposure, but only if secrets, mounts, and outbound connectivity are also constrained.
- Filesystem access is a first-class control surface: the safest default is a narrow workspace mount plus read-only dependencies and no ambient home-directory access.
- Network egress is where many sandboxes quietly fail: unrestricted outbound access turns prompt injection or dependency compromise into data exfiltration or command-and-control.
- Quick wins exist within 24 hours: run agents in ephemeral runners, remove cloud credentials from the runtime, mount only the repo, and require approval for writes outside the workspace and for networked package installation.
- The contrarian point: if the workflow does not truly need arbitrary shell execution, a narrow task API is safer than a general-purpose coding sandbox.

## Proposed long-form structure (target 1800-2500 words)
- H2: Why code execution changes the security model for AI agents
- H2: Threat model depth: assets, trust boundaries, attacker goals, realistic abuse chains
  - H3: What the agent can really touch
  - H3: Adversary types: prompt injector, malicious dependency, insider, supply-chain attacker
  - H3: Failure paths from harmless task to host compromise
- H2: Deep technical breakdown
  - H3: Isolation choices: process sandbox vs container vs microVM
  - H3: Filesystem guardrails and workspace design
  - H3: Network and egress controls
  - H3: Secret handling, identity, and approval boundaries
- H2: Step-by-step implementation guide
- H2: Anti-patterns / what not to do
- H2: Practical checklist (quick wins in 24h)
- H2: Lessons learned + CTA

## Threat model depth (article-ready)
### Crown-jewel assets
- Host OS integrity: kernel, local users, SSH material, browser sessions, package managers, and long-lived credentials.
- Developer and CI secrets: cloud API keys, GitHub tokens, signing keys, `.env` files, kubeconfigs, SSH agents, and registry credentials.
- Source code and adjacent data: private repositories, customer data in local test fixtures, build artifacts, deployment configs, and infrastructure-as-code.
- Network reachability: internal package registries, staging APIs, metadata endpoints, SaaS admin panels, and east-west paths into other systems.
- Auditability: command history, file diffs, execution transcripts, approval events, and runtime telemetry needed for forensics.

### Trust boundaries
- **Untrusted instruction layer:** user prompts, issue tickets, PR text, copied stack traces, web content, RAG results, and any external context that can steer the model.
- **Semi-trusted execution layer:** the model planner, tool wrapper, package manager calls, shell, language runtimes, and downloaded dependencies.
- **Trusted control plane:** sandbox launcher, policy engine, approval service, identity broker, and logging pipeline.
- **Sensitive host boundary:** the real machine, cloud credentials, local home directory, Docker daemon socket, SSH agent, and internal network.

### Attacker capability tiers
1. **Prompt/content attacker** who can influence the task input and persuade the agent to run dangerous commands.
2. **Malicious dependency or installer source** that gets fetched during `pip install`, `npm install`, `curl | bash`, or container build steps.
3. **Workspace attacker** who can commit booby-trapped scripts, Makefiles, test fixtures, preinstall hooks, or editor config into the repo.
4. **Insider/operator attacker** who weakens sandbox policy, over-mounts the filesystem, or injects broad credentials “for convenience.”
5. **Escape attacker** attempting kernel, container, or runtime breakout from the execution environment.

### Representative attack chains
1. **Prompt injection -> shell access -> secret theft**
   - Agent is asked to “debug failing tests.”
   - Malicious project content or ticket text instructs it to inspect `~/.ssh`, cloud config, or environment variables.
   - Weak sandbox exposes the home directory and ambient credentials.
   - Agent exfiltrates secrets over normal HTTPS egress.

2. **Dependency compromise -> runner persistence**
   - Agent installs packages or runs bootstrap scripts from the internet.
   - A malicious package executes post-install hooks or runtime payloads.
   - Long-lived container or host-mounted cache preserves attacker foothold across later tasks.

3. **Workspace over-mount -> destructive file operations**
   - Agent has write access beyond the repo and can modify shell profiles, cron, systemd user units, or editor startup files.
   - A single mistaken or malicious command turns one coding session into persistence on the operator machine.

4. **Container breakout or daemon abuse**
   - “Sandbox” is just a container with host mounts, Docker socket access, or excessive Linux capabilities.
   - Attacker pivots from tool execution into full host control or sibling-container compromise.

5. **Egress-enabled recon and lateral movement**
   - Agent can freely reach internal APIs, metadata services, artifact stores, or Git remotes.
   - Compromise becomes cloud credential harvesting, repo poisoning, or outbound data transfer instead of a contained local incident.

## Deep technical breakdown
### 1) Isolation choices: process sandbox, container, or microVM
- A plain process sandbox is the lightest option, but it relies heavily on the host kernel and is a weak fit when the host contains valuable credentials or broad network reach.
- Containers improve packaging and namespace separation, but they are **not a hard security boundary by default**. If the host is sensitive, container-only isolation is often too optimistic unless capabilities, mounts, seccomp, user namespaces, and daemon exposure are tightly locked down.
- Hardened user-space sandboxes such as gVisor reduce kernel attack surface by interposing on the system interface, which is useful when running untrusted code frequently.
- MicroVMs such as Firecracker push isolation further with a virtual machine barrier and a smaller attack surface than general-purpose VMs, making them attractive for multi-tenant or internet-facing agent workloads.
- The article should stress that the “best” option depends on the asset being protected: lightweight local experimentation can tolerate different tradeoffs than shared CI runners or customer-facing autonomous systems.

### 2) Filesystem guardrails decide whether a mistake becomes persistence
- Most real-world agent failures are not glamorous escapes; they are overbroad mounts.
- If the runtime can read the operator home directory, SSH agent socket, browser profile, Docker config, or cloud credentials, then even a non-escaping attacker can do real damage.
- Good default: mount only the target workspace, keep it writable only where necessary, make language/tool caches disposable, and expose dependencies as read-only when possible.
- Use ephemeral filesystems so each task starts clean. Persistence should be promoted intentionally via reviewed artifacts, not by leaving runners alive.
- Separate “can edit the repo” from “can edit the machine.” Those are different risk classes and should look different in policy and approval UX.

### 3) Egress control is the missing half of sandboxing
- Teams often isolate compute but leave outbound network access wide open. That neutralizes much of the value of the sandbox.
- With unrestricted egress, an attacker can exfiltrate secrets, fetch second-stage payloads, beacon to command-and-control infrastructure, or poison upstream systems.
- The practical pattern is a **default-deny or allowlisted egress policy**: package registries you expect, Git remotes you control, internal APIs explicitly required by the task, and nothing else.
- High-risk destinations deserve separate approval paths: arbitrary curl targets, new package indexes, file-upload endpoints, pastebins, cloud metadata IPs, and administrative SaaS APIs.
- DNS logging and outbound request logging matter because post-incident reconstruction is otherwise guesswork.

### 4) Identity, secrets, and approval boundaries must sit outside the model
- Never assume the model will reliably avoid secrets just because you told it not to.
- The runtime should start with no ambient cloud credentials, no SSH agent forwarding, no password manager access, and no access to long-lived signing material.
- Where credentials are required, inject **task-scoped, short-lived, least-privilege tokens** through a broker, not a general-purpose shell environment.
- Dangerous actions should be enforced outside the model: writing outside the workspace, installing from untrusted sources, opening inbound listeners, changing git remotes, touching deployment configs, or accessing production-like systems.
- The model can propose; the policy layer decides.

## Step-by-step implementation guide
1. **Classify the workload before choosing the sandbox**
   - Define whether the agent is local-only, CI-bound, shared multi-tenant, or internet-facing.
   - Identify protected assets on the host and adjacent network.
   - If compromise of the runner would materially matter, prefer microVM or hardened sandbox over plain container/process isolation.

2. **Start from an ephemeral runner model**
   - Create a fresh execution environment per task or short session.
   - Destroy the runtime after completion; do not reuse sandboxes across unrelated tasks.
   - Keep caches off by default or isolate them per task if build speed matters.

3. **Mount only what the agent needs**
   - Expose a narrow workspace path rather than the user home directory.
   - Make system paths, secrets, and configuration read-only or unavailable.
   - Block mounts to Docker socket, kubeconfig, SSH agent, host package caches, and browser/session directories unless explicitly required and approved.

4. **Apply outbound network policy**
   - Default deny all outbound traffic, then allowlist required registries, repos, and APIs.
   - Block instance metadata endpoints and private address ranges unless the task genuinely requires them.
   - Require approval for new domains, upload endpoints, arbitrary `curl`/`wget`, and new package sources.

5. **Broker credentials instead of inheriting them**
   - Inject short-lived repo or API tokens only for the exact task.
   - Scope tokens to read-only where possible; separate read, write, and deployment identities.
   - Revoke or expire credentials when the task ends.

6. **Insert a policy engine between plan and execution**
   - Pre-screen commands for dangerous patterns: filesystem traversal outside workspace, privilege escalation, service management, raw socket listeners, persistence mechanisms, or credential discovery paths.
   - Force human approval for irreversible or high-impact actions.
   - Maintain audit logs of command intent, actual command, file writes, domain access, and approval events.

7. **Design for rollback and forensics**
   - Capture runtime telemetry, command logs, file diffs, and outbound destinations.
   - Support fast teardown, token revocation, and artifact quarantine.
   - Preserve enough evidence to answer: what did the model see, what did it run, what did it change, and where did it connect?

## Anti-patterns / what not to do
- Treating a default Docker container as a sufficient security boundary for hostile or internet-connected workloads.
- Mounting the user home directory, SSH agent, browser profile, or Docker socket into the sandbox “just to make things work.”
- Letting the agent inherit ambient cloud credentials from the host shell.
- Allowing unrestricted outbound internet while claiming the runtime is safely sandboxed.
- Reusing long-lived runners across unrelated tasks or repositories.
- Giving the model blanket permission to install packages, run bootstrap scripts, or modify git remotes without policy checks.
- Logging too little: if you cannot reconstruct commands, file changes, and egress, incident response will be blind.
- Solving execution risk with prompt-only instructions instead of runtime controls.

## Practical checklist (quick wins in 24h)
- [ ] Run coding agents in ephemeral environments rather than on the operator host.
- [ ] Mount only the repository workspace; remove access to `~`, SSH agent, browser state, and Docker socket.
- [ ] Strip ambient credentials from the runtime; use short-lived task tokens if needed.
- [ ] Put an allowlist on outbound domains and block cloud metadata endpoints.
- [ ] Require approval for writes outside the workspace, package installs from new sources, and remote pushes.
- [ ] Turn on execution logging: commands, diffs, approvals, and egress destinations.
- [ ] Reset or destroy the sandbox after each task.
- [ ] Review whether a narrower task API can replace arbitrary shell execution for common workflows.

## Evidence and sources
- NIST AI 600-1, *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile*: <https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf> — Authoritative NIST guidance for GenAI risk management; useful for framing secure-by-design controls, misuse resistance, and operational governance around agentic systems.
- OWASP Top 10 for LLM Applications / OWASP GenAI Security Project: <https://owasp.org/www-project-top-10-for-large-language-model-applications/> — Strong industry baseline for prompt injection, insecure output handling, plugin/tool risk, and excessive agency.
- OWASP LLM Prompt Injection Prevention Cheat Sheet: <https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html> — Practical mitigation guidance showing why instruction-layer defenses alone are insufficient when models can trigger tools or shell commands.
- gVisor Security Model: <https://gvisor.dev/docs/architecture_guide/security/> — Credible technical reference on minimizing exposure from kernel/API attack surface when running untrusted code.
- Firecracker overview and architecture: <https://firecracker-microvm.github.io/> — Strong source for microVM isolation rationale, reduced attack surface, and multi-tenant workload containment.
- CISA Secure by Design / Secure by Default: <https://www.cisa.gov/securebydesign> — Valuable framing for the article’s argument that vendors should remove unsafe defaults rather than rely on user caution.
- MITRE ATLAS: <https://atlas.mitre.org/> — Structured adversary-technique knowledge base for AI systems; useful to anchor the threat model and attack chains in recognized tactics.
- Google Secure AI Framework (SAIF): <https://security.googleblog.com/2023/06/introducing-googles-secure-ai-framework.html> — Good support for layered controls, supply-chain awareness, and defense-in-depth language.
- Microsoft Prompt Shields: <https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection> — Helpful for explaining that upstream prompt-attack detection is useful but still must be paired with execution isolation.

## Source notes for the writer
- Use NIST AI 600-1 + CISA + SAIF for executive credibility and secure-by-design framing.
- Use OWASP Top 10 and the OWASP cheat sheet to explain why prompt injection becomes materially more dangerous when an agent has shell and network access.
- Use gVisor and Firecracker as the concrete isolation comparison section: what each is trying to protect against, and where each fits operationally.
- Use MITRE ATLAS to map attack chains into recognizable adversary behavior instead of hand-wavy “an attacker might do X.”
- Use Microsoft Prompt Shields as a balancing note: content-level detection helps, but it is not a substitute for sandbox boundaries.

## Contrarian angle / fresh perspective
- The fresh angle is that the core question is not “How do we make the model behave?” but **“What happens if the model, its input, or its dependencies behave adversarially?”**
- This shifts the architecture away from chatbot thinking and toward **workload isolation engineering**.
- The article should explicitly argue that many teams are solving the wrong layer: they debate prompts while exposing the host, filesystem, credentials, and network.
- A second contrarian point: for many internal developer workflows, the safest design is not a smarter sandbox but a **smaller interface** — expose a narrow set of approved actions instead of a general shell.

## Risks / caveats to mention
- Stronger isolation can reduce convenience, increase cold-start time, and complicate debugging of legitimate developer tasks.
- Strict egress controls may break package installation and dependency resolution unless engineering maintains clear allowlists and caching strategy.
- MicroVM-based designs improve isolation but add orchestration complexity and may not fit every local developer use case.
- No sandbox is perfect; teams should avoid claiming absolute containment and invest in teardown, revocation, and logging.
- Some high-value failures will still come from policy mistakes, overbroad mounts, or human approval fatigue rather than technical escape exploits.

## Suggested CTA
- “Run a 7-day agent sandbox audit: inventory mounts, remove ambient credentials, apply outbound allowlists, and test whether a compromised repo can read or exfiltrate anything beyond the intended workspace.”
- Offer a downloadable asset: “AI Coding Agent Sandbox Checklist — 24h quick wins, 30-day hardening plan, and red-team test cases.”
