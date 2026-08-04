# 🛠 Gestión del servicio wake.service

Este documento resume los comandos básicos para administrar el servicio `wake.service`, que ejecuta el script `wake.py` automáticamente en segundo plano.

> Nota: Estos comandos aplican para el servicio de usuario (`systemctl --user`).

## Ver estado del servicio
systemctl --user status wake.service

## Ver logs del servicio
journalctl --user -u wake.service -n 50
journalctl --user -u wake.service -f
journalctl --user -u wake.service -p err
journalctl --user -u wake.service -b

## Editar el archivo del servicio
nano ~/.config/systemd/user/wake.service

## Recargar configuración después de editar
systemctl --user daemon-reload

## Iniciar el servicio
systemctl --user start wake.service

## Reiniciar el servicio
systemctl --user restart wake.service

## Detener el servicio
systemctl --user stop wake.service

## Habilitar el servicio al arranque
systemctl --user enable wake.service

## Deshabilitar el servicio al arranque
systemctl --user disable wake.service

## Ver contenido del archivo del servicio
systemctl --user cat wake.service

## Ver el proceso en ejecución
ps aux | grep wake.py | grep -v grep

## Matar el proceso manualmente (para probar reinicio automático)
pkill -f wake.py

## Verificar ubicación del servicio
ls ~/.config/systemd/user/wake.service

## Probar el script manualmente
python3 ~/Documents/wake.py

## Recargar y reiniciar todo
systemctl --user daemon-reload && systemctl --user restart wake.service

## Estado esperado
Active: active (running)
Sistema listo. Esperando wake...

# 🖥 Control del entorno gráfico (Raspberry Pi OS Bookworm)

## Apagar el entorno gráfico (volver a modo consola)
sudo systemctl isolate multi-user.target

## Encender el entorno gráfico
sudo systemctl isolate graphical.target