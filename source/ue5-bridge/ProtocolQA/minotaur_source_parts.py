"""Resolve the stock Minotaur part IDs for a private conversion, never edit MPKs.

Both the installed archive and the official live manifest's archive contain a
contiguous block of decimal IDs (1400.038407 through 1468.499289). The map
references their integer portions. Keep this accommodation local to the
Minotaur candidate; reject ambiguous keys instead of silently replacing parts.
"""
from decimal import Decimal, InvalidOperation


def resolve_parts(rows):
    parts, fractional = {}, []
    for row in rows:
        if not row:
            continue
        key = row[0].strip()
        if key.isdigit():
            if key in parts and 1400 <= int(key) < 1469:
                raise ValueError('Duplicate part ID: '+key)
            # Preserve the existing converter's last-row behavior outside the
            # candidate block; unrelated stock duplicate IDs are not repaired here.
            parts[key] = row
        elif '.' in key:
            try:
                number = Decimal(key)
            except InvalidOperation:
                continue
            if not number.is_finite() or not 1400 <= number < 1469:
                raise ValueError('Unreviewed fractional part ID: '+key)
            integer = int(number)
            if number-integer <= 0 or number-integer >= Decimal('0.5'):
                raise ValueError('Unexpected Minotaur fractional ID: '+key)
            if len(row) < 6 or row[5].strip() not in {'20', '21'}:
                raise ValueError('Unexpected Minotaur archive: '+key)
            fractional.append((str(integer), row))
    if fractional and {int(key) for key, _ in fractional} != set(range(1400, 1469)):
        raise ValueError('Incomplete stock fractional part block')
    aliases = {}
    for key, row in fractional:
        if key in parts:
            raise ValueError('Ambiguous Minotaur part ID: '+key)
        parts[key] = row
        aliases[key] = {'source_id': row[0], 'mesh': row[2], 'archive': row[5]}
    return parts, aliases
