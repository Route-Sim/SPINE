# Backend Architecture Diagram Guide for Visual Paradigm

## Diagram Type
**Component Diagram** or **Deployment Diagram** (showing threads/processes)

In Visual Paradigm, you can use:
- **Component Diagram** - Shows software components and their relationships
- **Deployment Diagram** - Shows runtime architecture with threads/processes
- **Activity Diagram** - Alternative if you want to show the flow

**Recommended: Component Diagram with Thread annotations**

## Components to Include - Visual Paradigm Element Types

This section tells you **exactly what Visual Paradigm element type to use** for each part of your diagram.

---

### Element Type: **Package** (for Thread Boundaries)

**When to use:** To group components that run in the same thread.

**Visual Paradigm Steps:**
1. Insert → Package (or click Package icon in toolbar)
2. Name the package (e.g., "WebSocket Thread")
3. Right-click package → Stereotype → Add `<<thread>>`
4. Drag components into the package

**Packages to Create:**

#### Package 1: "WebSocket Thread"
- **Type:** Package
- **Stereotype:** `<<thread>>`
- **Location:** Right side of diagram
- **Contains:** All components listed below in "WebSocket Thread Components"

#### Package 2: "Simulation Thread"
- **Type:** Package
- **Stereotype:** `<<thread>>`
- **Location:** Left side of diagram
- **Contains:** All components listed below in "Simulation Thread Components"

#### Package 3: "Statistics Thread"
- **Type:** Package
- **Stereotype:** `<<thread>>`
- **Location:** Bottom left of diagram
- **Contains:** All components listed below in "Statistics Thread Components"

---

### Element Type: **Component** (for Main Software Components)

**When to use:** For any software component (threads, queues, world, etc.)

**Visual Paradigm Steps:**
1. Insert → Component (or click Component icon)
2. Name the component
3. Right-click → Stereotype → Add stereotype (e.g., `<<thread>>`, `<<queue>>`)
4. Drag into appropriate package (or leave outside if shared)

---

### WebSocket Thread Components (inside "WebSocket Thread" Package)

#### Component 1: WebSocketServer
- **Type:** Component
- **Name:** `WebSocketServer`
- **Stereotype:** `<<thread>>`
- **Location:** Inside "WebSocket Thread" package
- **Note:** Add a Note element (see below) with responsibilities:
  - Accepts WebSocket connections
  - Receives actions from clients
  - Broadcasts signals to clients

#### Component 2: Uvicorn Server
- **Type:** Component
- **Name:** `Uvicorn Server`
- **Stereotype:** `<<ASGI server>>`
- **Location:** Inside "WebSocket Thread" package (below WebSocketServer)
- **Note:** This is a sub-component of WebSocketServer

#### Component 3: Async Event Loop
- **Type:** Component
- **Name:** `Async Event Loop`
- **Stereotype:** `<<async task>>`
- **Location:** Inside "WebSocket Thread" package (below Uvicorn Server)
- **Note:** This is a sub-component of WebSocketServer

---

### Simulation Thread Components (inside "Simulation Thread" Package)

#### Component 4: SimulationController
- **Type:** Component
- **Name:** `SimulationController`
- **Stereotype:** `<<thread>>`
- **Location:** Inside "Simulation Thread" package
- **Note:** Add a Note element with responsibilities:
  - Main simulation loop
  - Processes actions from ActionQueue
  - Runs world.step()
  - Emits signals to SignalQueue
  - Collects statistics

#### Component 5: World
- **Type:** Component
- **Name:** `World`
- **Stereotype:** `<<simulation>>`
- **Location:** Inside "Simulation Thread" package (below SimulationController)
- **Note:** Add a Note element with responsibilities:
  - Manages agents
  - Graph structure
  - Simulation step execution

---

### Statistics Thread Components (inside "Statistics Thread" Package)

#### Component 6: StatisticsWriter
- **Type:** Component
- **Name:** `StatisticsWriter`
- **Stereotype:** `<<thread>>`
- **Location:** Inside "Statistics Thread" package
- **Note:** Add a Note element with responsibilities:
  - Writes statistics batches to files
  - Runs in background

---

### Shared Components (OUTSIDE all packages - these connect threads)

#### Component 7: ActionQueue
- **Type:** Component
- **Name:** `ActionQueue`
- **Stereotype:** `<<queue>>` or `<<thread-safe>>`
- **Location:** Between "WebSocket Thread" and "Simulation Thread" packages
- **Note:** This is a thread-safe queue - highlight it (use orange/yellow color)

#### Component 8: SignalQueue
- **Type:** Component
- **Name:** `SignalQueue`
- **Stereotype:** `<<queue>>` or `<<thread-safe>>`
- **Location:** Between "Simulation Thread" and "WebSocket Thread" packages
- **Note:** This is a thread-safe queue - highlight it (use orange/yellow color)

#### Component 9: SimulationRunner
- **Type:** Component
- **Name:** `SimulationRunner`
- **Stereotype:** `<<main thread>>` or `<<orchestrator>>`
- **Location:** Top center, OUTSIDE all packages
- **Note:** Add a Note element with responsibilities:
  - Orchestrates all threads
  - Manages lifecycle (start/stop)
  - Handles shutdown signals

---

### Element Type: **Note** (for Responsibilities)

**When to use:** To attach responsibilities/descriptions to components.

**Visual Paradigm Steps:**
1. Insert → Note (or click Note icon)
2. Click near the component you want to annotate
3. Type responsibilities as bullet points:
   ```
   • Responsibility 1
   • Responsibility 2
   • Responsibility 3
   ```
4. **Attach the note to the component:**
   - Right-click the note → Attach to Model Element
   - Select the component
   - The note will now move with the component

**Components that need Notes:**
- WebSocketServer
- SimulationController
- StatisticsWriter
- World
- SimulationRunner

---

### Element Type: **Actor** (for Frontend - Optional)

**When to use:** To represent external systems (Frontend client).

**Visual Paradigm Steps:**
1. Insert → Actor (or click Actor icon - stick figure)
2. Name: `Frontend` or `Client`
3. Location: Left side, outside all packages
4. **Alternative:** You can use a Component with stereotype `<<external>>` instead

**Note:** This is optional - you can also just show arrows coming from outside the diagram.

---

### Element Type: **Dependency** or **Association** (for Arrows/Connections)

**When to use:** To show data flow between components.

**Visual Paradigm Steps:**
1. Click on source component
2. Drag to target component
3. Visual Paradigm will prompt for relationship type
4. Choose: **Dependency** (dashed arrow) or **Association** (solid arrow)
5. Double-click the arrow to add label (e.g., "puts actions", "enqueue()")

**Arrow Types:**
- **Dependency** (dashed): For "uses" relationships (e.g., SimulationController → World)
- **Association** (solid): For data flow (e.g., WebSocketServer → ActionQueue)

---

## Quick Reference: When to Use Each Element Type

| Element Type | Use For | Example |
|-------------|---------|---------|
| **Package** | Grouping components in same thread | "WebSocket Thread" package |
| **Component** | Software components | WebSocketServer, ActionQueue, World |
| **Note** | Responsibilities/descriptions | Attached to each main component |
| **Actor** | External systems (optional) | Frontend/Client |
| **Dependency** | "Uses" relationships | SimulationController → World |
| **Association** | Data flow | WebSocketServer → ActionQueue |

---

## Visual Paradigm Creation Order (Recommended)

1. **Create Packages first** (3 packages for threads)
2. **Add Components inside packages** (drag into packages)
3. **Add shared Components outside** (ActionQueue, SignalQueue, SimulationRunner)
4. **Add Actor** (Frontend) - optional
5. **Add Notes** to components (attach responsibilities)
6. **Draw Arrows** (Dependency/Association) between components
7. **Add Labels** to arrows (double-click arrow)
8. **Style and Color** components and packages

## Connections (Arrows/Relationships)

### Data Flow Arrows

1. **Frontend → WebSocketServer**
   - Arrow: `sends actions`
   - Direction: External (Frontend) → WebSocketServer

2. **WebSocketServer → ActionQueue**
   - Arrow: `puts actions`
   - Direction: WebSocketServer → ActionQueue
   - Label: `enqueue()`

3. **ActionQueue → SimulationController**
   - Arrow: `consumes actions`
   - Direction: ActionQueue → SimulationController
   - Label: `get_nowait()`

4. **SimulationController → World**
   - Arrow: `calls`
   - Direction: SimulationController → World
   - Label: `world.step()`

5. **SimulationController → SignalQueue**
   - Arrow: `emits signals`
   - Direction: SimulationController → SignalQueue
   - Label: `put()`

6. **SignalQueue → WebSocketServer (Async Loop)**
   - Arrow: `consumes signals`
   - Direction: SignalQueue → WebSocketServer
   - Label: `get_nowait()`

7. **WebSocketServer → Frontend**
   - Arrow: `broadcasts signals`
   - Direction: WebSocketServer → Frontend

8. **SimulationController → StatisticsWriter**
   - Arrow: `writes batches`
   - Direction: SimulationController → StatisticsWriter
   - (Optional: show internal queue)

9. **SimulationRunner → All Threads**
   - Arrow: `manages lifecycle`
   - Direction: SimulationRunner → (all threads)
   - Style: Dashed line (control flow)

## Visual Styling Recommendations

### Colors
- **Threads**: Light blue or light gray
- **Queues**: Yellow or orange (highlight importance)
- **Main orchestrator**: Purple (matches your theme)
- **World/Simulation**: Green

### Shapes
- **Threads**: Rectangle with rounded corners
- **Queues**: Cylinder or rectangle with queue icon
- **Components**: Standard rectangles

### Labels
- Use clear, descriptive labels on all arrows
- Add stereotypes (`<<thread>>`, `<<queue>>`) to clarify component types
- Show method names where relevant (`put()`, `get_nowait()`, `step()`)

## Layout Suggestion

```
                    [Frontend]
                       ↕
              [WebSocketServer]
              (Thread + Async Loop)
                 ↕        ↕
         [ActionQueue] [SignalQueue]
                 ↕        ↕
        [SimulationController]
              (Thread)
                 ↓
              [World]
         (Simulation State)
                 ↓
        [StatisticsWriter]
            (Thread)
```

## How to Represent Threads in Component Diagrams

In Visual Paradigm Component Diagrams, you have **two main approaches** to represent threads:

### Approach 1: Packages (Recommended for Clear Thread Boundaries)

**Use Packages to group all components that run in the same thread:**

1. **Create a Package** for each thread:
   - Insert → Package (or use Package icon)
   - Name it: `<<WebSocket Thread>>` (use stereotype for clarity)

2. **Place components inside the package:**
   - **WebSocket Thread Package** contains:
     - `WebSocketServer` (main component)
     - `Uvicorn Server` (sub-component)
     - `Async Event Loop` (sub-component)

   - **Simulation Thread Package** contains:
     - `SimulationController` (main component)
     - `World` (used by controller)

   - **Statistics Thread Package** contains:
     - `StatisticsWriter` (main component)

3. **Keep shared components outside packages:**
   - `ActionQueue` and `SignalQueue` stay outside (they connect threads)
   - `SimulationRunner` stays outside (orchestrates all threads)

**Visual Result:** Clear visual boundaries showing which components run in which thread.

### Approach 2: Single Component with Stereotype (Simpler)

**Show only the main component per thread:**

1. **One component per thread:**
   - `WebSocketServer` with stereotype `<<thread>>`
   - `SimulationController` with stereotype `<<thread>>`
   - `StatisticsWriter` with stereotype `<<thread>>`

2. **Sub-components shown as notes or documentation:**
   - Add a note to `WebSocketServer` listing: "Contains: Uvicorn Server, Async Event Loop"
   - Or mention in component documentation

**Visual Result:** Cleaner diagram, less detail, but still shows thread separation.

### Recommendation for Your Diagram

**Use Approach 1 (Packages)** because:
- ✅ Clearly shows thread boundaries
- ✅ Makes it obvious that Uvicorn Server and Async Event Loop are part of WebSocket Thread
- ✅ Professional and comprehensive
- ✅ Easy to understand the architecture

**Package Names:**
- `<<WebSocket Thread>>` - Contains: WebSocketServer, Uvicorn Server, Async Event Loop
- `<<Simulation Thread>>` - Contains: SimulationController, World
- `<<Statistics Thread>>` - Contains: StatisticsWriter

**Visual Paradigm Steps for Packages:**
1. Insert → Package
2. Name it (e.g., "WebSocket Thread")
3. Add stereotype: Right-click package → Stereotype → Add `<<thread>>`
4. Drag components into the package
5. Style the package (color, border) to distinguish threads

**Package Structure Example:**
```
┌─────────────────────────────────────┐
│ <<WebSocket Thread>>                │
│ ┌─────────────────┐                │
│ │ WebSocketServer │                │
│ │  <<thread>>     │                │
│ └─────────────────┘                │
│ ┌─────────────────┐                │
│ │ Uvicorn Server  │                │
│ │  <<ASGI server>>│                │
│ └─────────────────┘                │
│ ┌─────────────────┐                │
│ │ Async Event Loop │                │
│ │  <<async task>>  │                │
│ └─────────────────┘                │
└─────────────────────────────────────┘
```

**Note:** In Visual Paradigm, components inside a package are visually contained within the package rectangle. The package acts as a namespace/container.

## Key Points to Emphasize

1. **Thread-safe queues are the communication mechanism** - highlight these prominently
2. **No direct thread-to-thread communication** - everything goes through queues
3. **Async event loop within WebSocket thread** - for signal broadcasting
4. **SimulationRunner orchestrates** but doesn't participate in data flow
5. **Bidirectional communication**: Actions (Frontend → Backend), Signals (Backend → Frontend)

## How to Add Responsibilities in Visual Paradigm

### Method 1: Notes (Recommended for Diagram Visibility)

**Step-by-step:**
1. Select the component (e.g., `SimulationController`)
2. Go to **Insert** → **Note** (or use toolbar Note icon)
3. Click near the component to place the note
4. Type the responsibilities as bullet points:
   ```
   • Main simulation loop
   • Processes actions from ActionQueue
   • Runs world.step()
   • Emits signals to SignalQueue
   • Collects statistics
   ```
5. **Attach the note to the component:**
   - Right-click the note → **Attach to Model Element**
   - Select the component
   - The note will now move with the component

**Visual Result:** A note box with a dashed line connecting to the component

### Method 2: Component Documentation (Properties Panel)

**Step-by-step:**
1. Right-click the component → **Properties** (or double-click)
2. Go to **Documentation** tab
3. Add responsibilities in the documentation field
4. This appears in the properties panel and can be exported in reports

**Visual Result:** Not visible on diagram, but available in documentation/reports

### Method 3: Text Annotation

**Step-by-step:**
1. Go to **Insert** → **Text**
2. Click near the component
3. Type responsibilities (can use bullet points)
4. Format text as needed

**Visual Result:** Free-floating text near the component

### Recommendation

**Use Method 1 (Notes)** because:
- ✅ Visible directly on the diagram
- ✅ Moves with components when repositioning
- ✅ Clear visual connection to components
- ✅ Professional appearance
- ✅ Can be formatted and styled

**Tip:** Use a consistent note style (same color, font size) for all responsibility notes to maintain visual consistency.

## Example Visual Paradigm Steps

1. Create new **Component Diagram**
2. **Create Packages for each thread:**
   - Insert → Package → Name: "WebSocket Thread" (add `<<thread>>` stereotype)
   - Insert → Package → Name: "Simulation Thread" (add `<<thread>>` stereotype)
   - Insert → Package → Name: "Statistics Thread" (add `<<thread>>` stereotype)
3. **Add components inside packages:**
   - Drag `WebSocketServer`, `Uvicorn Server`, `Async Event Loop` into "WebSocket Thread" package
   - Drag `SimulationController`, `World` into "Simulation Thread" package
   - Drag `StatisticsWriter` into "Statistics Thread" package
4. **Add shared components outside packages:**
   - `ActionQueue`, `SignalQueue` (between packages, connecting threads)
   - `SimulationRunner` (outside, orchestrates all)
5. Add stereotypes to components: Right-click → Stereotype → Add `<<thread>>`, `<<queue>>`, etc.
6. **Add responsibility notes** (Method 1 above) for each main component
7. Draw arrows showing data flow (can cross package boundaries)
8. Add labels to arrows showing method names or data types
9. Use colors to distinguish:
   - Different thread packages (light blue, light green, light yellow)
   - Queues (orange/yellow - highlight importance)
   - Main orchestrator (purple - matches your theme)
10. Add a legend explaining stereotypes, colors, and package meanings

## Final Checklist

- [ ] All threads are clearly labeled
- [ ] **Responsibilities added as notes** attached to each component
- [ ] ActionQueue and SignalQueue are prominently displayed
- [ ] Data flow arrows show direction (Frontend ↔ Backend)
- [ ] Thread boundaries are clear (packages or visual separation)
- [ ] Method names on queue operations (`put()`, `get_nowait()`)
- [ ] SimulationRunner shown as orchestrator (dashed lines)
- [ ] World component shown as simulation state
- [ ] Statistics writer shown (optional but good to include)
