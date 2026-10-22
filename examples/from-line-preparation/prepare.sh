#!/usr/bin/env bash
# Write separate transformed copies, then concatenate in input order.
set -eu
export LC_ALL=C

usage() {
    printf 'Usage: bash prepare.sh NEW_OUTPUT_DIRECTORY INPUT_FILE...\n       bash prepare.sh --files0-from FILE_LIST NEW_OUTPUT_DIRECTORY\n' >&2
    exit 2
}

[ "$#" -ge 2 ] || usage
if [ "$1" = '--files0-from' ]; then
    [ "$#" -eq 3 ] || usage
    listing=$2
    output=$3
    [ -f "$listing" ] && [ -r "$listing" ] || {
        printf 'Cannot read file list: %s\n' "$listing" >&2
        exit 1
    }
    set --
    # read and set are Bash builtins: no child receives the full path list.
    while true; do
        input=
        if IFS= read -r -d '' input; then
            [ -n "$input" ] || {
                printf 'File list contains an empty pathname.\n' >&2
                exit 1
            }
            set -- "$@" "$input"
        else
            [ -z "$input" ] || {
                printf 'Every pathname must end with a NUL byte.\n' >&2
                exit 1
            }
            break
        fi
    done < "$listing"
    [ "$#" -gt 0 ] || {
        printf 'File list is empty.\n' >&2
        exit 1
    }
else
    output=$1
    shift
fi
command -v perl >/dev/null

# A blank sentinel keeps Bash 3.2's nounset handling of empty arrays happy.
names=("")
for input in "$@"; do
    [ -f "$input" ] && [ -r "$input" ] || {
        printf 'Cannot read input file: %s\n' "$input" >&2
        exit 1
    }
    name=${input##*/}
    for seen in "${names[@]}"; do
        [ "$name" != "$seen" ] || {
            printf 'Input names must be distinct: %s\n' "$name" >&2
            exit 1
        }
    done
    names+=("$name")
done

# mkdir fails if the destination already exists. Never edit the inputs.
mkdir -- "$output"
mkdir -- "$output/parts"
set -C
for input in "$@"; do
    perl -pe 'BEGIN { binmode STDIN; binmode STDOUT; $seen = 0 }
        s/^From/>From/ if /^From/ && ++$seen > 1' \
        < "$input" > "$output/parts/${input##*/}"
done

# Keep the separate copies exact. Only the combined copy adds a missing
# final LF, so the following file cannot start halfway through a line.
for input in "$@"; do
    perl -pe 'BEGIN { binmode STDIN; binmode STDOUT }
        $_ .= "\n" if eof && !/\n\z/' < "$output/parts/${input##*/}"
done > "$output/combined.txt"
