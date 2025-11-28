# Extensions Backlog

Prioritized list of planned extensions for JMeter Test Generator.

---

## Completed

| Extension | Description |
|-----------|-------------|
| OpenAPI Change Detection | Detect API changes, auto-update JMX files |
| Correlation/Extractors | JSONPostProcessor for variable extraction (v2 scenarios) |
| Mermaid Diagram Export | Export scenario diagrams to Mermaid format |
| MCP Server Integration | Full CLI-MCP parity with 5 tools |
| Loop Support | count and while loops with interval |
| Output folder prompt | Prompt for output folder when generating JMX (default: current directory) |
| Transaction Controllers | Group samplers into logical transactions for aggregated metrics |

---

## P1 - High Priority

| Extension | Description |
|-----------|-------------|
| CSV Data Set Config | Data-driven testing with CSV files |
| Request body generation | Generate realistic test data with Faker |
| More assertion types | JSON assertions, regex, response time |

---

## P2 - Medium Priority

| Extension | Description |
|-----------|-------------|
| Scenario Init Wizard | Interactive `jmeter-gen scenario init` command |
| Conditional Execution | if/else conditions for scenario steps |
| Think Time | Configurable delays between steps |
| Bearer token support | Authorization header with Bearer tokens |
| Basic auth | HTTP Basic authentication |
| API key in headers | Custom API key headers |

---

## P3 - Lower Priority

| Extension | Description |
|-----------|-------------|
| Postman/Insomnia Import | Import collections to pt_scenario.yaml |
| Multiple Scenarios | Multiple Thread Groups in one file |
| Assertions Library | Extended assertions (headers, timing) |
| Scenario Composition | Reusable steps with include |
| GraphQL Support | Support for GraphQL APIs |

---

See [v2/ideas/FUTURE_IDEAS.md](v2/ideas/FUTURE_IDEAS.md) for detailed specifications.
