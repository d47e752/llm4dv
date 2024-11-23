// distributed under the mit license
// https://opensource.org/licenses/mit-license.php

`timescale 1 ns / 1 ps
`default_nettype none

module async_fifo

    #(
        parameter DSIZE = 8,
        parameter ASIZE = 4,
        parameter FALLTHROUGH = "TRUE" // First word fall-through without latency
    )(
        input  wire             wclk,
        input  wire             wrst_n,
        input  wire             winc,
        input  wire [DSIZE-1:0] wdata,
        output wire             wfull,
        output wire             awfull,
        input  wire             rclk,
        input  wire             rrst_n,
        input  wire             rinc,
        output wire [DSIZE-1:0] rdata,
        output wire             rempty,
        output wire             arempty
    );

    wire [ASIZE-1:0] waddr, raddr;
    wire [ASIZE  :0] wptr, rptr, wq2_rptr, rq2_wptr;

    // The module synchronizing the read point
    // from read to write domain
    sync_r2w
    #(ASIZE)
    sync_r2w (
    .wq2_rptr (wq2_rptr),
    .rptr     (rptr),
    .wclk     (wclk),
    .wrst_n   (wrst_n)
    );

    // The module synchronizing the write point
    // from write to read domain
    sync_w2r
    #(ASIZE)
    sync_w2r (
    .rq2_wptr (rq2_wptr),
    .wptr     (wptr),
    .rclk     (rclk),
    .rrst_n   (rrst_n)
    );

    // The module handling the write requests
    wptr_full
    #(ASIZE)
    wptr_full (
    .awfull   (awfull),
    .wfull    (wfull),
    .waddr    (waddr),
    .wptr     (wptr),
    .wq2_rptr (wq2_rptr),
    .winc     (winc),
    .wclk     (wclk),
    .wrst_n   (wrst_n)
    );

    // The DC-RAM
    fifomem
    #(DSIZE, ASIZE, FALLTHROUGH)
    fifomem (
    .rclken (rinc),
    .rclk   (rclk),
    .rdata  (rdata),
    .wdata  (wdata),
    .waddr  (waddr),
    .raddr  (raddr),
    .wclken (winc),
    .wfull  (wfull),
    .wclk   (wclk)
    );

    // The module handling read requests
    rptr_empty
    #(ASIZE)
    rptr_empty (
    .arempty  (arempty),
    .rempty   (rempty),
    .raddr    (raddr),
    .rptr     (rptr),
    .rq2_wptr (rq2_wptr),
    .rinc     (rinc),
    .rclk     (rclk),
    .rrst_n   (rrst_n)
    );

`ifdef FORMAL
    integer rptr_prev;
    logic rempty_prev;
    logic rrst_n_prev;

    logic [3:0] cycle_count_r;
    logic [3:0] cycle_count_w;

    initial begin 
        assume(~rrst_n)
        assume(~wrst_n)
        cycle_count_r <= 0;
        cycle_count_w <= 0;

        rptr_prev <= 0;
        rempty_prev <= 0;
        rrst_n_prev <= 0;

        wptr_prev <= 0;
        wfull_prev <= 0;
        wrst_n_prev <= 0;
    end

    always @(posedge rclk) begin
        if (cycle_count_r < 10)
            cycle_count_r <= cycle_count_r + 1;
    end
    always @(posedge wclk) begin
        if (cycle_count_w < 10)
            cycle_count_w <= cycle_count_w + 1;
    end

    
    assume property ( @(posedge rclk or posedge wclk) ((cycle_count_r < 5 || cycle_count_w < 5)  |-> (~rrst_n && ~wrst_n)));
    assume property ( @(posedge rclk or posedge wclk) ((cycle_count_r > 4 && cycle_count_w > 4) |-> (rrst_n && wrst_n)));

    // read side
    always @(posedge rclk) begin
        if (rrst_n) begin
            rptr_prev <= rptr;
            rempty_prev <= rempty;
            rrst_n_prev <= rrst_n;

            empty: cover (rempty & ~(rempty_prev));
            full_read_wrap: cover (rptr == 0 & ~(rptr_prev == 1 | rptr_prev == 0 | ~(rrst_n_prev)));
            gray_read_wrap: cover (rptr[-1] != rptr_prev[-1]);
            underflow: cover (rinc & rempty);
            read_while_write: cover (rinc & winc);
        end
    end

    integer wptr_prev;
    logic wfull_prev;
    logic wrst_n_prev;

    // write side
    always @(posedge wclk) begin
        if(wrst_n) begin
            wptr_prev <= wptr;
            wfull_prev <= wfull;
            wrst_n_prev <= wrst_n;

            full: cover (wfull & ~(wfull_prev));
            full_write_wrap: cover (wptr == 0 & ~(wptr_prev == 1 | wptr_prev == 0 | ~(wrst_n_prev)));
            gray_write_wrap: cover (wptr[-1] != wptr_prev[-1]);
            overflow: cover (winc & wfull);
            write_while_read: cover (rinc & winc);
        end
    end
`endif
endmodule

`resetall
