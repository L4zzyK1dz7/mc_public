### The Agile Story Map (Red vs. Blue Detection)

|  | Epic 1: Configuration UI (Streamlit) | Epic 2: Simulation Math (Domain Logic) | Epic 3: Monte Carlo Engine | Epic 4: Results & Export |
| --- | --- | --- | --- | --- |
| **Slice 1: The Walking Skeleton** *(Sprint 1)* | Create a Streamlit page with a single "Run" button and hardcoded variables. | Create 1 Red and 1 Blue agent. They don't move. Just calculate distance between their starting points. | Write a basic function that runs the math exactly **1 time**. | Display a plain text "Detected" or "Time Out" message on the Streamlit UI. |
| **Slice 2: Core Mechanics** *(Sprint 2)* | Add UI inputs for Grid Size, Sensor Radius, and Time Limit. | Implement random movement per tick. Implement Pythagorean distance check against the Sensor Radius. | Implement the "Tick" loop. Stop early if detection occurs, or stop when Time Limit is hit. | Show the exact `tick_count` of when the simulation ended in a simple UI table. |
| **Slice 3: The Monte Carlo Scale** *(Sprint 3)* | Add UI input for "Number of Replications". | Refactor to support *lists* of multiple Red and Blue agents roaming the same grid. | Wrap the tick loop in a standard `for` loop to run `N` sequential replications. | Aggregate the results of all replications into a single Streamlit DataFrame (e.g., Win Rate, Avg Ticks). |
| **Slice 4: Export & Polish** *(Sprint 4)* | Add granular sliders for Red Agent Count, Blue Agent Count, and specific speeds. | Add edge-collision math (agents bounce off grid walls instead of walking off). | Add a `st.progress()` bar to the loop so the UI updates during long sequential runs. | Add a Streamlit `st.download_button()` to export the DataFrame to a `.csv` file. |

---



1. **The UI (Epic 1 & 4):** Because a single-threaded loop will "block" Streamlit, the user won't be able to click anything else while the `for` loop is running. This is perfectly fine for a simple tool, but it means adding that progress bar in Slice 4 is crucial so they know the app hasn't crashed.


You caught a crucial shift in the architecture. This is a fantastic product management catch.

Whether "Data Ingest and Validation" needs to be its own Epic depends entirely on **how the user is giving you the data** in this new Streamlit version.

### Scenario A: Sliders Only (Validation is Built-In)

If your users are *only* using Streamlit sliders and number boxes to set the parameters (e.g., Grid Size = 100, Red Agents = 5), you actually don't need a massive Data Validation Epic. Streamlit handles it for you. You can't type the word "apple" into a Streamlit integer slider. The UI *is* the validation. In this case, "Configuration UI" covers it.



|  | Epic 1: Data Ingest & Validation | Epic 2: Simulation Math | Epic 3: Monte Carlo Engine | Epic 4: Results & Export |
| --- | --- | --- | --- | --- |
| **Slice 1: The Walking Skeleton** | Create a hardcoded Python dictionary of starting data. No validation yet. | 1 Red, 1 Blue agent. Calculate distance between their starting points. | Run the math 1 time. | `print()` "Detected" or "Time Out" to the console/UI. |
| **Slice 2: Core Mechanics** | Add Streamlit file uploader or inputs. Validate that values aren't empty/null. | Implement random movement per tick and Pythagorean distance check against Sensor Radius. | Implement the "Tick" loop. Stop early if detection occurs, or when Time Limit hits. | Show the exact `tick_count` of when the simulation ended in a simple UI table. |
| **Slice 3: The Monte Carlo Scale** | Add complex validation: Ensure starting coordinates are inside the grid bounds. | Support lists of multiple Red and Blue agents roaming the same grid. | Wrap the tick loop in a standard `for` loop to run `N` sequential replications. | Aggregate the results of all replications into a single Streamlit DataFrame. |
| **Slice 4: Export & Polish** | Add logic validation: Ensure Red and Blue agents don't spawn on top of each other. | Add edge-collision math (agents bounce off grid walls instead of walking off). | Add a `st.progress()` bar to the loop so the UI updates during long runs. | Add a Streamlit `st.download_button()` to export the DataFrame to a `.csv` file. |



Translating your Story Map into Jira is where the abstract planning finally becomes a concrete developer to-do list.

In Jira, you will work from the top down: creating the big buckets first, filling them with stories, and then organizing those stories into your sprint timeline.

Here is the exact click-by-click process to populate your backlog.

1. **Step 1: Create the 4 Epics (The Columns):**
Go to your Jira Backlog view. Look for the **Epic Panel** (usually on the left side) and click **Create Epic**. Create exactly four Epics, naming them after the columns on your Story Map:

* `Epic 1: Data Ingest & Validation`
* `Epic 2: Simulation Math`
* `Epic 3: Monte Carlo Engine`
* `Epic 4: Results & Export`


2. **Step 2: Create the User Stories (The Grid Boxes):**
Click the standard **Create Issue** button (select the "Story" issue type). You are going to create one Story ticket for every single box on your grid (16 tickets total).

For each ticket, make sure you **link it to its parent Epic**.

**Example format for the title:**

* `[UI] Hardcoded Data Dictionary` (Link to Epic 1)
* `[Math] Basic 1v1 Distance Check` (Link to Epic 2)
* `[Engine] Single-run execution function` (Link to Epic 3)


3. **Step 3: Write the Acceptance Criteria (The Definition of Done):**
Open each Story you just created and fill out the description. You must define exactly what the developer needs to build so they know when to stop coding.

**Example for the Epic 2 / Slice 2 Story:**

* *Description:* "As a user, I want the agents to move randomly and check their sensors so a detection can occur."
* *Acceptance Criteria:*
1. Agents must move X, Y coordinates randomly per tick.
2. Must use Pythagorean theorem to check distance between Red and Blue agents.
3. If distance < Sensor Radius, system must log a 'Detection'.




4. **Step 4: Create Sprints and Slice the Work (The Rows):**
At the top of your Jira Backlog, click **Create Sprint**. Do this four times to create Sprint 1, 2, 3, and 4.

Now, look at **Slice 1 (The Walking Skeleton)** on your Story Map. Find those specific four Jira tickets in your backlog and **drag them into Sprint 1**.

Drag the Slice 2 stories into Sprint 2, and so on. Your Jira Timeline will now perfectly reflect your Agile strategy.


5. **Step 5: Add Sub-Tasks (The Developer Instructions):** Done during the Sprint Planning meeting.
You do not need to do this for the whole board right now. When Sprint 1 actually starts, the developer assigned to a Story will click into it and create **Sub-tasks**.

For the `[Math] Basic 1v1 Distance Check` story, the developer's Sub-tasks might be:

* Create `Agent` Python class with `x,y` properties.
* Write `math.dist()` calculation function.


### The Golden Rule of the Jira Backlog

Once you finish Step 4, **stop.**

Do not spend hours writing perfect Acceptance Criteria or Sub-tasks for Sprint 3 or Sprint 4 right now. In Agile, the things you learn in Sprint 1 will almost certainly change how you build Sprint 3.

Populate the titles for the whole board, but only heavily detail the tickets in the Sprint you are about to start.

let's open up just Epic 1 (Data Ingest & Validation) and look inside the bucket. You will create these 4 separate User Stories and link all of them to Epic 1:

User Story 1 (For Sprint 1): Create a hardcoded Python dictionary of starting data.

User Story 2 (For Sprint 2): Add a Streamlit file uploader and validate that inputs aren't empty.

User Story 3 (For Sprint 3): Add boundary checking to ensure agents start inside the grid.

User Story 4 (For Sprint 4): Add logic checking to ensure Red and Blue agents don't spawn on top of each other.


You hit the nail on the head. That is the gold standard for writing Agile tickets.

It is called the **"Connextra" format**:

> *"As a [persona], I want to [action] so that [value/benefit]."*

And yes, **every single story (every slice) inside Epic 1 gets written exactly like this.**

We write them this way to force the developer to focus on *why* the feature matters to a human being, rather than just treating it as a sterile technical task.

Here is exactly how you write the four stories for Epic 1 using this format.

### Translating Epic 1 Slices into Formatted User Stories

**Slice 1: The Hardcoded Dictionary**

* **The Story:** "As a **developer**, I want to **run the simulation using a hardcoded data dictionary**, so that **I can test the core math pipeline without spending time building a UI.**"
* *Note:* In Slice 1 (The Walking Skeleton), the "user" is often the developer or the tester. It's okay to admit that the value here is purely technical validation!

**Slice 2: The Basic Uploader**

* **The Story:** "As a **data analyst**, I want to **upload my agent coordinates via a Streamlit file uploader**, so that **I can change the starting parameters without having to edit Python code.**"

**Slice 3: Boundary Validation**

* **The Story:** "As a **data analyst**, I want to **receive a UI warning if my uploaded agents are placed outside the grid dimensions**, so that **I don't waste time running a corrupted, invalid simulation.**"

**Slice 4: Logic Validation**

* **The Story:** "As a **data analyst**, I want the **system to reject files where Red and Blue agents spawn on the exact same starting coordinate**, so that **my Monte Carlo results are mathematically fair and valid.**"

---

### Why This Format is So Powerful

Look at Slice 4. If you had just written a task that said, *"Check for overlapping coordinates,"* a developer might have decided to automatically delete one of the overlapping agents and run the simulation anyway.

But because you wrote, *"...so that my Monte Carlo results are mathematically fair and valid,"* the developer understands the context. They know that silently deleting an agent ruins the fairness of the test. The format tells them they need to stop the program and throw a hard error back to the user.

Writing the **Acceptance Criteria (AC)** is the most important part of the entire Jira ticket. If the User Story is the *goal*, the Acceptance Criteria are the *boundary lines*.

It acts as a contract: If the developer meets all the criteria, the ticket is officially "Done." If even one criterion fails, the ticket bounces back to "In Progress."

Let's take **Slice 3 (Boundary Validation)** from your first Epic and write the Acceptance Criteria for it.

### The Context

> **User Story:** As a data analyst, I want to receive a UI warning if my uploaded agents are placed outside the grid dimensions, so that I don't waste time running a corrupted, invalid simulation.

### How to Write the Acceptance Criteria

You can write AC as simple bullet points, or you can use the industry-standard **Given / When / Then** format (also known as Behavior-Driven Development or BDD). As a Senior Developer, I highly recommend using a mix of both to remove all ambiguity.

Here is exactly what goes into that Jira ticket under the User Story:

---

**Acceptance Criteria:**

* **Technical Rules:**
* The system must read the current `Grid Size` dynamically from the Streamlit UI (e.g., if the user sets it to 100x100).
* The system must check every X and Y coordinate in the uploaded CSV against that Grid Size.
* Coordinates cannot be less than 0, and cannot be greater than the Grid Size.


* **Scenario A: Successful Upload**
* **Given** the Grid Size is 100x100
* **When** the user uploads a CSV where all agents are between 0 and 100
* **Then** the UI shows a green `st.success()` message and enables the "Run Simulation" button.


* **Scenario B: Out of Bounds Upload**
* **Given** the Grid Size is 100x100
* **When** the user uploads a CSV with a Red Agent at coordinate `(105, 50)`
* **Then** the system blocks the simulation from starting.
* **And** the system displays a red `st.error()` message that explicitly tells the user *which* row in the CSV failed (e.g., "Error: Red Agent on Row 4 is outside the 100x100 grid").



---

### Why this saves you weeks of wasted time

Imagine you *didn't* write Scenario B.

A junior developer might write code that just crashes the Python script entirely if a number is too high. Or, they might show a generic error message that says "Invalid Data," forcing the data analyst to manually hunt through a 10,000-row CSV file to figure out which agent is broken.

By writing exact Acceptance Criteria, you are forcing the developer to build a good User Experience (telling the user exactly which row failed) before they are allowed to move the Jira ticket to the "Done" column.