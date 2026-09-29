---
description: "Top-level Tiny Tapeout module for TinyTracer, instantiating the SRAM controller, RTU, Execution Unit, Accumulator, and I/O Unit."
---

# `tt_um_tinytracer` — Top-Level Module for TinyTracer

## Overview

This module instantiates the SRAM, SRAM controller, RTU, Execution Unit (EXU), Accumulator, and I/O Unit. The EXU in turn instantiates the Decode Unit, Register File, and FU Control Unit (see [`exu`](exu/exu.md)).

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `ADDR_WIDTH`  |     8      | Width of SRAM addresses               |
| `DATA_WIDTH`  |     16     | Width of SRAM data words              |
| `SPP`         |     8      | Samples per pixel                     |
| `MAX_BOUNCES` |     10     | Ray bounce limit                      |
| `COLOUR_DEPTH` |     8      | Bits per colour channel           |
| `Q_INT`       |     8      | Integer bits in fixed point format    |
| `Q_FRAC`      |     8      | Fractional bits in fixed point format |
| `MACRO_W`     |    101     | Width of macro-op encoding            |
| `WLEN`        |     16     | Word length                           |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal               |
| `rst_n`  |     1     | Active-low reset              |
| `uart_rx`  |     1     | Receives scene data sent from host device to load into SRAM |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `uart_tx`  |     1      | Streams coloured pixel data back to host device              |
