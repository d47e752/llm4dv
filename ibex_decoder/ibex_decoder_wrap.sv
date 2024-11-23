// Copyright ***** contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0

module ibex_decoder_wrap(input [31:0] insn_i);
  ibex_decoder#(
    .BranchTargetALU(1)
  ) u_decoder (
    .clk_i               (1'b0),
    .rst_ni              (1'b0),
    .branch_taken_i      (1'b1),
    .instr_first_cycle_i (1'b1),
    .instr_rdata_i       (insn_i),
    .instr_rdata_alu_i   (insn_i),
    .illegal_c_insn_i    (1'b0)
  );

  `ifdef FORMAL
    import ibex_pkg::*;

    integer i;
    integer j;

    logic [6:0] operations [3:0];

    logic [6:0] alu_op_seen;
    logic [6:0] alu_imm_op_seen;
    logic illegal_insn_seen;
    logic [4:0] write_reg_seen;
    logic [4:0] read_reg_a_seen;
    logic [4:0] read_reg_b_seen;
    logic [1:0] load_seen;
    logic [1:0] store_seen;

    logic alu_op_seen_changed;
    logic alu_imm_op_seen_changed;
    logic write_reg_seen_changed;
    logic read_reg_a_seen_changed;
    logic read_reg_b_seen_changed;
    logic load_seen_changed;
    logic store_seen_changed;

    always_comb begin
      operations[0] = ALU_ADD;
      operations[1] = ALU_SUB;
      operations[2] = ALU_XOR;
      operations[3] = ALU_OR;
      operations[4] = ALU_AND;
      operations[5] = ALU_SRA;
      operations[6] = ALU_SRL;
      operations[7] = ALU_SLL;
      operations[8] = ALU_SLT;
      operations[9] = ALU_SLTU;

      alu_op_seen_changed = 0;
      alu_imm_op_seen_changed = 0;
      write_reg_seen_changed = 0;
      read_reg_a_seen_changed = 0;
      read_reg_b_seen_changed = 0;
      load_seen_changed = 0;
      store_seen_changed = 0;

      if(u_decoder.alu_op_b_mux_sel_o == OP_B_IMM) begin
        alu_imm_op_seen = u_decoder.alu_operator_o;
        alu_imm_op_seen_changed = 1;
      end else begin
        alu_op_seen = u_decoder.alu_operator_o;
        alu_op_seen_changed = 1;
      end

      illegal_insn_seen = u_decoder.illegal_insn_o;

      if (u_decoder.rf_we_o != 0) begin
        write_reg_seen = u_decoder.rf_waddr_o;
        write_reg_seen_changed = 1;
      end
      if (u_decoder.rf_ren_a_o != 0) begin
        read_reg_a_seen = u_decoder.rf_raddr_a_o;
        read_reg_a_seen_changed = 1;
      end
      if (u_decoder.rf_ren_b_o != 0) begin
        read_reg_b_seen = u_decoder.rf_raddr_b_o;
        read_reg_b_seen_changed = 1;
      end

      if (u_decoder.data_we_o != 0) begin
          store_seen = u_decoder.data_type_o;
          store_seen_changed = 1;
      end else begin
          load_seen = u_decoder.data_type_o;
          load_seen_changed = 1;
      end

      illegal_insn: cover(illegal_insn_seen);

      if(read_reg_a_seen_changed || read_reg_b_seen_changed || write_reg_seen_changed) begin
        for (i = 0; i < 31; i++) begin
          read_reg_a_seen_cov: cover (read_reg_a_seen == i);
          read_reg_b_seen_cov: cover (read_reg_b_seen == i);
          write_reg_seen_cov: cover (write_reg_seen == i);
        end
      end

      if(read_reg_a_seen_changed || read_reg_b_seen_changed || write_reg_seen_changed || alu_op_seen_changed) begin
        for (i = 0; i < 10; i++) begin
          alu_op_seen_cov: cover (alu_op_seen == operations[i]);
          if(alu_op_seen == operations[i]) begin
            for (j = 0; j < 31; j++) begin
              alu_ops_x_read_reg_a: cover (read_reg_a_seen == j);
              alu_ops_x_read_reg_b: cover (read_reg_b_seen == j);
              alu_ops_x_write_reg: cover (write_reg_seen == j);
            end
          end
        end
      end

      if(read_reg_a_seen_changed || write_reg_seen_changed || alu_imm_op_seen_changed) begin
        if (|alu_imm_op_seen) begin
          for (i = 0; i < 10; i++) begin
            alu_imm_ops_cov: cover (alu_imm_op_seen == operations[i]);
            if(alu_op_seen == operations[i]) begin
              for (j = 0; j < 31; j++) begin
                alu_imm_ops_x_read_reg_a: cover (read_reg_a_seen == j);
                alu_imm_ops_x_write_reg: cover (write_reg_seen == j);
              end
            end
          end
        end
      end

      if(read_reg_a_seen_changed || write_reg_seen_changed || load_seen_changed) begin
        for (i = 0; i < 3; i++) begin
          load_ops_cov: cover (load_seen == i)
          for (j = 0; j < 31; j++) begin
            load_ops_x_read_reg_a: cover (read_reg_a_seen == j);
            load_ops_x_write_reg: cover (write_reg_seen == j);
          end
        end
      end

      if(read_reg_a_seen_changed || write_reg_seen_changed || store_seen_changed) begin
        for (i = 0; i < 3; i++) begin
          store_ops_cov: cover (store_seen == i)
          for (j = 0; j < 31; j++) begin
            store_ops_x_read_reg_a: cover (read_reg_a_seen == j);
            store_ops_x_read_reg_b: cover (write_reg_seen == j);
          end
        end
      end
    end
  `endif
endmodule
