# Fault catalog

Faults by layer, from the smallest to the widest, with common ways to inject them and how to stop them. Every inject and stop command here changes a system: propose it, check the stop first, and run it only with the go-ahead (`SKILL.md`, Safety rules). Use only tools the project or platform already has.

## Tools you may find

| Tool | Where | Notes |
|---|---|---|
| Chaos Mesh, LitmusChaos | Kubernetes | Faults as resources; deleting the resource stops the fault |
| Service mesh fault injection (Istio, Linkerd, Envoy) | Kubernetes with a mesh | Delays and errors per route and percentage of traffic |
| AWS Fault Injection Service, Azure Chaos Studio | Cloud | Managed experiments with stop conditions tied to alarms |
| Toxiproxy | Any, as a proxy in front of a dependency | Latency, timeouts, bandwidth limits, cut connections |
| Pumba | Docker | Kill, pause, network faults on containers |
| tc with netem | Linux hosts and containers with the right privileges | Latency, loss, corruption on an interface |
| Commercial platforms | Any | Use them only if the organization already has them |

Without any of them, manual injection works for first experiments: stop a process, scale a deployment down, block a port in a test environment.

## Instances and processes

| Fault | Inject (example) | Stop | Tests |
|---|---|---|---|
| Lose one pod | `kubectl delete pod <pod> -n <namespace>` | The controller recreates it; nothing to undo | Load balancing, readiness probes, in-flight request handling |
| Fewer replicas | `kubectl scale deploy/<name> -n <namespace> --replicas=<n>` | Scale back to the noted original | Capacity margin, autoscaling |
| Stop a container | `docker stop <container>` | `docker start <container>` | Restart policies, client reconnection |
| Pause a process (hang, not crash) | `docker pause <container>` | `docker unpause <container>` | Timeouts and health checks for a hung dependency |

Note the original replica count and configuration before any change; the stop restores exactly that.

## Network

| Fault | Inject (example) | Stop | Tests |
|---|---|---|---|
| Added latency | `tc qdisc add dev <iface> root netem delay 200ms 50ms` | `tc qdisc del dev <iface> root netem` | Timeouts, latency budgets, user-facing p99 |
| Packet loss | `tc qdisc add dev <iface> root netem loss 5%` | `tc qdisc del dev <iface> root netem` | Retries, idempotency |
| Latency to one dependency | Toxiproxy: add a `latency` toxic to the dependency's proxy | Remove the toxic | Timeouts and fallbacks per dependency |
| Errors on a route for part of the traffic | Mesh fault injection: abort 10% with HTTP 503 | Restore the previous route configuration | Retries, circuit breakers, error handling in callers |
| Dependency unreachable | Firewall or network policy denying the dependency's port, in a test environment | Remove the rule or policy | Fallbacks, graceful degradation, alerting |

`tc` acts on a whole interface: in a shared host it affects everything on it. Prefer per-dependency tools (a proxy, the mesh) where possible.

Mesh example (Istio), delaying 10% of requests to one service by 2 seconds:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: ratings
spec:
  hosts: ["ratings"]
  http:
    - fault:
        delay:
          percentage: { value: 10 }
          fixedDelay: 2s
      route:
        - destination: { host: ratings }
```

Save the current VirtualService before applying this one; the stop is applying the saved version again.

## Dependencies

| Fault | How | Tests |
|---|---|---|
| A dependency slow | Proxy latency, or a stub that sleeps | Timeouts shorter than the caller's own deadline; thread pools not exhausted |
| A dependency failing | Stop it in a test environment, or a stub returning errors | Fallbacks, cached responses, feature degradation, error messages |
| A dependency returning bad data | A stub with malformed or unexpected responses | Validation at the boundary |
| A database failover | The managed service's documented failover test, or promoting a replica in a test environment | Reconnection, write retries, the length of the write outage |
| A queue unavailable | Stop the broker in a test environment | Producers buffering or failing safely; consumers resuming |

## Resources

| Fault | Inject (example) | Stop | Tests |
|---|---|---|---|
| CPU pressure | A CPU stress tool already present, with a timeout | It ends with its timeout; kill it otherwise | Autoscaling, latency under contention |
| Memory pressure | A memory stress tool already present, with a limit and a timeout | Its timeout | Memory limits, out-of-memory behavior, restarts |
| Disk filling | `fallocate -l <size> <test-path>/chaos-fill` on a test volume | Delete that one file | Alerts on disk, log rotation, behavior when writes fail |
| File descriptors or connections exhausted | A test client that opens and holds connections | Stop the client | Pool limits, error handling |

Always set a timeout or a size limit on resource faults, so they end even if the stop is forgotten.

## Configuration and time

| Fault | How | Tests |
|---|---|---|
| Expired or wrong certificate | A test environment with a certificate about to expire | Alerting before expiry; error messages |
| Revoked credentials | Rotate a test credential without updating the client | Detection, error handling, the rotation runbook |
| A bad configuration rollout | Ship a deliberately wrong value to a canary in a test environment | Canary analysis, automatic rollback |
| Clock skew | Only in an isolated environment | Token validation, scheduling, ordering |

## Zones and regions

| Fault | How | Tests |
|---|---|---|
| Lose a zone | Drain or cordon the nodes of one zone in a test cluster; or the cloud's zone-failure experiment | Capacity across zones, stateful failover |
| Regional failover | A planned drill following the documented failover procedure | Data replication lag, DNS or traffic switch time, the runbook |

Zone and region drills in production are planned events: service owner approval, a change window, the people on call ready, and the failover runbook rehearsed in non-production first.

## Never

- Faults that delete or corrupt data someone needs.
- Faults on systems of other teams or third parties without their owners' agreement.
- Faults whose stop has not been checked.
- A second fault added during a run.
