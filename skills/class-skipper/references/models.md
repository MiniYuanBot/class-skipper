# Worker models

Read this before resolving requests and looking up worker caches. The
coordinator is always the session the user started; this file only chooses the
model and reasoning effort of subagents.

## Configuration

Models come from the manifest's top-level `models` key
([course.example.yaml](course.example.yaml)) or from an explicit request such as
“写作用 sonnet”, which overrides the manifest for that run. `models` is not a run
option: do not pass it to `prepare --options`, so changing models or hosts keeps
the same run, plan and source caches.

```yaml
models:
  claude:
    workers: {model: sonnet, effort: medium}   # every worker except the editor
    editor: {model: opus, effort: high}
  codex:
    workers: {model: gpt-6.1-sol, effort: medium}
    editor: {model: gpt-6-astra, effort: high}
```

Use only the section for the current host (`claude` for Claude Code, `codex` for
Codex). Inside it:

| Key | Applies to |
| --- | --- |
| `workers` | every worker below that has no own key |
| `reader` | oversized-material range readers |
| `writer` | chapter writers |
| `figure` | the slide figure reader |
| `links` | the external link finder |
| `editor` | the single editorial revision |

A value is a model string or `{model, effort}`; either field may be omitted.

| Host | `model` | `effort` |
| --- | --- | --- |
| Claude Code | Agent tool alias: `opus`, `sonnet`, `haiku`, `fable` (full IDs such as `claude-sonnet-5-5` are not accepted) | `low`, `medium`, `high`, `xhigh`, `max` |
| Codex | a model ID the host lists, e.g. `gpt-6-astra`, `gpt-6.1-sol` | `low`, `medium`, `high`, `xhigh`, `max`, `ultra` |

**Default.** A field missing from `reader`, `writer`, `figure` or `links` comes
from `workers`; anything still missing, and anything missing from `editor`,
means the session's own model and effort. Without any `models` configuration every worker runs on the
session model. Never choose a different model on your own initiative.

## Applying the settings

- **Claude Code:** pass the resolved alias as the Agent tool's `model` and the
  effort as its `effort`. For session-model workers, pass the coordinator's own
  alias explicitly, because an omitted `model` may resolve to a configured
  subagent default instead of the session model.
- **Codex:** pass model and effort through the fields the active spawn tool's
  schema defines (configuration files call the effort `model_reasoning_effort`);
  never guess field names. For session-model workers, pass the parent's model and
  effort explicitly unless the host guarantees inheritance. An already configured
  agent role may be used only when its effective model and effort match the
  resolved values; check `[agents]` defaults, which can defeat inheritance. When
  overriding, start the worker without chat history if the tool allows it, and
  always give the full worker brief from SKILL.md.
- Image viewing or web access must be available to the chosen worker; otherwise
  follow SKILL.md's capability fallbacks.

## Fallback

If a configured model is unavailable or rejected, retry the worker once on the
session model, then let the coordinator do the task. Never try other model IDs
or spawn probe agents. Report every substitution; never present a fallback as
the configured model.

## Cache and reporting

Resolve settings before cache lookup and record them in the request as
workflow.md describes. If spawning falls back, update the request and repeat the
lookup before model work; never store fallback output under the rejected
settings' key. Report configured versus applied model and effort per role.
