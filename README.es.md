# OniDash L3

OniDash L3 es una utilidad para Windows con controles Xbox. Detecta un doble toque rapido del stick analogico izquierdo (o pulsaciones configurables de botones) y simula automaticamente un clic del stick izquierdo (LS/L3), usado en juegos como **Onimusha: Way of the Sword** para correr.

## Por que este proyecto

Correr en juegos como Onimusha puede depender de tocar dos veces el stick izquierdo o presionar LS/L3. En controles reales esta deteccion puede resultar poco fiable o incomoda. Esta herramienta crea un controlador Xbox virtual e inyecta el LS en el momento correcto sin interferir con el movimiento normal.

## Funcionalidades

- Lectura en tiempo real del controlador Xbox real mediante XInput.
- Controlador Xbox virtual mediante ViGEmBus/vgamepad.
- Espejo de todos los ejes y botones al controlador virtual.
- Deteccion automatica del slot del controlador real (opcion "Automatico"), con eleccion manual de 0 a 3.
- Editor visual de mapeos: elige la entrada fisica (con boton "Detectar entrada"), la accion de destino y el modo de activacion, todo con selectores - sin escribir codigo.
- Modos de activacion: Mantener, Toque unico, Alternar, Repetir y Umbral analogico.
- Repetir Nx por activacion (ej.: exactamente 3 veces por toque), con intervalo, duracion de pulsacion y repetecion continua opcional (desactivada por defecto).
- Condiciones de activacion: directa, umbral analogico o secuencia de toques rapidos (ej.: doble empuje del LS), con entrada modificadora opcional (ej.: LB).
- Boton "Probar mapeo" envia la secuencia al controlador virtual antes de guardar.
- Lista con resumen legible (ej.: `LS a B · Repetir 3x · Intervalo 300 ms`), editar con doble clic, duplicar, activar/desactivar y eliminar.
- Aviso de conflictos entre mapeos antes de guardar.
- Migracion automatica de configuraciones antiguas, sin borrar datos.
- Interfaz negro/dorado, icono, estado en tiempo real e indicador de LS.
- Soporte opcional de HidHide para ocultar el controlador real y hacer el virtual principal.
- Idiomas: Portugues, English, Espanol.

## Requisitos

- Windows 10/11.
- Controlador Xbox (recomendado USB).
- ViGEmBus Driver 1.22 o superior.
- XInput (incluido en Windows).
- Para ejecutar el script: Python 3.10+ con `XInput-Python` y `vgamepad`.
- Opcional: HidHide.

## Como usar (script)

```bat
cd %USERPROFILE%\Documents\XboxDashL3
pip install XInput-Python vgamepad
python xbox_dash_l3.py
```

## Como usar (.exe)

Abre `dist\OniDashL3\OniDashL3.exe` o el acceso directo `OniDash L3`.

Pasos:
1. Conecta el controlador Xbox por USB.
2. En Configuracion, elige el slot XInput del controlador (o deja en "Automatico").
3. En Mapeo, haz clic en "Anadir mapeo".
4. Elige la entrada (o usa "Detectar entrada" y pulsala), la accion, el modo y las opciones.
5. Usa "Probar mapeo" para comprobar; luego "Guardar".
6. En el juego/Steam, elige el controlador virtual si hace falta.

## HidHide (opcional)

Para hacer el controlador virtual principal automaticamente:
1. Instala HidHide: https://github.com/nefarius/HidHide/releases
2. Marca "Usar HidHide" en la app.
3. Reinicia la app.
4. Reconecta el USB del controlador.

## Limitaciones

- Algunos juegos leen el controlador fisico (slot 0) antes del virtual. Si el virtual no responde, usa HidHide, reconecta o cambia el orden.
- La deteccion de doble toque depende de la calibracion del analogico; ajusta umbral, histeresis, intervalo y retardos.
- HidHide es un controlador de terceros y puede requerir reinicio.
- El programa no sustituye ni altera el controlador real.

## Solucion de problemas

- Si aparece "vgamepad no disponible", instala ViGEmBus y reinicia.
- Falsos positivos: sube el umbral y reduce el intervalo.
- No detecta: baja el umbral y aumenta el intervalo; revisa la inversion del eje Y.
- Las pulsaciones de boton no se cuentan: suelta completamente el boton entre toques.