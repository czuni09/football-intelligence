"""
ALL-IN-ONE FOOTBALL INTELLIGENCE DASHBOARD
Egyetlen fájl - minden benne van!

TELEPÍTÉS:
1. Mentsd el ezt a fájlt: app.py
2. pip install streamlit requests beautifulsoup4
3. streamlit run app.py

VAGY:
Streamlit Cloud-ra feltölteni közvetlenül!
"""

import streamlit as st
import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# BACKEND - Intelligence System
# ============================================

class FootballIntelligence:
    """Kompakt intelligence rendszer"""
    
    def __init__(self):
        self.odds_key = os.environ.get("ODDS_API_KEY")
        self.weather_key = os.environ.get("WEATHER_API_KEY", "")
        self.news_key = os.environ.get("NEWS_API_KEY", "")
        
        if not self.odds_key:
            raise ValueError("ODDS_API_KEY hiányzik!")
    
    def get_matches_with_odds(self, sport: str = 'soccer_epl') -> List[Dict]:
        """Meccsek lekérése"""
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
            params = {
                'apiKey': self.odds_key,
                'regions': 'eu',
                'markets': 'h2h',
                'oddsFormat': 'decimal'
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Odds API hiba: {e}")
            return []
    
    def analyze_match(self, match: Dict, target_odds: float = 2.0) -> Optional[Dict]:
        """Meccs elemzése"""
        home = match.get('home_team', 'Unknown')
        away = match.get('away_team', 'Unknown')
        
        bookmakers = match.get('bookmakers', [])
        if not bookmakers:
            return None
        
        best_odds = {'home': 0, 'draw': 0, 'away': 0}
        
        for bookmaker in bookmakers:
            markets = bookmaker.get('markets', [])
            for market in markets:
                if market.get('key') == 'h2h':
                    for outcome in market.get('outcomes', []):
                        name = outcome.get('name')
                        price = outcome.get('price', 0)
                        
                        if name == home:
                            best_odds['home'] = max(best_odds['home'], price)
                        elif name == away:
                            best_odds['away'] = max(best_odds['away'], price)
                        else:
                            best_odds['draw'] = max(best_odds['draw'], price)
        
        # Találjunk 2.00 körüli odds-ot
        picks = []
        for outcome, odd in best_odds.items():
            if 1.80 <= odd <= 2.20:
                # Egyszerű konfidencia számítás
                confidence = 50
                if odd < 2.05:
                    confidence += 10
                if outcome == 'home':
                    confidence += 5
                
                picks.append({
                    'pick': outcome.upper(),
                    'odds': odd,
                    'confidence': min(confidence, 85)
                })
        
        if not picks:
            return None
        
        picks.sort(key=lambda x: abs(x['odds'] - target_odds))
        
        return {
            'match': f"{home} vs {away}",
            'commence_time': match.get('commence_time', 'Unknown'),
            'odds': best_odds,
            'recommendation': picks[0]
        }
    
    def find_best_bets(self, leagues: List[str], target_odds: float = 2.0) -> List[Dict]:
        """Legjobb tippek keresése"""
        all_picks = []
        
        for league in leagues:
            matches = self.get_matches_with_odds(league)
            
            for match in matches[:5]:
                analysis = self.analyze_match(match, target_odds)
                if analysis:
                    all_picks.append(analysis)
        
        all_picks.sort(key=lambda x: x['recommendation']['confidence'], reverse=True)
        return all_picks


# ============================================
# FRONTEND - Streamlit UI
# ============================================

def setup_page():
    """Page config és CSS"""
    st.set_page_config(
        page_title="⚽ Football Intelligence",
        page_icon="⚽",
        layout="wide"
    )
    
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            text-align: center;
            color: #1E88E5;
            margin-bottom: 1rem;
        }
        .match-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 10px;
            color: white;
            margin: 1rem 0;
        }
        .high-conf { background-color: #4CAF50; padding: 0.3rem; border-radius: 5px; color: white; }
        .med-conf { background-color: #FF9800; padding: 0.3rem; border-radius: 5px; color: white; }
        .low-conf { background-color: #f44336; padding: 0.3rem; border-radius: 5px; color: white; }
    </style>
    """, unsafe_allow_html=True)


def check_setup():
    """API kulcsok ellenőrzése"""
    odds_key = os.environ.get("ODDS_API_KEY")
    
    if not odds_key:
        st.error("❌ ODDS_API_KEY hiányzik!")
        st.info("""
        ### Hogyan állítsd be:
        
        **Streamlit Cloud:**
        1. Settings > Secrets
        2. Add hozzá:
        ```
        ODDS_API_KEY = "your_key_here"
        ```
        
        **Lokálisan:**
        1. Hozd létre: `.streamlit/secrets.toml`
        2. Add hozzá ugyanazt
        
        **API kulcs szerzése:**
        - Regisztrálj: https://the-odds-api.com/
        - Ingyenes: 500 request/hó
        """)
        return False
    
    return True


def display_match(analysis: Dict, rank: int):
    """Meccs megjelenítése"""
    rec = analysis['recommendation']
    conf = rec['confidence']
    
    conf_class = "high-conf" if conf >= 75 else "med-conf" if conf >= 60 else "low-conf"
    conf_emoji = "🔥" if conf >= 75 else "⚡" if conf >= 60 else "⚠️"
    
    st.markdown(f"""
    <div class="match-card">
        <h2>#{rank} | {analysis['match']}</h2>
        <p>⏰ {analysis['commence_time']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        st.markdown(f"### 🎯 Ajánlás: **{rec['pick']}**")
        st.markdown(f"### 💰 Odds: **{rec['odds']:.2f}**")
    
    with col2:
        st.markdown(f'<div class="{conf_class}">{conf_emoji} Konfidencia: {conf}%</div>', unsafe_allow_html=True)
    
    with col3:
        if st.button("📊 Odds", key=f"odds_{rank}"):
            st.session_state[f'show_{rank}'] = not st.session_state.get(f'show_{rank}', False)
    
    if st.session_state.get(f'show_{rank}', False):
        odds = analysis['odds']
        o1, o2, o3 = st.columns(3)
        with o1:
            st.metric("🏠 Hazai", f"{odds['home']:.2f}")
        with o2:
            st.metric("🤝 Döntetlen", f"{odds['draw']:.2f}")
        with o3:
            st.metric("✈️ Vendég", f"{odds['away']:.2f}")
    
    st.markdown("---")


def main():
    """Main app"""
    setup_page()
    
    # Header
    st.markdown('<div class="main-header">⚽ FOOTBALL INTELLIGENCE</div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">AI-powered 2.00x odds finder</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Beállítások")
        
        if not check_setup():
            return
        
        st.success("✅ API kulcs OK!")
        
        st.markdown("---")
        st.markdown("### 🏆 Ligák")
        
        leagues_map = {
            '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League': 'soccer_epl',
            '🇪🇸 La Liga': 'soccer_spain_la_liga',
            '🇩🇪 Bundesliga': 'soccer_germany_bundesliga',
            '🇮🇹 Serie A': 'soccer_italy_serie_a',
            '⭐ Champions League': 'soccer_uefa_champs_league'
        }
        
        selected = []
        for name, key in leagues_map.items():
            if st.checkbox(name, value=(key in ['soccer_epl', 'soccer_spain_la_liga'])):
                selected.append(key)
        
        st.markdown("---")
        st.markdown("### 🎯 Cél Odds")
        target = st.slider("Target", 1.5, 3.0, 2.0, 0.1)
        
        st.markdown("---")
        st.caption(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        st.warning("⚠️ Ez NEM fogadási tanács!")
    
    # Main
    if not check_setup():
        return
    
    if st.button("🚀 ELEMZÉS INDÍTÁSA", type="primary", use_container_width=True):
        
        with st.spinner("🔍 Elemzés folyamatban..."):
            try:
                intel = FootballIntelligence()
                results = intel.find_best_bets(selected, target)
                
                if not results:
                    st.warning("😕 Nincs megfelelő lehetőség most. Próbáld később!")
                    return
                
                st.success(f"✅ {len(results)} LEHETŐSÉG TALÁLVA!")
                
                # Stats
                s1, s2, s3 = st.columns(3)
                with s1:
                    st.metric("📊 Meccsek", len(results))
                with s2:
                    avg_conf = sum(r['recommendation']['confidence'] for r in results) / len(results)
                    st.metric("🎯 Átlag konf.", f"{avg_conf:.0f}%")
                with s3:
                    avg_odds = sum(r['recommendation']['odds'] for r in results) / len(results)
                    st.metric("💰 Átlag odds", f"{avg_odds:.2f}")
                
                st.markdown("---")
                st.markdown("## 🏆 TOP AJÁNLÁSOK")
                
                for idx, result in enumerate(results[:5], 1):
                    display_match(result, idx)
                
            except Exception as e:
                st.error(f"❌ Hiba: {str(e)}")
                st.exception(e)
    
    else:
        st.info("""
        ### 🎯 Használat:
        
        1. **Válassz ligákat** (balra)
        2. **Állítsd be** a cél odds-t
        3. **Kattints** az "Elemzés indítása" gombra
        4. **Várd meg** az eredményt (~20-30 mp)
        
        ### 📊 Mit csinál:
        - Valós odds lekérés több bukmékertől
        - 2.00 körüli lehetőségek keresése
        - Konfidencia számítás
        - Top 5 ajánlás
        
        ### ⚠️ FONTOS:
        Ez csak elemzés, NEM garancia!
        Felelősen fogadj!
        """)


if __name__ == "__main__":
    main()