# Logical-clock Snowflake IDs

SynCode replaces the MyBatis-Plus default `ASSIGN_ID` generator in deployed Java services with a logical-clock Snowflake generator.

## ID layout

The signed `BIGINT` stays positive and uses the following 63 bits:

| Field | Bits | Meaning |
| --- | ---: | --- |
| Logical timestamp | 41 | Milliseconds since the MyBatis-Plus compatibility epoch (`2010-11-04T01:42:54.657Z`) |
| Worker ID | 10 | Explicit Java process identity, range `0..1023` |
| Sequence | 12 | Per-logical-millisecond sequence, range `0..4095` |

The numeric value is trend-increasing. Under one worker it is strictly increasing, so normal inserts remain concentrated near the right edge of the InnoDB clustered primary-key index.

Keeping the existing MyBatis-Plus epoch is intentional: changing the epoch during migration would make new numeric IDs smaller than existing rows and would lose the right-edge insertion property.

## Clock rollback handling

For each ID, the generator uses the larger of the physical clock and the previous logical timestamp. A backward system-clock adjustment therefore keeps the logical timestamp unchanged and continues through the 12-bit sequence. When that sequence is exhausted, the logical timestamp advances by one millisecond without waiting for the physical clock.

This behavior avoids the default generator's rollback exception and prevents an in-process clock rollback from reusing a timestamp/sequence pair.

## Crash and restart handling

The generator persists a future high watermark before issuing IDs from a logical-time range. The default reservation is 10 seconds. Calls inside the reserved range use memory only; crossing the watermark atomically reserves the next range and forces the state file to disk.

After a restart, the generator begins after the persisted high watermark, even when the physical clock is behind it. This preallocation matters because periodically saving only the last used timestamp can replay IDs generated after the most recent save when a process crashes.

Each state file has a process lock. Two JVMs cannot intentionally share the same worker ID and state path at the same time.

## Deployment rules

- Every concurrently running ID-producing JVM must have a distinct `SYNCODE_ID_LOGICAL_CLOCK_WORKER_ID`.
- `SYNCODE_ID_LOGICAL_CLOCK_STATE_FILE` must reside on durable storage.
- Docker Swarm definitions mount a separate named volume for every Java business service.
- A worker ID must not be reused with an empty state volume while the physical clock may still be behind that worker's last logical timestamp.
- State volumes must be included in backup and migration procedures when services move between hosts.

The feature is opt-in outside the deployment definitions. Local processes continue using the MyBatis-Plus default unless `SYNCODE_ID_LOGICAL_CLOCK_ENABLED=true` and a worker ID are provided.
