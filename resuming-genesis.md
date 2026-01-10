# How to Resume Work on Project Genesis

This document provides the steps to quickly resume development and operations.

## 1. Read the System Manifest

The single source of truth for this project's architecture and operations is the manifest file. Before taking any action, parse this file:
**`./manifest.yaml`**

This file contains the locations, commands, and actions for all components in the `genesis` system.

## 2. Verify or Restart the System

Use the `manifest.yaml` to guide you. To restart the full simulation for observation, the `restart_all_for_observation` action is defined in the manifest. A typical sequence is:
1.  Ensure `genesis-core` is built on `genesis-compute`.
2.  Run the `start` command for the `core` component on `genesis-compute`.
3.  Run the `start` command for the `observer` component on the local machine.

## 3. Review the Next Steps

The next development phase is documented in two places:
- High-level roadmap: `../DESIGN.md` (See "Phase 3: The Hunger")
- Infrastructure plan: `./INFRASTRUCTURE_PLAN.md`
