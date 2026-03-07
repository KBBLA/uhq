#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AUTOSHOP - VERSION FINALE ULTIME
- Cache + Pré-indexation
- Prix persistants
- Timeout sur les fonctions longues
- Serveur HTTP pour UptimeRobot / cron-job
- Prêt pour Render
"""

import os
import json
import uuid
import hashlib
import threading
import time
import requests
import re
import random
import string
import sys
import io
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from types import SimpleNamespace
from aiohttp import web
from functools import wraps

# Correction encodage Windows
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')

# === SERVEUR HTTP POUR UPTIMEROBOT / CRON-JOB ===
async def health_check(request):
    return web.Response(text="OK", status=200)

async def start_http_server():
    app_web = web.Application()
    app_web.router.add_get('/health', health_check)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    print("✅ Serveur HTTP démarré sur le port 10000")

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.create_task(start_http_server())

# === IMPORTS TELEGRAM ===
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from fpdf import FPDF

# === CONFIGURATION ===
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8483744061:AAH7n9OtzmpqtphEFZNIqJZTu-4zcj8qAZY")
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', 8295467733))

if os.environ.get('RENDER'):
    DOSSIER = Path("/opt/render/project/src")
else:
    DOSSIER = Path("C:/Users/guidu/Desktop/autoshop2.0")

DOSSIER.mkdir(exist_ok=True)
DOSSIER_DATA = DOSSIER / "data"
DOSSIER_LOGS = DOSSIER / "logs"
DOSSIER_TEMP = DOSSIER / "temp"
for dossier in [DOSSIER_DATA, DOSSIER_LOGS, DOSSIER_TEMP]:
    dossier.mkdir(exist_ok=True)

FICHIER_CLIENTS = DOSSIER_DATA / "clients.json"
FICHIER_UTILISATEURS = DOSSIER_DATA / "utilisateurs.json"
FICHIER_UTILISES = DOSSIER_DATA / "utilises.json"
FICHIER_TRANSACTIONS = DOSSIER_DATA / "transactions.json"
FICHIER_PRIX = DOSSIER_DATA / "prix.json"

PRIX_PAR_DEFAUT = {
    'fiche': 0.05,
    'nm': 0.05,
    'ml': 0.05
}

CRYPTO_CONFIG = {
    'ETH': {'adresse': '0xVotreAdresseEthereum', 'decimals': 18},
    'SOL': {'adresse': 'VotreAdresseSolana', 'decimals': 9},
    'BTC': {'adresse': '1VotreAdresseBitcoin', 'decimals': 8}
}

# === LOGGING ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(DOSSIER_LOGS / 'bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# === MAPPINGS ===
REGIONS = {
    '01': 'ARA', '03': 'ARA', '07': 'ARA', '15': 'ARA', '26': 'ARA', '38': 'ARA',
    '42': 'ARA', '43': 'ARA', '63': 'ARA', '69': 'ARA', '73': 'ARA', '74': 'ARA',
    '21': 'BFC', '25': 'BFC', '39': 'BFC', '58': 'BFC', '70': 'BFC', '71': 'BFC',
    '89': 'BFC', '90': 'BFC', '35': 'BRE', '22': 'BRE', '29': 'BRE', '56': 'BRE',
    '18': 'CVL', '28': 'CVL', '36': 'CVL', '37': 'CVL', '41': 'CVL', '45': 'CVL',
    '2A': 'COR', '2B': 'COR', '08': 'GE', '10': 'GE', '51': 'GE', '52': 'GE',
    '54': 'GE', '55': 'GE', '57': 'GE', '67': 'GE', '68': 'GE', '88': 'GE',
    '02': 'HDF', '59': 'HDF', '60': 'HDF', '62': 'HDF', '80': 'HDF',
    '75': 'IDF', '77': 'IDF', '78': 'IDF', '91': 'IDF', '92': 'IDF',
    '93': 'IDF', '94': 'IDF', '95': 'IDF',
    '14': 'NOR', '27': 'NOR', '50': 'NOR', '61': 'NOR', '76': 'NOR',
    '16': 'NAQ', '17': 'NAQ', '19': 'NAQ', '23': 'NAQ', '24': 'NAQ',
    '33': 'NAQ', '40': 'NAQ', '47': 'NAQ', '64': 'NAQ', '79': 'NAQ',
    '86': 'NAQ', '87': 'NAQ',
    '09': 'OCC', '11': 'OCC', '12': 'OCC', '30': 'OCC', '31': 'OCC',
    '32': 'OCC', '34': 'OCC', '46': 'OCC', '48': 'OCC', '65': 'OCC',
    '66': 'OCC', '81': 'OCC', '82': 'OCC',
    '44': 'PDL', '49': 'PDL', '53': 'PDL', '72': 'PDL', '85': 'PDL',
    '04': 'PACA', '05': 'PACA', '06': 'PACA', '13': 'PACA', '83': 'PACA',
    '84': 'PACA', '971': 'DOM', '972': 'DOM', '973': 'DOM', '974': 'DOM', '976': 'DOM'
}

BANQUES = {
    'BNPA': 'BNP Paribas', 'BNP': 'BNP Paribas',
    'AGRI': 'Crédit Agricole', 'CA': 'Crédit Agricole',
    'SOGE': 'Société Générale', 'SG': 'Société Générale',
    'CMC': 'Crédit Mutuel', 'CM': 'Crédit Mutuel',
    'CIC': 'CIC',
    'LBP': 'La Banque Postale',
    'HSBC': 'HSBC',
    'BOUY': 'Boursorama',
    'AXA': 'AXA Banque',
    'ING': 'ING Direct',
    'FORT': 'Fortuneo',
    'HELL': 'Hello Bank',
    'MONA': 'Monabanq',
    'ORAN': 'Orange Bank',
    'REVO': 'Revolut',
    'N26': 'N26',
    'BP': 'Banque Populaire',
    'CE': 'Caisse d\'Epargne',
    'LCL': 'LCL',
    'NICK': 'Nickel',
}

OPERATEURS = {
    '06': {'06': 'Orange', '07': 'Orange', '60': 'SFR', '61': 'SFR', '62': 'SFR',
           '63': 'SFR', '64': 'SFR', '65': 'SFR', '66': 'Bouygues', '67': 'Bouygues',
           '68': 'Bouygues', '69': 'Free', '70': 'Free', '71': 'Free', '72': 'Free',
           '73': 'Free', '74': 'Free', '75': 'Free', '76': 'Free', '77': 'Free',
           '78': 'Free', '79': 'Free'},
    '07': {'07': 'Orange', '70': 'Orange', '71': 'Orange', '72': 'Orange', '73': 'Orange',
           '74': 'Orange', '75': 'Orange', '76': 'Orange', '77': 'Orange', '78': 'SFR',
           '79': 'SFR', '80': 'SFR', '81': 'Bouygues', '82': 'Bouygues', '83': 'Bouygues',
           '84': 'Free', '85': 'Free', '86': 'Free', '87': 'Free', '88': 'Free', '89': 'Free'}
}

DOMAINES = {
    'gmail.com': 'Gmail',
    'hotmail.fr': 'Hotmail',
    'hotmail.com': 'Hotmail',
    'outlook.fr': 'Outlook',
    'live.fr': 'Live',
    'yahoo.fr': 'Yahoo',
    'orange.fr': 'Orange',
    'sfr.fr': 'SFR',
    'bouygues.fr': 'Bouygues',
    'free.fr': 'Free',
    'laposte.net': 'La Poste',
    'icloud.com': 'iCloud',
}

# === DECORATEUR TIMEOUT ===
def timeout(seconds):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Fonction {func.__name__} timeout après {seconds}s")
                return None
        return wrapper
    return decorator

# === CLASSE PRINCIPALE ===
class AutoShop:
    def __init__(self):
        self.clients = {}
        self.valides = {}
        self.utilises = set()
        self.users = {}
        self.transactions = []
        self.scanned = False
        self.par_banque = defaultdict(list)
        self.par_region = defaultdict(list)
        self.par_operateur = defaultdict(list)
        self.par_domaine = defaultdict(list)
        self.prix = self.charger_prix()
        self.charger()

    def charger_prix(self):
        if FICHIER_PRIX.exists():
            try:
                with open(FICHIER_PRIX, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return PRIX_PAR_DEFAUT.copy()
        return PRIX_PAR_DEFAUT.copy()

    def sauver_prix(self):
        with open(FICHIER_PRIX, 'w', encoding='utf-8') as f:
            json.dump(self.prix, f, indent=2, ensure_ascii=False)

    def charger(self):
        try:
            if FICHIER_CLIENTS.exists():
                with open(FICHIER_CLIENTS, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.clients = data.get('clients', {})
                    self.valides = data.get('valides', {})
            if FICHIER_UTILISATEURS.exists():
                with open(FICHIER_UTILISATEURS, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            if FICHIER_UTILISES.exists():
                with open(FICHIER_UTILISES, 'r', encoding='utf-8') as f:
                    self.utilises = set(json.load(f))
            if FICHIER_TRANSACTIONS.exists():
                with open(FICHIER_TRANSACTIONS, 'r', encoding='utf-8') as f:
                    self.transactions = json.load(f)
            logger.info(f"Chargé: {len(self.valides)} valides, {len(self.utilises)} utilisés")
        except Exception as e:
            logger.error(f"Erreur chargement: {e}")

    def sauver(self):
        with open(FICHIER_CLIENTS, 'w', encoding='utf-8') as f:
            json.dump({'clients': self.clients, 'valides': self.valides}, f, indent=2, ensure_ascii=False)
        with open(FICHIER_UTILISATEURS, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)
        with open(FICHIER_UTILISES, 'w', encoding='utf-8') as f:
            json.dump(list(self.utilises), f, indent=2, ensure_ascii=False)
        with open(FICHIER_TRANSACTIONS, 'w', encoding='utf-8') as f:
            json.dump(self.transactions, f, indent=2, ensure_ascii=False)
        logger.info("Données sauvegardées")

    def get_region(self, cp):
        if not cp:
            return 'INCONNU'
        cp = re.sub(r'\D', '', cp)
        if len(cp) < 2:
            return 'INCONNU'
        dep = cp[:2]
        if dep == '97' and len(cp) >= 3:
            dep = cp[:3]
        return REGIONS.get(dep, 'AUTRE')

    def get_banque(self, bic):
        if not bic:
            return 'INCONNU'
        bic = bic.upper()
        for code, nom in BANQUES.items():
            if code in bic:
                return nom
        if bic.startswith('FR'):
            return 'AUTRE BANQUE FR'
        return 'AUTRE'

    def get_operateur(self, tel):
        if not tel:
            return 'INCONNU'
        tel = re.sub(r'\D', '', tel)
        if len(tel) < 4:
            return 'INCONNU'
        prefixe = tel[:2]
        if prefixe not in OPERATEURS:
            return 'AUTRE'
        return OPERATEURS[prefixe].get(tel[2:4], 'AUTRE')

    def get_domaine(self, email):
        if not email or '@' not in email:
            return 'INCONNU'
        domaine = email.split('@')[1].lower()
        for d, nom in DOMAINES.items():
            if d in domaine:
                return nom
        return 'AUTRE'

    def parse_ligne(self, ligne):
        try:
            ligne = ligne.strip()
            if not ligne or ligne.startswith('#'):
                return None
            for sep in ['|', ';', ',', '\t']:
                parts = ligne.split(sep)
                if len(parts) >= 8:
                    break
            else:
                return None
            parts = [p.strip() for p in parts]
            c = {}
            idx = 0
            c['nom'] = parts[idx] if idx < len(parts) else ''
            idx += 1
            c['pays'] = parts[idx] if idx < len(parts) else ''
            idx += 1
            c['date'] = parts[idx] if idx < len(parts) else ''
            idx += 1
            c['adresse'] = parts[idx] if idx < len(parts) else ''
            idx += 1
            c['cp'] = parts[idx] if idx < len(parts) else ''
            idx += 1
            c['ville'] = parts[idx] if idx < len(parts) else ''
            idx += 1
            c['tel'] = parts[idx] if idx < len(parts) else ''
            idx += 1
            c['email'] = parts[idx] if idx < len(parts) else ''
            idx += 1
            c['iban'] = parts[idx] if idx < len(parts) else ''
            idx += 1
            c['bic'] = parts[idx] if idx < len(parts) else ''
            c['region'] = self.get_region(c['cp'])
            c['banque'] = self.get_banque(c['bic'])
            c['operateur'] = self.get_operateur(c['tel'])
            c['domaine'] = self.get_domaine(c['email'])
            c['valide'] = all([c['nom'], c['date'], c['adresse'], c['cp'], c['ville'], c['tel'], c['email']])
            uid = f"{c['nom']}|{c['date']}|{c.get('iban', '')}"
            c['id'] = hashlib.md5(uid.encode()).hexdigest()[:16]
            return c
        except Exception as e:
            logger.error(f"Erreur parse: {e}")
            return None

    def scanner(self, force=False):
        if self.scanned and not force:
            logger.info("📦 Utilisation du cache - Scan déjà effectué")
            return {'fichiers': len(self.clients), 'lignes': 0, 'valides': len(self.valides)}
        logger.info("="*50)
        logger.info("SCAN DU DOSSIER")
        logger.info("="*50)
        self.clients = {}
        self.valides = {}
        fichiers = list(DOSSIER.glob("*.txt")) + list(DOSSIER.glob("*.csv"))
        logger.info(f"Dossier: {DOSSIER}")
        logger.info(f"Fichiers trouvés: {len(fichiers)}")
        if not fichiers:
            logger.warning("⚠️ AUCUN FICHIER TROUVÉ!")
            self.sauver()
            return {'fichiers': 0, 'lignes': 0, 'valides': 0}
        total_lignes = 0
        valides = 0
        for fichier in fichiers:
            try:
                logger.info(f"Lecture de {fichier.name}...")
                with open(fichier, 'r', encoding='utf-8', errors='ignore') as f:
                    lignes = f.readlines()
                logger.info(f"  - {len(lignes)} lignes")
                for i, ligne in enumerate(lignes):
                    total_lignes += 1
                    client = self.parse_ligne(ligne)
                    if client:
                        self.clients[client['id']] = client
                        if client.get('valide'):
                            self.valides[client['id']] = client
                            valides += 1
                    if i > 0 and i % 50000 == 0:
                        logger.info(f"    ... {i} lignes traitées")
                logger.info(f"  ✅ {valides} clients valides dans ce fichier")
            except Exception as e:
                logger.error(f"Erreur lecture {fichier}: {e}")
        logger.info("🔄 Pré-indexation des données...")
        self.par_banque.clear()
        self.par_region.clear()
        self.par_operateur.clear()
        self.par_domaine.clear()
        for cid, client in self.valides.items():
            self.par_banque[client['banque']].append(client)
            self.par_region[client['region']].append(client)
            self.par_operateur[client['operateur']].append(client)
            self.par_domaine[client['domaine']].append(client)
        logger.info("✅ Pré-indexation terminée")
        logger.info("="*50)
        logger.info(f"SCAN TERMINÉ")
        logger.info(f"Total lignes: {total_lignes}")
        logger.info(f"Total valides: {valides}")
        logger.info("="*50)
        self.scanned = True
        self.sauver()
        return {'fichiers': len(fichiers), 'lignes': total_lignes, 'valides': valides}

    def stats(self):
        stats = {
            'dispos': len(self.valides) - len(self.utilises),
            'banques': defaultdict(int),
            'regions': defaultdict(int),
            'operateurs': defaultdict(int),
            'domaines': defaultdict(int)
        }
        for cid, c in self.valides.items():
            if cid in self.utilises:
                continue
            stats['banques'][c['banque']] += 1
            stats['regions'][c['region']] += 1
            stats['operateurs'][c['operateur']] += 1
            stats['domaines'][c['domaine']] += 1
        return stats

shop = AutoShop()

# === PRIX CRYPTO ===
class PrixCrypto:
    def __init__(self):
        self.prix = {'BTC': 50000, 'ETH': 2500, 'SOL': 150}
        self.last = None
    def maj(self):
        try:
            btc = requests.get('https://blockchain.info/ticker', timeout=5)
            if btc.status_code == 200:
                self.prix['BTC'] = btc.json()['EUR']['last']
            coins = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=ethereum,solana&vs_currencies=eur', timeout=5)
            if coins.status_code == 200:
                data = coins.json()
                self.prix['ETH'] = data['ethereum']['eur']
                self.prix['SOL'] = data['solana']['eur']
            self.last = datetime.now()
            logger.info(f"Prix mis à jour")
        except Exception as e:
            logger.error(f"Erreur prix: {e}")
    def get(self, crypto):
        if not self.last or datetime.now() - self.last > timedelta(minutes=5):
            self.maj()
        return self.prix.get(crypto, 0)

prix = PrixCrypto()

# === VERIFICATION AUTO ===
class VerifAuto:
    def __init__(self):
        self.attente = {}
        self.app = None
    def set_app(self, app):
        self.app = app
    def demarrer(self):
        t = threading.Thread(target=self._boucle, daemon=True)
        t.start()
        logger.info("Vérification auto démarrée")
    def _boucle(self):
        while True:
            try:
                self._verifier()
                time.sleep(30)
            except:
                pass
    def _verifier_sol(self, adresse, montant_attendu):
        try:
            url = f"https://api.solscan.io/account/transactions?account={adresse}&limit=5"
            headers = {'Accept': 'application/json'}
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                for tx in data.get('data', [])[:5]:
                    if tx.get('status') == 'Success':
                        for instr in tx.get('parsedInstruction', []):
                            if instr.get('type') == 'transfer':
                                params = instr.get('params', {})
                                if params.get('destination') == adresse:
                                    recu = params.get('lamports', 0) / 1e9
                                    if abs(recu - montant_attendu) < 0.01:
                                        return True
        except:
            pass
        return False
    def _verifier(self):
        suppr = []
        for cmd, data in list(self.attente.items()):
            try:
                crypto = data['crypto']
                adr = data['adresse']
                montant = data['montant_crypto']
                if crypto == 'BTC':
                    url = f"https://blockchain.info/rawaddr/{adr}"
                    r = requests.get(url, timeout=5)
                    if r.status_code == 200:
                        btc_data = r.json()
                        for tx in btc_data.get('txs', [])[:5]:
                            recu = sum(o['value'] for o in tx['out'] if o.get('addr') == adr) / 1e8
                            if recu > 0 and abs(recu - montant) < 0.0005:
                                self._confirmer(cmd, data)
                                suppr.append(cmd)
                                break
                elif crypto == 'ETH':
                    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={adr}&sort=desc"
                    r = requests.get(url, timeout=5)
                    if r.status_code == 200:
                        eth_data = r.json()
                        if eth_data.get('status') == '1':
                            for tx in eth_data.get('result', [])[:5]:
                                if tx.get('to', '').lower() == adr.lower():
                                    recu = int(tx.get('value', 0)) / 1e18
                                    if abs(recu - montant) < 0.01:
                                        self._confirmer(cmd, data)
                                        suppr.append(cmd)
                                        break
                elif crypto == 'SOL':
                    if self._verifier_sol(adr, montant):
                        self._confirmer(cmd, data)
                        suppr.append(cmd)
            except Exception as e:
                logger.error(f"Erreur vérif {cmd}: {e}")
        for cmd in suppr:
            self.attente.pop(cmd, None)
    def _confirmer(self, cmd, data):
        try:
            logger.info(f"🎉 Paiement confirmé {cmd}")
            if self.app:
                import asyncio
                asyncio.create_task(self._livrer(cmd, data))
        except Exception as e:
            logger.error(f"Erreur confirmation: {e}")
    async def _livrer(self, cmd, data):
        try:
            uid = data['user_id']
            panier = data['panier']
            montant = data['montant_eur']
            if data.get('type') == 'recharge':
                user_str = str(uid)
                if user_str in shop.users:
                    shop.users[user_str]['solde'] += montant
                    if 'recharges' not in shop.users[user_str]:
                        shop.users[user_str]['recharges'] = []
                    shop.users[user_str]['recharges'].append({'date': datetime.now().isoformat(), 'montant': montant, 'cmd': cmd})
                    shop.sauver()
                    await self.app.bot.send_message(uid, f"✅ Recharge confirmée !\n💰 +{montant:.2f}€\n💶 Nouveau solde: {shop.users[user_str]['solde']:.2f}€")
                return
            await self.app.bot.send_message(uid, "✅ Paiement confirmé !\n📦 Préparation...")
            for art in panier:
                for cid in art['clients']:
                    if cid in shop.valides:
                        shop.utilises.add(cid)
            shop.sauver()
            for i, art in enumerate(panier, 1):
                clients = [shop.valides[cid] for cid in art['clients'] if cid in shop.valides]
                if not clients:
                    continue
                if art['type'] == 'fiche':
                    pdf = self._pdf_fiche(clients, f"Lot{art['lot']}_{art.get('banque','')}_{art.get('region','')}_{art['quantite']}")
                elif art['type'] == 'nm':
                    pdf = self._pdf_nm(clients, f"Lot{art['lot']}_{art['operateur']}_{art['quantite']}")
                else:
                    pdf = self._pdf_ml(clients, f"Lot{art['lot']}_{art['domaine']}_{art['quantite']}")
                with open(pdf, 'rb') as f:
                    await self.app.bot.send_document(chat_id=uid, document=f, filename=f"{art['type']}_{art['lot']}.pdf", caption=f"📄 Lot {i}/{len(panier)}")
                os.unlink(pdf)
            await self.app.bot.send_message(uid, f"✅ Commande #{cmd} terminée ! Merci.")
        except Exception as e:
            logger.error(f"Erreur livraison: {e}")
    def _pdf_fiche(self, clients, info):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f"FICHE - {info}", 0, 1, 'C')
        pdf.ln(10)
        pdf.set_font('Arial', '', 10)
        for i, c in enumerate(clients, 1):
            pdf.cell(0, 8, f"{i}. {c['nom']}", 0, 1, 'L')
            pdf.set_font('Arial', '', 8)
            pdf.cell(0, 5, f"   Né: {c['date']}", 0, 1, 'L')
            pdf.cell(0, 5, f"   {c['adresse']}, {c['cp']} {c['ville']}", 0, 1, 'L')
            pdf.cell(0, 5, f"   Tél: {c['tel']} ({c['operateur']})", 0, 1, 'L')
            pdf.cell(0, 5, f"   Email: {c['email']}", 0, 1, 'L')
            if c.get('iban'):
                pdf.cell(0, 5, f"   IBAN: {c['iban']}", 0, 1, 'L')
            pdf.ln(3)
        filename = DOSSIER_TEMP / f"fiche_{info}_{uuid.uuid4().hex[:8]}.pdf"
        pdf.output(str(filename))
        return str(filename)
    def _pdf_nm(self, clients, info):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f"NM - {info}", 0, 1, 'C')
        pdf.ln(10)
        pdf.set_font('Arial', '', 10)
        for c in clients:
            pdf.cell(0, 5, c['tel'], 0, 1, 'L')
        filename = DOSSIER_TEMP / f"nm_{info}_{uuid.uuid4().hex[:8]}.pdf"
        pdf.output(str(filename))
        return str(filename)
    def _pdf_ml(self, clients, info):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f"ML - {info}", 0, 1, 'C')
        pdf.ln(10)
        pdf.set_font('Arial', '', 10)
        for c in clients:
            pdf.cell(0, 5, c['email'], 0, 1, 'L')
        filename = DOSSIER_TEMP / f"ml_{info}_{uuid.uuid4().hex[:8]}.pdf"
        pdf.output(str(filename))
        return str(filename)

verif = VerifAuto()

# === SECURITE ===
def is_admin(update):
    return update.effective_user.id == ADMIN_USER_ID

# === ACCUEIL ===
async def accueil(update_or_query, context):
    if hasattr(update_or_query, 'effective_user'):
        user = update_or_query.effective_user
        uid = str(user.id)
    else:
        user = update_or_query.from_user
        uid = str(user.id)
    stats = shop.stats()
    solde = shop.users[uid].get('solde', 0) if uid in shop.users else 0
    texte = f"""
👋 BIENVENUE {user.first_name} !

📊 STOCKS: {stats['dispos']:,} fiches

💰 SOLDE: {solde}€
"""
    keyboard = [
        [InlineKeyboardButton("📄 FICHE", callback_data='menu_fiche'),
         InlineKeyboardButton("📱 NM", callback_data='menu_nm'),
         InlineKeyboardButton("📧 ML", callback_data='menu_ml')],
        [InlineKeyboardButton("🛒 PANIER", callback_data='panier'),
         InlineKeyboardButton("💰 PORTEFEUILLE", callback_data='portefeuille')]
    ]
    if hasattr(update_or_query, 'message'):
        await update_or_query.message.reply_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update_or_query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))

# === START ===
async def start(update: Update, context):
    user = update.effective_user
    uid = str(user.id)
    if uid not in shop.users:
        shop.users[uid] = {'nom': user.first_name, 'user': user.username, 'date': datetime.now().isoformat(), 'solde': 0, 'achats': [], 'recharges': []}
        shop.sauver()
    await accueil(update, context)

# === ADMIN ===
async def admin(update: Update, context):
    if not is_admin(update):
        await update.message.reply_text("⛔ Accès refusé")
        return
    stats = shop.stats()
    texte = f"""
⚙️ ADMIN PANEL

📊 STATS:
• Valides: {len(shop.valides)}
• Utilisés: {len(shop.utilises)}
• Dispos: {stats['dispos']}
• Users: {len(shop.users)}

💰 PRIX:
• FICHE: {shop.prix['fiche']*1000:.0f}€/1000
• NM: {shop.prix['nm']*1000:.0f}€/1000
• ML: {shop.prix['ml']*1000:.0f}€/1000
"""
    keyboard = [
        [InlineKeyboardButton("📤 SCANNER", callback_data='admin_scan'),
         InlineKeyboardButton("🔄 REINDEX", callback_data='admin_reindex')],
        [InlineKeyboardButton("📊 STATS", callback_data='admin_stats'),
         InlineKeyboardButton("💰 PRIX", callback_data='admin_prix')],
        [InlineKeyboardButton("👥 USERS", callback_data='admin_users'),
         InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')]
    ]
    await update.message.reply_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))

# === HANDLER PRINCIPAL ===
async def button(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    # RETOURS
    if data == 'retour_accueil':
        await accueil(query, context)
        return
    if data == 'retour_fiche':
        await menu_fiche(query, context)
        return
    if data == 'retour_nm':
        await menu_nm(query, context)
        return
    if data == 'retour_ml':
        await menu_ml(query, context)
        return

    # MENUS
    if data == 'menu_fiche':
        await menu_fiche(query, context)
        return
    if data == 'menu_nm':
        await menu_nm(query, context)
        return
    if data == 'menu_ml':
        await menu_ml(query, context)
        return

    # FICHE - OPTIONS
    if data == 'fiche_banque':
        await fiche_banques(query, context)
        return
    if data == 'fiche_region':
        await fiche_regions(query, context)
        return
    if data == 'fiche_mixte':
        await fiche_mixte_banque(query, context)
        return

    # FICHE - BANQUE
    if data.startswith('banque_fiche_'):
        banque = data.replace('banque_fiche_', '')
        context.user_data['type'] = 'fiche'
        context.user_data['banque'] = banque
        context.user_data['mode'] = 'banque'
        context.user_data['quantite'] = 1000
        await banque_fiche(query, context, banque)
        return
    if data.startswith('region_dans_banque_'):
        parts = data.replace('region_dans_banque_', '').split('|')
        banque = parts[0]; region = parts[1]
        context.user_data['type'] = 'fiche'
        context.user_data['banque'] = banque
        context.user_data['region'] = region
        context.user_data['mode'] = 'mixte'
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)
        return

    # FICHE - REGION
    if data.startswith('region_fiche_'):
        region = data.replace('region_fiche_', '')
        context.user_data['type'] = 'fiche'
        context.user_data['region'] = region
        context.user_data['mode'] = 'region'
        context.user_data['quantite'] = 1000
        await region_fiche(query, context, region)
        return
    if data.startswith('banque_dans_region_'):
        parts = data.replace('banque_dans_region_', '').split('|')
        region = parts[0]; banque = parts[1]
        context.user_data['type'] = 'fiche'
        context.user_data['region'] = region
        context.user_data['banque'] = banque
        context.user_data['mode'] = 'mixte'
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)
        return

    # FICHE - MIXTE
    if data.startswith('mixte_banque_'):
        banque = data.replace('mixte_banque_', '')
        context.user_data['mixte_banque'] = banque
        await fiche_mixte_region(query, context, banque)
        return
    if data.startswith('mixte_valider_'):
        parts = data.replace('mixte_valider_', '').split('|')
        banque = parts[0]; region = parts[1]
        context.user_data['type'] = 'fiche'
        context.user_data['banque'] = banque
        context.user_data['region'] = region
        context.user_data['mode'] = 'mixte'
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)
        return

    # NM
    if data.startswith('operateur_'):
        op = data.replace('operateur_', '')
        context.user_data['type'] = 'nm'
        context.user_data['operateur'] = op
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)
        return

    # ML
    if data.startswith('domaine_'):
        dom = data.replace('domaine_', '')
        context.user_data['type'] = 'ml'
        context.user_data['domaine'] = dom
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)
        return

    # QUANTITE
    if data.startswith('quantite_'):
        parts = data.split('_')
        action = parts[1]
        if 'quantite' not in context.user_data:
            context.user_data['quantite'] = 1000
        if action == 'moins' and context.user_data['quantite'] > 1000:
            context.user_data['quantite'] -= 1000
        elif action == 'plus':
            context.user_data['quantite'] += 1000
        elif action == 'valider':
            await ajouter_au_panier(query, context)
            return
        await choix_quantite(query, context)
        return

    # PANIER
    if data == 'panier':
        panier = context.user_data.get('panier', [])
        if not panier:
            await query.edit_message_text("🛒 Panier vide")
            return
        total = sum(a['prix'] for a in panier)
        texte = "🛒 PANIER\n\n"
        for i, a in enumerate(panier, 1):
            if a['type'] == 'fiche':
                if 'banque' in a and 'region' in a:
                    texte += f"{i}. 📄 FICHE - {a['banque']} {a['region']} - {a['quantite']} clients - {a['prix']:.2f}€\n"
                elif 'banque' in a:
                    texte += f"{i}. 📄 FICHE - {a['banque']} - {a['quantite']} clients - {a['prix']:.2f}€\n"
                else:
                    texte += f"{i}. 📄 FICHE - {a['region']} - {a['quantite']} clients - {a['prix']:.2f}€\n"
            elif a['type'] == 'nm':
                texte += f"{i}. 📱 NM - {a['operateur']} - {a['quantite']} clients - {a['prix']:.2f}€\n"
            else:
                texte += f"{i}. 📧 ML - {a['domaine']} - {a['quantite']} clients - {a['prix']:.2f}€\n"
        texte += f"\n💰 TOTAL: {total:.2f}€"
        keyboard = [
            [InlineKeyboardButton("✅ VALIDER", callback_data='valider'), InlineKeyboardButton("🗑️ VIDER", callback_data='vider')],
            [InlineKeyboardButton("🔙 CONTINUER", callback_data='retour_accueil')]
        ]
        await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if data == 'vider':
        context.user_data['panier'] = []
        await query.edit_message_text("🗑️ Panier vidé")
        return
    if data == 'valider':
        panier = context.user_data.get('panier', [])
        if not panier:
            await query.edit_message_text("❌ Panier vide")
            return
        total = sum(a['prix'] for a in panier)
        context.user_data['total_commande'] = total
        context.user_data['panier_commande'] = panier.copy()
        context.user_data['commande_id'] = uuid.uuid4().hex[:8].upper()
        keyboard = [
            [InlineKeyboardButton("🟣 ETH", callback_data='payer_eth'), InlineKeyboardButton("🔵 SOL", callback_data='payer_sol')],
            [InlineKeyboardButton("🟡 BTC", callback_data='payer_btc'), InlineKeyboardButton("🔙 RETOUR", callback_data='panier')]
        ]
        await query.edit_message_text(f"💰 TOTAL: {total:.2f}€\n\nChoisissez votre crypto :", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # PAIEMENT
    if data in ['payer_eth', 'payer_sol', 'payer_btc']:
        crypto = data.replace('payer_', '').upper()
        total = context.user_data.get('total_commande', 0)
        cmd_id = context.user_data.get('commande_id', '')
        p = prix.get(crypto)
        montant_crypto = total / p if p > 0 else 0
        adresse = CRYPTO_CONFIG[crypto]['adresse']
        texte = f"""
💰 PAIEMENT {crypto}

Commande #{cmd_id}
💶 {total:.2f}€ = {montant_crypto:.6f} {crypto}

📤 Envoyez EXACTEMENT ce montant à :
`{adresse}`

⏳ Vérification automatique dans quelques minutes...
"""
        verif.attente[cmd_id] = {
            'crypto': crypto,
            'montant_eur': total,
            'montant_crypto': montant_crypto,
            'user_id': query.from_user.id,
            'adresse': adresse,
            'panier': context.user_data.get('panier_commande', [])
        }
        context.user_data['panier'] = []
        await query.edit_message_text(texte)
        return

    # RECHARGE
    if data == 'recharger':
        keyboard = [
            [InlineKeyboardButton("🟣 50€ ETH", callback_data='recharge_50_eth'), InlineKeyboardButton("🔵 50€ SOL", callback_data='recharge_50_sol')],
            [InlineKeyboardButton("🟡 50€ BTC", callback_data='recharge_50_btc'), InlineKeyboardButton("🔙 RETOUR", callback_data='portefeuille')]
        ]
        await query.edit_message_text("💰 RECHARGER PORTEFEUILLE\n\nChoisissez 50€ de recharge :", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if data.startswith('recharge_50_'):
        crypto = data.replace('recharge_50_', '').upper()
        cmd_id = f"RECH_{uuid.uuid4().hex[:8].upper()}"
        p = prix.get(crypto)
        montant_crypto = 50 / p if p > 0 else 0
        adresse = CRYPTO_CONFIG[crypto]['adresse']
        texte = f"""
💰 RECHARGE 50€

Commande #{cmd_id}
💶 50€ = {montant_crypto:.6f} {crypto}

📤 Envoyez à :
`{adresse}`

⏳ Vérification automatique...
"""
        verif.attente[cmd_id] = {'crypto': crypto, 'montant_eur': 50, 'montant_crypto': montant_crypto, 'user_id': query.from_user.id, 'adresse': adresse, 'panier': [], 'type': 'recharge'}
        await query.edit_message_text(texte)
        return

    # PORTEFEUILLE
    if data == 'portefeuille':
        uid = str(query.from_user.id)
        solde = shop.users[uid].get('solde', 0) if uid in shop.users else 0
        texte = f"💰 PORTEFEUILLE\n\n💶 Solde: {solde:.2f}€"
        keyboard = [[InlineKeyboardButton("📥 RECHARGER 50€", callback_data='recharger')], [InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')]]
        await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ADMIN
    if not is_admin(update):
        return
    if data == 'admin_scan':
        fichiers = list(DOSSIER.glob("*.txt")) + list(DOSSIER.glob("*.csv"))
        texte = f"📋 FICHIERS: {len(fichiers)}\n\n"
        for f in fichiers[:10]:
            texte += f"• {f.name}\n"
        keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')]]
        await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if data == 'admin_reindex':
        await query.edit_message_text("🔄 Reindexation...")
        r = shop.scanner(force=True)
        await query.edit_message_text(f"✅ {r['valides']} clients valides")
        return
    if data == 'admin_stats':
        stats = shop.stats()
        texte = f"""
📊 STATS DÉTAILLÉES

👥 CLIENTS
• Total: {len(shop.clients)}
• Valides: {len(shop.valides)}
• Utilisés: {len(shop.utilises)}
• Dispos: {stats['dispos']}

🏦 TOP BANQUES
"""
        for b, c in list(stats['banques'].items())[:10]:
            texte += f"• {b}: {c}\n"
        texte += "\n🌍 TOP RÉGIONS\n"
        for r, c in list(stats['regions'].items())[:10]:
            texte += f"• {r}: {c}\n"
        texte += "\n📱 TOP OPÉRATEURS\n"
        for o, c in list(stats['operateurs'].items())[:10]:
            texte += f"• {o}: {c}\n"
        texte += "\n📧 TOP DOMAINES\n"
        for d, c in list(stats['domaines'].items())[:10]:
            texte += f"• {d}: {c}\n"
        keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')]]
        await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if data == 'admin_prix':
        keyboard = [
            [InlineKeyboardButton(f"📄 FICHE: {shop.prix['fiche']*1000:.0f}€/1000", callback_data='modif_prix_fiche')],
            [InlineKeyboardButton(f"📱 NM: {shop.prix['nm']*1000:.0f}€/1000", callback_data='modif_prix_nm')],
            [InlineKeyboardButton(f"📧 ML: {shop.prix['ml']*1000:.0f}€/1000", callback_data='modif_prix_ml')],
            [InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')]
        ]
        await query.edit_message_text("💰 MODIFIER LES PRIX\n\nCliquez sur un service :", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if data.startswith('modif_prix_'):
        service = data.replace('modif_prix_', '')
        context.user_data['prix_a_modifier'] = service
        await query.edit_message_text(f"💰 Entrez le nouveau prix pour {service.upper()} (pour 1000) :")
        return
    if data == 'admin_users':
        texte = "👥 UTILISATEURS\n\n"
        for uid, u in list(shop.users.items())[:10]:
            nom = u.get('nom', 'Inconnu')
            solde = u.get('solde', 0)
            achats = len(u.get('achats', []))
            texte += f"• {nom}: {solde}€ - {achats} achats\n"
        keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')]]
        await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))
        return

# === FONCTIONS MENU ===
async def menu_fiche(query, context):
    stats = shop.stats()
    keyboard = [
        [InlineKeyboardButton("🏦 PAR BANQUE", callback_data='fiche_banque'),
         InlineKeyboardButton("🌍 PAR RÉGION", callback_data='fiche_region')],
        [InlineKeyboardButton("🎯 RECHERCHE MIXTE", callback_data='fiche_mixte')],
        [InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')]
    ]
    await query.edit_message_text(f"📄 SERVICE FICHE\n\nDisponibles: {stats['dispos']} fiches\n\nChoisissez votre méthode :", reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_nm(query, context):
    stats = shop.stats()
    ops = [(o, c) for o, c in stats['operateurs'].items() if c >= 1000]
    ops = sorted(ops, key=lambda x: x[1], reverse=True)
    keyboard = []
    for o, c in ops[:10]:
        keyboard.append([InlineKeyboardButton(f"📱 {o} ({c})", callback_data=f'operateur_{o}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')])
    await query.edit_message_text(f"📱 SERVICE NM\n\nDisponibles: {stats['dispos']} numéros\nChoisissez un opérateur :", reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_ml(query, context):
    stats = shop.stats()
    doms = [(d, c) for d, c in stats['domaines'].items() if c >= 1000]
    doms = sorted(doms, key=lambda x: x[1], reverse=True)
    keyboard = []
    for d, c in doms[:10]:
        keyboard.append([InlineKeyboardButton(f"📧 {d} ({c})", callback_data=f'domaine_{d}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')])
    await query.edit_message_text(f"📧 SERVICE ML\n\nDisponibles: {stats['dispos']} emails\nChoisissez un domaine :", reply_markup=InlineKeyboardMarkup(keyboard))

async def fiche_banques(query, context):
    stats = shop.stats()
    banques = [(b, c) for b, c in stats['banques'].items() if c >= 1000]
    banques = sorted(banques, key=lambda x: x[1], reverse=True)
    keyboard = []
    for b, c in banques[:10]:
        keyboard.append([InlineKeyboardButton(f"🏦 {b} ({c})", callback_data=f'banque_fiche_{b}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='menu_fiche')])
    await query.edit_message_text("🏦 SÉLECTION PAR BANQUE\n\nChoisissez une banque :", reply_markup=InlineKeyboardMarkup(keyboard))

async def fiche_regions(query, context):
    stats = shop.stats()
    regions = [(r, c) for r, c in stats['regions'].items() if c >= 1000]
    regions = sorted(regions, key=lambda x: x[1], reverse=True)
    keyboard = []
    for r, c in regions[:10]:
        keyboard.append([InlineKeyboardButton(f"🌍 {r} ({c})", callback_data=f'region_fiche_{r}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='menu_fiche')])
    await query.edit_message_text("🌍 SÉLECTION PAR RÉGION\n\nChoisissez une région :", reply_markup=InlineKeyboardMarkup(keyboard))

async def fiche_mixte_banque(query, context):
    stats = shop.stats()
    banques = [(b, c) for b, c in stats['banques'].items() if c >= 1000]
    banques = sorted(banques, key=lambda x: x[1], reverse=True)
    keyboard = []
    for b, c in banques[:10]:
        keyboard.append([InlineKeyboardButton(f"🏦 {b} ({c})", callback_data=f'mixte_banque_{b}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='menu_fiche')])
    await query.edit_message_text("🎯 RECHERCHE MIXTE - Étape 1/2\n\nChoisissez une banque :", reply_markup=InlineKeyboardMarkup(keyboard))

async def fiche_mixte_region(query, context, banque):
    clients = shop.par_banque.get(banque, [])
    regions = defaultdict(int)
    for c in clients:
        regions[c['region']] += 1
    regions_triees = sorted(regions.items(), key=lambda x: x[1], reverse=True)
    keyboard = []
    for r, count in regions_triees[:8]:
        keyboard.append([InlineKeyboardButton(f"🌍 {r} ({count})", callback_data=f'mixte_valider_{banque}|{r}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='fiche_mixte')])
    await query.edit_message_text(f"🎯 RECHERCHE MIXTE - Étape 2/2\n\nBanque: {banque}\nChoisissez une région :", reply_markup=InlineKeyboardMarkup(keyboard))

@timeout(10)
async def banque_fiche(query, context, banque):
    clients = shop.par_banque.get(banque, [])
    regions = defaultdict(int)
    for c in clients:
        regions[c['region']] += 1
    regions_triees = sorted(regions.items(), key=lambda x: x[1], reverse=True)
    if len(regions_triees) > 1:
        keyboard = []
        for r, count in regions_triees[:8]:
            keyboard.append([InlineKeyboardButton(f"🌍 {r} ({count})", callback_data=f'region_dans_banque_{banque}|{r}')])
        keyboard.append([InlineKeyboardButton("🌍 TOUTES LES RÉGIONS", callback_data=f'region_dans_banque_{banque}|TOUTES')])
        keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='fiche_banque')])
        await query.edit_message_text(f"🏦 {banque}\n\nChoisissez une région :", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        region = regions_triees[0][0] if regions_triees else 'TOUTES'
        context.user_data['type'] = 'fiche'
        context.user_data['banque'] = banque
        context.user_data['region'] = region
        context.user_data['mode'] = 'banque'
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)

@timeout(10)
async def region_fiche(query, context, region):
    clients = shop.par_region.get(region, [])
    banques = defaultdict(int)
    for c in clients:
        banques[c['banque']] += 1
    banques_triees = sorted(banques.items(), key=lambda x: x[1], reverse=True)
    if len(banques_triees) > 1:
        keyboard = []
        for b, count in banques_triees[:8]:
            keyboard.append([InlineKeyboardButton(f"🏦 {b} ({count})", callback_data=f'banque_dans_region_{region}|{b}')])
        keyboard.append([InlineKeyboardButton("🏦 TOUTES LES BANQUES", callback_data=f'banque_dans_region_{region}|TOUTES')])
        keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='fiche_region')])
        await query.edit_message_text(f"🌍 {region}\n\nChoisissez une banque :", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        banque = banques_triees[0][0] if banques_triees else 'TOUTES'
        context.user_data['type'] = 'fiche'
        context.user_data['region'] = region
        context.user_data['banque'] = banque
        context.user_data['mode'] = 'region'
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)

async def choix_quantite(query, context):
    quantite = context.user_data.get('quantite', 1000)
    type_ = context.user_data.get('type', 'fiche')
    if type_ == 'fiche':
        mode = context.user_data.get('mode', 'region')
        banque = context.user_data.get('banque', '')
        region = context.user_data.get('region', '')
        if banque and region and region != 'TOUTES':
            clients = [c for c in shop.par_banque.get(banque, []) if c['region'] == region]
            nom = f"FICHE - {banque} {region}"
            max_dispo = len(clients)
            retour_callback = f'retour_banque_fiche_{banque}' if mode == 'banque' else f'retour_region_fiche_{region}'
        elif banque and region == 'TOUTES':
            clients = shop.par_banque.get(banque, [])
            nom = f"FICHE - {banque} TOUTES RÉGIONS"
            max_dispo = len(clients)
            retour_callback = f'retour_banque_fiche_{banque}'
        elif banque:
            clients = shop.par_banque.get(banque, [])
            nom = f"FICHE - {banque}"
            max_dispo = len(clients)
            retour_callback = 'fiche_banque'
        elif region:
            clients = shop.par_region.get(region, [])
            nom = f"FICHE - {region}"
            max_dispo = len(clients)
            retour_callback = 'fiche_region'
        else:
            await query.edit_message_text("❌ Erreur de sélection")
            return
    elif type_ == 'nm':
        op = context.user_data.get('operateur')
        clients = shop.par_operateur.get(op, [])
        nom = f"NM - {op}"
        max_dispo = len(clients)
        retour_callback = 'menu_nm'
    else:
        dom = context.user_data.get('domaine')
        clients = shop.par_domaine.get(dom, [])
        nom = f"ML - {dom}"
        max_dispo = len(clients)
        retour_callback = 'menu_ml'
    if max_dispo == 0:
        await query.edit_message_text(f"❌ Plus de stock disponible")
        return
    if quantite > max_dispo:
        quantite = max_dispo
        context.user_data['quantite'] = quantite
    prix_total = quantite * shop.prix[type_]
    texte = f"""
📦 {nom}

📊 Disponible: {max_dispo} clients

🔢 Quantité: {quantite} clients
💰 Prix: {prix_total:.2f}€
💶 Tarif: 20 clients = 1€
"""
    keyboard = [
        [InlineKeyboardButton("➖ 1000", callback_data='quantite_moins'),
         InlineKeyboardButton(f"{quantite}", callback_data='rien'),
         InlineKeyboardButton("➕ 1000", callback_data='quantite_plus')],
        [InlineKeyboardButton("✅ AJOUTER AU PANIER", callback_data='quantite_valider')],
        [InlineKeyboardButton("🔙 RETOUR", callback_data=retour_callback)]
    ]
    await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))

async def ajouter_au_panier(query, context):
    quantite = context.user_data.get('quantite', 1000)
    type_ = context.user_data.get('type', 'fiche')
    if type_ == 'fiche':
        mode = context.user_data.get('mode', 'region')
        banque = context.user_data.get('banque', '')
        region = context.user_data.get('region', '')
        if banque and region and region != 'TOUTES':
            clients = [c for c in shop.par_banque.get(banque, []) if c['region'] == region]
            clients = sorted(clients, key=lambda x: x['id'])[:quantite]
            if len(clients) < quantite:
                await query.edit_message_text(f"❌ Stock insuffisant !")
                return
            article = {'type': 'fiche', 'banque': banque, 'region': region, 'quantite': quantite, 'prix': quantite * shop.prix['fiche'], 'clients': [c['id'] for c in clients]}
            nom = f"FICHE - {banque} {region}"
            menu_retour = 'menu_fiche'
        elif banque and region == 'TOUTES':
            clients = shop.par_banque.get(banque, [])[:quantite]
            if len(clients) < quantite:
                await query.edit_message_text(f"❌ Stock insuffisant !")
                return
            article = {'type': 'fiche', 'banque': banque, 'region': 'TOUTES', 'quantite': quantite, 'prix': quantite * shop.prix['fiche'], 'clients': [c['id'] for c in clients]}
            nom = f"FICHE - {banque} TOUTES RÉGIONS"
            menu_retour = 'menu_fiche'
        elif banque:
            clients = shop.par_banque.get(banque, [])[:quantite]
            if len(clients) < quantite:
                await query.edit_message_text(f"❌ Stock insuffisant !")
                return
            article = {'type': 'fiche', 'banque': banque, 'quantite': quantite, 'prix': quantite * shop.prix['fiche'], 'clients': [c['id'] for c in clients]}
            nom = f"FICHE - {banque}"
            menu_retour = 'menu_fiche'
        elif region:
            clients = shop.par_region.get(region, [])[:quantite]
            if len(clients) < quantite:
                await query.edit_message_text(f"❌ Stock insuffisant !")
                return
            article = {'type': 'fiche', 'region': region, 'quantite': quantite, 'prix': quantite * shop.prix['fiche'], 'clients': [c['id'] for c in clients]}
            nom = f"FICHE - {region}"
            menu_retour = 'menu_fiche'
        else:
            await query.edit_message_text("❌ Erreur de sélection")
            return
    elif type_ == 'nm':
        op = context.user_data.get('operateur')
        clients = shop.par_operateur.get(op, [])[:quantite]
        if len(clients) < quantite:
            await query.edit_message_text(f"❌ Stock insuffisant !")
            return
        article = {'type': 'nm', 'operateur': op, 'quantite': quantite, 'prix': quantite * shop.prix['nm'], 'clients': [c['id'] for c in clients]}
        nom = f"NM - {op}"
        menu_retour = 'menu_nm'
    else:
        dom = context.user_data.get('domaine')
        clients = shop.par_domaine.get(dom, [])[:quantite]
        if len(clients) < quantite:
            await query.edit_message_text(f"❌ Stock insuffisant !")
            return
        article = {'type': 'ml', 'domaine': dom, 'quantite': quantite, 'prix': quantite * shop.prix['ml'], 'clients': [c['id'] for c in clients]}
        nom = f"ML - {dom}"
        menu_retour = 'menu_ml'
    if 'panier' not in context.user_data:
        context.user_data['panier'] = []
    article['lot'] = len(context.user_data['panier']) + 1
    context.user_data['panier'].append(article)
    context.user_data['quantite'] = 1000
    keyboard = [
        [InlineKeyboardButton("🛒 VOIR PANIER", callback_data='panier')],
        [InlineKeyboardButton("🔙 CONTINUER", callback_data=menu_retour)]
    ]
    await query.edit_message_text(f"✅ AJOUTÉ AU PANIER !\n\n📦 {nom}\n📊 {quantite} clients\n💰 {article['prix']:.2f}€", reply_markup=InlineKeyboardMarkup(keyboard))

# === GESTION MESSAGES ===
async def handle_message(update: Update, context):
    if not is_admin(update):
        return
    if 'prix_a_modifier' in context.user_data:
        try:
            nouveau_prix = float(update.message.text)
            service = context.user_data['prix_a_modifier']
            shop.prix[service] = nouveau_prix / 1000
            shop.sauver_prix()
            del context.user_data['prix_a_modifier']
            await update.message.reply_text(f"✅ Prix modifié: {service.upper()} = {nouveau_prix:.0f}€/1000")
        except ValueError:
            await update.message.reply_text("❌ Veuillez entrer un nombre valide")

# === TEST APIS ===
def test_apis():
    logger.info("Test des APIs crypto...")
    try:
        r = requests.get("https://blockchain.info/ticker", timeout=5)
        if r.status_code == 200:
            logger.info("✅ API Blockchain.info OK")
    except:
        logger.warning("⚠️ API Blockchain.info indisponible")
    try:
        r = requests.get("https://api.etherscan.io/api?module=proxy&action=eth_blockNumber", timeout=5)
        if r.status_code == 200:
            logger.info("✅ API Etherscan OK")
    except:
        logger.warning("⚠️ API Etherscan indisponible")
    try:
        r = requests.get("https://api.solscan.io/", timeout=5)
        if r.status_code == 200:
            logger.info("✅ API Solscan OK")
    except:
        logger.warning("⚠️ API Solscan indisponible")

# === MAIN ===
def main():
    logger.info("🚀 Démarrage du bot...")
    test_apis()
    shop.scanner(force=True)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    verif.set_app(app)
    verif.demarrer()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("✅ Bot prêt - Version ultime")
    app.run_polling()

if __name__ == "__main__":
    main()