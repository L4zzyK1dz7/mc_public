# Monte Carlo Simulation Test Plan

This document outlines the comprehensive testing strategy for the Monte Carlo simulation engine. It is intended to guide test-driven development (TDD) efforts to ensure robustness, accuracy, and adherence to the 80%+ coverage requirement.

For the granular tabular test matrix mapping directly to these suites, see [test_plan_matrix.md](test_plan_matrix.md).


## 1. Schema & Configuration Validation
**Goal**: Verify that all inputs defined in YAML config files are correctly parsed and validated.
* **Platform Configurations**:
  * Test team enum assignments (Blue/Red).
  * Verify kinematics (e.g., speed > 0 validation).
  * Test behaviour fallback configurations (e.g., 'stop' on neutralised).
* **Movement Configurations**:
  * Verify schema defaults for `RandomWalkMovement`, `IntruderSearchMovement`, etc.
  * Verify `UserDefinedWaypointsMovement` requires valid coordinate lists.
* **Sensor Configurations**:
  * Test validation logic for generic sensors (FOV limits: 0-360).
  * Validate $K$-of-$N$ parameters ($K \le N$, $N > 0$).
  * Test interpolation data structure sizes.
* **Simulation & World Schema**:
  * Test simulation constraints (e.g., replications > 0, timesteps > 0).
  * Verify world limits (length, width) validation.

## 2. Core State Management
**Goal**: Test that mutable states update predictably based on simulation flow.
* **Platform State (`PlatformState`)**:
  * Verify blueprint mappings properly instantiate platform kinematics.
  * Test `advance_step()` cleanly delegates to the movement strategy without corrupting runtime states.
* **Movement State (`MovementState`)**:
  * Test distance remaining tracking and threshold behaviours.
  * Verify that reaching a waypoint correctly updates the heading and remaining distance for the next leg.
* **Sensor Runtime State (`SensorRuntimeState`)**:
  * Test sliding window bounds enforcement (`Deque` maxlen limits).
  * Verify independent tracking of multiple targets per sensor instance.

## 3. Movement Strategies
**Goal**: Validate the polymorphic strategy implementations for generating waypoints.
* **Random Walk**:
  * Verify bounds enforcement (does not assign waypoints outside world dimensions).
  * Check deterministic generation based on the RNG seed.
* **User Defined Waypoints**:
  * Test traversal through a fixed list.
  * Test behaviour upon exhausting the list (e.g., looping vs. stopping).
* **Search / Patrol Patterns**:
  * Verify algorithms calculate the appropriate geometric nodes.

## 4. Detection Pipeline
**Goal**: Validate exhaustive and stochastic target detection. *(Note: Primarily complete)*
* **Generic Sensors**:
  * Confirm interval time gating blocks premature execution.
  * Verify relative Field of View (FOV) logic, including 360-degree wraparound.
  * Test PoD lookup (distance-based linear interpolation).
  * Verify $K$-of-$N$ cumulative success logic across sequential ticks.
  * Ensure exhaustive target resolution (finding one target doesn't short-circuit evaluating others).
* **Pipeline Orchestration**:
  * Confirm `iter_platform_sensors` yields accurate detecting/target pairs.
  * Verify registry pattern smoothly handles missing strategies.

## 5. End Conditions & Rule Resolution
**Goal**: Validate that simulation replications terminate accurately and logically.
* **Time Limits**:
  * Ensure replication halts precisely when $step \ge max\_steps$.
* **Boundary Escapes**:
  * Verify detection of targets physically escaping the `World` limits.
* **Detection Criteria**:
  * **Initial Detection**: Verify the simulation flags completion immediately on the first reported detection event.
  * **Team Detection**: Verify simulation terminates only when *all* platforms of a designated team have been detected.
* **Condition Priority**:
  * Test ties (e.g., target escapes at the same tick time limit is reached) to ensure deterministic priorities.

## 6. Monte Carlo Orchestration & Integration
**Goal**: Validate the core execution loop and concurrency patterns.
* **Single Replication Loop (`_execute_single_replication`)**:
  * Test deterministic output based on a known seed.
  * Verify the order of operations (move -> detect -> evaluate end condition -> snapshot).
* **Seed Generation & Propagation**:
  * Confirm that a master seed properly spawns deterministic sub-seeds for concurrent replications.
  * Test recovery behaviour when providing an explicit `seeds.txt` configuration.
* **Aggregation**:
  * Verify that multiple replication results (lists of dicts) aggregate into expected data structures without data loss.

## 7. Output Management & Analytics
**Goal**: Ensure snapshots represent identical moments in time accurately.
* **Position Snapshot Manager**:
  * Validate that standard steps log positional events.
  * Verify that an instantaneous detection logs a snapshot of *all* platforms precisely aligned to that time.
* **Detection Manager**:
  * Check storage payload of detection artefacts (sensors, ranges, IDs).
* **CSV/JSON Generation**:
  * Test output serialisation for analytical consumption.

## Summary Checklist
- [x] Schema unit tests (~15 test cases - Complete)
- [x] Core state management tests (~9 test cases - Complete)
- [x] Movement strategy unit tests (~6 test cases - Complete)
- [x] Detection pipeline logic (9 test cases - Complete)
- [x] End Condition unit tests (~5 test cases - Complete)
- [x] Orchestrator integration tests (~6 test cases - Complete)
- [x] IO / Output Manager tests (~6 test cases - Complete)
