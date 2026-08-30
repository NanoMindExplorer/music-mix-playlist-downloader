_mmpd() {
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    local cmds="download retrofit lyrics organize cache config doctor self-update completion"
    local global="--version -V --quiet -q --help -h"

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${cmds} ${global}" -- "${cur}") )
        return 0
    fi

    local cmd="${COMP_WORDS[1]}"
    case "${cmd}" in
        download)
            COMPREPLY=( $(compgen -W "--format -f --output -o --max --lyrics --translate --no-translate --transliterate --lrc-format --sync-huawei --no-sync-huawei --no-embed --no-dedup --isrc --no-isrc --concurrent --help" -- "${cur}") )
            case "${prev}" in
                --format|-f) COMPREPLY=( $(compgen -W "mp3 flac wav best" -- "${cur}") ) ;;
                --lyrics) COMPREPLY=( $(compgen -W "musixmatch chain youtube-cc cc off none" -- "${cur}") ) ;;
                --transliterate) COMPREPLY=( $(compgen -W "auto ja zh yue off" -- "${cur}") ) ;;
                --lrc-format) COMPREPLY=( $(compgen -W "gabung pisah id_only" -- "${cur}") ) ;;
                --output|-o) COMPREPLY=( $(compgen -d -- "${cur}") ) ;;
            esac
            ;;
        retrofit)
            COMPREPLY=( $(compgen -W "--dir -d --lyrics-only --covers-only --translate --no-translate --transliterate --lrc-format --overwrite --fetch-missing --no-fetch --workers --sync-huawei --no-sync-huawei --no-embed --help" -- "${cur}") )
            case "${prev}" in
                --dir|-d) COMPREPLY=( $(compgen -d -- "${cur}") ) ;;
                --transliterate) COMPREPLY=( $(compgen -W "auto ja zh yue off" -- "${cur}") ) ;;
                --lrc-format) COMPREPLY=( $(compgen -W "gabung pisah id_only" -- "${cur}") ) ;;
            esac
            ;;
        lyrics)
            COMPREPLY=( $(compgen -W "--dir -d --translate-only --transliterate --lrc-format --sync-huawei --no-sync-huawei --no-embed --help" -- "${cur}") )
            case "${prev}" in
                --dir|-d) COMPREPLY=( $(compgen -d -- "${cur}") ) ;;
                --transliterate) COMPREPLY=( $(compgen -W "auto ja zh yue off" -- "${cur}") ) ;;
                --lrc-format) COMPREPLY=( $(compgen -W "gabung pisah id_only" -- "${cur}") ) ;;
            esac
            ;;
        organize)
            COMPREPLY=( $(compgen -W "--dir -d --no-recursive --dry-run --help" -- "${cur}") )
            case "${prev}" in --dir|-d) COMPREPLY=( $(compgen -d -- "${cur}") ) ;; esac
            ;;
        cache)
            COMPREPLY=( $(compgen -W "--stats --clear --clear-expired --clear-negative --help" -- "${cur}") )
            ;;
        config)
            COMPREPLY=( $(compgen -W "--create-example --path --credentials-path --help" -- "${cur}") )
            ;;
        self-update)
            COMPREPLY=( $(compgen -W "--no-pull --help" -- "${cur}") )
            ;;
        completion)
            COMPREPLY=( $(compgen -W "bash zsh fish" -- "${cur}") )
            ;;
    esac
}
complete -F _mmpd mmpd
