# rapiro/ — código para la Raspberry Pi

Solo estos 3 archivos van a la Pi. Nada más.

```
rapiro/
├── actuator.py       ← loop principal: pollea la API y manda colores por serial
├── rapiro_client.py  ← protocolo serial del Rapiro
├── requirements.txt  ← dependencias (requests, pyserial, python-dotenv)
└── .env              ← configuración local (crearlo vos, no está en el repo)
```

---

## 1. Copiar a la Pi

```bash
# Desde tu máquina, con la Pi en la misma red:
scp -r rapiro/ pi@<ip-de-la-pi>:~/rapiro
```

O con un pendrive, o clonando el repo entero y usando solo esta carpeta.

---

## 2. Instalar dependencias en la Pi

```bash
cd ~/rapiro
pip install -r requirements.txt
```

Solo instala 3 paquetes livianos. No hace falta venv.

---

## 3. Crear el archivo `.env`

Dentro de `~/rapiro/` crear un archivo llamado `.env`:

```env
# URL de la API en EC2 (la que imprime terraform al final del apply)
API_URL=http://<ip-ec2>:8000

# Puerto serial del Rapiro (verificar con: ls /dev/tty*)
RAPIRO_SERIAL_PORT=/dev/ttyAMA0

# Dejar estas con los defaults salvo que haya que cambiarlas
# RAPIRO_BAUD_RATE=57600
# POLL_INTERVAL_S=1.0
```

> Para encontrar el puerto serial del Rapiro:
> ```bash
> ls /dev/tty*
> # Desconectar y reconectar el Rapiro y volver a listar — el nuevo que aparece es el puerto
> ```

---

## 4. Correr

```bash
# Sin Rapiro físico — solo muestra logs (para verificar que llegan los colores desde EC2):
DRY_RUN=1 python actuator.py

# Con Rapiro conectado:
python actuator.py
```

Para que arranque automáticamente al encender la Pi, agregar al crontab:
```bash
crontab -e
# Agregar esta línea:
@reboot cd /home/pi/rapiro && python actuator.py >> /tmp/rapiro.log 2>&1
```

---

## 5. Qué hace el Rapiro por cada clase

Cada clasificación dispara un **gesto + color de ojos**. Los comandos y tiempos
están verificados contra el firmware oficial (`RAPIRO_ver0_0.ino`) y el script
probado en hardware real de grupo-stefi.

| Clase | Gesto | Ojos |
|-------|-------|------|
| `plastico` | levanta brazo derecho (`#M6`) → home | amarillo |
| `papel_carton` | mueve ambos brazos (`#M5`) → home | azul |
| `metal` | levanta brazo izquierdo (`#M8`) → home | naranja |
| `descarte_comun` | sacude la cabeza ("no") | rojo |
| `no_identificado` | ladea la cabeza (duda) | blanco tenue |

> No se usan los motions de caminar (`#M1`/`#M2`): el robot está sobre un
> basurero y caminar lo haría caer. Solo brazos, cabeza y ojos.

Para cambiar gestos o colores, editar `build_behavior()` en `rapiro_client.py`.

## 6. Logs esperados

```
[rapiro] iniciando (PRODUCCION) — http://54.x.x.x:8000
[rapiro] plastico
[rapiro] metal
[rapiro] detenido.
```

Un log por clasificación. Silencioso el resto del tiempo.
En `DRY_RUN` además imprime la secuencia de comandos que mandaría:
```
[rapiro] plastico → #M6 #M0 #PR255G255B000T010
```
