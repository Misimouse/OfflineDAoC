# Original world clock integration

The native Time window displays the original server's game time. The bridge calls the
installed Godot Server.game_hour helper unchanged, preserving day/night interpolation
and the faster original night rate. It does not use the computer's wall clock or add a
second time simulation. Missing, malformed or out-of-world time hides the display.

The original timedisp artwork is copied byte for byte, with its original 100 × 32 logical
size, 24-hour text and initial position. Its painted close cross is interactive. The
original move handle drags it; Esc > Windows > Time recovers it. Position and visibility
persist per character, use the existing interface scale and remain within the viewport.
Reset Window Layout restores placement. No new keyboard binding or gameplay action is
invented for the clock.

Verification distinguishes three paths: exact original time-helper and transport tests;
two ordinary players receiving real original server time and returning to character
selection through normal saved logout; and the actual Unreal Slate window, including
close, drag capture, visibility, formatting, saved layout and a rendered screenshot.
The previous native packages run against the same private candidate. Installation requires
their evidence, exact predecessor files, the original image hash, backups and rollback.

No server rules, played database or WORK map changes belong to this delivery. Owner
gameplay review is deferred as requested. When ready, check Time progresses, move and
close/recover it through Windows, change UI scale, re-enter a character, and return to
character selection. Day/night lighting, weather and the entire migration are separate
acceptance scopes.
