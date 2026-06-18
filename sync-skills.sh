#!/bin/bash
# ============================================================
# sync-skills.sh — Skills Hub Synchronizer
# Sincroniza skills de plugins de Antigravity IDE hacia el Hub
# central via symlinks. Sin copias, sin duplicados.
#
# Uso: ./sync-skills.sh [--dry-run] [--clean]
#   --dry-run   Muestra lo que haría sin ejecutar nada
#   --clean     Elimina symlinks rotos antes de sincronizar
# ============================================================

HUB_DIR="/Users/crotalo/desarrollo-local/server/skills"
PLUGINS_DIR="/Users/crotalo/.gemini/config/plugins"

DRY_RUN=false
CLEAN=false
LINKED=0
SKIPPED=0
BROKEN_REMOVED=0

# Parse args
for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true ;;
    --clean)   CLEAN=true ;;
  esac
done

echo "🔗 Skills Hub Synchronizer"
echo "   Hub:     $HUB_DIR"
echo "   Plugins: $PLUGINS_DIR"
$DRY_RUN && echo "   Modo:    DRY-RUN (sin cambios reales)"
echo ""

# Limpiar symlinks rotos si se solicita
if $CLEAN; then
  echo "🧹 Limpiando symlinks rotos..."
  find "$HUB_DIR" -maxdepth 1 -type l | while read -r link; do
    if [ ! -e "$link" ]; then
      skill_name=$(basename "$link")
      if $DRY_RUN; then
        echo "   [DRY] Eliminaría symlink roto: $skill_name"
      else
        rm "$link"
        echo "   ❌ Symlink roto eliminado: $skill_name"
        ((BROKEN_REMOVED++))
      fi
    fi
  done
  echo ""
fi

# Sincronizar skills desde plugins
echo "📦 Sincronizando desde plugins de Antigravity IDE..."
while IFS= read -r -d '' skill_dir; do
  skill_name=$(basename "$skill_dir")
  target="$HUB_DIR/$skill_name"

  # Saltar si el SKILL.md no existe (no es un skill válido)
  [ ! -f "$skill_dir/SKILL.md" ] && continue

  if [ -e "$target" ] || [ -L "$target" ]; then
    # Ya existe (sea archivo real o symlink válido)
    echo "   ⏭  Omitido (ya existe): $skill_name"
    ((SKIPPED++))
  else
    if $DRY_RUN; then
      echo "   [DRY] Enlazaría: $skill_name"
      echo "         → $skill_dir"
    else
      ln -s "$skill_dir" "$target"
      echo "   ✅ Enlazado: $skill_name"
      echo "      → $skill_dir"
      ((LINKED++))
    fi
  fi
done < <(find "$PLUGINS_DIR" -mindepth 3 -maxdepth 4 -type d -name "SKILL.md" -prune -o \
         -type d -path "*/skills/*" ! -name "skills" -print0 2>/dev/null)

echo ""
echo "─────────────────────────────────"
if $DRY_RUN; then
  echo "Resultado (DRY-RUN): sin cambios reales"
else
  echo "✅ Nuevos enlaces:     $LINKED"
  echo "⏭  Omitidos:          $SKIPPED"
  [ $BROKEN_REMOVED -gt 0 ] && echo "🗑  Rotos eliminados:  $BROKEN_REMOVED"
fi
echo ""
echo "Hub activo: $HUB_DIR"
ls -la "$HUB_DIR" 2>/dev/null | grep -v "^total" | grep -v "^d" | awk '{print "   " $0}'
