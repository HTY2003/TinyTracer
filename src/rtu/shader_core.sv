// Shader Core: keeps the attenuation and makes the sample colour when the path ends.
module shader_core #(
    parameter ADDR_WIDTH = 9,
    parameter WLEN       = 16,
    parameter DATA_WIDTH = 16
) (
    input  logic                   clk,
    input  logic                   rst_n,        // global reset, active low

    // RTU FSM <-> Shader Core
    input  logic                   new_sample,   // 1-cycle pulse: att = 255
    input  logic                   start,        // 1-cycle pulse: shade one segment
    input  logic                   hit,          // from the IU: 1 = object or ground hit, 0 = sky
    input  logic                   hit_ground,   // from the IU: 1 = the hit is the ground
    input  logic [ADDR_WIDTH-1:0]  hit_addr,     // from the IU: SRAM address of the hit object's w0
    input  logic                   last_bounce,  // 1 when the bounce count is 8: a surface hit gives black
    output logic                   done,         // 1-cycle pulse: the outputs below are valid
    output logic                   path_end,     // 1 = the sample is finished (sky, glow or black)
    output logic [1:0]             material,     // path goes on: 00 matte, 01 mirror, 10 glass. This is FED TO Ray Generator so it knows the type of bounce.
    output logic [35:0]            sample,       // R [35:24], G [23:12], B [11:0], valid with path_end = 1

    // Ray and scene, from RTU registers (must not change from start to done)
    input  logic [47:0]            ray_origin,   // hit point, POS (Q9.7): z [47:32], y [31:16], x [15:0]
    input  logic [47:0]            ray_dir,      // D, DIR (Q2.14), length 1: z [47:32], y [31:16], x [15:0]
    input  logic [23:0]            sky_horizon,  // R [23:16], G [15:8], B [7:0]
    input  logic [23:0]            sky_top,      // same order
    input  logic [23:0]            ground_a,     // checker colours, same order
    input  logic [23:0]            ground_b,

    // SRAM reads (the RTU passes them on to the SRAM Controller)
    output logic [ADDR_WIDTH-1:0]  sram_addr,    // register: address of the word to read
    output logic                   sram_rd,      // 1-cycle pulse: read the word at sram_addr
    input  logic [DATA_WIDTH-1:0]  sram_data,    // SRAM word, shared by all RTU sub-blocks
    input  logic                   sram_valid,   // 1 = sram_data holds the word asked for

    // Macro-ops (the RTU passes them on to the Decode Unit; the macro_if client signals)
    output logic                   req_valid,    // 1 = req_op holds a macro-op
    output logic [101:0]           req_op,       // fmt [101], u [100:53], v [52:5], opcode [4:0]
    input  logic                   req_ready,    // 1 = the Decode Unit takes req_op in this cycle
    input  logic                   resp_valid,   // 1 = resp_result holds the result
    input  logic [3*WLEN-1:0]      resp_result,  // z [47:32], y [31:16], x [15:0]
    output logic                   resp_ready    // 1 = the SC takes resp_result in this cycle
);

localparam SCRATCH_BITS     = 40;
localparam STATE_BITS       = 5;

typedef enum logic [STATE_BITS-1:0] {
    STATE_IDLE      ,
    STATE_OBJ1      ,
    STATE_OBJ1W     ,
    STATE_OBJ2      ,
    STATE_OBJ2W     ,
    STATE_OBJ3      ,
    STATE_OBJ3W     ,
    STATE_SUR       ,
    STATE_SURW      ,
    STATE_SKY1      ,
    STATE_SKY1W     ,
    STATE_SKY2      ,
    STATE_SKY2W     ,
    STATE_SKY3      ,
    STATE_SKY3W     ,
    STATE_SKY4      ,
    STATE_SKY4W     ,
    STATE_GLO1      ,
    STATE_GLO1W     ,
    STATE_GLO2      ,
    STATE_GLO2W     ,
    STATE_END_SAMP  ,
    STATE_END_SUR
} state_t;

// registers
state_t                   state_r;
logic [SCRATCH_BITS-1:0]  scratch_r;
logic [23:0]              att_r;
// wires
logic                     obj1_to_zro;
logic                     obj3_to_glo;
logic [23:0]              idle_gnd_col_ns;
logic [23:0]              sur_att_ns;
logic [7:0]               tmp1_red;
logic [7:0]               tmp1_grn;
logic [7:0]               tmp1_blu;
logic [7:0]               tmp2_red;
logic [7:0]               tmp2_grn;
logic [7:0]               tmp2_blu;
logic [8:0]               tmp1_red_p1;
logic [8:0]               tmp1_grn_p1;
logic [8:0]               tmp1_blu_p1;
logic [47:0]              tmp1;
logic [47:0]              tmp2;
logic [47:0]              tmp1_p1;

// State transition wires
assign obj1_to_zro        = ~&sram_data[1:0] & last_bounce;
assign obj3_to_glo        = &scratch_r[25:24];

// Next-state wires
assign idle_gnd_col_ns    = (ray_origin[9] ^ ray_origin[25]) ? ground_a : ground_b;
assign sur_att_ns         = {resp_result[40:33], resp_result[24:17], resp_result[8:1]};

// Macro-op operand wires
assign tmp1_red           = (state_r == STATE_SUR) ? scratch_r[23:16] : att_r[23:16];
assign tmp1_grn           = (state_r == STATE_SUR) ? scratch_r[15:8]  : att_r[15:8];
assign tmp1_blu           = (state_r == STATE_SUR) ? scratch_r[7:0]   : att_r[7:0];
assign tmp2_red           = (state_r == STATE_SUR) ? att_r[23:16] : scratch_r[23:16];
assign tmp2_grn           = (state_r == STATE_SUR) ? att_r[15:8]  : scratch_r[15:8];
assign tmp2_blu           = (state_r == STATE_SUR) ? att_r[7:0]   : scratch_r[7:0];
assign tmp1_red_p1        = tmp1_red + 1;
assign tmp1_grn_p1        = tmp1_grn + 1;
assign tmp1_blu_p1        = tmp1_blu + 1;
assign tmp1               = {8'b0, tmp1_red, 8'b0, tmp1_grn, 8'b0, tmp1_blu};
assign tmp2               = {8'b0, tmp2_red, 8'b0, tmp2_grn, 8'b0, tmp2_blu};
assign tmp1_p1            = {7'b0, tmp1_red_p1, 7'b0, tmp1_grn_p1, 7'b0, tmp1_blu_p1};

// Output wires
assign material           = scratch_r[25:24];
assign sample             = scratch_r[35:0];
assign path_end           = state_r == STATE_END_SAMP;
assign done               = state_r == STATE_END_SUR || state_r == STATE_END_SAMP;

// SRAM read wires
// TODO: Check assumption that addr does not matter once rd has been pulsed
assign sram_addr          = hit_addr + (state_r == STATE_OBJ1 ? 2 :
                                        state_r == STATE_OBJ2 ? 1 :
                                                                0);
assign sram_rd            = ( (state_r == STATE_OBJ1) ||
                              (state_r == STATE_OBJ2) ||
                              (state_r == STATE_OBJ3) );

// Macro-op interface wires
// TODO: Add entries for more states
assign req_valid          = state_r == STATE_SUR;
assign resp_ready         = '1;

always_comb begin
  case (state_r)
    STATE_SUR: req_op = {1'b0, tmp1_p1, tmp2, 5'b10011};
    default:   req_op = 'x;
  endcase
end

// State register
// TODO: Add entries for more states
always_ff @(posedge clk or negedge rst_n) begin
  if (~rst_n) begin
    state_r <= STATE_IDLE;
  end
  else begin
    case (state_r)
      STATE_IDLE:
        casez ({start, hit, hit_ground, last_bounce})
          4'b10??:  state_r <= STATE_SKY1;          // Sky sample
          4'b110?:  state_r <= STATE_OBJ1;          // Object surface
          4'b1111:  state_r <= STATE_END_SAMP;      // Zero sample
          4'b1110:  state_r <= STATE_SUR;           // Ground surface
          default:;
        endcase

      STATE_OBJ1:   state_r <= STATE_OBJ1W;
      STATE_OBJ1W:
        case ({sram_valid, obj1_to_zro})
          2'b11:    state_r <= STATE_END_SAMP;      // Zero sample
          2'b10:    state_r <= STATE_OBJ2;          // Object surface or glow sample
          default:;
        endcase

      STATE_OBJ2:                   state_r <= STATE_OBJ2W;
      STATE_OBJ2W:  if (sram_valid) state_r <= STATE_OBJ3;
      STATE_OBJ3:                   state_r <= STATE_OBJ3W;
      STATE_OBJ3W: 
        case ({sram_valid, obj3_to_glo})
          2'b11:    state_r <= STATE_GLO1;          // Glow sample
          2'b10:    state_r <= STATE_SUR;           // Object surface
          default:;
        endcase

      STATE_SUR:    if (req_ready)  state_r <= STATE_SURW;
      STATE_SURW:   if (resp_valid) state_r <= STATE_END_SUR;
      STATE_END_SUR:                state_r <= STATE_IDLE;
      STATE_END_SAMP:               state_r <= STATE_IDLE;
      default:;
    endcase
  end
end

// Scratch register
// TODO: Add entries for more states
always_ff @(posedge clk or negedge rst_n) begin
  if (~rst_n) begin
    scratch_r <= '0;
  end
  else begin
    case (state_r)
      STATE_IDLE:
        casez ({start, hit, hit_ground, last_bounce})
          4'b1111:  scratch_r[35:0]   <= '0;                        // Zero sample
          4'b1110:  scratch_r[25:0]   <= {2'b00, idle_gnd_col_ns};  // Ground surface
          default:;
        endcase

      STATE_OBJ1W:
        case ({sram_valid, obj1_to_zro})
          2'b11:    scratch_r[35:0]   <= '0;                        // Zero sample
          default:  scratch_r[39:24]  <= sram_data[15:0];           // Read W2
        endcase

      STATE_OBJ2W:  scratch_r[23:8]   <= sram_data[15:0];           // Read W1
      STATE_OBJ3W:  scratch_r[7:0]    <= sram_data[15:8];           // Read W0
      default:;
    endcase
  end
end

// Attenuation register
// TODO: Add entries for more states
always_ff @(posedge clk or negedge rst_n) begin
  if (~rst_n) begin
    att_r <= '1;
  end
  else begin
    case (state_r)
      STATE_IDLE: if (start & new_sample) att_r <= '1;
      STATE_SURW: if (resp_valid)         att_r <= sur_att_ns;
      default:;
    endcase
  end
end

endmodule
