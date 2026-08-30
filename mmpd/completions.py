"""Skrip tab-completion untuk mmpd (bash/zsh/fish)."""

from __future__ import annotations

_BASH = r"""_mmpd() {
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
"""

_ZSH = r"""#compdef mmpd
_arguments -C \
  '(-V --version)'{-V,--version}'[cetak versi]' \
  '(-q --quiet)'{-q,--quiet}'[kurangi output]' \
  '1:command:(download retrofit lyrics organize cache config doctor self-update completion)' \
  '*::arg:->args'

case $state in
  args)
    case $words[1] in
      download)
        _arguments \
          '(-f --format)'{-f,--format}'[format audio]:fmt:(mp3 flac wav best)' \
          '(-o --output)'{-o,--output}'[folder output]:dir:_files -/' \
          '--max[batas lagu]:n:' \
          '--lyrics[mesin lirik]:src:(musixmatch chain youtube-cc cc off none)' \
          '--translate[terjemahkan]' \
          '--no-translate[jangan terjemahkan]' \
          '--transliterate[aksara]:mode:(auto ja zh yue off)' \
          '--lrc-format[format LRC]:fmt:(gabung pisah id_only)' \
          '--isrc[ISRC matching]' \
          '--no-isrc[tanpa ISRC]' \
          '--concurrent[unduh paralel]' \
          '--no-embed[jangan tanam ID3]' \
          '--no-dedup[matikan archive]' \
          '1:url or query:'
        ;;
      retrofit|lyrics|organize)
        _arguments '(-d --dir)'{-d,--dir}'[folder]:dir:_files -/' '--dry-run' '--lyrics-only' '--covers-only'
        ;;
      cache)
        _arguments '--stats' '--clear' '--clear-expired' '--clear-negative'
        ;;
      completion)
        _arguments '1:shell:(bash zsh fish)'
        ;;
    esac
    ;;
esac
"""

_FISH = r"""complete -c mmpd -f
complete -c mmpd -n "__fish_use_subcommand" -a "download" -d "Download non-interaktif"
complete -c mmpd -n "__fish_use_subcommand" -a "retrofit" -d "Perbaiki koleksi lama"
complete -c mmpd -n "__fish_use_subcommand" -a "lyrics" -d "Suntik terjemahan LRC"
complete -c mmpd -n "__fish_use_subcommand" -a "organize" -d "Rapikan audio + LRC"
complete -c mmpd -n "__fish_use_subcommand" -a "cache" -d "Kelola cache"
complete -c mmpd -n "__fish_use_subcommand" -a "config" -d "Kelola config.toml"
complete -c mmpd -n "__fish_use_subcommand" -a "doctor" -d "Diagnostik"
complete -c mmpd -n "__fish_use_subcommand" -a "self-update" -d "Update non-destruktif"
complete -c mmpd -n "__fish_use_subcommand" -a "completion" -d "Cetak skrip completion"
complete -c mmpd -s V -l version -d "Cetak versi"
complete -c mmpd -s q -l quiet -d "Kurangi output"
complete -c mmpd -n "__fish_seen_subcommand_from download" -s f -l format -a "mp3 flac wav best"
complete -c mmpd -n "__fish_seen_subcommand_from download" -l lyrics -a "musixmatch chain youtube-cc cc off none"
complete -c mmpd -n "__fish_seen_subcommand_from download retrofit lyrics" -l transliterate -a "auto ja zh yue off"
complete -c mmpd -n "__fish_seen_subcommand_from download retrofit lyrics" -l lrc-format -a "gabung pisah id_only"
complete -c mmpd -n "__fish_seen_subcommand_from completion" -a "bash zsh fish"
"""


def render_completion(shell: str) -> str:
    shell = (shell or "bash").lower()
    if shell == "zsh":
        return _ZSH.lstrip("\n")
    if shell == "fish":
        return _FISH.lstrip("\n")
    return _BASH.lstrip("\n")
