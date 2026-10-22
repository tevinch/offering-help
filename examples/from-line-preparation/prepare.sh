#!/usr/bin/env bash
# Write separate transformed copies, then concatenate in argument order.
set -eu
export LC_ALL=C

if [ "$#" -lt 2 ]; then
    printf 'Usage: bash prepare.sh NEW_OUTPUT_DIRECTORY INPUT_FILE...\n' >&2
    exit 2
fi
output=$1
shift
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
