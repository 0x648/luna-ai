@echo off

SET CONDA_PATH=.\Miniconda3

REM 激活base环境
CALL %CONDA_PATH%\Scripts\activate.bat %CONDA_PATH%

cmd /k