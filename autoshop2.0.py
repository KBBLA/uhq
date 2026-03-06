# -*- coding: utf-8 -*-
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
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from types import SimpleNamespace

# === PRINTS DE DEBUG ===
print("="*50)
print("BOT DÉMARRAGE ÉTAPE 1")
print("="*50)
sys.stdout.flush()

print(f"Test d'écriture dans les logs")
sys.stdout.flush()

# === CORRECTION ENCODAGE WINDOWS ===
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')

# === IMPORTS TELEGRAM ===
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from fpdf import FPDF

# =========================
# CONFIGURATION AVEC ADAPTATION RENDER
# =========================

# Token et admin depuis variables d'environnement (ou valeurs par défaut)
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8483744061:AAH7n9OtzmpqtphEFZNIqJZTu-4zcj8qAZY")
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', 8295467733))

# Détection de l'environnement Render
if os.environ.get('RENDER'):
    DOSSIER = Path("/opt/render/project/src")
else:
    DOSSIER = Path("C:/Users/guidu/Desktop/autoshop2.0")

# Création des sous-dossiers
DOSSIER.mkdir(exist_ok=True)
DOSSIER_DATA = DOSSIER / "data"
DOSSIER_LOGS = DOSSIER / "logs"
DOSSIER_TEMP = DOSSIER / "temp"

for dossier in [DOSSIER_DATA, DOSSIER_LOGS, DOSSIER_TEMP]:
    dossier.mkdir(exist_ok=True)

# Fichiers de données
FICHIER_CLIENTS = DOSSIER_DATA / "clients.json"
FICHIER_UTILISATEURS = DOSSIER_DATA / "utilisateurs.json"
FICHIER_UTILISES = DOSSIER_DATA / "utilises.json"
FICHIER_TRANSACTIONS = DOSSIER_DATA / "transactions.json"
FICHIER_PRIX = DOSSIER_DATA / "prix.json"

# Prix par défaut (20 clients = 1€)
PRIX_PAR_DEFAUT = {
    'fiche': 0.05,
    'nm': 0.05,
    'ml': 0.05
}

# Configuration crypto
CRYPTO_CONFIG = {
    'ETH': {'adresse': '0xF8b46473e778406d1F9911932eaa423E028fA492', 'decimals': 18},
    'SOL': {'adresse': 'CJGz8F4SHzvVhZPr9k22v3rwgzMndQ5J5ssucND29B4V', 'decimals': 9},
    'BTC': {'adresse': 'bc1qyawv8j0mpxywqct8tntt96mqv8wnww4fxu0yg0', 'decimals': 8}
}

# =========================
# LOGGING
# =========================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(DOSSIER_LOGS / 'bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# =========================
# MAPPINGS COMPLETS
# =========================

# Mapping des départements vers régions
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

# Mapping des BIC vers noms de banques (DICTIONNAIRE COMPLET)
BANQUES = {
    # ===== GROUPE 1 : BANQUES NATIONALES =====
    'BNPA': 'BNP Paribas', 'BNP': 'BNP Paribas', 'BNPAFRPP': 'BNP Paribas',
    'BNPAFRPPXXX': 'BNP Paribas', '30004': 'BNP Paribas', 'BNPAP': 'BNP Paribas',
    'BNPAFRP': 'BNP Paribas', 'BNPAFR': 'BNP Paribas',
    
    'AGRI': 'Crédit Agricole', 'CA': 'Crédit Agricole', 'AGRIFRPP': 'Crédit Agricole',
    'AGRIFRPPXXX': 'Crédit Agricole', '30006': 'Crédit Agricole', 'AGRIFR': 'Crédit Agricole',
    'AGRIC': 'Crédit Agricole', 'CAFRPP': 'Crédit Agricole',
    
    'SOGE': 'Société Générale', 'SG': 'Société Générale', 'SOGEFRPP': 'Société Générale',
    'SOGEFRPPXXX': 'Société Générale', '30003': 'Société Générale', 'SOGEFR': 'Société Générale',
    
    'CMC': 'Crédit Mutuel', 'CM': 'Crédit Mutuel', 'CMCIFR2A': 'Crédit Mutuel',
    'CMCIFR2AXXX': 'Crédit Mutuel', '30002': 'Crédit Mutuel', 'CMUT': 'Crédit Mutuel',
    'CCOP': 'Crédit Mutuel', 'CMMC': 'Crédit Mutuel',
    
    'CIC': 'CIC', 'CICFRPP': 'CIC', 'CMCIC': 'CIC', '30066': 'CIC',
    'CICE': 'CIC', 'CICO': 'CIC', 'CICN': 'CIC', 'CICS': 'CIC',
    
    'LBP': 'La Banque Postale', 'BAPO': 'La Banque Postale', 'LBPFRPP': 'La Banque Postale',
    'LBPFRPPXXX': 'La Banque Postale', '30041': 'La Banque Postale',
    
    'HSBC': 'HSBC', 'HSBCFRPP': 'HSBC', 'HSBCFRPPXXX': 'HSBC', '30056': 'HSBC',
    
    'BOUY': 'Boursorama', 'BOURS': 'Boursorama', 'BOUYFRPP': 'Boursorama',
    'BUX': 'Boursorama', '30086': 'Boursorama',
    
    'AXA': 'AXA Banque', 'AXAB': 'AXA Banque', 'AXAFRPP': 'AXA Banque', '30088': 'AXA Banque',
    
    'ING': 'ING Direct', 'INGB': 'ING Direct', 'INGFRPP': 'ING Direct', '30076': 'ING Direct',
    
    'FORT': 'Fortuneo', 'FORTUNEO': 'Fortuneo', 'FORTFRPP': 'Fortuneo', '30198': 'Fortuneo',
    
    'HELL': 'Hello Bank', 'HELLO': 'Hello Bank', 'HELO': 'Hello Bank',
    
    'MONA': 'Monabanq', 'MONABANQ': 'Monabanq',
    
    'ORAN': 'Orange Bank', 'ORANGE': 'Orange Bank', 'ORAB': 'Orange Bank',
    
    'REVO': 'Revolut', 'REVOLT': 'Revolut', 'REVOFRPP': 'Revolut',
    
    'N26': 'N26', 'N26FRPP': 'N26', 'NTWO': 'N26',
    
    'NICK': 'Nickel', 'NICKEL': 'Nickel', 'NIKL': 'Nickel',
    
    # ===== GROUPE 2 : BANQUES POPULAIRES =====
    'BP': 'Banque Populaire', 'BPCE': 'Banque Populaire', 'BPCEFRPP': 'Banque Populaire',
    'BPCEFRPPXXX': 'Banque Populaire', 'CCBP': 'Banque Populaire', '10107': 'Banque Populaire',
    'BPAY': 'Banque Populaire', 'BPAL': 'Banque Populaire', 'BPAU': 'Banque Populaire',
    'BPAX': 'Banque Populaire',
    
    'BRED': 'BRED', 'BREDFRPP': 'BRED',
    'CASD': 'Casden Banque Populaire', 'CASDEN': 'Casden Banque Populaire',
    'CCB': 'Crédit Coopératif', 'COOP': 'Crédit Coopératif',
    
    # ===== GROUPE 3 : CAISSES D'EPARGNE =====
    'CE': 'Caisse d\'Epargne', 'CEP': 'Caisse d\'Epargne', 'CEPA': 'Caisse d\'Epargne',
    'CEPAFRPP': 'Caisse d\'Epargne', '11207': 'Caisse d\'Epargne', 'CEFR': 'Caisse d\'Epargne',
    'CEIDF': 'Caisse d\'Epargne IDF', 'CEARA': 'Caisse d\'Epargne ARA',
    'CEPAC': 'Caisse d\'Epargne PACA', 'CENOR': 'Caisse d\'Epargne Normandie',
    'CEBFC': 'Caisse d\'Epargne BFC', 'CEBRE': 'Caisse d\'Epargne Bretagne',
    'CECVL': 'Caisse d\'Epargne CVL', 'CEGE': 'Caisse d\'Epargne Grand Est',
    'CEHDF': 'Caisse d\'Epargne HDF', 'CENA': 'Caisse d\'Epargne NA',
    'CENQ': 'Caisse d\'Epargne NQ', 'CEPDL': 'Caisse d\'Epargne PDL',
    
    # ===== GROUPE 4 : LCL =====
    'LCL': 'LCL', 'LCLFRPP': 'LCL', 'LCLFRPPXXX': 'LCL', 'CRLY': 'LCL',
    'LCLPAR': 'LCL', 'LCLPRO': 'LCL',
    
    # ===== GROUPE 5 : CRÉDIT DU NORD =====
    'CDN': 'Crédit du Nord', 'NOR': 'Crédit du Nord', 'CREDINORD': 'Crédit du Nord',
    '30007': 'Crédit du Nord', 'CDNFRPP': 'Crédit du Nord',
    
    # ===== GROUPE 6 : BANQUES RÉGIONALES =====
    'CHAIX': 'Banque Chaix', 'CTOIS': 'Banque Courtois', 'KOLB': 'Banque Kolb',
    'LAYD': 'Banque Laydernier', 'NEUF': 'Banque de Neuflize', 'BRA': 'Banque Rhône-Alpes',
    'TARN': 'Banque Tarneaud', 'TRANS': 'Banque Transatlantique', 'BQUE': 'Banque de Savoie',
    'BQMC': 'Banque Marze', 'BRS': 'Banque Rhône-Alpes Sud', 'BCH': 'Banque Chalus',
    'BGR': 'Banque Graniou', 'BJR': 'Banque Jazz', 'BTL': 'Banque Thaler',
    'BMR': 'Banque Marze', 'BRH': 'Banque Rhône-Alpes', 'BTO': 'Banque de Touraine',
    'BLO': 'Banque de Loire', 'BLY': 'Banque Lyonnaise', 'BST': 'Banque de Strasbourg',
    'BLI': 'Banque de Lille', 'BMA': 'Banque de Marseille', 'BNA': 'Banque Nanceienne',
    
    # ===== GROUPE 7 : BANQUES PRIVÉES =====
    'RIVA': 'Riva Bank', 'BORD': 'Banque de Bordeaux', 'BTOU': 'Banque de Touraine',
    'BLOI': 'Banque de Loire', 'BLYO': 'Banque Lyonnaise', 'BSTR': 'Banque de Strasbourg',
    'BLIL': 'Banque de Lille', 'BMAR': 'Banque de Marseille', 'BNAN': 'Banque Nanceienne',
    
    # ===== GROUPE 8 : BANQUES D'INVESTISSEMENT =====
    'NATX': 'Natixis', 'NATIXIS': 'Natixis', 'BP2S': 'BP2S', 'BPSS': 'BPSS',
    'CALY': 'Calyon', 'CLYP': 'Calyon', 'CAIS': 'Caisse des Dépôts', 'CDC': 'Caisse des Dépôts',
    
    # ===== GROUPE 9 : BANQUES ÉTRANGÈRES EN FRANCE =====
    'BARCL': 'Barclays France', 'BARC': 'Barclays France',
    'DEUT': 'Deutsche Bank France', 'DBFR': 'Deutsche Bank France',
    'GOLD': 'Goldman Sachs France', 'MORG': 'Morgan Stanley France',
    'UBS': 'UBS France', 'UBSW': 'UBS France', 'JPMC': 'JP Morgan France',
    'CACE': 'Caceis Bank', 'ODDO': 'Oddo BHF', 'ODDOFRPP': 'Oddo BHF',
    'ROTH': 'Rothschild & Co', 'LAZ': 'Lazard Frères',
    
    # ===== GROUPE 10 : BANQUES EN LIGNE =====
    'FORTU': 'Fortuneo', 'BINC': 'BforBank', 'BFOR': 'BforBank',
    'MAX': 'Max', 'MAXX': 'Max', 'QNTO': 'Qonto', 'QONT': 'Qonto',
    'SHFT': 'Shine', 'SHIN': 'Shine', 'ANDB': 'Anytime', 'ANY': 'Anytime',
    'WELT': 'Welth', 'WLTH': 'Welth', 'MONE': 'MoneyVox',
    
    # ===== GROUPE 11 : BANQUES POSTALES =====
    'LBPCR': 'La Banque Postale Crédit', 'LBPCO': 'La Banque Postale Crédit',
    'LBPCB': 'La Banque Postale',
    
    # ===== GROUPE 12 : CRÉDITS MUNICIPAUX =====
    'CMUN': 'Crédit Municipal de Paris', 'CMP': 'Crédit Municipal de Paris',
    'CMBO': 'Crédit Municipal de Bordeaux', 'CMLY': 'Crédit Municipal de Lyon',
    'CMNI': 'Crédit Municipal de Nîmes', 'CMTL': 'Crédit Municipal de Toulouse',
    'CMLI': 'Crédit Municipal de Lille', 'CMST': 'Crédit Municipal de Strasbourg',
    
    # ===== GROUPE 13 : CAISSES DE CRÉDIT MUTUEL =====
    'CMAR': 'Crédit Mutuel Arkea', 'CMBR': 'Crédit Mutuel Bretagne',
    'CMCE': 'Crédit Mutuel Centre', 'CMSO': 'Crédit Mutuel Sud-Ouest',
    'CMOC': 'Crédit Mutuel Océan', 'CMMC': 'Crédit Mutuel Massif Central',
    'CMAN': 'Crédit Mutuel Anjou', 'CMM': 'Crédit Mutuel Maine',
    'ARKEA': 'Crédit Mutuel Arkea', 'FEDERAL': 'Banque Fédérale du Crédit Mutuel',
    'BECM': 'Banque Européenne du Crédit Mutuel', 'CMNE': 'Crédit Mutuel Nord Europe',
    
    # ===== GROUPE 14 : BANQUES DE DÉTAIL =====
    'CARREF': 'Carrefour Banque', 'CETE': 'Cetelem', 'COFI': 'Cofidis',
    'FRAN': 'Franfinance', 'SOFI': 'Sofinco', 'PSA': 'PSA Banque',
    'RENA': 'RCI Banque', 'BNF': 'BNF Banque', 'FLOA': 'Floa Bank',
    'YOUS': 'Younited Credit', 'YOUN': 'Younited Credit', 'PRET': 'Pret d\'Union',
    
    # ===== GROUPE 15 : BANQUES SPÉCIALISÉES =====
    'CASDEN': 'Casden Banque Populaire', 'CCF': 'Crédit Commercial de France',
    'CCF2': 'Crédit Commercial de France', 'BTP': 'Banque BTP', 'BTPB': 'Banque BTP',
    'BFM': 'BFM', 'BAIL': 'Crédit Agricole Leasing',
    
    # ===== GROUPE 16 : BANQUES DE PROXIMITÉ =====
    'BPS': 'Banque Populaire du Sud', 'BPCA': 'Banque Populaire Côte d\'Azur',
    'BPAQ': 'Banque Populaire Aquitaine', 'BPLR': 'Banque Populaire Loire',
    'BPRA': 'Banque Populaire Rhône-Alpes', 'BPIDF': 'Banque Populaire IDF',
    'BPMED': 'Banque Populaire Méditerranée', 'BPCEN': 'Banque Populaire Centre',
    'BPNOR': 'Banque Populaire Nord', 'BPOU': 'Banque Populaire Ouest',
    
    # ===== GROUPE 17 : AUTRES =====
    'BQ': 'Banque Populaire', 'CERA': 'CERA', 'CER': 'CER', 'CEF': 'CEF',
    'CEI': 'CEI', 'CEL': 'CEL',
    
    # ===== GROUPE 18 : BANQUES SPÉCIFIQUES =====
    'BCC': 'Banque Courtois', 'BCP': 'Banque Châtelain Patrimoine',
    'BSP': 'Banque de Savoie', 'BML': 'Banque Martin Maurel',
    'BMM': 'Banque Martin Maurel', 'BL': 'Banque Laydernier',
}

# Mapping des préfixes téléphone vers opérateurs
OPERATEURS = {
    '06': {
        '06': 'Orange', '07': 'Orange', '60': 'SFR', '61': 'SFR', '62': 'SFR',
        '63': 'SFR', '64': 'SFR', '65': 'SFR', '66': 'Bouygues', '67': 'Bouygues',
        '68': 'Bouygues', '69': 'Free', '70': 'Free', '71': 'Free', '72': 'Free',
        '73': 'Free', '74': 'Free', '75': 'Free', '76': 'Free', '77': 'Free',
        '78': 'Free', '79': 'Free',
    },
    '07': {
        '07': 'Orange', '70': 'Orange', '71': 'Orange', '72': 'Orange', '73': 'Orange',
        '74': 'Orange', '75': 'Orange', '76': 'Orange', '77': 'Orange', '78': 'SFR',
        '79': 'SFR', '80': 'SFR', '81': 'Bouygues', '82': 'Bouygues', '83': 'Bouygues',
        '84': 'Free', '85': 'Free', '86': 'Free', '87': 'Free', '88': 'Free', '89': 'Free',
    }
}

# Mapping des domaines email
DOMAINES = {
    'gmail.com': 'Gmail', 'googlemail.com': 'Gmail',
    'hotmail.fr': 'Hotmail', 'hotmail.com': 'Hotmail', 'msn.com': 'Hotmail',
    'outlook.fr': 'Outlook', 'outlook.com': 'Outlook', 'live.fr': 'Live',
    'live.com': 'Live',
    'yahoo.fr': 'Yahoo', 'yahoo.com': 'Yahoo', 'ymail.com': 'Yahoo',
    'orange.fr': 'Orange', 'wanadoo.fr': 'Orange', 'voila.fr': 'Orange',
    'sfr.fr': 'SFR', 'neuf.fr': 'SFR',
    'bouygues.fr': 'Bouygues', 'bbox.fr': 'Bouygues',
    'free.fr': 'Free',
    'laposte.net': 'La Poste',
    'icloud.com': 'iCloud', 'me.com': 'iCloud', 'mac.com': 'iCloud',
    'protonmail.com': 'ProtonMail', 'proton.me': 'ProtonMail',
}

# =========================
# CLASS PRINCIPALE
# =========================

class AutoShop:
    def __init__(self):
        self.clients = {}
        self.valides = {}
        self.utilises = set()
        self.users = {}
        self.transactions = []
        self.prix = PRIX_PAR_DEFAUT.copy()
        self.charger()
    
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
                    
                for uid, user_data in self.users.items():
                    if 'achats' not in user_data:
                        user_data['achats'] = []
                    if 'recharges' not in user_data:
                        user_data['recharges'] = []
            
            if FICHIER_UTILISES.exists():
                with open(FICHIER_UTILISES, 'r', encoding='utf-8') as f:
                    self.utilises = set(json.load(f))
            
            if FICHIER_TRANSACTIONS.exists():
                with open(FICHIER_TRANSACTIONS, 'r', encoding='utf-8') as f:
                    self.transactions = json.load(f)
            
            if FICHIER_PRIX.exists():
                with open(FICHIER_PRIX, 'r', encoding='utf-8') as f:
                    self.prix = json.load(f)
            
            logger.info(f"Chargé: {len(self.valides)} valides, {len(self.utilises)} utilisés")
        except Exception as e:
            logger.error(f"Erreur chargement: {e}")
    
    def sauver(self):
        try:
            with open(FICHIER_CLIENTS, 'w', encoding='utf-8') as f:
                json.dump({
                    'clients': self.clients,
                    'valides': self.valides
                }, f, indent=2, ensure_ascii=False)
            
            with open(FICHIER_UTILISATEURS, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
            
            with open(FICHIER_UTILISES, 'w', encoding='utf-8') as f:
                json.dump(list(self.utilises), f, indent=2, ensure_ascii=False)
            
            with open(FICHIER_TRANSACTIONS, 'w', encoding='utf-8') as f:
                json.dump(self.transactions, f, indent=2, ensure_ascii=False)
            
            with open(FICHIER_PRIX, 'w', encoding='utf-8') as f:
                json.dump(self.prix, f, indent=2, ensure_ascii=False)
            
            logger.info("Données sauvegardées")
        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")
    
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
        """Parse une ligne avec TOUS les séparateurs possibles"""
        try:
            ligne = ligne.strip()
            if not ligne or ligne.startswith('#'):
                return None
            
            separateurs = ['|', ';', ',', '\t']
            parties = None
            
            for sep in separateurs:
                test = ligne.split(sep)
                if len(test) >= 8:
                    parties = test
                    logger.debug(f"Séparateur trouvé: '{sep}'")
                    break
            
            if not parties:
                test = re.split(r'\s+', ligne)
                if len(test) >= 8:
                    parties = test
                    logger.debug("Séparateur trouvé: espaces")
            
            if not parties:
                test = ligne.split(':')
                if len(test) >= 8:
                    parties = test
                    logger.debug("Séparateur trouvé: ':'")
            
            if not parties:
                logger.warning(f"Aucun séparateur trouvé pour: {ligne[:50]}...")
                return None
            
            parties = [p.strip() for p in parties]
            
            c = {}
            idx = 0
            c['nom'] = parties[idx] if idx < len(parties) else ''
            idx += 1
            c['pays'] = parties[idx] if idx < len(parties) else ''
            idx += 1
            c['date'] = parties[idx] if idx < len(parties) else ''
            idx += 1
            c['adresse'] = parties[idx] if idx < len(parties) else ''
            idx += 1
            c['cp'] = parties[idx] if idx < len(parties) else ''
            idx += 1
            c['ville'] = parties[idx] if idx < len(parties) else ''
            idx += 1
            c['tel'] = parties[idx] if idx < len(parties) else ''
            idx += 1
            c['email'] = parties[idx] if idx < len(parties) else ''
            idx += 1
            c['iban'] = parties[idx] if idx < len(parties) else ''
            idx += 1
            c['bic'] = parties[idx] if idx < len(parties) else ''
            
            c['region'] = self.get_region(c['cp'])
            c['banque'] = self.get_banque(c['bic'])
            c['operateur'] = self.get_operateur(c['tel'])
            c['domaine'] = self.get_domaine(c['email'])
            
            c['valide'] = all([
                c['nom'], 
                c['date'], 
                c['adresse'], 
                c['cp'], 
                c['ville'], 
                c['tel'], 
                c['email']
            ])
            
            uid = f"{c['nom']}|{c['date']}|{c.get('iban', '')}"
            c['id'] = hashlib.md5(uid.encode()).hexdigest()[:16]
            
            return c
            
        except Exception as e:
            logger.error(f"Erreur parse ligne: {e}")
            return None
    
    def scanner(self):
        """Scanne tous les fichiers avec logs détaillés"""
        logger.info("="*50)
        logger.info("SCAN DU DOSSIER")
        logger.info("="*50)
        
        self.clients = {}
        self.valides = {}
        
        fichiers = list(DOSSIER.glob("*.txt")) + list(DOSSIER.glob("*.csv")) + \
                   list(DOSSIER.glob("*.TXT")) + list(DOSSIER.glob("*.CSV"))
        
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
                    
                    if i > 0 and i % 10000 == 0:
                        logger.info(f"    ... {i} lignes traitées")
                
                logger.info(f"  ✅ {valides} clients valides dans ce fichier")
                
            except Exception as e:
                logger.error(f"Erreur lecture {fichier}: {e}")
        
        logger.info("="*50)
        logger.info(f"SCAN TERMINÉ")
        logger.info(f"Total lignes: {total_lignes}")
        logger.info(f"Total valides: {valides}")
        logger.info("="*50)
        
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

# =========================
# PRIX CRYPTO
# =========================

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

# =========================
# FONCTIONS DE LIVRAISON PDF CLEAN
# =========================

async def livrer_commande(update_or_query, context, commande_id: str, panier: list, montant: float):
    """Livre une commande avec des PDFs propres et bien formatés"""
    try:
        await update_or_query.message.reply_text("📦 **Préparation de votre commande...**")
        
        total_clients = 0
        for article in panier:
            for client_id in article['clients']:
                if client_id in shop.valides:
                    shop.utilises.add(client_id)
                    total_clients += 1
        shop.sauver()
        
        pdfs_envoyes = 0
        for i, article in enumerate(panier, 1):
            clients = [shop.valides[cid] for cid in article['clients'] if cid in shop.valides]
            if not clients:
                continue
            
            if article['type'] == 'fiche':
                pdf_path = generer_pdf_fiche_clean(clients, article)
            elif article['type'] == 'nm':
                pdf_path = generer_pdf_nm_clean(clients, article)
            else:
                pdf_path = generer_pdf_ml_clean(clients, article)
            
            with open(pdf_path, 'rb') as f:
                await update_or_query.message.reply_document(
                    document=f,
                    filename=f"{article['type']}_{commande_id}_{article['lot']}.pdf",
                    caption=f"✅ Lot {i}/{len(panier)} - {article['quantite']} clients"
                )
            
            os.unlink(pdf_path)
            pdfs_envoyes += 1
        
        await update_or_query.message.reply_text(
            f"✅ **Commande #{commande_id} terminée !**\n\n"
            f"📊 {total_clients} clients livrés\n"
            f"📄 {pdfs_envoyes} fichiers PDF\n"
            f"💰 Total: {montant:.2f}€\n\n"
            f"Merci de votre confiance !"
        )
        
        logger.info(f"Commande {commande_id} livrée: {pdfs_envoyes} PDFs, {total_clients} clients")
        
    except Exception as e:
        logger.error(f"Erreur livraison commande {commande_id}: {e}")
        await update_or_query.message.reply_text(
            f"❌ Erreur lors de la livraison. Contactez l'admin avec le numéro #{commande_id}"
        )

def generer_pdf_fiche_clean(clients, article):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"FICHE BANCAIRE", 0, 1, 'C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"Lot #{article['lot']} - {article['quantite']} clients", 0, 1, 'C')
    
    if 'banque' in article and 'region' in article:
        pdf.cell(0, 6, f"{article['banque']} - {article['region']}", 0, 1, 'C')
    elif 'banque' in article:
        pdf.cell(0, 6, f"{article['banque']}", 0, 1, 'C')
    elif 'region' in article:
        pdf.cell(0, 6, f"Région {article['region']}", 0, 1, 'C')
    
    pdf.ln(5)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
    pdf.ln(10)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(10, 8, '#', 1, 0, 'C', 1)
    pdf.cell(40, 8, 'Nom', 1, 0, 'L', 1)
    pdf.cell(25, 8, 'Naissance', 1, 0, 'C', 1)
    pdf.cell(50, 8, 'Adresse', 1, 0, 'L', 1)
    pdf.cell(25, 8, 'Téléphone', 1, 0, 'L', 1)
    pdf.cell(40, 8, 'Email', 1, 1, 'L', 1)
    
    pdf.set_font('Arial', '', 8)
    for i, client in enumerate(clients[:50], 1):
        if i > 1 and i % 50 == 1:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 9)
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(10, 8, '#', 1, 0, 'C', 1)
            pdf.cell(40, 8, 'Nom', 1, 0, 'L', 1)
            pdf.cell(25, 8, 'Naissance', 1, 0, 'C', 1)
            pdf.cell(50, 8, 'Adresse', 1, 0, 'L', 1)
            pdf.cell(25, 8, 'Téléphone', 1, 0, 'L', 1)
            pdf.cell(40, 8, 'Email', 1, 1, 'L', 1)
            pdf.set_font('Arial', '', 8)
        
        nom = client['nom'][:38] if len(client['nom']) > 38 else client['nom']
        date = client['date'][:23] if len(client['date']) > 23 else client['date']
        adresse = f"{client['adresse'][:20]} {client['cp']} {client['ville'][:10]}"
        adresse = adresse[:48] if len(adresse) > 48 else adresse
        tel = client['tel'][:23] if len(client['tel']) > 23 else client['tel']
        email = client['email'][:38] if len(client['email']) > 38 else client['email']
        
        pdf.cell(10, 6, str(i), 1, 0, 'C')
        pdf.cell(40, 6, nom, 1, 0, 'L')
        pdf.cell(25, 6, date, 1, 0, 'C')
        pdf.cell(50, 6, adresse, 1, 0, 'L')
        pdf.cell(25, 6, tel, 1, 0, 'L')
        pdf.cell(40, 6, email, 1, 1, 'L')
    
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, "IBAN / BIC", 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(10, 8, '#', 1, 0, 'C', 1)
    pdf.cell(60, 8, 'IBAN', 1, 0, 'L', 1)
    pdf.cell(40, 8, 'BIC', 1, 0, 'L', 1)
    pdf.cell(40, 8, 'Banque', 1, 0, 'L', 1)
    pdf.cell(40, 8, 'Région', 1, 1, 'L', 1)
    
    pdf.set_font('Arial', '', 8)
    for i, client in enumerate(clients, 1):
        if i > 1 and i % 60 == 1:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 9)
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(10, 8, '#', 1, 0, 'C', 1)
            pdf.cell(60, 8, 'IBAN', 1, 0, 'L', 1)
            pdf.cell(40, 8, 'BIC', 1, 0, 'L', 1)
            pdf.cell(40, 8, 'Banque', 1, 0, 'L', 1)
            pdf.cell(40, 8, 'Région', 1, 1, 'L', 1)
            pdf.set_font('Arial', '', 8)
        
        iban = client.get('iban', '')[:58] if len(client.get('iban', '')) > 58 else client.get('iban', '')
        bic = client.get('bic', '')[:38] if len(client.get('bic', '')) > 38 else client.get('bic', '')
        banque = client.get('banque', '')[:38] if len(client.get('banque', '')) > 38 else client.get('banque', '')
        region = client.get('region', '')[:38] if len(client.get('region', '')) > 38 else client.get('region', '')
        
        pdf.cell(10, 6, str(i), 1, 0, 'C')
        pdf.cell(60, 6, iban, 1, 0, 'L')
        pdf.cell(40, 6, bic, 1, 0, 'L')
        pdf.cell(40, 6, banque, 1, 0, 'L')
        pdf.cell(40, 6, region, 1, 1, 'L')
    
    filename = DOSSIER_TEMP / f"fiche_{article['lot']}_{uuid.uuid4().hex[:8]}.pdf"
    pdf.output(str(filename))
    return str(filename)

def generer_pdf_nm_clean(clients, article):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"NUMÉROS DE TÉLÉPHONE", 0, 1, 'C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"Lot #{article['lot']} - {article['quantite']} numéros", 0, 1, 'C')
    pdf.cell(0, 6, f"Opérateur: {article['operateur']}", 0, 1, 'C')
    pdf.ln(5)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
    pdf.ln(10)
    
    pdf.set_font('Courier', '', 10)
    col_width = 63
    x_init = pdf.get_x()
    y_init = pdf.get_y()
    
    for i, client in enumerate(clients, 1):
        col = (i - 1) % 3
        if col == 0 and i > 1:
            pdf.set_y(y_init + ((i-1)//3) * 6)
        
        pdf.set_x(x_init + col * col_width)
        pdf.cell(col_width, 6, client['tel'], 0, 0, 'L')
        
        if i % 150 == 0:
            pdf.add_page()
            y_init = pdf.get_y()
    
    filename = DOSSIER_TEMP / f"nm_{article['lot']}_{uuid.uuid4().hex[:8]}.pdf"
    pdf.output(str(filename))
    return str(filename)

def generer_pdf_ml_clean(clients, article):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"ADRESSES EMAIL", 0, 1, 'C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"Lot #{article['lot']} - {article['quantite']} emails", 0, 1, 'C')
    pdf.cell(0, 6, f"Domaine: {article['domaine']}", 0, 1, 'C')
    pdf.ln(5)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
    pdf.ln(10)
    
    pdf.set_font('Courier', '', 9)
    col_width = 95
    x_init = pdf.get_x()
    y_init = pdf.get_y()
    
    for i, client in enumerate(clients, 1):
        col = (i - 1) % 2
        if col == 0 and i > 1:
            pdf.set_y(y_init + ((i-1)//2) * 5)
        
        pdf.set_x(x_init + col * col_width)
        pdf.cell(col_width, 5, client['email'][:45], 0, 0, 'L')
        
        if i % 200 == 0:
            pdf.add_page()
            y_init = pdf.get_y()
    
    filename = DOSSIER_TEMP / f"ml_{article['lot']}_{uuid.uuid4().hex[:8]}.pdf"
    pdf.output(str(filename))
    return str(filename)

# =========================
# VÉRIFICATION AUTO AVEC TOLÉRANCE
# =========================

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
        # API 1: Solscan
        try:
            url = f"https://api.solscan.io/account/transactions?account={adresse}&limit=10"
            headers = {'Accept': 'application/json'}
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                for tx in data.get('data', [])[:10]:
                    if tx.get('status') == 'Success':
                        for instr in tx.get('parsedInstruction', []):
                            if instr.get('type') == 'transfer':
                                params = instr.get('params', {})
                                if params.get('destination') == adresse:
                                    montant_recu = params.get('lamports', 0) / 10**9
                                    if abs(montant_recu - montant_attendu) < 0.01:
                                        logger.info(f"✅ SOL confirmé via Solscan: {montant_recu}")
                                        return True
        except Exception as e:
            logger.warning(f"Solscan indisponible: {e}")
        
        # API 2: Solana RPC
        try:
            url = "https://api.mainnet-beta.solana.com"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [adresse, {"limit": 5}]
            }
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code == 200:
                signatures = r.json().get('result', [])
                if signatures:
                    logger.info(f"✅ SOL confirmé via RPC")
                    return True
        except Exception as e:
            logger.warning(f"Solana RPC indisponible: {e}")
        
        return False
    
    def _verifier(self):
        suppr = []
        for cmd, data in list(self.attente.items()):
            try:
                crypto = data['crypto']
                adr = data['adresse']
                montant_attendu = data['montant_crypto']
                
                logger.info(f"Vérification {crypto} - Commande {cmd} - Attendu: {montant_attendu:.6f}")
                
                if crypto == 'BTC':
                    url = f"https://blockchain.info/rawaddr/{adr}"
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        data_btc = r.json()
                        for tx in data_btc.get('txs', [])[:10]:
                            montant_recu = 0
                            for out in tx.get('out', []):
                                if out.get('addr') == adr:
                                    montant_recu += out.get('value', 0) / 100_000_000
                            
                            if montant_recu > 0 and abs(montant_recu - montant_attendu) < 0.0005:
                                logger.info(f"✅ BTC confirmé: {montant_recu}")
                                self._confirmer(cmd, data)
                                suppr.append(cmd)
                                break
                
                elif crypto == 'ETH':
                    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={adr}&sort=desc"
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        data_eth = r.json()
                        if data_eth.get('status') == '1':
                            for tx in data_eth.get('result', [])[:10]:
                                if tx.get('to', '').lower() == adr.lower():
                                    montant_recu = int(tx.get('value', 0)) / 10**18
                                    if abs(montant_recu - montant_attendu) < 0.01:
                                        logger.info(f"✅ ETH confirmé: {montant_recu}")
                                        self._confirmer(cmd, data)
                                        suppr.append(cmd)
                                        break
                
                elif crypto == 'SOL':
                    if self._verifier_sol(adr, montant_attendu):
                        self._confirmer(cmd, data)
                        suppr.append(cmd)
            
            except Exception as e:
                logger.error(f"Erreur vérification {cmd}: {e}")
        
        for cmd in suppr:
            self.attente.pop(cmd, None)
            logger.info(f"Commande {cmd} retirée de la file d'attente")
    
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
            type_paiement = data.get('type', 'achat')
            
            if type_paiement == 'recharge':
                user_str = str(uid)
                if user_str in shop.users:
                    shop.users[user_str]['solde'] += montant
                    if 'recharges' not in shop.users[user_str]:
                        shop.users[user_str]['recharges'] = []
                    shop.users[user_str]['recharges'].append({
                        'date': datetime.now().isoformat(),
                        'montant': montant,
                        'cmd': cmd
                    })
                    shop.sauver()
                    
                    await self.app.bot.send_message(
                        uid,
                        f"✅ **Recharge confirmée !**\n\n"
                        f"💰 +{montant:.2f}€\n"
                        f"💶 Nouveau solde: {shop.users[user_str]['solde']:.2f}€"
                    )
                return
            
            await self.app.bot.send_message(uid, "✅ **Paiement confirmé !**\n📦 Préparation de vos PDFs...")
            
            fake_message = SimpleNamespace()
            fake_message.reply_text = lambda text, **kwargs: self.app.bot.send_message(uid, text, **kwargs)
            fake_update = SimpleNamespace()
            fake_update.message = fake_message
            
            await livrer_commande(fake_update, None, cmd, panier, montant)
            
        except Exception as e:
            logger.error(f"Erreur livraison: {e}")
            await self.app.bot.send_message(
                uid,
                f"❌ Erreur lors de la livraison. Contactez l'admin avec le numéro #{cmd}"
            )

verif = VerifAuto()

# =========================
# SÉCURITÉ
# =========================

def is_admin(update):
    return update.effective_user.id == ADMIN_USER_ID

# =========================
# FONCTION ACCUEIL
# =========================

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

# =========================
# START
# =========================

async def start(update: Update, context):
    user = update.effective_user
    uid = str(user.id)
    
    if uid not in shop.users:
        shop.users[uid] = {
            'nom': user.first_name,
            'user': user.username,
            'date': datetime.now().isoformat(),
            'solde': 0,
            'achats': [],
            'recharges': []
        }
        shop.sauver()
    
    await accueil(update, context)

# =========================
# ADMIN
# =========================

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

💰 PRIX ACTUELS:
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

# =========================
# BUTTON HANDLER
# =========================

async def button(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # ===== RETOURS =====
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
    
    if data.startswith('retour_region_fiche_'):
        region = data.replace('retour_region_fiche_', '')
        await region_fiche(query, context, region)
        return
    
    if data.startswith('retour_banque_fiche_'):
        banque = data.replace('retour_banque_fiche_', '')
        await banque_fiche(query, context, banque)
        return
    
    # ===== MENUS PRINCIPAUX =====
    if data == 'menu_fiche':
        await menu_fiche(query, context)
        return
    
    if data == 'menu_nm':
        await menu_nm(query, context)
        return
    
    if data == 'menu_ml':
        await menu_ml(query, context)
        return
    
    # ===== FICHE - OPTIONS =====
    if data == 'fiche_banque':
        await fiche_banques(query, context)
        return
    
    if data == 'fiche_region':
        await fiche_regions(query, context)
        return
    
    if data == 'fiche_mixte':
        await fiche_mixte_banque(query, context)
        return
    
    # ===== FICHE - BANQUES =====
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
        banque = parts[0]
        region = parts[1]
        context.user_data['type'] = 'fiche'
        context.user_data['banque'] = banque
        context.user_data['region'] = region
        context.user_data['mode'] = 'mixte'
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)
        return
    
    # ===== FICHE - RÉGIONS =====
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
        region = parts[0]
        banque = parts[1]
        context.user_data['type'] = 'fiche'
        context.user_data['region'] = region
        context.user_data['banque'] = banque
        context.user_data['mode'] = 'mixte'
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)
        return
    
    # ===== FICHE - MIXTE =====
    if data.startswith('mixte_banque_'):
        banque = data.replace('mixte_banque_', '')
        context.user_data['mixte_banque'] = banque
        await fiche_mixte_region(query, context, banque)
        return
    
    if data.startswith('mixte_valider_'):
        parts = data.replace('mixte_valider_', '').split('|')
        banque = parts[0]
        region = parts[1]
        context.user_data['type'] = 'fiche'
        context.user_data['banque'] = banque
        context.user_data['region'] = region
        context.user_data['mode'] = 'mixte'
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)
        return
    
    # ===== NM =====
    if data.startswith('operateur_'):
        op = data.replace('operateur_', '')
        context.user_data['type'] = 'nm'
        context.user_data['operateur'] = op
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)
        return
    
    # ===== ML =====
    if data.startswith('domaine_'):
        dom = data.replace('domaine_', '')
        context.user_data['type'] = 'ml'
        context.user_data['domaine'] = dom
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)
        return
    
    # ===== CHOIX QUANTITÉ =====
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
    
    # ===== PANIER =====
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
            [InlineKeyboardButton("✅ VALIDER", callback_data='valider'),
             InlineKeyboardButton("🗑️ VIDER", callback_data='vider')],
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
            [InlineKeyboardButton("🟣 ETH", callback_data='payer_eth'),
             InlineKeyboardButton("🔵 SOL", callback_data='payer_sol')],
            [InlineKeyboardButton("🟡 BTC", callback_data='payer_btc')],
            [InlineKeyboardButton("🔙 RETOUR", callback_data='panier')]
        ]
        
        await query.edit_message_text(
            f"💰 TOTAL: {total:.2f}€\n\nChoisissez votre crypto :",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
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
    
    # ===== RECHARGE =====
    if data == 'recharger':
        keyboard = [
            [InlineKeyboardButton("🟣 50€ ETH", callback_data='recharge_50_eth'),
             InlineKeyboardButton("🔵 50€ SOL", callback_data='recharge_50_sol')],
            [InlineKeyboardButton("🟡 50€ BTC", callback_data='recharge_50_btc')],
            [InlineKeyboardButton("🔙 RETOUR", callback_data='portefeuille')]
        ]
        await query.edit_message_text(
            "💰 RECHARGER PORTEFEUILLE\n\nChoisissez 50€ de recharge :",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data.startswith('recharge_50_'):
        crypto = data.replace('recharge_50_', '').upper()
        montant_eur = 50
        cmd_id = f"RECH_{uuid.uuid4().hex[:8].upper()}"
        
        p = prix.get(crypto)
        montant_crypto = montant_eur / p if p > 0 else 0
        adresse = CRYPTO_CONFIG[crypto]['adresse']
        
        texte = f"""
💰 RECHARGE 50€

Commande #{cmd_id}
💶 50€ = {montant_crypto:.6f} {crypto}

📤 Envoyez à :
`{adresse}`

⏳ Vérification automatique...
"""
        
        verif.attente[cmd_id] = {
            'crypto': crypto,
            'montant_eur': 50,
            'montant_crypto': montant_crypto,
            'user_id': query.from_user.id,
            'adresse': adresse,
            'panier': [],
            'type': 'recharge'
        }
        
        await query.edit_message_text(texte)
        return
    
    # ===== PORTEFEUILLE =====
    if data == 'portefeuille':
        uid = str(query.from_user.id)
        solde = shop.users[uid].get('solde', 0) if uid in shop.users else 0
        
        texte = f"""
💰 PORTEFEUILLE

💶 Solde: {solde:.2f}€
"""
        
        keyboard = [
            [InlineKeyboardButton("📥 RECHARGER 50€", callback_data='recharger')],
            [InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')]
        ]
        
        await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # ===== ADMIN =====
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
        r = shop.scanner()
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

# =========================
# FONCTIONS MENU
# =========================

async def menu_fiche(query, context):
    stats = shop.stats()
    
    keyboard = [
        [InlineKeyboardButton("🏦 PAR BANQUE", callback_data='fiche_banque'),
         InlineKeyboardButton("🌍 PAR RÉGION", callback_data='fiche_region')],
        [InlineKeyboardButton("🎯 RECHERCHE MIXTE", callback_data='fiche_mixte')],
        [InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')]
    ]
    
    await query.edit_message_text(
        f"📄 SERVICE FICHE\n\nDisponibles: {stats['dispos']} fiches\n\nChoisissez votre méthode :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def menu_nm(query, context):
    stats = shop.stats()
    ops = [(o, c) for o, c in stats['operateurs'].items() if c >= 1000]
    ops = sorted(ops, key=lambda x: x[1], reverse=True)
    
    keyboard = []
    for o, c in ops[:10]:
        keyboard.append([InlineKeyboardButton(f"📱 {o} ({c})", callback_data=f'operateur_{o}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')])
    
    await query.edit_message_text(
        f"📱 SERVICE NM\n\nDisponibles: {stats['dispos']} numéros\nChoisissez un opérateur :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def menu_ml(query, context):
    stats = shop.stats()
    doms = [(d, c) for d, c in stats['domaines'].items() if c >= 1000]
    doms = sorted(doms, key=lambda x: x[1], reverse=True)
    
    keyboard = []
    for d, c in doms[:10]:
        keyboard.append([InlineKeyboardButton(f"📧 {d} ({c})", callback_data=f'domaine_{d}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='retour_accueil')])
    
    await query.edit_message_text(
        f"📧 SERVICE ML\n\nDisponibles: {stats['dispos']} emails\nChoisissez un domaine :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== FICHE - BANQUES =====

async def fiche_banques(query, context):
    stats = shop.stats()
    banques = [(b, c) for b, c in stats['banques'].items() if c >= 1000]
    banques = sorted(banques, key=lambda x: x[1], reverse=True)
    
    keyboard = []
    for b, c in banques[:10]:
        keyboard.append([InlineKeyboardButton(f"🏦 {b} ({c})", callback_data=f'banque_fiche_{b}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='menu_fiche')])
    
    await query.edit_message_text(
        "🏦 SÉLECTION PAR BANQUE\n\nChoisissez une banque :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def banque_fiche(query, context, banque):
    clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['banque'] == banque]
    
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
        
        await query.edit_message_text(
            f"🏦 {banque}\n\nChoisissez une région :",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        region = regions_triees[0][0]
        context.user_data['type'] = 'fiche'
        context.user_data['banque'] = banque
        context.user_data['region'] = region
        context.user_data['mode'] = 'banque'
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)

# ===== FICHE - RÉGIONS =====

async def fiche_regions(query, context):
    stats = shop.stats()
    regions = [(r, c) for r, c in stats['regions'].items() if c >= 1000]
    regions = sorted(regions, key=lambda x: x[1], reverse=True)
    
    keyboard = []
    for r, c in regions[:10]:
        keyboard.append([InlineKeyboardButton(f"🌍 {r} ({c})", callback_data=f'region_fiche_{r}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='menu_fiche')])
    
    await query.edit_message_text(
        "🌍 SÉLECTION PAR RÉGION\n\nChoisissez une région :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def region_fiche(query, context, region):
    clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['region'] == region]
    
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
        
        await query.edit_message_text(
            f"🌍 {region}\n\nChoisissez une banque :",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        banque = banques_triees[0][0]
        context.user_data['type'] = 'fiche'
        context.user_data['region'] = region
        context.user_data['banque'] = banque
        context.user_data['mode'] = 'region'
        context.user_data['quantite'] = 1000
        await choix_quantite(query, context)

# ===== FICHE - MIXTE =====

async def fiche_mixte_banque(query, context):
    stats = shop.stats()
    banques = [(b, c) for b, c in stats['banques'].items() if c >= 1000]
    banques = sorted(banques, key=lambda x: x[1], reverse=True)
    
    keyboard = []
    for b, c in banques[:10]:
        keyboard.append([InlineKeyboardButton(f"🏦 {b} ({c})", callback_data=f'mixte_banque_{b}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='menu_fiche')])
    
    await query.edit_message_text(
        "🎯 RECHERCHE MIXTE - Étape 1/2\n\nChoisissez une banque :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def fiche_mixte_region(query, context, banque):
    clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['banque'] == banque]
    
    regions = defaultdict(int)
    for c in clients:
        regions[c['region']] += 1
    
    regions_triees = sorted(regions.items(), key=lambda x: x[1], reverse=True)
    
    keyboard = []
    for r, count in regions_triees[:8]:
        keyboard.append([InlineKeyboardButton(f"🌍 {r} ({count})", callback_data=f'mixte_valider_{banque}|{r}')])
    keyboard.append([InlineKeyboardButton("🔙 RETOUR", callback_data='fiche_mixte')])
    
    await query.edit_message_text(
        f"🎯 RECHERCHE MIXTE - Étape 2/2\n\nBanque: {banque}\nChoisissez une région :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== CHOIX QUANTITÉ =====

async def choix_quantite(query, context):
    quantite = context.user_data.get('quantite', 1000)
    type_ = context.user_data.get('type', 'fiche')
    
    if type_ == 'fiche':
        mode = context.user_data.get('mode', 'region')
        banque = context.user_data.get('banque', '')
        region = context.user_data.get('region', '')
        
        if banque and region and region != 'TOUTES':
            clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['banque'] == banque and c['region'] == region]
            nom = f"FICHE - {banque} {region}"
            max_dispo = len(clients)
            retour_callback = f'retour_banque_fiche_{banque}' if mode == 'banque' else f'retour_region_fiche_{region}'
        elif banque and region == 'TOUTES':
            clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['banque'] == banque]
            nom = f"FICHE - {banque} TOUTES RÉGIONS"
            max_dispo = len(clients)
            retour_callback = f'retour_banque_fiche_{banque}'
        elif banque:
            clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['banque'] == banque]
            nom = f"FICHE - {banque}"
            max_dispo = len(clients)
            retour_callback = 'fiche_banque'
        elif region:
            clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['region'] == region]
            nom = f"FICHE - {region}"
            max_dispo = len(clients)
            retour_callback = 'fiche_region'
        else:
            await query.edit_message_text("❌ Erreur de sélection")
            return
    
    elif type_ == 'nm':
        op = context.user_data.get('operateur')
        clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['operateur'] == op]
        nom = f"NM - {op}"
        max_dispo = len(clients)
        retour_callback = 'menu_nm'
    
    else:
        dom = context.user_data.get('domaine')
        clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['domaine'] == dom]
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
            clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['banque'] == banque and c['region'] == region]
            clients = sorted(clients, key=lambda x: x['id'])[:quantite]
            if len(clients) < quantite:
                await query.edit_message_text(f"❌ Stock insuffisant !")
                return
            article = {
                'type': 'fiche',
                'banque': banque,
                'region': region,
                'quantite': quantite,
                'prix': quantite * shop.prix['fiche'],
                'clients': [c['id'] for c in clients]
            }
            nom = f"FICHE - {banque} {region}"
            menu_retour = 'menu_fiche'
        
        elif banque and region == 'TOUTES':
            clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['banque'] == banque]
            clients = sorted(clients, key=lambda x: x['id'])[:quantite]
            if len(clients) < quantite:
                await query.edit_message_text(f"❌ Stock insuffisant !")
                return
            article = {
                'type': 'fiche',
                'banque': banque,
                'region': 'TOUTES',
                'quantite': quantite,
                'prix': quantite * shop.prix['fiche'],
                'clients': [c['id'] for c in clients]
            }
            nom = f"FICHE - {banque} TOUTES RÉGIONS"
            menu_retour = 'menu_fiche'
        
        elif banque:
            clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['banque'] == banque]
            clients = sorted(clients, key=lambda x: x['id'])[:quantite]
            if len(clients) < quantite:
                await query.edit_message_text(f"❌ Stock insuffisant !")
                return
            article = {
                'type': 'fiche',
                'banque': banque,
                'quantite': quantite,
                'prix': quantite * shop.prix['fiche'],
                'clients': [c['id'] for c in clients]
            }
            nom = f"FICHE - {banque}"
            menu_retour = 'menu_fiche'
        
        elif region:
            clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['region'] == region]
            clients = sorted(clients, key=lambda x: x['id'])[:quantite]
            if len(clients) < quantite:
                await query.edit_message_text(f"❌ Stock insuffisant !")
                return
            article = {
                'type': 'fiche',
                'region': region,
                'quantite': quantite,
                'prix': quantite * shop.prix['fiche'],
                'clients': [c['id'] for c in clients]
            }
            nom = f"FICHE - {region}"
            menu_retour = 'menu_fiche'
        
        else:
            await query.edit_message_text("❌ Erreur de sélection")
            return
    
    elif type_ == 'nm':
        op = context.user_data.get('operateur')
        clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['operateur'] == op]
        clients = sorted(clients, key=lambda x: x['id'])[:quantite]
        if len(clients) < quantite:
            await query.edit_message_text(f"❌ Stock insuffisant !")
            return
        article = {
            'type': 'nm',
            'operateur': op,
            'quantite': quantite,
            'prix': quantite * shop.prix['nm'],
            'clients': [c['id'] for c in clients]
        }
        nom = f"NM - {op}"
        menu_retour = 'menu_nm'
    
    else:
        dom = context.user_data.get('domaine')
        clients = [c for c in shop.valides.values() if c['id'] not in shop.utilises and c['domaine'] == dom]
        clients = sorted(clients, key=lambda x: x['id'])[:quantite]
        if len(clients) < quantite:
            await query.edit_message_text(f"❌ Stock insuffisant !")
            return
        article = {
            'type': 'ml',
            'domaine': dom,
            'quantite': quantite,
            'prix': quantite * shop.prix['ml'],
            'clients': [c['id'] for c in clients]
        }
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
    
    await query.edit_message_text(
        f"✅ AJOUTÉ AU PANIER !\n\n📦 {nom}\n📊 {quantite} clients\n💰 {article['prix']:.2f}€",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# GESTION DES MESSAGES (PRIX)
# =========================

async def handle_message(update: Update, context):
    if not is_admin(update):
        return
    
    if 'prix_a_modifier' in context.user_data:
        try:
            nouveau_prix = float(update.message.text)
            service = context.user_data['prix_a_modifier']
            
            shop.prix[service] = nouveau_prix / 1000
            shop.sauver()
            
            del context.user_data['prix_a_modifier']
            
            await update.message.reply_text(
                f"✅ Prix modifié: {service.upper()} = {nouveau_prix:.0f}€/1000"
            )
        except ValueError:
            await update.message.reply_text("❌ Veuillez entrer un nombre valide")

# =========================
# TEST DES APIS AU DÉMARRAGE
# =========================

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
        logger.warning("⚠️ API Solscan indisponible - APIs de secours prêtes")

# =========================
# MAIN
# =========================
def main():
    logger.info("🚀 Démarrage du bot...")

    test_apis()
    shop.scanner()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    verif.set_app(app)
    verif.demarrer()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("✅ Bot prêt - Version Render - Tous les séparateurs")
    app.run_polling()

if __name__ == "__main__":
    main()
