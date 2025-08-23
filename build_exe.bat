pyinstaller --clean print_server_v2.spec --distpath print_server_v2

echo cmd.exe /K print_server_v2.exe > print_server_v2\run_print_server.bat
echo sleep 10000 >> print_server_v2\run_print_server.bat

