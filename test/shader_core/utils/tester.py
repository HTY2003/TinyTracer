# this is the class that ties everything together
from dataclasses import dataclass
import logging
import cocotb
import cocotb.triggers as triggers
import cocotb.clock as clock
from typing import Annotated, Literal, Union

from cases import Object, Ground, Sky
from decoder import Decoder
from sram import Sram



class Tester: 
    
    def __init__(self, dut):
        self.dut = dut
        self.clk = clock.Clock(self.dut.clk, 10, units="ns")
        self.decoder = Decoder()
        self.sram = Sram()
        self.REGISTRY = {
                    Object  : self.obj_test,
                    Ground  : self.gnd_test,
                    Sky     : self.sky_test
            }


    async def reset(self):
        self.sram.data.clear()
        self.dut.rst_n.value = 0
        await triggers.ClockCycles(self.dut.clk, 5)
        self.dut.rst_n.value = 1
    

    async def run(self):

        cocotb.start_soon(self.clk.start())
        cocotb.start_soon(self.sram.run(self.dut))
        cocotb.start_soon(self.decoder.run(self.dut))

    def pack_sample(self, t):
        return t[2] << 24 | t[1] << 12 | t[0] 

    async def verify_op(self, u, v, op, fmt, extra_shift=0):

        await triggers.RisingEdge(self.dut.resp_valid)
      
        expected_res = self.decoder.process_req(u,v,op,fmt)

        assert expected_res == int(self.dut.resp_result.value)
        return expected_res

    async def sample_done(self):
        while True:
            await triggers.RisingEdge(self.dut.clk)
            if int(self.dut.done.value) == 1:
                vals = (int(self.dut.path_end.value),
                        int(self.dut.sample.value),
                        int(self.dut.material.value))
                await triggers.RisingEdge(self.dut.clk)
                assert int(self.dut.done.value) == 0
                return vals

    async def pull_correct_addrs(self,obj):
        addrs = []
        r = 3
        expected_addrs = [obj.hit_addr + 2, obj.hit_addr + 1, obj.hit_addr]
        if (obj.mat != 0b11 and obj.last_bounce == 1):
            r = 1
            expected_addrs = [obj.hit_addr+2]

        async def addr_monitor():
            while True:
                await triggers.RisingEdge(self.dut.sram_rd)
                addrs.append(int(self.dut.sram_addr.value))
        cocotb.start_soon(addr_monitor())
        seen = 0


        # im genuinely confused about how this works instead of the for loop i had before
        while seen < r:
            await triggers.RisingEdge(self.dut.clk)
            if self.dut.sram_valid.value == 1:
                assert int(self.dut.sram_data.value) == self.sram.data[obj.hit_addr + 2 - seen]
                seen += 1;
        
  

        assert addrs == expected_addrs

    def res_to_real_tuple(self, res):
        tup = (res & 0xFFFF, res >> 16 & 0xFFFF, res  >> 32 & 0xFFFF)
        real_tup = tuple(map(self.decoder.to_real, tup))
        return real_tup

    def real_tuple_to_res(self, tup):
        res = tup[0] << 32 | tup[1] << 16 | tup[2] 
        return res

    def verify_end_behaviour(self, case, res, path_end, sample, material):
        if case.terminate or case.last_bounce:
            assert path_end == 1
            assert sample == res
        else:
            assert path_end == 0
        if isinstance(case, Object) and not (case.terminate or case.last_bounce):
            assert material == case.mat
    
    async def path_end_high_at_start(self):
        await triggers.RisingEdge(self.dut.start)
        assert self.dut.path_end.value == 1
        

     
    def start(self, obj):
        self.dut.start.value = obj.start
        self.dut.new_sample.value = obj.new_sample

    
    
    async def obj_test(self, obj, att):
        if (obj.new_sample == 1):
            att = Att(255, 255, 255)
        self.dut.hit_ground.value    = 0
        self.dut.hit_addr.value      = obj.hit_addr
        self.dut.hit.value           = 1
        self.sram.ingest_obj(obj)


        await self.pull_correct_addrs(obj)

        await triggers.RisingEdge(self.dut.clk)
        self.dut.start.value         = 0
        self.dut.new_sample.value    = 0


        expected_res = None

        if (obj.mat == 0b11):
            u = (att.b+1, att.g+1, att.r+1)
            v = (obj.b, obj.g, obj.r)

            expected_res = await self.verify_op(u, v, Decoder.M_VMUL, 0)
            
            u_in = obj.strength & 0xFFFF
            u = (u_in, u_in, u_in)
            v = self.res_to_real_tuple(expected_res)

            v = tuple(map(lambda x: (x >> 1) & 0xFF, v))
            
            expected_res = await self.verify_op(u,v, Decoder.M_SCAL_VEC,0)

            expected_tup = self.res_to_real_tuple(expected_res)
            expected_tup = tuple(map(lambda x: (x>>3) & 0xFFF, expected_tup))

            expected_res = self.pack_sample(expected_tup)

        elif (obj.last_bounce == 1):
            return 0
        else:
            u = (att.b, att.g, att.r)
            v = (obj.b+1, obj.g+1, obj.r+1)

            expected_res = await self.verify_op(u,v, Decoder.M_VMUL, 0)
            
            expected_tup = self.res_to_real_tuple(expected_res)
            expected_tup = tuple(map(lambda x: (x>>1) & 0xFF, expected_tup))

            expected_res = self.real_tuple_to_res(expected_tup)

        
        return expected_res


    async def gnd_test(self, gnd, att):
        if (gnd.new_sample == 1): 
            att = Att(255, 255, 255)
        self.dut.hit_ground.value    = gnd.hit_ground
        self.dut.hit.value           = gnd.hit
        self.dut.ray_origin.value    = gnd.ray_o_z << 32 | gnd.ray_o_y << 16 | gnd.ray_o_x 
        

        self.dut.ground_a.value = gnd.gnd_a_r << 16 | gnd.gnd_a_g << 8 | gnd.gnd_a_b 

        self.dut.ground_b.value = gnd.gnd_b_r << 16 | gnd.gnd_b_g << 8 | gnd.gnd_b_b

        await triggers.RisingEdge(self.dut.clk)
        self.dut.start.value         = 0
        self.dut.new_sample.value    = 0

        expected_res = None

        if (gnd.last_bounce == 1):
            return 0

        else:
            checker = (gnd.ray_o_x >> 9 & 1) ^ (gnd.ray_o_y >> 9 & 1)

            u = (att.b, att.g, att.r)
            ray = (gnd.gnd_b_b, gnd.gnd_b_g, gnd.gnd_b_r) if checker else (gnd.gnd_a_b, gnd.gnd_a_g, gnd.gnd_a_r)

            ray = tuple(c+1 for c in ray)
            
            expected_res = await self.verify_op(u, ray, Decoder.M_VMUL, 0)
            
            expected_tup = self.res_to_real_tuple(expected_res)
            expected_tup = tuple(map(lambda x: (x>>1) & 0xFF, expected_tup))

            expected_res = self.real_tuple_to_res(expected_tup)


        return expected_res


    async def sky_test(self, sky, att):
        if (sky.new_sample == 1):
            att = Att(255, 255, 255)
        self.dut.hit_ground.value    = 0
        self.dut.hit.value           = 0

        self.dut.ray_dir.value       = sky.ray_dir_z << 32 | sky.ray_dir_y << 16 | sky.ray_dir_x

        self.dut.sky_horizon.value  =  sky.hor_r << 16 | sky.hor_g << 8 | sky.hor_b

        self.dut.sky_top.value      =  sky.top_r << 16 | sky.top_g << 8 | sky.top_b

        await triggers.RisingEdge(self.dut.clk)
        self.dut.start.value         = 0
        self.dut.new_sample.value    = 0

        top_vec = (sky.top_b, sky.top_g, sky.top_r)
        hor_vec = (sky.hor_b, sky.hor_g, sky.hor_r)

        expected_res1 = await self.verify_op(top_vec, hor_vec, Decoder.M_VSUB, 0)
        z_val = 0 if (sky.ray_dir_z >> 15 == 1) else sky.ray_dir_z
        dir_vec = (z_val, z_val, z_val)
        res1 = self.res_to_real_tuple(expected_res1)

        expected_res2 = await self.verify_op(dir_vec, res1, Decoder.M_SCAL_VEC, 1)
        
        res2 = self.res_to_real_tuple(expected_res2)
        
        expected_res3 = await self.verify_op(hor_vec, res2, Decoder.M_VADD, 0)

        res3 = self.res_to_real_tuple(expected_res3)

        att_vec = (att.b+1, att.g+1, att.r+1)

        expected_res4 = await self.verify_op(att_vec, res3, Decoder.M_VMUL, 0)

    
        expected_tup = self.res_to_real_tuple(expected_res4)
        expected_tup = tuple(map(lambda x: (x>>1) & 0xFF, expected_tup))

        expected_res4 = self.pack_sample(expected_tup)


        return expected_res4


async def run_test(dut, case, att):
    tester = Tester(dut)

    cocotb.start_soon(tester.run())

    await triggers.RisingEdge(dut.clk)
    await tester.reset()
    await triggers.RisingEdge(dut.clk)
    

    watcher = cocotb.start_soon(tester.sample_done())

    dut.new_sample.value    = case.new_sample
    dut.start.value         = 1
    dut.last_bounce.value   = case.last_bounce

    test_func = tester.REGISTRY.get(type(case))
    res = await test_func(case, att)

    path_end, sample, material = await watcher
    tester.verify_end_behaviour(case, res, path_end, sample, material)


