

from dataclasses import dataclass
import logging
import cocotb
import cocotb.triggers as triggers
import cocotb.clock as clock
from typing import Annotated, Literal, Union


@dataclass
class Att:
    r           : Annotated[int, "8-bit"]
    g           : Annotated[int, "8-bit"]
    b           : Annotated[int, "8-bit"]


@dataclass
class BaseCase:
    start       : Annotated[int, "1-bit"]
    new_sample  : Annotated[int, "1-bit"]
    hit         : Annotated[int, "1-bit"]
    hit_ground  : Annotated[int, "1-bit"]
    last_bounce : Annotated[int, "1-bit"]
    terminate   : Annotated[int, "1-bit"]
    name        : str

@dataclass
class Object(BaseCase):
    hit_addr    : Annotated[int, "8-bit"]
    r           : Annotated[int, "8-bit"]
    g           : Annotated[int, "8-bit"]
    b           : Annotated[int, "8-bit"]
    mat         : Annotated[int, "2-bit"]
    strength    : Annotated[int, "14-bit"]
    kind        : Literal["object"] = "object"


@dataclass
class Ground(BaseCase):
    ray_o_x     : Annotated[int, "16-bit"]
    ray_o_y     : Annotated[int, "16-bit"]
    ray_o_z     : Annotated[int, "16-bit"]
    gnd_a_r     : Annotated[int, "8-bit"]
    gnd_a_g     : Annotated[int, "8-bit"]
    gnd_a_b     : Annotated[int, "8-bit"]
    gnd_b_r     : Annotated[int, "8-bit"]
    gnd_b_g     : Annotated[int, "8-bit"]
    gnd_b_b     : Annotated[int, "8-bit"]
    kind        : Literal["object"] = "ground"


@dataclass
class Sky(BaseCase):
    ray_dir_x   : Annotated[int, "16-bit"]
    ray_dir_y   : Annotated[int, "16-bit"]
    ray_dir_z   : Annotated[int, "16-bit"]
    hor_r       : Annotated[int, "8-bit"]
    hor_g       : Annotated[int, "8-bit"]
    hor_b       : Annotated[int, "8-bit"]
    top_r       : Annotated[int, "8-bit"]
    top_g       : Annotated[int, "8-bit"]
    top_b       : Annotated[int, "8-bit"]
    kind        : Literal["object"] = "sky"


    
RayCase = Annotated[
        Union[Object, Ground, Sky],
        "cases the ray can find itself in"
        ]



def obj_case(**kw):
    d = dict(start=1, new_sample=1, hit=1, hit_ground=0, last_bounce=0,
             terminate=0, name="obj", hit_addr=0, r=200, g=100, b=50,
             mat=0, strength=0)
    d.update(kw)
    return Object(**d)

def gnd_case(**kw):
    d = dict(start=1, new_sample=1, hit=1, hit_ground=1, last_bounce=0,
             terminate=0, name="gnd", ray_o_x=0, ray_o_y=0, ray_o_z=0,
             gnd_a_r=200, gnd_a_g=100, gnd_a_b=50,
             gnd_b_r=20, gnd_b_g=40, gnd_b_b=60)
    d.update(kw)
    return Ground(**d)

def sky_case(**kw):
    d = dict(start=1, new_sample=1, hit=0, hit_ground=0, last_bounce=0,
             terminate=1, name="sky", ray_dir_x=0, ray_dir_y=0,
             ray_dir_z=8192, hor_r=200, hor_g=150, hor_b=100,
             top_r=50, top_g=80, top_b=120)
    d.update(kw)
    return Sky(**d)
