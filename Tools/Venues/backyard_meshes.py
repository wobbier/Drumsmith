"""The yard's sign painter, prop shop and rigid-pose tailor. All geometry is in venue metres."""
import importlib.util
import math
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'Art/Venues/Backyard'
MODELS = ROOT / 'Assets/Venues/Backyard/Models'
ATLAS = '../../../Models/Venue/PolygonTown_01_A.png'
spec = importlib.util.spec_from_file_location('yard_geometry', ART / 'Models/Original/generate_original_props.py')
geo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geo)
geo.PALETTE.update({'teal':(738,1271),'ripple':(660,1037),'wine':(192,1180),'slate':(231,1414),'peat':(582,1830),
                    'mud':(75,1518),'canvas':(140,1258),'tape':(478,1076),'jade':(634,1219)})


def save(path, content):
    if not path.exists() or path.read_bytes() != content.encode():
        path.write_bytes(content.encode())
    if path.suffix=='.obj':
        twin=path.with_suffix('.obj.assbin')
        if twin.exists() and twin.stat().st_mtime_ns < max(path.stat().st_mtime_ns,(MODELS/'Yard.mtl').stat().st_mtime_ns):
            twin.unlink()


def mesh_file(mesh, centre=True):
    if centre:
        mesh.finish()
    colours = list(geo.PALETTE)
    coords, normals, faces = {}, {}, []
    for face, ink, _ in mesh.faces:
        xyz = [(round(x, 6), round(y, 6), round(-z, 6)) for x, y, z in reversed(face)]
        cross = geo.cross(geo.sub(xyz[1], xyz[0]), geo.sub(xyz[2], xyz[0]))
        if geo.dot(cross, cross) < 1e-14:
            continue
        n = tuple(round(v, 6) for v in geo.unit(cross))
        ni = normals.setdefault(n, len(normals) + 1)
        ti = colours.index(ink) + 1
        faces.append('f ' + ' '.join(f'{coords.setdefault(p, len(coords)+1)}/{ti}/{ni}' for p in xyz))
    lines = [f'# {mesh.note}', 'mtllib Yard.mtl', 'o ' + mesh.name, 's off']
    lines += ['v %g %g %g' % p for p in coords]
    lines += ['vt %.8f %.8f' % ((x+.5)/2048, 1-(y+.5)/2048) for x, y in geo.PALETTE.values()]
    lines += ['vn %g %g %g' % n for n in normals] + ['usemtl Yard'] + faces
    save(MODELS / (mesh.name + '.obj'), '\n'.join(lines) + '\n')
    return mesh


def practical_glass():
    mesh = geo.Mesh('PracticalGlass', 'Shared faceted glass for festoons and torch tips. Centre pivot; diameter two before scaling.')
    mesh.sphere((0,0,0),1,'white',sides=8,bands=4)
    return mesh_file(mesh,False)


def promote(layout):
    MODELS.mkdir(parents=True, exist_ok=True)
    save(MODELS/'Yard.mtl', 'newmtl Yard\nKd 1 1 1\nKs 0 0 0\nNs 0\nillum 1\nmap_Kd '+ATLAS+'\n')
    for asset in layout['assets']:
        if not asset['path'].startswith('Art/') or asset['id'] == 'Festoon2m':
            continue
        lines = (ROOT / asset['path']).read_text().splitlines()
        clean = [f"# Staged from {asset['path']}", 'mtllib Yard.mtl', 'o '+asset['id'], 'usemtl Yard']
        if asset['id']=='PartyHouse':
            palette=list(geo.PALETTE);group=''
            swap={'main_house':'slate','garage_wing':'peat','roof_fascia':'wood','siding_courses':'peat',
                  'garage_door':'jade','garage_door_seams':'slate','window_trim':'wood','sliding_door_frame':'wine',
                  'sliding_door_glass':'wine','gable_west':'slate','gable_east':'slate','window_mullions':'slate',
                  'roof_railing':'wood','roof_rail_top':'wood','window_upper_2':'navy','window_upper_3':'navy','window_lower_0':'navy'}
            clean += [line for line in lines if line.startswith('v ')]
            clean += ['vt %.8f %.8f'%((x+.5)/2048,1-(y+.5)/2048) for x,y in geo.PALETTE.values()]
            clean += [line for line in lines if line.startswith('vn ')] + ['s off']
            for line in lines:
                if line.startswith('g '):group=line[2:]
                if line.startswith('f '):
                    if group in swap:
                        corners=[c.split('/') for c in line[2:].split()]
                        line='f '+' '.join(f'{v}/{palette.index(swap[group])+1}/{n}' for v,t,n in corners)
                    clean.append(line)
        else:
            clean += [line for line in lines if line.startswith(('v ', 'vt ', 'vn ', 'f ', 's '))]
        save(MODELS/(asset['id']+'.obj'), '\n'.join(clean)+'\n')


GLYPHS = {
    'A': [[(0,0),(.4,1),(.61,1),(1,0)],[(.18,.4),(.80,.4)]],
    'D': [[(0,0),(0,1),(.54,1),(.92,.75),(.90,.24),(.55,0),(0,0)]],
    'E': [[(.92,1),(0,1),(0,0),(.98,0)],[(0,.51),(.78,.51)]],
    'F': [[(0,0),(0,1),(.99,1)],[(.01,.51),(.74,.51)]],
    'M': [[(0,0),(0,1),(.5,.39),(1,1),(1,0)]],
    'R': [[(0,0),(0,1),(.67,1),(.91,.85),(.89,.60),(.65,.47),(0,.47)],[(.50,.47),(1,0)]],
    'S': [[(.92,.87),(.73,1),(.2,.97),(.02,.79),(.07,.62),(.78,.43),(.93,.26),(.83,.08),(.24,0),(0,.13)]],
    'T': [[(0,1),(1,1)],[(.5,1),(.47,0)]],
    'Y': [[(0,1),(.48,.53),(1,1)],[(.48,.54),(.47,0)]],
}


def stripe(m, a, b, width, ink, z):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dy)
    nx, ny = -dy/length*width/2, dx/length*width/2
    ex, ey = dx/length*width*.25, dy/length*width*.25
    points = [(a[0]-ex-nx,a[1]-ey-ny,z),(a[0]-ex+nx,a[1]-ey+ny,z),
              (b[0]+ex+nx,b[1]+ey+ny,z),(b[0]+ex-nx,b[1]+ey-ny,z)]
    m.face(points, ink)


def letters(m, text, x, y, height, width, ink, z, lean=.15):
    for i, letter in enumerate(text):
        for stroke in GLYPHS.get(letter, []):
            pts = [(x + i*width*1.32 + width*a + lean*b*height, y + height*b) for a,b in stroke]
            for a,b in zip(pts,pts[1:]):
                stripe(m,a,b,height*.132,ink,z)


def backdrop():
    m = geo.Mesh('AftersDrop', 'Original hand-lettered, stitched sound-system drop on a crooked pipe. Front -Z.')
    m.tube((-4.73,2.93,0),(4.73,3.12,0),.045,.045,'silver',8)
    edges = [-4.52,-3.63,-2.78,-1.87,-.93,0,.93,1.87,2.78,3.68,4.51]
    for i,(x,b) in enumerate(zip(edges,edges[1:])):
        def edge(t,top):
            sag=(1-(t/4.52)**2)
            return (t, (2.9+.021*t-.18*sag if top else .29+.021*t-.19*sag+.075*math.cos(3*t)),
                    .075*math.sin(2.1*t)+(.02 if top else -.06*sag))
        top,bot= edge(x,True),edge(x,False); nt,nb=edge(b,True),edge(b,False)
        m.face([bot,top,nt,nb], 'navy' if i not in (0,7,9) else 'violet')
        m.face([nb,nt,top,bot], 'navy')
        m.beam((x,2.95+.02*x,-.015),top,.032,'cream')
    m.face([(-4.49,.25,-.145),(-4.49,2.75,-.145),(-2.93,2.70,-.145),(-3.93,.22,-.145)],'pink')
    for x in (-4.29,-4.03,-3.77): stripe(m,(x,.56),(x+.53,1.56),.085,'orange',-.153)
    for x in (-3.19,-3.04,-2.89): stripe(m,(x,2.29),(x+.15,2.51),.057,'aqua',-.16)
    letters(m,'AFTERS',-3.15,.67,1.32,.93,'pink',-.172)
    letters(m,'AFTERS',-3.23,.75,1.32,.93,'cream',-.185)
    stripe(m,(-2.42,.47),(2.96,.54),.055,'aqua',-.19)
    for i in range(13): stripe(m,(2.15+i*.142,2.24),(2.21+i*.142,2.42),.04 if i%3 else .095,'silver',-.19)
    for x in (-4.22,4.24):
        for y in (.49,2.52):
            m.tube((x,y,-.20),(x,y,-.22),.069,.069,'silver',8)
            m.tube((x,y,-.224),(x,y,-.229),.031,.031,'black',7)
    return mesh_file(m)


def decks():
    m=geo.Mesh('DoorDecks','A salvaged door, open milk crates, vinyl decks, tonearms, faders and patch leads.')
    for x in (-.96,.95):
        for k in range(2):
            cy=.19+.37*k
            for side in (-1,1):
                for dy in (-.156,.15): m.box((x,cy+dy,side*.27),(.58,.047,.045),'aqua' if k==0 else 'navy')
                for dx in (-.26,0,.26): m.box((x+dx,cy,side*.27),(.034,.33,.042),'blue')
                m.box((x+side*.27,cy+.15,0),(.044,.047,.55),'aqua')
                m.beam((x-.235,cy-.13,side*.27),(x+.235,cy+.13,side*.27),.027,'blue')
    m.box((0,.77,0),(2.9,.08,.84),'wood_light');m.box((0,.829,.02),(2.50,.049,.65),'black')
    for x in (-.76,.75):
        m.box((x,.877,0),(.83,.075,.60),'silver')
        m.tube((x,.916,0),(x,.94,0),.255,.252,'rubber',16)
        m.tube((x,.941,0),(x,.95,0),.085,.085,'pink' if x<0 else 'yellow',12)
        m.beam((x+.32,.959,.22),(x+.255,.991,.10),.018,'cream');m.beam((x+.255,.991,.10),(x+.18,.956,.03),.018,'silver')
    m.box((0,.89,0),(.48,.09,.61),'navy')
    for row in range(3):
        for j in range(4): m.tube((-.15+j*.096,.938,-.16+row*.08),(-.15+j*.096,.975,-.16+row*.08),.024,.020,'cream' if row%2 else 'orange',6)
    for i in range(4): m.box((-.16+i*.099,.948,.14),(.021,.012,.12),'silver');m.box((-.16+i*.099,.971,.1+i*.025),(.052,.035,.024),'yellow')
    for x in (-1.15,1.14):
        m.beam((x,.84,-.32),(x+.07,.58,-.46),.02,'rubber');m.beam((x+.07,.58,-.46),(x-.03,.09,-.38),.021,'rubber')
    return mesh_file(m)


def paper_cup():
    m=geo.Mesh('PaperCup','Soft red party cup with a rolled ivory lip, pressed ribs and a dark open mouth.')
    layers=[(0,.034,'wine'),(.016,.035,'pink'),(.034,.037,'wine'),(.038,.037,'pink'),(.087,.048,'pink'),
            (.091,.049,'wine'),(.096,.050,'pink'),(.146,.054,'pink'),(.149,.056,'canvas'),(.155,.056,'canvas'),(.155,.050,'canvas'),(.143,.05,'wine')]
    for (y,r,ink),(ny,nr,_) in zip(layers,layers[1:]):
        for i in range(10):
            a,b=i*math.tau/10,(i+1)*math.tau/10
            m.face([(r*math.cos(b),y,r*math.sin(b)),(r*math.cos(a),y,r*math.sin(a)),(nr*math.cos(a),ny,nr*math.sin(a)),(nr*math.cos(b),ny,nr*math.sin(b))],ink)
    m.tube((0,.127,0),(0,.130,0),.050,.050,'wine',10)
    return mesh_file(m)


def throw():
    m=geo.Mesh('BeachTowel','Crooked striped beach towel folded over a cushion; hem and short knotted fringe.')
    profile=[(-.52,.06),(-.51,.26),(-.47,.49),(-.43,.61),(-.28,.645),(-.06,.653),(.18,.65)]
    for j in range(10):
        x0,x1=-.35+.07*j,-.35+.07*(j+1)
        for i,((z,y),(nz,ny)) in enumerate(zip(profile,profile[1:])):
            def v(x,z,y):return(x,y+.016*math.cos(15*x)+.014*math.sin(4*x+z*6),z+.04*x)
            pts=[v(x0,z,y),v(x1,z,y),v(x1,nz,ny),v(x0,nz,ny)]
            ink=['ripple','canvas','teal','teal','ripple','canvas','ripple','tape','canvas','teal'][j]
            m.face(pts,ink);m.face(pts[::-1],ink)
        x=(x0+x1)/2;m.tube((x,.073,-.526),(x+.012,.01,-.516),.006,.004,'canvas',4)
    return mesh_file(m,False)


def picnic_rug():
    m=geo.Mesh('PicnicRug','The kitchen runner dragged out beside the sofa: woven diamonds, striped ends and a dog-eared corner.')
    m.face([(-1.21,0,-.52),(-1.21,0,.52),(1.10,0,.52),(1.21,.027,.40),(1.21,0,-.52)],'jade')
    for sign in (-1,1):
        for n,ink in ((.92,'tape'),(.979,'pink'),(1.064,'ripple')):
            x=sign*n;m.face([(x-.018,.004,-.505),(x-.018,.004,.505),(x+.018,.004,.505),(x+.018,.004,-.505)],ink)
    for x in (-.62,-.21,.21,.62):
        pts=[(x-.18,.005,0),(x,.005,.19),(x+.18,.005,0),(x,.005,-.19)];m.face(pts,'teal')
        m.face([(x-.08,.008,0),(x,.008,.08),(x+.08,.008,0),(x,.008,-.08)],'ripple')
    return mesh_file(m,False)


def flyers():
    m=geo.Mesh('GateFlyers','Wheat-pasted plywood: offset ink, torn overlapping sheets, hand-painted arrow and a spiral sun.')
    m.box((0,.93,0),(1.16,1.86,.068),'wood')
    m.face([(-.52,.34,-.041),(-.52,1.78,-.041),(.49,1.73,-.041),(.45,.27,-.041)],'pink')
    m.face([(-.45,.47,-.052),(-.38,1.65,-.052),(.46,1.61,-.052),(.41,.51,-.052),(.18,.53,-.052),(.16,.45,-.052)],'cream')
    for i in range(14):
        a=i*math.tau/14
        stripe(m,(.01+math.cos(a)*.13,1.33+math.sin(a)*.13),(.01+math.cos(a)*(.20+.023*(i%3)),1.33+math.sin(a)*.22),.023,'pink',-.058)
    letters(m,'YARD',-.37,.94,.16,.14,'black',-.068);letters(m,'FM',-.31,.64,.20,.16,'black',-.07)
    stripe(m,(.14,.75),(.32,.77),.04,'pink',-.073);stripe(m,(.25,.84),(.33,.77),.042,'pink',-.073);stripe(m,(.25,.69),(.33,.77),.042,'pink',-.073)
    for x in (-.42,.42): stripe(m,(x-.04,1.73),(x+.10,1.77),.047,'silver',-.08)
    return mesh_file(m)


def canopy():
    m=geo.Mesh('PatchworkFly','Rope-tensioned sail made from three odd awnings; both cloth faces, contrasting seams and tied corners.')
    def v(u,t):
        return ((u-.5)*6.3, 1.02+.58*u-.72*t-.65*math.sin(u*math.pi)*math.sin(t*math.pi)+.27*math.sin(3*u+t), (t-.5)*3.4+.65*u)
    for i in range(6):
        for j in range(2):
            pts=[v(i/6,j/2),v((i+1)/6,j/2),v((i+1)/6,(j+1)/2),v(i/6,(j+1)/2)]
            ink=['pink','orange','cream','pink','violet','orange'][i]
            m.face(pts,ink);m.face(pts[::-1],ink)
        for j in range(2): m.beam(v(i/6,j/2),v(i/6,(j+1)/2),.024,'silver')
    for u in (0,1):
        for t in (0,1):
            a=v(u,t);m.beam(a,(a[0]+(.8 if u else -.8),a[1]+.12,a[2]+(.6 if t else -.6)),.031,'cream')
    return mesh_file(m)


def shutter():
    m=geo.Mesh('RadioShutter','A backyard pirate-radio mural brushed across a salvaged corrugated shutter. Front -Z.')
    for band in range(9):
        y=.12+band*.25
        m.box((0,y,0),(4.24,.244,.028),'jade' if band%3!=1 else 'navy')
    m.face([(-2.08,.13,-.025),(-2.08,2.10,-.025),(-.02,2.10,-.025),(-.77,.15,-.025)],'wine')
    for k in range(8):
        x=-1.91+.19*k;stripe(m,(x,.37),(x+.13,.54),.043,'pink',-.04)
    letters(m,'YARD',-1.83,1.14,.60,.47,'canvas',-.051)
    letters(m,'FM',-.92,.40,.49,.40,'pink',-.054)
    for n in (1,2,3):
        points=[(.85+(.20+n*.18)*math.cos(i*.16-.89),1.16+(.20+n*.18)*math.sin(i*.16-.89)) for i in range(13)]
        for a,b in zip(points,points[1:]):stripe(m,a,b,.054,'ripple' if n!=2 else 'tape',-.044)
    for i in range(3):
        for j in range(6):
            if (i+j)%2==0:m.box((1.43+j*.089,.24+i*.089,-.046),(.081,.081,.004),'canvas')
    return mesh_file(m)


def water_traces():
    m=geo.Mesh('PoolWakes','Broken low-poly reflections: three quiet crests, the float and two sets of feet.')
    def arc(x,z,r,a,b,thick,col):
        pts=[(x+r*math.cos(t),z+r*.65*math.sin(t)) for t in [a+(b-a)*i/8 for i in range(9)]]
        for i,(p,q) in enumerate(zip(pts,pts[1:])):
            dx,dz=q[0]-p[0],q[1]-p[1];length=math.hypot(dx,dz);w=thick*(.31+.69*math.sin((i+.5)*math.pi/8))
            nx,nz=-dz/length*w,dx/length*w
            m.face([(p[0]-nx,0,p[1]-nz),(p[0]+nx,0,p[1]+nz),(q[0]+nx,0,q[1]+nz),(q[0]-nx,0,q[1]-nz)],col)
    for x,z,r in [(7.2,-4.7,.74),(8.98,-7.7,.68),(7.8,-8.72,.65),(8.68,-9.05,.38),(7.62,-9.07,.41)]:
        arc(x,z,r,-.2,2.5,.020,'ripple');arc(x,z,r+.18,1.35,3.4,.013,'teal');arc(x,z,r+.35,.35,1.9,.012,'ripple')
    arc(7.81,-6.45,.88,.14,1.84,.021,'ripple');arc(8.13,-6.47,.82,.45,1.51,.013,'teal')
    return mesh_file(m,False)


def party_traces():
    m=geo.Mesh('PatioMorning','Scuffed grass, crushed cans, bent paper flyers and confetti footprints left by the party.')
    rng=random.Random(22619)
    for cx,cz,dx,dz in [(-3.1,-19,2.6,1.0),(-9.1,-6,2,.7),(4,-15,3,1.6),(-1.3,-7,2.2,.7),(5.2,.65,1.4,.6)]:
        for _ in range(5):
            x,z=cx+rng.uniform(-dx,dx),cz+rng.uniform(-dz,dz);a,b=rng.uniform(.18,.55),rng.uniform(.10,.30)
            pts=[(x+a*math.cos(i*math.tau/7)*rng.uniform(.7,1.2),.008,z+b*math.sin(i*math.tau/7)*rng.uniform(.7,1.2)) for i in range(7)]
            m.face(pts[::-1],rng.choice(['peat','mud','jade']))
        for i in range(14):
            x,z=cx+rng.uniform(-dx,dx),cz+rng.uniform(-dz,dz)
            if i%6==0:
                p=[(x-.075,.018,z-.042),(x-.045,.032,z+.08),(x+.074,.016,z+.059),(x+.057,.029,z-.054)]
                m.face(p,'canvas');m.face(p[::-1],'canvas')
            elif i%5==0:
                m.tube((x,.032,z),(x+.081,.035,z+.046),.028,.023,'silver',7)
                m.tube((x+.016,.034,z+.01),(x+.057,.035,z+.034),.029,.027,'pink',7)
            else:
                a=rng.uniform(0,math.tau);ex,ez=.043*math.cos(a),.043*math.sin(a)
                p=[(x,.017,z),(x-ez*.31,.018,z+ex*.31),(x+ex,.022,z+ez)];m.face(p,rng.choice(['pink','tape','canvas','aqua']));m.face(p[::-1],'canvas')
    return mesh_file(m,False)


def bent_part(person, piece, bend):
    name = f'{person}_{piece}_{bend}'
    src = ROOT/'Assets/Models/People/Crowd'/person/(piece+'.obj')
    verts, rest_y, uv, faces = [],[],[],[]
    elbow, hip, knee = -.323, .8763, .46
    def smooth(v):
        v=max(0,min(1,v));return v*v*(3-2*v)
    for line in src.read_text().splitlines():
        if line.startswith('v '):
            x,y,nz=map(float,line.split()[1:]);z=-nz;rest_y.append(y)
            if piece=='Legs':
                ang=math.radians(79);y1=.57+(y-hip)*math.cos(ang)+z*math.sin(ang);z1=-(y-hip)*math.sin(ang)+z*math.cos(ang)
                w=smooth((y-.37)/.19);ty=(.49+y-knee)*(1-w)+y1*w;tz=(.405+z)*(1-w)+z1*w
                w=smooth((y-.81)/.10);ty=ty*(1-w)+(y-hip+.57)*w;tz=tz*(1-w)+z*w
            else:
                ang=math.radians(bend);w=smooth((-.23-y)/.17)
                ty=y*(1-w)+(elbow+(y-elbow)*math.cos(ang)+z*math.sin(ang))*w
                tz=z*(1-w)+(-(y-elbow)*math.sin(ang)+z*math.cos(ang))*w
            verts.append((x,ty,-tz))
        elif line.startswith('vt '): uv.append(line)
        elif line.startswith('f '): faces.append([tuple(map(int,x.split('/'))) for x in line.split()[1:]])
    lines=['# Posed from '+str(src.relative_to(ROOT)),'mtllib Yard.mtl','o '+name,'s off','usemtl Yard']
    lines += ['v %.5f %.5f %.5f'%p for p in verts]+uv
    denim=piece=='Legs' and person=='Daughter_01'
    tones=('blue','teal','canvas','wine','ripple')
    if denim:
        for ink in tones:
            x,y=geo.PALETTE[ink];lines.append('vt %.8f %.8f'%((x+.5)/2048,1-(y+.5)/2048))
    for i,face in enumerate(faces,1):
        a,b,c=[verts[x[0]-1] for x in face];n=geo.cross(geo.sub(b,a),geo.sub(c,a));n=geo.unit(n) if geo.dot(n,n)>1e-15 else (0,1,0)
        if denim:
            h=sum(rest_y[v-1] for v,t,k in face)/3
            ink=2 if h<.105 else 3 if h<.136 else 4 if h<.18 else 0 if a[0]<0 else 1
            face=[(v,len(uv)+ink+1,k) for v,t,k in face]
        lines+=['vn %.5f %.5f %.5f'%n,'f '+' '.join(f'{v}/{t}/{i}' for v,t,_ in face)]
    save(MODELS/(name+'.obj'),'\n'.join(lines)+'\n')
    return f'Assets/Venues/Backyard/Models/{name}.obj'
