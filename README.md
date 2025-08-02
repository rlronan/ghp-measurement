# Greenwich house pottery Measuring app code (public)

## Receipt printing:
Locations: 
  - Greenwich (Jones street)
  - Chelsea (14th Street)
  - Barrow Street (Barrow Street)

Each location has compiled printer server file in the form of an .exe + a folder called _internals + a secret key file (not provided here)
E.g. Greenwich has:
  greenwich_print_server.exe
  greenwich_print_server_secret_key.txt (or as an ENV variable)
  run_print_server.bat 
  _internal/ (folder)

The file run_print_server.bat needs to be run which opens a command prompt and runs greenwich_print_server.exe

