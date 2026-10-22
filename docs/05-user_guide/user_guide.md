## MAKO: Monte-Carlo Agent Kinematic Observation Tool 
---

## 1. Welcome to MAKO

Named after the fastest, most agile predator in the ocean, **MAKO** is engineered for rapid prototyping, surveillance, and detection scenarios. **Kinematic** for agent movement and **Observation** for sensor sweeps to find and hunt their prey.  

![MAKO Shark](images/shark.png)

### YU-GI-OH Dual Monster Reference
MAKO is also a character in the Yu-Gi-Oh Dual Monsters card game first appeared in episode 7 who uses purely water monsters in his deck.

![MAKO](images/mako.png)

### 1.1 What Problem Does MAKO Solve?
Physically testing search patterns and sensor configurations at sea is expensive and time-consuming. MAKO allows users to analayse how sensors are performing with a given platform in a scenario. It's best used to rapidly prototype different force-mixes against a known target threat. 

MAKO solves this by letting you rapidly construct multi-agent scenarios:
* **Hunters/Detectors (Blue Team)**: Surface patrol vessels, maritime patrol aircraft, autonomous platforms, onboard directional sonars/radars sensors, and deployed multistatic sonobuoy fields.
* **Targets/Intruders/Counter-Detectors (Red Team)**: Submarines or intruder vessels attempting to transit an area. With counter detection capabilities. *Counter detection is defined as red detecting blue without blue neededing to detect red initially*.

By simulating hundreds or thousands of randomised runs (known as **Monte Carlo replications**), MAKO aggregates the results. Instead of wondering *"Will my patrol ship detect the submarine?"*, MAKO reveals: *"Across N randomised encounters, your patrol ship has a X% probability of detecting the submarine within T hours."*

---

## 2. Before You Begin: Core Assumptions & Conventions

### 2.1 The Simulation World is a 2D Plane
MAKO is simulated in a two-dimensional Cartesian plane ($X$ and $Y$ measured in kilometres). 
* **What is modelled**: Platform speeds in mps, courses as headings in degrees, waypoints, and horizontal ranges.
* **What is not modelled**: Ocean bathymetry, water column depth layers (thermoclines), 3D diving depth, and bottom reverberation. Post detection manoeuvres.

### 2.2 Empirical Probability of Detection (PoD)
Sensors in MAKO do not compute raw acoustic wave propagation or radar cross-section physics from scratch. Instead, they evaluate detection using empirical **Probability of Detection (PoD)** lookup curves taken from other predictive models:
* **Generic Sensors (Range-Based)**: At each simulation timestep, MAKO calculates the straight-line distance between the detector and the target and evaluates whether the target falls within the sensor's FOV. It uses the sensor's performance table (`distance_m` vs `pod`) to evaluate PoD and rolls against a $k$-of-$n$ sliding window.
* **Specific Sensors (Trail Crossing)**: Models platforms detecting opponents when their current step segment crosses a historical trail segment of an opposing target. Its performance table defines `time_late_hours` vs `pod`, judging the detection probability by the age of the crossed trail segment. If an intersection occurs, an independent $k$-of-$n$ trial is rolled for that crossing. To guarantee continuous path coverage without gaps, specific sensors require `interval_time_sec` to match the global simulation `timestep_sec`.

### 2.3 Hunter and Target Balance
You must define **at least one Red platform** (Target/Intruder) and **at least one Blue platform** (Hunter/Detector) before MAKO will allow you to run the Monte-Carlo.

### 2.4 Multistatic Sonobuoy Requirements
MAKO supports MultiStatic Active (MSA) sonobuoy fields (where passive receivers listen for echoes produced by an active source from a sensor). For a sonobuoy field to record detections, **at least one Blue platform must carry an active acoustic source (pinger)**.

### 2.5 The Two-Step Launch Sequence
To ensure configuration integrity, MAKO web page  requires the user to:
1. **Create Config YAML**: Compiles your visual settings into a validated scenario file. Also generates the sensor CSV files for the platforms sensor performance data and attributes. *YAML file is a structured JSON file*
2. **Run Simulation**: Executes the Monte Carlo engine.

### 2.6 Seed Reproducibility
* **Use Seeds File (Ticked)**: Produces deterministic, perfectly repeatable results. Ideal for controlled experiments and side-by-side tactical comparisons.
* **Use Seeds File (Unticked)**: Generates purely stochastic random variations each time you click Run.


---

## 3. Sensor Field of View (FOV) & Angle Conventions

One of the most common pitfalls for maritime planners using computer simulations is the difference between **Navigational Compass Bearings** and **Mathematical/Python Angles**.


### 3.1 The Difference at a Glance

| Feature | Navigational / Maritime Convention | MAKO / Python Cartesian Convention |
| :--- | :--- | :--- |
| **Zero Reference ($0^\circ$)** | **True North** | **East** in world frame; or **Platform Heading** |
| **Direction of Sweep** | **Clockwise** | **Counter-Clockwise** |
| **$090^\circ$ Direction** | **East** | **North** |
| **$180^\circ$ Direction** | **South** | **West** |
| **$270^\circ$ Direction** | **West** | **South** |

### 3.2 How MAKO Computes Sensor Arcs
In MAKO, every platform moves along a heading vector determined by its current course/leg. Generic sensors mounted on platforms have two key angle properties:
* `FOV Start (deg)`: The beginning of the sensor's arc (relative to the platform heading).
* `FOV End (deg)`: The end of the sensor's arc (relative to the platform heading).

```
                         90° (Port Beam)
                               ^
                               |
       180° (Aft / Stern) <--- Platform ---> 0° (Bow / Direction of Travel)
                               |
                               v
                        270° (Starboard Beam)
```

In MAKO:
1. **$0^\circ$ aligns with the platform's forward direction of travel (the bow)**.
2. The angle sweeps **counter-clockwise**:
   * **$0^\circ$ to $90^\circ$**: Covers the forward-port quadrant.
   * **$90^\circ$ to $180^\circ$**: Covers the aft-port quadrant.
   * **$180^\circ$ to $270^\circ$**: Covers the aft-starboard quadrant.
   * **$270^\circ$ to $360^\circ$**: Covers the forward-starboard quadrant.
3. **Omnidirectional Coverage**: Setting `FOV Start = 0` and `FOV End = 360` creates a complete $360^\circ$ circular coverage envelope around the platform.
4. **Forward Sector Example**: To simulate a forward-looking bow sonar spanning $45^\circ$ to port and $45^\circ$ to starboard:
   * Set `FOV Start = 315.0` (starboard bow)
   * Set `FOV End = 45.0` (port bow)
   * Because $315^\circ > 45^\circ$, MAKO automatically wraps the field of view through $0^\circ$ (dead ahead).

> [!TIP]
> **Rule of Thumb**: If you are thinking in compass bearings, remember that MAKO sweeps to the left (counter-clockwise), whereas your bridge compass sweeps to the right (clockwise). Always double-check your sensor start and end angles!

### 3.3 Sensor Interval Time & The Global Timestep

Sensors in naval warfare do not all evaluate the environment at the same rate:
* **Passive Sonars & ESM**: Often operate continuously or evaluate integration windows over very short cycles (e.g. every `1.0` or `2.0` seconds).
* **Active Sonars**: Rely on distinct pulse repetition intervals (pings) with listening periods that account for two-way acoustic travel time over long distances (e.g. pinging every `30.0` or `60.0` seconds).
* **Surveillance Radars**: May complete a full $360^\circ$ mast rotation every `2.0` to `4.0` seconds.

In MAKO, each sensor defines an `Interval Time (sec)` specifying how often it evaluates contacts. However, because MAKO advances the world in discrete clock ticks governed by the global **Time Step (seconds)** in the sidebar, these timing parameters must be algined.

#### The Risk of Missed Sensor Looks
At each simulation tick/time-step ($t, t + \Delta t, t + 2\Delta t, \dots$), MAKO checks whether the current simulation time has reached a sensor's next scheduled evaluation time. 
* If the global timestep is **larger** than the sensor's interval (e.g. global `Time Step = 5.0 s` while a passive sonar has `Interval Time = 1.0 s`), the sensor will only ever be checked every 5 seconds. **Four out of five sensor looks are completely missed!**
* Furthermore, missed evaluations directly degrade your $k$-of-$n$ sliding window performance, as targets may pass through the sensor's detection window before sufficient hits (True/False) can be recorded.

#### The Golden Rule: The Lowest Common Denominator
When a scenario features multiple sensors with different operational cycles, you must configure the global **Time Step (seconds)** in the sidebar to be a **common divisor (lowest common denominator)** of all sensor interval times.

| Platform Sensor Suite | Individual Sensor Intervals | Recommended Global Timestep | Why? |
| :--- | :--- | :--- | :--- |
| **Passive Sonar only** | `1.0 s` | `1.0 s` | Matches the sensor evaluation rate exactly. |
| **Active Sonar only** | `30.0 s` | `5.0 s` or `10.0 s` | Divides evenly into 30 seconds; also captures smooth platform motion. |
| **Mixed: Passive + Active Sonar** | Passive: `2.0 s`, Active: `5.0 s` | `1.0 s` | $1.0\text{ s}$ divides evenly into both $2.0\text{ s}$ and $5.0\text{ s}$, ensuring no evaluations are skipped. |
| **Mixed: Radar + Sonobuoy Field** | Radar: `3.0 s`, Sonobuoy: `10.0 s` | `1.0 s` | Prevents timing drift between radar sweeps and sonobuoy processing cycles. |

> [!IMPORTANT]
> **Simulation Fidelity vs. Speed**: 
> A smaller global timestep (such as `1.0 s` or `0.5 s`) ensures maximum sensor accuracy and prevents skipped detections. However, smaller timesteps require more calculations per replication. For rapid high-level exploratory runs, keep sensor intervals clean multiples of each other (e.g. `2.0 s`, `4.0 s`, and `10.0 s`) so you can comfortably set the global timestep to `2.0 s`.

---

## 4. Tour of the MAKO User Interface

MAKO's interface is organised into clear, purposeful sections accessible from the navigation menu:

```
[Sidebar Settings]  -->  [1. Create Platforms]  -->  [2. Create Sonobuoys]  -->  [3. Run Simulation]  -->  [4. View Results]
```

### 4.1 The Sidebar: Global Environment & Mission Bounds
The sidebar controls global scenario bounds and simulation run lengths:


* **World Parameters**:
  * `Origin X / Origin Y (km)`: The bottom-left reference corner of the operating area (usually set to `0, 0`).
  * `Length / Height (km)`: The horizontal and vertical boundaries of the maritime theatre (e.g. $100 \times 100\text{ km}$).
* **Simulation Parameters**:
  * `Number of Simulations`: How many independent replications to run (e.g. `1000`). Higher counts produce smoother, more statistically robust probability curves.
  * `Time Limit (hours)`: The maximum mission duration before an un-detected target is marked as "Timed Out".
  * `Time Step (seconds)`: How often platform positions are recalculated (typically `1.0` second).
  * `Detection End Condition`:
    * `initial_detection`: Stops the current replication the instant any hunter makes a confirmed contact.
    * `team_detection`: Continues running until cooperative team-level detection criteria are fulfilled.
  * `Use Seeds File`: Ensures repeatability across experimental comparisons. *Leave it as ticked for now* 

---

### 4.2 Create Platforms (Blue and Red Teams)
This page is where you build the mobile assets in your force.


1. **Identity**:
   * `Display Name`: A distinctive label 
   * `Team`: Assign **Blue** or **Red**.
2. **Kinematics**:
   * `Speed (m/s)`: Continuous operating speed ($1\text{ knot} \approx 0.514\text{ m/s}$).
3. **Movement Patterns**:
   * **Random Walk**: The platform patrols randomly within boundary limits, suitable for general search patterns.
   * **Barrier Search**: The platform patrols back and forth in a straight line, ideal for blocking an intruding entity.
   * **Intruder Search**: Ideal for an infiltrating target entering from an operational boundary and transiting towards an objective.
   * **User Defined Waypoints**: Specify exact coordinate waypoints ($X, Y$ in km) that the platform must navigate sequentially.
4. **Onboard Sensors**:
   * Add one or more sensors to your platform.
   * **Sensor Types**: `Generic` (with configurable FOV arcs) or `Specific` (trail segment crossing).
   * **Detection Threshold ($k$-of-$n$)**: Requires $k$ positive detection rolls out of the last $n$ consecutive time intervals to confirm a valid track, preventing single-ping false alarms.
   * **Active Source**: Blue vessels can be designated as active acoustic emitters to illuminate targets for passive sonobuoy fields.
5. **Neutralised Platform Behaviour**:
   * Applies only when `Detection End Condition` is set to `team_detection` (under `initial_detection` the simulation ends on first contact).
   * **Stop**: Upon detection by opposition sensors or sonobuoys, the platform halts at its terminal position (effective speed becomes $0\text{ m/s}$). It is excluded from further opposition targeting and cannot be detected again.
   * **Continue**: The platform continues traversing its route at full speed, but is counted as detected and cannot be detected again by opposing sensors or sonobuoys.
   * **Sensor Continuity**: In both `Stop` and `Continue` modes, a neutralised platform's own fitted sensors remain active and can continue detecting opposing platforms.

* **Configured Platforms Overview & Deletion**: Located at the top of the Create Platforms page, the **Configured Platforms** table provides a consolidated view of all created platforms (Name, Team, Speed, Movement type, and attached Sensors). To remove a platform draft, select its name from the dropdown list and click **Delete Platform**.

---

### 4.3 Create Sonobuoys (Stationary Sensor Fields)
Sonobuoys are stationary passive receivers deployed across an area to form barrier lines or screening fields.


* **Coordinates ($X, Y\text{ km}$)**: Position each buoy at tactical choke points or barrier lines.
* **Detection Criteria ($k$-of-$n$)**: Set track confirmation criteria per buoy.
* **Evaluation Modes**: Choose between 3 types of evaluation modes. 1. Single sonobuoy detection. 2. Multi sonobuoy detection (data fusion). 3. Single ping sonobuoy detection (multiple buoys can detect the same target in a single ping).  
* **Field-Level Data Fusion**: Set how many distinct sonobuoys must detect a target simultaneously before a team-level alert is declared.

---

### 4.4 Run Simulation
The Home page monitors scenario readiness and controls execution.


* **Status Card**:
  * 🔴 **Red (No Platforms / Unready)**: Alerts you if no platforms exist.
  * 🟡 **Amber (Partially Ready)**: Shows that platforms exist, but you are still missing either a Red or a Blue platform.
  * 🟢 **Green (Simulation Ready)**: Confirms you have at least one Red and one Blue platform ready.
* **Scenario Overview Tables**: Below the status card, read-only summary tables display all currently configured **Platforms** and **Sonobuoys** with their key parameters and sensors.
* **Step 1: "Create Config YAML"**: Click this to validate and bundle all settings into `input_data/config.yaml`. A green confirmation notification will appear.
* **Step 2: "Run Simulation"**: Click this to execute the Monte Carlo run. A real-time replication progress bar (`Replication X of N`) updates after each replication and stays visible upon completion alongside a success message.

---

### 4.5 Results (Analytics & Playback)
Once a run completes, navigate to **Results** to explore your findings across four dedicated tabs:

#### 1. Detection Analytics Tab (Look Here First!)
This is the primary dashboard to view the performance:


* **Top Metric Cards**:
  * **Total Replications**: Number of scenarios completed.
  * **Fleet Detection Prob ($P_{\text{det}}$)**: The overall percentage of replications in which the detectors successfully detected the intruder.
  * **Time Limit Reached %**: How often the target eluded detection for the entire mission duration.
  * **Target Escaped %**: How often the intruder reached the boundary without being intercepted.
* **Detection Time Histogram**: Shows the statistical distribution of *when* detections occurred (e.g. most detections happen between 15 and 30 minutes into the patrol).
* **Fleet Convergence Chart**: A line graph verifying that running more replications stabilised the probability estimate, confirming statistical confidence.

#### 2. Animation Tab (Tactical Replay)
Inspect individual scenario runs visually:


* Select any individual replication from the dropdown menu.
* Use the time slider and Play/Pause controls to view the animation.
* **Operating Area Boundary**: A solid black box clearly marks the scenario's geographic operating limits.
* **Barrier Patrol Lines**: Broad grey lines depict barrier patrol boundaries drawn beneath platform trails.

#### 3. Summary Statistics Tab
Displays tables showing pairwise performance (e.g. which specific platform or sensor made the most contacts, average detection range, and mean time to intercept).

#### 4. Raw Positions Tab
Provides complete tabular logs of platform coordinates ($X, Y$) at every time-step for audit trails and export.

---

## 5. Getting Started: Step-by-Step Follow-Me Scenario

Follow this step-by-step tutorial to configure and execute your very first successful MAKO scenario:

### Step 1: Set World & Simulation Parameters
1. Look at the **Sidebar** on the left.
2. Confirm the **World Parameters**:
   * `Origin X = 0`, `Origin Y = 0`
   * `Length = 100`, `Height = 100` (representing a $100 \times 100\text{ km}$ area).
3. Under **Simulation Parameters**:
   * Set `Number of Simulations = 100` (for a rapid initial test).
   * Set `Time Limit (hours) = 2`.
   * Set `Time Step (seconds) = 1.0`.
   * Keep `Detection End Condition = initial_detection`.
   * Ensure `Use Seeds File` is ticked.

### Step 2: Create the Red Target
1. In the navigation menu, select **Create Platforms**.
2. Enter the platform details:
   * **Display Name**: `Red Intruder`
   * **Team**: Select `Red`
   * **Speed (m/s)**: `5.0` (approx. 10 knots)
3. Under **Movement Settings**:
   * Select `Intruder Search`
   * Set `Start Distance (km) = 0.0`
   * Set `End Condition = Boundary Reached`
4. Click **Save Platform**.

### Step 3: Create the Blue Hunter
1. Stay on the **Create Platforms** page.
2. Enter the platform details:
   * **Display Name**: `USV`
   * **Team**: Select `Blue`
   * **Speed (m/s)**: `12.0` (approx. 23 knots)
3. Under **Movement Settings**:
   * Select `Random Walk`
4. Under **Sensor Configuration**:
   * Click **Sensor 1** to expand it.
   * Set `Display Name = Passive Sonar`.
   * Set `Sensor Type = Generic`.
   * Set `FOV Start = 0.0`, `FOV End = 360.0` (omnidirectional coverage).
   * Set `K = 1`, `N = 1` (instant single-contact confirmation).
   * Enter a sample detection range: 
     * Distance: `0` to `20,000` metres ($20\text{ km}$).
     * PoD: `0.9` at close range decaying to `0.1` at $20\text{ km}$.
   * Click **Save Sensor**.
5. Click **Save Platform**.

### Step 4: Generate Configuration & Run
1. In the navigation menu, select **Run Monte Carlo Simulation** (Home).
2. Look at the status card: it should display a **green "Simulation Ready"** box listing `Red Intruder` and `Blue Defender`. Review the Platforms and Sonobuoys summary tables below the card.
3. Click the button labelled **Create Config YAML**.
4. Once the green notification appears, click **Run Simulation**.
5. Watch the progress bar advance through all 100 replications until completion.

### Step 5: Inspect Your Results
1. In the navigation menu, select **Results**.
2. Look at the top metric cards on the **Detection Analytics** tab:
   * Read the **Fleet Detection Prob ($P_{\text{det}}$)** to discover the likelihood of intercepting the intruder.
3. Switch to the **Animation** tab:
   * Choose `Replication 1` from the dropdown list.
   * Press **Play** or drag the slider to watch `Blue Defender` hunt down `Red Intruder` in full animated playback with operating area and barrier lines displayed.

---

## 6. Troubleshooting & Frequently Asked Questions (FAQ)

### Q1: Why did my simulation finish with a 0% Detection Rate?
> **Answer**: This usually happens for one of three reasons:
> 1. **Sensor Range Too Small**: The patrol area is vast (e.g. $100 \times 100\text{ km}$) but your sensor detection range is only $2\text{ km}$.
> 2. **Mission Time Limit Too Short**: The vessels did not have enough time to encounter each other before the time limit expired.
> 3. **Sensor Intervals / $k$-of-$n$**: If $k$ is set high (e.g. 5 detections) but the target speeds quickly past the sensor, the sliding window never registers enough consecutive hits.

### Q2: Why aren't my Sonobuoys recording any detections?
> **Answer**: Multistatic sonobuoys are passive listening nodes that require an acoustic echo. Ensure that at least one of your Blue vessels has **Active Source** checked on its sensor configuration to emit pings.

### Q3: Why do I get the exact same results every time I click Run?
> **Answer**: In the sidebar, `Use Seeds File` is enabled by default. This uses predefined random seeds for perfect scientific repeatability. If you want natural statistical variance, uncheck `Use Seeds File`.


---

*MAKO: Monte-Carlo Agent Kinematic Observation — Built for high-speed simulation and rapid concept exploration.*
