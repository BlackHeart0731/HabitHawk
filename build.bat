@echo off
echo.
echo HabitHawk.exeをビルド中...
echo (この処理には時間がかかる場合があります)
    
:: PyInstallerでアプリケーションをビルド
pyinstaller HabitHawk.spec

echo.
echo アイコンを更新中...
    
:: Resource Hackerを使ってアイコンを更新
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist\HabitHawk.exe -save dist\HabitHawk.exe -action addoverwrite -resource "HabitHawk.ico" -mask ICONGROUP,1,1033
    
echo.
echo ビルドとアイコンの更新が完了しました。
pause