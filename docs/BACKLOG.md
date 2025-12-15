# Extensions Backlog

Prioritized list of planned extensions for JMeter Test Generator.

---

## Completed

| Extension | Description |
|-----------|-------------|
| OpenAPI Change Detection | Detect API changes, auto-update JMX files |
| Correlation/Extractors | JSONPostProcessor for variable extraction (v2 scenarios) |
| Mermaid Diagram Export | Export scenario diagrams to Mermaid format |
| MCP Server Integration | Full CLI-MCP parity with 9 tools |
| Loop Support | count and while loops with interval |
| Output folder prompt | Prompt for output folder when generating JMX (default: current directory) |
| Transaction Controllers | Group samplers into logical transactions for aggregated metrics |
| Scenario Init Wizard | Interactive `jmeter-gen new scenario` command (v3.0.0) |
| Scenario Validator | Dedicated CLI and MCP tool for validating pt_scenario.yaml before generation (v3.2.0) |
| Multi-step Loops | Loop blocks wrapping multiple steps with count/while support |
| Think Time | Configurable delays between steps (`think_time` in scenario) |

---

## P1 - High Priority

| Extension | Description |
|-----------|-------------|
| Conditional Execution | if/else conditions for scenario steps |
| TestAction | Flow control: pause, stop, go to next iteration |

---

## P2 - Medium Priority

| Extension | Description |
|-----------|-------------|
| Global Authorization | Auto-apply captured token (Bearer) to all subsequent requests |
| More assertion types | JSON assertions, regex, response time |
| CSV Data Set Config | Data-driven testing with CSV files |
| Foreach Loop | Iterate over captured array variables (petIds_1, petIds_2, etc.) |
| Bearer token support | Authorization header with Bearer tokens |
| Basic auth | HTTP Basic authentication |
| API key in headers | Custom API key headers |

---

## P3 - Lower Priority

| Extension | Description |
|-----------|-------------|
| Multiple Scenarios | Multiple Thread Groups in one file |
| Assertions Library | Extended assertions (headers, timing) |
| Scenario Composition | Reusable steps with include |
| GraphQL Support | Support for GraphQL APIs |

---

See [v2/ideas/FUTURE_IDEAS.md](v2/ideas/FUTURE_IDEAS.md) for detailed specifications.
