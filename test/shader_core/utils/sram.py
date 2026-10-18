import logging
import cocotb
import cocotb.triggers as triggers
import cocotb.clock as clock


class Sram:

    def __init__(self):
        self.data = {}

    def return_data(self, addr):
        return self.data.get(addr, 0)

    def ingest_obj(self, obj):
        # write to w2
        self.data[obj.hit_addr+2]    = (obj.strength << 2) | obj.mat
        
        #write to w1
        self.data[obj.hit_addr+1]    = (obj.r << 8) | obj.g

        #write to w0
        self.data[obj.hit_addr]      = (obj.b << 8) | 0


    async def run(self, dut):
        dut.sram_valid.value = 0
        while True:
             
            await triggers.RisingEdge(dut.clk)
            dut.sram_valid.value = 0
            if (dut.sram_rd.value == 1):
                addr = dut.sram_addr.value
                await triggers.RisingEdge(dut.clk)
                dut.sram_data.value = self.return_data(int(addr))
                dut.sram_valid.value = 1
