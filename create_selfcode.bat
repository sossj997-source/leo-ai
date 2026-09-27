@echo off
REM Auto-create self_code module files

cd /d "%~dp0"

echo ============================================
echo  Creating self_code module
echo ============================================

if not exist "app\self_code" mkdir "app\self_code"
if not exist "app\agent\tools\auto_tools" mkdir "app\agent\tools\auto_tools"

echo Creating __init__.py...
(
echo # app/self_code/__init__.py
echo from app.self_code.generator import CodeGenerator
echo from app.self_code.sandbox import SandboxExecutor
echo from app.self_code.registry import ToolRegistryManager
echo from app.self_code.executor import AutoToolExecutor
echo.
echo __all__ = [
echo     "CodeGenerator",
echo     "SandboxExecutor",
echo     "ToolRegistryManager",
echo     "AutoToolExecutor",
echo ]
) > "app\self_code\__init__.py"

echo Creating auto_tools/__init__.py...
(
echo # Auto-generated tools
) > "app\agent\tools\auto_tools\__init__.py"

echo.
echo ============================================
echo  Basic files created.
echo  Now copying Python modules from source...
echo ============================================

echo.
echo NOTE: Python files with complex code need manual paste.
echo       Run the following in PowerShell to open each file:
echo.
echo       notepad app\self_code\generator.py
echo       notepad app\self_code\sandbox.py
echo       notepad app\self_code\registry.py
echo       notepad app\self_code\executor.py
echo       notepad app\self_code\main.py
echo       notepad app\agent\tools\self_code_tools.py
echo.
pause