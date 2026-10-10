# HSI-CL-XY/2K live canary

This **dedicated branch** runs the same 1,799-byte interpreter already preserved on `Notes/main`, through a read-only health server. It executes exactly two fixed, bounded samples on startup: accepted UTM step and rejected malformed candidate. Evidence is exposed at `/health` and `/evidence`, using ephemeral state. No arbitrary code inputs are taken from HTTP. No trader order, authentication, external API call, or live domain action is performed.

Deploy from branch `hsi-cl-xy-2k-railway-canary-v1`, not Notes/main. This is a runtime proof-of-execution only; it does not replace the original three HSI gate services, decide halting, or guarantee all evolutions valid.
