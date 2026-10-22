# Source this file in Bash or Zsh. PROJECT_ROOT is this example's setting.
_project_jump() {
    local root target
    case ${PROJECT_ROOT:-} in
        /*) ;;
        *) printf 'Set PROJECT_ROOT to an absolute project directory.\n' >&2; return 2 ;;
    esac
    root=$(builtin cd -- "$PROJECT_ROOT" && builtin pwd -P) || return
    target=$(command zoxide query --base-dir "$root" "$@") || return
    target=$(builtin cd -- "$target" && builtin pwd -P) || return
    # A symlink below the project must not silently take us outside it.
    if [ "$root" != / ]; then
        case "$target/" in
            "$root/"*) ;;
            *) printf 'The selected directory resolves outside PROJECT_ROOT.\n' >&2; return 1 ;;
        esac
    fi
    builtin cd -- "$target"
}

pz() { _project_jump -- "$@"; }
pzi() { _project_jump --interactive -- "$@"; }
