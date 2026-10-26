# Greenwich house pottery Measuring app code (public)

## Receipt printing:
Locations: 
  - Greenwich (Jones street)
  - Chelsea (14th Street)
  - Barrow Street (Barrow Street)

### Chelsea and Barrow: print_server_v2
Chelsea and Barrow run the same `print_server_v2.exe`, built from `print_server_v2.py` by running `build_exe.bat` on Windows.
It is a single self-contained exe (no `_internal` folder). The location is passed on the command line, and each location's
printer IP is in `PRINTER_IPS` in `print_server_v2.py`.

Each location's folder has:
  print_server_v2.exe
  run_chelsea_print_server.bat (or run_barrow_print_server.bat)
  chelsea_print_server_secret_key.txt (or barrow_..., or as a CHELSEA_PRINT_SERVER_SECRET_KEY / BARROW_... ENV variable; not provided here)

Run the location's .bat file, which opens a command prompt and runs `print_server_v2.exe Chelsea` (or `Barrow`).
The secret key file must be in the folder the .bat file is run from.
If the printer's IP has changed, add `--printer-ip <ip>` to the command in the .bat file.

Chelsea's key is the server's `PRINT_SERVER_SECRET_KEY`; the old Chelsea exe read it from `print_server_secret_key.txt`.

### Greenwich: compiled print server (v1)
Greenwich has a compiled printer server file in the form of an .exe + a folder called _internal + a secret key file (not provided here):
  greenwich_print_server.exe
  greenwich_print_server_secret_key.txt (or as an ENV variable)
  run_print_server.bat 
  _internal/ (folder)

The file run_print_server.bat needs to be run which opens a command prompt and runs greenwich_print_server.exe.
The .exe must sit next to the `_internal` folder, not inside it.

