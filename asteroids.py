import pygame
import random
import math
import sys
import json
import os
import array

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

# ── Constants ─────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 900, 700
FPS = 60
WHITE    = (255, 255, 255)
BLACK    = (0,   0,   0)
GRAY     = (180, 180, 180)
RED      = (220,  50,  50)
ORANGE   = (255, 140,   0)
CYAN     = (0,   220, 255)
YELLOW   = (255, 230,   0)
GREEN    = (50,  200,  80)
PURPLE   = (180,  60, 220)
DARK_RED = (140,  20,  20)
GOLD     = (255, 200,  40)
PINK     = (255, 100, 200)
TEAL     = (0,   200, 180)

fullscreen = False
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Asteroid Dodge")
clock  = pygame.time.Clock()
render_surf = pygame.Surface((WIDTH, HEIGHT))

font_big   = pygame.font.SysFont("consolas", 48, bold=True)
font_med   = pygame.font.SysFont("consolas", 28)
font_small = pygame.font.SysFont("consolas", 20)
font_tiny  = pygame.font.SysFont("consolas", 16)

stars = [(random.randint(0,WIDTH), random.randint(0,HEIGHT), random.uniform(0.5,2.5)) for _ in range(200)]

LEADERBOARD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leaderboard.json")

# ── Sound synthesis (no files needed) ────────────────────────────────────────
def make_sound(freq=440, duration=0.08, wave="sine", vol=0.3, decay=True):
    sr = 44100
    n  = int(sr * duration)
    buf = array.array('h', [0] * n)
    for i in range(n):
        t = i / sr
        if wave == "sine":
            s = math.sin(2 * math.pi * freq * t)
        elif wave == "square":
            s = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
        elif wave == "noise":
            s = random.uniform(-1, 1)
        elif wave == "sweep":
            f2 = freq * 0.3
            ft = freq + (f2 - freq) * i / n
            s = math.sin(2 * math.pi * ft * t)
        else:
            s = math.sin(2 * math.pi * freq * t)
        if decay:
            s *= (1 - i / n)
        buf[i] = int(s * vol * 32767)
    sound = pygame.sndarray.make_sound(buf)
    return sound

try:
    SFX = {
        "shoot":       make_sound(800,  0.06, "square", 0.15),
        "hit":         make_sound(150,  0.12, "noise",  0.35),
        "boss_hit":    make_sound(300,  0.10, "square", 0.25),
        "boss_die":    make_sound(80,   0.40, "sweep",  0.45),
        "powerup":     make_sound(660,  0.20, "sine",   0.35),
        "shield":      make_sound(440,  0.15, "sine",   0.28),
        "extra_life":  make_sound(880,  0.25, "sine",   0.35),
        "boss_spawn":  make_sound(120,  0.30, "sweep",  0.50),
        "level_up":    make_sound(550,  0.30, "sine",   0.40),
    }
    SOUND_ON = True
except Exception:
    SFX = {}
    SOUND_ON = False

def play(name):
    if SOUND_ON and name in SFX:
        SFX[name].play()

# ── Helpers ───────────────────────────────────────────────────────────────────
def toggle_fullscreen():
    global fullscreen, screen
    fullscreen = not fullscreen
    screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN) if fullscreen else pygame.display.set_mode((WIDTH,HEIGHT), pygame.RESIZABLE)

def blit_scaled():
    sw, sh = screen.get_size()
    screen.blit(pygame.transform.scale(render_surf,(sw,sh)),(0,0))
    pygame.display.flip()

def mouse_pos():
    mx,my = pygame.mouse.get_pos()
    sw,sh = screen.get_size()
    return int(mx*WIDTH/sw), int(my*HEIGHT/sh)

def draw_text_centered(surf, text, font, color, cx, cy):
    s = font.render(text, True, color)
    surf.blit(s,(cx-s.get_width()//2, cy-s.get_height()//2))

def distance(ax,ay,bx,by): return math.hypot(ax-bx,ay-by)

def draw_stars():
    for sx,sy,sr in stars:
        pygame.draw.circle(render_surf,(200,200,255),(int(sx),int(sy)),int(sr))

def handle_common_keys(event):
    if event.type == pygame.QUIT: pygame.quit(); sys.exit()
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_F11: toggle_fullscreen()

def draw_button(surf, text, x, y, w, h, hover):
    col  = (30,180,80) if hover else (20,120,55)
    bord = GREEN       if hover else CYAN
    pygame.draw.rect(surf, col,  (x,y,w,h), border_radius=10)
    pygame.draw.rect(surf, bord, (x,y,w,h), 2, border_radius=10)
    lbl = font_med.render(text, True, WHITE)
    surf.blit(lbl,(x+w//2-lbl.get_width()//2, y+h//2-lbl.get_height()//2))

def btn_hit(x,y,w,h):
    mx,my = mouse_pos()
    return x<=mx<=x+w and y<=my<=y+h

# ── Leaderboard ───────────────────────────────────────────────────────────────
def load_leaderboard():
    try:
        if os.path.exists(LEADERBOARD_FILE):
            with open(LEADERBOARD_FILE,"r") as f:
                data = json.load(f)
            if isinstance(data, list): return data
    except Exception as e: print(f"LOAD ERROR: {e}")
    return []

def save_score(name, score):
    scores = load_leaderboard()
    scores.append({"name":str(name),"score":int(score)})
    scores.sort(key=lambda x:x["score"],reverse=True)
    scores = scores[:10]
    try:
        with open(LEADERBOARD_FILE,"w") as f: json.dump(scores,f,indent=2)
        print(f"SAVED OK: '{name}' scored {score}")
    except Exception as e: print(f"SAVE ERROR: {e}")
    return scores

def draw_leaderboard(surf, scores, highlight_score=None):
    pw,ph = 420,390
    px,py = WIDTH//2-pw//2, HEIGHT//2-ph//2+40
    pygame.draw.rect(surf,(10,10,35),(px,py,pw,ph),border_radius=12)
    pygame.draw.rect(surf,CYAN,(px,py,pw,ph),2,border_radius=12)
    draw_text_centered(surf,"HIGH SCORES",font_med,GOLD,WIDTH//2,py+26)
    pygame.draw.line(surf,CYAN,(px+16,py+50),(px+pw-16,py+50),1)
    fresh = load_leaderboard()
    if not fresh:
        draw_text_centered(surf,"No scores yet!",font_small,GRAY,WIDTH//2,py+ph//2)
        return
    highlighted = False
    for i,e in enumerate(fresh[:10]):
        ry = py+62+i*30
        is_new = (not highlighted) and (highlight_score is not None) and (e["score"]==highlight_score)
        if is_new: highlighted=True
        color = GOLD if i==0 else (CYAN if i==1 else (ORANGE if i==2 else WHITE))
        if is_new:
            pygame.draw.rect(surf,(20,50,20),(px+8,ry-3,pw-16,24),border_radius=4)
            color=GREEN
        surf.blit(font_small.render(f"#{i+1}",True,color),(px+14,ry))
        surf.blit(font_small.render(e["name"][:12],True,color),(px+70,ry))
        sc=font_small.render(str(e["score"]),True,color)
        surf.blit(sc,(px+pw-16-sc.get_width(),ry))

# ── Power-ups ─────────────────────────────────────────────────────────────────
POWERUP_TYPES = [
    {"kind":"shield",      "color":(0,180,255),  "label":"SHIELD",       "duration":300},
    {"kind":"rapidfire",   "color":(255,200,0),  "label":"RAPID FIRE",   "duration":300},
    {"kind":"tripleshot",  "color":(0,255,120),  "label":"TRIPLE SHOT",  "duration":300},
    {"kind":"slowmo",      "color":(180,0,255),  "label":"SLOW MO",      "duration":240},
    {"kind":"extralife",   "color":(255,80,80),  "label":"+1 LIFE",      "duration":0},
    {"kind":"magnet",      "color":(255,140,0),  "label":"SCORE x2",     "duration":360},
]

def spawn_powerup(x, y):
    t = random.choice(POWERUP_TYPES)
    return {"x":float(x),"y":float(y),"vy":1.5,"r":16,
            "kind":t["kind"],"color":t["color"],"label":t["label"],
            "duration":t["duration"],"alive":True,"tick":0}

def draw_powerup(surf, p):
    x,y = int(p["x"]),int(p["y"])
    p["tick"]+=1
    pulse = abs(math.sin(p["tick"]*0.08))*4
    r = int(p["r"]+pulse)
    # glow ring
    pygame.draw.circle(surf, p["color"], (x,y), r+4, 2)
    pygame.draw.circle(surf, WHITE,      (x,y), r,   0)
    pygame.draw.circle(surf, p["color"], (x,y), r-2, 0)
    lbl = font_tiny.render(p["label"][:3], True, BLACK)
    surf.blit(lbl,(x-lbl.get_width()//2, y-lbl.get_height()//2))

# ── Debris ────────────────────────────────────────────────────────────────────
DEBRIS_TYPES = [
    {"color":GRAY,   "shape":"rock",      "r":28, "speed":(1.5,3.0)},
    {"color":GRAY,   "shape":"rock",      "r":16, "speed":(2.0,4.0)},
    {"color":CYAN,   "shape":"satellite", "r":22, "speed":(1.2,2.5)},
    {"color":ORANGE, "shape":"station",   "r":20, "speed":(1.0,2.0)},
    {"color":RED,    "shape":"capsule",   "r":18, "speed":(1.8,3.5)},
    {"color":YELLOW, "shape":"panel",     "r":24, "speed":(1.0,2.2)},
]

def spawn_debris(speed_mult=1.0):
    t = random.choice(DEBRIS_TYPES)
    spd = random.uniform(*t["speed"]) * speed_mult
    ang = random.uniform(70,110)
    return {"x":float(random.randint(0,WIDTH)),"y":float(-t["r"]-5),
            "vx":math.cos(math.radians(ang))*spd*random.choice([-1,1]),
            "vy":math.sin(math.radians(ang))*spd,
            "r":t["r"],"color":t["color"],"shape":t["shape"],
            "rot":0,"rot_speed":random.uniform(-2,2),
            "seed":random.randint(0,99999)}

def draw_debris(surf, d):
    x,y,r,rot = int(d["x"]),int(d["y"]),d["r"],d["rot"]
    rad = math.radians(rot)
    if d["shape"]=="rock":
        seed=d.get("seed",12345); rng=random.Random(seed); n=10
        pts=[(x+math.cos(math.radians(rot+i*(360/n)))*r*rng.uniform(0.65,1.0),
              y+math.sin(math.radians(rot+i*(360/n)))*r*rng.uniform(0.65,1.0)) for i in range(n)]
        pygame.draw.polygon(surf,(60,55,50),pts)
        pts2=[(x-3+math.cos(math.radians(rot+i*(360/n)))*r*rng.uniform(0.4,0.65),
               y-3+math.sin(math.radians(rot+i*(360/n)))*r*rng.uniform(0.4,0.65)) for i in range(n)]
        pygame.draw.polygon(surf,(105,95,85),pts2)
        pygame.draw.polygon(surf,(155,145,135),pts,2)
        for _ in range(2):
            ca=rng.uniform(0,2*math.pi); cd=rng.uniform(0,r*0.4); cr=rng.randint(3,max(4,r//5))
            pygame.draw.circle(surf,(38,35,32),(int(x+math.cos(ca)*cd),int(y+math.sin(ca)*cd)),cr)
            pygame.draw.circle(surf,(78,72,65),(int(x+math.cos(ca)*cd),int(y+math.sin(ca)*cd)),cr,1)
        pygame.draw.circle(surf,(200,192,180),(x-r//4,y-r//4),max(2,r//7))
    elif d["shape"]=="satellite":
        bw,bh=r,r//2
        pygame.draw.rect(surf,(30,60,80),(x-bw//2+2,y-bh//2+2,bw,bh),border_radius=3)
        pygame.draw.rect(surf,(60,120,160),(x-bw//2,y-bh//2,bw,bh),border_radius=3)
        pygame.draw.rect(surf,(100,180,220),(x-bw//2,y-bh//2,bw,bh),2,border_radius=3)
        for rx2,ry2 in [(-bw//2+4,-bh//2+4),(bw//2-6,-bh//2+4),(-bw//2+4,bh//2-6),(bw//2-6,bh//2-6)]:
            pygame.draw.circle(surf,(180,220,255),(x+rx2,y+ry2),2)
        pygame.draw.line(surf,(150,150,150),(x+2,y-bh//2),(x+r//2+4,y-bh//2-r//2),2)
        pygame.draw.circle(surf,WHITE,(x+r//2+4,y-bh//2-r//2),3)
        pygame.draw.rect(surf,(20,20,60),(x-bw//2-r,y-5,r-2,10),border_radius=1)
        pygame.draw.rect(surf,(60,80,200),(x-bw//2-r,y-5,r-2,10),1,border_radius=1)
        for px2 in range(x-bw//2-r+3,x-bw//2-4,5):
            pygame.draw.line(surf,(80,100,220),(px2,y-4),(px2,y+4),1)
        bend=math.radians(25); px3=x+bw//2+int(math.cos(bend)*(r-2)); py3=y+int(math.sin(bend)*(r-2))
        pygame.draw.line(surf,(30,30,80),(x+bw//2,y),(px3,py3),8)
        pygame.draw.line(surf,(60,80,200),(x+bw//2,y),(px3,py3),6)
        pygame.draw.circle(surf,(200,230,255),(x-2,y-2),2)
    elif d["shape"]=="station":
        pygame.draw.circle(surf,(50,50,70),(x+1,y+1),r//2+1)
        pygame.draw.circle(surf,(80,100,130),(x,y),r//2)
        pygame.draw.circle(surf,(120,150,190),(x,y),r//2,2)
        for i in range(4):
            a=math.radians(rot+i*90); full=i<2; length=r if full else r*0.45
            ex2,ey2=int(x+math.cos(a)*length),int(y+math.sin(a)*length)
            col=(100,120,150) if full else (80,60,50)
            pygame.draw.line(surf,col,(x,y),(ex2,ey2),5)
            if full:
                pygame.draw.circle(surf,(130,160,200),(ex2,ey2),7)
                pygame.draw.circle(surf,(180,210,240),(ex2,ey2),7,1)
                pygame.draw.circle(surf,CYAN,(ex2,ey2),3)
            else:
                pygame.draw.circle(surf,(100,60,40),(ex2,ey2),4)
        pygame.draw.circle(surf,(40,60,90),(x,y),r//4)
        pygame.draw.circle(surf,CYAN,(x,y),r//4,1)
        pygame.draw.circle(surf,(150,210,255),(x-2,y-2),3)
    elif d["shape"]=="capsule":
        hw=r//2; hh=r
        pygame.draw.ellipse(surf,(80,10,10),(x-hw//2+2,y-hh+2,hw,hh*2))
        pygame.draw.ellipse(surf,(160,30,30),(x-hw//2,y-hh,hw,hh*2))
        pygame.draw.rect(surf,YELLOW,(x-hw//2,y-hh//3,hw,hh//5))
        pygame.draw.rect(surf,YELLOW,(x-hw//2,y+hh//5,hw,hh//5))
        pygame.draw.ellipse(surf,(220,80,80),(x-hw//2,y-hh,hw,hh*2),2)
        pygame.draw.ellipse(surf,(200,200,100),(x-hw//2,y-hh,hw,hh//4))
        pygame.draw.ellipse(surf,(200,200,100),(x-hw//2,y+hh-hh//4,hw,hh//4))
        pygame.draw.rect(surf,(200,150,0),(x-hw//2+2,y-4,hw-4,8),border_radius=2)
        lbl=font_tiny.render("!",True,BLACK); surf.blit(lbl,(x-lbl.get_width()//2,y-4))
        pygame.draw.line(surf,(255,180,180),(x-hw//2+3,y-hh+4),(x-hw//2+3,y+hh-4),1)
    elif d["shape"]=="panel":
        corners=[(-r,-r//4),(r,-r//4),(r,r//4),(-r,r//4)]
        rpts=[(x+cx*math.cos(rad)-cy*math.sin(rad),y+cx*math.sin(rad)+cy*math.cos(rad)) for cx,cy in corners]
        spts=[(px2+2,py2+2) for px2,py2 in rpts]
        pygame.draw.polygon(surf,(5,10,30),spts)
        pygame.draw.polygon(surf,(10,15,60),rpts)
        for ci in range(1,4):
            frac=ci/4
            tx=rpts[0][0]+(rpts[1][0]-rpts[0][0])*frac; ty=rpts[0][1]+(rpts[1][1]-rpts[0][1])*frac
            bx2=rpts[3][0]+(rpts[2][0]-rpts[3][0])*frac; by2=rpts[3][1]+(rpts[2][1]-rpts[3][1])*frac
            pygame.draw.line(surf,(30,40,100),(int(tx),int(ty)),(int(bx2),int(by2)),1)
        lx=rpts[0][0]+(rpts[3][0]-rpts[0][0])*0.5; ly=rpts[0][1]+(rpts[3][1]-rpts[0][1])*0.5
        rx2=rpts[1][0]+(rpts[2][0]-rpts[1][0])*0.5; ry2=rpts[1][1]+(rpts[2][1]-rpts[1][1])*0.5
        pygame.draw.line(surf,(30,40,100),(int(lx),int(ly)),(int(rx2),int(ry2)),1)
        pygame.draw.polygon(surf,(80,100,160),rpts,2)
        gx1=int(rpts[0][0]+(rpts[1][0]-rpts[0][0])*0.2); gy1=int(rpts[0][1]+(rpts[1][1]-rpts[0][1])*0.2)
        gx2=int(rpts[0][0]+(rpts[1][0]-rpts[0][0])*0.5); gy2=int(rpts[0][1]+(rpts[1][1]-rpts[0][1])*0.5)
        pygame.draw.line(surf,(150,180,255),(gx1,gy1),(gx2,gy2),2)

# ── Ship ──────────────────────────────────────────────────────────────────────
class Ship:
    def __init__(self):
        self.x,self.y=float(WIDTH//2),float(HEIGHT-100)
        self.speed=5; self.r=20; self.lives=3
        self.invincible=0; self.flame_tick=0
        # power-up states
        self.shield=0; self.rapidfire=0; self.tripleshot=0
        self.slowmo=0; self.magnet=0

    def update(self, keys):
        spd = self.speed * (0.5 if self.slowmo > 0 else 1.0)  # slowmo affects debris not ship
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.x-=self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.x+=self.speed
        if keys[pygame.K_UP]    or keys[pygame.K_w]: self.y-=self.speed
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: self.y+=self.speed
        self.x=max(self.r,min(WIDTH-self.r,self.x))
        self.y=max(self.r,min(HEIGHT-self.r,self.y))
        if self.invincible>0: self.invincible-=1
        self.flame_tick+=1
        for attr in ["shield","rapidfire","tripleshot","slowmo","magnet"]:
            if getattr(self,attr)>0: setattr(self,attr,getattr(self,attr)-1)

    def draw(self, surf):
        if self.invincible>0 and (self.invincible//4)%2==0: return
        x,y=int(self.x),int(self.y)
        # shield bubble
        if self.shield>0:
            pulse=abs(math.sin(self.flame_tick*0.1))*6
            pygame.draw.circle(surf,(0,150,255),(x,y),int(self.r+14+pulse),3)
            pygame.draw.circle(surf,(100,200,255),(x,y),int(self.r+14+pulse),1)
        if self.flame_tick%6<3:
            pygame.draw.polygon(surf,ORANGE,[(x-8,y+18),(x,y+32),(x+8,y+18)])
            pygame.draw.polygon(surf,YELLOW,[(x-4,y+18),(x,y+26),(x+4,y+18)])
        # ship color changes with power-ups
        ship_col=(60,160,255)
        if self.rapidfire>0: ship_col=(255,200,0)
        if self.tripleshot>0: ship_col=(0,255,120)
        if self.magnet>0: ship_col=(255,140,0)
        pygame.draw.polygon(surf,ship_col,[(x,y-24),(x+18,y+18),(x,y+10),(x-18,y+18)])
        pygame.draw.polygon(surf,WHITE,[(x,y-24),(x+18,y+18),(x,y+10),(x-18,y+18)],2)
        pygame.draw.ellipse(surf,CYAN,(x-7,y-12,14,14))

# ── Bullet ────────────────────────────────────────────────────────────────────
class Bullet:
    def __init__(self, x, y, col=YELLOW):
        self.x=float(x); self.y=float(y); self.vy=-42; self.r=5; self.alive=True; self.col=col
    def update(self):
        self.y+=self.vy
        if self.y<-10: self.alive=False
    def draw(self, surf):
        pygame.draw.circle(surf,self.col,(int(self.x),int(self.y)),self.r)
        pygame.draw.circle(surf,WHITE,(int(self.x),int(self.y)),self.r,1)

# ── Boss ──────────────────────────────────────────────────────────────────────
class Boss:
    NAMES=["THE WRECKER","SATELLITE QUEEN","THE PULSAR","COMET LORD","THE SINGULARITY"]
    def __init__(self,num):
        self.num=num; self.kind=((num-1)%5)+1
        self.MAX_HP=200*(2**(num-1)); self.hp=self.MAX_HP
        self.r=55; self.x=float(WIDTH//2); self.y=130.0
        self.projectiles=[]; self.alive=True; self.flash=0; self.tick=0
        self.vx=2.5; self.vy=0.0; self.phase=0
    def _fire_aimed(self,ship,spread=0,speed=4.5,size=10,col=ORANGE):
        a=math.atan2(ship.y-self.y,ship.x-self.x)+math.radians(spread)
        self.projectiles.append({"x":self.x,"y":self.y+self.r,"vx":math.cos(a)*speed,"vy":math.sin(a)*speed,"r":size,"alive":True,"color":col})
    def _fire_ring(self,n,speed=3.5,size=9,col=CYAN):
        for i in range(n):
            a=math.radians(i*360/n)
            self.projectiles.append({"x":self.x,"y":self.y,"vx":math.cos(a)*speed,"vy":math.sin(a)*speed,"r":size,"alive":True,"color":col})
    def update(self,ship):
        self.tick+=1
        if self.flash>0: self.flash-=1
        k=self.kind
        if k==1:
            self.x+=self.vx
            if self.x<self.r or self.x>WIDTH-self.r: self.vx*=-1
            if self.tick%70==0:
                for ao in [-25,0,25]: self._fire_aimed(ship,ao,speed=4.5,col=ORANGE)
        elif k==2:
            if self.phase==0:
                self.x+=self.vx
                if self.x<self.r or self.x>WIDTH-self.r: self.vx*=-1
                if self.tick%90==0: self.phase=1
            elif self.phase==1:
                dx=ship.x-self.x; dy=ship.y-self.y; dist=max(1,math.hypot(dx,dy))
                self.x+=dx/dist*5; self.y+=dy/dist*5
                if self.y>280: self._fire_ring(8,speed=3.5,col=CYAN); self.phase=2
            elif self.phase==2:
                self.y-=4
                if self.y<=130: self.y=130; self.phase=0
        elif k==3:
            self.x=WIDTH//2+math.sin(self.tick*0.015)*200
            self.y=130+math.sin(self.tick*0.02)*40
            if self.tick%55==0: self._fire_ring(12,speed=4,col=PURPLE)
            if self.tick%110==0:
                for ao in [-15,0,15]: self._fire_aimed(ship,ao,speed=6,size=13,col=RED)
        elif k==4:
            t2=self.tick*0.025
            self.x=WIDTH//2+math.sin(t2)*340; self.y=160+math.sin(t2*2)*80
            if self.tick%18==0: self._fire_aimed(ship,0,speed=5.5,size=8,col=YELLOW)
        elif k==5:
            self.x+=self.vx
            if self.x<self.r or self.x>WIDTH-self.r: self.vx*=-1
            if self.tick%180==0:
                self.x=float(random.randint(100,WIDTH-100)); self.y=float(random.randint(80,200))
                self._fire_ring(20,speed=5,size=8,col=(180,0,255))
            if self.tick%40==0:
                for ao in range(-40,45,10): self._fire_aimed(ship,ao,speed=4+random.uniform(-1,1),size=9,col=RED)
        for p in self.projectiles:
            p["x"]+=p["vx"]; p["y"]+=p["vy"]
            if p["x"]<-20 or p["x"]>WIDTH+20 or p["y"]<-20 or p["y"]>HEIGHT+20: p["alive"]=False
        self.projectiles=[p for p in self.projectiles if p["alive"]]
    def take_damage(self,dmg):
        self.hp=max(0,self.hp-dmg); self.flash=8
        if self.hp<=0: self.alive=False
    def _draw_hp_bar(self,surf):
        x,y,r=int(self.x),int(self.y),self.r
        bw=220; bx=x-bw//2; by=y-r-22
        pygame.draw.rect(surf,DARK_RED,(bx,by,bw,12),border_radius=4)
        pygame.draw.rect(surf,GREEN,(bx,by,int(bw*self.hp/self.MAX_HP),12),border_radius=4)
        pygame.draw.rect(surf,WHITE,(bx,by,bw,12),1,border_radius=4)
        lbl=font_small.render(f"{self.NAMES[self.kind-1]}  {self.hp}/{self.MAX_HP}",True,WHITE)
        surf.blit(lbl,(x-lbl.get_width()//2,by-20))
    def draw(self,surf):
        x,y,r=int(self.x),int(self.y),self.r
        cc=WHITE if self.flash else None
        if self.kind==1:
            for layer,col,rr in [(1,DARK_RED,r),(0,RED if not cc else WHITE,r-8)]:
                pts=[(x+math.cos(math.radians(60*i+self.tick*1.5))*rr,y+math.sin(math.radians(60*i+self.tick*1.5))*rr) for i in range(6)]
                pygame.draw.polygon(surf,col,pts)
            for i in range(6):
                a=math.radians(60*i+self.tick*1.5+30)
                pygame.draw.line(surf,ORANGE,(x,y),(int(x+math.cos(a)*(r+18)),int(y+math.sin(a)*(r+18))),3)
            pygame.draw.circle(surf,YELLOW,(x,y),14); pygame.draw.circle(surf,RED,(x,y),7)
        elif self.kind==2:
            pygame.draw.rect(surf,(40,80,120),(x-24,y-16,48,32),border_radius=5)
            pygame.draw.rect(surf,CYAN if not cc else WHITE,(x-24,y-16,48,32),2,border_radius=5)
            for side in [-1,1]:
                angle=math.radians(self.tick*2); px2=x+side*(36+math.cos(angle)*8); py2=y+math.sin(angle)*12
                pygame.draw.rect(surf,YELLOW if not cc else WHITE,(int(px2)-18,int(py2)-7,36,14),border_radius=2)
            pygame.draw.circle(surf,CYAN,(x,y),10); pygame.draw.circle(surf,WHITE,(x,y),5)
        elif self.kind==3:
            pulse=abs(math.sin(self.tick*0.07))
            for rr,col in [(r,PURPLE),(r-14,(120,0,200)),(r-28,WHITE)]:
                pygame.draw.circle(surf,col if not cc else WHITE,(x,y),int(rr+pulse*10),4)
            pygame.draw.circle(surf,(200,0,255) if not cc else WHITE,(x,y),18)
            pygame.draw.circle(surf,WHITE,(x,y),8)
            for i in range(6):
                a=math.radians(self.tick*3+i*60)
                pygame.draw.line(surf,PURPLE,(x,y),(int(x+math.cos(a)*r),int(y+math.sin(a)*r)),2)
        elif self.kind==4:
            for i in range(8):
                tx=x-math.cos(0)*i*7; ty=y-i*7
                tc=(255,max(0,200-i*25),0)
                pygame.draw.circle(surf,tc,(int(tx),int(ty)),max(2,r//2-i*4))
            pygame.draw.circle(surf,(255,180,0) if not cc else WHITE,(x,y),r//2+4)
            pygame.draw.circle(surf,YELLOW if not cc else WHITE,(x,y),r//3)
            pygame.draw.circle(surf,WHITE,(x,y),8)
        elif self.kind==5:
            for i in range(5):
                rr=r-i*8
                if rr<4: break
                col=(max(0,80-i*15),0,max(0,180-i*30))
                pygame.draw.circle(surf,col if not cc else WHITE,(x,y),rr)
            for i in range(8):
                a=math.radians(self.tick*4+i*45)
                pygame.draw.line(surf,(180,0,255) if not cc else WHITE,(int(x+math.cos(a)*8),int(y+math.sin(a)*8)),(int(x+math.cos(a+0.5)*(r-4)),int(y+math.sin(a+0.5)*(r-4))),2)
            pygame.draw.circle(surf,BLACK,(x,y),16); pygame.draw.circle(surf,WHITE,(x,y),6)
        for p in self.projectiles:
            pc=p.get("color",ORANGE)
            pygame.draw.circle(surf,pc,(int(p["x"]),int(p["y"])),p["r"])
            pygame.draw.circle(surf,WHITE,(int(p["x"]),int(p["y"])),p["r"]//2)
        self._draw_hp_bar(surf)

# ── Particle ──────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self,x,y,color):
        self.x=float(x); self.y=float(y); a=random.uniform(0,2*math.pi); s=random.uniform(1,5)
        self.vx=math.cos(a)*s; self.vy=math.sin(a)*s; self.life=random.randint(20,45); self.color=color
    def update(self): self.x+=self.vx; self.y+=self.vy; self.vy+=0.1; self.life-=1
    def draw(self,surf): pygame.draw.circle(surf,self.color,(int(self.x),int(self.y)),max(1,self.life//10))

# ── Difficulty levels ─────────────────────────────────────────────────────────
LEVELS = {
    "EASY":   {"spawn_interval":12,"max_debris":25,"speed_mult":0.7, "color":(50,200,80),  "desc":"Chill dodging"},
    "NORMAL": {"spawn_interval":8, "max_debris":40,"speed_mult":1.0, "color":(0,220,255),  "desc":"Classic chaos"},
    "HARD":   {"spawn_interval":4, "max_debris":60,"speed_mult":1.4, "color":(220,50,50),  "desc":"Pure mayhem"},
}
chosen_level = "NORMAL"

# ══════════════════════════════════════════════════════════════════════════════
#  SCREENS
# ══════════════════════════════════════════════════════════════════════════════

def home_screen(highlight_score=None):
    global chosen_level
    scores = load_leaderboard()
    tick = 0
    bw,bh=260,54; bx,by=WIDTH//2-bw//2,195
    # level button positions
    lvl_names=list(LEVELS.keys())
    pygame.event.clear()
    while True:
        clock.tick(FPS); tick+=1
        mx,my=mouse_pos()
        hover = bx<=mx<=bx+bw and by<=my<=by+bh

        for event in pygame.event.get():
            handle_common_keys(event)
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:
                    if fullscreen: toggle_fullscreen()
                    else: pygame.quit(); sys.exit()
                if event.key==pygame.K_SPACE: return
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                if hover: return
                # level buttons
                for i,name in enumerate(lvl_names):
                    lbx=WIDTH//2-220+i*150; lby=by+bh+22
                    if lbx<=mx<=lbx+130 and lby<=my<=lby+36:
                        chosen_level=name; play("level_up")

        render_surf.fill((5,5,18)); draw_stars()
        draw_text_centered(render_surf,"ASTEROID DODGE",font_big,CYAN,WIDTH//2,100)
        draw_text_centered(render_surf,"Space Junk Survival",font_small,GRAY,WIDTH//2,152)
        draw_button(render_surf,"▶  CLICK TO PLAY",bx,by,bw,bh,hover)
        alpha=int(130+100*math.sin(tick*0.06))
        hint=font_tiny.render("or press SPACE",True,(alpha,alpha,alpha))
        render_surf.blit(hint,(WIDTH//2-hint.get_width()//2,by+bh+5))

        # difficulty selector
        for i,name in enumerate(lvl_names):
            lbx=WIDTH//2-220+i*150; lby=by+bh+22
            sel=chosen_level==name
            lv=LEVELS[name]
            bc=lv["color"] if sel else (60,60,60)
            pygame.draw.rect(render_surf,(20,20,20) if not sel else (15,30,15),(lbx,lby,130,36),border_radius=8)
            pygame.draw.rect(render_surf,bc,(lbx,lby,130,36),2,border_radius=8)
            lbl=font_small.render(name,True,bc if not sel else WHITE)
            render_surf.blit(lbl,(lbx+65-lbl.get_width()//2,lby+8))

        sel_desc=font_tiny.render(LEVELS[chosen_level]["desc"],True,LEVELS[chosen_level]["color"])
        render_surf.blit(sel_desc,(WIDTH//2-sel_desc.get_width()//2,by+bh+65))

        draw_leaderboard(render_surf,scores,highlight_score)
        footer=font_tiny.render("F11=Fullscreen  ESC=Quit",True,(70,70,70))
        render_surf.blit(footer,(WIDTH//2-footer.get_width()//2,HEIGHT-22))
        blit_scaled()


def name_entry_screen(score):
    name=""; ignore_space=True; frame=0
    pygame.event.clear()
    while True:
        clock.tick(FPS); frame+=1
        if frame>60: ignore_space=False
        bw,bh=240,50; bx,by=WIDTH//2-bw//2,HEIGHT//2+90
        mx,my=mouse_pos(); can_save=bool(name.strip())
        btn_hover=bx<=mx<=bx+bw and by<=my<=by+bh and can_save
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_F11: toggle_fullscreen()
                elif event.key==pygame.K_BACKSPACE: name=name[:-1]
                elif event.key==pygame.K_SPACE and can_save and not ignore_space: return name.strip()
                elif event.key not in (pygame.K_RETURN,pygame.K_SPACE,pygame.K_BACKSPACE,pygame.K_ESCAPE):
                    if len(name)<12 and event.unicode.isprintable() and event.unicode!=" ":
                        name+=event.unicode.upper()
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and btn_hover: return name.strip()
        render_surf.fill((5,5,18)); draw_stars()
        draw_text_centered(render_surf,"GAME OVER",font_big,RED,WIDTH//2,HEIGHT//2-150)
        draw_text_centered(render_surf,f"FINAL SCORE:  {score}",font_med,YELLOW,WIDTH//2,HEIGHT//2-95)
        draw_text_centered(render_surf,"TYPE YOUR NAME:",font_med,CYAN,WIDTH//2,HEIGHT//2-42)
        bx2=WIDTH//2-160
        pygame.draw.rect(render_surf,(30,30,70),(bx2,HEIGHT//2-4,320,50),border_radius=8)
        pygame.draw.rect(render_surf,CYAN,(bx2,HEIGHT//2-4,320,50),2,border_radius=8)
        ns=font_med.render(name+"|",True,WHITE)
        render_surf.blit(ns,(WIDTH//2-ns.get_width()//2,HEIGHT//2+4))
        if not can_save:
            draw_text_centered(render_surf,"type a name first",font_tiny,GRAY,WIDTH//2,HEIGHT//2+62)
        else:
            draw_text_centered(render_surf,"press SPACE  or  click button below",font_tiny,GREEN,WIDTH//2,HEIGHT//2+62)
        draw_button(render_surf,"SAVE & SEE SCORES",bx,by,bw,bh,btn_hover if can_save else False)
        if not can_save:
            pygame.draw.rect(render_surf,(40,40,40),(bx,by,bw,bh),border_radius=10)
            draw_text_centered(render_surf,"SAVE & SEE SCORES",font_med,(100,100,100),WIDTH//2,by+bh//2)
        blit_scaled()

# ══════════════════════════════════════════════════════════════════════════════
#  GAME LOOP
# ══════════════════════════════════════════════════════════════════════════════

def game_loop():
    global chosen_level
    lvl = LEVELS[chosen_level]

    ship=Ship(); debris_list,bullets,particles,powerups=[],[],[],[]
    boss=None; score=0; boss_num=0; next_boss=200
    boss_active=False; boss_flash=0; boss_intro_timer=0
    spawn_timer=0; bullet_timer=0
    spawn_interval=lvl["spawn_interval"]
    max_debris=lvl["max_debris"]
    speed_mult=lvl["speed_mult"]

    # powerup drop tracking
    powerup_timer=0
    powerup_interval=600  # drop every 10s

    # active powerup HUD list
    active_labels=[]  # (label, color, frames_left)

    # floating score popups
    popups=[]  # (x,y,text,color,life)

    def explode(x,y,color,n=18):
        for _ in range(n): particles.append(Particle(x,y,color))

    def popup(x,y,text,color=WHITE):
        popups.append({"x":float(x),"y":float(y),"text":text,"color":color,"life":60})

    while True:
        clock.tick(FPS)

        for event in pygame.event.get():
            handle_common_keys(event)
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:
                    if fullscreen: toggle_fullscreen()

        keys=pygame.key.get_pressed()

        # slowmo: debris move at half speed when active
        slowmo_active = ship.slowmo > 0

        ship.update(keys)

        # ── Auto fire during boss ──
        if boss_active and boss and boss.alive:
            fire_rate = FPS//3 if ship.rapidfire>0 else FPS
            bullet_timer+=1
            if bullet_timer>=fire_rate:
                bullet_timer=0
                play("shoot")
                if ship.tripleshot>0 or True:  # always triple during boss
                    bullets.append(Bullet(ship.x-14,ship.y-24,YELLOW))
                    bullets.append(Bullet(ship.x,   ship.y-24,YELLOW))
                    bullets.append(Bullet(ship.x+14,ship.y-24,YELLOW))
                else:
                    bullets.append(Bullet(ship.x,ship.y-24))

        # ── Spawn debris ──
        if not boss_active:
            spawn_timer+=1
            if spawn_timer>=spawn_interval and len(debris_list)<max_debris:
                spawn_timer=0
                debris_list.append(spawn_debris(speed_mult * (0.5 if slowmo_active else 1.0)))

        # ── Spawn power-ups periodically ──
        if not boss_active:
            powerup_timer+=1
            if powerup_timer>=powerup_interval:
                powerup_timer=0
                px2=float(random.randint(60,WIDTH-60))
                powerups.append(spawn_powerup(px2,-20))

        # ── Update debris ──
        sm = 0.5 if slowmo_active else 1.0
        for d in debris_list:
            d["x"]+=d["vx"]*sm; d["y"]+=d["vy"]*sm; d["rot"]+=d["rot_speed"]*sm
            if d["y"]>HEIGHT+50:
                d["y"]=-d["r"]-5; d["x"]=float(random.randint(0,WIDTH))
                if not boss_active:
                    pts = 2 if ship.magnet>0 else 1
                    score+=pts

        # ── Update power-ups ──
        for p in powerups:
            p["y"]+=p["vy"]; p["tick"]+=1
            if p["y"]>HEIGHT+30: p["alive"]=False
        powerups=[p for p in powerups if p["alive"]]

        # ── Power-up collision ──
        for p in powerups:
            if distance(p["x"],p["y"],ship.x,ship.y)<p["r"]+ship.r:
                p["alive"]=False
                play("powerup")
                k=p["kind"]
                if k=="shield":      ship.shield=p["duration"];     popup(ship.x,ship.y,"SHIELD!",(0,180,255))
                elif k=="rapidfire": ship.rapidfire=p["duration"];   popup(ship.x,ship.y,"RAPID FIRE!",YELLOW)
                elif k=="tripleshot":ship.tripleshot=p["duration"];  popup(ship.x,ship.y,"TRIPLE SHOT!",GREEN)
                elif k=="slowmo":    ship.slowmo=p["duration"];      popup(ship.x,ship.y,"SLOW MO!",PURPLE)
                elif k=="extralife":
                    ship.lives=min(ship.lives+1,6)
                    play("extra_life")
                    popup(ship.x,ship.y,"+1 LIFE!",RED)
                elif k=="magnet":    ship.magnet=p["duration"];      popup(ship.x,ship.y,"SCORE x2!",ORANGE)

        for b in bullets: b.update()
        bullets=[b for b in bullets if b.alive]
        for p in particles: p.update()
        particles=[p for p in particles if p.life>0]
        for p in popups:
            p["y"]-=1; p["life"]-=1
        popups=[p for p in popups if p["life"]>0]

        # ── Trigger boss ──
        if not boss_active and score>=next_boss:
            boss_active=True; boss_num+=1
            debris_list.clear(); boss=Boss(boss_num); bullet_timer=0
            boss_intro_timer=180; play("boss_spawn")

        if boss_active and boss and boss.alive:
            boss.update(ship)
            for b in bullets:
                if distance(b.x,b.y,boss.x,boss.y)<boss.r+b.r:
                    boss.take_damage(10); b.alive=False
                    explode(b.x,b.y,YELLOW,6); play("boss_hit")
            if ship.invincible==0 and ship.shield==0:
                for p in boss.projectiles:
                    if distance(p["x"],p["y"],ship.x,ship.y)<p["r"]+ship.r:
                        p["alive"]=False
                        ship.lives=max(0,ship.lives-1)
                        ship.invincible=120
                        explode(ship.x,ship.y,CYAN,12); play("hit")
                        break
            elif ship.invincible==0 and ship.shield>0:
                for p in boss.projectiles:
                    if distance(p["x"],p["y"],ship.x,ship.y)<ship.r+20+p["r"]:
                        p["alive"]=False; play("shield")
                        popup(ship.x,ship.y,"BLOCKED!",CYAN)
                        break
            if not boss.alive:
                explode(boss.x,boss.y,RED,40)
                bonus=200 if chosen_level=="HARD" else (150 if chosen_level=="NORMAL" else 100)
                score+=bonus; popup(boss.x,boss.y,f"+{bonus}!",GOLD)
                boss_active=False; boss_flash=180; next_boss+=200
                play("boss_die")

        if boss_flash>0: boss_flash-=1

        # ── Debris collision ──
        if ship.invincible==0:
            for d in debris_list:
                if distance(d["x"],d["y"],ship.x,ship.y)<d["r"]+ship.r-4:
                    if ship.shield>0:
                        ship.shield=0
                        d["y"]=-d["r"]-5; d["x"]=float(random.randint(0,WIDTH))
                        play("shield"); popup(ship.x,ship.y,"SHIELD BROKE!",CYAN)
                    else:
                        ship.lives=max(0,ship.lives-1)
                        ship.invincible=120
                        explode(ship.x,ship.y,CYAN,15); play("hit")
                        d["y"]=-d["r"]-5; d["x"]=float(random.randint(0,WIDTH))
                    break

        # ── Game over ──
        if ship.lives<=0:
            name=name_entry_screen(score)
            print(f"[GAME OVER] name='{name}' score={score}")
            if not name: name="UNKNOWN"
            save_score(name,score)
            home_screen(highlight_score=score)
            return

        # ══════════
        #   DRAW
        # ══════════
        render_surf.fill((5,5,18)); draw_stars()
        for d in debris_list: draw_debris(render_surf,d)
        for p in powerups: draw_powerup(render_surf,p)
        for b in bullets: b.draw(render_surf)
        if boss_active and boss and boss.alive: boss.draw(render_surf)
        for p in particles: p.draw(render_surf)
        ship.draw(render_surf)

        # floating popups
        for p in popups:
            alpha=max(0,p["life"]*4)
            lbl=font_small.render(p["text"],True,p["color"])
            render_surf.blit(lbl,(int(p["x"])-lbl.get_width()//2,int(p["y"])))

        # ── HUD ──
        render_surf.blit(font_med.render(f"SCORE: {score}",True,WHITE),(12,10))

        # lives
        for i in range(ship.lives):
            hx=WIDTH-30-i*34
            pygame.draw.polygon(render_surf,(60,160,255),[(hx,8),(hx+12,24),(hx,18),(hx-12,24)])

        # level badge
        lv_col=LEVELS[chosen_level]["color"]
        lv_lbl=font_tiny.render(chosen_level,True,lv_col)
        render_surf.blit(lv_lbl,(12,HEIGHT-22))

        # active power-up bars
        bar_y=45
        for attr,col,label in [("shield",(0,180,255),"SHIELD"),("rapidfire",YELLOW,"RAPID FIRE"),
                                ("tripleshot",GREEN,"TRIPLE"),("slowmo",PURPLE,"SLOW MO"),("magnet",ORANGE,"x2 SCORE")]:
            val=getattr(ship,attr)
            if val>0:
                max_val=360
                bw=120
                pygame.draw.rect(render_surf,(30,30,30),(12,bar_y,bw,12),border_radius=4)
                pygame.draw.rect(render_surf,col,(12,bar_y,int(bw*val/max_val),12),border_radius=4)
                pygame.draw.rect(render_surf,WHITE,(12,bar_y,bw,12),1,border_radius=4)
                ll=font_tiny.render(label,True,col)
                render_surf.blit(ll,(136,bar_y-1))
                bar_y+=18

        # boss bar
        if not boss_active:
            prog=min(1.0,(score-(next_boss-200))/200)
            bw=200; bx2=WIDTH//2-bw//2
            pygame.draw.rect(render_surf,(50,20,20),(bx2,10,bw,14),border_radius=6)
            pygame.draw.rect(render_surf,RED,(bx2,10,int(bw*prog),14),border_radius=6)
            pygame.draw.rect(render_surf,WHITE,(bx2,10,bw,14),1,border_radius=6)
            lbl=font_small.render(f"BOSS IN {max(0,next_boss-score)} pts",True,GRAY)
            render_surf.blit(lbl,(bx2+bw//2-lbl.get_width()//2,27))

        if boss_active:
            draw_text_centered(render_surf,"BOSS BATTLE  —  AUTO-FIRE ON",font_small,RED,WIDTH//2,HEIGHT-20)

        if boss_intro_timer>0 and boss:
            boss_intro_timer-=1
            kind_colors=[RED,CYAN,PURPLE,YELLOW,(180,0,255)]
            bc=kind_colors[boss.kind-1]
            draw_text_centered(render_surf,f"BOSS #{boss.num}",font_med,WHITE,WIDTH//2,HEIGHT//2-40)
            draw_text_centered(render_surf,Boss.NAMES[boss.kind-1],font_big,bc,WIDTH//2,HEIGHT//2+10)
            draw_text_centered(render_surf,"GOOD LUCK!",font_small,GRAY,WIDTH//2,HEIGHT//2+62)

        if boss_flash>0 and not boss_active:
            render_surf.blit(font_big.render("BOSS DEFEATED!",True,GREEN),(WIDTH//2-font_big.size("BOSS DEFEATED!")[0]//2,HEIGHT//2-30))

        hint=font_tiny.render("WASD/Arrows=move  F11=Fullscreen",True,(70,70,70))
        render_surf.blit(hint,(WIDTH-hint.get_width()-10,HEIGHT-22))
        blit_scaled()

# ── Entry point ───────────────────────────────────────────────────────────────
while True:
    try:
        home_screen()
        game_loop()
    except SystemExit: raise
    except Exception as e: print(f"ERROR: {e}"); pass
