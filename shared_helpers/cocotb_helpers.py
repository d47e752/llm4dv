import math
from cocotb.triggers import ClockCycles
import time
#================================================================
# drive an input that is a SV struct
def assemble_payload_from_struct(variables):
    payload = 0
    shift_amnt = 0
    for variable in variables:
        payload += variable[0] * (2**shift_amnt)
        shift_amnt += variable[1]
    return payload

# determine what bins have been hit
# coverage_monitor: the coverage monitor used
# sample_condition: only try to determine bin hits if this is high
# signals: the bundle of signals needed to determine coverage hits
# finish_condition: determines when to stop sampling
# duration: whether to measure the number of clock cycles an output is high.
#   duration[0]: the list containing "duration" coverage bins
#   duration[1]: the number the duration count needs to be divided by
#   duration[2]: the duration is measured on signals[duration[2]]
# count_high: whether to measure the max number of signals in the signals bundle that are high at the same time
#   count_high[0]: "rolling" count
#   count_high[1]: the list containing the "max high" coverage bins
# combine: whether there are cross bins of the above mentioned two types of coverage bins
#   combine[0]: type of combination
#   combine[1]: the list containing the "combined" coverage bins
def determine_coverage(coverage_monitor, sample_condition, signals, finish_condition, duration, count_high, combine):
    continue_with_sampling = True
    if(sample_condition):
        if(finish_condition):
            if count_high != None:
                if(count_high[0]):
                    coverage_monitor.max_high -= 1
            if combine != None:
                if combine[0] == 0:
                    combine[1][int(math.ceil(coverage_monitor.duration / duration[1]))][coverage_monitor.max_high] += 1
            if duration != None:
                duration[0][int(math.ceil(coverage_monitor.duration / duration[1]))] += 1
                coverage_monitor.duration = 0
            if count_high != None:
                count_high[1][coverage_monitor.max_high] += 1
                coverage_monitor.max_high = 1
            coverage_monitor.coverage_sampled_event.set()
            continue_with_sampling = False
        else:
            if duration != None:
                if(signals[duration[2]] == '1'):
                    coverage_monitor.duration += 1
            if count_high != None:
                if(not count_high[0]):
                    high_count = signals.count('1')
                    if(high_count > coverage_monitor.max_high):
                        coverage_monitor.max_high = high_count
                else:
                    if(signals[-1*coverage_monitor.max_high] == '1'):
                        coverage_monitor.max_high += 1 # will result in max_high becoming 1 larger than it should be
            continue_with_sampling = True
    return continue_with_sampling

async def do_reset(reset_sig, clock_sig, reset_cycles):
    reset_sig.value = 1
    await ClockCycles(clock_sig, 3)

    reset_sig.value = 0
    await ClockCycles(clock_sig, reset_cycles)

    reset_sig.value = 1

#================================================================