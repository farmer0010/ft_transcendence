# Service Architecture

## Services and their single responsibility

| Service | Responsibility | Talks to |
|---|---|---|
| `backend` | Locker rental/return, auth, coin/store, calendar, admin, scheduling. Publishes domain events; never calls Slack directly. | MariaDB (JPA), Redis (cache, locks, stream producer), `ai` (REST), `notification-service` (indirectly, via Redis Stream) |
| `ai` | Classifies a return photo as empty/occupied. | nothing (stateless inference) |
| `notification-service` | Consumes the Slack alarm stream and sends the actual Slack DM. The only service allowed to call the Slack API. | Redis (stream consumer), Slack API |
| `nginx` | Reverse proxy / routing for the public-facing API and FE. | `backend` |
| `fe` | Web client. | `nginx` |

`backend` and `notification-service` do not call each other directly over REST — they are decoupled through Redis Streams. This was a deliberate choice over a synchronous REST call: a Slack outage or rate limit should never block a rental/return request, and the backend already used an async, transactional-outbox-like pattern (`AlarmEventHandler`) for this before the split.

## Why notification-service exists

Before this split, Slack alarm consumption (`SlackAlarmStreamListener` + `SlackBotService`) ran inside the same JVM as the rest of the backend. It has nothing to do with locker/rental logic, has its own external dependency (the Slack API) and its own failure mode, and can be deployed/restarted independently of the backend. Splitting it out is the "microservices backend" module for this project.

The **logtime-sync stream** (`LogtimeStreamListener`) was *not* moved — it directly touches domain services (`UserUseCase`, `ItemRepositoryPort`) and belongs with the rest of the backend's business logic. Only the Slack-specific consumer was extracted.

## Event flow: rental/return/overdue alarm -> Slack DM

```mermaid
sequenceDiagram
    participant Domain as backend domain/scheduler code
    participant Handler as backend: AlarmEventHandler
    participant Stream as Redis Stream: slack-alarm-stream
    participant Listener as notification-service: SlackAlarmStreamListener
    participant Slack as Slack API

    Domain->>Domain: business transaction (e.g. mark overdue, admin notice)
    Domain->>Handler: ApplicationEventPublisher.publishEvent(AlarmEvent)
    Note over Domain,Handler: AlarmEventHandler is @TransactionalEventListener(AFTER_COMMIT) -<br/>only fires once the surrounding transaction actually commits
    Handler->>Stream: XADD slack-alarm-stream {intraId, email?, message}
    Listener->>Stream: XREADGROUP (consumer group: cabinet-backend-group)
    Listener->>Listener: dedup check (SETNX notification:processed:<record-id>)
    alt not seen before
        Listener->>Slack: chat.postMessage (DM)
    else already processed (redelivery)
        Listener->>Listener: skip send
    end
    Listener->>Stream: XACK + XDEL
```

### Producers of `AlarmEvent`

Both still live in the backend and are unchanged by the split:

- `LentScheduler` (overdue / imminent-return / auto-extension-disabled alarms) — publishes from inside `@Transactional` scheduled jobs.
- `AdminAlarmService.sendEmergencyNotice` (via `SlackAlarmAdapter`, which implements the `AlarmPort` domain port) — this method is now `@Transactional(readOnly = true)` specifically so the `AFTER_COMMIT` event listener actually fires (it previously called `SlackBotService` synchronously with no transaction boundary at all, which worked by accident; publishing-based delivery requires a real transaction to commit).

### Redis Stream record schema (`slack-alarm-stream`)

Written by `AlarmEventHandler` (backend), read by `SlackAlarmStreamListener` (notification-service):

| Field | Type | Required | Notes |
|---|---|---|---|
| `intraId` | string | yes | Used as the Slack DM target (looked up via `slack_users.csv` or the Slack `users.list` API) |
| `email` | string | no | Carried for completeness; not currently used by the consumer |
| `message` | string | yes | Final DM text, already formatted by the producer |

Consumer group: `cabinet-backend-group` (unchanged name, so any pending/unacked entries from before the split are still visible to the new service). Delivery semantics: at-least-once (standard Redis Stream consumer group behavior — a crash between `XREADGROUP` and `XACK` leaves the entry pending and it gets redelivered). The consumer deduplicates redeliveries using a `SETIFABSENT` guard key (`notification:processed:<stream-record-id>`, 24h TTL) before actually calling Slack, so a redelivered message is acknowledged/deleted but not re-sent.

## Hexagonal boundaries

The backend's existing ports/adapters structure is preserved: `AlarmPort` (domain port, `com.gyeongsan.cabinet.domain.alarm.port.out`) is still implemented by `SlackAlarmAdapter` (`adapter/out/external/slack`) — only the adapter's internals changed (it publishes an event instead of calling a service method directly). Domain code (`AdminAlarmService`) has zero knowledge that Slack delivery moved to another process.

notification-service is intentionally not structured as a hexagonal app — it is a thin, single-purpose consumer (read a stream, call one external API) where that structure would add indirection without a corresponding benefit.
