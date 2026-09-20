---
name: ux-planner
description: Creates user persona journeys, cognitive walkthroughs, information architecture, and structural wireframes for web applications. Synthesizes UX patterns from msitarzewski/agency-agents (ArchitectUX, UI Designer, Persona Walkthrough Specialist) and ui-ux-pro-max.
---

# UX Planner — Persona-Driven Architecture & Wireframing

## Overview

The **UX Planner** skill designs user interfaces from the psychological perspective of specific user personas before code is written. It translates user mental models, task workflows, and cognitive friction points into information architecture, layout grids, and structural wireframes.

Adapted from **The Agency (msitarzewski/agency-agents)**:
- **ArchitectUX**: Technical information architecture, layout grids, CSS foundations, and developer handoffs.
- **UI Designer**: Component specifications, visual hierarchies, and design token contracts.
- **Persona Walkthrough Specialist**: Cognitive think-aloud simulations, trust deltas, and friction analysis grounded in LIFT and Fogg behavior models.

---

## When to Use

- When planning a new page, application dashboard, or significant interface workflow.
- When existing UI feels "unclean", confusing, or disconnected from the actual user persona.
- When establishing screen-by-screen wireframes, information architecture, and visual hierarchy.
- When validating whether a layout answers the persona's 5-second test ("What is this? Is it for me? What do I do next?").

---

## Core Planning Workflow

### Step 1: Define Target User Personas
For each primary audience, define:
1. **Role & Mental Model**: What are they trying to accomplish? What tools do they live in?
2. **5-Second Intent**: What must they see immediately upon opening the page?
3. **Primary Fears & Anxieties**: What kills trust (e.g. unprovable claims, clutter, slow loads)?
4. **Success Threshold**: What triggers satisfaction (e.g. instant test execution, deterministic proof)?

### Step 2: Information Architecture & Information Density
1. **Screen Hierarchy**: Order components by importance to the primary persona.
2. **Zoning**: Split the screen into functional zones (Navigation, Inputs/Configuration, Inspection, Telemetry, Details).
3. **Density Rating**: Align with persona expectations (e.g., Data-Dense for developers/engineers vs Spacious for consumer landing pages).

### Step 3: Structural Wireframes (ASCII / Layout Schematics)
Construct clean, proportioned wireframe layouts showing:
- Header & Context controls (workspace, environment, agent, health).
- Split-pane grids and columns.
- Card structures and control placements.
- Data tables, inspection drawers, and modals.
- State transitions (empty, loading, populated, error).

### Step 4: Cognitive Walkthrough (Persona Simulation)
Walk through the wireframe step-by-step:
- **Look**: What element catches the user's eye first?
- **Think**: What is the persona's inner monologue?
- **Do**: What is the immediate, low-friction next action?
- **Trust Delta**: Does trust go up ($\uparrow$) or down ($\downarrow$)?

---

## Output Deliverables
Every UX Planning session produces a dedicated design document (e.g. `docs/design/ux-wireframes.md`) containing:
1. Persona profiles and user journey maps.
2. Complete layout wireframes for every key view and drawer.
3. Component-level interaction specs.
4. Cognitive walkthrough audit results.
