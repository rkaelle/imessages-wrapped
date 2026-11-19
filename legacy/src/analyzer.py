"""
Analytics Engine for iMessage Wrapped
Calculates all insights from message data
"""

import pandas as pd
import numpy as np
from datetime import datetime
from collections import Counter
from typing import Dict, List, Tuple
from .utils import calculate_response_time, extract_emojis, get_contact_display_name


class MessageAnalyzer:
    """Analyzes iMessage data and generates insights"""

    def __init__(self, messages_df: pd.DataFrame):
        """
        Initialize analyzer with message data

        Args:
            messages_df: DataFrame from iMessageDatabase.get_messages()
        """
        self.messages = messages_df.copy()
        self._preprocess()

    def _preprocess(self):
        """Preprocess messages for analysis"""
        # Add derived columns
        self.messages['hour'] = self.messages['date'].dt.hour
        self.messages['day_of_week'] = self.messages['date'].dt.dayofweek
        self.messages['day_name'] = self.messages['date'].dt.day_name()
        self.messages['month'] = self.messages['date'].dt.to_period('M')
        # Handle NULL text (photos, attachments, reactions)
        self.messages['text'] = self.messages['text'].fillna('')
        
        self.messages['word_count'] = self.messages['text'].str.split().str.len().fillna(0)
        self.messages['char_count'] = self.messages['text'].str.len()

        # Extract emojis
        self.messages['emojis'] = self.messages['text'].apply(extract_emojis)

    def get_summary_stats(self) -> Dict:
        """
        Get overall summary statistics

        Returns:
            Dictionary with summary stats
        """
        total_messages = len(self.messages)
        sent = (self.messages['is_from_me'] == 1).sum()
        received = (self.messages['is_from_me'] == 0).sum()

        return {
            'total_messages': total_messages,
            'messages_sent': sent,
            'messages_received': received,
            'conversations': self.messages['chat_id'].nunique(),
            'contacts': self.messages[self.messages['is_from_me'] == 0]['phone_number'].nunique(),
            'group_chats': self.messages[self.messages['is_group'] == True]['chat_id'].nunique(),
            'date_range': (self.messages['date'].min(), self.messages['date'].max())
        }

    def get_top_contacts(self, limit: int = 10) -> pd.DataFrame:
        """
        Get most messaged contacts (1-on-1 only)

        Args:
            limit: Number of top contacts to return

        Returns:
            DataFrame with contact stats
        """
        # Filter to 1-on-1 conversations only (NOT group chats)
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        
        if len(one_on_one) == 0:
            return pd.DataFrame()
        
        # Get unique contacts
        contacts_data = []
        
        for phone in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == phone]
            
            total = len(contact_msgs)
            sent = len(contact_msgs[contact_msgs['is_from_me'] == 1])
            received = len(contact_msgs[contact_msgs['is_from_me'] == 0])
            
            contacts_data.append({
                'phone_number': phone,
                'total_messages': total,
                'messages_sent': sent,
                'messages_received': received,
                'display_name': get_contact_display_name(phone)
            })
        
        if len(contacts_data) == 0:
            return pd.DataFrame()
        
        contact_stats = pd.DataFrame(contacts_data)
        
        # Sort by total messages
        contact_stats = contact_stats.sort_values('total_messages', ascending=False).head(limit)

        return contact_stats.reset_index(drop=True)

    def get_ghosting_analysis(self, min_messages: int = 20) -> pd.DataFrame:
        """
        Analyze who ghosts you most (low response rate)

        Args:
            min_messages: Minimum messages sent to include in analysis

        Returns:
            DataFrame with ghosting stats
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()

        results = []

        for contact in one_on_one['phone_number'].unique():
            if pd.isna(contact):
                continue

            contact_msgs = one_on_one[one_on_one['phone_number'] == contact].sort_values('date')

            # Count messages you sent
            sent_by_you = (contact_msgs['is_from_me'] == 1).sum()

            if sent_by_you < min_messages:
                continue

            # Count responses (their message within 24h after yours)
            responses = 0
            your_messages = contact_msgs[contact_msgs['is_from_me'] == 1]

            for idx, msg in your_messages.iterrows():
                # Find next message from them within 24 hours
                later_msgs = contact_msgs[
                    (contact_msgs['date'] > msg['date']) &
                    (contact_msgs['date'] <= msg['date'] + pd.Timedelta(hours=24)) &
                    (contact_msgs['is_from_me'] == 0)
                ]

                if len(later_msgs) > 0:
                    responses += 1

            response_rate = (responses / sent_by_you * 100) if sent_by_you > 0 else 0

            results.append({
                'phone_number': contact,
                'display_name': get_contact_display_name(contact),
                'messages_you_sent': sent_by_you,
                'responses': responses,
                'response_rate': response_rate
            })

        df = pd.DataFrame(results)

        if len(df) > 0:
            df = df.sort_values('response_rate', ascending=True).head(10)

        return df.reset_index(drop=True)

    def get_fastest_responders(self, min_messages: int = 20) -> pd.DataFrame:
        """
        Find fastest responders

        Args:
            min_messages: Minimum messages to include

        Returns:
            DataFrame with response time stats
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()

        results = []

        for contact in one_on_one['phone_number'].unique():
            if pd.isna(contact):
                continue

            contact_msgs = one_on_one[one_on_one['phone_number'] == contact].sort_values('date')

            # Get messages from them
            received = (contact_msgs['is_from_me'] == 0).sum()

            if received < min_messages:
                continue

            # Calculate response times
            response_times = []
            your_messages = contact_msgs[contact_msgs['is_from_me'] == 1]

            for idx, msg in your_messages.iterrows():
                # Find next message from them
                later_msgs = contact_msgs[
                    (contact_msgs['date'] > msg['date']) &
                    (contact_msgs['is_from_me'] == 0)
                ]

                if len(later_msgs) > 0:
                    next_msg = later_msgs.iloc[0]
                    resp_time = calculate_response_time(msg['date'], next_msg['date'])
                    if resp_time is not None and resp_time < 1440:  # Less than 1 day
                        response_times.append(resp_time)

            if len(response_times) >= 5:  # Need at least 5 responses
                median_resp = np.median(response_times)

                results.append({
                    'phone_number': contact,
                    'display_name': get_contact_display_name(contact),
                    'median_response_minutes': median_resp,
                    'avg_response_minutes': np.mean(response_times),
                    'response_count': len(response_times)
                })

        df = pd.DataFrame(results)

        if len(df) > 0:
            df = df.sort_values('median_response_minutes', ascending=True).head(10)

        return df.reset_index(drop=True)

    def get_conversation_balance(self, limit: int = 10) -> pd.DataFrame:
        """
        Analyze conversation balance (who initiates more)

        Args:
            limit: Number of contacts to return

        Returns:
            DataFrame with balance stats
        """
        # Filter to 1-on-1 only (exclude group chats)
        one_on_one = self.messages[self.messages['is_group'] == False].copy()

        results = []

        for contact in one_on_one['phone_number'].unique():
            if pd.isna(contact):
                continue

            contact_msgs = one_on_one[one_on_one['phone_number'] == contact]

            sent = int((contact_msgs['is_from_me'] == 1).sum())
            received = int((contact_msgs['is_from_me'] == 0).sum())
            total = sent + received

            # Require actual two-way conversation (both sent and received messages)
            if total < 10 or sent < 3 or received < 3:
                continue

            balance_ratio = sent / received if received > 0 else float('inf')

            results.append({
                'phone_number': contact,
                'display_name': get_contact_display_name(contact),
                'messages_sent': sent,
                'messages_received': received,
                'balance_ratio': balance_ratio,
                'balance_pct': (sent / total * 100) if total > 0 else 50
            })

        df = pd.DataFrame(results)

        if len(df) > 0:
            # Sort by total messages (sent + received) to show most active conversations
            df['total_messages'] = df['messages_sent'] + df['messages_received']
            df = df.sort_values('total_messages', ascending=False).head(limit)
            df = df.drop('total_messages', axis=1)

        return df.reset_index(drop=True)

    def get_time_patterns(self) -> Dict:
        """
        Analyze messaging time patterns

        Returns:
            Dictionary with time pattern stats
        """
        hourly = self.messages.groupby('hour').size()
        daily = self.messages.groupby('day_name').size()
        monthly = self.messages.groupby('month').size()

        # Most active hour
        most_active_hour = hourly.idxmax()

        # Most active day
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_ordered = daily.reindex(day_order, fill_value=0)
        most_active_day = daily_ordered.idxmax()

        return {
            'hourly_distribution': hourly.to_dict(),
            'daily_distribution': daily_ordered.to_dict(),
            'monthly_distribution': monthly.to_dict(),
            'most_active_hour': most_active_hour,
            'most_active_day': most_active_day,
            'hourly_data': hourly,
            'daily_data': daily_ordered
        }

    def get_emoji_stats(self, limit: int = 10) -> Dict:
        """
        Analyze emoji usage

        Args:
            limit: Number of top emojis to return

        Returns:
            Dictionary with emoji stats
        """
        all_emojis = []
        for emoji_list in self.messages['emojis']:
            all_emojis.extend(emoji_list)

        if len(all_emojis) == 0:
            return {
                'total_emojis': 0,
                'unique_emojis': 0,
                'top_emojis': []
            }

        emoji_counts = Counter(all_emojis)
        top_emojis = emoji_counts.most_common(limit)

        return {
            'total_emojis': len(all_emojis),
            'unique_emojis': len(emoji_counts),
            'top_emojis': top_emojis,
            'emoji_rate': len(all_emojis) / len(self.messages) * 100
        }

    def get_message_length_stats(self) -> Dict:
        """
        Analyze message length patterns

        Returns:
            Dictionary with length stats
        """
        return {
            'avg_words': self.messages['word_count'].mean(),
            'avg_chars': self.messages['char_count'].mean(),
            'median_words': self.messages['word_count'].median(),
            'median_chars': self.messages['char_count'].median(),
            'longest_message': self.messages.loc[self.messages['char_count'].idxmax()]['text'][:100] if len(self.messages) > 0 else ''
        }

    def get_group_chat_stats(self, limit: int = 10) -> pd.DataFrame:
        """
        Analyze group chat activity

        Args:
            limit: Number of top groups to return

        Returns:
            DataFrame with group stats
        """
        group_msgs = self.messages[self.messages['is_group'] == True].copy()

        if len(group_msgs) == 0:
            return pd.DataFrame()

        # Get first non-null value for each group
        def first_valid(x):
            return x.dropna().iloc[0] if len(x.dropna()) > 0 else None
        
        # Import database to query participant counts
        from .database import iMessageDatabase
        
        # Group by chat and aggregate
        group_stats = group_msgs.groupby('chat_id').agg({
            'message_id': 'count',
            'is_from_me': lambda x: (x == 1).sum(),
            'chat_name': first_valid
        }).reset_index()

        group_stats.columns = ['chat_id', 'total_messages', 'your_messages', 'chat_name']

        # Get actual participant counts from database
        try:
            import sqlite3
            from pathlib import Path
            db_path = Path.home() / "Library" / "Messages" / "chat.db"
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
            
            # Query chat_handle_join for participant counts
            participant_counts = {}
            for chat_id in group_stats['chat_id']:
                cursor = conn.execute(
                    "SELECT COUNT(DISTINCT handle_id) FROM chat_handle_join WHERE chat_id = ?",
                    (int(chat_id),)
                )
                count = cursor.fetchone()[0]
                participant_counts[chat_id] = count
            
            conn.close()
            
            group_stats['participants'] = group_stats['chat_id'].map(participant_counts).fillna(1).astype(int)
        except Exception:
            # Fallback if database query fails
            group_stats['participants'] = 2

        # Calculate your participation rate
        group_stats['your_participation_pct'] = (
            group_stats['your_messages'] / group_stats['total_messages'] * 100
        )

        # Sort by total messages
        group_stats = group_stats.sort_values('total_messages', ascending=False).head(limit)

        # Clean up group names
        def format_group_name(row):
            name = row['chat_name']
            if pd.isna(name) or name == '' or name.strip() == '':
                return f"Group Chat #{int(row['chat_id'])}"
            return name
        
        group_stats['chat_name'] = group_stats.apply(format_group_name, axis=1)

        return group_stats.reset_index(drop=True)

    def get_busiest_period(self) -> Dict:
        """
        Find busiest messaging period

        Returns:
            Dictionary with busiest period info
        """
        monthly = self.messages.groupby(self.messages['date'].dt.to_period('M')).size()

        if len(monthly) == 0:
            return {}

        busiest_month = monthly.idxmax()
        busiest_count = monthly.max()

        return {
            'busiest_month': str(busiest_month),
            'message_count': int(busiest_count)
        }

    def get_messaging_personality(self) -> Dict:
        """
        Determine messaging personality traits

        Returns:
            Dictionary with personality traits
        """
        # Time of day preference
        hourly = self.messages.groupby('hour').size()
        peak_hour = hourly.idxmax()

        if 0 <= peak_hour < 6:
            time_personality = "Night Owl"
        elif 6 <= peak_hour < 12:
            time_personality = "Early Bird"
        elif 12 <= peak_hour < 17:
            time_personality = "Afternoon Texter"
        elif 17 <= peak_hour < 21:
            time_personality = "Evening Chatter"
        else:
            time_personality = "Night Texter"

        # Message length preference
        avg_words = self.messages['word_count'].mean()
        if avg_words < 5:
            length_personality = "Brief Texter"
        elif avg_words < 15:
            length_personality = "Balanced Texter"
        else:
            length_personality = "Essay Writer"

        # Emoji usage
        emoji_rate = len([e for emojis in self.messages['emojis'] for e in emojis]) / len(self.messages)
        if emoji_rate > 0.5:
            emoji_personality = "Emoji Enthusiast"
        elif emoji_rate > 0.1:
            emoji_personality = "Occasional Emoji User"
        else:
            emoji_personality = "Text Purist"

        # Initiation rate
        sent_ratio = (self.messages['is_from_me'] == 1).sum() / len(self.messages)
        if sent_ratio > 0.6:
            initiation_personality = "Conversation Starter"
        elif sent_ratio > 0.4:
            initiation_personality = "Balanced Conversationalist"
        else:
            initiation_personality = "Reactive Responder"

        return {
            'time_personality': time_personality,
            'length_personality': length_personality,
            'emoji_personality': emoji_personality,
            'initiation_personality': initiation_personality,
            'peak_hour': peak_hour
        }

    def get_activity_heatmap(self) -> pd.DataFrame:
        """
        Get message activity data for heatmap visualization
        
        Returns:
            DataFrame with hour, day, and message counts
        """
        # Create hour and day columns
        heatmap_data = self.messages.copy()
        heatmap_data['hour'] = heatmap_data['date'].dt.hour
        heatmap_data['day_name'] = heatmap_data['date'].dt.day_name()
        
        # Group by hour and day
        activity = heatmap_data.groupby(['day_name', 'hour']).size().reset_index(name='messages')
        
        # Pivot for heatmap format
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_pivot = activity.pivot(index='day_name', columns='hour', values='messages').fillna(0)
        heatmap_pivot = heatmap_pivot.reindex(day_order)
        
        return heatmap_pivot

    def get_message_timeline(self, granularity: str = 'month') -> pd.DataFrame:
        """
        Get message count timeline
        
        Args:
            granularity: 'day', 'week', or 'month'
            
        Returns:
            DataFrame with date and message counts
        """
        timeline = self.messages.copy()
        
        if granularity == 'day':
            timeline['period'] = timeline['date'].dt.date
        elif granularity == 'week':
            timeline['period'] = timeline['date'].dt.to_period('W').astype(str)
        else:  # month
            timeline['period'] = timeline['date'].dt.to_period('M').astype(str)
        
        # Count messages per period
        counts = timeline.groupby('period').size().reset_index(name='messages')
        
        # Separate sent vs received
        sent = timeline[timeline['is_from_me'] == 1].groupby('period').size()
        received = timeline[timeline['is_from_me'] == 0].groupby('period').size()
        
        counts['sent'] = counts['period'].map(sent).fillna(0)
        counts['received'] = counts['period'].map(received).fillna(0)
        
        return counts

    def get_top_contacts_chart_data(self, limit: int = 10) -> pd.DataFrame:
        """
        Get data for top contacts bar chart
        
        Args:
            limit: Number of contacts to return
            
        Returns:
            DataFrame formatted for charting
        """
        contacts = self.get_top_contacts(limit)
        
        if len(contacts) == 0:
            return pd.DataFrame()
        
        # Format for charting
        chart_data = contacts[['display_name', 'messages_sent', 'messages_received']].copy()
        chart_data.columns = ['Contact', 'Sent', 'Received']
        
        return chart_data

    def get_longest_streak(self) -> dict:
        """
        Find longest messaging streak (consecutive days)
        
        Returns:
            Dictionary with streak information
        """
        # Group messages by date
        dates = self.messages['date'].dt.date.unique()
        dates = sorted(dates)
        
        if len(dates) == 0:
            return {'days': 0, 'start_date': None, 'end_date': None}
        
        max_streak = 1
        current_streak = 1
        max_start = dates[0]
        max_end = dates[0]
        current_start = dates[0]
        
        for i in range(1, len(dates)):
            # Check if consecutive day
            if (dates[i] - dates[i-1]).days == 1:
                current_streak += 1
            else:
                # Streak broken
                if current_streak > max_streak:
                    max_streak = current_streak
                    max_start = current_start
                    max_end = dates[i-1]
                current_streak = 1
                current_start = dates[i]
        
        # Check final streak
        if current_streak > max_streak:
            max_streak = current_streak
            max_start = current_start
            max_end = dates[-1]
        
        return {
            'days': max_streak,
            'start_date': max_start,
            'end_date': max_end
        }

    def get_response_time_distribution(self, bins: int = 10) -> pd.DataFrame:
        """
        Get distribution of response times
        
        Args:
            bins: Number of bins for distribution
            
        Returns:
            DataFrame with response time ranges and counts
        """
        response_times = []
        
        # Sort messages by date
        sorted_msgs = self.messages.sort_values('date')
        
        # For each pair of consecutive messages
        for i in range(len(sorted_msgs) - 1):
            curr = sorted_msgs.iloc[i]
            next_msg = sorted_msgs.iloc[i + 1]
            
            # Check if they're from different people (response)
            if curr['is_from_me'] != next_msg['is_from_me']:
                time_diff = (next_msg['date'] - curr['date']).total_seconds() / 60  # minutes
                if 0 < time_diff < 1440:  # Within 24 hours
                    response_times.append(time_diff)
        
        if len(response_times) == 0:
            return pd.DataFrame()
        
        # Create distribution
        import numpy as np
        counts, bin_edges = np.histogram(response_times, bins=bins)
        
        # Format bins
        bin_labels = []
        for i in range(len(bin_edges) - 1):
            if bin_edges[i+1] < 60:
                bin_labels.append(f"{int(bin_edges[i])}-{int(bin_edges[i+1])}m")
            else:
                bin_labels.append(f"{bin_edges[i]/60:.1f}-{bin_edges[i+1]/60:.1f}h")
        
        return pd.DataFrame({
            'range': bin_labels,
            'count': counts
        })

    def get_top_words(self, limit: int = 20, min_length: int = 3) -> pd.DataFrame:
        """
        Get most frequently used words
        
        Args:
            limit: Number of top words to return
            min_length: Minimum word length to include
            
        Returns:
            DataFrame with words and counts
        """
        # Common stop words to filter out
        stop_words = {'the', 'and', 'for', 'you', 'that', 'this', 'with', 'are', 'was', 
                     'but', 'not', 'have', 'from', 'they', 'been', 'has', 'will', 'what',
                     'can', 'out', 'when', 'there', 'all', 'your', 'just', 'like', 'dont',
                     'its', 'get', 'know', 'got', 'going', 'yeah', 'okay', 'really'}
        
        # Get all words from text messages
        all_words = []
        for text in self.messages['text'].dropna():
            if text and len(text.strip()) > 0:
                words = text.lower().split()
                # Remove punctuation from words
                cleaned = [w.strip('.,!?;:()[]{}"\'\\') for w in words 
                          if len(w) >= min_length and w.lower() not in stop_words]
                all_words.extend(cleaned)
        
        if len(all_words) == 0:
            return pd.DataFrame()
        
        # Count frequencies
        word_counts = Counter(all_words)
        
        top_words = pd.DataFrame(word_counts.most_common(limit), columns=['word', 'count'])
        return top_words

    def get_top_emojis(self, limit: int = 20) -> pd.DataFrame:
        """
        Get most frequently used emojis
        
        Args:
            limit: Number of top emojis to return
            
        Returns:
            DataFrame with emojis and counts
        """
        # Flatten all emoji lists
        all_emojis = []
        for emoji_list in self.messages['emojis'].dropna():
            if emoji_list:
                all_emojis.extend(emoji_list)
        
        if len(all_emojis) == 0:
            return pd.DataFrame()
        
        emoji_counts = Counter(all_emojis)
        top_emojis = pd.DataFrame(emoji_counts.most_common(limit), columns=['emoji', 'count'])
        return top_emojis

    def get_sent_vs_received_words(self, limit: int = 10) -> dict:
        """
        Compare most used words in sent vs received messages
        
        Args:
            limit: Number of top words for each category
            
        Returns:
            Dictionary with sent and received top words
        """
        stop_words = {'the', 'and', 'for', 'you', 'that', 'this', 'with', 'are', 'was'}
        
        sent_words = []
        received_words = []
        
        sent_msgs = self.messages[self.messages['is_from_me'] == 1]
        received_msgs = self.messages[self.messages['is_from_me'] == 0]
        
        # Process sent messages
        for text in sent_msgs['text'].dropna():
            if text and len(text.strip()) > 0:
                words = text.lower().split()
                sent_words.extend([w.strip('.,!?;:') for w in words 
                                 if len(w) >= 3 and w.lower() not in stop_words])
        
        # Process received messages
        for text in received_msgs['text'].dropna():
            if text and len(text.strip()) > 0:
                words = text.lower().split()
                received_words.extend([w.strip('.,!?;:') for w in words 
                                     if len(w) >= 3 and w.lower() not in stop_words])
        
        sent_top = Counter(sent_words).most_common(limit) if sent_words else []
        received_top = Counter(received_words).most_common(limit) if received_words else []
        
        return {
            'sent': pd.DataFrame(sent_top, columns=['word', 'count']) if sent_top else pd.DataFrame(),
            'received': pd.DataFrame(received_top, columns=['word', 'count']) if received_top else pd.DataFrame()
        }

    def get_typing_patterns(self) -> dict:
        """
        Analyze typing patterns (message length distribution)
        
        Returns:
            Dictionary with typing pattern statistics
        """
        # Filter messages with text
        text_msgs = self.messages[self.messages['char_count'] > 0].copy()
        
        if len(text_msgs) == 0:
            return {
                'avg_length': 0,
                'short_messages': 0,
                'medium_messages': 0,
                'long_messages': 0,
                'style': 'No text messages'
           }
        
        total = len(text_msgs)
        short = len(text_msgs[text_msgs['char_count'] < 20])  # < 20 chars
        medium = len(text_msgs[(text_msgs['char_count'] >= 20) & (text_msgs['char_count'] < 100)])
        long = len(text_msgs[text_msgs['char_count'] >= 100])
        
        # Determine style
        if short / total > 0.7:
            style = "Quick Texter"
        elif long / total > 0.3:
            style = "Essay Writer"
        else:
            style = "Balanced"
        
        return {
            'avg_length': text_msgs['char_count'].mean(),
            'short_messages': short,
            'short_pct': (short / total * 100),
            'medium_messages': medium,
            'medium_pct': (medium / total * 100),
            'long_messages': long,
            'long_pct': (long / total * 100),
            'style': style
        }

    def get_message_reactions(self) -> pd.DataFrame:
        """
        Get reaction statistics (if available in database)
        
        Returns:
            DataFrame with reaction counts
        """
        # Check for reactions in text (simplified - reactions are stored differently)
        # This is a placeholder - actual implementation would need to query associated_message_type
        return pd.DataFrame({
            'reaction': ['❤️', '👍', '😂', '!', '?'],
            'count': [0, 0, 0, 0, 0]
        })

    # =========================================================================
    # ADVANCED ANALYTICS - CONVERSATION DYNAMICS
    # =========================================================================

    def get_conversation_initiators(self, gap_hours: int = 6) -> pd.DataFrame:
        """
        Analyze who starts conversations (first message after N+ hour gap)
        
        Args:
            gap_hours: Minimum gap to consider a new conversation
            
        Returns:
            DataFrame with initiation stats per contact
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact].sort_values('date')
            
            if len(contact_msgs) < 5:
                continue
            
            # Find conversation starters (first message after gap)
            you_started = 0
            they_started = 0
            
            prev_time = None
            for idx, msg in contact_msgs.iterrows():
                if prev_time is None:
                    # First message in history
                    if msg['is_from_me'] == 1:
                        you_started += 1
                    else:
                        they_started += 1
                else:
                    gap = (msg['date'] - prev_time).total_seconds() / 3600
                    if gap >= gap_hours:
                        if msg['is_from_me'] == 1:
                            you_started += 1
                        else:
                            they_started += 1
                            
                prev_time = msg['date']
            
            total_convos = you_started + they_started
            if total_convos >= 3:
                results.append({
                    'phone_number': contact,
                    'display_name': get_contact_display_name(contact),
                    'you_started': you_started,
                    'they_started': they_started,
                    'total_conversations': total_convos,
                    'you_initiate_pct': (you_started / total_convos * 100) if total_convos > 0 else 50
                })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('total_conversations', ascending=False)
        return df.reset_index(drop=True)

    def get_double_texters(self, min_messages: int = 20) -> pd.DataFrame:
        """
        Analyze who double-texts (sends multiple messages before getting a response)
        
        Args:
            min_messages: Minimum messages to include contact
            
        Returns:
            DataFrame with double-text stats
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact].sort_values('date')
            
            if len(contact_msgs) < min_messages:
                continue
            
            # Count consecutive messages
            you_doubles = 0
            they_doubles = 0
            you_max_streak = 1
            they_max_streak = 1
            current_streak = 1
            
            prev_from_me = None
            for idx, msg in contact_msgs.iterrows():
                from_me = msg['is_from_me'] == 1
                
                if prev_from_me is not None:
                    if from_me == prev_from_me:
                        current_streak += 1
                        if current_streak == 2:  # At least 2 in a row
                            if from_me:
                                you_doubles += 1
                            else:
                                they_doubles += 1
                        if from_me:
                            you_max_streak = max(you_max_streak, current_streak)
                        else:
                            they_max_streak = max(they_max_streak, current_streak)
                    else:
                        current_streak = 1
                
                prev_from_me = from_me
            
            total_msgs = len(contact_msgs)
            results.append({
                'phone_number': contact,
                'display_name': get_contact_display_name(contact),
                'you_double_texts': you_doubles,
                'they_double_texts': they_doubles,
                'you_max_streak': you_max_streak,
                'they_max_streak': they_max_streak,
                'your_double_rate': (you_doubles / total_msgs * 100) if total_msgs > 0 else 0
            })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('you_double_texts', ascending=False).head(15)
        return df.reset_index(drop=True)

    def get_late_night_messaging(self) -> pd.DataFrame:
        """
        Analyze late night messaging patterns (midnight-5am)
        
        Returns:
            DataFrame with late night stats per contact
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        
        # Define late night as 00:00-05:00
        late_night = one_on_one[one_on_one['hour'].isin([0, 1, 2, 3, 4])].copy()
        
        if len(late_night) == 0:
            return pd.DataFrame()
        
        results = []
        for contact in late_night['phone_number'].dropna().unique():
            contact_late = late_night[late_night['phone_number'] == contact]
            contact_all = one_on_one[one_on_one['phone_number'] == contact]
            
            late_count = len(contact_late)
            total_count = len(contact_all)
            
            if late_count >= 5:
                results.append({
                    'phone_number': contact,
                    'display_name': get_contact_display_name(contact),
                    'late_night_messages': late_count,
                    'total_messages': total_count,
                    'late_night_pct': (late_count / total_count * 100) if total_count > 0 else 0,
                    'peak_late_hour': contact_late['hour'].mode().iloc[0] if len(contact_late) > 0 else 0
                })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('late_night_messages', ascending=False).head(10)
        return df.reset_index(drop=True)

    def get_response_comparison(self, min_responses: int = 10) -> pd.DataFrame:
        """
        Compare your response time vs their response time per contact
        
        Args:
            min_responses: Minimum responses needed
            
        Returns:
            DataFrame with bidirectional response time comparison
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact].sort_values('date')
            
            if len(contact_msgs) < 20:
                continue
            
            your_response_times = []
            their_response_times = []
            
            prev_msg = None
            for idx, msg in contact_msgs.iterrows():
                if prev_msg is not None:
                    # If sender changed, this is a response
                    if msg['is_from_me'] != prev_msg['is_from_me']:
                        time_diff = (msg['date'] - prev_msg['date']).total_seconds() / 60
                        
                        # Filter reasonable response times (< 24 hours)
                        if 0 < time_diff < 1440:
                            if msg['is_from_me'] == 1:
                                your_response_times.append(time_diff)
                            else:
                                their_response_times.append(time_diff)
                
                prev_msg = msg
            
            if len(your_response_times) >= min_responses and len(their_response_times) >= min_responses:
                your_median = np.median(your_response_times)
                their_median = np.median(their_response_times)
                
                results.append({
                    'phone_number': contact,
                    'display_name': get_contact_display_name(contact),
                    'your_median_mins': your_median,
                    'their_median_mins': their_median,
                    'difference_mins': their_median - your_median,
                    'you_faster': your_median < their_median,
                    'speed_ratio': their_median / your_median if your_median > 0 else float('inf')
                })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('difference_mins', ascending=True)
        return df.reset_index(drop=True)

    def get_conversation_depth(self, timeout_hours: float = 2.0) -> pd.DataFrame:
        """
        Measure conversation depth (back-and-forth exchanges before timeout)
        
        Args:
            timeout_hours: Hours of silence to end a conversation
            
        Returns:
            DataFrame with conversation depth stats
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact].sort_values('date')
            
            if len(contact_msgs) < 20:
                continue
            
            conversations = []
            current_exchanges = 0
            prev_from_me = None
            prev_time = None
            
            for idx, msg in contact_msgs.iterrows():
                # Check for conversation timeout
                if prev_time is not None:
                    gap = (msg['date'] - prev_time).total_seconds() / 3600
                    if gap >= timeout_hours:
                        if current_exchanges > 0:
                            conversations.append(current_exchanges)
                        current_exchanges = 0
                        prev_from_me = None
                
                # Count exchanges (sender switches)
                from_me = msg['is_from_me'] == 1
                if prev_from_me is not None and from_me != prev_from_me:
                    current_exchanges += 1
                
                prev_from_me = from_me
                prev_time = msg['date']
            
            # Don't forget last conversation
            if current_exchanges > 0:
                conversations.append(current_exchanges)
            
            if len(conversations) >= 3:
                results.append({
                    'phone_number': contact,
                    'display_name': get_contact_display_name(contact),
                    'avg_exchanges': np.mean(conversations),
                    'max_exchanges': max(conversations),
                    'total_conversations': len(conversations),
                    'depth_score': np.mean(conversations) * np.log(len(conversations) + 1)
                })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('depth_score', ascending=False).head(15)
        return df.reset_index(drop=True)

    # =========================================================================
    # ADVANCED ANALYTICS - LANGUAGE & TEXT ANALYSIS
    # =========================================================================

    def get_punctuation_analysis(self) -> dict:
        """
        Analyze question and exclamation usage
        
        Returns:
            Dictionary with punctuation stats
        """
        text_msgs = self.messages[self.messages['text'].str.len() > 0].copy()
        
        if len(text_msgs) == 0:
            return {'questions': 0, 'exclamations': 0, 'caps': 0}
        
        sent = text_msgs[text_msgs['is_from_me'] == 1]['text']
        received = text_msgs[text_msgs['is_from_me'] == 0]['text']
        
        def count_pattern(series, pattern):
            return series.str.contains(pattern, regex=True, na=False).sum()
        
        def count_caps(series):
            # Messages that are mostly CAPS (>50% uppercase)
            count = 0
            for text in series.dropna():
                if len(text) >= 5:
                    upper_ratio = sum(1 for c in text if c.isupper()) / len(text)
                    if upper_ratio > 0.5:
                        count += 1
            return count
        
        return {
            'you_questions': count_pattern(sent, r'\?'),
            'they_questions': count_pattern(received, r'\?'),
            'you_exclamations': count_pattern(sent, r'!'),
            'they_exclamations': count_pattern(received, r'!'),
            'you_multi_exclaim': count_pattern(sent, r'!!+'),
            'they_multi_exclaim': count_pattern(received, r'!!+'),
            'you_caps': count_caps(sent),
            'they_caps': count_caps(received),
            'total_questions': count_pattern(text_msgs['text'], r'\?'),
            'total_exclamations': count_pattern(text_msgs['text'], r'!')
        }

    def get_vocabulary_diversity(self, min_messages: int = 50) -> pd.DataFrame:
        """
        Analyze vocabulary diversity per contact (lexical richness)
        
        Args:
            min_messages: Minimum messages with text
            
        Returns:
            DataFrame with vocabulary stats
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact]
            texts = contact_msgs[contact_msgs['text'].str.len() > 0]['text']
            
            if len(texts) < min_messages:
                continue
            
            # Collect all words
            all_words = []
            for text in texts.dropna():
                words = text.lower().split()
                cleaned = [w.strip('.,!?;:()[]{}"\'\\/') for w in words if len(w) >= 2]
                all_words.extend(cleaned)
            
            if len(all_words) < 100:
                continue
            
            unique_words = len(set(all_words))
            total_words = len(all_words)
            
            # Type-Token Ratio (TTR) - lexical diversity metric
            ttr = unique_words / total_words if total_words > 0 else 0
            
            results.append({
                'phone_number': contact,
                'display_name': get_contact_display_name(contact),
                'unique_words': unique_words,
                'total_words': total_words,
                'vocabulary_diversity': ttr,
                'diversity_pct': ttr * 100
            })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('vocabulary_diversity', ascending=False)
        return df.reset_index(drop=True)

    def get_slang_usage(self) -> dict:
        """
        Track common texting abbreviations and slang
        
        Returns:
            Dictionary with slang usage counts
        """
        # Common texting abbreviations
        slang_terms = {
            'lol': 0, 'lmao': 0, 'omg': 0, 'tbh': 0, 'imo': 0,
            'btw': 0, 'idk': 0, 'nvm': 0, 'brb': 0, 'gtg': 0,
            'smh': 0, 'ikr': 0, 'rn': 0, 'irl': 0, 'fyi': 0,
            'wyd': 0, 'hbu': 0, 'ngl': 0, 'fr': 0, 'ong': 0,
            'haha': 0, 'hahaha': 0, 'ok': 0, 'okay': 0, 'k': 0,
            'yea': 0, 'yeah': 0, 'yep': 0, 'nope': 0, 'ya': 0
        }
        
        sent_counts = {term: 0 for term in slang_terms}
        received_counts = {term: 0 for term in slang_terms}
        
        for idx, msg in self.messages.iterrows():
            text = msg['text']
            if not text or len(text.strip()) == 0:
                continue
            
            words = text.lower().split()
            words_cleaned = [w.strip('.,!?;:()[]{}"\'\\/') for w in words]
            
            for term in slang_terms:
                if term in words_cleaned:
                    count = words_cleaned.count(term)
                    slang_terms[term] += count
                    if msg['is_from_me'] == 1:
                        sent_counts[term] += count
                    else:
                        received_counts[term] += count
        
        # Sort by usage
        sorted_slang = sorted(slang_terms.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'overall': dict(sorted_slang[:15]),
            'you_use_most': sorted(sent_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'they_use_most': sorted(received_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'total_slang': sum(slang_terms.values())
        }

    def get_link_analysis(self) -> dict:
        """
        Analyze shared URLs/links
        
        Returns:
            Dictionary with link stats
        """
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        
        sent_links = []
        received_links = []
        
        for idx, msg in self.messages.iterrows():
            text = msg['text']
            if not text:
                continue
            
            urls = re.findall(url_pattern, text)
            if urls:
                if msg['is_from_me'] == 1:
                    sent_links.extend(urls)
                else:
                    received_links.extend(urls)
        
        # Extract domains
        def extract_domain(url):
            try:
                from urllib.parse import urlparse
                return urlparse(url).netloc.replace('www.', '')
            except:
                return 'unknown'
        
        sent_domains = Counter([extract_domain(u) for u in sent_links])
        received_domains = Counter([extract_domain(u) for u in received_links])
        
        return {
            'total_links': len(sent_links) + len(received_links),
            'you_sent': len(sent_links),
            'they_sent': len(received_links),
            'your_top_domains': sent_domains.most_common(10),
            'their_top_domains': received_domains.most_common(10)
        }

    def get_sentiment_analysis(self) -> dict:
        """
        Basic sentiment scoring using positive/negative word lists
        
        Returns:
            Dictionary with sentiment stats
        """
        positive_words = {
            'love', 'great', 'awesome', 'amazing', 'wonderful', 'fantastic',
            'happy', 'excited', 'glad', 'good', 'nice', 'perfect', 'excellent',
            'beautiful', 'best', 'thanks', 'thank', 'appreciate', 'fun', 'enjoy',
            'cool', 'sweet', 'lovely', 'brilliant', 'superb', 'incredible'
        }
        
        negative_words = {
            'hate', 'bad', 'awful', 'terrible', 'horrible', 'worst',
            'sad', 'angry', 'upset', 'annoyed', 'frustrated', 'disappointed',
            'boring', 'stupid', 'dumb', 'ugly', 'wrong', 'fail', 'sucks',
            'ugh', 'damn', 'crap', 'annoying', 'sorry', 'unfortunately'
        }
        
        you_positive = 0
        you_negative = 0
        they_positive = 0
        they_negative = 0
        
        for idx, msg in self.messages.iterrows():
            text = msg['text']
            if not text:
                continue
            
            words = set(text.lower().split())
            pos_count = len(words & positive_words)
            neg_count = len(words & negative_words)
            
            if msg['is_from_me'] == 1:
                you_positive += pos_count
                you_negative += neg_count
            else:
                they_positive += pos_count
                they_negative += neg_count
        
        you_total = you_positive + you_negative
        they_total = they_positive + they_negative
        
        return {
            'you_positive': you_positive,
            'you_negative': you_negative,
            'they_positive': they_positive,
            'they_negative': they_negative,
            'your_positivity_rate': (you_positive / you_total * 100) if you_total > 0 else 50,
            'their_positivity_rate': (they_positive / they_total * 100) if they_total > 0 else 50,
            'your_sentiment_score': you_positive - you_negative,
            'their_sentiment_score': they_positive - they_negative
        }

    # =========================================================================
    # ADVANCED ANALYTICS - TEMPORAL PATTERNS
    # =========================================================================

    def get_response_time_heatmap(self) -> pd.DataFrame:
        """
        Analyze your response speed by hour of day
        
        Returns:
            DataFrame with hourly response time averages
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        one_on_one = one_on_one.sort_values('date')
        
        hourly_response_times = {h: [] for h in range(24)}
        
        prev_msg = None
        for idx, msg in one_on_one.iterrows():
            if prev_msg is not None:
                # Your response to them
                if msg['is_from_me'] == 1 and prev_msg['is_from_me'] == 0:
                    time_diff = (msg['date'] - prev_msg['date']).total_seconds() / 60
                    if 0 < time_diff < 1440:  # Within 24 hours
                        hour = msg['date'].hour
                        hourly_response_times[hour].append(time_diff)
            prev_msg = msg
        
        results = []
        for hour in range(24):
            times = hourly_response_times[hour]
            if times:
                results.append({
                    'hour': hour,
                    'avg_response_mins': np.mean(times),
                    'median_response_mins': np.median(times),
                    'response_count': len(times)
                })
            else:
                results.append({
                    'hour': hour,
                    'avg_response_mins': 0,
                    'median_response_mins': 0,
                    'response_count': 0
                })
        
        return pd.DataFrame(results)

    def get_daily_rhythm(self) -> dict:
        """
        Analyze first and last message times each day
        
        Returns:
            Dictionary with daily rhythm patterns
        """
        msgs = self.messages.copy()
        msgs['date_only'] = msgs['date'].dt.date
        
        first_messages = []
        last_messages = []
        
        for date in msgs['date_only'].unique():
            day_msgs = msgs[msgs['date_only'] == date].sort_values('date')
            if len(day_msgs) > 0:
                first_hour = day_msgs.iloc[0]['date'].hour
                last_hour = day_msgs.iloc[-1]['date'].hour
                first_messages.append(first_hour)
                last_messages.append(last_hour)
        
        return {
            'avg_first_message_hour': np.mean(first_messages) if first_messages else 12,
            'avg_last_message_hour': np.mean(last_messages) if last_messages else 20,
            'earliest_first_ever': min(first_messages) if first_messages else 0,
            'latest_last_ever': max(last_messages) if last_messages else 23,
            'active_hours_daily': np.mean([l - f for f, l in zip(first_messages, last_messages)]) if first_messages else 8,
            'days_analyzed': len(first_messages)
        }

    def get_weekend_vs_weekday(self) -> dict:
        """
        Compare messaging patterns on weekends vs weekdays
        
        Returns:
            Dictionary with weekend/weekday comparison
        """
        msgs = self.messages.copy()
        
        # 5 = Saturday, 6 = Sunday
        weekend = msgs[msgs['day_of_week'].isin([5, 6])]
        weekday = msgs[~msgs['day_of_week'].isin([5, 6])]
        
        def analyze_subset(df):
            if len(df) == 0:
                return {'count': 0, 'avg_hour': 12, 'avg_length': 0}
            return {
                'count': len(df),
                'avg_hour': df['hour'].mean(),
                'avg_length': df['char_count'].mean(),
                'emoji_rate': len([e for emojis in df['emojis'] for e in emojis]) / len(df) if len(df) > 0 else 0
            }
        
        weekend_stats = analyze_subset(weekend)
        weekday_stats = analyze_subset(weekday)
        
        # Normalize to per-day basis (5 weekdays vs 2 weekend days)
        weekend_per_day = weekend_stats['count'] / 2 if weekend_stats['count'] > 0 else 0
        weekday_per_day = weekday_stats['count'] / 5 if weekday_stats['count'] > 0 else 0
        
        return {
            'weekend_total': weekend_stats['count'],
            'weekday_total': weekday_stats['count'],
            'weekend_per_day': weekend_per_day,
            'weekday_per_day': weekday_per_day,
            'weekend_avg_hour': weekend_stats['avg_hour'],
            'weekday_avg_hour': weekday_stats['avg_hour'],
            'more_active_on': 'Weekend' if weekend_per_day > weekday_per_day else 'Weekday',
            'difference_pct': abs(weekend_per_day - weekday_per_day) / max(weekend_per_day, weekday_per_day, 1) * 100
        }

    def get_monthly_comparison(self) -> pd.DataFrame:
        """
        Compare messaging patterns across months
        
        Returns:
            DataFrame with monthly stats
        """
        msgs = self.messages.copy()
        msgs['year_month'] = msgs['date'].dt.to_period('M')
        
        results = []
        for period in msgs['year_month'].unique():
            month_msgs = msgs[msgs['year_month'] == period]
            
            results.append({
                'period': str(period),
                'total_messages': len(month_msgs),
                'sent': (month_msgs['is_from_me'] == 1).sum(),
                'received': (month_msgs['is_from_me'] == 0).sum(),
                'unique_contacts': month_msgs['phone_number'].nunique(),
                'avg_per_day': len(month_msgs) / period.days_in_month,
                'emoji_rate': len([e for emojis in month_msgs['emojis'] for e in emojis]) / len(month_msgs) * 100 if len(month_msgs) > 0 else 0
            })
        
        df = pd.DataFrame(results)
        return df.sort_values('period', ascending=False)

    # =========================================================================
    # ADVANCED ANALYTICS - RELATIONSHIP EVOLUTION
    # =========================================================================

    def get_relationship_trends(self, window_months: int = 3) -> pd.DataFrame:
        """
        Track how relationships evolve over time
        
        Args:
            window_months: Rolling window for trend calculation
            
        Returns:
            DataFrame with relationship trend data
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact].copy()
            
            if len(contact_msgs) < 20:
                continue
            
            contact_msgs['year_month'] = contact_msgs['date'].dt.to_period('M')
            monthly = contact_msgs.groupby('year_month').size()
            
            if len(monthly) < 4:
                continue
            
            # Calculate trend (recent vs older)
            half_point = len(monthly) // 2
            older_avg = monthly.iloc[:half_point].mean()
            recent_avg = monthly.iloc[half_point:].mean()
            
            # Trend direction
            if recent_avg > older_avg * 1.2:
                trend = 'Growing'
            elif recent_avg < older_avg * 0.8:
                trend = 'Fading'
            else:
                trend = 'Stable'
            
            results.append({
                'phone_number': contact,
                'display_name': get_contact_display_name(contact),
                'older_avg_monthly': older_avg,
                'recent_avg_monthly': recent_avg,
                'trend': trend,
                'change_pct': ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0,
                'months_active': len(monthly)
            })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('change_pct', ascending=False)
        return df.reset_index(drop=True)

    def get_growing_friendships(self, limit: int = 10) -> pd.DataFrame:
        """
        Find friendships with increasing message frequency
        
        Returns:
            DataFrame with growing relationships
        """
        trends = self.get_relationship_trends()
        if len(trends) == 0:
            return pd.DataFrame()
        
        growing = trends[trends['trend'] == 'Growing'].head(limit)
        return growing.reset_index(drop=True)

    def get_fading_friendships(self, limit: int = 10) -> pd.DataFrame:
        """
        Find friendships with decreasing message frequency
        
        Returns:
            DataFrame with fading relationships
        """
        trends = self.get_relationship_trends()
        if len(trends) == 0:
            return pd.DataFrame()
        
        fading = trends[trends['trend'] == 'Fading'].sort_values('change_pct', ascending=True).head(limit)
        return fading.reset_index(drop=True)

    def get_top_contact_by_year(self) -> pd.DataFrame:
        """
        Find the #1 contact for each calendar year
        
        Returns:
            DataFrame with top contact per year
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        one_on_one['year'] = one_on_one['date'].dt.year
        
        results = []
        for year in sorted(one_on_one['year'].unique()):
            year_msgs = one_on_one[one_on_one['year'] == year]
            
            contact_counts = year_msgs.groupby('phone_number').size()
            if len(contact_counts) > 0:
                top_contact = contact_counts.idxmax()
                top_count = contact_counts.max()
                
                results.append({
                    'year': year,
                    'top_contact': get_contact_display_name(top_contact),
                    'phone_number': top_contact,
                    'message_count': top_count,
                    'total_year_msgs': len(year_msgs),
                    'pct_of_year': (top_count / len(year_msgs) * 100) if len(year_msgs) > 0 else 0
                })
        
        return pd.DataFrame(results)

    # =========================================================================
    # ADVANCED ANALYTICS - EMOJI PER CONTACT
    # =========================================================================

    def get_emoji_by_contact(self, min_emojis: int = 10) -> pd.DataFrame:
        """
        Analyze emoji usage per contact
        
        Args:
            min_emojis: Minimum emojis to include
            
        Returns:
            DataFrame with per-contact emoji stats
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact]
            
            # Their emojis
            their_msgs = contact_msgs[contact_msgs['is_from_me'] == 0]
            their_emojis = [e for emojis in their_msgs['emojis'] for e in emojis]
            
            # Your emojis to them
            your_msgs = contact_msgs[contact_msgs['is_from_me'] == 1]
            your_emojis = [e for emojis in your_msgs['emojis'] for e in emojis]
            
            if len(their_emojis) >= min_emojis or len(your_emojis) >= min_emojis:
                their_top = Counter(their_emojis).most_common(3)
                your_top = Counter(your_emojis).most_common(3)
                
                results.append({
                    'phone_number': contact,
                    'display_name': get_contact_display_name(contact),
                    'their_emoji_count': len(their_emojis),
                    'your_emoji_count': len(your_emojis),
                    'their_top_emoji': their_top[0][0] if their_top else '',
                    'your_top_emoji': your_top[0][0] if your_top else '',
                    'their_signature': ' '.join([e[0] for e in their_top]) if their_top else '',
                    'your_signature': ' '.join([e[0] for e in your_top]) if your_top else ''
                })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('their_emoji_count', ascending=False)
        return df.reset_index(drop=True)

    def get_emoji_only_messages(self) -> dict:
        """
        Analyze messages that are ONLY emojis
        
        Returns:
            Dictionary with emoji-only stats
        """
        import re
        
        emoji_pattern = re.compile(
            r'^[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
            r'\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251'
            r'\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\s]+$'
        )
        
        you_emoji_only = 0
        they_emoji_only = 0
        most_common = Counter()
        
        for idx, msg in self.messages.iterrows():
            text = msg['text']
            if text and len(text.strip()) > 0:
                if emoji_pattern.match(text.strip()):
                    if msg['is_from_me'] == 1:
                        you_emoji_only += 1
                    else:
                        they_emoji_only += 1
                    most_common[text.strip()] += 1
        
        total = len(self.messages)
        
        return {
            'you_emoji_only': you_emoji_only,
            'they_emoji_only': they_emoji_only,
            'total_emoji_only': you_emoji_only + they_emoji_only,
            'emoji_only_pct': (you_emoji_only + they_emoji_only) / total * 100 if total > 0 else 0,
            'most_common_emoji_msgs': most_common.most_common(10)
        }

    # =========================================================================
    # ADVANCED ANALYTICS - GAMIFICATION & ACHIEVEMENTS
    # =========================================================================

    def get_streak_leaderboard(self) -> pd.DataFrame:
        """
        Calculate longest messaging streaks per contact
        
        Returns:
            DataFrame with streak data
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact]
            dates = sorted(contact_msgs['date'].dt.date.unique())
            
            if len(dates) < 3:
                continue
            
            # Find longest streak of consecutive days
            max_streak = 1
            current_streak = 1
            
            for i in range(1, len(dates)):
                if (dates[i] - dates[i-1]).days == 1:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1
            
            results.append({
                'phone_number': contact,
                'display_name': get_contact_display_name(contact),
                'longest_streak_days': max_streak,
                'total_days_texted': len(dates),
                'first_message': min(dates),
                'last_message': max(dates)
            })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('longest_streak_days', ascending=False).head(15)
        return df.reset_index(drop=True)

    def get_achievements(self) -> list:
        """
        Calculate messaging achievements/badges
        
        Returns:
            List of achievement dictionaries with unlocked status
        """
        stats = self.get_summary_stats()
        streak = self.get_longest_streak()
        emoji_stats = self.get_emoji_stats()
        personality = self.get_messaging_personality()
        
        achievements = []
        
        # Message Count Achievements
        achievements.append({
            'name': 'Getting Started',
            'description': 'Send your first 100 messages',
            'icon': '🎯',
            'unlocked': stats['total_messages'] >= 100,
            'progress': min(stats['total_messages'], 100),
            'target': 100
        })
        
        achievements.append({
            'name': 'Chatty',
            'description': 'Send 1,000 messages',
            'icon': '💬',
            'unlocked': stats['total_messages'] >= 1000,
            'progress': min(stats['total_messages'], 1000),
            'target': 1000
        })
        
        achievements.append({
            'name': 'Power Texter',
            'description': 'Send 10,000 messages',
            'icon': '⚡',
            'unlocked': stats['total_messages'] >= 10000,
            'progress': min(stats['total_messages'], 10000),
            'target': 10000
        })
        
        achievements.append({
            'name': 'Legendary',
            'description': 'Send 100,000 messages',
            'icon': '🌟',
            'unlocked': stats['total_messages'] >= 100000,
            'progress': min(stats['total_messages'], 100000),
            'target': 100000
        })
        
        # Streak Achievements
        achievements.append({
            'name': 'Week Warrior',
            'description': 'Maintain a 7-day messaging streak',
            'icon': '📅',
            'unlocked': streak['days'] >= 7,
            'progress': min(streak['days'], 7),
            'target': 7
        })
        
        achievements.append({
            'name': 'Monthly Master',
            'description': 'Maintain a 30-day messaging streak',
            'icon': '🔥',
            'unlocked': streak['days'] >= 30,
            'progress': min(streak['days'], 30),
            'target': 30
        })
        
        achievements.append({
            'name': 'Century Club',
            'description': 'Maintain a 100-day messaging streak',
            'icon': '💯',
            'unlocked': streak['days'] >= 100,
            'progress': min(streak['days'], 100),
            'target': 100
        })
        
        # Emoji Achievements
        achievements.append({
            'name': 'Emoji Initiate',
            'description': 'Use 100 different emojis',
            'icon': '😊',
            'unlocked': emoji_stats['unique_emojis'] >= 100,
            'progress': min(emoji_stats['unique_emojis'], 100),
            'target': 100
        })
        
        achievements.append({
            'name': 'Emoji Master',
            'description': 'Use 500 different emojis',
            'icon': '🎨',
            'unlocked': emoji_stats['unique_emojis'] >= 500,
            'progress': min(emoji_stats['unique_emojis'], 500),
            'target': 500
        })
        
        # Social Achievements
        achievements.append({
            'name': 'Social Butterfly',
            'description': 'Message 50 different contacts',
            'icon': '🦋',
            'unlocked': stats['contacts'] >= 50,
            'progress': min(stats['contacts'], 50),
            'target': 50
        })
        
        achievements.append({
            'name': 'Group Enthusiast',
            'description': 'Participate in 10 group chats',
            'icon': '👥',
            'unlocked': stats['group_chats'] >= 10,
            'progress': min(stats['group_chats'], 10),
            'target': 10
        })
        
        # Time-based Achievements
        achievements.append({
            'name': 'Night Owl',
            'description': 'Your peak messaging time is after midnight',
            'icon': '🦉',
            'unlocked': personality['peak_hour'] < 5 or personality['peak_hour'] >= 23,
            'progress': 1 if personality['peak_hour'] < 5 or personality['peak_hour'] >= 23 else 0,
            'target': 1
        })
        
        achievements.append({
            'name': 'Early Bird',
            'description': 'Your peak messaging time is before 8am',
            'icon': '🐦',
            'unlocked': 5 <= personality['peak_hour'] < 8,
            'progress': 1 if 5 <= personality['peak_hour'] < 8 else 0,
            'target': 1
        })
        
        return achievements

    def get_hall_of_fame(self) -> dict:
        """
        Generate a hall of fame with various "awards"
        
        Returns:
            Dictionary with award categories and winners
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        
        awards = {}
        
        # Most Messages Overall
        top_contacts = self.get_top_contacts(1)
        if len(top_contacts) > 0:
            awards['Most Chatted'] = {
                'winner': top_contacts.iloc[0]['display_name'],
                'stat': f"{top_contacts.iloc[0]['total_messages']:,} messages",
                'icon': '🏆'
            }
        
        # Fastest Responder
        fastest = self.get_fastest_responders(1)
        if len(fastest) > 0:
            awards['Speed Demon'] = {
                'winner': fastest.iloc[0]['display_name'],
                'stat': f"{fastest.iloc[0]['median_response_minutes']:.1f} min avg response",
                'icon': '⚡'
            }
        
        # Most Emoji User
        emoji_by_contact = self.get_emoji_by_contact(5)
        if len(emoji_by_contact) > 0:
            awards['Emoji Champion'] = {
                'winner': emoji_by_contact.iloc[0]['display_name'],
                'stat': f"{emoji_by_contact.iloc[0]['their_emoji_count']} emojis sent",
                'icon': '😊'
            }
        
        # Conversation Starter
        initiators = self.get_conversation_initiators()
        if len(initiators) > 0:
            # Find who THEY start most with you
            they_start_most = initiators.sort_values('they_started', ascending=False)
            if len(they_start_most) > 0:
                awards['Always Reaching Out'] = {
                    'winner': they_start_most.iloc[0]['display_name'],
                    'stat': f"Started {they_start_most.iloc[0]['they_started']} conversations",
                    'icon': '👋'
                }
        
        # Late Night Texter
        late_night = self.get_late_night_messaging()
        if len(late_night) > 0:
            awards['Night Owl Friend'] = {
                'winner': late_night.iloc[0]['display_name'],
                'stat': f"{late_night.iloc[0]['late_night_messages']} late night texts",
                'icon': '🌙'
            }
        
        # Longest Streak
        streaks = self.get_streak_leaderboard()
        if len(streaks) > 0:
            awards['Streak Master'] = {
                'winner': streaks.iloc[0]['display_name'],
                'stat': f"{streaks.iloc[0]['longest_streak_days']} day streak",
                'icon': '🔥'
            }
        
        # Growing Friendship
        growing = self.get_growing_friendships(1)
        if len(growing) > 0:
            awards['New Bestie'] = {
                'winner': growing.iloc[0]['display_name'],
                'stat': f"{growing.iloc[0]['change_pct']:.0f}% more messages recently",
                'icon': '📈'
            }
        
        return awards

    def get_comprehensive_personality(self) -> dict:
        """
        Generate a comprehensive personality profile
        
        Returns:
            Dictionary with detailed personality insights
        """
        basic = self.get_messaging_personality()
        sentiment = self.get_sentiment_analysis()
        slang = self.get_slang_usage()
        weekend = self.get_weekend_vs_weekday()
        punctuation = self.get_punctuation_analysis()
        rhythm = self.get_daily_rhythm()
        
        # Calculate personality traits (0-100 scale)
        traits = {}
        
        # Expressiveness (emoji + exclamation usage)
        emoji_rate = len([e for emojis in self.messages['emojis'] for e in emojis]) / max(len(self.messages), 1)
        exclaim_rate = punctuation['you_exclamations'] / max(len(self.messages), 1)
        traits['expressiveness'] = min(100, int((emoji_rate + exclaim_rate) * 200))
        
        # Positivity
        traits['positivity'] = int(sentiment['your_positivity_rate'])
        
        # Question Asker (curiosity)
        question_rate = punctuation['you_questions'] / max(len(self.messages), 1) * 100
        traits['curiosity'] = min(100, int(question_rate * 10))
        
        # Verbosity (average message length)
        avg_length = self.messages['char_count'].mean()
        traits['verbosity'] = min(100, int(avg_length / 2))
        
        # Night Owl vs Early Bird (-50 to 50 scale, mapped to 0-100)
        if rhythm['avg_first_message_hour'] < 9:
            traits['early_bird_score'] = min(100, int((9 - rhythm['avg_first_message_hour']) * 12))
        else:
            traits['early_bird_score'] = max(0, int((18 - rhythm['avg_first_message_hour']) * 6))
        
        # Consistency (messages per day variance)
        msgs_per_day = self.messages.groupby(self.messages['date'].dt.date).size()
        if len(msgs_per_day) > 0:
            consistency = 100 - min(100, int(msgs_per_day.std() / msgs_per_day.mean() * 50))
            traits['consistency'] = max(0, consistency)
        else:
            traits['consistency'] = 50
        
        return {
            'basic_personality': basic,
            'traits': traits,
            'sentiment': sentiment,
            'daily_rhythm': rhythm,
            'weekend_personality': weekend,
            'top_slang': slang['overall'],
            'summary': self._generate_personality_summary(traits, basic, weekend)
        }

    def _generate_personality_summary(self, traits: dict, basic: dict, weekend: dict) -> str:
        """Generate a text summary of personality"""
        parts = []
        
        # Time preference
        parts.append(f"You're a {basic['time_personality']}")
        
        # Expressiveness
        if traits['expressiveness'] > 70:
            parts.append("who loves expressing yourself with emojis and exclamation points")
        elif traits['expressiveness'] < 30:
            parts.append("with a calm, reserved texting style")
        
        # Weekend preference
        if weekend['more_active_on'] == 'Weekend':
            parts.append("You're more active on weekends.")
        else:
            parts.append("You text more during the week.")
        
        # Add positivity note
        if traits['positivity'] > 70:
            parts.append("Your messages tend to be very positive! 😊")
        elif traits['positivity'] < 40:
            parts.append("You keep it real in your texts.")
        
        return " ".join(parts)

    # =========================================================================
    # PHASE 2 - ADDITIONAL ADVANCED ANALYTICS
    # =========================================================================

    def get_conversation_enders(self, gap_hours: int = 6) -> pd.DataFrame:
        """
        Analyze who typically ends conversations (last message before gap)
        
        Args:
            gap_hours: Minimum gap to consider conversation ended
            
        Returns:
            DataFrame with conversation ending stats per contact
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact].sort_values('date')
            
            if len(contact_msgs) < 5:
                continue
            
            you_ended = 0
            they_ended = 0
            
            prev_msg = None
            for idx, msg in contact_msgs.iterrows():
                if prev_msg is not None:
                    gap = (msg['date'] - prev_msg['date']).total_seconds() / 3600
                    if gap >= gap_hours:
                        # Previous message ended the conversation
                        if prev_msg['is_from_me'] == 1:
                            you_ended += 1
                        else:
                            they_ended += 1
                prev_msg = msg
            
            # Last message also counts as an ender
            if prev_msg is not None:
                if prev_msg['is_from_me'] == 1:
                    you_ended += 1
                else:
                    they_ended += 1
            
            total = you_ended + they_ended
            if total >= 3:
                results.append({
                    'phone_number': contact,
                    'display_name': get_contact_display_name(contact),
                    'you_ended': you_ended,
                    'they_ended': they_ended,
                    'total_conversations': total,
                    'you_end_pct': (you_ended / total * 100) if total > 0 else 50
                })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('total_conversations', ascending=False)
        return df.reset_index(drop=True)

    def get_thread_resurrection(self, days_threshold: int = 7) -> pd.DataFrame:
        """
        Who revives dead conversations (messages after N+ days of silence)
        
        Args:
            days_threshold: Days of silence before revival counts
            
        Returns:
            DataFrame with resurrection stats
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact].sort_values('date')
            
            if len(contact_msgs) < 10:
                continue
            
            you_revived = 0
            they_revived = 0
            
            prev_time = None
            for idx, msg in contact_msgs.iterrows():
                if prev_time is not None:
                    gap_days = (msg['date'] - prev_time).days
                    if gap_days >= days_threshold:
                        if msg['is_from_me'] == 1:
                            you_revived += 1
                        else:
                            they_revived += 1
                prev_time = msg['date']
            
            total = you_revived + they_revived
            if total >= 1:
                results.append({
                    'phone_number': contact,
                    'display_name': get_contact_display_name(contact),
                    'you_revived': you_revived,
                    'they_revived': they_revived,
                    'total_resurrections': total,
                    'comeback_king': 'You' if you_revived > they_revived else 'Them'
                })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('total_resurrections', ascending=False).head(15)
        return df.reset_index(drop=True)

    def get_seasonal_trends(self) -> pd.DataFrame:
        """
        Analyze message volume by season
        
        Returns:
            DataFrame with seasonal messaging patterns
        """
        msgs = self.messages.copy()
        msgs['month_num'] = msgs['date'].dt.month
        
        # Assign seasons (Northern Hemisphere)
        def get_season(month):
            if month in [12, 1, 2]:
                return 'Winter'
            elif month in [3, 4, 5]:
                return 'Spring'
            elif month in [6, 7, 8]:
                return 'Summer'
            else:
                return 'Fall'
        
        msgs['season'] = msgs['month_num'].apply(get_season)
        
        seasonal_stats = []
        for season in ['Winter', 'Spring', 'Summer', 'Fall']:
            season_msgs = msgs[msgs['season'] == season]
            if len(season_msgs) > 0:
                seasonal_stats.append({
                    'season': season,
                    'total_messages': len(season_msgs),
                    'avg_per_day': len(season_msgs) / max(season_msgs['date'].dt.date.nunique(), 1),
                    'sent': (season_msgs['is_from_me'] == 1).sum(),
                    'received': (season_msgs['is_from_me'] == 0).sum(),
                    'emoji_rate': len([e for emojis in season_msgs['emojis'] for e in emojis]) / len(season_msgs) * 100
                })
        
        return pd.DataFrame(seasonal_stats)

    def get_dead_hours(self, min_days: int = 30) -> list:
        """
        Identify hours when you NEVER (or rarely) text
        
        Args:
            min_days: Minimum days of data required
            
        Returns:
            List of dead hours
        """
        msgs = self.messages.copy()
        
        # Count messages per hour
        hourly = msgs.groupby('hour').size()
        total_days = (msgs['date'].max() - msgs['date'].min()).days
        
        if total_days < min_days:
            return []
        
        dead_hours = []
        for hour in range(24):
            count = hourly.get(hour, 0)
            # If less than 1 message per week on average
            if count < (total_days / 7):
                dead_hours.append(hour)
        
        return dead_hours

    def get_message_momentum(self, window_days: int = 7) -> pd.DataFrame:
        """
        Detect when conversations are accelerating vs slowing down
        
        Args:
            window_days: Rolling window for momentum calculation
            
        Returns:
            DataFrame with momentum per contact
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact].copy()
            
            if len(contact_msgs) < 20:
                continue
            
            # Group by week
            contact_msgs['week'] = contact_msgs['date'].dt.to_period('W')
            weekly = contact_msgs.groupby('week').size()
            
            if len(weekly) < 4:
                continue
            
            # Calculate momentum (recent vs early)
            recent_weeks = weekly.tail(4).mean()
            older_weeks = weekly.head(4).mean()
            
            if older_weeks > 0:
                momentum = ((recent_weeks - older_weeks) / older_weeks) * 100
            else:
                momentum = 100 if recent_weeks > 0 else 0
            
            results.append({
                'phone_number': contact,
                'display_name': get_contact_display_name(contact),
                'recent_weekly_avg': recent_weeks,
                'older_weekly_avg': older_weeks,
                'momentum_pct': momentum,
                'status': '🚀 Accelerating' if momentum > 20 else ('📉 Slowing' if momentum < -20 else '➡️ Steady')
            })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('momentum_pct', ascending=False)
        return df.reset_index(drop=True)

    def get_one_way_streets(self, min_messages: int = 20) -> pd.DataFrame:
        """
        Find contacts you message but rarely message back (or vice versa)
        
        Args:
            min_messages: Minimum total messages
            
        Returns:
            DataFrame with one-sided conversation stats
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact]
            
            total = len(contact_msgs)
            if total < min_messages:
                continue
            
            sent = (contact_msgs['is_from_me'] == 1).sum()
            received = (contact_msgs['is_from_me'] == 0).sum()
            
            # Calculate imbalance
            if total > 0:
                your_pct = (sent / total) * 100
                imbalance = abs(your_pct - 50)  # 0 = perfectly balanced, 50 = one-sided
                
                if imbalance > 25:  # More than 75/25 split
                    results.append({
                        'phone_number': contact,
                        'display_name': get_contact_display_name(contact),
                        'you_sent': sent,
                        'they_sent': received,
                        'your_pct': your_pct,
                        'imbalance': imbalance,
                        'direction': 'You → Them' if your_pct > 50 else 'Them → You'
                    })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('imbalance', ascending=False).head(15)
        return df.reset_index(drop=True)

    def get_group_chat_mvps(self) -> pd.DataFrame:
        """
        Who drives the most conversation in each group chat
        
        Returns:
            DataFrame with MVP per group chat
        """
        group_msgs = self.messages[self.messages['is_group'] == True].copy()
        
        if len(group_msgs) == 0:
            return pd.DataFrame()
        
        results = []
        
        for chat_id in group_msgs['chat_id'].unique():
            chat_msgs = group_msgs[group_msgs['chat_id'] == chat_id]
            
            if len(chat_msgs) < 20:
                continue
            
            # Get chat name
            chat_name = chat_msgs['chat_name'].dropna().iloc[0] if len(chat_msgs['chat_name'].dropna()) > 0 else f"Group #{chat_id}"
            
            # Count messages per participant
            participant_counts = chat_msgs[chat_msgs['is_from_me'] == 0].groupby('phone_number').size()
            
            if len(participant_counts) > 0:
                mvp = participant_counts.idxmax()
                mvp_count = participant_counts.max()
                total_from_others = participant_counts.sum()
                
                results.append({
                    'chat_id': chat_id,
                    'chat_name': chat_name,
                    'mvp': get_contact_display_name(mvp),
                    'mvp_messages': mvp_count,
                    'mvp_pct': (mvp_count / total_from_others * 100) if total_from_others > 0 else 0,
                    'total_messages': len(chat_msgs)
                })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('total_messages', ascending=False).head(10)
        return df.reset_index(drop=True)

    def get_group_chat_lurkers(self) -> pd.DataFrame:
        """
        Find people in group chats who rarely participate
        
        Returns:
            DataFrame with lurker stats
        """
        group_msgs = self.messages[self.messages['is_group'] == True].copy()
        
        if len(group_msgs) == 0:
            return pd.DataFrame()
        
        # Get all participants and their message counts
        participant_stats = {}
        
        for chat_id in group_msgs['chat_id'].unique():
            chat_msgs = group_msgs[group_msgs['chat_id'] == chat_id]
            chat_name = chat_msgs['chat_name'].dropna().iloc[0] if len(chat_msgs['chat_name'].dropna()) > 0 else f"Group #{chat_id}"
            
            # Get participant counts
            participant_counts = chat_msgs[chat_msgs['is_from_me'] == 0].groupby('phone_number').size()
            total_msgs = len(chat_msgs)
            
            for phone, count in participant_counts.items():
                pct = (count / total_msgs * 100) if total_msgs > 0 else 0
                if pct < 5:  # Less than 5% participation = lurker
                    key = phone
                    if key not in participant_stats:
                        participant_stats[key] = {
                            'phone_number': phone,
                            'display_name': get_contact_display_name(phone),
                            'groups_lurking': 0,
                            'total_lurk_msgs': 0
                        }
                    participant_stats[key]['groups_lurking'] += 1
                    participant_stats[key]['total_lurk_msgs'] += count
        
        results = list(participant_stats.values())
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('groups_lurking', ascending=False).head(15)
        return df.reset_index(drop=True)

    def get_text_vs_media_ratio(self) -> pd.DataFrame:
        """
        Compare text vs media messages per contact
        
        Returns:
            DataFrame with text/media ratio per contact
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact]
            
            total = len(contact_msgs)
            if total < 20:
                continue
            
            # Text messages have actual text content
            text_msgs = (contact_msgs['text'].str.len() > 0).sum()
            media_msgs = total - text_msgs
            
            results.append({
                'phone_number': contact,
                'display_name': get_contact_display_name(contact),
                'text_messages': text_msgs,
                'media_messages': media_msgs,
                'text_pct': (text_msgs / total * 100) if total > 0 else 50,
                'style': 'Text Heavy' if text_msgs > media_msgs * 1.5 else ('Media Heavy' if media_msgs > text_msgs * 1.5 else 'Balanced')
            })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('media_messages', ascending=False)
        return df.reset_index(drop=True)

    def get_average_sentence_length(self) -> dict:
        """
        Analyze if you're a rambler or concise texter
        
        Returns:
            Dictionary with sentence length stats
        """
        text_msgs = self.messages[self.messages['text'].str.len() > 0].copy()
        
        if len(text_msgs) == 0:
            return {'you_avg': 0, 'they_avg': 0}
        
        sent = text_msgs[text_msgs['is_from_me'] == 1]
        received = text_msgs[text_msgs['is_from_me'] == 0]
        
        you_avg = sent['word_count'].mean() if len(sent) > 0 else 0
        they_avg = received['word_count'].mean() if len(received) > 0 else 0
        
        # Classify style
        if you_avg < 5:
            your_style = 'Ultra Concise'
        elif you_avg < 10:
            your_style = 'Concise'
        elif you_avg < 20:
            your_style = 'Moderate'
        elif you_avg < 40:
            your_style = 'Detailed'
        else:
            your_style = 'Essay Writer'
        
        return {
            'you_avg_words': you_avg,
            'they_avg_words': they_avg,
            'your_style': your_style,
            'you_longer': you_avg > they_avg,
            'difference': abs(you_avg - they_avg)
        }

    def get_message_bingo(self) -> list:
        """
        Find your most commonly used phrases/patterns
        
        Returns:
            List of common phrases you use
        """
        sent_msgs = self.messages[(self.messages['is_from_me'] == 1) & (self.messages['text'].str.len() > 0)]
        
        if len(sent_msgs) < 100:
            return []
        
        # Common phrase patterns to look for
        phrases_to_check = {
            'haha': 0, 'lol': 0, 'omg': 0, 'yeah': 0, 'yes': 0, 'no': 0,
            'ok': 0, 'okay': 0, 'sure': 0, 'thanks': 0, 'thank you': 0,
            'sorry': 0, 'love you': 0, 'miss you': 0, 'see you': 0,
            "i'm": 0, "i'll": 0, "i've": 0, 'gonna': 0, 'wanna': 0,
            'nice': 0, 'cool': 0, 'awesome': 0, 'amazing': 0, 'great': 0,
            'good morning': 0, 'good night': 0, 'hey': 0, 'hi': 0, 'hello': 0,
            'what': 0, 'how': 0, 'why': 0, 'when': 0, 'where': 0,
            'literally': 0, 'actually': 0, 'basically': 0, 'honestly': 0,
            '!!': 0, '??': 0, '...': 0, 'lmao': 0, 'omfg': 0
        }
        
        for text in sent_msgs['text'].str.lower():
            if not text:
                continue
            for phrase in phrases_to_check:
                if phrase in text:
                    phrases_to_check[phrase] += 1
        
        # Get top phrases
        sorted_phrases = sorted(phrases_to_check.items(), key=lambda x: x[1], reverse=True)
        
        # Return top 12 that have been used at least 10 times
        bingo_card = [{'phrase': p, 'count': c} for p, c in sorted_phrases if c >= 10][:12]
        
        return bingo_card

    def get_contact_affinity_score(self) -> pd.DataFrame:
        """
        Calculate a relationship strength score for each contact
        
        Score based on: frequency, recency, balance, response time, depth
        
        Returns:
            DataFrame with affinity scores
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        now = self.messages['date'].max()
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact]
            
            total = len(contact_msgs)
            if total < 10:
                continue
            
            # Frequency score (0-25)
            freq_score = min(25, total / 100 * 25)
            
            # Recency score (0-25)
            last_msg = contact_msgs['date'].max()
            days_since = (now - last_msg).days
            if days_since < 7:
                recency_score = 25
            elif days_since < 30:
                recency_score = 20
            elif days_since < 90:
                recency_score = 15
            elif days_since < 180:
                recency_score = 10
            else:
                recency_score = 5
            
            # Balance score (0-25)
            sent = (contact_msgs['is_from_me'] == 1).sum()
            received = (contact_msgs['is_from_me'] == 0).sum()
            balance = min(sent, received) / max(sent, received, 1)
            balance_score = balance * 25
            
            # Consistency score (0-25) - how many months active
            months = contact_msgs['date'].dt.to_period('M').nunique()
            consistency_score = min(25, months * 2.5)
            
            total_score = freq_score + recency_score + balance_score + consistency_score
            
            results.append({
                'phone_number': contact,
                'display_name': get_contact_display_name(contact),
                'affinity_score': total_score,
                'frequency_score': freq_score,
                'recency_score': recency_score,
                'balance_score': balance_score,
                'consistency_score': consistency_score,
                'grade': 'A+' if total_score >= 90 else ('A' if total_score >= 80 else ('B' if total_score >= 70 else ('C' if total_score >= 60 else 'D')))
            })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('affinity_score', ascending=False)
        return df.reset_index(drop=True)

    def get_best_time_to_text(self) -> pd.DataFrame:
        """
        When each contact is most likely to respond quickly
        
        Returns:
            DataFrame with optimal texting times per contact
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        results = []
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact].sort_values('date')
            
            if len(contact_msgs) < 50:
                continue
            
            # Track response times by hour you sent
            hourly_response_times = {h: [] for h in range(24)}
            
            prev_msg = None
            for idx, msg in contact_msgs.iterrows():
                if prev_msg is not None:
                    # If you sent, and they responded
                    if prev_msg['is_from_me'] == 1 and msg['is_from_me'] == 0:
                        time_diff = (msg['date'] - prev_msg['date']).total_seconds() / 60
                        if 0 < time_diff < 1440:  # Within 24 hours
                            hour_sent = prev_msg['date'].hour
                            hourly_response_times[hour_sent].append(time_diff)
                prev_msg = msg
            
            # Find best hour
            best_hour = None
            best_time = float('inf')
            
            for hour, times in hourly_response_times.items():
                if len(times) >= 5:
                    avg = np.median(times)
                    if avg < best_time:
                        best_time = avg
                        best_hour = hour
            
            if best_hour is not None:
                results.append({
                    'phone_number': contact,
                    'display_name': get_contact_display_name(contact),
                    'best_hour': best_hour,
                    'avg_response_mins': best_time,
                    'time_label': f"{best_hour:02d}:00"
                })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('avg_response_mins', ascending=True)
        return df.reset_index(drop=True)

    def get_emoji_evolution(self) -> pd.DataFrame:
        """
        Track how emoji usage has changed over time
        
        Returns:
            DataFrame with emoji usage by period
        """
        msgs = self.messages.copy()
        msgs['year_month'] = msgs['date'].dt.to_period('M')
        
        results = []
        for period in sorted(msgs['year_month'].unique()):
            period_msgs = msgs[msgs['year_month'] == period]
            
            all_emojis = [e for emojis in period_msgs['emojis'] for e in emojis]
            
            if len(all_emojis) > 0:
                top_emoji = Counter(all_emojis).most_common(1)[0]
                unique_emojis = len(set(all_emojis))
            else:
                top_emoji = ('', 0)
                unique_emojis = 0
            
            results.append({
                'period': str(period),
                'total_emojis': len(all_emojis),
                'unique_emojis': unique_emojis,
                'top_emoji': top_emoji[0],
                'emoji_per_msg': len(all_emojis) / len(period_msgs) * 100 if len(period_msgs) > 0 else 0
            })
        
        return pd.DataFrame(results)

    def get_multi_tasking_indicator(self) -> dict:
        """
        Detect concurrent conversations at once
        
        Returns:
            Dictionary with multi-tasking stats
        """
        msgs = self.messages[self.messages['is_from_me'] == 1].copy()
        msgs = msgs.sort_values('date')
        
        # Look for messages to different contacts within 5 minutes
        concurrent_sessions = 0
        max_concurrent = 1
        
        for i in range(len(msgs) - 1):
            curr = msgs.iloc[i]
            next_msg = msgs.iloc[i + 1]
            
            time_diff = (next_msg['date'] - curr['date']).total_seconds() / 60
            
            # If within 5 minutes to a different contact
            if time_diff < 5 and curr['chat_id'] != next_msg['chat_id']:
                concurrent_sessions += 1
        
        # Calculate average
        total_days = (msgs['date'].max() - msgs['date'].min()).days
        
        return {
            'concurrent_sessions': concurrent_sessions,
            'avg_per_day': concurrent_sessions / max(total_days, 1),
            'multitasker_level': 'Heavy' if concurrent_sessions / max(total_days, 1) > 5 else ('Moderate' if concurrent_sessions / max(total_days, 1) > 2 else 'Light')
        }

    def get_monthly_mvp(self) -> pd.DataFrame:
        """
        Most active contact each month
        
        Returns:
            DataFrame with monthly MVP
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        one_on_one['year_month'] = one_on_one['date'].dt.to_period('M')
        
        results = []
        for period in sorted(one_on_one['year_month'].unique()):
            period_msgs = one_on_one[one_on_one['year_month'] == period]
            
            contact_counts = period_msgs.groupby('phone_number').size()
            
            if len(contact_counts) > 0:
                mvp = contact_counts.idxmax()
                mvp_count = contact_counts.max()
                
                results.append({
                    'period': str(period),
                    'mvp': get_contact_display_name(mvp),
                    'message_count': mvp_count,
                    'pct_of_month': (mvp_count / len(period_msgs) * 100) if len(period_msgs) > 0 else 0
                })
        
        return pd.DataFrame(results)

    def get_contact_churn_rate(self) -> dict:
        """
        How many new contacts per month vs inactive ones
        
        Returns:
            Dictionary with churn statistics
        """
        one_on_one = self.messages[self.messages['is_group'] == False].copy()
        one_on_one['year_month'] = one_on_one['date'].dt.to_period('M')
        
        # Track first and last appearance of each contact
        contact_first_seen = {}
        contact_last_seen = {}
        
        for contact in one_on_one['phone_number'].dropna().unique():
            contact_msgs = one_on_one[one_on_one['phone_number'] == contact]
            contact_first_seen[contact] = contact_msgs['year_month'].min()
            contact_last_seen[contact] = contact_msgs['year_month'].max()
        
        # Count new vs churned by month
        months = sorted(one_on_one['year_month'].unique())
        
        new_contacts_per_month = []
        churned_per_month = []
        
        for period in months:
            new = sum(1 for c, first in contact_first_seen.items() if first == period)
            churned = sum(1 for c, last in contact_last_seen.items() if last == period)
            new_contacts_per_month.append(new)
            churned_per_month.append(churned)
        
        return {
            'total_contacts': len(contact_first_seen),
            'avg_new_per_month': np.mean(new_contacts_per_month) if new_contacts_per_month else 0,
            'avg_churned_per_month': np.mean(churned_per_month[:-1]) if len(churned_per_month) > 1 else 0,  # Exclude last month
            'net_growth': np.mean(new_contacts_per_month) - np.mean(churned_per_month[:-1]) if len(churned_per_month) > 1 else 0
        }

    def get_all_time_records(self) -> dict:
        """
        All-time records and extremes
        
        Returns:
            Dictionary with record-breaking stats
        """
        records = {}
        
        # Busiest single day
        daily = self.messages.groupby(self.messages['date'].dt.date).size()
        if len(daily) > 0:
            busiest_day = daily.idxmax()
            records['busiest_day'] = {
                'date': str(busiest_day),
                'count': int(daily.max())
            }
        
        # Longest message
        text_msgs = self.messages[self.messages['text'].str.len() > 0]
        if len(text_msgs) > 0:
            longest_idx = text_msgs['char_count'].idxmax()
            longest_msg = text_msgs.loc[longest_idx]
            records['longest_message'] = {
                'length': int(longest_msg['char_count']),
                'preview': str(longest_msg['text'])[:100] + '...' if len(str(longest_msg['text'])) > 100 else str(longest_msg['text'])
            }
        
        # Most emojis in single message
        emoji_counts = self.messages['emojis'].apply(len)
        if emoji_counts.max() > 0:
            most_emoji_idx = emoji_counts.idxmax()
            most_emoji_msg = self.messages.loc[most_emoji_idx]
            records['most_emojis_single'] = {
                'count': int(emoji_counts.max()),
                'emojis': ''.join(most_emoji_msg['emojis'][:10])
            }
        
        # First message ever
        first_msg = self.messages.iloc[0]
        records['first_message'] = {
            'date': str(first_msg['date'].date()),
            'preview': str(first_msg['text'])[:50] if first_msg['text'] else '[Media]'
        }
        
        # Total days with messages
        records['total_days_active'] = self.messages['date'].dt.date.nunique()
        
        return records

    def get_comprehensive_stats(self) -> dict:
        """
        Get all stats in a comprehensive dictionary for export/overview
        
        Returns:
            Dictionary with comprehensive statistics
        """
        stats = {
            'summary': self.get_summary_stats(),
            'personality': self.get_messaging_personality(),
            'all_time_records': self.get_all_time_records(),
            'streak': self.get_longest_streak(),
            'emoji_stats': self.get_emoji_stats(),
            'sentiment': self.get_sentiment_analysis(),
            'churn': self.get_contact_churn_rate(),
            'sentence_length': self.get_average_sentence_length()
        }
        
        return stats

