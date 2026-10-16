"""Translation tables for OniDash L3 (PT/EN/ES)."""


def detect_language():
    try:
        import locale
        loc = locale.getdefaultlocale()[0] or "pt"
    except Exception:
        loc = "pt"
    loc = str(loc).lower()
    if loc.startswith("es"):
        return "es"
    if loc.startswith("en"):
        return "en"
    return "pt"


# rows: (key, pt, en, es)
_ROWS = [
    ("app_title", "OniDash L3", "OniDash L3", "OniDash L3"),
    ("universal_controller", "Controlador Universal", "Universal Controller", "Controlador Universal"),
    ("stopped", "Parado", "Stopped", "Detenido"),
    ("starting", "Iniciando...", "Starting...", "Iniciando..."),
    ("waiting_real", "Aguardando controle real no slot {idx}...", "Waiting for real controller on slot {idx}...", "Esperando controlador real en el slot {idx}..."),
    ("waiting_real_auto", "Aguardando controle real (detecção automática de slot)...", "Waiting for real controller (automatic slot detection)...", "Esperando controlador real (detección automática de slot)..."),
    ("real_disconnected", "Controle real (slot {idx}) desconectado. Aguardando...", "Real controller (slot {idx}) disconnected. Waiting...", "Controlador real (slot {idx}) desconectado. Esperando..."),
    ("real_disconnected_auto", "Controle real desconectado. Aguardando...", "Real controller disconnected. Waiting...", "Controlador real desconectado. Esperando..."),
    ("slot_auto", "Automático", "Automatic", "Automático"),
    ("reading_error", "Erro de leitura: {e}", "Read error: {e}", "Error de lectura: {e}"),
    ("virtual_error", "Erro do controle virtual: {e}", "Virtual controller error: {e}", "Error del controlador virtual: {e}"),
    ("nav_home", "Início", "Home", "Inicio"),
    ("nav_mapping", "Mapeamento", "Mapping", "Mapeo"),
    ("nav_analog", "Analógicos", "Analogs", "Analógicos"),
    ("nav_triggers", "Gatilhos", "Triggers", "Gatillos"),
    ("nav_profiles", "Perfis", "Profiles", "Perfiles"),
    ("nav_settings", "Configurações", "Settings", "Configuración"),
    ("home_title", "Início", "Home", "Inicio"),
    ("mapping_title", "Mapeamento", "Mapping", "Mapeo"),
    ("analogs_title", "Analógicos", "Analogs", "Analógicos"),
    ("triggers_title", "Gatilhos", "Triggers", "Gatillos"),
    ("profiles_title", "Perfis", "Profiles", "Perfiles"),
    ("settings_title", "Configurações", "Settings", "Configuración"),
    ("controller_status", "Estado da conexão", "Connection status", "Estado de la conexión"),
    ("checking", "Verificando...", "Checking...", "Verificando..."),
    ("active_profile", "Perfil ativo", "Active profile", "Perfil activo"),
    ("quick_actions", "Ações rápidas", "Quick actions", "Acciones rápidas"),
    ("open_mapping", "Abrir Mapeamento", "Open Mapping", "Abrir Mapeo"),
    ("edit_analogs", "Editar Analógicos", "Edit Analogs", "Editar Analógicos"),
    ("status_connected", "Conectado", "Connected", "Conectado"),
    ("status_disconnected", "Desconectado", "Disconnected", "Desconectado"),
    ("map_summary", "Resumo", "Summary", "Resumen"),
    ("map_status", "Status", "Status", "Estado"),
    ("map_active", "Ativo", "Enabled", "Activo"),
    ("map_inactive", "Inativo", "Disabled", "Inactivo"),
    ("map_toggle", "Ativar/Desativar", "Enable/Disable", "Activar/Desactivar"),
    ("map_hint", "Clique duas vezes em um mapeamento para editá-lo.", "Double-click a mapping to edit it.", "Haz doble clic en un mapeo para editarlo."),
    ("map_to", "para", "to", "a"),
    ("map_none", "Nenhum mapeamento criado. Clique em Adicionar mapeamento.", "No mappings yet. Click Add mapping.", "Ningún mapeo creado. Haz clic en Agregar mapeo."),
    ("add_mapping", "Adicionar mapeamento", "Add mapping", "Agregar mapeo"),
    ("edit", "Editar", "Edit", "Editar"),
    ("duplicate", "Duplicar", "Duplicate", "Duplicar"),
    ("remove", "Remover", "Remove", "Eliminar"),
    ("refresh", "Atualizar", "Refresh", "Actualizar"),
    ("desc_mapping", "Cada linha é um mapeamento: entrada física → ação virtual. Clique duas vezes para abrir o editor visual com seletores de entrada, ação, modo, condição, repetições e atrasos.", "Each row is a mapping: physical input → virtual action. Double-click to open the visual editor with selectors for input, action, mode, condition, repetitions and delays.", "Cada fila es un mapeo: entrada física → acción virtual. Haz doble clic para abrir el editor visual con selectores de entrada, acción, modo, condición, repeticiones y retardos."),
    ("desc_analog", "Zona morta: ignora movimentos pequenos perto do centro. Sensibilidade: amplifica o sinal. Curva: altera a resposta (maior = mais forte no fim do curso). Limiar: ponto de ativação usado pelo mapeamento. Inverter: troca a direção do eixo.", "Deadzone: ignores small movements near the center. Sensitivity: amplifies the signal. Curve: changes response (higher = stronger at range end). Threshold: activation point used by mappings. Invert: flips axis direction.", "Zona muerta: ignora movimientos pequeños cerca del centro. Sensibilidad: amplifica la señal. Curva: cambia la respuesta (mayor = más fuerte al final del recorrido). Umbral: punto de activación usado por el mapeo. Invertir: cambia la dirección del eje."),
    ("desc_triggers", "Zona morta: ignora pressões leves. Sensibilidade: ajusta a resposta. Inverter: troca a orientação do gatilho. Cada gatilho é configurado separadamente.", "Deadzone: ignores light presses. Sensitivity: adjusts response. Invert: flips trigger direction. Each trigger is configured separately.", "Zona muerta: ignora pulsaciones leves. Sensibilidad: ajusta la respuesta. Invertir: cambia la orientación del gatillo. Cada gatillo se configura por separado."),
    ("desc_profiles", "Perfis são conjuntos independentes de mapeamentos. Crie, duplique, edite, importe e exporte em JSON validado. O perfil ativo define os mapeamentos em execução.", "Profiles are independent mapping sets. Create, duplicate, edit, import and export validated JSON. The active profile defines the running mappings.", "Los perfiles son conjuntos independientes de mapeos. Crea, duplica, edita, importa y exporta en JSON validado. El perfil activo define los mapeos en ejecución."),
    ("desc_settings", "Idioma: troca toda a interface imediatamente. Slot XInput: qual controle é lido. Controle virtual: saída enviada ao jogo. HidHide: oculta o controle real para o virtual ser o principal. Iniciar com o app: liga o motor automaticamente.", "Language: switches the whole UI immediately. XInput slot: which controller is read. Virtual controller: output sent to the game. HidHide: hides the real controller so the virtual one is primary. Start with app: starts the engine automatically.", "Idioma: cambia toda la interfaz al instante. Slot XInput: qué controlador se lee. Controlador virtual: salida enviada al juego. HidHide: oculta el controlador real para que el virtual sea el principal. Iniciar con la app: arranca el motor automáticamente."),
    ("deadzone", "Zona morta", "Deadzone", "Zona muerta"),
    ("sensitivity", "Sensibilidade", "Sensitivity", "Sensibilidad"),
    ("curve", "Curva", "Curve", "Curva"),
    ("threshold", "Limiar", "Threshold", "Umbral"),
    ("invert", "Inverter", "Invert", "Invertir"),
    ("changes_apply", "As alterações aplicam-se à configuração ativa.", "Changes apply to the active configuration.", "Los cambios se aplican a la configuración activa."),
    ("use", "Usar", "Use", "Usar"),
    ("delete", "Excluir", "Delete", "Eliminar"),
    ("profile_new", "Novo", "New", "Nuevo"),
    ("profile_import", "Importar", "Import", "Importar"),
    ("profile_export", "Exportar", "Export", "Exportar"),
    ("profile_edit_title", "Editar perfil", "Edit profile", "Editar perfil"),
    ("profile_name", "Nome", "Name", "Nombre"),
    ("profile_desc", "Descrição", "Description", "Descripción"),
    ("profile_new_name", "Perfil {n}", "Profile {n}", "Perfil {n}"),
    ("profile_new_desc", "Novo perfil", "New profile", "Nuevo perfil"),
    ("profile_copy", "cópia", "copy", "copia"),
    ("import_error", "Falha ao importar: {e}", "Import failed: {e}", "Error al importar: {e}"),
    ("export_error", "Falha ao exportar: {e}", "Export failed: {e}", "Error al exportar: {e}"),
    ("cannot_delete_last_profile", "Não é possível excluir o último perfil.", "Cannot delete the last profile.", "No se puede eliminar el último perfil."),
    ("invalid_profile", "Perfil inválido", "Invalid profile", "Perfil inválido"),
    ("language", "Idioma", "Language", "Idioma"),
    ("controller_and_virtual", "Controle", "Controller", "Controlador"),
    ("xinput_slot", "Slot XInput", "XInput slot", "Slot XInput"),
    ("create_virtual", "Criar controle virtual (X360)", "Create virtual controller (X360)", "Crear controlador virtual (X360)"),
    ("use_hidhide", "Usar HidHide (ocultar o controle real)", "Use HidHide (hide the real controller)", "Usar HidHide (ocultar el controlador real)"),
    ("start_with_app", "Iniciar motor com o aplicativo", "Start engine with the app", "Iniciar motor con la aplicación"),
    ("diagnostics", "Diagnóstico", "Diagnostics", "Diagnóstico"),
    ("test_ls", "Testar LS (L3)", "Test LS (L3)", "Probar LS (L3)"),
    ("save_settings", "Salvar configurações", "Save settings", "Guardar configuración"),
    ("editor_new", "Novo mapeamento", "New mapping", "Nuevo mapeo"),
    ("editor_edit", "Editar mapeamento", "Edit mapping", "Editar mapeo"),
    ("editor_input", "Entrada física", "Physical input", "Entrada física"),
    ("editor_input_help", "Escolha na lista ou clique em Detectar entrada e pressione o botão desejado.", "Pick from the list or click Detect input and press the desired button.", "Elige en la lista o pulsa Detectar entrada y presiona el botón deseado."),
    ("editor_detect", "Detectar entrada", "Detect input", "Detectar entrada"),
    ("editor_detect_stop", "Parar detecção", "Stop detection", "Detener detección"),
    ("editor_detect_wait", "Pressione o botão ou mova o analógico desejado...", "Press the desired button or move the stick...", "Pulsa el botón o mueve el analógico deseado..."),
    ("editor_action", "Ação de destino", "Target action", "Acción de destino"),
    ("editor_action_help", "O que o jogo recebe (saída do controle virtual).", "What the game receives (virtual controller output).", "Lo que recibe el juego (salida del controlador virtual)."),
    ("editor_mode", "Modo de ativação", "Activation mode", "Modo de activación"),
    ("editor_condition", "Condição de ativação", "Activation condition", "Condición de activación"),
    ("editor_modifier", "Entrada modificadora (opcional)", "Modifier input (optional)", "Entrada modificadora (opcional)"),
    ("editor_modifier_help", "Se definida, o mapeamento só age com essa entrada pressionada junto.", "If set, the mapping only works while this input is held.", "Si se define, el mapeo solo actúa con esa entrada pulsada."),
    ("editor_modifier_none", "Nenhuma", "None", "Ninguna"),
    ("editor_threshold", "Limiar (%)", "Threshold (%)", "Umbral (%)"),
    ("editor_threshold_help", "Ponto de ativação do analógico/gatilho.", "Activation point of the stick/trigger.", "Punto de activación del analógico/gatillo."),
    ("editor_seq_count", "Número de toques", "Number of quick presses", "Número de pulsaciones"),
    ("editor_seq_interval", "Intervalo entre toques (ms)", "Interval between presses (ms)", "Intervalo entre pulsaciones (ms)"),
    ("editor_seq_help", "A ativação ocorre após a sequência rápida de toques.", "Activation happens after the quick-press sequence.", "La activación ocurre tras la secuencia rápida de pulsaciones."),
    ("editor_tap_ms", "Duração do pressionamento (ms)", "Press duration (ms)", "Duración de la pulsación (ms)"),
    ("editor_tap_help", "Quanto tempo a ação fica pressionada.", "How long the action stays pressed.", "Cuánto tiempo queda pulsada la acción."),
    ("editor_repeat_count", "Quantidade de repetições", "Number of repetitions", "Cantidad de repeticiones"),
    ("editor_repeat_interval", "Intervalo entre repetições (ms)", "Interval between repetitions (ms)", "Intervalo entre repeticiones (ms)"),
    ("editor_repeat_press", "Duração de cada pressionamento (ms)", "Duration of each press (ms)", "Duración de cada pulsación (ms)"),
    ("editor_continuous", "Repetir continuamente até soltar", "Repeat continuously until release", "Repetir continuamente hasta soltar"),
    ("editor_continuous_help", "Desativado: repete apenas a quantidade definida, uma vez por ativação.", "Off: repeats only the set amount, once per activation.", "Desactivado: repite solo la cantidad definida, una vez por activación."),
    ("editor_delays", "Atrasos", "Delays", "Retardos"),
    ("editor_delay_enable", "Usar atrasos neste mapeamento", "Use delays in this mapping", "Usar retardos en este mapeo"),
    ("editor_delay_activate", "Atraso para ativar (ms)", "Activation delay (ms)", "Retardo para activar (ms)"),
    ("editor_delay_deactivate", "Atraso para desativar (ms)", "Deactivation delay (ms)", "Retardo para desactivar (ms)"),
    ("editor_test", "Testar mapeamento", "Test mapping", "Probar mapeo"),
    ("editor_test_info", "Envia a ação ao controle virtual como se ela tivesse sido ativada.", "Sends the action to the virtual controller as if it had been activated.", "Envía la acción al controlador virtual como si se hubiera activado."),
    ("editor_test_sent", "Teste enviado ao controle virtual.", "Test sent to the virtual controller.", "Prueba enviada al controlador virtual."),
    ("editor_test_fail", "Controle virtual indisponível. Verifique o driver ViGEmBus.", "Virtual controller unavailable. Check the ViGEmBus driver.", "Controlador virtual no disponible. Verifica el driver ViGEmBus."),
    ("editor_save", "Salvar", "Save", "Guardar"),
    ("editor_cancel", "Cancelar", "Cancel", "Cancelar"),
    ("editor_reset", "Restaurar padrões", "Restore defaults", "Restaurar valores"),
    ("editor_conflict_title", "Conflito detectado", "Conflict detected", "Conflicto detectado"),
    ("editor_conflict", "Já existe um mapeamento ativo para a mesma entrada. Salvar mesmo assim?", "An enabled mapping already uses the same input. Save anyway?", "Ya existe un mapeo activo para la misma entrada. ¿Guardar igualmente?"),
    ("editor_threshold_needs_analog", "O modo/condição de limiar exige entrada analógica (analógico ou gatilho).", "Threshold mode/condition requires an analog input (stick or trigger).", "El modo/condición de umbral requiere una entrada analógica (analógico o gatillo)."),
    ("mode_hold_short", "Segurar", "Hold", "Mantener"),
    ("mode_hold_desc", "Mantém a ação ativada enquanto a entrada estiver ativa.", "Keeps the action active while the input is engaged.", "Mantiene la acción activa mientras la entrada esté activa."),
    ("mode_tap_short", "Toque único", "Single tap", "Toque único"),
    ("mode_tap_desc", "Cada ativação pressiona a ação uma vez, pela duração definida.", "Each activation presses the action once, for the set duration.", "Cada activación pulsa la acción una vez, por la duración definida."),
    ("mode_toggle_short", "Alternar", "Toggle", "Alternar"),
    ("mode_toggle_desc", "Cada ativação liga ou desliga a ação.", "Each activation turns the action on or off.", "Cada activación enciende o apaga la acción."),
    ("mode_repeat_short", "Repetir", "Repeat", "Repetir"),
    ("mode_repeat_desc", "Cada ativação repete a ação a quantidade de vezes definida.", "Each activation repeats the action the set number of times.", "Cada activación repite la acción la cantidad de veces definida."),
    ("mode_threshold_short", "Ativar por limiar", "Threshold activation", "Activar por umbral"),
    ("mode_threshold_desc", "Mantém a ação ativa enquanto o valor analógico estiver acima do limiar.", "Keeps the action active while the analog value is above the threshold.", "Mantiene la acción activa mientras el valor analógico supere el umbral."),
    ("cond_direct", "Imediata", "Immediate", "Inmediata"),
    ("cond_direct_desc", "A entrada ativa o mapeamento assim que é pressionada.", "The input activates the mapping as soon as it is pressed.", "La entrada activa el mapeo en cuanto se pulsa."),
    ("cond_threshold", "Limiar analógico", "Analog threshold", "Umbral analógico"),
    ("cond_threshold_desc", "A ativação usa o limiar definido para o valor analógico.", "Activation uses the threshold set for the analog value.", "La activación usa el umbral definido para el valor analógico."),
    ("cond_sequence", "Toques rápidos", "Quick presses", "Pulsaciones rápidas"),
    ("cond_sequence_desc", "A entrada precisa ser tocada várias vezes rapidamente.", "The input must be tapped several times quickly.", "La entrada debe pulsarse varias veces rápidamente."),
    ("sum_hold", "Segurar", "Hold", "Mantener"),
    ("sum_tap", "Toque {ms} ms", "Tap {ms} ms", "Toque {ms} ms"),
    ("sum_toggle", "Alternar", "Toggle", "Alternar"),
    ("sum_repeat", "Repetir {n}x", "Repeat {n}x", "Repetir {n}x"),
    ("sum_repeat_cont", "Repetir continuamente", "Repeat continuously", "Repetir continuamente"),
    ("sum_interval", "Intervalo {ms} ms", "Interval {ms} ms", "Intervalo {ms} ms"),
    ("sum_press", "Pressionar {ms} ms", "Press {ms} ms", "Pulsar {ms} ms"),
    ("sum_threshold", "Limiar {pct}%", "Threshold {pct}%", "Umbral {pct}%"),
    ("sum_seq", "{n} toques rápidos ({ms} ms)", "{n} quick presses ({ms} ms)", "{n} pulsaciones rápidas ({ms} ms)"),
    ("sum_modifier", "com {btn}", "with {btn}", "con {btn}"),
    ("sum_delays", "Atrasos {a}/{d} ms", "Delays {a}/{d} ms", "Retardos {a}/{d} ms"),
]


TRANSLATIONS = {"pt": {}, "en": {}, "es": {}}
for _key, _pt, _en, _es in _ROWS:
    TRANSLATIONS["pt"][_key] = _pt
    TRANSLATIONS["en"][_key] = _en
    TRANSLATIONS["es"][_key] = _es


def T(code, key, **kw):
    table = TRANSLATIONS.get(code, TRANSLATIONS["pt"])
    txt = table.get(key, TRANSLATIONS["pt"].get(key, key))
    try:
        return txt.format(**kw)
    except Exception:
        return txt

