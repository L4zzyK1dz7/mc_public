# Technical Design Document

**Version:** 1.0
**Author:** Gian Lagasca
**Status:** Draft
**Last Updated:** August 2026

---

## 1. System Overview

> *Provide a 2-3 sentence summary of how the system works technically. Reference the PRD for business goals.*

The Monte Carlo ABM Engine is a local, CLI-based Python application. It ingests YAML/CSV configurations, executes `N` independent agent-based model replications concurrently using Python 3.14t multithreading, and aggregates the results into a unified CSV output.

## 2. High-Level Architecture (The Pipeline)

> *Describe the core flow of data. For this tool, we are using the Scatter-Gather pattern.*

The system executes in three distinct, sequential phases:
1.  **Stage 1 (Single-Threaded):** The `DataLoader` reads and validates the `.yaml` config and starting `.csv` files, instantiating a read-only `ConfigState` object in memory.
2.  **Stage 2 (Multi-Threaded - Scatter):** A `ThreadPoolExecutor` spawns `W` worker threads. Each thread receives a reference to `ConfigState`, builds a unique `AgentUniverse` in isolated memory, and runs the simulation logic. 
3.  **Stage 3 (Single-Threaded - Gather):** The `Aggregator` collects the dictionaries returned by the worker threads and streams them sequentially to `output.csv`.

## 3. Data Schemas & State Management

> *Define the exact structures of your inputs and outputs. This prevents developers from guessing what the data looks like.*

### 3.1 Input Configuration (`config.yaml`)
*   **Target:** `config.yaml`
*   **Structure:**
    *   `replications` (int): Number of Monte Carlo runs.
    *   `ticks` (int): Steps per replication.
    *   `agent_count` (int): Number of initial agents.
    *   `movement_speed` (float): Global parameter for agent traversal.

### 3.2 Output Schema (`output.csv`)
*   **Target:** `results_[timestamp].csv`
*   **Columns:** 
    *   `rep_id` (int)
    *   `total_ticks_survived` (int)
    *   `resources_consumed` (float)
    *   `end_state_code` (string)

## 4. Core Modules & Classes

> *List the main Python classes you plan to write and what they are responsible for.*

*   `ConfigParser`: Responsible for loading YAML and validating types.
*   `Agent`: The base class for entities. Holds local state (`x_pos`, `y_pos`, `health`).
*   `SimulationEnvironment`: Instantiated **once per thread**. Contains the spatial grid and the list of active `Agent` objects.
*   `MonteCarloEngine`: The orchestrator class that sets up the `ThreadPoolExecutor` and maps the replications.

## 5. Concurrency & Threading Model

> *Explicitly define how threads are managed so future developers don't break the isolation.*

*   **Concurrency Engine:** `concurrent.futures.ThreadPoolExecutor`
*   **Python Target:** Python 3.14t (Free-Threaded build).
*   **Memory Isolation Strategy:** The `ConfigState` object is read-only. No thread is permitted to mutate the base configuration. The `SimulationEnvironment` and all `Agent` instances must be instantiated *inside* the worker function to guarantee zero shared state across replications.

## 6. Error Handling & Logging

> *How does the system fail gracefully? If one thread crashes, does the whole program die?*

*   **Validation Errors:** Handled in Stage 1. If the YAML is malformed, the system raises a `ValueError` and exits immediately before spawning threads.
*   **Thread Failures:** Handled in Stage 2. If a specific replication fails (e.g., divide by zero error in agent logic), the thread returns an `ErrorResult` object rather than crashing the thread pool. The `Aggregator` logs the failed `rep_id` and continues writing the successful runs.

## 7. Testing Strategy 
### 7.1 Separation of Concerns (The Humble UI)
The application follows a strictly decoupled architecture separating the Simulation Engine (Backend) from the Streamlit Interface (Frontend). Because UI testing is notoriously brittle and slow, the Streamlit frontend is treated as a "Humble Object." It contains no business logic or math. All logic is pushed down into the Python engine.

### 7.2 In-Scope for Unit Testing (pytest)
Automated testing will strictly target the core Python simulation engine to ensure mathematical accuracy and system stability.

Vector Math & Kinematics: Waypoint arrival calculations, unit vectors, and time-step interpolations.

Event Scheduling: Continuous Collision Detection (CCD) logic predicting when an agent enters a sensor radius.

Data Pipelines: Functions that parse initial state dictionaries and functions that format the final Monte Carlo results into DataFrames/CSVs.

### 7.3 Out-of-Scope for Unit Testing
We will rely on the underlying frameworks' internal validation for the following components:

Streamlit Input Validation: We will not test if sliders or number inputs correctly restrict user inputs.

Plotly Rendering: We will not test if the browser successfully renders the visual traces or animations.

### 7.4 Future End-to-End (E2E) Testing
Once the core simulation is feature-complete, we may implement a lightweight integration test using Streamlit's AppTest framework to simulate a single headless run (e.g., clicking "Run Simulation") purely to verify the app does not throw unhandled exceptions during execution.


## 8. Future Considerations & Extensibility

> *Document the architectural decisions that leave room for future growth, as well as known technical debt.*

*   **Database Integration:** V1.0 relies entirely on local file I/O. However, data loading logic is decoupled via the `DataLoader` class. Future SQL integration will only require rewriting this class without touching the `MonteCarloEngine`.
*   **Validation Limitations:** Currently using custom validation for PyYAML. If config complexity increases, this should be refactored to use `Pydantic` for schema enforcement.

## 9. Related Documents & Architecture Decisions

For the business context and historical technical decisions that shaped this architecture, refer to the following documents:

*   **Business Rules:** [PRD: Monte Carlo ABM Tool v1.0](../01-prd/main-prd.md)
*   **Technical Decisions:**
    *   [ADR-001: Use of Python 3.14t Multithreading](../03-adr/001-use-python-3.14t.md)
    *   [ADR-002: Scatter-Gather Pipeline Pattern](../03-adr/002-scatter-gather-pattern.md)
    *   [ADR-003: PyYAML over SuperYaml](../03-adr/003-pyyaml-over-superyaml.md)