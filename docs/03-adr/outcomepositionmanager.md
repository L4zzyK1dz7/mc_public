# OutcomePositionManager

## Purpose

`OutcomePositionManager` records platform position snapshots during one Monte Carlo replication. It gives the simulation a consistent event history that can later be converted into `raw_positions.csv` and used by the animation.

The manager records state; it does not control state.

- `MovementManager` generates waypoints and moves platforms.
- The detection pipeline determines whether a detection occurred.
- The simulation orchestrator decides when a snapshot should be captured.
- `OutcomePositionManager` stores snapshots.
- The output layer converts snapshots into CSV columns and units.

## Replication scope

A new manager is created for every replication:

```mermaid
flowchart LR
    R[Monte Carlo run] --> R1[Replication 1]
    R --> R2[Replication 2]
    R --> RN[Replication N]

    R1 --> M1[OutcomePositionManager 1]
    R2 --> M2[OutcomePositionManager 2]
    RN --> MN[OutcomePositionManager N]

    M1 --> E1[Events for replication 1]
    M2 --> E2[Events for replication 2]
    MN --> EN[Events for replication N]
```

This prevents events from different replications being mixed. It also means the manager can start empty and be discarded after its replication result has been created.

## Events recorded

The manager captures four types of `PlatformPositionEvent`:

| Event | When it is recorded | Platforms recorded |
|---|---|---|
| `initial_position` | After platform states and their first waypoints are created | All platforms |
| `waypoint_generated` | After a new waypoint has been assigned to a platform | The platform receiving the waypoint |
| `detection` | When the detection pipeline reports a detection | The detecting platform |
| `time_limit` | When the simulation reaches its time limit | All platforms |

Each event contains a snapshot of the platform's position, current waypoint, heading, speed, team, status, timestamp, and optional detection metadata.

The snapshot contains scalar values rather than a reference to the mutable `PlatformState`. Later movement therefore cannot change an event that has already been recorded.

## Event lifecycle

```mermaid
flowchart TD
    A[Start replication] --> B[Initialise PlatformState objects]
    B --> C[Record initial_position for every platform]

    C --> D[Run timestep]
    D --> E[MovementManager updates platforms]

    E --> F{New waypoint generated?}
    F -->|Yes| G[Orchestrator records waypoint_generated]
    F -->|No| H[Continue]
    G --> H

    H --> I[Detection pipeline]
    I --> J{Detection reported?}
    J -->|Yes| K[Orchestrator records detection]
    J -->|No| L[Continue]
    K --> L

    L --> M{Time limit reached?}
    M -->|No| D
    M -->|Yes| N[Record time_limit for every platform]
    N --> O[Return events in SimulationResult]
```

## Ordering rule

Record a snapshot after the relevant state change:

```mermaid
sequenceDiagram
    participant MM as MovementManager
    participant PS as PlatformState
    participant S as Simulation orchestrator
    participant OP as OutcomePositionManager

    MM->>MM: Generate new waypoint
    MM->>MM: Calculate waypoint properties
    MM->>PS: Update current waypoint
    MM-->>S: Return platform with new waypoint
    S->>OP: Record waypoint_generated snapshot
    MM->>PS: Move platform
```

This ensures a `waypoint_generated` event contains the new waypoint, not the previous one. The platform position is the position at which the new waypoint was assigned.

## Responsibilities and coupling

`MovementManager` must remain independent of output code. It must not import or call `OutcomePositionManager`, write CSV files, or construct output events. Instead, it returns movement facts to the orchestrator, such as which platforms received new waypoints.

```mermaid
flowchart LR
    MM[MovementManager] -->|updates| PS[PlatformState]
    MM -->|returns movement facts| S[Simulation orchestrator]
    DP[Detection pipeline] -->|returns detection facts| S
    S -->|passes state snapshots| OP[OutcomePositionManager]
    OP -->|PlatformPositionEvent list| SR[SimulationResult]
    SR --> OUT[Output layer]
    OUT --> CSV[raw_positions.csv]
    CSV --> ANI[Animation]
```

The manager is therefore an output-side collector, not part of the movement or detection domain logic.

## Output flow

Events use internal SI units:

- positions and waypoints: metres;
- speed: metres per second;
- timestamp: seconds.

`OutcomePositionManager` does not convert units. The output layer performs these conversions when creating `raw_positions.csv`:

```mermaid
flowchart LR
    A[PlatformPositionEvent list] --> B[build_positions_df]
    B --> C[Metres to kilometres]
    B --> D[Seconds to minutes]
    B --> E[Metres per second to kilometres per hour]
    C --> F[raw_positions.csv]
    D --> F
    E --> F
    F --> G[animation_archive.py]
```

The event type is retained internally so the reason for each row is known. CSV formatting may omit that field when maintaining the existing file format.

## Current integration boundary

The initial position, waypoint-generated, and time-limit events are recorded by the simulation orchestrator. Detection events should be recorded when the detection pipeline exposes a result containing:

- detecting platform;
- target platform;
- sensor name;
- detection distance;
- detection timestamp.

Until that interface exists, the manager supports detection events but the simulation cannot populate them automatically.
