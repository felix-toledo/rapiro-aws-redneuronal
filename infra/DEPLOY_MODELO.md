# Cómo subir un modelo nuevo al EC2

Guía operativa para reemplazar el modelo `.keras` en producción (la API que corre
en el EC2). El modelo **no** va por GitHub (pesa ~150 MB y está en `.gitignore`):
se sube directo por `scp` y se reconstruye la imagen Docker.

> Datos del EC2 (sacados de `terraform output` en `infra/`):
> - IP / usuario: `ubuntu@<IP>` — verificá la IP con `terraform output public_ip`
>   porque cambia si la instancia se para y arranca.
> - Key SSH: `~/.ssh/rapiro-key.pem` (en Windows: `C:\Users\<usuario>\.ssh\rapiro-key.pem`)
> - Ruta del modelo en el EC2: `/opt/rapiro/models/garbage_cnn_model.keras`
> - Ruta del código en el EC2: `/opt/rapiro/`

---

## 0. ANTES de subir: probar el modelo localmente

**Siempre** verificar el modelo en la laptop antes de tocar el EC2. Reemplazá el
archivo en `models/garbage_cnn_model.keras` y corré una prueba que use la misma
ruta de código que producción (`cloud/classifier.py`).

Qué hay que confirmar:

1. **Estructura del archivo** — un `.keras` válido es un zip con
   `config.json`, `metadata.json` y `model.weights.h5` adentro:
   ```bash
   python -c "import zipfile; z=zipfile.ZipFile('models/garbage_cnn_model.keras'); print([i.filename for i in z.infolist()])"
   ```
2. **Carga y formas** — que `tf.keras.models.load_model` no falle, que el
   `input_shape` coincida con `IMAGE_SIZE` de `cloud/classifier.py`, y que el
   `output_shape` tenga tantas clases como `outputs/class_indices.json` (4).
3. **Clasificación coherente** — clasificar una imagen real de cada clase del
   `dataset_propio/` y revisar que las predicciones tengan sentido.

> ⚠️ **Si cambia el tamaño de entrada del modelo**, hay que actualizar
> `IMAGE_SIZE` en `cloud/classifier.py` y subir TAMBIÉN ese archivo (ver paso 1).
> Historial: la CNN propia original era 128×128; el modelo de transfer learning
> es 224×224. `IMAGE_SIZE` ya está en `(224, 224)`.
>
> `notebook_client.py` NO necesita cambios: manda el JPEG crudo y el resize pasa
> en el servidor.

---

## 1. Subir los archivos al EC2 (desde PowerShell en la laptop)

El repo en `/opt/rapiro` lo clonó `root`, así que `ubuntu` no puede escribir ahí
directamente. Subimos a la home (`~`) y después movemos con `sudo` (paso 3).

Subí el modelo (siempre):
```powershell
scp -i $HOME\.ssh\rapiro-key.pem "<ruta-local>\models\garbage_cnn_model.keras" ubuntu@<IP>:~/garbage_cnn_model.keras
```

Subí `classifier.py` SOLO si lo modificaste (p.ej. cambió `IMAGE_SIZE`):
```powershell
scp -i $HOME\.ssh\rapiro-key.pem "<ruta-local>\cloud\classifier.py" ubuntu@<IP>:~/classifier.py
```

## 2. Entrar por SSH
```powershell
ssh -i $HOME\.ssh\rapiro-key.pem ubuntu@<IP>
```

## 3. Mover, reconstruir y reiniciar (ya dentro del EC2)
```bash
sudo cp ~/garbage_cnn_model.keras /opt/rapiro/models/garbage_cnn_model.keras
# Solo si subiste classifier.py:
sudo cp ~/classifier.py /opt/rapiro/cloud/classifier.py

cd /opt/rapiro
docker build -f cloud/Dockerfile -t rapiro-api .   # rápido: cachea la capa de TensorFlow
sudo systemctl restart rapiro-api
```

## 4. Verificar
```bash
curl http://localhost:8000/health
# Esperado: {"status":"ok","model_loaded":true}

# Ver logs si algo falla:
sudo journalctl -u rapiro-api -n 50 --no-pager
```

Después, desde la notebook, probar `edge/notebook_client.py` apuntando a
`API_URL=http://<IP>:8000` y clasificar en vivo.

---

## Por qué hay que reconstruir la imagen

El modelo está horneado dentro de la imagen Docker (`COPY models/` en
`cloud/Dockerfile`), no montado como volumen. Por eso copiar el archivo no alcanza:
hay que rebuildear para que entre a la imagen. El rebuild es rápido porque Docker
cachea la capa pesada (`pip install` de TensorFlow) y solo rehace desde
`COPY models/` en adelante.

**Mejora opcional a futuro:** montar el modelo como volumen
(`docker run -v /opt/rapiro/models:/app/models ...` en el systemd de
`infra/user_data.sh`). Así las próximas actualizaciones serían solo `scp` +
`systemctl restart`, sin rebuild.

## Pendiente de Git

El cambio de `IMAGE_SIZE` en `cloud/classifier.py` conviene commitearlo, así si el
EC2 se reconstruye desde cero (nuevo `terraform apply`) no se pierde. El `.keras`
seguirá yendo por `scp` aparte (está en `.gitignore`).
