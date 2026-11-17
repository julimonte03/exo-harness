# Where the code shows each element

Search, then read the lines that prove it, and cite them. Skip dependency and build folders (`node_modules`, `vendor`, `dist`, `build`, `.venv`, `target`). Never open files that hold secrets (`.env`, keystores, credential files): their names are enough, and the data protection contract (`.exo/shared/data-protection.md`) forbids copying their content.

## Containers

| Signal | Where | What it proves |
|---|---|---|
| A service in a compose file | `compose.yaml`, `docker-compose*.yml` (`services:`) | A runnable unit, its image or build folder, its ports and its dependencies (`depends_on`) |
| A workload manifest | Kubernetes `Deployment`, `StatefulSet`, `CronJob`, `Job`; Helm charts and values; Kustomize overlays | A deployed unit, its replicas, its schedule for jobs |
| A function or app definition | Serverless framework files, cloud function configs, platform files such as `Procfile`, `app.yaml` | A unit run by a platform |
| A build that produces something runnable | `package.json` with `start` or a framework, `pyproject.toml` with an app entry point, `pom.xml` or `build.gradle` with a boot plugin, `go.mod` with a `main` package, a `Dockerfile` | A container and its technology |
| A front end | A web framework build (`vite.config.*`, `next.config.*`, `angular.json`), a mobile project | A client container |
| A scheduled or background worker | Queue consumers, schedulers, `celery`, cron definitions | A separate container when it runs as its own process |

A library or a shared package is not a container. A monorepo folder that only other folders import is a component of each container that uses it.

## Data stores and queues

| Signal | Where |
|---|---|
| Database drivers and ORMs | Dependencies (a PostgreSQL, MySQL, SQL Server, MongoDB or Redis client), ORM configuration, migrations folders |
| Connection settings | The names of environment variables or settings keys (`*_DB_URL`, `DATABASE_URL`, `REDIS_HOST`): cite the name, never the value |
| Message brokers | Producer and consumer code, topic and queue names, broker clients in the dependencies |
| Object storage and caches | Storage SDK calls, bucket names in configuration (cite the setting, not the bucket when it reveals an account) |
| Infrastructure as code | Terraform, Pulumi, CloudFormation, Bicep resources for databases, queues, caches and buckets |

Who owns a store: the container that runs its migrations or writes to it. Two containers writing the same store is worth a note.

## Relations

| Relation | Signal |
|---|---|
| Synchronous HTTP or gRPC | HTTP clients with a base URL setting, generated API clients, gRPC stubs, calls to a gateway |
| Asynchronous | A producer in one container and a consumer of the same topic or queue in another |
| Database access | Repository or ORM code, raw queries |
| Front end to back end | API calls in the client code, proxy configuration of the dev server, the gateway's routes |
| External system | An SDK of a third party, a client whose base URL setting points outside, webhooks received at a route |
| Identity | OAuth or OIDC configuration, an identity provider SDK, token validation middleware |

For each relation, the direction (who starts it), synchronous or asynchronous, the protocol, and what flows, with the line of the call or the subscription.

## People and roles

- Authentication roles and permission names in the code.
- User-facing entry points: web routes, mobile screens, admin consoles, CLI commands.
- The README or the product documentation.

Name roles ("Customer", "Support agent"), never people.

## Components

- The package or folder structure of one container, the modules that the entry point wires together, and the imports between them.
- Group by responsibility (API layer, domain, persistence, integrations), not by file. Five to nine components is enough.
- A dependency between components is an import or an injected interface; cite one import per arrow.

## Deployment

- Infrastructure as code: networks, subnets, security groups or firewall rules, load balancers, gateways, clusters, node pools, regions.
- Deployment manifests: namespaces, ingress rules, services, replicas.
- CI deploy jobs: the target environments and their order.
- Environments by their generic role (production, staging) in a diagram that may leave the team; their real names, account IDs and regions are sanitized before it does.

## Comparing a diagram with the code (drift)

1. Inventory the elements of the existing diagram.
2. For each, find its evidence in the current code.
3. Report: in the diagram and in the code (unchanged), in the diagram only (removed or renamed), in the code only (missing from the diagram), and changed relations or technologies. Cite `path:line` for each.
4. Offer the updated diagram; never overwrite the existing one without the person's approval.
