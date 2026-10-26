pyinstaller --clean print_server_v2.spec --distpath print_server_v2

echo REM If the receipt printer's IP address changes, edit the --printer-ip value below. > print_server_v2\run_chelsea_print_server.bat
echo cmd.exe /K print_server_v2.exe Chelsea --printer-ip 10.186.3.27 >> print_server_v2\run_chelsea_print_server.bat
echo sleep 10000 >> print_server_v2\run_chelsea_print_server.bat

echo REM If the receipt printer's IP address changes, edit the --printer-ip value below. > print_server_v2\run_greenwich_print_server.bat
echo cmd.exe /K print_server_v2.exe Greenwich --printer-ip 192.168.105.50 >> print_server_v2\run_greenwich_print_server.bat
echo sleep 10000 >> print_server_v2\run_greenwich_print_server.bat

echo REM If the receipt printer's IP address changes, edit the --printer-ip value below. > print_server_v2\run_barrow_print_server.bat
echo cmd.exe /K print_server_v2.exe Barrow --printer-ip 192.168.115.147 >> print_server_v2\run_barrow_print_server.bat
echo sleep 10000 >> print_server_v2\run_barrow_print_server.bat

