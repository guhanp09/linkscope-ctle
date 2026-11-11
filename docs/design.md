# Source degeneration and measurement conventions

Each input MOSFET has a source resistor Rs to the shared tail node. Cs connects the two source nodes, so in differential mode each half-circuit sees an effective 2Cs bypass. Ignoring output parasitics, the voltage gain is approximately gm·Rd·(1+s·2RsCs)/(1+gmRs+s·2RsCs). The low-frequency degeneration reduces gain and improves linear input range; the capacitive bypass restores transconductance at higher frequencies. Output capacitance and transistor parasitics limit the eventual high-frequency gain.

This estimate predicts a zero near 1/(2π·2RsCs), but exact measured poles and zeros come from the circuit response. The stable three-pole fit is a reduced-order model; its third pole is outside the fitted band and must not be interpreted as a separately extracted physical pole. The 500 MHz evaluation frequency is the Nyquist frequency of the illustrative 1 Gbit/s link.

The differential source is 1 V AC total, split +0.5/−0.5 between the two input terminals around 1.2 V common mode. The gain is V(outp,outn)/V(diff). Device and resistor noise are included by SPICE; the ideal reference contributes none. The input-referred noise is integrated only over the stated 100 kHz–10 GHz band. The separate link experiment does not add that noise and must not be interpreted as a noise-limited receiver result.

PVT is global process, voltage and temperature variation; no random mismatch yield is reported. All twenty Rs/Cs combinations are retained so the chosen candidate and alternatives can be reviewed.
