pyinstaller --clean print_server_v2.spec --distpath print_server_v2

echo cmd.exe /K print_server_v2.exe Chelsea > print_server_v2\run_chelsea_print_server.bat
echo sleep 10000 >> print_server_v2\run_chelsea_print_server.bat

echo cmd.exe /K print_server_v2.exe Greenwich > print_server_v2\run_greenwich_print_server.bat
echo sleep 10000 >> print_server_v2\run_greenwich_print_server.bat

echo cmd.exe /K print_server_v2.exe Barrow > print_server_v2\run_barrow_print_server.bat
echo sleep 10000 >> print_server_v2\run_barrow_print_server.bat

