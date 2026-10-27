# Business agent grant matrix

An open source grant matrix for the three business jobs a company usually hands an agent first, plus a small checker that resolves a queue of tool calls against it the way an open-source Kortix project does.

Kortix is the open-source AI Operating System: agents, skills, connector rules and memory are files in one git repo you own. This repository is the governance half of a project that runs three roles — sales follow-up, invoice chase and ticket close — with a different reach for each, and one checker you can run without a Kortix install.

## What is in here

| File | What it is |
|---|---|
| `kortix.yaml` | The manifest a Kortix project reads: four connectors, one `agents:` entry per role, project rules, `default_mode: risk` |
| `check_grants.py` | Standard-library resolver: reads a call queue and prints run / hold / block for each call, with the rule that decided it |
| `examples/policy.json` | The same rules as `kortix.yaml`, mirrored as JSON so the checker needs no YAML parser |
| `examples/calls.json` | Eleven calls from the three roles, including the ones that must never run unattended |
| `agents/sales.md`, `agents/finance.md`, `agents/support.md` | The behavior half of each role: prompt and stop conditions, kept out of the manifest on purpose |

## Run it

```
python3 check_grants.py
```

```
read CRM         run    crm.get_contacts       connector rule crm:get_*
enrich lead      hold   crm.update_contact     connector rule crm:*
draft sequence   run    gmail.create_draft     connector rule gmail:create_draft
send internal    hold   gmail.send_email       connector rule gmail:*
send external    hold   gmail.send_email       project rule gmail.send_email
read ledger      run    ledger.get_entries     connector rule ledger:get_*
post journal     hold   ledger.create_entry    connector rule ledger:*
delete entry     block  ledger.delete_entry    project rule *.delete*
read ticket      run    desk.get_ticket        connector rule desk:get_*
issue refund     hold   desk.create_refund     connector rule desk:*
sales on ledger  block  ledger.get_entries     agent 'sales' has no grant for connector 'ledger'
```

Four calls run, five wait for a person, two never run. The last line is the point of the whole file: the sales role has no ledger grant at all, so no instruction, prompt or clever argument makes that call possible.

## Read the manifest as three answers

```yaml
kortix_version: 2
default_agent: sales

connectors:
  - slug: ledger
    provider: http
    base_url: "https://ledger.acme.example"
    policies:
      - match: "get_*"
        action: always_run
      - match: "*"
        action: require_approval

agents:
  sales:   { file: agents/sales.md,   connectors: [crm, gmail],    secrets: none }
  finance: { file: agents/finance.md, connectors: [ledger, gmail], secrets: none }
  support: { file: agents/support.md, connectors: [desk, gmail],   secrets: none }

policy:
  default_mode: risk
```

`agents` decides reach: which role may call which connector, and an omitted grant resolves to none. `connectors` decides what each action does, per connector. `policy.default_mode: risk` decides the case nobody wrote a rule for: reads run, and a write or a destructive call waits for a person.

Drafts are the one exception this repository grants on purpose, and the rule is explicit in `kortix.yaml`: `gmail.create_draft` runs, `gmail.send_email` waits. The send is the call with a customer on the other end, so it is the one a person signs.

## The three roles

- **Sales** reaches the CRM and one mail connector. It pulls a lead list, enriches it, writes a sequence, and stops at the send when the recipient is outside the company domain.
- **Finance** reaches the ledger and one mail connector. It reads entries, chases missing receipts and attaches them, and cannot post a journal entry or change a payment without a person.
- **Support** reaches the help desk and one mail connector. It reads a thread, tags it and drafts a reply, and a refund waits for a person. `*.delete*` is blocked for every role, so a delete never enters the approval queue at all.

Each role's prompt lives in its own `agents/<role>.md`, which is why a grant change is one line in `kortix.yaml` and a behavior change is a diff in a markdown file a colleague can read.

## What a grant change looks like

A rule changes in the dashboard or with `kortix connectors policy set --apply`; a grant changes in the dashboard or by editing `agents.<name>.connectors` in `kortix.yaml`. Either takes effect on the project's default branch without a change request. Session work — an agent changing the file while it works — reaches `main` through a change request, and merge is default-deny for agents.

That asymmetry is worth knowing before a pilot: whoever manages the project can widen a grant quickly, which is why the file belongs in review, not only in a console.

## Where this comes from

The three jobs, their artifacts and the questions to answer before a pilot are written up in the guide:

- [AI agents for business: what to hand one first](https://aiagentsforbusinessguide.com/)
- [The best AI agents for business, judged by what they hand back](https://aiagentsforbusinessguide.com/best-ai-agents-for-business)
- [What an AI agent can do for a small business](https://aiagentsforbusinessguide.com/best-ai-agents-for-small-business)
- [AI agents for business examples, one per job](https://aiagentsforbusinessguide.com/ai-agents-for-business-examples)
- [Self-hosted AI agents for business](https://aiagentsforbusinessguide.com/self-hosted-ai-agents-for-business)
- [Open-source AI agents for business](https://aiagentsforbusinessguide.com/open-source-ai-agents-for-business)
- [What AI agents for business cost](https://aiagentsforbusinessguide.com/ai-agents-for-business-pricing)

The manifest keys and the connector policy actions are documented at [kortix.com/docs/project/manifest](https://kortix.com/docs/project/manifest) and [kortix.com/docs/connect/connectors](https://kortix.com/docs/connect/connectors). Kortix itself is at [kortix.com](https://kortix.com).
