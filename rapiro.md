# Cómo correr el Rapiro (Raspberry Pi) — paso a paso

Guía operativa para arrancar el actuador (`edge/pi_actuator.py`) en la Raspberry Pi.
La Pi hace polling a la API en el EC2 (`GET /comando`) y, cuando hay una
clasificación nueva, manda el color de ojos al Rapiro por serial.

> Pipeline completo: **notebook** clasifica una foto → **EC2** guarda el color →
> **Pi** lo lee por polling → **Rapiro** cambia el color de los ojos.

---

## Antes de empezar

- La API en el EC2 tiene que estar corriendo. Verificá:
  `curl http://<IP-EC2>:8000/health` → debe responder `{"status":"ok","model_loaded":true}`.
- **IP del EC2:** sacala con `terraform output public_ip` en `infra/` (cambia si la
  instancia se para y arranca). En esta guía se usa `100.56.233.233` como ejemplo.
- El Rapiro tiene que estar conectado por serial y encendido (solo para el paso 4).

---

## 1. Entrar por SSH a la Pi

```bash
ssh <usuario>@<ip-de-la-pi>
```

## 2. Ir a la carpeta del proyecto

```bash
cd ~/nuestro-codigo      # ajustá si la tenés en otra ruta
```

## 3. Instalar dependencias (solo la primera vez)

La Pi necesita `requests` (HTTP) y `pyserial` (serial):

```bash
pip3 install requests pyserial
```

> Si usás un venv en la Pi, activalo primero: `source venv/bin/activate` y ahí instalás.

## 4. Primera prueba en modo seguro (DRY_RUN)

`DRY_RUN=1` **no manda nada por serial**, solo imprime qué comando *enviaría*.
Sirve para confirmar que la Pi habla con el EC2 sin mover el robot.

```bash
API_URL=http://100.56.233.233:8000 DRY_RUN=1 python3 -m edge.pi_actuator
```

Dejalo corriendo, andá a la notebook, clasificá una imagen, y en la Pi tiene que
aparecer algo así:

```
[pi_actuator] Nueva clase: plastico  → ojos R=... G=... B=...  cmd=#PR...
[pi_actuator] DRY_RUN: comando NO enviado por serial.
```

Eso confirma que el ciclo completo (notebook → EC2 → Pi) funciona.
Cortás con **Ctrl+C**.

## 5. Modo producción (manda al Rapiro de verdad)

Con el Rapiro conectado y encendido:

```bash
API_URL=http://100.56.233.233:8000 RAPIRO_SERIAL_PORT=/dev/ttyAMA0 python3 -m edge.pi_actuator
```

Ahora cada clasificación cambia el color de los ojos del Rapiro.
Cortás con **Ctrl+C**.

---

## Detalles importantes

- **Corré siempre con `-m`** (`python3 -m edge.pi_actuator`) desde la raíz
  `nuestro-codigo/`. NO uses `python3 edge/pi_actuator.py` — fallan los imports
  del paquete `edge`.
- **`/dev/ttyAMA0`** es el puerto serial por defecto, no hace falta pasarlo salvo
  que quieras ser explícito o tengas otro puerto.
- **Si tira "Permission denied" en el serial:** tu usuario no está en el grupo
  `dialout`. Arreglo:
  ```bash
  sudo usermod -aG dialout $USER
  ```
  y reconectás la sesión SSH (o probás con `sudo` para salir del paso).
- **El buzón del EC2 arranca vacío** tras reiniciar la API, así que al lanzar
  `pi_actuator` se queda esperando (sin mover nada) hasta tu primera clasificación
  real. No acumula pruebas viejas: solo existe el último comando.

## Variables de entorno disponibles

| Variable | Default | Para qué |
|---|---|---|
| `API_URL` | `http://localhost:8000` | URL de la API en el EC2 (obligatorio en producción) |
| `RAPIRO_SERIAL_PORT` | `/dev/ttyAMA0` | Puerto serial del Rapiro |
| `RAPIRO_BAUD_RATE` | `57600` | Baud rate del serial |
| `POLL_INTERVAL_S` | `1.0` | Segundos entre cada poll a `/comando` |
| `DRY_RUN` | (vacío) | Si está definida, NO manda serial (solo imprime) |

## Consejo

Hacé siempre primero el **paso 4 (DRY_RUN)** para validar la conexión sin riesgo,
y recién después el **paso 5** con el robot real.
