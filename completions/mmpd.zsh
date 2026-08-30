#compdef mmpd
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
