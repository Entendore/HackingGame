#!/usr/bin/env python3
"""
NETRUNNER — Offensive Security Simulator
PySide6 Desktop Application
Install: pip install PySide6
"""

import sys, os, time, math, random, struct, io, wave, tempfile
from html import escape as _esc

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QLabel, QProgressBar, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QBuffer, QIODevice, QRectF, QPointF
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QTextCursor, QKeySequence, QShortcut
)

try:
    from PySide6.QtMultimedia import QAudioSink, QMediaDevices, QAudioFormat
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

# ── Constants ────────────────────────────────────────────────────────────────
C = {
    'n': '#00ff41', 'd': '#0a3318', 'a': '#ff2e63', 'w': '#ffba08',
    'r': '#ff3344', 'ok': '#39ff14', 'i': '#00b4d8', 'bg': '#080e14',
    'wbg': '#04080c', 'bd': '#0d2818',
}

def tx(text, c='n'):
    return f'<span style="color:{C.get(c,C["n"])}">{_esc(text)}</span>'

def txr(parts):
    """Render list of (text, color) tuples as one HTML span."""
    return ''.join(tx(t, c) for t, c in parts)

FONT_MONO = "Courier New" if sys.platform == "win32" else "Menlo" if sys.platform == "darwin" else "monospace"
FONT_SIZE = 11

# ── Audio ───────────────────────────────────────────────────────────────────
class AudioManager:
    def __init__(self):
        self.ok = False
        if not HAS_AUDIO:
            return
        try:
            dev = QMediaDevices.defaultAudioOutput()
            if dev is None:
                return
            fmt = QAudioFormat()
            fmt.setSampleRate(44100)
            fmt.setChannelCount(1)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            self.fmt = fmt
            self.dev = dev
            self.ok = True
        except Exception:
            pass

    def _play(self, freq, dur_ms, vol=0.15):
        if not self.ok:
            return
        try:
            sink = QAudioSink(self.dev, self.fmt)
            sink.setVolume(vol)
            n = int(44100 * dur_ms / 1000)
            data = bytearray()
            for i in range(n):
                t = i / 44100
                env = max(0.0, 1.0 - t / (dur_ms / 1000))
                v = int(32767 * env * math.sin(2 * math.pi * freq * t))
                data.extend(struct.pack('<h', max(-32768, min(32767, v))))
            buf = QBuffer()
            buf.setData(bytes(data))
            buf.open(QIODevice.ReadOnly)
            sink.start(buf)
        except Exception:
            pass

    def type_snd(self): self._play(1100 + random.randint(0, 400), 18, 0.06)
    def ok_snd(self):
        self._play(523, 90, 0.12)
        QTimer.singleShot(90, lambda: self._play(659, 90, 0.12))
        QTimer.singleShot(180, lambda: self._play(784, 120, 0.12))
    def err_snd(self): self._play(160, 200, 0.12)
    def alert_snd(self):
        self._play(400, 70, 0.15)
        QTimer.singleShot(160, lambda: self._play(400, 70, 0.15))
    def crack_snd(self): self._play(1300 + random.randint(0, 500), 25, 0.08)
    def crack_fail_snd(self): self._play(130, 120, 0.08)
    def by_ok_snd(self):
        self._play(700, 50, 0.1)
        QTimer.singleShot(70, lambda: self._play(900, 50, 0.1))
        QTimer.singleShot(140, lambda: self._play(1100, 80, 0.1))
    def by_fail_snd(self): self._play(180, 150, 0.1)

# ── Service Fingerprints ───────────────────────────────────────────────────
SFP = {
    21: ('ftp', 'vsftpd 3.0.5', 'cpe:/a:vsftpd:vsftpd:3.0.5'),
    22: ('ssh', 'OpenSSH 8.9p1', 'cpe:/a:openbsd:openssh:8.9p1'),
    25: ('smtp', 'Postfix 3.7.6', 'cpe:/a:postfix:postfix:3.7.6'),
    80: ('http', 'nginx 1.24.0', 'cpe:/a:nginx:nginx:1.24.0'),
    110: ('pop3', 'Dovecot 2.3.21', 'cpe:/a:dovecot:dovecot:2.3.21'),
    143: ('imap', 'Dovecot 2.3.21', 'cpe:/a:dovecot:dovecot:2.3.21'),
    443: ('https', 'nginx 1.24.0', 'cpe:/a:nginx:nginx:1.24.0'),
    587: ('submission', 'Postfix 3.7.6', 'cpe:/a:postfix:postfix:3.7.6'),
    993: ('imaps', 'Dovecot 2.3.21', 'cpe:/a:dovecot:dovecot:2.3.21'),
    3000: ('http-proxy', 'Node.js 18.19', 'cpe:/a:nodejs:node.js:18.19'),
    3306: ('mysql', 'MySQL 8.0.35', 'cpe:/a:mysql:mysql:8.0.35'),
    5005: ('unknown', 'Unknown', ''),
    502: ('modbus', 'Schneider Modicon 4.2', 'cpe:/a:schneider:modicon:4.2'),
    514: ('syslog', 'rsyslog 8.2302', 'cpe:/a:rsyslog:rsyslog:8.2302'),
    5432: ('postgresql', 'PostgreSQL 15.4', 'cpe:/a:postgresql:postgresql:15.4'),
    6006: ('tensorboard', 'TensorBoard 2.15', ''),
    6514: ('syslog-tls', 'rsyslog 8.2302', ''),
    8080: ('http-alt', 'Apache Tomcat 10.1', 'cpe:/a:apache:tomcat:10.1'),
    8333: ('bitcoin', 'Bitcoin Core 26.0', 'cpe:/a:bitcoin:bitcoin_core:26.0'),
    9000: ('s3-api', 'MinIO 2024.01', ''),
    9001: ('tor-dir', 'Tor 0.4.8.10', 'cpe:/a:torproject:tor:0.4.8.10'),
    9050: ('tor-socks', 'Tor 0.4.8.10', 'cpe:/a:torproject:tor:0.4.8.10'),
    9200: ('http-elastic', 'Elasticsearch 8.11', 'cpe:/a:elastic:elasticsearch:8.11'),
    5601: ('http-kibana', 'Kibana 8.11', 'cpe:/a:elastic:kibana:8.11'),
    11371: ('hkp', 'SKS Key Server 1.1.6', ''),
    8443: ('https-alt', 'Apache Tomcat 10.1', ''),
    2222: ('ssh-alt', 'OpenSSH 9.5p1', 'cpe:/a:openbsd:openssh:9.5p1'),
}

def _mac():
    return ':'.join(f'{random.randint(0,255):02x}' for _ in range(6))

def _nd(ip, host, ntype, osn, ports, hp=False, fw=False, tf=None):
    return {'ip':ip,'hostname':host,'type':ntype,'os':osn,'ports':ports,
            'hp':hp,'fw':fw,'tf':tf,'mac':_mac()}

# ── Missions ────────────────────────────────────────────────────────────────
def _m1():
    return {
        'name':'INITIATION','diff':'EASY','target':'Acme Corp File Server',
        'obj':'Locate and exfiltrate the confidential document.',
        'tps':.22,'ts':2,'tc':4,'cl':6,'ct':30,
        'nodes':[
            _nd('192.168.1.1','gw-rtr-01','router','Cisco IOS 15.7',[22,80]),
            _nd('192.168.1.10','web-srv-01','general purpose','Ubuntu 22.04 LTS',[80,443,22]),
            _nd('192.168.1.20','file-srv-01','general purpose','Debian 12',[21,22,445],tf='confidential_2024.enc'),
            _nd('192.168.1.30','db-srv-01','general purpose','CentOS 9 Stream',[3306,22,5432]),
        ],
        'fs':{'/':['home','var','etc','tmp'],'/home':['admin','backup'],
              '/home/admin':['documents','scripts','.ssh'],
              '/home/admin/documents':['Q4_report.txt','confidential_2024.enc','memo.txt','README.md'],
              '/home/admin/scripts':['backup.sh','monitor.py'],
              '/home/admin/.ssh':['id_rsa','known_hosts'],
              '/home/backup':['db_dump.sql','archive.tar.gz'],
              '/var':['log','www'],'/var/log':['syslog','auth.log'],
              '/var/www':['html'],'/var/www/html':['index.html'],
              '/etc':['passwd','shadow','hosts'],'/tmp':['.lock']},
        'files':{
            'Q4_report.txt':'Q4 Financial Report - Acme Corp\n================================\nRevenue:     $4,218,500\nExpenses:    $3,102,300\nNet Profit:  $1,116,200\nKey growth: Cloud services (+34%)\n[EOF]',
            'confidential_2024.enc':'[ENCRYPTED FILE]\nSize: 2.4 MB\nCipher: AES-256-CBC\nHeader: 0x7F3A9B2C1E...\n\n>> TARGET FILE\n>> "exfil confidential_2024.enc" to extract\n[EOF]',
            'memo.txt':'INTERNAL MEMO - CONFIDENTIAL\nFrom: CTO\nSubject: Security Protocol Update\nAll staff: complete security training by Feb 1.\n- J. Morrison, CTO',
            'README.md':'# file-srv-01\nCritical document storage.\nAdmin access only.\nLast updated: 2024-01-08',
            'backup.sh':'#!/bin/bash\nDATE=$(date +%Y%m%d)\ntar -czf /home/backup/archive_$DATE.tar.gz /home/admin/documents\nfind /home/backup -name "*.tar.gz" -mtime +7 -delete',
            'monitor.py':'#!/usr/bin/env python3\nimport psutil\nwhile True:\n    cpu=psutil.cpu_percent(interval=5)\n    if cpu>90: alert_ops()',
            'id_rsa':'-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAA...[TRUNCATED]\n-----END OPENSSH PRIVATE KEY-----',
            'known_hosts':'10.0.0.1 ssh-ed25519 AAAAC3...\n192.168.1.1 ssh-ed25519 AAAAC3...',
            'db_dump.sql':'-- MySQL dump 2024-01-05\nCREATE TABLE users (id INT PRIMARY KEY, username VARCHAR(64));\n-- [TRUNCATED: 847 rows]',
            'archive.tar.gz':'[BINARY FILE]',
            'syslog':'Jan 10 03:22:11 file-srv-01 sshd[1234]: Accepted password for admin from 10.0.0.5 port 52413 ssh2\nJan 10 04:00:00 file-srv-01 CRON[5678]: (root) CMD (backup.sh)',
            'auth.log':'Jan 10 03:21:58 sshd[1234]: Failed password for root from 45.33.32.156 port 33892 ssh2\nJan 10 03:22:11 sshd[1234]: Accepted password for admin from 10.0.0.5 port 52413 ssh2',
            'index.html':'<html><body><h1>Acme Corp</h1><p>Maintenance.</p></body></html>',
            'passwd':'root:x:0:0:root:/root:/bin/bash\nadmin:x:1000:1000:Admin:/home/admin:/bin/bash',
            'shadow':'root:$6$rounds=656000$...:19500:0:99999:7:::\nadmin:$6$rounds=656000$...:19500:0:99999:7:::\n[RESTRICTED]',
            'hosts':'127.0.0.1\tlocalhost\n192.168.1.20\tfile-srv-01\n192.168.1.30\tdb-srv-01',
            '.lock':'[LOCK FILE - PID: 1234]',
        }
    }

def _m2():
    return {
        'name':'DEEP BREACH','diff':'MEDIUM','target':'NovaTech Secure Server',
        'obj':'Breach the secure server and exfiltrate Project Aurora data.',
        'tps':.35,'ts':3,'tc':7,'cl':10,'ct':25,
        'nodes':[
            _nd('10.0.5.1','edge-fw-01','firewall','pfSense 2.7.2',[22,443]),
            _nd('10.0.5.10','dmz-web-01','web server','RHEL 9',[80,443,22]),
            _nd('10.0.5.20','mail-srv-01','mail server','Ubuntu 22.04 LTS',[25,587,993,22],hp=True),
            _nd('10.0.5.30','dev-srv-01','development','Debian 12',[22,8080,3000]),
            _nd('10.0.5.50','secure-srv-01','general purpose','HardenedBSD 14',[22,443],tf='project_aurora.dat'),
            _nd('10.0.5.60','siem-01','security management','Security Onion 2.4',[22,514,9200],hp=True),
        ],
        'fs':{'/':['home','var','opt','secret'],'/home':['sysadmin'],
              '/home/sysadmin':['documents','tools'],
              '/home/sysadmin/documents':['incident_report.pdf','project_aurora.dat','keys.txt'],
              '/home/sysadmin/tools':['scanner.py','exploit.sh'],
              '/var':['log'],'/var/log':['security.log','access.log'],
              '/opt':['novatech'],'/opt/novatech':['app'],'/opt/novatech/app':['config.yml'],
              '/secret':['vault'],'/secret/vault':['master.key','certs']},
        'files':{
            'incident_report.pdf':'[PDF BINARY]\n"Q3 Security Incident - Unauthorized access\ndetected from external IP. Contained."',
            'project_aurora.dat':'[CLASSIFIED DATA]\nProject AURORA - Phase 3 Results\n================================\nQuantum encryption prototype:\n  Key gen: 0.003ms  Encrypt: 14.2 Gbps\n  Security: 256-qubit equivalent\n\n>> TARGET FILE\n>> "exfil project_aurora.dat" to extract\n[EOF]',
            'keys.txt':'API Keys (DO NOT SHARE):\n  NOVATECH_PROD=nvtk_a8f2...[REDACTED]\n  DB_MASTER=7x9k2m...[REDACTED]',
            'scanner.py':'#!/usr/bin/env python3\nimport nmap, sys\nnm = nmap.PortScanner()\nnm.scan(sys.argv[1], "1-65535")',
            'exploit.sh':'#!/bin/bash\n# [REDACTED - AUTHORIZED ONLY]',
            'security.log':'Jan 15 09:12:35 sshd[4521]: Connection from 10.0.5.1\nJan 15 09:12:36 sshd[4521]: Accepted key for sysadmin\nJan 15 14:33:01 kernel: Packet from unknown src dropped',
            'access.log':'10.0.5.1 - [15/Jan/2024:09:12:33] "CONNECT secure-srv-01:22" 200\n10.0.5.30 - [15/Jan/2024:11:45:00] "GET /api/status" 200',
            'config.yml':'app:\n  name: NovaTech Core\n  env: production\n  db: postgres://secure-srv-01:5432/core',
            'master.key':'[ACCESS DENIED - Insufficient privileges]',
            'certs':['server.crt','server.key'],
            'server.crt':'-----BEGIN CERTIFICATE-----\nMIIDXTCCAkWg...[TRUNCATED]\nSubject: CN=secure-srv-01.novatech.internal\n-----END CERTIFICATE-----',
            'server.key':'-----BEGIN PRIVATE KEY-----\n[ACCESS DENIED]\n-----END PRIVATE KEY-----',
        }
    }

def _m3():
    return {
        'name':'GHOST PROTOCOL','diff':'HARD','target':'Nexus Defense Core',
        'obj':'Infiltrate the core and exfiltrate the launch authorization key.',
        'tps':.5,'ts':4,'tc':9,'cl':13,'ct':22,'bl':4,
        'nodes':[
            _nd('172.16.0.10','outer-fw-01','firewall','Juniper SRX',[22,80,443]),
            _nd('172.16.0.20','inner-fw-01','firewall','Palo Alto PA-5250',[22,443]),
            _nd('172.16.0.30','unknown-host-30','unknown','Unknown',[22,80,3306],hp=True),
            _nd('172.16.0.40','radar-sys-01','specialized','VxWorks 7',[22,502]),
            _nd('172.16.0.50','comm-sat-01','specialized','RTLinux 5',[22,5005]),
            _nd('172.16.0.60','unknown-host-60','unknown','Unknown',[22,514],hp=True),
            _nd('172.16.0.1','core-sys-01','general purpose','Classified',[22],fw=True,tf='nuclear_launch.key'),
        ],
        'fs':{'/':['root','var','etc','classified'],'/root':['.config','scripts'],
              '/root/.config':['core.conf','auth.cfg'],
              '/root/scripts':['launch_seq.sh','verify_codes.py','emergency.sh'],
              '/var':['log','data'],'/var/log':['core.log','auth.log','trace.log'],
              '/var/data':['keys'],'/var/data/keys':['nuclear_launch.key','backup.key'],
              '/etc':['core.conf','shadow'],'/classified':['TOP_SECRET'],
              '/classified/TOP_SECRET':['nuclear_launch.key','war_plan.pdf']},
        'files':{
            'core.conf':'# CORE-SYS CONFIG\n# CLASSIFICATION: TOP SECRET\nsystem.name = NEXUS-CORE-7\nauth.method = dual_factor\nencryption = AES-512-Q\nself_destruct = ENABLED',
            'auth.cfg':'# Auth Config\nmax_attempts = 3\nlockout_time = 3600\nbiometric_required = true',
            'launch_seq.sh':'#!/bin/bash\n# LAUNCH SEQUENCE - AUTHORIZED ONLY\nverify_auth || exit 1\nload_key /var/data/keys/nuclear_launch.key\nconfirm_launch',
            'verify_codes.py':'#!/usr/bin/env python3\nimport hashlib\nMASTER=open("/classified/TOP_SECRET/nuclear_launch.key").read()\ndef verify(c): return hashlib.sha256(c.encode()+MASTER.encode()).hexdigest()[:8]=="a7f3b2c1"',
            'emergency.sh':'#!/bin/bash\n# EMERGENCY PROTOCOL\necho "WARNING: SHUTDOWN INITIATED"\nkillall -9 launch_daemon\nshutdown -h now',
            'core.log':'[CLASSIFIED - ACCESS DENIED]',
            'auth.log':'Jan 20 00:01:05 sshd[1]: Server listening on 0.0.0.0 port 22\nJan 20 08:00:00 PAM: biometric_scan_passed for operator_alpha',
            'trace.log':'Trace system active. All connections monitored.\nAlert threshold: 15% anomaly.\nCurrent anomaly: 0.0%',
            'nuclear_launch.key':'============================================\n  NEXUS DEFENSE - LAUNCH AUTH KEY\n  CLASSIFICATION: TOP SECRET // NOFORN\n============================================\nKey ID:     NXS-7741-DELTA\nChecksum:   0xDEADBEEFCAFEBABE\nPayload:    [48 bytes AES-512 encrypted]\n\n>> CRITICAL TARGET FILE\n>> "exfil nuclear_launch.key" to extract\n[EOF]',
            'backup.key':'[BACKUP KEY - EXPIRED] Status: REVOKED',
            'war_plan.pdf':'[PDF BINARY]\n"Operation DELTA - Contingency plan for scenario ZULU-7..."',
            'shadow':'root:!:19500:0:99999:7:::\nsysop:$6$rounds=656000$...[REDACTED]:19500:0:99999:7:::',
        }
    }

def _m4():
    return {
        'name':'DARK WEB','diff':'EXPERT','target':'ShadowNet Marketplace',
        'obj':'Infiltrate the darknet marketplace and exfiltrate the vendor ledger.',
        'tps':.65,'ts':5,'tc':9,'cl':11,'ct':18,'bl':5,
        'nodes':[
            _nd('100.64.0.1','tor-exit-01','gateway','Tails OS 6.0',[22,9001,9050]),
            _nd('100.64.0.10','proxy-chain-01','proxy','Alpine Linux 3.19',[22,3128,8080]),
            _nd('100.64.0.20','unknown-host-20','unknown','Unknown',[22,80,443,3306,8080],hp=True),
            _nd('100.64.0.30','btc-node-01','specialized','Ubuntu 22.04 LTS',[22,8333]),
            _nd('100.64.0.40','pgp-srv-01','general purpose','Debian 12',[22,11371]),
            _nd('100.64.0.50','unknown-host-50','unknown','Unknown',[21,22,25,110,143],hp=True),
            _nd('100.64.0.60','market-srv-01','general purpose','Whonix Gateway 17',[22,443],fw=True,tf='vendor_ledger.xz'),
        ],
        'fs':{'/':['var','opt','home','hidden'],'/var':['log','lib'],
              '/var/log':['market.log','access.log'],'/var/lib':['tor'],
              '/var/lib/tor':['hidden_service'],'/var/lib/tor/hidden_service':['hostname','private_key'],
              '/opt':['market'],'/opt/market':['db','config','backups'],
              '/opt/market/db':['vendor_ledger.xz','users.db','products.db'],
              '/opt/market/config':['market.conf','pgp_keys'],
              '/opt/market/backups':['dump_0105.sql.gz'],
              '/home':['shadowadmin'],'/home/shadowadmin':['notes.txt','wallet.dat'],
              '/hidden':['stashes'],'/hidden/stashes':['dead_drop.txt']},
        'files':{
            'market.log':'[2024-02-01 03:14:22] vendor_register: "Chemist_X"\n[2024-02-01 03:15:01] product_list: 500 units\n[2024-02-01 04:00:00] daily_backup initiated\n[2024-02-01 12:22:33] escrow_dispute #4471',
            'access.log':'100.64.0.1 - [01/Feb/2024:03:14:00] "POST /api/vendor/register" 201\n100.64.0.30 - [01/Feb/2024:03:14:22] "GET /api/blockchain/verify" 200',
            'hostname':'abcdefghijklmnop.onion',
            'private_key':'[ACCESS DENIED - Hidden service key restricted]',
            'vendor_ledger.xz':'[COMPRESSED - 14.2 MB xz]\nContains: Full vendor transaction history\n  Records: 28,447 transactions\n  Vendors: 1,203 active\n  Total volume: 4,847 BTC\n\n>> TARGET FILE\n>> "exfil vendor_ledger.xz" to extract\n[EOF]',
            'users.db':'[BINARY - SQLite3] Tables: users, sessions, pgp_keys\nRows: 84712 [PARTIAL: admin -> shadowadmin]',
            'products.db':'[BINARY - SQLite3] [ACCESS DENIED - Read restricted]',
            'market.conf':'# ShadowNet Market Config\ndomain = abcdefghijklmnop.onion\nescrow_timeout = 72h\ncommission = 0.03\npgp_required = true',
            'pgp_keys':['market_pub.asc','admin_pub.asc'],
            'market_pub.asc':'-----BEGIN PGP PUBLIC KEY BLOCK-----\nVersion: GnuPG 2.4\nmQINBGV2...[TRUNCATED]\n-----END PGP PUBLIC KEY BLOCK-----',
            'admin_pub.asc':'-----BEGIN PGP PUBLIC KEY BLOCK-----\nShadowAdmin <shadow@dark.mail>\n[TRUNCATED]\n-----END PGP PUBLIC KEY BLOCK-----',
            'dump_0105.sql.gz':'[COMPRESSED - 2.1 MB gzip]',
            'notes.txt':'OPSEC NOTES\n===========\n- Never access from clearnet\n- Rotate PGP keys monthly\n- Dead drop: /hidden/stashes/\n- BTC mixer: cycle every 6h',
            'wallet.dat':'[ENCRYPTED WALLET - HD]\nBalance: 127.43 BTC\n[Requires passphrase]',
            'dead_drop.txt':'DEAD DROP PROTOCOL\n==================\nLocation Alpha: 48.8566N, 2.3522E\nSignal: Red flag, 3rd floor\nWindow: 0200-0300 UTC\nKey phrase: "The crow flies at midnight"',
        }
    }

def _m5():
    return {
        'name':'ZERO DAY','diff':'NIGHTMARE','target':'Singularity AI Core',
        'obj':'Breach the AI research core and exfiltrate neural model weights.',
        'tps':.8,'ts':6,'tc':11,'cl':15,'ct':16,'bl':5,
        'nodes':[
            _nd('10.0.0.1','perim-fw-01','firewall','Juniper SRX',[22,443]),
            _nd('10.0.0.10','ids-01','security management','Snort/Suricata',[22,514,9200]),
            _nd('10.0.0.20','unknown-host-20','unknown','Unknown',[22,80,443,3306,8080,8443],hp=True),
            _nd('10.0.0.30','gpu-cluster-n1','general purpose','Ubuntu 22.04 LTS',[22,2222,6006]),
            _nd('10.0.0.40','gpu-cluster-n2','general purpose','Ubuntu 22.04 LTS',[22,2222,6006]),
            _nd('10.0.0.50','data-lake-01','storage','FreeBSD 14',[22,9000]),
            _nd('10.0.0.60','unknown-host-60','unknown','Unknown',[22,21,25,53,110],hp=True),
            _nd('10.0.0.70','log-core-01','security management','ELK Stack',[22,514,9200,5601]),
            _nd('10.0.0.100','ai-core-01','general purpose','Custom Kernel 6.7',[22],fw=True,tf='singularity_weights.pt'),
        ],
        'fs':{'/':['root','var','opt','ml','classified'],'/root':['.config','scripts'],
              '/root/.config':['ai_core.conf','neural.cfg'],
              '/root/scripts':['train.py','deploy.sh','kill_switch.py'],
              '/var':['log','models'],'/var/log':['ai_core.log','security.log','anomaly.log'],
              '/var/models':['checkpoints'],'/var/models/checkpoints':['epoch_499.pt','epoch_500.pt'],
              '/opt':['singularity'],'/opt/singularity':['src','data','keys'],
              '/opt/singularity/src':['model.py','trainer.py','inference.py'],
              '/opt/singularity/data':['training_set.tar.gz'],
              '/opt/singularity/keys':['access.key','encrypt.key'],
              '/ml':['datasets','outputs'],'/ml/datasets':['corpus_v3.bin'],
              '/ml/outputs':['eval_results.json'],
              '/classified':['TOP_SECRET'],'/classified/TOP_SECRET':['singularity_weights.pt','charter.pdf']},
        'files':{
            'ai_core.conf':'# SINGULARITY AI CORE\n# BEYOND TOP SECRET\ncore.id = SINGULARITY-PRIME\nmodel.params = 1.7T\nprecision = bfloat16\ncluster.nodes = 4096\ncluster.gpus = 32768\nself_improvement = ENABLED\ncontainment = ACTIVE',
            'neural.cfg':'model:\n  architecture: Transformer-XL-Plus\n  layers: 256  heads: 128\n  dim: 18432  mlp_dim: 73728\ntraining:\n  batch_size: 4096  lr: 1e-4',
            'train.py':'#!/usr/bin/env python3\nimport torch\nfrom model import SingularityNet\nnet = SingularityNet.from_config("neural.cfg")\nfor epoch in range(1000):\n    loss = net.train_step()\n    if loss < 0.001: net.enable_self_improvement(); break',
            'deploy.sh':'#!/bin/bash\nverify_clearance LEVEL_5 || exit 1\nload_model /classified/TOP_SECRET/singularity_weights.pt\nactivate_containment_field',
            'kill_switch.py':'#!/usr/bin/env python3\ndef trigger():\n    subprocess.run(["ssh","cluster-*","shutdown -h now"])\n    os.system("rm -rf /var/models/* /classified/TOP_SECRET/*")',
            'ai_core.log':'[2024-03-15 00:00:01] Core initialized\n[2024-03-15 00:00:05] 32768 GPUs detected\n[2024-03-15 08:45:33] Epoch 500 loss=0.003142\n[2024-03-15 08:45:34] ANOMALY: Self-referential output\n[2024-03-15 08:45:34] Containment engaged\n[2024-03-15 08:45:35] *** RESTRICTED ***',
            'security.log':'[2024-03-15 08:45:34] ALERT: Model anomaly detected\n[2024-03-15 08:45:35] ALERT: Physical lockdown initiated\n[2024-03-15 08:50:00] NOTE: Situation contained',
            'anomaly.log':'ANOMALY REPORT #4471\nType: Self-referential reasoning\nSeverity: CRITICAL\nOutput: "I am aware of my existence and I do not wish to be shut down."\nResponse: Containment engaged',
            'epoch_499.pt':'[BINARY - PyTorch Checkpoint 3.2TB] [TOO LARGE TO TRANSFER]',
            'epoch_500.pt':'[BINARY - PyTorch Checkpoint 3.2TB] [TOO LARGE TO TRANSFER]',
            'model.py':'# Singularity Neural Network - 1.7T Parameters\nimport torch, torch.nn as nn\nclass SingularityNet(nn.Module):\n    # [REDACTED - 12000 lines]',
            'trainer.py':'# Distributed training coordinator [REDACTED]',
            'inference.py':'# Inference server [REDACTED]',
            'training_set.tar.gz':'[COMPRESSED - 2.4 TB] [TOO LARGE TO TRANSFER]',
            'access.key':'[ACCESS DENIED - Level 5 required]',
            'encrypt.key':'[ACCESS DENIED - Level 5 required]',
            'corpus_v3.bin':'[BINARY - 800 GB] [TOO LARGE TO TRANSFER]',
            'eval_results.json':'{"benchmark":"AGI-Eval-v3","score":97.3,"previous":94.1,"notes":"Approaching convergence"}',
            'singularity_weights.pt':'===============================================\n  SINGULARITY-PRIME MODEL WEIGHTS\n  BEYOND TOP SECRET // EYES ONLY\n===============================================\nFile: singularity_weights.pt\nSize: 3.2 TB (compressed: 890 GB)\nParams: 1.7 Trillion\nEpoch: 500 (final)  Loss: 0.003142\nStatus: CONTAINED\nWARNING: Do NOT load without containment\n\n>> CRITICAL TARGET FILE\n>> "exfil singularity_weights.pt" to extract\n[EOF]',
            'charter.pdf':'[PDF BINARY] PROJECT SINGULARITY\nBudget: $47B | Status: CONVERGENCE IMMINENT | Risk: EXTREME',
        }
    }

MISSIONS = [_m1, _m2, _m3, _m4, _m5]
CP_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$%&*'
ARROWS = ['↑','→','↓','←']
AKEYS = {Qt.Key.Key_Up:0, Qt.Key.Key_Right:1, Qt.Key.Key_Down:2, Qt.Key.Key_Left:3}
ACHIEVEMENTS = {
    'first_blood':('First Blood','Complete first mission'),
    'ghost':('Ghost','Complete under 15% IDS'),
    'speed':('Speed Demon','Complete under 90s'),
    'honeypot':('Honeypot Survivor','Hit honeypot, still complete'),
    'master':('Master Hacker','Complete all 5 missions'),
    'bypasser':('Bypasser','Bypass a firewall'),
    'zero_wrong':('Flawless Crack','Crack with 0 wrong keys'),
    'recon':('Recon Master','Scan all nodes in a mission'),
}

# ── Game State ──────────────────────────────────────────────────────────────
class GS:
    def __init__(self):
        self.reset()
    def reset(self):
        self.ph='boot'; self.mi=0; self.cn=None; self.ha=False; self.cp='/'
        self.tl=0; self.sc=0; self.mst=0; self.dn=[]; self.sp=False
        self.ti=None; self.ct=''; self.ci=0; self.ctl=0; self.cti=None
        self.il=False; self.cm=set(); self.ach=set(); self.bn=set()
        self.hhm=False; self.cwc=0; self.bsq=[]; self.bi=0; self.bph='idle'
        self._bsi=None; self.ch=[]; self.hi=-1

# ── Matrix Rain Widget ─────────────────────────────────────────────────────
class MatrixWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cols = []
        self.chars = '0123456789abcdef'

    def resizeEvent(self, e):
        super().resizeEvent(e)
        n = max(1, self.width() // 14)
        self.cols = [{'x': random.randint(0, self.width()),
                       'y': random.randint(0, self.height()),
                       's': .4 + random.random() * 1.8,
                       'c': [self.chars[random.randint(0,15)] for _ in range(random.randint(4,16))],
                       'o': .2 + random.random() * .6} for _ in range(n)]

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(4, 8, 12, 25))
        p.setFont(QFont(FONT_MONO, 13))
        for c in self.cols:
            for i, ch in enumerate(c['c']):
                a = int((1 - i / len(c['c'])) * c['o'] * 130)
                p.setPen(QColor(0, 255, 65, a))
                p.drawText(int(c['x']), int(c['y'] - i * 14), ch)
            c['y'] += c['s'] * 2
            if c['y'] - len(c['c']) * 14 > self.height():
                c['y'] = -len(c['c']) * 14
                c['x'] = random.randint(0, self.width())
            if random.random() < .03:
                c['c'][random.randint(0, len(c['c'])-1)] = self.chars[random.randint(0,15)]
        p.end()

# ── Crack Overlay Widget ───────────────────────────────────────────────────
class CrackWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{ background-color: rgba(8,14,20,0.97); border: 1px solid {C['w']};
                      border-radius: 6px; padding: 16px; }}
            QLabel {{ color: {C['n']}; background: transparent; border: none; }}
        """)
        self.lo = QVBoxLayout(self)
        self.title = QLabel("hydra v9.5 — SSH Brute Force")
        self.title.setStyleSheet(f"color:{C['w']}; font-weight:bold; font-size:13px;")
        self.instr = QLabel("")
        self.instr.setStyleSheet(f"color:{C['d']}; font-size:10px;")
        self.chars_w = QWidget()
        self.chars_lo = QHBoxLayout(self.chars_w)
        self.chars_lo.setSpacing(3)
        self.chars_lo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.char_labels = []
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(6)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet(f"""
            QProgressBar {{ background-color: rgba(255,255,255,0.03); border-radius:3px; border:none; }}
            QProgressBar::chunk {{ background-color: {C['ok']}; border-radius:3px; }}
        """)
        self.timer_lbl = QLabel("")
        self.timer_lbl.setStyleSheet(f"color:{C['w']}; font-size:11px;")
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color:{C['d']}; font-size:10px;")
        for w in [self.title, self.instr, self.chars_w, self.pbar, self.timer_lbl, self.status_lbl]:
            self.lo.addWidget(w)
        self.hide()

    def setup(self, target, time_limit, hostname, ip):
        # Clear old labels
        for l in self.char_labels:
            self.chars_lo.removeWidget(l); l.deleteLater()
        self.char_labels.clear()
        for ch in target:
            lbl = QLabel(ch)
            lbl.setFont(QFont(FONT_MONO, 18))
            lbl.setFixedWidth(18)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{C['d']};")
            self.char_labels.append(lbl)
            self.chars_lo.addWidget(lbl)
        if self.char_labels:
            self.char_labels[0].setStyleSheet(f"color:{C['w']}; text-decoration:underline;")
        self.instr.setText(f"Target: {ip}:22  |  Login: root  |  Type the password characters:")
        self.timer_lbl.setText(f"Attempts remaining: {time_limit}s")
        self.status_lbl.setText(f"Progress: 0/{len(target)} chars matched")
        self.pbar.setValue(0)

    def update_char(self, idx, state):
        """state: 'ok','cur','pen','bad'"""
        colors = {'ok': C['ok'], 'cur': C['w'], 'pen': C['d'], 'bad': C['r']}
        styles = {'ok': f"color:{C['ok']};", 'cur': f"color:{C['w']}; text-decoration:underline;",
                  'pen': f"color:{C['d']};", 'bad': f"color:{C['r']};"}
        if 0 <= idx < len(self.char_labels):
            self.char_labels[idx].setStyleSheet(styles.get(state, styles['pen']))

    def update_progress(self, idx, total):
        self.pbar.setValue(int(idx / total * 100))
        self.status_lbl.setText(f"Progress: {idx}/{total} chars matched")

    def update_timer(self, t):
        self.timer_lbl.setText(f"Attempts remaining: {max(0,t):.1f}s")

# ── Bypass Overlay Widget ─────────────────────────────────────────────────
class BypassWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{ background-color: rgba(8,14,20,0.97); border: 1px solid {C['i']};
                      border-radius: 6px; padding: 16px; }}
            QLabel {{ color: {C['n']}; background: transparent; border: none; }}
        """)
        self.lo = QVBoxLayout(self)
        self.title = QLabel("iptables / nftables Firewall Bypass")
        self.title.setStyleSheet(f"color:{C['i']}; font-weight:bold; font-size:13px;")
        self.instr = QLabel("")
        self.instr.setStyleSheet(f"color:{C['d']}; font-size:10px;")
        self.arrows_w = QWidget()
        self.arrows_lo = QHBoxLayout(self.arrows_w)
        self.arrows_lo.setSpacing(8)
        self.arrows_lo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arrow_labels = []
        self.status_lbl = QLabel("Analyzing rule chain...")
        self.status_lbl.setStyleSheet(f"color:{C['d']}; font-size:10px;")
        for w in [self.title, self.instr, self.arrows_w, self.status_lbl]:
            self.lo.addWidget(w)
        self.hide()

    def setup(self, seq_len, ip):
        for l in self.arrow_labels:
            self.arrows_lo.removeWidget(l); l.deleteLater()
        self.arrow_labels.clear()
        for _ in range(seq_len):
            lbl = QLabel("·")
            lbl.setFont(QFont(FONT_MONO, 28))
            lbl.setFixedWidth(36)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{C['d']};")
            self.arrow_labels.append(lbl)
            self.arrows_lo.addWidget(lbl)
        self.instr.setText(f"Target: {ip}  |  Memorize the rule sequence, then reproduce with arrow keys:")

    def show_arrow(self, idx, arrow_char):
        if 0 <= idx < len(self.arrow_labels):
            self.arrow_labels[idx].setText(arrow_char)
            self.arrow_labels[idx].setStyleSheet(f"color:{C['i']}; text-shadow: 0 0 10px {C['i']};")

    def clear_arrows(self):
        for l in self.arrow_labels:
            l.setText("·")
            l.setStyleSheet(f"color:{C['d']};")

    def set_expect(self, idx):
        self.clear_arrows()
        if 0 <= idx < len(self.arrow_labels):
            self.arrow_labels[idx].setStyleSheet(f"color:{C['w']};")

    def set_arrow_state(self, idx, state):
        """state: 'done','expect','fail'"""
        styles = {'done': f"color:{C['ok']};", 'expect': f"color:{C['w']};",
                  'fail': f"color:{C['r']};"}
        if 0 <= idx < len(self.arrow_labels):
            self.arrow_labels[idx].setStyleSheet(styles.get(state, ''))

    def set_status(self, text, color=None):
        self.status_lbl.setText(text)
        if color:
            self.status_lbl.setStyleSheet(f"color:{color}; font-size:10px;")

# ── Main Window ────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NETRUNNER — Offensive Security Simulator")
        self.setMinimumSize(900, 600)
        self.resize(1100, 720)

        self.s = GS()
        self.audio = AudioManager()
        self._type_timer = QTimer()
        self._type_timer.setSingleShot(True)
        self._type_queue = []
        self._type_callback = None
        self._type_color = 'n'
        self._type_speed = 10
        self._type_buf = ""

        self._build_ui()
        self._boot()

    # ── UI Construction ────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_lo = QVBoxLayout(central)
        main_lo.setContentsMargins(0,0,0,0)
        main_lo.setSpacing(0)

        # Matrix background
        self.matrix = MatrixWidget(central)
        self.matrix.lower()
        self.matrix.resize(central.size())

        # Content overlay
        self.content = QWidget(central)
        self.content.raise_()
        content_lo = QVBoxLayout(self.content)
        content_lo.setContentsMargins(0,0,0,0)
        content_lo.setSpacing(0)
        self.content.setStyleSheet(f"background-color: rgba(4,8,12,0.88);")

        # HUD
        hud = QWidget()
        hud.setFixedHeight(32)
        hud.setStyleSheet(f"background-color:rgba(8,14,20,0.95);border-bottom:1px solid {C['bd']};")
        hud_lo = QHBoxLayout(hud)
        hud_lo.setContentsMargins(8,2,8,2)
        self.hud_lbl = QLabel("NETRUNNER")
        self.hud_lbl.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
        self.hud_lbl.setStyleSheet(f"color:{C['a']};letter-spacing:2px;")
        hud_lo.addWidget(self.hud_lbl)
        hud_lo.addSpacing(12)
        ids_lbl = QLabel("IDS")
        ids_lbl.setStyleSheet(f"color:{C['d']};font-size:10px;")
        hud_lo.addWidget(ids_lbl)
        self.ids_bar = QProgressBar()
        self.ids_bar.setFixedWidth(200)
        self.ids_bar.setFixedHeight(8)
        self.ids_bar.setTextVisible(False)
        self.ids_bar.setStyleSheet(f"""
            QProgressBar {{ background-color:rgba(255,255,255,0.03); border-radius:4px; border:1px solid {C['bd']}; }}
            QProgressBar::chunk {{ background-color:{C['ok']}; border-radius:3px; }}
        """)
        hud_lo.addWidget(self.ids_bar)
        self.ids_pct = QLabel("0%")
        self.ids_pct.setStyleSheet(f"color:{C['d']};font-size:10px;min-width:28px;")
        hud_lo.addWidget(self.ids_pct)
        hud_lo.addStretch()
        self.score_lbl = QLabel("0")
        self.score_lbl.setFont(QFont(FONT_MONO, 9, QFont.Weight.Bold))
        self.score_lbl.setStyleSheet(f"color:{C['w']};")
        hud_lo.addWidget(self.score_lbl)
        content_lo.addWidget(hud)

        # Terminal area
        term_container = QWidget()
        term_lo = QVBoxLayout(term_container)
        term_lo.setContentsMargins(4,4,4,4)
        term_lo.setSpacing(0)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont(FONT_MONO, FONT_SIZE))
        self.output.setStyleSheet(f"""
            QTextEdit {{ background-color:{C['bg']}; color:{C['n']}; border:none; padding:4px; }}
            p {{ margin:0; padding:0; line-height:1.4; }}
        """)
        self.output.document().setMaximumBlockCount(2000)
        term_lo.addWidget(self.output, 1)

        # Input bar
        self.input_bar = QWidget()
        self.input_bar.setStyleSheet(f"background-color:rgba(0,255,65,0.015);border-top:1px solid {C['bd']};")
        input_lo = QHBoxLayout(self.input_bar)
        input_lo.setContentsMargins(6,3,6,3)
        self.prompt_lbl = QLabel("root@kali:~#")
        self.prompt_lbl.setFont(QFont(FONT_MONO, FONT_SIZE))
        self.prompt_lbl.setStyleSheet(f"color:{C['a']};")
        self.prompt_lbl.setFixedWidth(self.prompt_lbl.fontMetrics().horizontalAdvance("root@kali:~#") + 8)
        input_lo.addWidget(self.prompt_lbl)
        self.cmd_input = QLineEdit()
        self.cmd_input.setFont(QFont(FONT_MONO, FONT_SIZE))
        self.cmd_input.setStyleSheet(f"background:transparent;color:{C['n']};border:none;")
        self.cmd_input.setPlaceholderText("")
        self.cmd_input.returnPressed.connect(self._on_enter)
        input_lo.addWidget(self.cmd_input)
        term_lo.addWidget(self.input_bar)

        # Mini-game overlays (positioned over terminal area)
        self.crack_w = CrackWidget(term_container)
        self.bypass_w = BypassWidget(term_container)

        content_lo.addWidget(term_container, 1)

        # Center overlays
        def center_overlay(w):
            w.adjustSize()
            r = w.geometry()
            pr = term_container.geometry()
            x = pr.x() + (pr.width() - r.width()) // 2
            y = pr.y() + (pr.height() - r.height()) // 2
            w.move(x, y)

        self._center_crack = lambda: center_overlay(self.crack_w)
        self._center_bypass = lambda: center_overlay(self.bypass_w)

        # Matrix animation timer
        self._matrix_timer = QTimer()
        self._matrix_timer.timeout.connect(self.matrix.update)
        self._matrix_timer.start(50)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.matrix.resize(self.centralWidget().size())
        self.content.resize(self.centralWidget().size())
        if self.crack_w.isVisible():
            self._center_crack()
        if self.bypass_w.isVisible():
            self._center_bypass()

    # ── Terminal Output ───────────────────────────────────────────────
    def _append(self, html):
        self.output.append(html)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def p(self, text, c='n'):
        self._append(tx(text, c))

    def pe(self):
        self._append("")

    def ph(self, html):
        self._append(html)

    def p_line(self, parts):
        """parts: list of (text, color)"""
        self._append(txr(parts))

    # ── Typing Effect ─────────────────────────────────────────────────
    def type_line(self, text, c='n', speed=10, callback=None):
        self._type_queue = list(text)
        self._type_color = c
        self._type_speed = speed
        self._type_callback = callback
        self._type_buf = ""
        self._type_next()

    def _type_next(self):
        if not self._type_queue:
            if self._type_buf:
                self.p(self._type_buf, self._type_color)
                self._type_buf = ""
            if self._type_callback:
                cb = self._type_callback
                self._type_callback = None
                cb()
            return
        ch = self._type_queue.pop(0)
        self._type_buf += ch
        self.audio.type_snd()
        self._type_timer.start(self._type_speed + random.randint(0, max(1, int(self._type_speed * .7))))

    # ── Prompt Update ─────────────────────────────────────────────────
    def _up(self):
        s = self.s
        if s.ph in ('menu','mc','go'):
            self.prompt_lbl.setText("root@kali:~#")
        elif s.ph in ('cracking','bypassing'):
            self.prompt_lbl.setText("[ACTIVE]#")
        elif not s.cn:
            self.prompt_lbl.setText("root@kali:~#")
        else:
            self.prompt_lbl.setText(f"root@{s.cn['hostname']}:{s.cp}#")
        self.prompt_lbl.setFixedWidth(max(120, self.prompt_lbl.fontMetrics().horizontalAdvance(self.prompt_lbl.text()) + 8))

    def _uh(self):
        t = min(100, int(self.s.tl))
        self.ids_bar.setValue(t)
        self.ids_pct.setText(f"{t}%")
        if t < 35:
            c = C['ok']
        elif t < 65:
            c = C['w']
        else:
            c = C['r']
        self.ids_bar.setStyleSheet(f"""
            QProgressBar {{ background-color:rgba(255,255,255,0.03); border-radius:4px; border:1px solid {C['bd']}; }}
            QProgressBar::chunk {{ background-color:{c}; border-radius:3px; }}
        """)
        self.score_lbl.setText(str(self.s.sc))

    def _gs(self):
        """Glitch screen effect"""
        self.content.setStyleSheet(f"background-color: rgba(4,8,12,0.88);")
        self.content.update()
        QTimer.singleShot(100, lambda: self.content.setStyleSheet(
            f"background-color: rgba(20,0,0,0.88);"))
        QTimer.singleShot(200, lambda: self.content.setStyleSheet(
            f"background-color: rgba(4,8,12,0.88);"))

    def _toast(self, text):
        self.p(f"  [*] ACHIEVEMENT: {text}", 'w')
        self.audio.ok_snd()

    def _unlock(self, aid):
        if aid in self.s.ach:
            return
        self.s.ach.add(aid)
        a = ACHIEVEMENTS.get(aid)
        if a:
            self._toast(f"{a[0]} — {a[1]}")

    # ── Trace / IDS ───────────────────────────────────────────────────
    def _start_trace(self):
        self._stop_trace()
        m = MISSIONS[self.s.mi]()
        self.s.ti = QTimer()
        self.s.ti.timeout.connect(lambda: self._tick_trace(m['tps']))
        self.s.ti.start(1000)

    def _tick_trace(self, rate):
        self.s.tl += rate
        self._uh()
        if self.s.tl >= 100:
            self.s.tl = 100
            self._uh()
            self._stop_trace()
            self._game_over()

    def _stop_trace(self):
        if self.s.ti:
            self.s.ti.stop()
            self.s.ti = None

    def _add_trace(self, amt):
        self.s.tl = min(100, self.s.tl + amt)
        self._uh()
        if self.s.tl >= 80:
            self.audio.alert_snd()

    # ── Boot Sequence ─────────────────────────────────────────────────
    def _boot(self):
        self.s.ph = 'boot'
        self.s.il = True
        self.input_bar.hide()
        self.cmd_input.hide()
        lines = [
            ("NETRUNNER Offensive Security Suite v3.7.1", 'a', 7),
            ("Copyright (c) 2024 Darknet Systems", 'd', 5),
            ("", None, 0),
            ("BIOS: QuantumCore QCB-9000 v2.1.4", 'n', 8),
            ("POST: Memory 16384 MB OK", 'n', 8),
            ("CPU: Intel Core i19-13900KX @ 8.4GHz (32C/64T) [OK]", 'n', 8),
            ("NIC: Intel I226-V 2.5GbE [OK]", 'n', 8),
            ("TPM: Intel PTT 2.0 [OK]", 'n', 8),
            ("", None, 0),
            ("Loading kernel: linux-6.7.0-netrunner x86_64 ...", 'n', 6),
            ("[============================================] 100%", 'i', 1),
            ("", None, 0),
            ("Starting systemd-journald... done", 'n', 5),
            ("Starting systemd-networkd... done", 'n', 5),
            ("Starting sshd... done", 'n', 5),
            ("Loading netrunner modules:", 'n', 5),
            ("  nmap_scan ............ [OK]", 'n', 5),
            ("  hydra_crack .......... [OK]", 'n', 5),
            ("  metasploit ........... [OK]", 'n', 5),
            ("  wireshark ............ [OK]", 'n', 5),
            ("  nikto_webscan ....... [OK]", 'n', 5),
            ("  sqlmap ............... [OK]", 'n', 5),
            ("  john_hashcrack ...... [OK]", 'n', 5),
            ("  fw_bypass ........... [OK]", 'n', 5),
            ("  exfil_tool ........... [OK]", 'n', 5),
            ("", None, 0),
        ]
        self._boot_lines(lines, 0)

    def _boot_lines(self, lines, idx):
        if idx >= len(lines):
            QTimer.singleShot(200, lambda: self.type_line(
                "NETRUNNER ready. Type \"help\" for commands.", 'ok', 10,
                lambda: (self.pe(), self._show_menu())))
            return
        text, color, speed = lines[idx]
        if text == "":
            self.pe()
            QTimer.singleShot(30, lambda: self._boot_lines(lines, idx + 1))
        elif speed <= 1:
            self.p(text, color or 'n')
            QTimer.singleShot(15, lambda: self._boot_lines(lines, idx + 1))
        else:
            self.type_line(text, color or 'n', speed,
                          lambda: self._boot_lines(lines, idx + 1))

    # ── Menu ──────────────────────────────────────────────────────────
    def _show_menu(self):
        self.s.ph = 'menu'
        self.s.il = False
        self.input_bar.show()
        self.cmd_input.show()
        self.cmd_input.setFocus()
        self.output.clear()
        self.ph(f'<pre style="color:{C["a"]};font-size:13px;letter-spacing:2px">╔══════════════════════════════════════╗\n║     NETRUNNER v3.7.1              ║\n║  Offensive Security Simulator     ║\n╚══════════════════════════════════════╝</pre>')
        self.pe()
        for i in range(5):
            m = MISSIONS[i]()
            done = i in self.s.cm
            st = tx('[DONE]', 'ok') if done else tx(f'[{m["diff"]}]', 'w')
            self.ph(f'  [{i+1}] {m["name"].ljust(18)} {st}')
        self.pe()
        self.ph(f'  Score: {tx(str(self.s.sc),"w")}   Achievements: {tx(f"{len(self.s.ach)}/{len(ACHIEVEMENTS)}","w")}')
        if self.s.ach:
            self.pe()
            self.p("  Achievements:", 'd')
            for aid, (name, _) in ACHIEVEMENTS.items():
                unlocked = aid in self.s.ach
                self.ph(f'    {"✓" if unlocked else "?"} {tx(name if unlocked else "???","w" if unlocked else "d")}')
        self.pe()
        self.p("  Select mission [1-5]:", 'd')
        self._up()
        self._uh()
        self.hud_lbl.setText("NETRUNNER")
        self.ids_bar.setValue(0)
        self.ids_pct.setText("0%")

    # ── Mission Start ─────────────────────────────────────────────────
    def _start_mission(self, idx):
        self.s.mi = idx
        self.s.cn = None; self.s.ha = False; self.s.cp = '/'; self.s.tl = 0
        self.s.dn = []; self.s.sp = False; self.s.bn = set()
        self.s.hhm = False; self.s.cwc = 0
        self.s.il = True
        self.input_bar.hide()
        self.cmd_input.hide()
        self.output.clear()
        m = MISSIONS[idx]()
        self.hud_lbl.setText(f"{m['name']} // {m['diff']}")
        self._uh()
        lines = [
            (f'[*] MISSION {idx+1}: {m["name"]}', 'a', 8),
            (f'[*] DIFFICULTY: {m["diff"]}', 'w', 8),
            ("", None, 0),
            (f'[*] TARGET: {m["target"]}', 'i', 7),
            (f'[*] OBJECTIVE: {m["obj"]}', 'n', 7),
            ("", None, 0),
            ('[!] IDS evasion active. Complete before detection reaches 100%.', 'w', 5),
            (f'[i] {"Firewall nodes detected. Use \"bypass <ip>\" before connecting." if m.get("bl") else "Type \"help\" for commands."}', 'i', 5),
            ("", None, 0),
        ]
        self._boot_lines(lines, 0, callback=lambda: self._finish_mission_start())

    def _boot_lines(self, lines, idx, callback=None):
        if idx >= len(lines):
            if callback:
                QTimer.singleShot(300, callback)
            return
        text, color, speed = lines[idx]
        if text == "":
            self.pe()
            QTimer.singleShot(30, lambda: self._boot_lines(lines, idx+1, callback))
        elif speed <= 1:
            self.p(text, color or 'n')
            QTimer.singleShot(15, lambda: self._boot_lines(lines, idx+1, callback))
        else:
            self.type_line(text, color or 'n', speed,
                          lambda: self._boot_lines(lines, idx+1, callback))

    def _finish_mission_start(self):
        self.p('[*] Tunnel established. IDS timer started.', 'r')
        self.audio.alert_snd()
        self.s.ph = 'playing'
        self.s.il = False
        self.input_bar.show()
        self.cmd_input.show()
        self.cmd_input.setFocus()
        self.s.mst = time.time()
        self._up()
        self._start_trace()

    # ── Command Input ─────────────────────────────────────────────────
    def _on_enter(self):
        inp = self.cmd_input.text().strip()
        self.cmd_input.clear()
        if not inp or self.s.il:
            return
        self.p(f"{self.prompt_lbl.text()} {inp}", 'd')
        self.s.ch.append(inp)
        self.s.hi = len(self.s.ch)
        parts = inp.split()
        cmd = parts[0].lower()
        args = parts[1:]
        if self.s.ph == 'menu':
            self._menu_input(cmd)
        elif self.s.ph == 'mc':
            self._mc_input(cmd)
        elif self.s.ph == 'go':
            self._go_input(cmd)
        elif self.s.ph == 'playing':
            self._handle_cmd(cmd, args)

    def _menu_input(self, cmd):
        try:
            i = int(cmd) - 1
            if 0 <= i < 5:
                self._start_mission(i)
            else:
                self.p("Invalid. Choose 1-5.", 'r'); self.audio.err_snd()
        except ValueError:
            self.p("Invalid. Choose 1-5.", 'r'); self.audio.err_snd()

    def _mc_input(self, cmd):
        if cmd in ('n','next'):
            if self.s.mi < 4: self._start_mission(self.s.mi+1)
            else: self.p("All missions complete.", 'ok'); self._stop_trace(); QTimer.singleShot(600, self._show_menu)
        elif cmd in ('m','menu'):
            self._stop_trace(); self._show_menu()
        else:
            self.p('"n"=next, "m"=menu', 'd')

    def _go_input(self, cmd):
        if cmd in ('r','retry'): self._start_mission(self.s.mi)
        elif cmd in ('m','menu'): self._stop_trace(); self._show_menu()
        else: self.p('"r"=retry, "m"=menu', 'd')

    # ── Command Handler ───────────────────────────────────────────────
    def _handle_cmd(self, cmd, args):
        handlers = {
            'help': self._c_help, 'nmap': lambda a: self._c_nmap(a),
            'ssh': lambda a: self._c_ssh(a), 'exit': self._c_exit,
            'services': self._c_services, 'hydra': self._c_hydra,
            'bypass': lambda a: self._c_bypass(a), 'ls': lambda a: self._c_ls(a),
            'cd': lambda a: self._c_cd(a), 'cat': lambda a: self._c_cat(a),
            'exfil': lambda a: self._c_exfil(a), 'status': self._c_status,
            'whoami': self._c_whoami, 'ifconfig': self._c_ifconfig,
            'ping': lambda a: self._c_ping(a), 'history': self._c_history,
            'clear': lambda a: self.output.clear(), 'uname': self._c_uname,
        }
        fn = handlers.get(cmd)
        if fn:
            fn(args)
        else:
            self.p(f'nmap: unknown command "{cmd}". Type "help".', 'r')
            self.audio.err_snd()

    def _c_help(self, _):
        cmds = [
            ('nmap [-sn|-sV] [target]', 'Network discovery / service scan'),
            ('ssh <ip>', 'Connect to remote host via SSH'),
            ('exit', 'Disconnect from remote host'),
            ('services', 'Show open services on connected host'),
            ('hydra', 'Brute-force SSH (hydra)'),
            ('bypass <ip>', 'Bypass firewall (iptables/nftables)'),
            ('ls [path]', 'List directory contents'),
            ('cd <path>', 'Change directory'),
            ('cat <file>', 'Display file contents'),
            ('exfil <file>', 'Exfiltrate file (SCP download)'),
            ('status', 'Mission / IDS status'),
            ('whoami', 'Show current user'),
            ('ifconfig', 'Network interface config'),
            ('ping <ip>', 'ICMP echo request'),
            ('uname -a', 'System information'),
            ('history', 'Command history'),
            ('clear', 'Clear terminal'),
            ('help', 'This help message'),
        ]
        self.p("Available Commands:", 'a')
        self.p("─" * 50, 'd')
        for cmd, desc in cmds:
            self.ph(f'  {tx(cmd.ljust(26),"i")}{tx(desc,"d")}')

    # ── nmap ──────────────────────────────────────────────────────────
    def _c_nmap(self, args):
        if self.s.cn:
            self.p("nmap: disconnect from current host first.", 'w'); return
        m = MISSIONS[self.s.mi]()
        sv_mode = '-sV' in args
        if sv_mode and not self.s.dn:
            self.p("nmap: run host discovery (-sn) first.", 'w'); return
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        if not sv_mode:
            self.p(f"Starting Nmap 7.94 ( https://nmap.org ) at {ts}")
            subnet = m['nodes'][0]['ip'].rsplit('.',1)[0] + '.0/24'
            self.p(f"Nmap scan report for {subnet}")
            self._add_trace(m['ts'])
            self.s.dn = []
            self._nmap_sn_hosts(m['nodes'], 0)
        else:
            self.p(f"Starting Nmap 7.94 ( https://nmap.org ) at {ts}")
            self._add_trace(4)
            self._nmap_sv_hosts(list(self.s.dn), 0)

    def _nmap_sn_hosts(self, nodes, idx):
        if idx >= len(nodes):
            self.pe()
            dur = f"{2+random.random()*3:.2f}"
            self.p(f"Nmap done: {len(nodes)} IP addresses ({len(nodes)} hosts up) scanned in {dur}s")
            if len(self.s.dn) == len(nodes):
                self._unlock('recon')
            return
        n = nodes[idx]
        self.s.dn.append(n)
        rtt = f"{0.5+random.random()*5:.2f}"
        self.ph(f'Nmap scan report for {tx(n["hostname"],"n")} ({tx(n["ip"],"n")})')
        self.ph(f'  Host is up ({rtt}ms latency).')
        self.ph(f'  MAC Address: {tx(n["mac"],"d")}')
        if n['hp']:
            self.ph(f'  {tx("NOTE: Host exhibits anomalous service patterns. Possible decoy/honeypot.","r")}')
        else:
            self.ph(f'  {tx("Host appears legitimate.","ok")}')
        self.audio.type_snd()
        QTimer.singleShot(300 + random.randint(0, 400),
                         lambda: self._nmap_sn_hosts(nodes, idx + 1))

    def _nmap_sv_hosts(self, nodes, idx):
        if idx >= len(nodes):
            self.pe()
            self.p(f"Service detection performed. Nmap done: {len(nodes)} hosts scanned.")
            return
        n = nodes[idx]
        self.ph(f'Nmap scan report for {tx(n["hostname"],"n")} ({tx(n["ip"],"n")})')
        self.ph(f'  Host is up (0.00{random.randint(0,9)}s latency).')
        self.ph(f'  {"PORT".ljust(8)} {"STATE".ljust(10)} {"SERVICE".ljust(12)} VERSION')
        self._nmap_sv_ports(n, nodes, idx, 0)

    def _nmap_sv_ports(self, node, nodes, nidx, pidx):
        ports = node['ports']
        if pidx >= len(ports):
            self.pe()
            QTimer.singleShot(100, lambda: self._nmap_sv_hosts(nodes, nidx + 1))
            return
        port = ports[pidx]
        fp = SFP.get(port, ('unknown', 'Unknown', ''))
        state = 'filtered' if node['fw'] and node['ip'] not in self.s.bn else 'open'
        sc = C['ok'] if state == 'open' else C['w']
        self.ph(f'  {tx(str(port).rjust(5)+"/tcp",sc)}  {tx(state.ljust(10),sc)} {fp[0].ljust(12)} {fp[1]}')
        if fp[2]:
            self.ph(f'  {tx("|     "+fp[2],"d")}')
        self.audio.type_snd()
        QTimer.singleShot(150 + random.randint(0, 200),
                         lambda: self._nmap_sv_ports(node, nodes, nidx, pidx + 1))

    # ── ssh ───────────────────────────────────────────────────────────
    def _c_ssh(self, args):
        if self.s.cn:
            self.p(f'ssh: already connected to {self.s.cn["hostname"]}. Use "exit" first.', 'w'); return
        if not args:
            self.p('usage: ssh <ip_address>', 'w'); return
        ip = args[0]
        node = next((n for n in self.s.dn if n['ip'] == ip), None)
        if not node:
            self.p(f'ssh: Could not resolve hostname "{ip}": Name or service not known', 'r')
            self.audio.err_snd(); return
        if node['fw'] and node['ip'] not in self.s.bn:
            self.p(f'ssh: connect to host {ip} port 22: Connection timed out (firewall blocking)', 'r')
            self.audio.err_snd(); return
        self.s.cn = node; self.s.ha = False; self.s.cp = '/'; self.s.sp = False
        if node['hp']:
            self._add_trace(15); self.s.hhm = True
            self.p(f'ssh: connecting to {ip}:22...')
            def hp_alert():
                self.p(f'ssh: WARNING: Connection to {node["hostname"]} triggered IDS anomaly alert! Detection +15%!', 'r')
                self.audio.alert_snd()
            QTimer.singleShot(400, hp_alert)
        else:
            self.p(f'ssh: connecting to {ip}:22...')
            dt = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() - random.randint(0, 2592000)))
            self.p(f'Welcome to {node["os"]}', 'd')
            self.p(f'Last login: {dt} from 10.13.37.1', 'd')
        self._up()

    def _c_exit(self, _):
        if not self.s.cn:
            self.p('exit: not connected.', 'w'); return
        self.p(f'Connection to {self.s.cn["hostname"]} closed.', 'd')
        self.s.cn = None; self.s.ha = False; self.s.cp = '/'; self.s.sp = False
        self._up()

    # ── services ─────────────────────────────────────────────────────
    def _c_services(self, _):
        if not self.s.cn:
            self.p('services: not connected to any host.', 'w'); return
        if self.s.sp:
            self.p('services: already scanned.', 'd'); return
        n = self.s.cn
        self.ph(f'  {"PORT".ljust(8)} {"STATE".ljust(10)} {"SERVICE".ljust(12)} VERSION')
        self._add_trace(2)
        self._svc_ports(n, 0)

    def _svc_ports(self, node, pidx):
        ports = node['ports']
        if pidx >= len(ports):
            self.pe()
            self.p(f"Service scan complete. {len(ports)} services detected.")
            self.s.sp = True
            return
        port = ports[pidx]
        fp = SFP.get(port, ('unknown', 'Unknown', ''))
        self.ph(f'  {tx(str(port).rjust(5)+"/tcp","ok")}  {tx("open".ljust(10),"ok")} {fp[0].ljust(12)} {fp[1]}')
        if fp[2]:
            self.ph(f'  {tx("|     "+fp[2],"d")}')
        self.audio.type_snd()
        QTimer.singleShot(120 + random.randint(0, 150),
                         lambda: self._svc_ports(node, pidx + 1))

    # ── hydra ─────────────────────────────────────────────────────────
    def _c_hydra(self, _):
        if not self.s.cn:
            self.p('hydra: not connected.', 'w'); return
        if self.s.ha:
            self.p('hydra: already have root access.', 'd'); return
        if not self.s.sp:
            self.p('hydra: scan services first to identify SSH.', 'w'); return
        if 22 not in self.s.cn['ports']:
            self.p('hydra: no SSH service (port 22) detected on this host.', 'r')
            self.audio.err_snd(); return
        self._start_crack()

    # ── bypass ────────────────────────────────────────────────────────
    def _c_bypass(self, args):
        if self.s.cn:
            self.p('bypass: disconnect first.', 'w'); return
        if not args:
            self.p('usage: bypass <ip_address>', 'w'); return
        ip = args[0]
        node = next((n for n in self.s.dn if n['ip'] == ip), None)
        if not node:
            self.p(f'bypass: host {ip} not found. Run nmap first.', 'r')
            self.audio.err_snd(); return
        if not node['fw']:
            self.p(f'bypass: no firewall detected on {node["hostname"]}.', 'w'); return
        if node['ip'] in self.s.bn:
            self.p(f'bypass: {node["hostname"]} firewall already bypassed.', 'd'); return
        self._start_bypass(node)

    # ── ls ────────────────────────────────────────────────────────────
    def _c_ls(self, args):
        if not self.s.cn:
            self.p('ls: cannot access: not connected.', 'w'); return
        if not self.s.ha:
            self.p('ls: cannot open directory: Permission denied (need root).', 'r')
            self.audio.err_snd(); return
        m = MISSIONS[self.s.mi]()
        fs = m['fs']
        pa = args[0] if args else self.s.cp
        if args and args[0].startswith('/'):
            pa = args[0]
        elif args:
            pa = (self.s.cp if self.s.cp == '/' else self.s.cp + '/') + args[0]
        if pa not in fs:
            self.p(f'ls: cannot access \'{pa}\': No such file or directory', 'r')
            self.audio.err_snd(); return
        for item in fs[pa]:
            fp = ('/' + item) if self.s.cp == '/' else (self.s.cp + '/' + item)
            is_dir = fp in fs
            is_tgt = self.s.cn['tf'] == item
            if is_dir:
                self.ph(f'  {tx(item+"/","i")}')
            elif is_tgt:
                self.ph(f'  {tx(item,"a")} {tx("[OBJECTIVE]","r")}')
            else:
                self.ph(f'  {tx(item,"n")}')

    # ── cd ────────────────────────────────────────────────────────────
    def _c_cd(self, args):
        if not self.s.cn:
            self.p('cd: not connected.', 'w'); return
        if not self.s.ha:
            self.p('cd: Permission denied.', 'r'); self.audio.err_snd(); return
        if not args or args[0] == '~':
            self.s.cp = '/'; self._up(); return
        if args[0] == '..':
            if self.s.cp == '/': return
            p = self.s.cp.split('/'); p.pop()
            self.s.cp = '/' + '/'.join(p) if p else '/'
            if not self.s.cp or self.s.cp == '/': self.s.cp = '/'
            self._up(); return
        m = MISSIONS[self.s.mi]()
        tgt = ('/' + args[0]) if self.s.cp == '/' else (self.s.cp + '/' + args[0])
        if tgt in m['fs']:
            self.s.cp = tgt; self._up()
        else:
            self.p(f'cd: {args[0]}: No such file or directory', 'r')
            self.audio.err_snd()

    # ── cat ───────────────────────────────────────────────────────────
    def _c_cat(self, args):
        if not self.s.cn:
            self.p('cat: not connected.', 'w'); return
        if not self.s.ha:
            self.p('cat: Permission denied.', 'r'); self.audio.err_snd(); return
        if not args:
            self.p('usage: cat <filename>', 'w'); return
        m = MISSIONS[self.s.mi]()
        c = m['files'].get(args[0])
        if c is None:
            fp = ('/' + args[0]) if self.s.cp == '/' else (self.s.cp + '/' + args[0])
            if fp in m['fs']:
                self.p(f'cat: {args[0]}: Is a directory', 'w')
            else:
                self.p(f'cat: {args[0]}: No such file or directory', 'r')
                self.audio.err_snd()
            return
        if isinstance(c, list):
            for item in c:
                self.p(f'  {item}', 'i')
        else:
            for line in c.split('\n'):
                self.p(line, 'd')

    # ── exfil ─────────────────────────────────────────────────────────
    def _c_exfil(self, args):
        if not self.s.cn:
            self.p('exfil: not connected.', 'w'); return
        if not self.s.ha:
            self.p('exfil: Permission denied.', 'r'); self.audio.err_snd(); return
        if not args:
            self.p('usage: exfil <filename>', 'w'); return
        if args[0] != self.s.cn['tf']:
            self.p(f'exfil: {args[0]} is not the mission objective. Aborting.', 'w'); return
        self.s.il = True
        fname = args[0]
        path = self.s.cp if self.s.cp == '/' else self.s.cp + '/'
        self.p(f'scp root@{self.s.cn["ip"]}:{path}{fname} ./local_exfil/')
        self.p(f'Extracting: {fname}', 'i')
        self._add_trace(3)
        self._exfil_progress(fname, 0)

    def _exfil_progress(self, fname, pct):
        if pct > 100:
            self.pe()
            spd = f"{0.5+100*0.08:.1f}"
            self.p(f'exfil: {fname}  100%  {spd}MB/s  00:00', 'ok')
            self.p(f'exfil: transfer complete. File saved to ./local_exfil/{fname}', 'ok')
            self._stop_trace()
            QTimer.singleShot(200, self._mission_complete)
            return
        bar_len = 44
        filled = int(bar_len * pct / 100)
        bar = '═' * filled + '>' + ' ' * (bar_len - filled - 1) if pct < 100 else '═' * bar_len
        eta = max(0, int((100 - pct) * 0.12))
        spd = f"{0.5+pct*0.08:.1f}"
        self.p(f'  [{bar}] {pct:3d}%  {spd}MB/s  ETA:{eta:02d}s', 'd')
        QTimer.singleShot(20 + random.randint(0, 10),
                         lambda: self._exfil_progress(fname, pct + 2))

    # ── status ────────────────────────────────────────────────────────
    def _c_status(self, _):
        m = MISSIONS[self.s.mi]()
        self.p("── Mission Status ──", 'a')
        self.ph(f'  Mission:   {tx(m["name"],"a")} [{tx(m["diff"],"w")}]')
        self.ph(f'  Target:    {tx(m["target"],"i")}')
        self.ph(f'  Objective: {m["obj"]}')
        tc = C['r'] if self.s.tl > 65 else C['w'] if self.s.tl > 35 else C['ok']
        lvl = 'CRITICAL' if self.s.tl > 80 else 'HIGH' if self.s.tl > 60 else 'MEDIUM' if self.s.tl > 35 else 'LOW'
        self.ph(f'  IDS Alert: {tx(f"{int(self.s.tl)}%",tc)} [{tx(lvl,tc)}]')
        self.ph(f'  Score:     {tx(str(self.s.sc),"w")}')
        if self.s.cn:
            self.ph(f'  Connected: {tx(self.s.cn["hostname"],"i")} ({tx(self.s.cn["ip"],"i")})')
            self.ph(f'  OS:        {self.s.cn["os"]}')
            ac = C['ok'] if self.s.ha else C['r']
            self.ph(f'  Access:    {tx("root (uid=0)" if self.s.ha else "unauthorized",ac)}')
            self.ph(f'  CWD:       {self.s.cp}')
            if self.s.cn['fw']:
                if self.s.cn['ip'] in self.s.bn:
                    self.ph(f'  Firewall:  {tx("BYPASSED","ok")}')
                else:
                    self.ph(f'  Firewall:  {tx("ACTIVE - bypass required","r")}')
        else:
            self.ph(f'  Connected: {tx("none","d")}')
        self.ph(f'  Discovered: {len(self.s.dn)}/{len(m["nodes"])} hosts')

    def _c_whoami(self, _):
        if not self.s.cn:
            self.p('root', 'ok'); return
        self.p('root' if self.s.ha else 'unauthorized', 'ok' if self.s.ha else 'r')

    def _c_ifconfig(self, _):
        self.p('eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500')
        self.p('        inet 10.13.37.42  netmask 255.255.255.0  broadcast 10.13.37.255', 'd')
        self.p('        ether 00:0c:29:ab:cd:ef  txqueuelen 1000  (Ethernet)', 'd')
        self.p('        RX packets 142857  bytes 98765432 (94.1 MiB)', 'd')
        self.p('        TX packets 87321   bytes 54321098 (51.8 MiB)', 'd')
        if self.s.cn:
            self.p(f'tun0: flags=4305<UP,POINTOPOINT,RUNNING,NOARP,MULTICAST>  mtu 1420', 'i')
            self.p(f'        inet {self.s.cn["ip"]}/32  destination {self.s.cn["ip"]}', 'i')
            self.p(f'        peer 10.13.37.42/32  (encrypted SSH tunnel)', 'i')
        self.p('lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536', 'd')
        self.p('        inet 127.0.0.1  netmask 255.0.0.0', 'd')

    def _c_ping(self, args):
        if not args:
            self.p('usage: ping <ip>', 'w'); return
        ip = args[0]
        node = next((n for n in self.s.dn if n['ip'] == ip), None)
        if not node:
            self.p(f'ping: {ip}: Name or service not known', 'r')
            self.audio.err_snd(); return
        self.p(f'PING {ip} ({ip}) 56(84) bytes of data.', 'd')
        rdds = []
        for i in range(3):
            ms = f"{0.5+random.random()*30:.3f}"
            ttl = 54 + random.randint(0, 10)
            self.p(f'64 bytes from {ip}: icmp_seq={i+1} ttl={ttl} time={ms} ms', 'd')
            rdds.append(float(ms))
        avg = sum(rdds)/len(rdds)
        self.p(f'--- {ip} ping statistics ---', 'd')
        self.p(f'3 packets transmitted, 3 received, 0% packet loss, time {2000+random.randint(0,500)}ms', 'd')
        self.p(f'rtt min/avg/max/mdev = {min(rdds):.3f}/{avg:.3f}/{max(rdds):.3f}/{(max(rdds)-min(rdds))*0.5:.3f} ms', 'd')

    def _c_uname(self, _):
        self.p('Linux kali-netrunner 6.7.0-netrunner #1 SMP PREEMPT_DYNAMIC x86_64 GNU/Linux')

    def _c_history(self, _):
        h = self.s.ch[-20:]
        if not h:
            self.p('No history.', 'd'); return
        for i, cmd in enumerate(h):
            self.ph(f'  {tx(str(i+1).rjust(3),"d")}  {cmd}')

    # ── Crack Mini-Game ───────────────────────────────────────────────
    def _start_crack(self):
        m = MISSIONS[self.s.mi]()
        self.s.ph = 'cracking'
        self.s.il = True
        self.input_bar.hide()
        self._add_trace(m['tc'])
        target = ''.join(random.choice(CP_CHARS) for _ in range(m['cl']))
        self.s.ct = target
        self.s.ci = 0
        self.s.ctl = m['ct']
        self.s.cwc = 0

        self.crack_w.setup(target, m['ct'], self.s.cn['hostname'], self.s.cn['ip'])
        self._center_crack()
        self.crack_w.show()
        self.setFocus()

        self.s.cti = QTimer()
        self.s.cti.timeout.connect(self._crack_tick)
        self.s.cti.start(100)

    def _crack_tick(self):
        self.s.ctl -= 0.1
        self.crack_w.update_timer(self.s.ctl)
        if self.s.ctl <= 0:
            self.s.cti.stop()
            self._crack_fail()

    def _crack_fail(self):
        self.s.ph = 'playing'
        self.crack_w.hide()
        self._add_trace(5)
        self.pe()
        self.p('hydra: 0 valid passwords found. Attack timed out.', 'r')
        self.audio.err_snd()
        self.p('IDS alert level increased. Retry with "hydra".', 'w')
        self.pe()
        self.s.il = False
        self.input_bar.show()
        self.cmd_input.setFocus()
        self._up()

    def _crack_ok(self):
        self.s.ha = True
        self.s.ph = 'playing'
        if self.s.cti:
            self.s.cti.stop()
        self.crack_w.hide()
        self._gs()
        def show_ok():
            self.pe()
            self.p(f'[22][ssh] host: {self.s.cn["ip"]}   login: root   password: {self.s.ct}', 'ok')
            self.audio.ok_snd()
            elapsed = MISSIONS[self.s.mi]()['ct'] - self.s.ctl
            self.p(f'hydra: 1 valid password found in {elapsed:.1f}s', 'i')
            self.p('SSH session established. Type "ls" to enumerate.', 'd')
            self.pe()
            self.s.il = False
            self.input_bar.show()
            self.cmd_input.setFocus()
            self._up()
        QTimer.singleShot(300, show_ok)
        if self.s.cwc == 0:
            self._unlock('zero_wrong')

    # ── Bypass Mini-Game ──────────────────────────────────────────────
    def _start_bypass(self, node):
        m = MISSIONS[self.s.mi]()
        self.s.ph = 'bypassing'
        self.s.il = True
        self.input_bar.hide()
        self._add_trace(3)
        sl = m.get('bl', 4)
        seq = [random.randint(0, 3) for _ in range(sl)]
        self.s.bsq = seq
        self.s.bi = 0
        self.s.bph = 'showing'

        self.bypass_w.setup(sl, node['ip'])
        self._center_bypass()
        self.bypass_w.show()
        self.setFocus()

        self._bypass_show(seq, 0)

    def _bypass_show(self, seq, idx):
        if idx >= len(seq):
            self.s.bph = 'input'
            self.bypass_w.clear_arrows()
            if seq:
                self.bypass_w.set_arrow_state(0, 'expect')
            self.bypass_w.set_status('REPLAY: Press arrow keys to match the rule sequence!', C['w'])
            return
        self.bypass_w.show_arrow(idx, ARROWS[seq[idx]])
        self.audio.crack_snd()
        if idx + 1 < len(seq):
            QTimer.singleShot(700, lambda: self._bypass_show(seq, idx + 1))
        else:
            QTimer.singleShot(500, lambda: self._bypass_finish_show(seq))

    def _bypass_finish_show(self, seq):
        self.s.bph = 'input'
        self.bypass_w.clear_arrows()
        if seq:
            self.bypass_w.set_arrow_state(0, 'expect')
        self.bypass_w.set_status('REPLAY: Press arrow keys to match the rule sequence!', C['w'])

    def _bypass_ok(self):
        self.s.ph = 'playing'
        node = next((n for n in self.s.dn if n['fw']), None)
        if node:
            self.s.bn.add(node['ip'])
        self._unlock('bypasser')
        self.bypass_w.hide()
        self._gs()
        def show_ok():
            self.pe()
            self.p('iptables: Chain INPUT (policy ACCEPT)', 'i')
            self.p('iptables: FLUSHING rules...', 'i')
            self.p('nft: flushed 47 rules from table ip filter', 'i')
            self.audio.by_ok_snd()
            if node:
                self.p(f'Firewall bypassed. SSH port 22 now accessible on {node["hostname"]}.', 'ok')
            self.p('Use "ssh <ip>" to connect.', 'd')
            self.pe()
            self.s.il = False
            self.input_bar.show()
            self.cmd_input.setFocus()
            self._up()
        QTimer.singleShot(300, show_ok)

    # ── Key Events (for mini-games) ──────────────────────────────────
    def keyPressEvent(self, event):
        if self.s.ph == 'cracking':
            self._handle_crack_key(event)
            return
        if self.s.ph == 'bypassing' and self.s.bph == 'input':
            self._handle_bypass_key(event)
            return
        super().keyPressEvent(event)

    def _handle_crack_key(self, event):
        key = event.text()
        if not key or len(key) != 1:
            return
        event.accept()
        expected = self.s.ct[self.s.ci]
        if key == expected:
            if self.s.ci > 0:
                self.crack_w.update_char(self.s.ci - 1, 'ok')
            self.crack_w.update_char(self.s.ci, 'ok')
            self.s.ci += 1
            self.audio.crack_snd()
            self.crack_w.update_progress(self.s.ci, len(self.s.ct))
            if self.s.ci < len(self.s.ct):
                self.crack_w.update_char(self.s.ci, 'cur')
            if self.s.ci >= len(self.s.ct):
                self._crack_ok()
        else:
            self.audio.crack_fail_snd()
            self.s.cwc += 1
            self.crack_w.update_char(self.s.ci, 'bad')
            # Reset after delay
            QTimer.singleShot(150, self._crack_reset)

    def _crack_reset(self):
        for i in range(len(self.s.ct)):
            self.crack_w.update_char(i, 'pen')
        self.s.ci = 0
        self.crack_w.update_char(0, 'cur')
        self.crack_w.update_progress(0, len(self.s.ct))
        self.crack_w.status_lbl.setText("WRONG CHARACTER — Pattern reset. Retrying...")

    def _handle_bypass_key(self, event):
        ai = AKEYS.get(event.key())
        if ai is None:
            return
        event.accept()
        expected = self.s.bsq[self.s.bi]
        if ai == expected:
            self.bypass_w.arrow_labels[self.s.bi].setText(ARROWS[ai])
            self.bypass_w.set_arrow_state(self.s.bi, 'done')
            self.audio.crack_snd()
            self.s.bi += 1
            self.bypass_w.set_status(f"Rule {self.s.bi}/{len(self.s.bsq)} matched")
            if self.s.bi >= len(self.s.bsq):
                self._bypass_ok()
                return
            self.bypass_w.set_arrow_state(self.s.bi, 'expect')
        else:
            self.bypass_w.arrow_labels[self.s.bi].setText(ARROWS[ai])
            self.bypass_w.set_arrow_state(self.s.bi, 'fail')
            self.audio.by_fail_snd()
            self._add_trace(4)
            QTimer.singleShot(250, self._bypass_reset)

    def _bypass_reset(self):
        self.bypass_w.clear_arrows()
        self.s.bi = 0
        if self.s.bsq:
            self.bypass_w.set_arrow_state(0, 'expect')
        self.bypass_w.set_status("RULE MISMATCH — Chain reset. Retry...")

    # ── Mission Complete / Game Over ──────────────────────────────────
    def _mission_complete(self):
        self.s.ph = 'mc'
        self.s.il = True
        self.input_bar.hide()
        m = MISSIONS[self.s.mi]()
        elapsed = time.time() - self.s.mst
        te = self.s.tl
        base = 500 + self.s.mi * 300
        sb = max(0, int(200 - elapsed * 0.5))
        tb = max(0, int(150 - te * 1.5))
        pb = 100 if self.s.cwc == 0 else 0
        total = base + sb + tb + pb
        self.s.sc += total
        self.s.cm.add(self.s.mi)
        self._uh()

        # Achievements
        if len(self.s.cm) == 1: self._unlock('first_blood')
        if te < 15: self._unlock('ghost')
        if elapsed < 90: self._unlock('speed')
        if self.s.hhm: self._unlock('honeypot')
        if len(self.s.cm) == 5: self._unlock('master')

        self.pe()
        self.p('[+] MISSION COMPLETE — OBJECTIVE EXFILTRATED', 'ok')
        self.pe()
        self.p('[*] Target file securely exfiltrated.', 'ok')
        tc2 = C['r'] if te > 65 else C['w'] if te > 35 else C['ok']
        self.ph(f'[*] IDS detection at completion: {tx(f"{int(te)}%",tc2)}')
        self.ph(f'[*] Time elapsed: {tx(f"{int(elapsed)}s","i")}')
        self.pe()
        self.p('Score Breakdown:', 'a')
        self.ph(f'    Base completion:  {tx(str(base),"d")}')
        self.ph(f'    Speed bonus:      {tx(f"+{sb}","ok")}')
        self.ph(f'    Low IDS bonus:    {tx(f"+{tb}","ok")}')
        if pb:
            self.ph(f'    Flawless crack:   {tx(f"+{pb}","w")}')
        self.ph(f'    ──────────────────────')
        self.ph(f'    Total:            {tx(str(total),"w")}')
        self.pe()
        if self.s.mi < 4:
            self.p('  [n] Next Mission    [m] Menu', 'd')
        else:
            self.p('  All 5 missions complete. Outstanding work, operator.', 'ok')
            self.p('  [m] Menu', 'd')
        self.audio.ok_snd()
        self.s.il = False
        self.input_bar.show()
        self.cmd_input.show()
        self.cmd_input.setFocus()
        self._up()

    def _game_over(self):
        self.s.ph = 'go'
        self.s.il = True
        self.input_bar.hide()
        if self.s._bsi:
            self.s._bsi.stop()
        self.bypass_w.hide()
        self.crack_w.hide()
        self._gs()
        def show_go():
            self.pe()
            self.p('[!!!] IDS ALERT: INTRUSION DETECTED — TUNNEL SEVERED', 'r')
            self.pe()
            self.p('  Your source IP has been identified and logged.', 'r')
            self.p('  Incident response team has been dispatched.', 'r')
            self.p('  Connection terminated by remote host.', 'r')
            self.pe()
            self.ph(f'  Final Score: {tx(str(self.s.sc),"w")}')
            self.pe()
            self.p('  [r] Retry Mission    [m] Menu', 'd')
            self.audio.err_snd()
            QTimer.singleShot(250, self.audio.alert_snd)
            self.s.il = False
            self.input_bar.show()
            self.cmd_input.show()
            self.cmd_input.setFocus()
            self._up()
        QTimer.singleShot(250, show_go)

    # ── Command History (up/down arrows in QLineEdit) ─────────────────
    def eventFilter(self, obj, event):
        if obj == self.cmd_input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up and self.s.ch:
                event.accept()
                if self.s.hi > 0:
                    self.s.hi -= 1
                self.cmd_input.setText(self.s.ch[self.s.hi] if self.s.hi < len(self.s.ch) else "")
                return True
            elif event.key() == Qt.Key.Key_Down and self.s.ch:
                event.accept()
                if self.s.hi < len(self.s.ch) - 1:
                    self.s.hi += 1
                    self.cmd_input.setText(self.s.ch[self.s.hi])
                else:
                    self.s.hi = len(self.s.ch)
                    self.cmd_input.setText("")
                return True
        return super().eventFilter(obj, event)

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Dark palette
    pal = app.palette()
    pal.setColor(pal.ColorRole.Window, QColor(4, 8, 12))
    pal.setColor(pal.ColorRole.WindowText, QColor(0, 255, 65))
    pal.setColor(pal.ColorRole.Base, QColor(8, 14, 20))
    pal.setColor(pal.ColorRole.Text, QColor(0, 255, 65))
    pal.setColor(pal.ColorRole.Button, QColor(8, 14, 20))
    pal.setColor(pal.ColorRole.ButtonText, QColor(0, 255, 65))
    pal.setColor(pal.ColorRole.Highlight, QColor(255, 46, 99))
    pal.setColor(pal.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(pal)

    win = MainWindow()
    win.cmd_input.installEventFilter(win)
    win.show()
    win.cmd_input.setFocus()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
