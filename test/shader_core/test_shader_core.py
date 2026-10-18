import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge
from utils.tester import run_test
from utils.cases import obj_case, gnd_case, sky_case

# --- CONFIGURATION ---
CLK_PERIOD_NS = 40  # 25MHz

# TODO: Maybe generate list of state names and values from RTL somehow
STATE_IDLE = 0

OTHER_INPUTS = {
    "new_sample": 1,
    "hit": 1,
    "hit_ground": 1,
    "hit_addr": 9,
    "last_bounce": 1,
    "ray_origin": 48,
    "ray_dir": 48,
    "sky_horizon": 24,
    "sky_top": 24,
    "ground_a": 24,
    "ground_b": 24,
    "sram_data": 16,
    "sram_valid": 1,
    "req_ready": 1,
    "resp_valid": 1,
    "resp_result": 48,
}

# --- HELPERS ---
def check_idle(dut, when):
    """Checks that state is STATE_IDLE"""
    state = dut.u1.state_r.value
    assert int(state) == STATE_IDLE, f"state_r is {int(state)}, not STATE_IDLE {when}"

# --- TEST CASES ---
@cocotb.test()
async def test_idle_without_start(dut):
    """With start=0, SC should stay in STATE_IDLE in all situations."""
    test_cycles = 1000

    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())

    dut.start.value = 0
    for name in OTHER_INPUTS:
        getattr(dut, name).value = 0

    # Reset on
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)

    # Check state
    await FallingEdge(dut.clk)
    check_idle(dut, "after reset")

    # Reset off
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1

    # For many cycles
    for cycle in range(test_cycles):
        # Change other inputs on falling edges
        for name, width in OTHER_INPUTS.items():
            getattr(dut, name).value = random.getrandbits(width)
        await RisingEdge(dut.clk)

        # Check state after rising edges
        check_idle(dut, f"after cycle {cycle}")
        await FallingEdge(dut.clk)
    
    dut._log.info(f"state_r stayed STATE_IDLE for {test_cycles} cycles with start = 0")


# object tests
@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_obj_mirror_not_last(dut):
    await run_test(dut, obj_case(mat=1), Att(255, 255, 255))

@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_obj_glass_not_last(dut):
    await run_test(dut, obj_case(mat=2), Att(255, 255, 255))

@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_obj_mirror_last(dut):
    await run_test(dut, obj_case(mat=1, last_bounce=1, terminate=1), Att(255, 255, 255))

@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_obj_glass_last(dut):
    await run_test(dut, obj_case(mat=2, last_bounce=1, terminate=1), Att(255, 255, 255))

@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_obj_nonzero_addr(dut):
    await run_test(dut, obj_case(hit_addr=37, mat=1), Att(255, 255, 255))

@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_glow_unit_strength(dut):
    await run_test(dut, obj_case(mat=3, terminate=1, strength=1024), Att(255, 255, 255))

@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_glow_last_bounce(dut):
    await run_test(dut, obj_case(mat=3, terminate=1, last_bounce=1, strength=2048), Att(255, 255, 255))


# ground tests
@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_ground_checker_a(dut):
    await run_test(dut, gnd_case(ray_o_x=0, ray_o_y=0), Att(255, 255, 255))

@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_ground_checker_b(dut):
    await run_test(dut, gnd_case(ray_o_x=512, ray_o_y=0), Att(255, 255, 255))

@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_ground_checker_both_bits(dut):
    await run_test(dut, gnd_case(ray_o_x=512, ray_o_y=512), Att(255, 255, 255))

@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_ground_last_bounce(dut):
    await run_test(dut, gnd_case(last_bounce=1, terminate=1), Att(255, 255, 255))


# sky tests
@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_sky_half_up(dut):
    await run_test(dut, sky_case(ray_dir_z=8192), Att(255, 255, 255))

@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_sky_full_up(dut):
    await run_test(dut, sky_case(ray_dir_z=16383), Att(255, 255, 255))

@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_sky_pointing_down(dut):
    await run_test(dut, sky_case(ray_dir_z=0xE000), Att(255, 255, 255))

@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_sky_last_bounce(dut):
    await run_test(dut, sky_case(last_bounce=1), Att(255, 255, 255))
