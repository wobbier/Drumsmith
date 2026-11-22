"""Drawn textures for StoryEventHorizon: the engraved inductee plaques and the Hall's frieze.

ffmpeg's drawtext does the lettering (ImageMagick isn't on this machine's PATH); the fonts are the
system's DejaVu / Noto serif faces found with fc-match. The names are made up. Deterministic: a
rerun writes the same bytes (bitexact PNG, no metadata), and an unchanged file isn't touched.
"""
import os
import subprocess
import tempfile

from story_event_horizon_mesh import save_bytes

SERIF = None


def font():
    global SERIF
    if SERIF is None:
        for pattern in ('DejaVu Serif:style=Bold', 'Noto Serif:style=Bold', 'serif:bold'):
            r = subprocess.run(['fc-match', '-f', '%{file}', pattern], capture_output=True, text=True)
            if r.returncode == 0 and os.path.exists(r.stdout.strip()):
                SERIF = r.stdout.strip()
                break
    return SERIF


def esc(text):
    return text.replace('\\', '\\\\').replace(':', '\\:').replace("'", "’")


def engrave(text, x, y, size, ink='0x2a1a06', lit='0xffe9b0'):
    """Engraved lettering: a light lip under a dark cut."""
    f = font()
    base = f"drawtext=fontfile='{f}':text='{esc(text)}':fontsize={size}:x={x}:y={y}"
    return [base.replace(f'x={x}:y={y}', f'x={x}+2:y={y}+3') + f':fontcolor={lit}@0.85',
            base + f':fontcolor={ink}']


def render(path, w, h, filters, bg='0xa8803a'):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, 'o.png')
        # Brushed brass: a vertical sheen and fine horizontal streaks, then the lettering.
        sheen = ("geq=r='clip(r(X,Y)*(0.82+0.25*sin(Y/H*3.1)+0.05*sin(X*0.9+Y*0.05)),0,255)':"
                 "g='clip(g(X,Y)*(0.82+0.25*sin(Y/H*3.1)+0.05*sin(X*0.9+Y*0.05)),0,255)':"
                 "b='clip(b(X,Y)*(0.80+0.22*sin(Y/H*3.1)),0,255)'")
        chain = ','.join([sheen] + filters)
        cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c={bg}:s={w}x{h}',
               '-vf', chain, '-frames:v', '1', '-fflags', '+bitexact', '-flags', '+bitexact', out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit('ffmpeg failed: ' + r.stderr)
        save_bytes(path, open(out, 'rb').read())


def frame(w, h, inset=14, ink='0x3b260a'):
    return [f'drawbox=x={inset}:y={inset}:w={w-2*inset}:h={h-2*inset}:color={ink}:t=6',
            f'drawbox=x={inset+14}:y={inset+14}:w={w-2*inset-28}:h={h-2*inset-28}:color={ink}@0.6:t=2']


INDUCTEES = [
    ('CLASS OF THE FIRST ORBIT', ['ADA KESTREL', 'MORRIS QUILL', 'JUNO HALVERSEN', 'TEDDY OKONKWO-RAY',
                                  'LOU FERRANTE', 'MAEVE DUCHARME']),
    ('CLASS OF THE LONG NIGHT', ['RUFUS ABERNATHY', 'SOL VARGA', 'IMOGEN TETHER', 'DEXTER MAHLANGU',
                                 'BIRDIE CALLOWAY', 'OTIS GRUENWALD']),
    ('CLASS OF THE SLOW STARS', ['PILAR ESTEVEZ', 'HAMISH CORRIGAN', 'NOOR AL-SAYED', 'WENDELL PIKE',
                                 'GRETA LINDQVIST', 'CASIMIR BOATENG']),
    ('CLASS OF THE BRASS RINGS', ['MARGO TALLIS', 'FELIX ODUYA', 'ROSA KAMINSKI', 'BENNY HARGREAVES',
                                  'YUKI MORROW', 'AUGUST DELACROIX']),
]


def plaques(folder):
    made = []
    for i, (title, names) in enumerate(INDUCTEES):
        w, h = 1024, 512
        f = frame(w, h) + engrave(title, '(w-text_w)/2', 52, 46)
        f += [f'drawbox=x=120:y=118:w={w-240}:h=4:color=0x3b260a@0.8:t=fill']
        for k, name in enumerate(names):
            col, row = k % 2, k // 2
            x = 70 + col * 470
            f += engrave(name, f'{x}+(440-text_w)/2', 160 + row * 110, 33)
            f += engrave('* * *', f'{x}+(440-text_w)/2', 208 + row * 110, 22, ink='0x4a3210')
        name = f'Plaque_{i+1}.png'
        render(os.path.join(folder, name), w, h, f)
        made.append(name)
    # The empty plate the induction fills (story: the nameplate stays blank on a missed pass).
    w, h = 1024, 512
    render(os.path.join(folder, 'Plaque_Blank.png'), w, h,
           frame(w, h) + engrave('INDUCTEE', '(w-text_w)/2', 70, 54) +
           [f'drawbox=x=180:y=300:w={w-360}:h=4:color=0x3b260a@0.7:t=fill'] +
           engrave('THIS SPACE RESERVED', '(w-text_w)/2', 340, 34, ink='0x4a3210'))
    made.append('Plaque_Blank.png')
    return made


def frieze(folder):
    w, h = 2048, 256
    f = frame(w, h, 10) + engrave('THE DRUMMER HALL OF FAME', '(w-text_w)/2', 70, 100)
    render(os.path.join(folder, 'Frieze.png'), w, h, f, bg='0xb08a40')
    render(os.path.join(folder, 'FriezeBack.png'), w, h,
           frame(w, h, 10) + engrave('EVENT HORIZON STATION  *  ORBIT OF THE LAST LIGHT', '(w-text_w)/2', 86, 76),
           bg='0xb08a40')
    return ['Frieze.png', 'FriezeBack.png']


def make_all(folder):
    return plaques(folder) + frieze(folder)
