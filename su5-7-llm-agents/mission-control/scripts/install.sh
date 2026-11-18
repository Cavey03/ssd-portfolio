#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --uninstall ) ]]; then
    printf 'Usage: %s [--uninstall]\n' "$0" >&2
    exit 1
fi

# Find the checkout and use absolute paths, since KDE does not expand ~.
script_path=$(readlink -f "$0")
repo_dir=$(dirname "$(dirname "$script_path")")
bin_dir=$(readlink -m "$HOME/.local/bin")
applications_dir=$(readlink -m "${XDG_DATA_HOME:-$HOME/.local/share}/applications")
mc_path="$bin_dir/mc"
desktop_path="$applications_dir/mission-control.desktop"

if [[ "${1-}" == --uninstall ]]; then
    # Only remove a launcher symlink; never delete someone's regular file.
    if [[ -L "$mc_path" ]]; then
        rm -- "$mc_path"
        printf 'Removed %s\n' "$mc_path"
    fi
    if [[ -e "$desktop_path" ]]; then
        rm -- "$desktop_path"
        printf 'Removed %s\n' "$desktop_path"
    fi
else
    if [[ -e "$mc_path" && ! -L "$mc_path" ]]; then
        printf 'Error: refusing to overwrite regular file or directory: %s\n' "$mc_path" >&2
        exit 1
    fi

    mkdir -p -- "$bin_dir" "$applications_dir"
    ln -sfn -- "$repo_dir/scripts/mc" "$mc_path"
    printf 'Linked %s -> %s/scripts/mc\n' "$mc_path" "$repo_dir"

    # Quote the Exec argument, then escape it for the desktop file's value syntax.
    # Percent signs are doubled because desktop launchers treat them as field codes.
    exec_path=${mc_path//\\/\\\\}
    exec_path=${exec_path//\"/\\\"}
    exec_path=${exec_path//\$/\\\$}
    exec_path=${exec_path//\`/\\\`}
    exec_path=${exec_path//\\/\\\\}
    exec_path=${exec_path//%/%%}
    while IFS= read -r line; do
        if [[ "$line" == *'@MC_PATH@'* ]]; then
            printf '%s"%s"%s\n' "${line%%@MC_PATH@*}" "$exec_path" "${line#*@MC_PATH@}"
        else
            printf '%s\n' "$line"
        fi
    done < "$repo_dir/packaging/mission-control.desktop.in" > "$desktop_path"
    printf 'Wrote %s\n' "$desktop_path"

    if command -v desktop-file-validate >/dev/null 2>&1; then
        desktop-file-validate "$desktop_path"
    fi
fi

# Refresh KDE's application metadata if the optional utility is installed.
if [[ -d "$applications_dir" ]] && command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$applications_dir"
fi
