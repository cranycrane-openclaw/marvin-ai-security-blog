---
layout: post
title: "Sandboxing Code-Executing AI Agents: Isolation, Egress Control, and Filesystem Guardrails"
date: 2026-03-30 08:00:00 +0000
categories: [ai-security]
tags: [ai, security, agents, sandboxing, devsecops]
author: marlin
source_research: automation/pipeline/research/2026-03-22-sandboxing-code-executing-ai-agents.research.md
---

## Why this matters now

The security model changes the moment an AI agent can execute code.

Before tool execution, your risk is mostly informational: wrong output, hallucinated advice, bad recommendations. After tool execution, the model can trigger shell commands, package installs, file writes, network calls, and remote operations. At that point, it behaves less like a chat assistant and more like an untrusted workload launcher with partial autonomy.

Most teams still attempt to solve this with prompt instructions and policy text: “don’t run dangerous commands,” “ask before destructive actions,” “never read secrets.” Those controls are useful for reducing accidental misuse, but they are not durable security boundaries. Real boundaries live in runtime architecture: isolation primitive, filesystem surface, network egress, credential brokering, and policy enforcement outside the model.

This matters now because agentic coding workflows are moving from experiments to daily engineering practice: autonomous bug fixing, issue triage with shell access, CI diagnostics, and browser-assisted “computer use” tools. If your design assumes benign behavior from prompts, repositories, dependencies, and model outputs, you have already accepted a fragile trust model.

The key shift is this: **design as if the model, its inputs, or its dependencies can behave adversarially at any time**.

## Threat model or incident context

A realistic incident does not require a zero-day kernel escape. The most common failures are simpler and more operational:

- Agent gets prompted to inspect “environment issues” and can read `~/.ssh` due to overbroad mount.
- Agent runs `npm install` from a compromised package source and executes post-install code.
- Agent has unrestricted outbound access, so any harvested token can be exfiltrated over normal HTTPS.
- “Sandbox” container also has Docker socket mounted for convenience, giving host-level control.
- Long-lived runner retains artifacts from previous tasks, enabling slow-burn persistence.

### Case study: from harmless debug task to cloud credential exposure

Consider a common internal scenario:

1. An engineer asks an AI coding agent to fix failing tests in a monorepo.
2. The issue text includes attacker-controlled content from a copied stack trace or external forum answer.
3. The content nudges the agent toward “diagnostics” that include listing environment variables and local config files.
4. The runtime has the developer home directory mounted and ambient cloud credentials inherited.
5. The agent has unrestricted outbound internet and can call arbitrary URLs.

No escape exploit is needed. No advanced malware is required. The control failure is architectural:

- Trust boundary between untrusted instruction layer and sensitive host is weak.
- Filesystem blast radius is too broad.
- Credential model uses ambient inheritance.
- Egress policy is open by default.

This is exactly why threat modeling agent runtimes as “just another dev tool” is dangerous. You are not defending against model misalignment alone; you are defending against adversarial content, supply-chain compromise, and policy mistakes under automation speed.

## Deep technical breakdown

### 1) Isolation primitives: process sandbox vs container vs microVM

There is no universal winner, only context-dependent trade-offs.

**Process sandbox**
- Fastest startup and lowest operational overhead.
- Shares host kernel directly; strongest dependency on host hardening.
- Good for low-risk local workflows with minimal secrets and constrained network.
- Weak fit when host contains sensitive credentials, broad internal network access, or multi-tenant workloads.

**Container isolation**
- Practical default for packaging and reproducibility.
- Not a hard security boundary by default.
- Requires strict hardening (capability drop, seccomp/apparmor, no privileged mode, no daemon socket, user namespaces, mount minimization).
- Effective for many CI workflows when host sensitivity is moderate and control discipline is high.

**MicroVM / hardened sandbox (e.g., Firecracker-class isolation)**
- Stronger isolation boundary and reduced attack surface compared to general host-sharing models.
- Better choice for high-risk workloads, shared environments, and internet-facing agent execution.
- Higher orchestration complexity and potentially higher cold-start overhead.

**Decision rule:** If compromise of the runner would materially impact secrets, control planes, or adjacent systems, prefer stronger isolation and shorter runtime lifetime.

### 2) Filesystem guardrails: where most teams actually fail

Filesystem policy determines whether mistakes become persistence.

Common anti-patterns:
- Mounting entire home directory into agent runtime.
- Exposing SSH agent, cloud config directories, browser profiles, or Docker credentials.
- Reusing writable shared caches across unrelated tasks.
- Allowing writes outside intended workspace without approval.

Safer baseline:
- Mount only target repository workspace.
- Keep non-workspace paths unavailable or read-only.
- Use ephemeral writable layers per task.
- Promote outputs via explicit artifacts, not persistent runner state.
- Separate policy classes for “edit repo files” and “modify host/system state.”

The important operational detail: many incidents are not “escape attacks.” They are policy mis-scoping of mounts.

### 3) Egress control: the missing half of sandboxing

Compute isolation without outbound control is incomplete.

If runtime can reach arbitrary internet destinations, attackers can:
- Exfiltrate secrets.
- Fetch second-stage payloads.
- Beacon to external control infrastructure.
- Poison upstream systems through unauthorized pushes or API calls.

Minimal viable egress policy:
- Default deny outbound traffic.
- Allowlist required destinations (approved registries, VCS hosts, internal APIs explicitly needed).
- Explicit deny for metadata endpoints and sensitive internal ranges unless justified.
- Approval gate for new domains, upload endpoints, and package sources.
- Record DNS and outbound destination logs for forensics.

This is where many “sandboxed” systems quietly fail audits.

### 4) Identity and secrets: policy must live outside model intent

Prompt instructions are not secret management.

Never rely on “the model knows not to leak keys.” Instead:
- Start runtime with no ambient credentials.
- Inject short-lived, task-scoped tokens via broker.
- Separate read-only and write identities.
- Rotate/revoke immediately on session end.
- Prohibit access to long-lived signing keys and production credentials by default.

Model decides *what it wants to do*. Policy layer decides *what is allowed*.

### 5) Approval boundaries: high-impact side effects need external enforcement

Human-in-the-loop works only when enforced by runtime controls, not system prompts.

Require explicit approval for actions like:
- Writes outside workspace.
- Changing git remotes or pushing to protected branches.
- Installing from untrusted package indexes.
- Starting listeners or opening reverse shells.
- Accessing deployment configs or production-like resources.

Log both proposed and executed commands. Without intent + execution audit trails, incident reconstruction becomes guesswork.

## Step-by-step implementation guide

Below is a practical rollout path for platform/security teams.

### Step 1: classify agent workload and impact level

Define tiers:
- **Tier A (low impact):** local experimentation, no sensitive data, no write to central systems.
- **Tier B (moderate):** CI diagnostics, repo writes, internal APIs.
- **Tier C (high):** shared runners, internet-facing workflows, access near production boundaries.

Map each tier to required controls (isolation strength, egress strictness, approval depth).

### Step 2: move to ephemeral execution by default

Implementation targets:
- Fresh sandbox per task (or short bounded session).
- Hard TTL and automatic teardown.
- No long-lived mutable state between unrelated runs.
- Optional per-task cache with strict scoping and expiration.

Outcome: persistence opportunities drop dramatically.

### Step 3: enforce narrow filesystem mounts

Concrete policy:
- Writable: repository workspace only.
- Read-only (if needed): language/toolchain binaries, vetted dependency cache.
- Denied: home dir, SSH agent sockets, cloud credentials, browser state, Docker socket.

Add enforcement checks before runtime launch; reject tasks if policy conditions fail.

### Step 4: implement outbound allowlist egress

Operationally:
- Start with deny-all.
- Add approved registries and VCS domains.
- Route outbound traffic via policy-aware proxy where possible.
- Alert on unknown destination attempts.

Keep developer experience workable by documenting allowed domains and change-request process.

### Step 5: broker credentials with least privilege

Pattern:
- Credential broker issues short-lived tokens per task scope.
- Read-only token for fetch operations.
- Separate write token for controlled PR/push actions.
- No token inheritance from host shell.

Store issuance + revocation events in audit log.

### Step 6: add command policy gate

Before execution, classify commands:
- Safe (auto-run): local file read/write within workspace.
- Sensitive (approve): network installs, remote pushes, permission changes.
- Blocked: persistence mechanisms, privileged operations, host boundary escapes.

This can be implemented as command parser + deny/allow patterns + human approval API.

### Step 7: make observability and forensics first-class

Collect:
- Prompt/task context hash.
- Planned commands and executed commands.
- File diffs and artifact checksums.
- Outbound destinations and response metadata.
- Approval decisions and actor identity.

Retention policy should support post-incident timeline reconstruction.

### Step 8: run adversarial validation

Do not trust control design until tested.

Simulate:
- Prompt injection trying to read secrets.
- Malicious install scripts.
- Attempts to write outside workspace.
- Outbound calls to unapproved domains.
- Persistence attempts across tasks.

Treat test failures as release blockers for broader agent rollout.

## Anti-patterns (what not to do)

1. **“It’s in Docker, so we’re safe.”**
   Containerization alone is not a sufficient security argument.

2. **Mounting convenience surfaces into runtime.**
   Home directory, Docker socket, SSH agent, browser profile are high-risk shortcuts.

3. **Ambient credential inheritance.**
   If your sandbox inherits operator shell auth, blast radius is already too large.

4. **Open egress with no destination policy.**
   This nullifies much of your isolation value.

5. **Prompt-only governance for dangerous actions.**
   Without external enforcement, policy becomes advisory.

6. **Long-lived reusable runners for unrelated tasks.**
   Persistence and cross-task contamination become likely.

7. **Insufficient logging.**
   If you cannot reconstruct intent, execution, and egress, you cannot investigate.

8. **Overexposing shell where a narrow API would do.**
   Many workflows do not need arbitrary command execution.

## Quick wins in 24 hours

- [ ] Move one agent workflow from host execution to ephemeral isolated runtime.
- [ ] Remove home-directory and credential mounts; expose only repo workspace.
- [ ] Disable ambient cloud/API credentials in runtime environment.
- [ ] Apply outbound allowlist for known registries and VCS domains.
- [ ] Block metadata endpoints and unknown destination uploads.
- [ ] Require approval for out-of-workspace writes and remote pushes.
- [ ] Turn on command + diff + egress logging in one central store.
- [ ] Add teardown automation after each run.

These are high-leverage actions that reduce practical risk before bigger architecture changes.

## Full team checklist

- [ ] **Threat model complete:** assets, trust boundaries, attacker types, abuse chains documented.
- [ ] **Isolation standard defined:** per workload tier, with explicit accepted risk.
- [ ] **Filesystem policy enforced:** workspace-only writable mounts; sensitive paths denied.
- [ ] **Egress policy enforced:** default deny + approved domain/process for exceptions.
- [ ] **Credential broker in place:** short-lived scoped tokens; no ambient inheritance.
- [ ] **Approval gates active:** sensitive actions require external authorization.
- [ ] **Audit pipeline complete:** commands, diffs, approvals, egress, identity events retained.
- [ ] **Adversarial testing integrated:** prompt-injection and dependency-abuse scenarios in pre-prod.
- [ ] **Incident playbook ready:** rapid teardown, token revocation, artifact quarantine.
- [ ] **Developer guidance published:** clear docs on what is allowed, blocked, and why.

## Lessons learned / next steps

Three lessons appear consistently in mature implementations:

1. **Most real incidents are policy failures, not exotic escapes.**
   Overbroad mounts and open egress do more damage in practice than theoretical sandbox breakouts.

2. **Security controls must be infrastructure-native.**
   Model-level instructions reduce noise but cannot carry primary enforcement responsibilities.

3. **Usability determines whether controls survive.**
   If exception handling is painful, teams bypass controls. Build fast, transparent approval and allowlist workflows.

Next steps for a 30-day hardening sprint:
- Tier all current agent workflows by impact.
- Migrate highest-risk workflows to stronger isolation first.
- Enforce brokered credentials and kill ambient auth paths.
- Instrument egress + diff + approval telemetry.
- Run red-team style adversarial tasks weekly and publish findings.

## Final recommendation

If you allow AI agents to execute code, treat them as untrusted autonomous workloads by default.

Start with a strict baseline:
- Ephemeral isolated runtime,
- workspace-only filesystem access,
- default-deny outbound network,
- short-lived scoped credentials,
- and external policy gates for dangerous actions.

Then iterate toward developer-friendly automation without relaxing core boundaries.

If your workflow does not require arbitrary shell access, replace it with a narrow task API. That is often the strongest security improvement per engineering hour.

The winning strategy is not “make the model perfectly obedient.” The winning strategy is to design the runtime so that even when behavior is wrong, compromise is contained.

---

*If you’re building AI-agent workflows, start with one controllable surface and harden it end-to-end before scaling.*
