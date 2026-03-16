@echo off
REM KanTu - Build and upload to PyPI
setlocal enabledelayedexpansion

cd /d "%~dp0"

set PYTHON=python
set VERSION_FILE=kantu\__init__.py

echo === KanTu PyPI Upload ===

echo [1/5] Bumping patch version...
%PYTHON% -c "import re; p='kantu/__init__.py'; t=open(p,encoding='utf-8').read(); m=re.search(r'(__version__\s*=\s*\"(\d+\.\d+\.)(\d+)\")', t); old=m.group(2)+m.group(3); new=m.group(2)+str(int(m.group(3))+1); open(p,'w',encoding='utf-8').write(t.replace(m.group(1), '__version__ = \"'+new+'\"')); print(f'  {old} -> {new}')"
if errorlevel 1 goto error

echo [2/5] Cleaning old builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist kantu.egg-info rmdir /s /q kantu.egg-info

echo [3/5] Installing build tools...
%PYTHON% -m pip install --upgrade build twine -q

echo [4/5] Building package...
%PYTHON% -m build
if errorlevel 1 goto error
%PYTHON% -m twine check dist\*
if errorlevel 1 goto error

echo [5/5] Uploading to PyPI...
%PYTHON% -m twine upload dist\*
if errorlevel 1 goto error

echo === Done! ===
goto end

:error
echo === Error occurred! ===
exit /b 1

:end
endlocal