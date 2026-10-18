import logging
import cocotb
import cocotb.triggers as triggers
import cocotb.clock as clock

class Decoder:

    M_VSUB      = 0b01101
    M_SCAL_VEC  = 0b01110
    M_VADD      = 0b01100
    M_VMUL      = 0b10011

    

    OPS = {
        M_VADD:     lambda u, v: tuple(a + b for a, b in zip(u, v)),
        M_VSUB:     lambda u, v: tuple(a - b for a, b in zip(u, v)),
        M_SCAL_VEC: lambda u, v: tuple(u[0] * b for b in v),
        M_VMUL:     lambda u, v: tuple(a * b for a, b in zip(u, v)),
    }

    def __init__(self):
        self.req_ready  = 1      
        self.resp_valid = 0

    def clamp(self, num):
        return(max(-32768, min(num, 32767)))

    # this func takes in a signed int and converts it to the negative real number
    def to_real(self, num):
        num &= 0xFFFF

        return num-0x10000 if num & 0x8000 else num

    # convert back to the signed int format which is not the real number
    def to_signed_format(self, num):
        return self.clamp(num) & 0xFFFF

    
    # ik RTU does shifting but imma just do it here for simplicity
    def shift_num(self, num, shift):
        if shift == 0:
            return num
        return (num + (1 << (shift - 1))) >> shift


    def process_req(self, u, v, op, fmt):
        u  = tuple(self.to_real(x) for x in u)
        v  = tuple(self.to_real(x) for x in v)

        func = Decoder.OPS[op]
        shift = 14 if fmt else 7
        shift = 0 if (op == Decoder.M_VSUB or op == Decoder.M_VADD) else shift
        res = func(u, v)
        
        res = tuple(self.to_signed_format(self.shift_num(x, shift)) for x in res)

        res =   res[2] << 32 | res[1] << 16 | res[0]

        return res


    def route_op(self, dut):
        req_op = int(dut.req_op.value)
        op_code = req_op & 0b11111
        v  = (req_op >> 5) & ((1<<48)-1)
        u = (req_op >> 53) & ((1<<48)-1)

        # these are all in the signed format so we gotta convert to real numbers
        ux = u          & 0xFFFF
        uy = u >> 16    & 0xFFFF
        uz = u >> 32    & 0xFFFF

        vx = v          & 0xFFFF
        vy = v >> 16    & 0xFFFF
        vz = v >> 32    & 0xFFFF

        fmt = (req_op >> 101) & 1

        res = self.process_req((ux, uy, uz), (vx, vy, vz), op_code, fmt)
        return res


    async def run(self, dut):


        dut.req_ready.value = 1
        dut.resp_valid.value = 0
        dut.resp_result.value = 0

        while True:
            await triggers.RisingEdge(dut.clk)

            if (dut.req_valid.value):
                dut.req_ready.value = 0
                result = self.route_op(dut)
                await triggers.ClockCycles(dut.clk, 7)
                dut.resp_valid.value = 1
                dut.resp_result.value = result
                
                await triggers.RisingEdge(dut.clk)
                while not (dut.resp_ready.value):
                    await triggers.RisingEdge(dut.clk)

            dut.req_ready.value = 1
            dut.resp_valid.value = 0


