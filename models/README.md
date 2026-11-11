# SKY130 model provenance

The NMOS/PMOS 1.8 V device model files and `lod.spice` are **unmodified** excerpts from the public [SkyWater primitive library](https://github.com/google/skywater-pdk-libs-sky130_fd_pr), commit `f62031a1be9aefe902d6d54cddd6f59b57627436`. Original files are Apache-2.0 licensed; the license and original file headers are retained. `provenance.json` records SHA-256 checksums, verified by the test suite.

Original cell files reside under `cells/nfet_01v8/` and `cells/pfet_01v8/`; `lod.spice` comes from `models/parameters/`. The five small `tt/ss/ff/sf/fs.spice` wrappers in this folder are local include lists. No full PDK installation is required and reproduction is offline after Python dependencies are installed.

Use `.option scale=1e-6`; device widths and lengths are specified in micrometres. Statistical/mismatch slope parameters are included to resolve model definitions, but mismatch variation is not enabled. Process corners represent global model corners, not a foundry-qualified yield estimate. Routing, layout-dependent stress geometry and extracted parasitics have not been supplied.
