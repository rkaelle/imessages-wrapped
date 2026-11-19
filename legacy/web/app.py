"""
iMessage Wrapped - Streamlit Web Application
Interactive dashboard for exploring your iMessage insights
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import iMessageDatabase
from src.analyzer import MessageAnalyzer
from src.utils import format_number, format_duration

# Page configuration
st.set_page_config(
    page_title="iMessage Wrapped",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; }
    .css-1d391kg { background-color: #1a1a2e; }
    .stMetric { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 15px; border-radius: 10px; border: 1px solid #30304a; }
    .stMetric label { color: #888; font-size: 12px; }
    .stMetric .metric-value { color: #007AFF; }
    h1, h2, h3 { color: #fff !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { background: #1a1a2e; color: #888; border-radius: 8px; padding: 8px 16px; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #007AFF 0%, #00d4ff 100%); color: #fff; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_messages(period: str):
    """Load messages for time period with caching"""
    # Calculate start date based on period
    now = datetime.now()
    
    if period == "Last Year":
        start_date = now - timedelta(days=365)
    elif period == "Last 6 Months":
        start_date = now - timedelta(days=180)
    elif period == "Last Month":
        start_date = now - timedelta(days=30)
    else:  # All Time
        start_date = None
    
    with iMessageDatabase() as db:
        return db.get_messages(start_date=start_date, end_date=now)


@st.cache_data(ttl=300)
def get_cached_stats(_analyzer):
    """Cache expensive summary stats"""
    return _analyzer.get_summary_stats()


@st.cache_data(ttl=300)
def get_cached_personality(_analyzer):
    """Cache personality analysis"""
    return _analyzer.get_messaging_personality()


@st.cache_data(ttl=300)
def get_cached_time_patterns(_analyzer):
    """Cache time patterns"""
    return _analyzer.get_time_patterns()


def main():
    # Header
    st.markdown("# 💬 iMessage Wrapped")
    st.markdown("*Your complete texting story, analyzed.*")
    
    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Settings")
        period = st.selectbox("Time Period", ["All Time", "Last Year", "Last 6 Months", "Last Month"])
        st.markdown("---")
        st.markdown("### 🔒 Privacy First")
        st.caption("All analysis is done locally. Your messages never leave your device.")
        
        # Show what period means
        now = datetime.now()
        if period == "Last Year":
            st.caption(f"📅 From {(now - timedelta(days=365)).strftime('%b %d, %Y')}")
        elif period == "Last 6 Months":
            st.caption(f"📅 From {(now - timedelta(days=180)).strftime('%b %d, %Y')}")
        elif period == "Last Month":
            st.caption(f"📅 From {(now - timedelta(days=30)).strftime('%b %d, %Y')}")
    
    # Load and analyze
    try:
        with st.spinner("Loading your messages..."):
            messages_df = load_messages(period)
            analyzer = MessageAnalyzer(messages_df)
        
        # Get key stats upfront (cached)
        stats = analyzer.get_summary_stats()
        
        # Quick Stats Bar
        st.markdown("---")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.metric("📨 Total", format_number(stats['total_messages']))
        with c2:
            st.metric("📤 Sent", format_number(stats['messages_sent']))
        with c3:
            st.metric("📥 Received", format_number(stats['messages_received']))
        with c4:
            st.metric("👥 Contacts", format_number(stats['contacts']))
        with c5:
            st.metric("💬 Groups", format_number(stats['group_chats']))
        with c6:
            ratio = stats['messages_sent'] / stats['messages_received'] if stats['messages_received'] > 0 else 0
            st.metric("⚖️ Ratio", f"{ratio:.2f}")
        
        st.markdown("---")
        
        # Main tabs - condensed and organized
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "🏠 Overview",
            "🔬 Deep Insights", 
            "👥 Relationships",
            "📊 Patterns",
            "🏆 Leaderboards",
            "🎯 Extras"
        ])
        
        # =========================================================================
        # TAB 1: OVERVIEW - Quick summary with personality & highlights
        # =========================================================================
        with tab1:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("👤 Your Texting Profile")
                
                personality = analyzer.get_messaging_personality()
                
                # Personality grid
                p1, p2, p3, p4 = st.columns(4)
                with p1:
                    st.markdown(f"### {personality['time_personality']}")
                    st.caption("Time Style")
                with p2:
                    st.markdown(f"### {personality['emoji_personality']}")
                    st.caption("Emoji Style")
                with p3:
                    st.markdown(f"### {personality['length_personality']}")
                    st.caption("Message Style")
                with p4:
                    st.markdown(f"### {personality['initiation_personality']}")
                    st.caption("Social Style")
                
                st.markdown("---")
                
                # All-time records
                st.subheader("🏅 Records")
                try:
                    records = analyzer.get_all_time_records()
                    r1, r2, r3 = st.columns(3)
                    with r1:
                        if 'busiest_day' in records:
                            st.metric("📈 Busiest Day", f"{records['busiest_day']['count']} msgs")
                            st.caption(records['busiest_day']['date'])
                    with r2:
                        if 'longest_message' in records:
                            st.metric("📝 Longest Msg", f"{records['longest_message']['length']} chars")
                    with r3:
                        if 'total_days_active' in records:
                            st.metric("📅 Days Active", format_number(records['total_days_active']))
                except:
                    pass
                
                # Streak
                try:
                    streak = analyzer.get_longest_streak()
                    if streak['days'] > 0:
                        st.success(f"🔥 **Longest Streak:** {streak['days']} consecutive days")
                except:
                    pass
            
            with col2:
                st.subheader("🏆 Top 5 Contacts")
                contacts = analyzer.get_top_contacts(5)
                if len(contacts) > 0:
                    for idx, row in contacts.iterrows():
                        st.markdown(f"**{idx+1}. {row['display_name']}**")
                        st.caption(f"{format_number(row['total_messages'])} messages")
                
                st.markdown("---")
                
                # Quick emoji stats
                st.subheader("😊 Top Emojis")
                emoji_stats = analyzer.get_emoji_stats(5)
                if emoji_stats['top_emojis']:
                    emoji_display = " ".join([f"{e}" for e, c in emoji_stats['top_emojis'][:5]])
                    st.markdown(f"### {emoji_display}")
                    st.caption(f"{format_number(emoji_stats['total_emojis'])} total")
            
            st.markdown("---")
            
            # Activity heatmap
            st.subheader("🔥 Activity Heatmap")
            try:
                heatmap = analyzer.get_activity_heatmap()
                if not heatmap.empty:
                    st.dataframe(heatmap.astype(int), use_container_width=True)
            except:
                st.info("Not enough data")
        
        # =========================================================================
        # TAB 2: DEEP INSIGHTS - Conversation dynamics (lazy loaded)
        # =========================================================================
        with tab2:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("💬 Conversation Dynamics")
                
                with st.expander("👋 Who Starts Conversations?", expanded=True):
                    try:
                        initiators = analyzer.get_conversation_initiators()
                        if len(initiators) > 0:
                            for idx, row in initiators.head(5).iterrows():
                                you_pct = row['you_initiate_pct']
                                st.markdown(f"**{row['display_name']}**")
                                st.progress(you_pct / 100)
                                st.caption(f"You: {you_pct:.0f}% | Them: {100-you_pct:.0f}%")
                        else:
                            st.info("Not enough data")
                    except:
                        st.info("Not enough data")
                
                with st.expander("🛑 Who Ends Conversations?"):
                    try:
                        enders = analyzer.get_conversation_enders()
                        if len(enders) > 0:
                            for idx, row in enders.head(5).iterrows():
                                you_pct = row['you_end_pct']
                                st.markdown(f"**{row['display_name']}**")
                                st.progress(you_pct / 100)
                                st.caption(f"You: {you_pct:.0f}% | Them: {100-you_pct:.0f}%")
                        else:
                            st.info("Not enough data")
                    except:
                        st.info("Not enough data")
                
                with st.expander("📱 Double-Text Analysis"):
                    try:
                        double_texters = analyzer.get_double_texters()
                        if len(double_texters) > 0:
                            top = double_texters.nlargest(5, 'you_double_texts')
                            for idx, row in top.iterrows():
                                st.markdown(f"**{row['display_name']}**: You {row['you_double_texts']}x | Them {row['they_double_texts']}x")
                        else:
                            st.info("Not enough data")
                    except:
                        st.info("Not enough data")
            
            with col2:
                st.subheader("⚡ Response Analysis")
                
                with st.expander("🏃 Response Speed", expanded=True):
                    try:
                        response_comp = analyzer.get_response_comparison()
                        if len(response_comp) > 0:
                            you_faster = response_comp[response_comp['you_faster'] == True].head(3)
                            they_faster = response_comp[response_comp['you_faster'] == False].head(3)
                            
                            st.markdown("**You're Faster:**")
                            for idx, row in you_faster.iterrows():
                                st.caption(f"• {row['display_name']}")
                            
                            st.markdown("**They're Faster:**")
                            for idx, row in they_faster.iterrows():
                                st.caption(f"• {row['display_name']}")
                        else:
                            st.info("Not enough data")
                    except:
                        st.info("Not enough data")
                
                with st.expander("🌊 Conversation Depth"):
                    try:
                        depth = analyzer.get_conversation_depth()
                        if len(depth) > 0:
                            for idx, row in depth.head(5).iterrows():
                                st.markdown(f"**{row['display_name']}**: {row['avg_exchanges']:.1f} avg exchanges")
                        else:
                            st.info("Not enough data")
                    except:
                        st.info("Not enough data")
                
                with st.expander("🌙 Late Night Texters"):
                    try:
                        late_night = analyzer.get_late_night_messaging()
                        if len(late_night) > 0:
                            for idx, row in late_night.head(5).iterrows():
                                st.markdown(f"**{row['display_name']}**: {row['late_night_messages']} msgs")
                        else:
                            st.info("Not enough data")
                    except:
                        st.info("Not enough data")
            
            st.markdown("---")
            
            # Behavioral Insights
            st.subheader("🧠 Behavioral Insights")
            b1, b2, b3, b4 = st.columns(4)
            
            with b1:
                try:
                    sentence = analyzer.get_average_sentence_length()
                    st.metric("📝 Style", sentence['your_style'])
                    st.caption(f"Avg: {sentence['you_avg_words']:.1f} words")
                except:
                    pass
            
            with b2:
                try:
                    multitask = analyzer.get_multi_tasking_indicator()
                    st.metric("🔀 Multitasker", multitask['multitasker_level'])
                except:
                    pass
            
            with b3:
                try:
                    churn = analyzer.get_contact_churn_rate()
                    st.metric("📈 Net Growth", f"{churn['net_growth']:+.1f}/mo")
                except:
                    pass
            
            with b4:
                try:
                    dead_hours = analyzer.get_dead_hours()
                    if dead_hours:
                        st.metric("😴 Dead Hours", f"{len(dead_hours)}")
                    else:
                        st.metric("😴 Dead Hours", "None")
                except:
                    pass
        
        # =========================================================================
        # TAB 3: RELATIONSHIPS
        # =========================================================================
        with tab3:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("💕 Relationship Health")
                
                with st.expander("🎯 Affinity Scores", expanded=True):
                    try:
                        affinity = analyzer.get_contact_affinity_score()
                        if len(affinity) > 0:
                            for idx, row in affinity.head(6).iterrows():
                                c1, c2 = st.columns([3, 1])
                                with c1:
                                    st.markdown(f"**{row['display_name']}**")
                                    st.progress(row['affinity_score'] / 100)
                                with c2:
                                    st.markdown(f"### {row['grade']}")
                        else:
                            st.info("Not enough data")
                    except:
                        st.info("Not enough data")
                
                with st.expander("📈 Growing Friendships"):
                    try:
                        growing = analyzer.get_growing_friendships()
                        if len(growing) > 0:
                            for idx, row in growing.iterrows():
                                st.markdown(f"🌱 **{row['display_name']}** +{row['change_pct']:.0f}%")
                        else:
                            st.info("None detected")
                    except:
                        st.info("Not enough data")
                
                with st.expander("📉 Fading Friendships"):
                    try:
                        fading = analyzer.get_fading_friendships()
                        if len(fading) > 0:
                            for idx, row in fading.iterrows():
                                st.markdown(f"🍂 **{row['display_name']}** {row['change_pct']:.0f}%")
                        else:
                            st.info("None detected")
                    except:
                        st.info("Not enough data")
            
            with col2:
                st.subheader("🏆 #1 Contact History")
                
                with st.expander("📅 Top Contact Each Year", expanded=True):
                    try:
                        yearly = analyzer.get_top_contact_by_year()
                        if len(yearly) > 0:
                            for idx, row in yearly.iterrows():
                                st.markdown(f"**{int(row['year'])}**: {row['top_contact']}")
                        else:
                            st.info("Not enough data")
                    except:
                        st.info("Not enough data")
                
                with st.expander("🔥 Streak Leaderboard"):
                    try:
                        streaks = analyzer.get_streak_leaderboard()
                        if len(streaks) > 0:
                            for idx, row in streaks.head(5).iterrows():
                                st.markdown(f"🔥 **{row['display_name']}**: {row['longest_streak_days']} days")
                        else:
                            st.info("Not enough data")
                    except:
                        st.info("Not enough data")
                
                with st.expander("🚦 One-Way Conversations"):
                    try:
                        one_way = analyzer.get_one_way_streets()
                        if len(one_way) > 0:
                            for idx, row in one_way.head(5).iterrows():
                                st.markdown(f"**{row['display_name']}** - {row['direction']}")
                        else:
                            st.info("All balanced!")
                    except:
                        st.info("Not enough data")
            
            st.markdown("---")
            
            # Group Chats
            st.subheader("💬 Group Chats")
            g1, g2 = st.columns(2)
            
            with g1:
                with st.expander("🌟 Group MVPs", expanded=True):
                    try:
                        mvps = analyzer.get_group_chat_mvps()
                        if len(mvps) > 0:
                            for idx, row in mvps.head(5).iterrows():
                                st.markdown(f"**{row['chat_name']}**")
                                st.caption(f"MVP: {row['mvp']}")
                        else:
                            st.info("No group data")
                    except:
                        st.info("No group data")
            
            with g2:
                try:
                    groups = analyzer.get_group_chat_stats(5)
                    if len(groups) > 0:
                        for idx, row in groups.iterrows():
                            st.markdown(f"**{row['chat_name']}**")
                            st.caption(f"{format_number(row['total_messages'])} msgs")
                except:
                    pass
        
        # =========================================================================
        # TAB 4: PATTERNS
        # =========================================================================
        with tab4:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("⏰ Time Patterns")
                
                time_patterns = analyzer.get_time_patterns()
                
                t1, t2 = st.columns(2)
                with t1:
                    st.metric("🌟 Peak Hour", f"{time_patterns['most_active_hour']:02d}:00")
                with t2:
                    st.metric("📅 Peak Day", time_patterns['most_active_day'])
                
                st.bar_chart(time_patterns['hourly_data'])
                
                with st.expander("📅 Weekend vs Weekday"):
                    try:
                        weekend = analyzer.get_weekend_vs_weekday()
                        w1, w2 = st.columns(2)
                        with w1:
                            st.metric("Weekday/day", f"{weekend['weekday_per_day']:.0f}")
                        with w2:
                            st.metric("Weekend/day", f"{weekend['weekend_per_day']:.0f}")
                        st.info(f"More active on **{weekend['more_active_on']}s**")
                    except:
                        st.info("Not enough data")
                
                with st.expander("🍂 Seasonal Trends"):
                    try:
                        seasonal = analyzer.get_seasonal_trends()
                        if len(seasonal) > 0:
                            for idx, row in seasonal.iterrows():
                                st.markdown(f"**{row['season']}**: {format_number(row['total_messages'])} msgs")
                        else:
                            st.info("Not enough data")
                    except:
                        st.info("Not enough data")
            
            with col2:
                st.subheader("📝 Language")
                
                with st.expander("😊 Sentiment", expanded=True):
                    try:
                        sentiment = analyzer.get_sentiment_analysis()
                        s1, s2 = st.columns(2)
                        with s1:
                            st.markdown("**You**")
                            st.progress(sentiment['your_positivity_rate'] / 100)
                            st.caption(f"{sentiment['your_positivity_rate']:.0f}% positive")
                        with s2:
                            st.markdown("**Them**")
                            st.progress(sentiment['their_positivity_rate'] / 100)
                            st.caption(f"{sentiment['their_positivity_rate']:.0f}% positive")
                    except:
                        st.info("Not enough data")
                
                with st.expander("🗣️ Slang Usage"):
                    try:
                        slang = analyzer.get_slang_usage()
                        st.metric("Total Slang", format_number(slang['total_slang']))
                        if slang['you_use_most']:
                            st.markdown("**Your favorites:** " + ", ".join([t for t, c in slang['you_use_most'][:5]]))
                    except:
                        st.info("Not enough data")
                
                with st.expander("❓ Punctuation"):
                    try:
                        punct = analyzer.get_punctuation_analysis()
                        st.metric("Questions Asked", format_number(punct['you_questions']))
                        st.metric("Exclamations", format_number(punct['you_multi_exclaim']))
                    except:
                        st.info("Not enough data")
        
        # =========================================================================
        # TAB 5: LEADERBOARDS
        # =========================================================================
        with tab5:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🌟 Hall of Fame")
                
                try:
                    hall_of_fame = analyzer.get_hall_of_fame()
                    if hall_of_fame:
                        for award_name, data in list(hall_of_fame.items())[:6]:
                            a1, a2 = st.columns([1, 3])
                            with a1:
                                st.markdown(f"## {data['icon']}")
                            with a2:
                                st.markdown(f"**{award_name}**")
                                st.markdown(f"### {data['winner']}")
                    else:
                        st.info("Not enough data")
                except:
                    st.info("Not enough data")
                
                st.markdown("---")
                
                # Signature Emojis
                st.subheader("😊 Signature Emojis")
                try:
                    emoji_contact = analyzer.get_emoji_by_contact()
                    if len(emoji_contact) > 0:
                        for idx, row in emoji_contact.head(5).iterrows():
                            st.markdown(f"**{row['display_name']}**: {row['their_signature']} / {row['your_signature']}")
                except:
                    pass
            
            with col2:
                st.subheader("🎮 Achievements")
                
                try:
                    achievements = analyzer.get_achievements()
                    unlocked = [a for a in achievements if a['unlocked']]
                    locked = [a for a in achievements if not a['unlocked']]
                    
                    st.markdown(f"**🔓 Unlocked: {len(unlocked)}/{len(achievements)}**")
                    
                    with st.expander("✅ Unlocked", expanded=True):
                        for ach in unlocked[:6]:
                            st.markdown(f"{ach['icon']} **{ach['name']}**")
                    
                    with st.expander("🔒 Locked"):
                        for ach in locked[:5]:
                            progress = ach['progress'] / ach['target'] if ach['target'] > 0 else 0
                            st.markdown(f"{ach['icon']} **{ach['name']}**")
                            st.progress(progress)
                            st.caption(f"{ach['progress']}/{ach['target']}")
                except:
                    st.info("Not enough data")
                
                st.markdown("---")
                
                # Message Bingo
                st.subheader("🎱 Your Phrases")
                try:
                    bingo = analyzer.get_message_bingo()
                    if bingo:
                        for item in bingo[:6]:
                            st.markdown(f"**{item['phrase']}** ({format_number(item['count'])}x)")
                except:
                    pass
        
        # =========================================================================
        # TAB 6: EXTRAS
        # =========================================================================
        with tab6:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Timeline")
                try:
                    timeline = analyzer.get_message_timeline('month')
                    if len(timeline) > 0:
                        chart_data = timeline.set_index('period')[['sent', 'received']]
                        st.line_chart(chart_data)
                except:
                    st.info("Not enough data")
                
                st.markdown("---")
                
                st.subheader("📱 Text vs Media")
                try:
                    text_media = analyzer.get_text_vs_media_ratio()
                    if len(text_media) > 0:
                        media_heavy = text_media[text_media['style'] == 'Media Heavy'].head(3)
                        text_heavy = text_media[text_media['style'] == 'Text Heavy'].head(3)
                        
                        m1, m2 = st.columns(2)
                        with m1:
                            st.markdown("**📸 Media Heavy**")
                            for idx, row in media_heavy.iterrows():
                                st.caption(row['display_name'])
                        with m2:
                            st.markdown("**📝 Text Heavy**")
                            for idx, row in text_heavy.iterrows():
                                st.caption(row['display_name'])
                except:
                    pass
            
            with col2:
                st.subheader("📋 Monthly Stats")
                try:
                    monthly = analyzer.get_monthly_comparison()
                    if len(monthly) > 0:
                        st.dataframe(
                            monthly.head(12)[['period', 'total_messages', 'unique_contacts']],
                            use_container_width=True,
                            hide_index=True
                        )
                except:
                    pass
                
                st.markdown("---")
                
                st.subheader("📊 Top Words")
                try:
                    words = analyzer.get_top_words(8)
                    if len(words) > 0:
                        for idx, row in words.iterrows():
                            st.markdown(f"**{idx+1}. {row['word']}** ({format_number(row['count'])})")
                except:
                    pass
    
    except Exception as e:
        st.error(f"Error: {e}")
        st.info("Make sure you have access to ~/Library/Messages/chat.db")


if __name__ == "__main__":
    main()
