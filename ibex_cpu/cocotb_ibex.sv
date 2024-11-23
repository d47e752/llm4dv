// Copyright ***** contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0

module cocotb_ibex(
  input  logic                         clk_i,
  input  logic                         rst_ni,

  // Instruction memory interface
  output logic                         instr_req_o,
  input  logic                         instr_gnt_i,
  input  logic                         instr_rvalid_i,
  output logic [31:0]                  instr_addr_o,
  input  logic [31:0]                  instr_rdata_i,

  // Data memory interface
  output logic                         data_req_o,
  input  logic                         data_gnt_i,
  input  logic                         data_rvalid_i,
  output logic                         data_we_o,
  output logic [3:0]                   data_be_o,
  output logic [31:0]                  data_addr_o,
  output logic [31:0]                  data_wdata_o,
  input  logic [31:0]                  data_rdata_i
);
  parameter bit                 SecureIbex               = 1'b0;
  parameter bit                 ICacheScramble           = 1'b0;
  parameter bit                 PMPEnable                = 1'b0;
  parameter int unsigned        PMPGranularity           = 0;
  parameter int unsigned        PMPNumRegions            = 4;
  parameter int unsigned        MHPMCounterNum           = 0;
  parameter int unsigned        MHPMCounterWidth         = 40;
  parameter bit                 RV32E                    = 1'b0;
  // parameter ibex_pkg::rv32m_e   RV32M                    = ibex_pkg::RV32MFast;
  // parameter ibex_pkg::rv32b_e   RV32B                    = ibex_pkg::RV32BNone;
  // parameter ibex_pkg::regfile_e RegFile                  = ibex_pkg::RegFileFF;
  parameter bit                 BranchTargetALU          = 1'b0;
  parameter bit                 WritebackStage           = 1'b0;
  parameter bit                 ICache                   = 1'b0;
  parameter bit                 DbgTriggerEn             = 1'b0;
  parameter bit                 ICacheECC                = 1'b0;
  parameter bit                 BranchPredictor          = 1'b0;

  ibex_top_tracing u_top (
    .clk_i,
    .rst_ni,

    .test_en_i              ('b0),
    .scan_rst_ni            (1'b1),
    // .ram_cfg_i              ('b0),

    .hart_id_i              (32'b0),
    // First instruction executed is at 0x0 + 0x80
    .boot_addr_i            (32'h00100000),

    .instr_req_o,
    .instr_gnt_i,
    .instr_rvalid_i,
    .instr_addr_o,
    .instr_rdata_i,
    .instr_rdata_intg_i     ('0),
    .instr_err_i            (1'b0),

    .data_req_o,
    .data_gnt_i,
    .data_rvalid_i,
    .data_we_o,
    .data_be_o,
    .data_addr_o,
    .data_wdata_o,
    .data_wdata_intg_o      (),
    .data_rdata_i,
    .data_rdata_intg_i      ('0),
    .data_err_i             (1'b0),

    .irq_software_i         (1'b0),
    .irq_timer_i            (1'b0),
    .irq_external_i         (1'b0),
    .irq_fast_i             (15'b0),
    .irq_nm_i               (1'b0),

    .scramble_key_valid_i   ('0),
    .scramble_key_i         ('0),
    .scramble_nonce_i       ('0),
    .scramble_req_o         (),

    .debug_req_i            ('b0),
    // .crash_dump_o           (),
    .double_fault_seen_o    (),

    .fetch_enable_i         (ibex_pkg::IbexMuBiOn),
    .alert_minor_o          (),
    .alert_major_internal_o (),
    .alert_major_bus_o      (),
    .core_sleep_o           ()
  );

    `ifdef FORMAL 
    logic [31:0] insn;
    assign insn = u_top.rvfi_insn;

    logic [6:0] op;
    logic [31:0] funct;

    logic [6:0] prev_op;
    logic [31:0] prev_funct;

    logic [4:0] rd;
    logic [4:0] rs1;
    logic [4:0] rs2;
    logic imm_neg;

    logic [4:0] prev_rd;

    logic [3:0] cycle_count;

    initial begin 
      assume(~rst_ni)
      cycle_count <= 0;
      op <= 0;
      funct <= 0;
      rd <= 0;
      rs1 <= 0;
      rs2 <= 0;
      prev_rd <= 0;
      prev_op <= 0;
      prev_funct <= 0;
    end

    always @(posedge clk_i) begin
      if (cycle_count < 10)
          cycle_count <= cycle_count + 1;
    end

    assume property ( @(posedge clk_i) cycle_count < 5 |-> ~rst_ni );
    assume property ( @(posedge clk_i) cycle_count > 4 |-> rst_ni );


    always @(posedge clk_i) begin
      op <= insn[6:0];
      funct <= insn & 'hFE007000;

      rd <= insn[11:7];
      rs2 <= insn[19:15];
      rs1 <= insn[24:20];

      imm_neg <= insn[31];

      prev_rd <= rd;
      prev_op <= op;
      prev_funct <= funct;

      if(op == 6'b0110011) begin: RIstruction
        if(funct == 'h00000000) begin: ADD
          seen: cover (1);
          zero_dst: cover (rd == 0);
          same_src: cover (rs1 == rs2);
          zero_src: cover (rs1 == 0 || rs2 == 0);

          raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

          raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
        end else if(funct == 'h40000000) begin: SUB
          seen: cover (1);
          zero_dst: cover (rd == 0);
          same_src: cover (rs1 == rs2);
          zero_src: cover (rs1 == 0 || rs2 == 0);

          raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

          raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
        end else if(funct == 'h00001000) begin: SLL
          seen: cover (1);
          zero_dst: cover (rd == 0);
          same_src: cover (rs1 == rs2);
          zero_src: cover (rs1 == 0 || rs2 == 0);

          raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

          raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
        end else if(funct == 'h00002000) begin: SLT
          seen: cover (1);
          zero_dst: cover (rd == 0);
          same_src: cover (rs1 == rs2);
          zero_src: cover (rs1 == 0 || rs2 == 0);

          raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

          raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
        end else if(funct == 'h00003000) begin: SLTU
          seen: cover (1);
          zero_dst: cover (rd == 0);
          same_src: cover (rs1 == rs2);
          zero_src: cover (rs1 == 0 || rs2 == 0);

          raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

          raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
        end else if(funct == 'h00004000) begin: XOR
          seen: cover (1);
          zero_dst: cover (rd == 0);
          same_src: cover (rs1 == rs2);
          zero_src: cover (rs1 == 0 || rs2 == 0);

          raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

          raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
        end else if(funct == 'h00005000) begin: SRL
          seen: cover (1);
          zero_dst: cover (rd == 0);
          same_src: cover (rs1 == rs2);
          zero_src: cover (rs1 == 0 || rs2 == 0);

          raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

          raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
        end else if(funct == 'h40005000) begin: SRA
          seen: cover (1);
          zero_dst: cover (rd == 0);
          same_src: cover (rs1 == rs2);
          zero_src: cover (rs1 == 0 || rs2 == 0);

          raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

          raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
        end else if(funct == 'h00006000) begin: OR
          seen: cover (1);
          zero_dst: cover (rd == 0);
          same_src: cover (rs1 == rs2);
          zero_src: cover (rs1 == 0 || rs2 == 0);

          raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

          raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
        end else if(funct == 'h00007000) begin: AND
          seen: cover (1);
          zero_dst: cover (rd == 0);
          same_src: cover (rs1 == rs2);
          zero_src: cover (rs1 == 0 || rs2 == 0);

          raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
          raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

          raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
        end
      end else if(op == 6'b1101111) begin: JAL
        seen: cover (1);
        zero_dst: cover (rd == 0);
        br_backwards: cover (imm_neg);
        br_forwards: cover (~imm_neg);
      end else if(op == 6'b0100011) begin: SIstruction
      if((insn & 'h00007000) == 'h00000000) begin: SB
        seen: cover (1);
        same_src: cover (rs1 == rs2);
        zero_src: cover (rs1 == 0 || rs2 == 0);

        raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

        raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
      end else if((insn & 'h00007000) == 'h00001000) begin: SH
        seen: cover (1);
        same_src: cover (rs1 == rs2);
        zero_src: cover (rs1 == 0 || rs2 == 0);

        raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

        raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
      end else if((insn & 'h00007000) == 'h00002000) begin: SW
        seen: cover (1);
        same_src: cover (rs1 == rs2);
        zero_src: cover (rs1 == 0 || rs2 == 0);

        raw_ADD: cover (prev_op == 6'b0110011 && prev_funct == 'h00000000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SUB: cover (prev_op == 6'b0110011 && prev_funct == 'h40000000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SLL: cover (prev_op == 6'b0110011 && prev_funct == 'h00001000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SLT: cover (prev_op == 6'b0110011 && prev_funct == 'h00002000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SLTU: cover (prev_op == 6'b0110011 && prev_funct == 'h00003000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_XOR: cover (prev_op == 6'b0110011 && prev_funct == 'h00004000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SRL: cover (prev_op == 6'b0110011 && prev_funct == 'h00005000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_SRA: cover (prev_op == 6'b0110011 && prev_funct == 'h40005000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_OR: cover (prev_op == 6'b0110011 && prev_funct == 'h00006000 && (prev_rd == rs1 || prev_rd == rs2));
        raw_AND: cover (prev_op == 6'b0110011 && prev_funct == 'h00007000 && (prev_rd == rs1 || prev_rd == rs2));

        raw_JAL: cover (prev_op == 6'b1101111 && (prev_rd == rs1 || prev_rd == rs2));
      end
        
      end
    end
  `endif
endmodule
