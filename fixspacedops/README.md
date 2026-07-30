fixspacedops.py
===============

Collapse blanks inside Fortran operator tokens in fixed source form files.

Why
---

Blanks are insignificant inside tokens in fixed source form, so this is legal,
and old code is full of it:

    IF(DONE. AND. IERR3.NE.0) THEN
    IF(T2X25 . GT . C4) GO TO 80
    IF(A .A ND. B) GO TO 90

All three mean `.AND.` / `.GT.`. In free source form a blank separates tokens,
so all three are syntax errors. Converting such a file with `fixed2free2.py`
produces free form source that will not compile, reported by gfortran as

    Error: The name 'and' cannot be used as a defined operator

This tool rewrites the operators so the source is valid in both forms. Removing
insignificant blanks does not change the meaning of a fixed form program, so the
edit is a no-op for an existing fixed form build. On a real code base you can
verify that directly by compiling before and after and comparing the object
files, which should be byte identical.

Usage
-----

    fixspacedops.py -n FILE...          # report what would change
    fixspacedops.py -i FILE...          # rewrite in place
    fixspacedops.py FILE                # write converted_FILE
    fixspacedops.py FILE -o OUT         # write OUT

Run it before `fixed2free2.py`.

What it will and will not touch
-------------------------------

Only the intrinsic operators and logical literals are rewritten:

    AND OR NOT EQV NEQV XOR EQ NE LT LE GT GE TRUE FALSE

Anything else between a pair of dots is left alone, because a defined operator
may legitimately be written without blanks and there is no way to tell that a
spaced one was meant to be a single token.

Skipped entirely: comment lines, preprocessor lines, columns 1-6, and anything
beyond column 72. Character literals and Hollerith payloads are stepped over, so
text data is never modified.

The Hollerith handling is not optional in practice. Legacy code contains
constants whose payload holds an apostrophe, for instance the Cs point group
irreducible representation labels A' and A":

    DATA GANT/8HA       ,8HAG      ,8HAU      ,8HA'      ,

A scanner that does not consume `nH` payloads literally treats that apostrophe
as opening a character literal and loses synchronisation for the rest of the
line. The same trap breaks naive comment detection.

Because only blanks are removed, lines can only get shorter, so this can never
push a statement past column 72.

Tests
-----

    python3 -m unittest test_fixspacedops
