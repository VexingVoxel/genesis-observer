# Genesis Project: Infrastructure & Development Hardening Plan

This document outlines a plan to harden the infrastructure, development, and operational processes for the `genesis` project. The goal is to make the system more robust, predictable, and easier to manage.

This plan leverages the existing Git-based deployment workflow (`push` from laptop -> `pull` on nodes) and focuses on automating the environment setup and service lifecycle management *after* a `git pull`.

---

## Area 1: Environment & Configuration Hardening

*   **Objective:** Guarantee that the environment on each node is consistent and capable of building and running the code pulled from Git. This prevents a successful `git pull` from failing due to missing dependencies, tools, or incorrect paths.

*   **Proposed Solution (Ansible):**
    1.  **Create a `playbook.yaml`:** This single file will codify the required state of all nodes. It will declare required packages (`build-essential`, `libzmq3-dev`, `python3-venv`, `yq`), ensure the Rust toolchain is installed, and configure the `admin` user's shell profile to include necessary environment variables (like sourcing `/home/admin/.cargo/env`).
    2.  **Justification:** This replaces manual, error-prone `ssh` and `apt-get` commands with a single, version-controllable, and idempotent command (`ansible-playbook`), eliminating environment drift and simplifying node setup.

*   **Configuration Centralization:**
    1.  **Modify Python Scripts:** Update `listener.py` and `launcher.py` to read the simulation host's IP from a `GENESIS_CORE_HOST` environment variable instead of a hardcoded value.
    2.  **Update `manifest.yaml`:** The `run` commands in the manifest will be prepended with `export GENESIS_CORE_HOST={{nodes.simulation_host.host}} && ...` to ensure configuration is always sourced from the manifest.

---

## Area 2: Automation After the `git pull`

*   **Objective:** Automate the build and restart process that occurs after new code is pulled to a node.

*   **Action Items:**
    1.  **Create a `rebuild-and-run.sh` script:** This script, deployed via Git to all nodes, will be node-aware. When executed, it will:
        *   Determine its own hostname.
        *   Find which `component` in `manifest.yaml` is assigned to it.
        *   Execute the corresponding `stop`, `build`, and `run` commands from the manifest for that component only.
    2.  **Integrate with the Git Workflow:** The existing mechanism that triggers a `git pull` on the nodes will be modified to execute `./scripts/rebuild-and-run.sh` immediately after a successful pull. This creates a fully automated CI/CD pipeline: `git push` -> nodes `git pull` -> nodes `rebuild-and-run`.

---

## Area 3: Unified Monitoring & Manual Control

*   **Objective:** Create a single, high-level interface on the laptop for managing and monitoring the entire distributed application.

*   **Action Items:**
    1.  **Create a `manage-genesis.sh` script:** This script will serve as the master control panel on the laptop. It will accept arguments like `status`, `stop`, and `restart`.
        *   `./manage-genesis.sh status`: Will use the manifest to execute the `is_running_check` for every component on its respective node and present a unified status report.
        *   `./manage-genesis.sh stop`: Will execute the `stop_all` action from the manifest.
        *   `./manage-genesis.sh restart`: Will execute the `restart_all_for_observation` action from the manifest.
        *   This script will require `yq` (a command-line YAML parser) to be installed on the laptop to parse `manifest.yaml` and orchestrate the remote commands.

---
