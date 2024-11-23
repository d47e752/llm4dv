# Copyright ***** contributors.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0
# Makefile

rwildcard=$(foreach d,$(wildcard $(1:=/*)),$(call rwildcard,$d,$2) $(filter $(subst *,%,$2),$d))

# defaults
SIM ?= verilator
TOPLEVEL_LANG ?= verilog
VERILOG_SOURCES += $(call rwildcard,$(PWD),*.sv *.svh *.v)


# use VHDL_SOURCES for VHDL files

# TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file
TOPLEVEL = cocotb_mips
# MODULE is the basename of the Python test file
MODULE = cocotb_mips

#--trace-fst --trace-structs \

EXTRA_ARGS +=  \
  +incdir+$(PWD)/src/ \
  -DSYNTHESIS=1 \
  -DRVFI=1 \
	--trace-fst \
  --trace-structs \
  --timing \
  -Wno-BLKANDNBLK \
	-Wno-fatal \
  -CFLAGS "-std=c++14 -Wall -O3"


# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
