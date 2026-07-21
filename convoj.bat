@echo off
rem Launcher pre convoj.py — natívne alebo v Dockeri (set CONVOJ_DOCKER=1)
rem V Docker režime spúšťaj z koreňa projektu (mountuje sa aktuálny adresár).

if not "%CONVOJ_DOCKER%"=="1" goto native

set "IMG=%CONVOJ_IMAGE%"
if "%IMG%"=="" set "IMG=convoj"
docker run --rm -v "%CD%:/work" -w /work %IMG% %*
goto :eof

:native
call python "%~dp0src\convoj.py" %*
