// Copyright ***** contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0

module stride_detector #(parameter MAX_STRIDE_WIDTH=5) (
  input clk_i,
  input rst_ni,

  input logic [31:0] value_i,
  input logic        valid_i,

  output logic [MAX_STRIDE_WIDTH-1:0] stride_1_o,
  output logic                        stride_1_valid_o,
  output logic [MAX_STRIDE_WIDTH-1:0] stride_2_o,
  output logic                        stride_2_valid_o
);

  typedef enum logic {
    STATE_SECOND_STRIDE,
    STATE_FIRST_STRIDE
  } state_e;

  state_e stride_2_state_q, stride_2_state_d;

  logic [1:0] stride_1_confidence_d, stride_1_confidence_q;

  logic [1:0] stride_2_confidence_d[2], stride_2_confidence_q[2];

  logic [31:0]                 last_value;
  logic [MAX_STRIDE_WIDTH-1:0] stride_1_d, stride_2_d[2];
  logic [MAX_STRIDE_WIDTH-1:0] stride_1_q, stride_2_q[2];
  logic [32:0]                 incoming_stride_full;
  logic [MAX_STRIDE_WIDTH-1:0] incoming_stride;
  logic                        incoming_stride_overflow;

  assign incoming_stride_full = value_i - last_value;

  assign incoming_stride_overflow =
    incoming_stride_full[MAX_STRIDE_WIDTH-1] ? ~&incoming_stride_full[32:MAX_STRIDE_WIDTH] :
                                                |incoming_stride_full[32:MAX_STRIDE_WIDTH];

  assign incoming_stride = incoming_stride_full[MAX_STRIDE_WIDTH-1:0];

  always_comb begin
    stride_1_confidence_d = stride_1_confidence_q;
    stride_1_d            = stride_1_q;

    if (valid_i) begin
      if ((incoming_stride == stride_1_q) && !incoming_stride_overflow) begin
        if (stride_1_confidence_q < 2'b11) begin
          stride_1_confidence_d = stride_1_confidence_q + 2'b1;
        end
      end else if (stride_1_confidence_q > 0) begin
        stride_1_confidence_d = stride_1_confidence_q - 2'b1;
      end else begin
        stride_1_d = incoming_stride;
      end
    end
  end

  always_comb begin
    stride_2_d[0] = stride_2_q[0];
    stride_2_d[1] = stride_2_q[1];

    stride_2_confidence_d[0] = stride_2_confidence_q[0];
    stride_2_confidence_d[1] = stride_2_confidence_q[1];

    stride_2_state_d = stride_2_state_q;

    if (valid_i) begin
      case (stride_2_state_q)
        STATE_FIRST_STRIDE: begin
          if ((incoming_stride == stride_2_q[0]) && !incoming_stride_overflow) begin
            if (stride_2_confidence_q[0] < 2'b11) begin
              stride_2_confidence_d[0] = stride_2_confidence_q[0] + 2'b1;
            end
          end else if (stride_2_confidence_q[0] > 0) begin
              stride_2_confidence_d[0] = stride_2_confidence_q[0] - 2'b1;
          end else begin
            stride_2_d[0] = incoming_stride;
          end

          stride_2_state_d = STATE_SECOND_STRIDE;
        end
        STATE_SECOND_STRIDE: begin
          if ((incoming_stride == stride_2_q[1]) && !incoming_stride_overflow) begin
            if (stride_2_confidence_q[1] < 2'b11) begin
              stride_2_confidence_d[1] = stride_2_confidence_q[1] + 2'b1;
            end
          end else if (stride_2_confidence_q[1] > 0) begin
            stride_2_confidence_d[1] = stride_2_confidence_q[1] - 2'b1;
          end else begin
            stride_2_d[1] = incoming_stride;
          end

          stride_2_state_d = STATE_FIRST_STRIDE;
        end
      endcase
    end
  end

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      last_value <= '0;
    end else begin
      if (valid_i) begin
        last_value <= value_i;
      end
    end
  end

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      stride_1_q            <= '0;
      stride_1_confidence_q <= '0;
    end else begin
      stride_1_q            <= stride_1_d;
      stride_1_confidence_q <= stride_1_confidence_d;
    end
  end

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      stride_2_q[0] <= '0;
      stride_2_q[1] <= '0;

      stride_2_confidence_q[0] <= '0;
      stride_2_confidence_q[1] <= '0;

      stride_2_state_q <= STATE_FIRST_STRIDE;
    end else begin
      stride_2_q[0] <= stride_2_d[0];
      stride_2_q[1] <= stride_2_d[1];

      stride_2_confidence_q[0] <= stride_2_confidence_d[0];
      stride_2_confidence_q[1] <= stride_2_confidence_d[1];

      stride_2_state_q <= stride_2_state_d;
    end
  end

  assign stride_1_valid_o = (stride_1_confidence_q == 2'b11) || (stride_2_confidence_q[0] == 2'b11);
  assign stride_1_o = stride_1_confidence_q == 2'b11 ? stride_1_q : stride_2_q[0];

  assign stride_2_valid_o = (stride_2_confidence_q[0] == 2'b11) &&
                            (stride_2_confidence_q[1] == 2'b11) &&
                            (stride_1_confidence_q != 2'b11);

  assign stride_2_o = stride_2_q[1];

`ifdef FORMAL
  parameter NUM_STRIDES = 32;
  parameter STRIDE_MIN = -16;
  parameter STRIDE_MAX = 15;

  integer i;
  integer j;

  logic [31:0] values [31:0];
  integer i;
  integer x;
  logic x_valid;
  integer y;
  logic y_valid;

  integer x_prev;
  logic x_prev_valid;
  integer y_prev;
  logic y_prev_valid;

  logic sample_single_stride_coverage;
  logic sample_double_stride_coverage;
  logic no_strides;

  logic prev_no_stride = 0;
  logic prev_single_stride = 0;
  logic prev_double_stride = 0;

  integer x_reg;
  integer y_reg;

  integer counter;

  // check latest strides
  always @(*) begin
    for (i = 0; i < NUM_STRIDES; i++) begin: stride_values
      stride_1_seen: cover (stride_1_valid_o & ~(stride_2_valid_o) & (stride_1_o == i));
      for (j = 0; j < NUM_STRIDES; j++) begin: stride_values_2
        stride_2_seen: cover (stride_1_valid_o & stride_2_valid_o & (stride_1_o == i) & (stride_2_o == j));
      end
    end

    single_stride_n_overflow: cover (x_reg < STRIDE_MIN & sample_single_stride_coverage);
    single_stride_p_overflow: cover (x_reg > STRIDE_MAX & sample_single_stride_coverage);
    
    no_stride_to_single: cover ((x_reg >= STRIDE_MIN) & (x_reg <= STRIDE_MAX) & (prev_no_stride) & sample_single_stride_coverage);
    double_stride_to_single: cover ((x_reg >= STRIDE_MIN) & (x_reg <= STRIDE_MAX) & (prev_double_stride) & sample_single_stride_coverage);


    double_stride_nn_overflow: cover ((x_reg < STRIDE_MIN) & (y_reg < STRIDE_MIN) & sample_double_stride_coverage);
    double_stride_np_overflow: cover ((x_reg < STRIDE_MIN) & (y_reg > STRIDE_MAX) & sample_double_stride_coverage);
    double_stride_pn_overflow: cover ((x_reg > STRIDE_MAX) & (y_reg < STRIDE_MIN) & sample_double_stride_coverage);
    double_stride_pp_overflow: cover ((x_reg > STRIDE_MAX) & (y_reg > STRIDE_MAX) & sample_double_stride_coverage);

    no_stride_to_double: cover ((x_reg >= STRIDE_MIN) & (x_reg <= STRIDE_MAX) & (y_reg >= STRIDE_MIN) & (y_reg <= STRIDE_MAX) & (prev_no_stride) & sample_double_stride_coverage);
    single_stride_to_double: cover ((x_reg >= STRIDE_MIN) & (x_reg <= STRIDE_MAX) & (y_reg >= STRIDE_MIN) & (y_reg <= STRIDE_MAX) & (prev_single_stride) & sample_double_stride_coverage);

  end

  always @(value_i) begin
    if(valid_i) begin

      

      for (i = 0; i < 31; i++) begin
        values[i] = values[i+1];
      end
      values[31] = value_i;

      // current
      x = values[31] - values[30];
      x_valid = 1;

      y = values[30] - values[29];
      y_valid = 1;

      for (i = 29; i > 16; i=i-2) begin
        if(~((values[i] - values[i-1]) == x)) begin
          x_valid = 0;
        end
      end

      for (i = 28; i > 16; i=i-2) begin
        if(~((values[i] - values[i-1]) == y)) begin
          y_valid = 0;
        end
      end

      if(x_valid & y_valid & (x == y)) begin
        sample_single_stride_coverage = 1;
        sample_double_stride_coverage = 0;
      end else if(x_valid & y_valid & ~(x == y)) begin
        sample_double_stride_coverage = 1;
        sample_single_stride_coverage = 0;
      end

      // previous
      x_prev = values[15] - values[14];
      x_prev_valid = 1;

      y_prev = values[14] - values[13];
      y_prev_valid = 1;

      for (i = 13; i > 0; i=i-2) begin
        if(~((values[i] - values[i-1]) == x_prev)) begin
          x_prev_valid = 0;
        end
      end

      for (i = 12; i > 0; i=i-2) begin
        if(~((values[i] - values[i-1]) == y_prev)) begin
          y_prev_valid = 0;
        end
      end

      if((x_prev >= STRIDE_MIN) & (x_prev <= STRIDE_MAX) & x_prev_valid & y_prev_valid & (x_prev == y_prev)) begin
        prev_no_stride = 0;
        prev_single_stride = 1;
        prev_double_stride = 0;
      end else if((x_prev >= STRIDE_MIN) & (x_prev <= STRIDE_MAX) & (y_prev >= STRIDE_MIN) & (y_prev <= STRIDE_MAX) & x_prev_valid & y_prev_valid & ~(x_prev == y_prev)) begin
        prev_no_stride = 0;
        prev_single_stride = 0;
        prev_double_stride = 1;
      end else begin
        prev_no_stride = 1;
        prev_single_stride = 0;
        prev_double_stride = 0;
      end
      x_reg = x;
      y_reg = y;
      end
    end
`endif
endmodule

