# OniDash L3

OniDash L3 es una utilidad para Windows con controles Xbox. Detecta un doble toque rapido del stick analogico izquierdo (o pulsaciones configurables de botones) y simula automaticamente un clic del stick izquierdo (LS/L3), usado en juegos como **Onimusha: Way of the Sword** para correr.

## Por que este proyecto

Correr en juegos como Onimusha puede depender de tocar dos veces el stick izquierdo o presionar LS/L3. En controles reales esta deteccion puede resultar poco fiable o incomoda. Esta herramienta crea un controlador Xbox virtual e inyecta el LS en el momento correcto sin interferir con el movimiento normal.

## Funcionalidades

- Lectura en tiempo real del controlador Xbox real mediante XInput.
- Controlador Xbox virtual mediante ViGEmBus/vgamepad.
- Espejo de todos los ejes y botones al controlador virtual.
- Gatillo por analogico: empuje el stick hacia adelante de 0 a 4 veces. 0 significa mantener para activar.
- Gatillo por boton: elige A, B, X, Y, LB, RB, LT, RT, L3/L4, Start, Back o D-Pad, con 1 a 4 pulsaciones.
- Modo del L3: Mantener (sigue corriendo mientras caminas) o Toque (clic rapido).
- Retardo de activacion y desactivacion configurable (0 a 1000 ms), con opcion de activar/desactivar.
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
2. Selecciona el controlador en la lista.
3. Ajusta gatillos, modo y retardos.
4. Activa la funcion.
5. En el juego/Steam, elige el controlador virtual si hace falta.

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