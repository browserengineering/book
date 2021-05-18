FNR == 1 {
    if (NR > 1) { printf "%6s  %4s  %s\n", words, code, LASTFILENAME }
    skip = 0; words = 0; code = 0;
}
/```/ { skip = 1 - skip }
skip { code += 1 }
! skip { words += NF }
{ LASTFILENAME = FILENAME }
END { printf "%6s  %4s  %s\n", words, code, FILENAME }
