// Copyright ***** contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0

module cocotb_mips(
    input  logic                         clk,
    input  logic                         rst,
    input  logic [4:0]                   intr,
    // ibus
    input  logic                         ibus_stall,
    input  logic [63:0]                  ibus_rddata,
    input  logic                         ibus_valid,
    input  logic                         ibus_ready,
    input  logic [63:0]                  ibus_rddata_extra,
    input  logic                         ibus_extra_valid,

    // dbus
    input  logic                         dbus_stall,
    input  logic [63:0]                  dbus_rddata,
    input  logic                         dbus_trans_out,

    // dbus_uncached
    input  logic                         dbus_uncached_stall,
    input  logic [63:0]                  dbus_uncached_rddata,
    input  logic                         dbus_uncached_trans_out
);

  // initialization of bus interfaces
  cpu_ibus_if ibus_if();
	cpu_dbus_if dbus_if();
	cpu_dbus_if dbus_uncached_if();

  logic ibus_read;
  logic [31:0] ibus_address;

  logic dbus_read;
  logic [31:0] dbus_address;
  logic dbus_write;
  logic [31:0] dbus_wrdata;
  logic [3:0] dbus_byteenable;


  always_comb begin
    // So cocotb can access required signals

    // ibus
    ibus_if.slave.stall = ibus_stall;
    ibus_if.slave.rddata = ibus_rddata;
    ibus_if.slave.valid = ibus_valid;
    ibus_if.slave.ready = ibus_ready;
    ibus_if.slave.rddata_extra = ibus_rddata_extra;
    ibus_if.slave.extra_valid = ibus_extra_valid;

    ibus_read = ibus_if.master.read;
    ibus_address = ibus_if.master.address;

    // dbus
    dbus_if.slave.stall = dbus_stall;
    dbus_if.slave.rddata = dbus_rddata;
    dbus_if.slave.trans_out = dbus_trans_out;

    dbus_read = dbus_if.master.read;
    dbus_address = dbus_if.master.address;
    dbus_write = dbus_if.master.write;
    dbus_wrdata = dbus_if.master.wrdata;
    dbus_byteenable = dbus_if.master.byteenable;

    // dbus_uncached
    dbus_uncached_if.slave.stall = dbus_uncached_stall;
    dbus_uncached_if.slave.rddata = dbus_uncached_rddata;
    dbus_uncached_if.slave.trans_out = dbus_uncached_trans_out;
  end

  // initialization of CPU
  cpu_core cpu_core_inst(
      .clk,
      .rst,
      .intr,
      .ibus(ibus_if.master),
  .dbus(dbus_if.master),
  .dbus_uncached(dbus_uncached_if.master)
  );

  `ifdef FORMAL 
    logic [31:0] insn;
    assign insn = cpu_core_inst.instr_fetch_inst.decoder_inst1.instr;

    logic [5:0] op;
    logic [5:0] funct;

    logic [5:0] prev_op;
    logic [5:0] prev_funct;

    logic [4:0] rd;
    logic [4:0] rt;
    logic [4:0] rs;
    logic [25:0] imm;

    logic [4:0] prev_rd;

    logic [31:0] pc;

    logic [3:0] cycle_count;
    
    initial begin 
        assume(rst)
        cycle_count <= 0;
        op <= 0;
        funct <= 0;
        rd <= 0;
        rt <= 0;
        rs <= 0;
        imm <= 0;
        pc <= 0;
        prev_rd <= 0;
        prev_op <= 0;
        prev_funct <= 0;
    end

    always @(posedge clk) begin
        if (cycle_count < 10)
            cycle_count <= cycle_count + 1;
    end

    assume property ( @(posedge clk) cycle_count < 5 |-> rst );
    assume property ( @(posedge clk) cycle_count > 4 |-> ~rst );

    always @(posedge clk) begin
      if(~rst) begin
        op <= insn[31:26];
        funct <= insn[5:0];

        rd <= insn[15:11];
        rt <= insn[20:16];
        rs <= insn[25:21];

        imm <= insn[25:0];

        pc <= cpu_core_inst.instr_fetch_inst.pc_gen.pc;

        prev_rd <= rd;
        prev_op <= op;
        prev_funct <= funct;

        if(op == 6'b000000) begin: RIstruction
          if(funct == 6'b100000) begin: ADD
            seen: cover (1);
            zero_dst: cover (rd == 0);
            same_src: cover (rt == rs);
            zero_src: cover (rt == 0 || rs == 0);

            raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
            raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
            raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
            raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
            raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
            raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
            raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
            raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
            raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
            raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

            raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end else if(funct == 6'b100010) begin: SUB
            seen: cover (1);
            zero_dst: cover (rd == 0);
            same_src: cover (rt == rs);
            zero_src: cover (rt == 0 || rs == 0);

            raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
            raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
            raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
            raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
            raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
            raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
            raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
            raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
            raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
            raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

            raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end else if(funct == 6'b001111) begin: SLL
            seen: cover (1);
            zero_dst: cover (rd == 0);
            same_src: cover (rt == rs);
            zero_src: cover (rt == 0 || rs == 0);

            raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
            raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
            raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
            raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
            raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
            raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
            raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
            raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
            raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
            raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

            raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end else if(funct == 6'b101010) begin: SLT
            seen: cover (1);
            zero_dst: cover (rd == 0);
            same_src: cover (rt == rs);
            zero_src: cover (rt == 0 || rs == 0);

            raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
            raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
            raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
            raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
            raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
            raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
            raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
            raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
            raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
            raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

            raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end else if(funct == 6'b101011) begin: SLTU
            seen: cover (1);
            zero_dst: cover (rd == 0);
            same_src: cover (rt == rs);
            zero_src: cover (rt == 0 || rs == 0);

            raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
            raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
            raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
            raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
            raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
            raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
            raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
            raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
            raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
            raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

            raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end else if(funct == 6'b100110) begin: XOR
            seen: cover (1);
            zero_dst: cover (rd == 0);
            same_src: cover (rt == rs);
            zero_src: cover (rt == 0 || rs == 0);

            raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
            raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
            raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
            raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
            raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
            raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
            raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
            raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
            raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
            raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

            raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end else if(funct == 6'b000010) begin: SRL
            seen: cover (1);
            zero_dst: cover (rd == 0);
            same_src: cover (rt == rs);
            zero_src: cover (rt == 0 || rs == 0);

            raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
            raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
            raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
            raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
            raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
            raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
            raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
            raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
            raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
            raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

            raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end else if(funct == 6'b000011) begin: SRA
            seen: cover (1);
            zero_dst: cover (rd == 0);
            same_src: cover (rt == rs);
            zero_src: cover (rt == 0 || rs == 0);

            raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
            raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
            raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
            raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
            raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
            raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
            raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
            raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
            raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
            raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

            raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end else if(funct == 6'b100101) begin: OR
            seen: cover (1);
            zero_dst: cover (rd == 0);
            same_src: cover (rt == rs);
            zero_src: cover (rt == 0 || rs == 0);

            raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
            raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
            raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
            raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
            raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
            raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
            raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
            raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
            raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
            raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

            raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end else if(funct == 6'b100100) begin: AND
            seen: cover (1);
            zero_dst: cover (rd == 0);
            same_src: cover (rt == rs);
            zero_src: cover (rt == 0 || rs == 0);

            raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
            raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
            raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
            raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
            raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
            raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
            raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
            raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
            raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
            raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

            raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end
        end else if(op == 6'b000011) begin: JAL
          seen: cover (1);
          br_backwards: cover (pc[27:0] > (imm << 2));
          br_forwards: cover (pc[27:0] < (imm << 2));

          
        end else if(op == 6'b101011 || op == 6'b101001 || op == 6'b101000) begin: IIstruction
          if(op[2:0] == 3'b000) begin: SB
          seen: cover (1);
          same_src: cover (rt == rs);
          zero_src: cover (rt == 0 || rs == 0);

          raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
          raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
          raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
          raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
          raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
          raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
          raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
          raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
          raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
          raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

          raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end else if(op[2:0] == 3'b001) begin: SH
          seen: cover (1);
          same_src: cover (rt == rs);
          zero_src: cover (rt == 0 || rs == 0);

          raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
          raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
          raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
          raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
          raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
          raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
          raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
          raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
          raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
          raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

          raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end else if (op[2:0] == 3'b011) begin: SW
          seen: cover (1);
          same_src: cover (rt == rs);
          zero_src: cover (rt == 0 || rs == 0);

          raw_ADD: cover (prev_op == 6'b000000 && prev_funct == 'b100000 && (prev_rd == rs || prev_rd == rt));
          raw_SUB: cover (prev_op == 6'b000000 && prev_funct == 'b100010 && (prev_rd == rs || prev_rd == rt));
          raw_SLL: cover (prev_op == 6'b000000 && prev_funct == 'b001111 && (prev_rd == rs || prev_rd == rt));
          raw_SLT: cover (prev_op == 6'b000000 && prev_funct == 'b101010 && (prev_rd == rs || prev_rd == rt));
          raw_SLTU: cover (prev_op == 6'b000000 && prev_funct == 'b101011 && (prev_rd == rs || prev_rd == rt));
          raw_XOR: cover (prev_op == 6'b000000 && prev_funct == 'b100110 && (prev_rd == rs || prev_rd == rt));
          raw_SRL: cover (prev_op == 6'b000000 && prev_funct == 'b000010 && (prev_rd == rs || prev_rd == rt));
          raw_SRA: cover (prev_op == 6'b000000 && prev_funct == 'b000011 && (prev_rd == rs || prev_rd == rt));
          raw_OR: cover (prev_op == 6'b000000 && prev_funct == 'b100101 && (prev_rd == rs || prev_rd == rt));
          raw_AND: cover (prev_op == 6'b000000 && prev_funct == 'b100100 && (prev_rd == rs || prev_rd == rt));

          raw_JAL: cover (prev_op == 6'b101000 && (31 == rs || 31 == rt));
          end
        end
      end
    end
  `endif
endmodule
