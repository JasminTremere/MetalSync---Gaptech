@echo off
echo Verificando se o Docker esta rodando...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker nao esta rodando! Inicie o Docker Desktop primeiro.
    pause
    exit
)
echo Docker rodando! Subindo os containers...
docker compose up --build -d
echo Pronto!
pause