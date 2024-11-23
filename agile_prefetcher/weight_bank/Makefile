# Makefile

# defaults
SIM ?= verilator
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES += $(PWD)/ultraram.v
VERILOG_SOURCES += $(PWD)/ultraram_fifo.sv
VERILOG_SOURCES += $(PWD)/top_pkg.sv
VERILOG_SOURCES += $(PWD)/prefetcher_weight_bank.sv

# use VHDL_SOURCES for VHDL files

# TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file
TOPLEVEL = prefetcher_weight_bank

# MODULE is the basename of the Python test file
MODULE = agile_prefetcher_weight_bank_cocotb

COCOTB_LOG_LEVEL = critical

EXTRA_ARGS += --trace-fst --trace-structs \
	-Wno-fatal -CFLAGS "-std=c++14 -Wall -O3"

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim