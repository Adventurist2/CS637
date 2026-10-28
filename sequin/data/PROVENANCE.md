# Benchmark provenance

The numeric MATPOWER files in `cases/` were copied unchanged from the data supplied in [Andrew Chio's SEQUIN repository](https://github.com/andrewgchio/SEQUIN), commit `d30f0c6528efe44c7cb5c82a1cd9dff0d6983296`.

Their headers identify [PGLib-OPF](https://github.com/power-grid-lib/pglib-opf), version 23.07, 23 July 2023. Retain the original headers and cite the IEEE PES Task Force benchmark library and SEQUIN paper in academic work. Consult the upstream projects for their data/source licensing and usage terms.

The six paper cases are the API 14, API 39, case60_c, API 118, case162_ieee_dtc, and case240_pserc files. The ordinary IEEE 14 file is also retained to make its distinction from the stressed research case explicit. Case loading records a SHA-256 checksum. Runtime demand perturbation and preprocessing do not modify these source files.
