---
description: "Execution Unit that wraps the Decode Unit, micro-op ROM, register file, and functional units, and executes macro-ops issued by the RTU."
---

# `exu` — Instantiates Decode Unit, Register File, and Functional Units

## Overview

The Execution Unit (EXU) is TinyTracer's backend. It receives macro-ops from the RTU, executes them, and returns their results. The EXU instantiates the Decode Unit, Register File, and Functional Units.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `MACRO_W`  |     101    | Macro operation width             |
| `MACROOP_W`  |     5      | Macro opcode width |
| `MICRO_W`  |     13    | Micro operation width             |
| `MICROOP_W`  |     4      | Micro opcode width |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| [`macro_if.server`](../tinytracer_if.md#macro_if)  | Macro-op request and response channel from the RTU, passed through to the Decode Unit |

## Architecture Overview


