if [ -z "${PS1-}" ]; then
  return
fi

_in_container_completion() {
    local cur_word args
    cur_word="${COMP_WORDS[COMP_CWORD]}"
    args=$(podman ps --format '{{ .Names }}')

    COMPREPLY=($(compgen -W "$args" -- "$cur_word"))
}

complete -F _in_container_completion in-container
